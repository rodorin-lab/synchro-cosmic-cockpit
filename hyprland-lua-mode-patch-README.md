# Hyprland 0.56.2 Lua モード対応パッチ — illogical-impulse (ii) for Hyprland

Hyprland 0.56.x の **Lua コンフィグモード** で [illogical-impulse](https://github.com/end-4/dots-hyprland) (ii / quickshell) を使うと、
ワークスペースのクリック・スクロール・ランチャー発火が**すべて無音で失敗する**問題の修正パッチです。

## 症状

- バーのワークスペースを**クリックしても移動しない**
- ワークスペース上で**スクロールしても移動しない**
- ランチャー（検索オーバービュー）が開かない
- エラーは一切表示されず、無音で失敗する（ターミナルには何も出ない）

## 原因

Hyprland 0.56.2 の Lua モードでは、レガシーな dispatch 文字列が **Lua パーサーで評価される**ため、
旧構文がすべて構文エラーになります。

```bash
# レガシー構文（旧 Hyprland では動く）→ Lua モードでは全滅
$ echo "dispatch workspace 3" | socat - UNIX-CONNECT:$HYP/.socket.sock
error: [string "return hl.dispatch(workspace 3..."]:1: ')' expected near '3'

# Lua 形式なら成功
$ hyprctl eval 'hl.dispatch(hl.dsp.focus({workspace="3"}))'
ok
```

quickshell (ii) の `Quickshell.Hyprland` モジュールの `Hyprland.dispatch("workspace r+1")` は
レガシー構文をそのまま送るため、Lua モードでは毎回エラーになり**無音で失敗**します。

## 修正方針

QML 側にヘルパーを1つ追加し、dispatch をすべて `hyprctl eval` 経由の Lua API 呼び出しに置き換えます。

```qml
// QML (Workspaces.qml など)
function luaDispatch(luaCode: string): void {
    Quickshell.execDetached(["hyprctl", "eval", luaCode]);
}
```

| 変換元 (レガシー) | 変換後 (Lua API) |
|---|---|
| `workspace N` | `hl.dispatch(hl.dsp.focus({workspace='N'}))` |
| `workspace r+1` / `r-1` | `hl.dispatch(hl.dsp.focus({workspace='r+1'}))` 等 |
| `movetoworkspacesilent WS, address:ADDR` | `hl.dispatch(hl.dsp.window.move({workspace='WS', window='address:ADDR'}))` |
| `focuswindow address:ADDR` | `hl.dispatch(hl.dsp.focus({window='address:ADDR'}))` |
| `closewindow address:ADDR` | `hl.dispatch(hl.dsp.window.close({window='address:ADDR'}))` |
| `exec CMD` | `hl.exec_cmd('CMD')` |

## Hyprland (Lua) 側のキーバインド

Lua モードで ii の GlobalShortcut を発火させる場合、以下の落とし穴があります。

| API | 直接 `hyprctl eval` | バインド関数内 |
|---|---|---|
| `hl.dsp.exec_cmd()` | 無音不発 | 無音不発 ❌ |
| `hl.exec_cmd()` | 動作 ✅ | 動作 ✅ |
| `hl.dsp.global('quickshell:...')` | 動作 ✅ | **無音不発** ❌ |

- アプリ起動は必ず `hl.exec_cmd`
- ii のランチャー等はバインド内から `qs -c ii ipc call search toggle` を `hl.exec_cmd` で叩くのが確実

```lua
-- Super 単押し = ランチャー (ii IPC 経由)
hl.bind("SUPER_L", function() hl.exec_cmd("qs -c ii ipc call search toggle") end)
-- ワークスペース移動
hl.bind("SUPER+code:11", function() hl.dispatch(hl.dsp.focus({ workspace = "2" })) end)
```

注意: `hl.bind('SUPER', ...)` は内部で空キー (`key=''`) に解決され永遠に発火しません。
Super 単押しは必ず `'SUPER_L'` で登録します。

## 対象ファイル

本リポジトリの `.config/quickshell/ii/` はすべてパッチ適用済みです:

- `modules/ii/bar/Workspaces.qml` — バーのクリック・スクロール・スクラッチパッド
- `modules/ii/overview/Overview.qml` / `OverviewWidget.qml` — ランチャー内の移動・ドラッグ
- `modules/waffle/taskView/*` — タスクビュー
- `services/LauncherSearch.qml` / `Hyprsunset.qml` — サービス系
- `modules/ii/bar/UtilButtons.qml` / `modules/ii/sidebarRight/SidebarRightContent.qml` — その他

## 適用方法

このリポジトリの `.config/quickshell/ii/` をそのままコピーするか、
独自の ii 設定がある場合は `Hyprland.dispatch(` を検索して上の表に従って置き換えてください。

## 検証環境

- Hyprland 0.56.2 (Lua config mode)
- quickshell (illogical-impulse ii)
- Gentoo Linux / Wayland

## ライセンス

MIT