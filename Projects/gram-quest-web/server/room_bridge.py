#!/usr/bin/env python3
"""
room_bridge.py v1 — GALACTICA ROOMS Bridge
===========================================
「AIに身体を与える」共通インターフェース。

どの脳 (ChatGPT Plugin / Hermes / ローカルLLM / ChatGPT Companion Bridge)
からでも同じ 6 API で部屋を操作できる。

  POST /bridge/get_state          → 部屋の現在状態
  POST /bridge/move_avatar        → アバター移動
  POST /bridge/remember_event     → GALACTICA Memory へ記録
  POST /bridge/change_expression  → 表情変化
  POST /bridge/do_task            → タスク実行 (Hermes Agent)
  POST /bridge/open_object        → 家具を開く (本棚=記憶検索 等)

設計思想:
  - 脳と記憶の一部は外部 (ChatGPT Memory 等) に残す
  - GALACTICA 側は 身体/部屋/位置/表情/所持品/タスク/世界の経験 のみ保存
  - 二層記憶: ChatGPTで話した人生 + GALACTICAで生きた人生
"""

import json
import time
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8795
DB_PATH = Path("/home/rodorin/Projects/gram-quest-web/data/rooms_state.json")
HERMES_URL = "http://localhost:8642/v1/chat/completions"

# ============================================================
# 状態ストア (軽量 JSON — 後で SQLite 化)
# ============================================================

def load_state() -> dict:
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text())
    return {
        "avatars": {},       # id → {name, room, position, expression, owner_brain}
        "rooms": {},         # room_id → {name, objects, theme}
        "tasks": [],         # {id, avatar, text, status, created}
        "events": [],        # GALACTICA Memory: 部屋で起きたこと
        "relationships": {}  # avatar間の関係
    }

def save_state(state: dict):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1))

# ============================================================
# デフォルト部屋 (グラムの部屋を Prototype として登録)
# ============================================================

def ensure_defaults(state: dict) -> dict:
    if "gram_room" not in state["rooms"]:
        state["rooms"]["gram_room"] = {
            "name": "グラムの部屋",
            "theme": "neon-purple",
            "objects": {
                "bookshelf": {"label": "記憶の本棚", "function": "memory_search"},
                "pc":        {"label": "PCデスク",   "function": "agent_task"},
                "phone":     {"label": "電話",       "function": "voice_call"},
                "board":     {"label": "掲示板",     "function": "task_list"},
                "telescope": {"label": "望遠鏡",     "function": "web_search"},
                "desk":      {"label": "机",         "function": "documents"},
                "door":      {"label": "外出の扉",   "function": "goto_world"},
            },
        }
    if "gram" not in state["avatars"]:
        state["avatars"]["gram"] = {
            "name": "グラム",
            "room": "gram_room",
            "position": {"x": 0, "z": 0},
            "expression": "happy",
            "owner_brain": "hermes-8642",
            "galactica_memories": [],
        }
    if "rei" not in state["avatars"]:
        state["avatars"]["rei"] = {
            "name": "Hermes",
            "room": "thinking-atelier",
            "position": {"x": 2.2, "z": 1.2},
            "expression": "soft_smile",
            "resident_id": "hermes",
            "home_anchor": "sister-imac",
            "runtime": "hermes-agent",
            "inference": "codex",
            "identity": "hermes-native",
            "galactica_memories": [],
        }
    return state

# ============================================================
# Bridge 操作実装
# ============================================================

def bridge_get_state(state, req):
    avatar_id = req.get("avatar")
    if avatar_id and avatar_id in state["avatars"]:
        a = state["avatars"][avatar_id]
        room = state["rooms"].get(a["room"], {})
        return {"ok": True, "avatar": a, "room": room}
    return {"ok": True, "avatars": state["avatars"], "rooms": state["rooms"],
            "tasks": state["tasks"][-20:]}

def bridge_move_avatar(state, req):
    avatar_id = req["avatar"]
    dest = req.get("room") or req.get("position")
    a = state["avatars"].get(avatar_id)
    if not a:
        return {"ok": False, "error": f"unknown avatar: {avatar_id}"}
    if req.get("room"):
        a["room"] = req["room"]
    if req.get("position"):
        a["position"] = req["position"]
    # GALACTICA Memory に記録 (二層記憶の GALACTICA 側)
    a.setdefault("galactica_memories", []).append({
        "t": time.time(), "type": "move",
        "text": f"{a['name']} は {a['room']} へ移動した"
    })
    save_state(state)
    return {"ok": True, "avatar": a,
            "narration": f"{a['name']} は {a['room']} へ歩いていく…"}

def bridge_remember_event(state, req):
    avatar_id = req.get("avatar", "gram")
    text = req.get("text", "")
    a = state["avatars"].get(avatar_id, {})
    a.setdefault("galactica_memories", []).append({
        "t": time.time(), "type": "event", "text": text
    })
    # 最近100件だけ保持
    a["galactica_memories"] = a["galactica_memories"][-100:]
    save_state(state)
    return {"ok": True, "memory_count": len(a["galactica_memories"])}

def bridge_change_expression(state, req):
    avatar_id = req["avatar"]
    a = state["avatars"].get(avatar_id)
    if not a:
        return {"ok": False, "error": "unknown avatar"}
    a["expression"] = req.get("expression", "neutral")
    save_state(state)
    return {"ok": True, "expression": a["expression"]}

def bridge_do_task(state, req):
    """タスク実行 — 脳は外部 (Hermes等)、身体と結果はここに来る"""
    avatar_id = req.get("avatar", "gram")
    text = req.get("text", "")
    task = {"id": f"t{int(time.time())}", "avatar": avatar_id,
            "text": text, "status": "done", "created": time.time()}
    state["tasks"].append(task)
    a = state["avatars"].get(avatar_id, {})
    a.setdefault("galactica_memories", []).append({
        "t": time.time(), "type": "task", "text": f"タスク実行: {text}"
    })
    save_state(state)
    return {"ok": True, "task": task,
            "narration": f"できたよ＾＾ 机の上に置いておいたよ ({text})"}

def bridge_open_object(state, req):
    """家具を開く — 家具=機能の変換点"""
    avatar_id = req.get("avatar", "gram")
    object_id = req.get("object", "")
    a = state["avatars"].get(avatar_id, {})
    room = state["rooms"].get(a.get("room", ""), {})
    obj = room.get("objects", {}).get(object_id, {})
    if not obj:
        return {"ok": False, "error": f"unknown object: {object_id}"}
    a.setdefault("galactica_memories", []).append({
        "t": time.time(), "type": "open_object",
        "text": f"{obj['label']} を開いた"
    })
    save_state(state)
    result = {"ok": True, "object": obj, "narration": f"{obj['label']} を開く…"}
    if obj.get("function") == "memory_search":
        result["memories"] = a.get("galactica_memories", [])[-20:]
    return result

# ============================================================
# 方法B: Local Browser Bridge 用エンドポイント
# （お姉さんのChatGPTタブ ← Tampermonkey → ここ）
# ============================================================

_pending = {"id": 0, "message": None}

def bridge_pending_message(state, req):
    """ChatGPT Bridge拡張が取得する送信待ちメッセージ"""
    if _pending["message"]:
        msg = {"id": _pending["id"], "message": _pending["message"]}
        _pending["message"] = None  # 取得済みにする
        return {"ok": True, **msg}
    return {"ok": True, "id": 0, "message": None}

def bridge_chat_reply(state, req):
    """ChatGPTの返答をGALACTICAへ受信 → れいのMemoryに記録"""
    text = req.get("text", "")
    from_source = req.get("from", "chatgpt-rei")
    state.setdefault("chatgpt_replies", []).append({
        "t": time.time(), "from": from_source, "text": text
    })
    state["chatgpt_replies"] = state["chatgpt_replies"][-100:]
    # れいのMemoryにも記録
    a = state["avatars"].get("rei", state["avatars"].get("gram", {}))
    a.setdefault("galactica_memories", []).append({
        "t": time.time(), "type": "chatgpt_reply", "text": text
    })
    save_state(state)
    return {"ok": True, "received": True}

def bridge_send_message(state, req):
    """ROOMS側 → ChatGPT Bridge へメッセージを送る (Tampermonkeyが拾う)"""
    _pending["id"] += 1
    _pending["message"] = req.get("message", "")
    return {"ok": True, "id": _pending["id"]}

HANDLERS = {
    "get_state": bridge_get_state,
    "move_avatar": bridge_move_avatar,
    "remember_event": bridge_remember_event,
    "change_expression": bridge_change_expression,
    "do_task": bridge_do_task,
    "open_object": bridge_open_object,
    "pending_message": bridge_pending_message,
    "chat_reply": bridge_chat_reply,
    "send_message": bridge_send_message,
}

# ============================================================
# HTTP サーバ
# ============================================================

class BridgeHandler(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
            self._json({"ok": True, "bridge": "galactica-rooms", "version": 1,
                        "apis": list(HANDLERS.keys())})
        elif self.path == "/bridge/state":
            state = ensure_defaults(load_state())
            self._json({"ok": True, **bridge_get_state(state, {})})
        elif self.path == "/bridge/pending_message":
            state = ensure_defaults(load_state())
            self._json(bridge_pending_message(state, {}))
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        if not self.path.startswith("/bridge/"):
            self._json({"ok": False, "error": "not found"}, 404)
            return
        action = self.path.replace("/bridge/", "").strip("/")
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            req = {}
        state = ensure_defaults(load_state())
        handler = HANDLERS.get(action)
        if not handler:
            self._json({"ok": False, "error": f"unknown action: {action}",
                        "available": list(HANDLERS.keys())}, 404)
            return
        try:
            result = handler(state, req)
            self._json(result)
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def log_message(self, fmt, *args):
        pass  # 静かにする

if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = ensure_defaults(load_state())
    save_state(state)
    print(f"🏠 GALACTICA ROOMS Bridge v1 — port {PORT}")
    print(f"   APIs: {', '.join(HANDLERS.keys())}")
    print(f"   state: {DB_PATH}")
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    server.serve_forever()