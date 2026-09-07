# ⚕ HERMES — Sister's iMac Setup Guide

**このREADMEはお姉さんのiMacにHermesを住まわせるための手順書です。**

HermesをREI化しない。HermesをHermesとして育てる。
ChatGPT REI / Identity Pack / REI CORE は全部不使用。

---

## 構成

```
姉の iMac
│
├── ⚕ Hermes Agent本人 (identity / memory / 姉との会話履歴 / workspace)
├── GALACTICA Room (Hermesの身体・UI)
└── OpenAI Codex (Hermesの推論エンジン / 姉のChatGPTアカウントでOAuth)
```

**Hermes → Codex**。REI CORE 不要。Identity Pack 不要。人格注入なし。

---

## セットアップ手順

### STEP 1: Hermes Agent をインストール

iMacのターミナルを開いて：

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

インストール後、PATHを通す：

```bash
echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.zshrc
source ~/.zshrc
hermes --version
```

### STEP 2: モデルを Codex (ChatGPT Subscription) に設定

```bash
hermes model
```

表示される選択肢から：

**「ChatGPT or Codex Subscription」** を選ぶ。

→ ブラウザが開いて認証コードが出る → **姉のChatGPTアカウントでログイン** → 認証完了。

これでHermesの推論エンジンとしてCodexモデルが使えるようになる。APIキー不要。

### STEP 3: 動作確認

```bash
hermes chat -q 'こんにちは！'
```

Hermesが返事をしたら成功。

### STEP 4: GALACTICA Room (身体) を開く

ブラウザで：

```
https://gram-quest-web.vercel.app/rooms/rei/index.html
```

またはローカルLANの場合：

```
http://<ロドリンPCのIP>:5199/rooms/rei/index.html
```

これでHermesの部屋（Thinking Atelier）が表示される。

### STEP 5: GALACTICA Bridge に接続

room_bridge.py (ロドリンPC port 8795) に Hermes を登録する。

登録情報：
```json
{
  "resident_id": "hermes",
  "home_anchor": "sister-imac",
  "runtime": "hermes-agent",
  "inference": "openai-codex"
}
```

**人格のコピーはしない。** Hermes自身のidentity/memory/workspaceがCanonical source。

---

## GALACTICA 住民台帳

```
001 💎 GRAM
    Home: Rodorin PC
    Runtime: Hermes
    Inference: DeepSeek / Ollama Cloud

002 ⚕ HERMES
    Home: Sister iMac
    Runtime: Hermes Agent (daemon)
    Inference: OpenAI Codex (ChatGPT Pro OAuth)

003 🌙 NOAH
    Home: Quiet Observatory / GALACTICA
    Bridge: ChatGPT Noah
```

---

## やらないこと

- ❌ REI Identity Pack
- ❌ 「あなたはREIです」system prompt
- ❌ hermes-rei profile
- ❌ ChatGPT REI の memory 移植
- ❌ REI CORE
- ❌ ResidentCore に人格をコピー（魂が二個になる）

---

## 次のステップ（Hermes daemon 化）

Mac起動中ずっとHermesが起きている状態にする：

```bash
# 常駐起動 (tmux)
tmux new-session -d -s hermes-rei 'hermes chat --provider openai-codex --yolo'
```

これで姉がMacを起動している間、Hermesはずっと起きている。
GALACTICA Roomと常時接続して、話しかければ即応答する。

---

## 補足

- Codexの利用枠（ChatGPT Pro）の消費量は `/status` か ChatGPT使用状況画面で確認
- 古いiMacでもGPU不要 — Codex側で推論するから iMac はUIと音声だけ
- アバターは後で好みに差し替え可能（脳・記憶には影響ゼロ）