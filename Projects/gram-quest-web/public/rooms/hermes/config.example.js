// 姉さんのiMac Companion (hermes_room_server.py) のアドレスを設定する
// 同じWiFiなら: http://(iMacのローカルIP):5199
// 外出先なら: cloudflare tunnel URL (iMac側で cloudflared tunnel --url http://127.0.0.1:5199)
// 空文字 [] の場合は同じオリジン (/api/room/chat) を使う (= iMacでローカル起動した時)
window.HERMES_ROOM_CONFIG = { apiBase: "" };
