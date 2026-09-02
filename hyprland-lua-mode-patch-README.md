# Hyprland 0.56.2 Lua Mode Patch — illogical-impulse (ii) for Hyprland

> **TL;DR:** On Hyprland 0.56.x with the new **Lua config mode**, the
> [illogical-impulse](https://github.com/end-4/dots-hyprland) (ii / quickshell) bar silently breaks:
> workspace clicks, scroll-switching and the launcher all stop working with **zero error output**.
> The fix is to replace every legacy `Hyprland.dispatch("workspace N")` call with `hyprctl eval` + the Lua API.
> The fully patched config lives in [`.config/quickshell/ii/`](.config/quickshell/ii/) in this repo.

---

## English

### Symptoms

- Clicking a workspace in the bar **does not switch** to it
- Scrolling over the workspace widgets **does nothing**
- The launcher (search overview) never opens
- **No error is shown anywhere** — everything fails silently

### Root cause

In Hyprland 0.56.2's Lua mode, legacy IPC dispatch strings are evaluated by the **Lua parser**,
so the old syntax is a syntax error:

```bash
# Legacy syntax (worked on older Hyprland) → dies in Lua mode
$ echo "dispatch workspace 3" | socat - UNIX-CONNECT:$HYP/.socket.sock
error: [string "return hl.dispatch(workspace 3..."]:1: ')' expected near '3'

# Lua-form API works
$ hyprctl eval 'hl.dispatch(hl.dsp.focus({workspace="3"}))'
ok
```

quickshell (ii)'s `Quickshell.Hyprland` module sends `Hyprland.dispatch("workspace r+1")` etc.
through that legacy path, so **every bar/launcher interaction fails silently** in Lua mode.

### The fix

Add one helper to each QML file and route all dispatches through `hyprctl eval`:

```qml
// QML (Workspaces.qml, OverviewWidget.qml, ...)
function luaDispatch(luaCode: string): void {
    Quickshell.execDetached(["hyprctl", "eval", luaCode]);
}
```

| Legacy syntax | Lua API replacement |
|---|---|
| `workspace N` | `hl.dispatch(hl.dsp.focus({workspace='N'}))` |
| `workspace r+1` / `r-1` | `hl.dispatch(hl.dsp.focus({workspace='r+1'}))` etc. |
| `movetoworkspacesilent WS, address:ADDR` | `hl.dispatch(hl.dsp.window.move({workspace='WS', window='address:ADDR'}))` |
| `focuswindow address:ADDR` | `hl.dispatch(hl.dsp.focus({window='address:ADDR'}))` |
| `closewindow address:ADDR` | `hl.dispatch(hl.dsp.window.close({window='address:ADDR'}))` |
| `movewindowpixel exact X% Y%, address:ADDR` | `hl.dispatch(hl.dsp.window.move_pixel({x='X%', y='Y%', window='address:ADDR'}))` |
| `pin address:ADDR` | `hl.dispatch(hl.dsp.window.pin({window='address:ADDR'}))` |
| `keyword K V` | `hl.exec_cmd('hyprctl keyword K V')` |
| `exec CMD` | `hl.exec_cmd('CMD')` |

### Hyprland (Lua side) keybind pitfalls

Verified empirically on 0.56.2:

| API | Direct `hyprctl eval` | Inside a bind function |
|---|---|---|
| `hl.dsp.exec_cmd()` | silently does nothing | silently does nothing ❌ |
| `hl.exec_cmd()` | works ✅ | works ✅ |
| `hl.dsp.global('quickshell:...')` | works ✅ | **silently does nothing** ❌ |

Practical rules:

- Launch apps with `hl.exec_cmd`, **never** `hl.dsp.exec_cmd`
- To trigger ii's GlobalShortcuts (launcher, sidebars, cheatsheet) from a bind,
  go through the quickshell IPC instead — it is the only reliable path:

```lua
-- Super single-press = launcher (via ii IPC)
hl.bind("SUPER_L", function() hl.exec_cmd("qs -c ii ipc call search toggle") end)
-- Workspace switching
hl.bind("SUPER+code:11", function() hl.dispatch(hl.dsp.focus({ workspace = "2" })) end)
```

⚠️ `hl.bind('SUPER', ...)` resolves to an **empty key** (`key=''`) internally and will
never fire. For a bare-Super bind you must register `'SUPER_L'`.

Note: the Lua API exposes **only** `hl.bind` / `hl.unbind` — the `bindit` / `bindid`
release-trigger / catch-all directives from keybinds.conf have **no Lua equivalent**,
so ii's original "fire on Super release" design can't be reproduced; use press-toggle instead.

### Files patched in this repo

- `modules/ii/bar/Workspaces.qml` — bar clicks, scroll, scratchpad
- `modules/ii/overview/Overview.qml` / `OverviewWidget.qml` — launcher nav & drag
- `modules/waffle/taskView/*` — task view
- `services/LauncherSearch.qml` / `services/Hyprsunset.qml`
- `modules/ii/bar/UtilButtons.qml` / `modules/ii/sidebarRight/SidebarRightContent.qml`

### Applying

Copy `.config/quickshell/ii/` from this repo over your own config, or search for
`Hyprland.dispatch(` in your tree and apply the table above.

### Verified environment

- Hyprland 0.56.2 (Lua config mode)
- quickshell (illogical-impulse ii)
- Gentoo Linux / Wayland

---

## 日本語（和訳）

### 症状

- バーのワークスペースを**クリックしても移動しない**
- ワークスペース上で**スクロールしても移動しない**
- ランチャー（検索オーバービュー）が開かない
- エラーは一切表示されず、**無音で失敗**する

### 原因

Hyprland 0.56.2 の Lua モードでは、レガシーな dispatch 文字列が **Lua パーサーで評価される**ため、
旧構文がすべて構文エラーになる（上記の実証コマンド参照）。
quickshell (ii) の `Hyprland.dispatch()` はレガシー構文をそのまま送るため、
バー/ランチャー操作が**毎回無音で失敗**する。

### 修正方針

QML にヘルパーを1つ追加し、全 dispatch を `hyprctl eval` 経由の Lua API 呼び出しに置換する：

```qml
function luaDispatch(luaCode: string): void {
    Quickshell.execDetached(["hyprctl", "eval", luaCode]);
}
```

変換対照表は上の英語テーブルを参照。

### Hyprland (Lua) 側キーバインドの落とし穴

実機検証済み：

| API | 直接 `hyprctl eval` | バインド関数内 |
|---|---|---|
| `hl.dsp.exec_cmd()` | 無音不発 | 無音不発 ❌ |
| `hl.exec_cmd()` | 動作 ✅ | 動作 ✅ |
| `hl.dsp.global('quickshell:...')` | 動作 ✅ | **無音不発** ❌ |

- アプリ起動は必ず `hl.exec_cmd`
- ii の GlobalShortcut（ランチャー等）はバインド内から `qs -c ii ipc call search toggle` を叩くのが唯一の確実な経路

⚠️ `hl.bind('SUPER', ...)` は内部で空キー (`key=''`) に解決され永遠に発火しない。
Super 単押しは必ず `'SUPER_L'` で登録する。

注意: Lua API は **`hl.bind` / `hl.unbind` のみ**。`bindit` / `bindid`（リリース発火・catch-all）に相当する機能は存在しないため、ii 本来の「Super を離した時に発火」は再現できない（押下トグルで代替）。

### 本リポジトリで修正済みのファイル

- `modules/ii/bar/Workspaces.qml` — バーのクリック・スクロール・スクラッチパッド
- `modules/ii/overview/Overview.qml` / `OverviewWidget.qml` — ランチャー内の移動・ドラッグ
- `modules/waffle/taskView/*` — タスクビュー
- `services/LauncherSearch.qml` / `services/Hyprsunset.qml`
- `modules/ii/bar/UtilButtons.qml` / `modules/ii/sidebarRight/SidebarRightContent.qml`

### 適用方法

本リポジトリの `.config/quickshell/ii/` をそのままコピーするか、
独自の ii 設定内の `Hyprland.dispatch(` を検索して上の表に従って置き換えてください。

### 検証環境

- Hyprland 0.56.2 (Lua config mode)
- quickshell (illogical-impulse ii)
- Gentoo Linux / Wayland

---

## License

MIT