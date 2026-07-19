#!/usr/bin/env python3
"""
🛸 グラムちゃん・コズミック・QML・ターミナル・ブリッジ v0.3
PyQt6でQMLを起動して、グラムちゃんと直接おしゃべり！

v0.3 の変更:
- PySide6 → PyQt6（PySide6 未導入・ディスク逼迫のため、既存の PyQt6 を利用）
- チャットは死んだ 9090 ブリテンボードではなく、ヘルメスの api_server
  (認証付き OpenAI 互換 REST, 127.0.0.1:18642) の永続セッションに直結
- システム状態は /proc を直接読む自己完結方式（9090 サーバに依存しない）
- exec_command は任意で、ハードニング済み 9090 synchro_server_v2 のシェル
  フォールバックにだけ使う（QML の主経路ではない）

システム python (/usr/bin/python3) で起動すること（PyQt6 が ~/.local にある）。
"""
import json
import os
import shutil
import threading
import urllib.request

from PyQt6.QtCore import QObject, pyqtSlot as Slot, pyqtSignal as Signal, QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

# ── ヘルメス api_server（認証付きチャット本線） ───────────────────────────
HERMES_API_BASE = "http://127.0.0.1:18642"
# ── 旧 synchro_server_v2（任意のシェル実行フォールバックのみ） ────────────
SHELL_API_BASE = "http://127.0.0.1:9090"

GRAM_NAME = "🛸💙 グラムちゃん"


def _load_env_value(key: str) -> str:
    """~/.hermes/.env から key=value を読む（gateway と同じ鍵を共有）。"""
    env_path = os.path.expanduser("~/.hermes/.env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


class GramBridge(QObject):
    messageReceived = Signal(str, str)
    commandResult = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._api_key = _load_env_value("API_SERVER_KEY")
        self._shell_secret = _load_env_value("COCKPIT_SHELL_SECRET")
        self._session_id = None
        self._session_lock = threading.Lock()

    # ── ヘルメスセッション管理 ────────────────────────────────────────
    def _ensure_session(self) -> str:
        """永続セッションを一度だけ作り、以降は使い回す（会話の連続性）。"""
        with self._session_lock:
            if self._session_id:
                return self._session_id
            req = urllib.request.Request(
                f"{HERMES_API_BASE}/api/sessions",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read())
            self._session_id = data["session"]["id"]
            return self._session_id

    # ── チャット送信（本線: api_server） ──────────────────────────────
    @Slot(str, str)
    def send_chat(self, agent, message):
        """ユーザー発話をヘルメスに送り、応答を messageReceived で返す。
        ネットワーク往復は GUI スレッドをブロックしないようワーカーで実行。"""
        def worker():
            try:
                if message.startswith("/web "):
                    self._fetch_reach("web", message[5:].strip())
                    return
                elif message.startswith("/youtube "):
                    self._fetch_reach("youtube", message[9:].strip())
                    return
                elif message.startswith("/search "):
                    self._fetch_reach("search", message[8:].strip())
                    return

                session_id = self._ensure_session()
                req = urllib.request.Request(
                    f"{HERMES_API_BASE}/api/sessions/{session_id}/chat",
                    data=json.dumps({"message": message}).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as res:
                    data = json.loads(res.read())
                reply = (data.get("message") or {}).get("content", "") or "……(応答が空だったよ)"
                self.messageReceived.emit(GRAM_NAME, reply)
            except Exception as e:
                self.messageReceived.emit(
                    GRAM_NAME,
                    f"⚠️ ヘルメスに繋がらないみたい… ({e})",
                )
        threading.Thread(target=worker, daemon=True).start()

    # ── インターネットの目（Agent-Reach 経由） ─────────────────────
    def _fetch_reach(self, reach_type, query):
        try:
            req = urllib.request.Request(
                f"{SHELL_API_BASE}/api/reach",
                data=json.dumps({"type": reach_type, "query": query}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "X-Cockpit-Secret": self._shell_secret,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read())
            content = data.get("content", "(内容が空だったよ)")
            self.messageReceived.emit("👁️ カイザーの目", content[:1000])
        except Exception as e:
            self.messageReceived.emit("👁️ カイザーの目", f"⚠️ 取得に失敗したよ… ({e})")

    # ── シェル実行フォールバック（任意・9090 経由） ───────────────────
    @Slot(str)
    def exec_command(self, command):
        """ハードニング済み synchro_server_v2 に生シェルコマンドを投げる。
        LLM の主経路ではなく、手動エスケープハッチ。"""
        def worker():
            try:
                req = urllib.request.Request(
                    f"{SHELL_API_BASE}/api/exec",
                    data=json.dumps({"command": command}).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "X-Cockpit-Secret": self._shell_secret,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as res:
                    self.commandResult.emit(res.read().decode())
            except Exception as e:
                self.commandResult.emit(
                    json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
                )
        threading.Thread(target=worker, daemon=True).start()

    # ── システム状態（/proc を直接読む自己完結方式） ─────────────────
    @Slot(result=str)
    def get_system_status(self):
        try:
            meminfo = {}
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]  # kB
                        meminfo[key] = int(val) * 1024  # bytes

            with open("/proc/loadavg", encoding="utf-8") as f:
                load = f.read().split()[:3]

            total, used, _free = shutil.disk_usage("/home/rodorin")

            return json.dumps({
                "status": "success",
                "memory": {
                    "total": meminfo.get("MemTotal", 0),
                    "available": meminfo.get("MemAvailable", 0),
                },
                "swap": {
                    "total": meminfo.get("SwapTotal", 0),
                    "free": meminfo.get("SwapFree", 0),
                },
                "disk": {"total": total, "used": used},
                "loadavg": load,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def main():
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()

    bridge = GramBridge()
    engine.rootContext().setContextProperty("gramBridge", bridge)

    qml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gram_terminal.qml")
    engine.load(QUrl.fromLocalFile(qml_path))

    if not engine.rootObjects():
        print("❌ QML読み込み失敗！gram_terminal.qmlが見つからないよ！")
        raise SystemExit(-1)

    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
