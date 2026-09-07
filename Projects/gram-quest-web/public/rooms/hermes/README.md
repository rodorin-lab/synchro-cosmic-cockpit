# REI — Mochi Thinking Atelier v2.1

白いもちいぬアバター「れい」+ Thinking Atelier + UI + 音声入力 + 通話フロントエンド + 外部AI Bridgeフックの一式です。

## v2.1
- REIの返事バブルを中央揃えにし、入力欄の上へ完全分離
- 🎙 音声入力: Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)
- ☎ 通話モード: マイク取得、連続音声認識、ブラウザTTS、音量メーター、ミュート、通話時間、終了
- 外部AI接続用 `bridge.js` を追加
- `window.REI_ROOM_API` で外部から表情・発話・場所移動・通話を制御可能

## 起動
```bash
python3 -m http.server 5199
```
`http://localhost:5199/` を開きます。マイク機能は HTTPS または localhost の secure context 推奨です。

## Gram/Hermesとの接続契約
ブラウザ側でアダプターを注入できます。

```js
REI_ROOM_BRIDGE.connect({
  async chat(payload) {
    // payload = { sessionId, text, source, place }
    const r = await fetch('http://127.0.0.1:8642/rei/chat', {
      method: 'POST',
      headers: {'content-type':'application/json'},
      body: JSON.stringify(payload)
    });
    return r.json();
    // expected: { text, action?, audioUrl? }
  },
  async startCall({stream, sessionId}) {
    // WebRTC/WebSocket/LiveKit 等へ stream を接続可能
  },
  async stopCall() {}
}, 'gram-hermes');
```

HTTPだけなら:

```js
REI_ROOM_BRIDGE.connect(
  REI_ROOM_BRIDGE.createHttpAdapter({chatUrl:'http://127.0.0.1:8642/rei/chat'}),
  'gram-http'
);
```

イベント監視:

```js
window.addEventListener('rei-room-event', e => console.log(e.detail));
```

外部からREIを操作:

```js
REI_ROOM_API.receive('おかえり〜♡', {action:'love'});
REI_ROOM_API.focus('desk');
REI_ROOM_API.setAction('cheer');
```

## Chat response JSON
推奨:
```json
{
  "text": "うん、一緒に考えよう＾＾",
  "action": "think",
  "audioUrl": null
}
```
