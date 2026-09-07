#!/usr/bin/env python3
"""
hermes_avatar_bridge.py v1 — 姉さんのiMac用 Hermes Avatar Bridge
=================================================================
Hermesの脳（identity/memory/session）と、アバターの身体（Thinking Atelier）
を繋ぐ薄いブリッジ。人格はHermesだけ。Bridgeは身体制御と通信のみ。

使い方 (姉さんのiMac):
  1. hermes chat --cli --provider openai-codex --yolo を tmux で常駐
  2. python3 hermes_avatar_bridge.py 8844
  3. ブラウザで http://127.0.0.1:5199/rooms/noah/index.html を開く

WebSocket プロトコル:
  ← アバター側からの受信:
     {"type": "user_text", "text": "..."}
     {"type": "call_start"} / {"type": "call_stop"}
  → アバター側への送信:
     {"type": "assistant_final", "text": "..."}
     {"type": "assistant_delta", "text": "..."}  (streaming時)
     {"type": "status", "state": "thinking"|"speaking"|"idle"|"working"}
     {"type": "avatar", "action": "wave", "emotion": "happy"}
"""
import asyncio
import json
import os
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8844
HERMES_WS_PORT = 8844  # WebSocket (簡易実装では HTTP polling で代用)
# 姉さんのiMac上のHermes daemonと通信する設定
# 常駐 hermes chat CLI は pexpect で制御するか、APIサーバを立てる

# ============================================================
# 簡易実装: HTTP polling ベース (最初の実験用)
# 将来: WebSocket + streaming に移行
# ============================================================

_PENDING_MESSAGES: list = []  # ROOMS → ChatGPT へ送るメッセージ
_CHAT_REPLIES: list = []      # ChatGPT → ROOMS へ返す返答
_SEQ = 0


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/bridge/health":
            self._json({
                "ok": True,
                "bridge": "hermes-avatar-bridge",
                "version": 1,
                "hermes_session": _HERMES_SESSION_ID,
            })
        elif self.path == "/bridge/pending_message":
            # ROOMS → ChatGPT拡張へ転送するメッセージを取得
            if _PENDING_MESSAGES:
                msg = _PENDING_MESSAGES.pop(0)
                self._json({"ok": True, "id": msg.get("id"), "message": msg.get("message")})
            else:
                self._json({"ok": True, "id": 0, "message": None})
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")

        if self.path == "/bridge/user_text":
            """アバター → Hermes へメッセージを送る"""
            text = data.get("text", "")
            if text:
                _PENDING_MESSAGES.append({"id": len(_PENDING_MESSAGES), "message": text})
                self._json({"ok": True, "queued": True})
            else:
                self._json({"ok": False, "error": "empty"})

        elif self.path == "/bridge/chat_reply":
            """ChatGPT拡張からの返答を受信 → アバターへ転送"""
            text = data.get("text", "")
            _CHAT_REPLIES.append({"t": time.time(), "text": text})
            self._json({"ok": True, "received": True})

        elif self.path == "/bridge/status":
            """Hermes の状態をアバターへ通知"""
            self._json({"ok": True, "status": data.get("state", "idle")})

        else:
            self._json({"ok": False, "error": "not found"}, 404)


# ============================================================
# Hermes session 管理 (CLI --resume で継続会話)
# ============================================================

_HERMES_SESSION_ID = None  # 初回は None → 新規セッション

def hermes_send(text: str) -> str:
    """Hermes daemon (CLI --resume) にメッセージを送って返事を得る"""
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    global _HERMES_SESSION_ID
    cmd = [os.path.expanduser("~/.local/bin/hermes")]
    # セッション継続
    if _HERMES_SESSION_ID:
        cmd += ["--resume", _HERMES_SESSION_ID]
    cmd += ["chat", "--provider", "ollama-cloud", "-m", "deepseek-v4-flash", "-q", text[:400], "--max-turns", "1", "--yolo"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    raw = (result.stdout or "").replace("\r", "")
    # session ID を保存
    m = re.findall(r"hermes --resume\s+(\S+)", raw)
    if m:
        _HERMES_SESSION_ID = m[-1]
    # 応答本文を抽出
    m2 = re.search(r"╭─[\s\S]*?⚕[\s\S]*?\n([\s\S]*?)\n\s*╰", raw, re.DOTALL)
    if m2:
        content = re.sub(r"^│\s?", "", m2.group(1), flags=re.MULTILINE).strip()
        if content:
            return content
    lines = [l.strip() for l in raw.splitlines()
             if l.strip() and not l.strip().startswith(("Session:", "⚠", "↻", "Title:", "Duration:"))]
    return lines[-1] if lines else ""


# ============================================================
# Room Bridge (ロドリンPC の room_bridge.py と連携)
# ============================================================

ROOMS_BRIDGE_URL = "http://localhost:8795"

def relay_to_rooms(user_text: str, reply: str):
    """Hermes の返答を ROOMS Bridge へ中継 (部屋のUIに表示する用)"""
    try:
        req = urllib.request.Request(
            f"{ROOMS_BRIDGE_URL}/bridge/chat_reply",
            data=json.dumps({"text": reply, "from": "hermes"}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


import urllib.request
import re

class ExtendedHandler(BridgeHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")

        if self.path in ("/bridge/chat", "/api/room/chat"):
            """アバターからのチャット → Hermes → 返答"""
            text = data.get("text", "")
            if not text:
                self._json({"ok": False, "error": "empty"})
                return
            try:
                reply = hermes_send(text)
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
                return
            relay_to_rooms(text, reply)
            self._json({"ok": True, "reply": reply})

        elif self.path == "/bridge/send_message":
            """ROOMS側からのメッセージを受け取り、pending queue に積む"""
            msg = data.get("message", "")
            _PENDING_MESSAGES.append({"id": len(_PENDING_MESSAGES), "message": msg})
            self._json({"ok": True, "id": len(_PENDING_MESSAGES) - 1})

        elif self.path == "/bridge/chat_reply":
            """Tampermonkey等からの返答を受信"""
            text = data.get("text", "")
            _CHAT_REPLIES.append({"t": time.time(), "text": text})
            self._json({"ok": True})
            relay_to_rooms("", text)

        else:
            # 親クラスの POST ハンドラを継承
            super().do_POST()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8844
    print(f"🔌 HERMES AVATAR BRIDGE v1: http://127.0.0.1:{port}")
    print(f"   脳: Hermes Agent (姉さんのiMac, Codex OAuth)")
    print(f"   部屋: Thinking Atelier / NOAH Observatoy")
    print(f"   役割: 身体制御と通信のみ。人格はHermesだけ。")
    server = HTTPServer(("0.0.0.0", port), ExtendedHandler)
    server.serve_forever()