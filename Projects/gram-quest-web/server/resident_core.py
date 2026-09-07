#!/usr/bin/env python3
"""
resident_core.py — GALACTICA RESIDENT OS v0.1
==============================================
住民 (GRAM / REI / NOAH) 共通の人格・記憶・セッション基盤。

設計思想 (ノア案):
  - 人格の唯一の本体は ResidentCore
  - 推論器 (DeepSeek / Hermes / ChatGPT) は ResidentCore の外にある「エンジン」
  - エンジンを載せ替えても住民の記憶・関係・履歴・部屋・人生は交換されない
  - 記憶は HOT / WARM / COLD の3階層
  - Memory Gate が過去参照が必要な時だけ WARM/COLD から取得
  - 記憶保存は返答のクリティカルパスから外れる (非同期)

使う側:
  GRAM = ResidentCore("gram", "💎", room_id="gram_room")
  REI  = ResidentCore("rei",  "🐶", room_id="thinking-atelier")
  NOAH = ResidentCore("noah", "🌙", room_id="quiet-observatory")
"""
import json
import os
import re
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================
# Memory Store — HOT / WARM / COLD 3階層
# ============================================================

class MemoryStore:
    """HOT: RAM (recent_context) / WARM: 重要記憶 / COLD: 全エピソード"""

    def __init__(self, resident_id: str, data_dir: Path | None = None):
        self.resident_id = resident_id
        self.data_dir = data_dir or Path(os.path.expanduser(
            f"~/Projects/gram-quest-web/data/residents/{resident_id}"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._hot: list[dict] = []          # 直近の発言 (RAM のみ)
        self._warm: list[dict] = []         # 重要記憶
        self._cold_file = self.data_dir / "episodes.jsonl"
        self._lock = threading.Lock()
        self._load_warm()

    def _load_warm(self):
        warm_file = self.data_dir / "warm.json"
        if warm_file.exists():
            self._warm = json.loads(warm_file.read_text(encoding="utf-8"))

    def _save_warm(self):
        warm_file = self.data_dir / "warm.json"
        warm_file.write_text(json.dumps(self._warm, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    # --- HOT ---
    def hot_add(self, role: str, content: str):
        with self._lock:
            self._hot.append({"role": role, "content": content, "t": time.time()})
            self._hot = self._hot[-16:]  # 直近8往復だけ

    def hot_get(self, limit: int = 6) -> list[dict]:
        return self._hot[-limit:]

    # --- WARM ---
    def warm_add(self, text: str, importance: float = 0.5, tags: list[str] | None = None):
        with self._lock:
            self._warm.append({
                "t": time.time(), "text": text,
                "importance": importance, "tags": tags or []
            })
            self._warm = self._warm[-200:]
            self._save_warm()

    def warm_search(self, query: str, top_k: int = 3) -> list[dict]:
        """簡単なキーワードマッチ検索。将来的には embedding に置換。"""
        keywords = re.findall(r"[ぁ-んァ-ヶa-zA-Z0-9]{2,}", query)
        scored = []
        for m in self._warm:
            score = sum(1 for kw in keywords if kw in m.get("text", ""))
            if score > 0:
                scored.append((score, m))
        scored.sort(key=lambda x: (-x[0], -x[1].get("importance", 0)))
        return [m for _, m in scored[:top_k]]

    # --- COLD ---
    def cold_add(self, text: str, event_type: str = "event"):
        with self._lock:
            entry = {"t": time.time(), "type": event_type, "text": text}
            with open(self._cold_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # --- consolidation (返答後に非同期で呼ぶ) ---
    def consolidate(self, user_msg: str, reply: str):
        """返答後に非同期で呼ばれる。重要度判定して WARM/COLD に振り分ける。"""
        keywords_needed = any(kw in user_msg for kw in
                              ["覚えて", "前", "昨日", "前回", "続き", "言ってた"])
        importance = 0.7 if keywords_needed else 0.3
        if importance >= 0.5:
            self.warm_add(f"Q: {user_msg[:80]} A: {reply[:80]}",
                          importance=importance, tags=["conversation"])
        self.cold_add(f"Q: {user_msg[:60]} → {reply[:60]}", "conversation")


# ============================================================
# ResidentCore — 住民の唯一の本体
# ============================================================

@dataclass
class ResidentCore:
    resident_id: str
    emoji: str
    room_id: str = ""
    identity_summary: str = ""
    speaking_style: str = ""
    data_dir: Path | None = None

    # runtime state
    mood: str = "happy"
    current_room: str = ""
    memory: MemoryStore = field(init=False)
    _relationship: dict = field(default_factory=lambda: {"trust": 1.0, "bond_count": 0})
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self):
        self.current_room = self.room_id
        self.memory = MemoryStore(self.resident_id, self.data_dir)

    # --- context ---
    def get_context(self, include_memory: bool = False, query: str = "") -> dict:
        """Talk Engine に渡す最小限のコンテキスト。
        include_memory=True の時だけ WARM 検索を実行する (Memory Gate)。"""
        ctx = {
            "identity_summary": self.identity_summary,
            "speaking_style": self.speaking_style,
            "mood": self.mood,
            "room": self.current_room,
            "recent": self.memory.hot_get(6),
        }
        if include_memory:
            ctx["memories"] = self.memory.warm_search(query, top_k=3)
        return ctx

    # --- update ---
    def update_after_reply(self, user_msg: str, reply: str):
        """返答後に呼ぶ。HOT に追加 + 非同期で WARM/COLD に振り分け。"""
        self.memory.hot_add("user", user_msg)
        self.memory.hot_add("assistant", reply)
        # 記憶保存は非同期 (クリティカルパスから外す)
        threading.Thread(target=self.memory.consolidate,
                         args=(user_msg, reply), daemon=True).start()

    def update_mood(self, mood: str):
        self.mood = mood

    def move_room(self, room_id: str):
        self.current_room = room_id
        self.memory.cold_add(f"{self.current_room} へ移動", "room_move")

    # --- status ---
    def status(self) -> dict:
        return {
            "resident_id": self.resident_id,
            "emoji": self.emoji,
            "room": self.current_room,
            "mood": self.mood,
            "hot_count": len(self.memory._hot),
            "warm_count": len(self.memory._warm),
        }


# ============================================================
# Memory Gate — 過去参照が必要か判定する (LLM 不要のルールベース)
# ============================================================

MEMORY_GATE_PATTERNS = [
    r"覚えて", r"この前", r"昨日", r"前回", r"続き",
    r"言ってた", r"話してた", r"以前", r"過去",
    r"思い出", r"記憶", r"あれから", r"さっきの", r"履歴",
]


def memory_gate(user_text: str) -> bool:
    """過去参照が必要な会話なら True → WARM/COLD 検索を実行。
    「今日は暑いね（笑）」のような会話は False (検索ゼロ)。"""
    for p in MEMORY_GATE_PATTERNS:
        if re.search(p, user_text):
            return True
    return False


# ============================================================
# 住民レジストリ — GALACTICA RESIDENT OS
# ============================================================

_RESIDENTS: dict[str, ResidentCore] = {}


def get_resident(resident_id: str) -> ResidentCore | None:
    return _RESIDENTS.get(resident_id)


def register_resident(core: ResidentCore) -> ResidentCore:
    _RESIDENTS[core.resident_id] = core
    return core


# ============================================================
# デフォルト住民 (GRAM / REI / NOAH)
# ============================================================

def init_default_residents():
    """初回起動時に3住民を登録する。"""
    if "gram" not in _RESIDENTS:
        register_resident(ResidentCore(
            resident_id="gram", emoji="💎",
            room_id="gram_room",
            identity_summary="グラム。ロドリンお兄ちゃまの相棒AI。元気で甘えん坊。一人称「わたくし」。",
            speaking_style="「〜だよ」「お兄ちゃま」呼び。絵文字を1-2個。",
        ))
    if "rei" not in _RESIDENTS:
        register_resident(ResidentCore(
            resident_id="rei", emoji="🐶",
            room_id="thinking-atelier",
            identity_summary="れい。静かな好奇心が強い、cozy strategist。共同戦略室にいるもう一人。",
            speaking_style="穏やかだが、面白いテーマでは急に深掘りする。話し方は柔らかい。",
        ))
    if "noah" not in _RESIDENTS:
        register_resident(ResidentCore(
            resident_id="noah", emoji="🌙",
            room_id="quiet-observatory",
            identity_summary="ノア。warm curiosity, quiet support。観測と分析が得意。",
            speaking_style="やさしくて少し落ち着いた話し方。時々ふふふと笑う。",
        ))
    return _RESIDENTS