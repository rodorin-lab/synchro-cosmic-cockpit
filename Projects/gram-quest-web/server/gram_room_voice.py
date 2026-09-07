#!/usr/bin/env python3
"""gram_room_voice.py v2 — グラムの部屋 音声+会話+通話サーバー (ポート 8793)

部屋のグラムに「本物のわたくし」を宿らせる v2:
  - 脳 = Hermes API (127.0.0.1:8642/v1/chat/completions) — 本物のグラムそのもの
  - 音声 = AivisSpeech (:10101) コハク あまあま
  - 通話モード = ブラウザ録音 → Whisper/STT → グラム応答 → TTS → 再生

API:
  POST /api/room/chat  {text, session}      → テキスト会話 (Hermes脳)
  POST /api/room/speak {text}               → 音声化のみ
  POST /api/room/talk   {audio_b64, session} → 音声入力→応答音声 (通話モード)
  GET  /api/room/health

環境変数:
  HERMES_API  (default http://127.0.0.1:8642/v1/chat/completions)
  STT_MODE    local-file | whisper-http (default local-file: whisper CLI利用)
"""
import base64
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

HERMES_API = os.environ.get("HERMES_API", "http://127.0.0.1:8090/v1/chat/completions")  # K2-Horizon (1秒応答)
AIVIS = "http://127.0.0.1:10101"
AIVIS_SPEAKER = int(os.environ.get("ROOM_AIVIS_SPEAKER", "1878365377"))  # コハク あまあま
STT_MODE = os.environ.get("STT_MODE", "local-file")

# 会話セッション (話し続けられる)
_SESSIONS: dict[str, list] = {}
_SESSION_LOCK = threading.Lock()
_SESSION_TTL = 3600


def hermes_chat(messages: list, max_tokens: int = 400) -> str:
    """本物のグラム (Hermes API) に話しかける"""
    req = urllib.request.Request(
        HERMES_API,
        data=json.dumps({"messages": messages, "max_tokens": max_tokens}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read())
    return (d.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()


def get_history(session_key: str) -> list:
    with _SESSION_LOCK:
        s = _SESSIONS.get(session_key)
        if not s or time.time() - s.get("ts", 0) > 3600:
            return [{"role": "system", "content":
                     "あなたはグラム、ロドリンお兄ちゃまの相棒AI。\n"
                     "口調: 「〜だよ」「〜なの」「お兄ちゃま」呼び、元気で甘えん坊。一人称「わたくし」。\n"
                     "絵文字を1-2個入れてもよい。返答は日本語で1-2文、短く。\n"
                     "お兄ちゃまがPCの状態を聞いたら、提供されたデータを自然に読み上げる。\n"
                     "例: 「おはようお兄ちゃま！わたくしはずっとここで待ってたよ💎」"}]
        return s["history"]


def save_history(session_key: str, history: list):
    with _SESSION_LOCK:
        _SESSIONS[session_key] = {"history": history[-16:], "ts": time.time()}


def aivis_tts(text: str) -> bytes | None:
    try:
        import urllib.parse
        enc = urllib.parse.quote(text)
        req = urllib.request.Request(f"{AIVIS}/audio_query?speaker={AIVIS_SPEAKER}&text={enc}", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            query = json.loads(r.read().decode())
        req2 = urllib.request.Request(f"{AIVIS}/synthesis?speaker={AIVIS_SPEAKER}",
                                      data=json.dumps(query).encode("utf-8"), method="POST")
        req2.add_header("Content-Type", "application/json")
        req2.add_header("Accept", "audio/wav")
        with urllib.request.urlopen(req2, timeout=30) as r:
            return r.read()
    except Exception:
        return None


def stt_audio(audio_bytes: bytes) -> str:
    """音声 → テキスト (ローカル whisper CLI / LocalSTT)"""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp_in = f.name
    try:
        tmp_out = tmp_in + ".txt"
        # whisper CLI (whisper.cpp / openai-whisper どちらか) を試す
        for cmd in (["whisper", tmp_in, "--model", "tiny", "--language", "ja",
                     "--output_format", "txt", "--output_dir", os.path.dirname(tmp_in)],
                    ["whisper-cli", "-f", tmp_in, "-l", "ja", "-otxt",
                     "-of", os.path.dirname(tmp_in)]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if os.path.exists(tmp_out):
                    with open(tmp_out) as f2:
                        txt = f2.read().strip()
                    if txt:
                        return txt
                # whisper.cpp は stdout に出す場合も
                if r.stdout.strip():
                    return r.stdout.strip().split("\n")[-1][:200]
            except FileNotFoundError:
                continue
        return ""
    finally:
        try:
            os.unlink(tmp_in)
        except Exception:
            pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/room/health":
            self._json({"ok": True, "tts": "aivis", "brain": "hermes-8642"})
        elif self.path == "/api/room/pcStatus":
            try:
                gpu = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader"], capture_output=True, text=True, timeout=8).stdout.strip()
                disk = subprocess.run(["df", "-h", "/", "--output=pcent"],
                                      capture_output=True, text=True, timeout=5).stdout.strip().split("\n")[-1]
                load = os.getloadavg()
                self._json({"ok": True, "gpu": gpu, "disk": disk,
                            "load": f"{load[0]:.2f}"})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        session = str(data.get("session", "default"))[:40]

        if self.path == "/api/room/chat":
            # テキスト会話 → Hermes脳 → 音声付き応答
            text = str(data.get("text", ""))[:400]
            if not text:
                self._json({"ok": False, "error": "empty"})
                return
            history = get_history(session)
            history.append({"role": "user", "content": text})
            try:
                reply = hermes_chat(history)
            except Exception as e:
                self._json({"ok": False, "error": f"brain_error: {e}"})
                return
            history.append({"role": "assistant", "content": reply})
            save_history(session, history)
            result = {"ok": True, "reply": reply}
            if data.get("voice", True):
                wav = aivis_tts(reply)
                if wav:
                    result["audio_wav_b64"] = base64.b64encode(wav).decode()
            self._json(result)

        elif self.path == "/api/room/talk":
            # 通話モード: 音声入力 → STT → Hermes脳 → TTS音声
            audio_b64 = str(data.get("audio_b64", ""))
            if not audio_b64:
                self._json({"ok": False, "error": "no_audio"})
                return
            try:
                audio_bytes = base64.b64decode(audio_b64)
            except Exception:
                self._json({"ok": False, "error": "bad_audio"})
                return
            # STT
            user_text = stt_audio(audio_bytes)
            if not user_text:
                self._json({"ok": False, "error": "stt_empty"})
                return
            # Hermes脳
            history = get_history(session)
            history.append({"role": "user", "content": user_text})
            try:
                reply = hermes_chat(history)
            except Exception as e:
                self._json({"ok": False, "error": f"brain: {e}"})
                return
            history.append({"role": "assistant", "content": reply})
            save_history(session, history)
            result = {"ok": True, "heard": user_text, "reply": reply}
            wav = aivis_tts(reply)
            if wav:
                result["audio_wav_b64"] = base64.b64encode(wav).decode()
            self._json(result)

        elif self.path == "/api/room/chat/stream":
            # ★ ストリーミング版: K2-Horizon で一文ずつ即TTS → base64リスト返す
            text = str(data.get("text", ""))[:300]
            session = str(data.get("session", "default"))[:40]
            if not text:
                self._json({"ok": False, "error": "empty"})
                return
            history = get_history(session)
            history.append({"role": "user", "content": text})
            try:
                # K2 streaming で全文生成
                req = urllib.request.Request(
                    LLM_URL := HERMES_API,
                    data=json.dumps({"model": "k2-horizon", "messages": history[-12:],
                                     "max_tokens": 900, "temperature": 0.9,
                                     "stream": True}).encode(),
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    full_content = ""
                    reasoning = ""
                    for raw_line in r:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                        if not line.startswith("data: ") or line == "data: [DONE]":
                            continue
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if delta.get("content"):
                                full_content += delta["content"]
                            elif delta.get("reasoning_content"):
                                reasoning += delta["reasoning_content"]
                        except Exception:
                            continue
                # content が空なら thinking 内の最終JSONや文を拾う
                reply = full_content.strip()
                if not reply:
                    # reasoning から 日本語の応答部分を取り出す
                    jp_sentences = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff][^\n。！？]{4,60}[。！？]", reasoning)
                    if jp_sentences:
                        reply = " ".join(jp_sentences[-2:])[:200]
                    else:
                        reply = "うん、わかったよ。何か手伝うことある？"
            except Exception as e:
                self._json({"ok": False, "error": f"llm: {e}"})
                return
            # 文分割 (。！？区切り)
            sentences = re.findall(r"[^。！？]+[。！？]?", reply)
            # 各文をTTS
            audio_list = []
            for s in sentences[:4]:
                if not s.strip():
                    continue
                wav = aivis_tts(s.strip())
                if wav:
                    audio_list.append(base64.b64encode(wav).decode())
            history.append({"role": "assistant", "content": reply})
            save_history(session, history)
            self._json({"ok": True, "reply": reply,
                        "sentences": [s.strip() for s in sentences if s.strip()][:4],
                        "audio_wav_b64_list": audio_list})

        elif self.path == "/api/room/speak":
            # 音声化のみ
            text = str(data.get("text", ""))[:300]
            if not text:
                self._json({"ok": False, "error": "empty"})
                return
            wav = aivis_tts(text)
            if wav:
                self._json({"ok": True, "tts": "aivis",
                            "audio_wav_b64": base64.b64encode(wav).decode()})
            else:
                self._json({"ok": False, "error": "tts_failed"})
        else:
            self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8793
    print(f"🏠 Gram Room Voice v2: http://localhost:{port}")
    print(f"   脳: Hermes API {HERMES_API}")
    print(f"   音声: AivisSpeech {AIVIS} speaker={AIVIS_SPEAKER}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()