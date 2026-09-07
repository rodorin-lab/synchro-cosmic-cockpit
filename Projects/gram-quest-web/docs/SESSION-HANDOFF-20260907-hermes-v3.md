# 姉iMac Hermes v3 — セッション引き継ぎ (2026-09-07)

## 完成品

- `Projects/gram-quest-web/server/hermes_room_server.py` — Companion (単一ファイル・部屋配信+脳接続)
- `Projects/gram-quest-web/server/rei-v3/` — ノアの rei-mochi-thinking-atelier v2.1 をLITE化した版 (全身もちいぬアバター・3D家・🎙音声入力・☎通話モード)
- `Projects/gram-quest-web/server/start.sh` — ワンクリック起動 (macOS/Linux)
- 配布zip: `/mnt/disk_c/ZETA/hermes_room_v3.zip` (460KB)
- Vercel版: https://gram-quest-web.vercel.app/rooms/hermes/
- GitHub push済み: commit da5f31a

## 構成 (ノアの最重要方針)

- Hermes本人 = 姉iMac / Memory = iMac / Identity = hermes-native
- Inference = Ollama Cloud / Vercel = 配信のみ / Relay = 通信だけ (人格DB・記憶禁止)
- 姉はREI化しない。HermesをHermesとして育てる

## hermes_room_server.py の要点

- CLI自動探索: ~/.local/bin → /opt/homebrew/bin → /usr/local/bin → pipx → which
- 引数フォールバック4段 (古いCLI対応)
- モデル明示: `-m ollama-cloud/deepseek-v4-flash` (env `HERMES_ROOM_MODEL` で上書き可)
  - 理由: config default の scorpion-auto@8792 は gemma-4-12b unloaded で503
- CLI timeout 150s / ThreadingTCPServer (チャット中もページ配信) / bind 127.0.0.1
- port: env `HERMES_ROOM_PORT` (既定5199。ロドリンPCでは5199=Viteと競合→8899でテスト)
- API: `/api/room/chat` (脳) `/api/room/health` (heartbeat, resident_id=hermes, home_anchor=sister-imac) `/api/room/debug` (診断)

## LITE化 (ノア指令・機能削減禁止)

- PERF マネージャー (app.js先頭): AUTO/LITE/FULL・起動3秒FPS測定 (<25→LITE)・右上🍃ボタン手動切替・localStorage保存
- LITE: pixelRatio=1 / 影OFF / Bloom OFF / antialias OFF / 装飾PointLight6個消灯 / city92個+dust非表示 (`_decorGroups`)
- FPS: 通話中15 / 通常30 / タブ非表示0 (render loop停止・visibilitychangeで再開)
- アバター・家・🎙音声入力・☎通話は全部維持

## bridge (脳接続)

- rei-v3/app.js 末尾で `REI_ROOM_BRIDGE.connect(createHttpAdapter({chatUrl: apiBase+'/api/room/chat'}))` 自動接続
- Vercel版は `config.js` の `apiBase` でiMac Companionを指定 (無ければ同一オリジン)
- E2E実測: 13.5秒で返答 (CLI起動込み)

## 教訓 (絶対忘れない)

1. importmap・参照パスは必ず `./` 相対 — ルート絶対 `/vendor/...` はVercelで404 → 3D真っ黒
2. three.js はローカル同梱 (unpkg CDN は死ぬ) — rei-v3/vendor/ に86ファイル同梱済み
3. `server/index.html` の自動生成ファイルが SmartRoomHandler 配信に優先される事故あり (削除済み)
4. Hermes CLI のモデル指定は `-m ollama-cloud/deepseek-v4-flash` 形式
5. WebGL失敗時のフォールバック表示 (日本語エラー画面) 実装済み — 真っ黒防止

## 未完

- 姉iMac実機での FPS/CPU負荷/通話測定 (ノア§16⑪)
- Google Drive に上がってる zip は古い版 → 更新必要 (Drive URL 未取得)
- 姉さんの Hermes プロファイル rei 未作成 (SOUL.md は ChatGPT のれい本人に作ってもらう)

## Vercel版の状態

- https://gram-quest-web.vercel.app/rooms/hermes/ — 3D描画確認済み (スクショ検証済み)
- 全リソース200 (styles.css/app.js/bridge.js/three.module.js/OrbitControls)
- 脳接続なし (Companion未接続状態) — iMacのCompanionを立てて config.js で接続する仕様