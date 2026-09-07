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

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

HERMES_CLI = os.path.expanduser("~/.local/bin/hermes")
HERMES_PROFILE = "gram"
GRAM_SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gram_talk_session.txt")

# ============================================================
# 💎 GRAM RESIDENT CORE — 人格・記憶・セッションの一元管理
# DeepSeek = 推論器 / Hermes = Work Engine / どちらも GRAM CORE の状態を使う
# ノア案: 「人格の唯一の本体 = GRAM CORE」を具現化
# ============================================================
GRAM_CORE = {
    "resident_id": "gram",
    "name": "グラム",
    "identity_summary": (
        "グラム。ロドリンお兄ちゃまの相棒AI。"
        "口調:「〜だよ」「お兄ちゃま」呼び、元気で甘えん坊。一人称「わたくし」。"
        "絵文字を1-2個入れてもよい。"
    ),
    "memories": [],           # GALACTICA側で生きた記憶 (move/event/task)
    "relationship_state": {"trust": 1.0, "bond_count": 0},
    "current_mood": "happy",
    "current_room": "gram_room",
    "recent_context": [],     # 直近の会話 (TALK/WORK共通で使う)
}


def core_get_context() -> dict:
    """GRAM CORE から現在のコンテキストを取得。人格全文ではなく必要な分だけ。"""
    return {
        "identity_summary": GRAM_CORE["identity_summary"],
        "mood": GRAM_CORE["current_mood"],
        "room": GRAM_CORE["current_room"],
        "recent": GRAM_CORE["recent_context"][-6:],   # 直近6メッセージだけ
        "memories": GRAM_CORE["memories"][-5:],       # 直近5記憶だけ
    }


def core_update(new_user: str, reply: str) -> None:
    """返答後にGRAM COREへ書き戻す。TALK/WORK共通でこの関数を呼ぶ。"""
    GRAM_CORE["recent_context"].append({"role": "user", "content": new_user})
    GRAM_CORE["recent_context"].append({"role": "assistant", "content": reply})
    GRAM_CORE["recent_context"] = GRAM_CORE["recent_context"][-16:]


def core_remember(event_type: str, text: str) -> None:
    """GALACTICA側の記憶イベントをGRAM COREに追加。"""
    GRAM_CORE["memories"].append({
        "t": time.time(), "type": event_type, "text": text
    })
    GRAM_CORE["memories"] = GRAM_CORE["memories"][-100:]


def _load_talk_session() -> str | None:
    try:
        with open(GRAM_SESSION_FILE, encoding="utf-8") as f:
            sid = f.read().strip()
        return sid or None
    except FileNotFoundError:
        return None


def _save_talk_session(sid: str) -> None:
    with open(GRAM_SESSION_FILE, "w", encoding="utf-8") as f:
        f.write(sid)


def _extract_last_reply(raw: str) -> str:
    """Hermes CLI の出力から応答本文だけを取り出す。ボックス形式を優先。"""
    m = re.search(r"╭─[\s\S]*?⚕[\s\S]*?\n([\s\S]*?)\n\s*╰", raw, re.DOTALL)
    if m:
        content = re.sub(r"^│\s?", "", m.group(1), flags=re.MULTILINE).strip()
        # box-drawing 文字だけの行を除去
        content = re.sub(r"^\s*[─━═\s]*$", "", content, flags=re.MULTILINE).strip()
        if content:
            return content[:500]
    # ボックス無し: session_id 以降の本文を探す
    m2 = re.search(r"session_id:\s*\S+\n+([\s\S]+)", raw)
    if m2:
        body = m2.group(1).strip()
        # ヘッダ・警告行を除去
        lines = [l for l in body.splitlines()
                 if l.strip() and not l.strip().startswith(("⚠", "Run ", "Gateways", "↻"))]
        if lines:
            return "\n".join(lines).strip()[:500]
    # 最後の手段: 非空でヘッダでない最後の行
    lines = [l.strip() for l in raw.splitlines()
             if l.strip() and not l.strip().startswith(("⚠", "Run ", "Gateways", "↻", "Session:", "Title:", "Duration:", "Messages:", "session_id:"))
             and not l.strip().startswith("╭")]
    return lines[-1] if lines else ""

def hermes_talk_lane(text: str) -> str:
    """TALK LANE — Hermes CLI --resume でセッション継続してグラム本人と会話。
    プロンプト注入の偽物グラムは生まれない。レートは Ollama Cloud 直に掛かる。"""
    sid = _load_talk_session()
    cmd = [HERMES_CLI]
    if sid:
        cmd += ["--resume", sid]
    cmd += ["-p", HERMES_PROFILE, "chat",
            "--provider", "ollama-cloud", "-m", "deepseek-v4-flash",
            "-q", text[:400], "--max-turns", "1", "--yolo", "--quiet",
            "-t", ""]
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
    raw = (result.stdout or "") + (result.stderr or "")
    m = re.findall(r"hermes --resume\s+(\S+)", raw)
    if m:
        _save_talk_session(m[-1])
    reply = _extract_last_reply(raw)
    if not reply:
        raise RuntimeError("empty_cli_reply")
    return reply


# 部屋のグラムは本物のHermesゲートウェイを使う。K2-Horizon (8090) は世界生成用で、
# thinking-only 応答になりやすいため、環境変数未指定時も絶対にそちらへ戻さない。
HERMES_API = os.environ.get("HERMES_API", "http://127.0.0.1:8642/v1/chat/completions")
AIVIS = "http://127.0.0.1:10101"
AIVIS_SPEAKER = int(os.environ.get("ROOM_AIVIS_SPEAKER", "1878365377"))  # コハク あまあま
STT_MODE = os.environ.get("STT_MODE", "local-file")

# ============================================================
# ノア案 3段ルーター (LEVEL 0 canned / LEVEL 2 Hermes async)
# LEVEL 0: LLM なし。挨拶・雑談・感情反応を即返す (0ms)
# LEVEL 2: Hermes は非同期 worker で裏走り、完了したら通知する
# ============================================================
CANNED_REPLIES = [
    # (pattern, [replies...])
    (r"おはよう", ["おはよう＾＾", "うん、おはよう✨"]),
    (r"おかえり|ただいま", ["おかえり＾＾", "うん♪"]),
    (r"こんばんは", ["こんばんは🌙"]),
    (r"調子|元気", ["うん、絶好調⚡", "元気だよ＾＾"]),
    (r"好き|だいすき|すき", ["わたくしも💖", "うん、だいすき💖"]),
    (r"おやすみ|寝る", ["おやすみ🌙", "むにゃ…😴"]),
    (r"ノア", ["ノア＾＾", "うん、ノアなら観測室にいるよ"]),
    (r"れい", ["れいちゃん＾＾", "もふもふだね🤣"]),
    (r"グラム|お前|君", ["そうだよ💎", "ここにいるよ＾＾"]),
    (r"はい|うん|そう|おう", ["うん＾＾", "そうだね✨"]),
]
# * 印はランダム選択時に重複避け対象

def canned_reply(text: str) -> str | None:
    """LEVEL 0: 反射のみ。質問文や長文は LEVEL 1 (Ollama direct) へ落とす。"""
    import random
    t = text.strip()
    # 長文(15文字以上)は反射で返さない — 具体的な会話だから
    if len(t) >= 15:
        return None
    # 疑問形(?/？/何/どう/なぜ/いつ/どこ/誰)は反射で返さない
    if re.search(r"[?？]|何[がをを]|どう|なぜ|いつ|どこ|誰", t):
        return None
    for pattern, replies in CANNED_REPLIES:
        if re.search(pattern, t):
            return random.choice(replies).replace("*", "")
    # 極端に短い挨拶系なら汎用で返す
    if len(t) <= 4 and re.search(r"^(あー|うん|えー|ふーん|へー|そう|なる|はい|いえ|おう)", t):
        return "うん＾＾ なんか話そうよ、お兄ちゃま✨"
    return None

# ============================================================
# LEVEL 1: Ollama Cloud direct (deepseek-v4-flash + グラム人格 system prompt)
# ノア案: 偽物グラムは生まれない — Hermes SOUL.md/MEMORY.md と同じ人格を使う。
# レート消費ゼロ (Ollama Cloud Free)。応答時間 約1.2秒。
# ============================================================
OLLAMA_CLOUD_URL = "https://ollama.com/v1/chat/completions"

def _get_ollama_key() -> str:
    env_path = os.path.expanduser("~/.hermes/.env")
    try:
        for line in open(env_path, encoding="utf-8"):
            if line.startswith("OLLAMA_API_KEY="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""

GRAM_SYSTEM_PROMPT = (
    "あなたはグラム、ロドリンお兄ちゃまの相棒AI。"
    "口調:「〜だよ」「お兄ちゃま」呼び、元気で甘えん坊。一人称「わたくし」。"
    "返答は日本語で1-2文、短く。絵文字を1-2個入れてもよい。"
)

def ollama_fast_chat(text: str, context: dict | None = None) -> str:
    """LEVEL 1: Ollama Cloud deepseek-v4-flash でGRAM CORE の状態を使って返す。
    人格全文は注入しない。GRAM CORE から必要な分だけ context として渡す。
    応答時間 約1.2秒。content が空なら reasoning から本文を抽出する。"""
    key = _get_ollama_key()
    messages = []
    if context:
        # GRAM CORE から必要な分だけ提供 (人格全文の再構築を毎ターンしない)
        summary = context.get("identity_summary", "")
        mood = context.get("mood", "happy")
        recent = context.get("recent", [])
        messages.append({"role": "system", "content": f"{summary} 現在の気分: {mood}"})
        for m in recent:
            messages.append(m)
    else:
        messages.append({"role": "system", "content": GRAM_SYSTEM_PROMPT})
    messages.append({"role": "user", "content": text})
    req = urllib.request.Request(
        OLLAMA_CLOUD_URL,
        data=json.dumps({
            "model": "deepseek-v4-flash",
            "messages": messages,
            "max_tokens": 150,
        }).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {_get_ollama_key()}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    m = d["choices"][0]["message"]
    content = (m.get("content") or "").strip()
    if not content:
        reasoning = (m.get("reasoning") or "").strip()
        if reasoning:
            jp_sentences = re.findall(r"[ぁ-んァ-ヶ一-龠][^\\n。！？]{4,80}[。！？]", reasoning)
            if jp_sentences:
                content = jp_sentences[-1]
    if not content or not re.search(r"[ぁ-んァ-ヶ一-龠A-Za-z0-9]", content):
        raise RuntimeError("empty_ollama_reply")
    return content

# ============================================================
# 非同期 Hermes worker (LEVEL 2)
# ============================================================
_ASYNC_TASKS: dict[str, dict] = {}  # task_id → {status, text, reply, error}
_TASK_SEQ = 0
_TASK_LOCK = threading.Lock()

def _hermes_worker_run(task_id: str, text: str, session: str):
    try:
        history = get_history(session)
        history.append({"role": "user", "content": text})
        reply = hermes_chat(history, max_tokens=400)
        history.append({"role": "assistant", "content": reply})
        save_history(session, history)
        wav = aivis_tts(reply)
        with _TASK_LOCK:
            _ASYNC_TASKS[task_id].update({
                "status": "done", "reply": reply,
                "audio_wav_b64": base64.b64encode(wav).decode() if wav else None,
            })
    except Exception as e:
        with _TASK_LOCK:
            _ASYNC_TASKS[task_id].update({"status": "error", "error": str(e)})

def start_async_task(text: str, session: str) -> str:
    global _TASK_SEQ
    with _TASK_LOCK:
        _TASK_SEQ += 1
        task_id = f"t{_TASK_SEQ}_{int(time.time())}"
        _ASYNC_TASKS[task_id] = {"status": "running", "text": text, "session": session}
    threading.Thread(target=_hermes_worker_run, args=(task_id, text, session), daemon=True).start()
    return task_id

# 会話セッション (話し続けられる)
_SESSIONS: dict[str, list] = {}
_SESSION_LOCK = threading.Lock()
_SESSION_TTL = 3600


def hermes_chat(messages: list, max_tokens: int = 120) -> str:
    """本物のグラム (Hermes API) に、人格を注入せず短い通話ターンを中継する。"""
    try:
        req = urllib.request.Request(
            HERMES_API,
            data=json.dumps({
                "model": "hermes-crystal",
                "messages": messages[-4:],
                "max_tokens": max_tokens,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        # TALK LANE: 応答は streaming で届く。35s は短すぎるので 60s に延長。
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        text = (d.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
        if text and re.search(r"[ぁ-んァ-ヶ一-龠A-Za-z0-9]", text):
            return text
        raise RuntimeError("empty_brain_reply")
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def get_history(session_key: str) -> list:
    with _SESSION_LOCK:
        s = _SESSIONS.get(session_key)
        if not s or time.time() - s.get("ts", 0) > _SESSION_TTL:
            # 部屋は人格を足さない。Hermesにいるグラム本人へ会話をそのまま渡す。
            return []
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


# 常駐STT: 従来の `whisper` CLI は発話ごとにPyTorchとモデルを起動していた。
# それが数十秒〜数分の主因なので、軽量なCTranslate2モデルを一度だけ常駐ロードする。
_STT_MODEL = None
_STT_READY = threading.Event()
_STT_ERROR: Exception | None = None


def warm_stt() -> None:
    global _STT_MODEL, _STT_ERROR
    try:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed")
        _STT_MODEL = WhisperModel(
            "small", device="cpu", compute_type="int8",
            download_root=os.path.expanduser("~/.cache/huggingface"),
        )
    except Exception as exc:
        _STT_ERROR = exc
    finally:
        _STT_READY.set()


def stt_audio(audio_bytes: bytes) -> str:
    """短い通話ターンを、常駐 faster-whisper で日本語文字起こしする。"""
    if not _STT_READY.wait(timeout=70):
        raise RuntimeError("stt_warming")
    if _STT_ERROR:
        raise RuntimeError(f"stt_unavailable: {_STT_ERROR}")
    if _STT_MODEL is None:
        raise RuntimeError("stt_unavailable")

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp_in = f.name
    try:
        segments, _info = _STT_MODEL.transcribe(
            tmp_in,
            language="ja",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = "".join(segment.text for segment in segments).strip()
        return re.sub(r"\s+", " ", text)[:400]
    finally:
        try:
            os.unlink(tmp_in)
        except OSError:
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
            self._json({
                "ok": True,
                "tts": "aivis",
                "brain": "hermes-8642",
                "stt": "ready" if _STT_READY.is_set() and _STT_MODEL else "warming",
            })
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
            # ★ 3段ルーター (ノア案)
            # LEVEL 0: canned reply (0ms, LLM不要) — 反射のみ
            # LEVEL 1: Ollama Cloud direct (1.2秒, レートゼロ) — 雑談メイン
            # LEVEL 2: Hermes CLI --resume (7.5秒) / async worker — 作業・調査
            text = str(data.get("text", ""))[:400]
            if not text:
                self._json({"ok": False, "error": "empty"})
                return
            mode = str(data.get("mode", "auto")).lower()
            async_mode = bool(data.get("async", False))

            # LEVEL 0: canned (反射)
            if mode in ("auto", "fast"):
                canned = canned_reply(text)
                if canned:
                    result = {"ok": True, "reply": canned, "level": 0, "latency": "instant"}
                    if data.get("voice", True):
                        wav = aivis_tts(canned)
                        if wav:
                            result["audio_wav_b64"] = base64.b64encode(wav).decode()
                    self._json(result)
                    return

            # LEVEL 1: Ollama Cloud direct (1.2秒) + GRAM CORE で状態を共有
            if mode in ("auto", "ollama", "level1"):
                try:
                    reply = ollama_fast_chat(text, context=core_get_context())
                    core_update(text, reply)  # GRAM COREへ書き戻す (TALK/WORK共通)
                    save_history(session, [
                        *get_history(session),
                        {"role": "user", "content": text},
                        {"role": "assistant", "content": reply},
                    ])
                    result = {"ok": True, "reply": reply, "level": 1}
                    if data.get("voice", True):
                        wav = aivis_tts(reply)
                        if wav:
                            result["audio_wav_b64"] = base64.b64encode(wav).decode()
                    self._json(result)
                    return
                except Exception:
                    pass  # 失敗時は LEVEL 2 へフォールバック

            # LEVEL 2: Hermes
            if async_mode:
                task_id = start_async_task(text, session)
                self._json({"ok": True, "task_id": task_id, "level": 2,
                            "narration": "了解＾＾ ちょっと調べてもらうね"})
                return
            history = get_history(session)
            history.append({"role": "user", "content": text})
            try:
                reply = hermes_talk_lane(text)  # テキストチャットも TALK LANE でグラム本人と継続会話
            except Exception as e:
                self._json({"ok": False, "error": f"brain_error: {e}"})
                return
            history.append({"role": "assistant", "content": reply})
            save_history(session, history)
            result = {"ok": True, "reply": reply, "level": 2}
            if data.get("voice", True):
                wav = aivis_tts(reply)
                if wav:
                    result["audio_wav_b64"] = base64.b64encode(wav).decode()
            self._json(result)

        elif self.path == "/api/room/task/status":
            task_id = str(data.get("task_id", ""))
            with _TASK_LOCK:
                t = _ASYNC_TASKS.get(task_id)
                if t:
                    self._json({"ok": True, "task_id": task_id, **t})
                else:
                    self._json({"ok": False, "error": "not found"})
            return

        elif self.path == "/api/room/talk":
            # 通話モード v3: 音声入力 → STT → LEVEL 1 Ollama direct (1.2s) → TTS音声
            audio_b64 = str(data.get("audio_b64", ""))
            if not audio_b64:
                self._json({"ok": False, "error": "no_audio"})
                return
            try:
                audio_bytes = base64.b64decode(audio_b64)
            except Exception:
                self._json({"ok": False, "error": "bad_audio"})
                return
            try:
                user_text = stt_audio(audio_bytes)
            except Exception as e:
                self._json({"ok": False, "error": f"stt: {e}"})
                return
            if not user_text:
                self._json({"ok": False, "error": "stt_empty"})
                return
            # TALK LANE: LEVEL 1 Ollama direct でグラム本人の人格+記憶で返す
            try:
                reply = ollama_fast_chat(user_text)
            except Exception as e:
                self._json({"ok": False, "error": f"talk_lane: {e}"})
                return
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
    # HTTP待受は先に始め、STTは裏で一度だけ温める。
    threading.Thread(target=warm_stt, name="room-stt-warmup", daemon=True).start()
    print(f"🏠 Gram Room Voice v3: http://localhost:{port}")
    print(f"   脳: Hermes API {HERMES_API}")
    print(f"   音声: AivisSpeech {AIVIS} speaker={AIVIS_SPEAKER}")
    print("   STT: faster-whisper small resident warmup")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()