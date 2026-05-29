#!/usr/bin/env python3
"""
🛸 グラムちゃん・コズミック・QML・ターミナル・ブリッジ v0.2
PySide6でQMLを起動して、お兄ちゃんの最強ターミナルを実現！
"""
import json
import urllib.request
import threading
import sys

from PySide6.QtCore import QObject, Slot, Signal, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

API_BASE = "http://localhost:9090"


class GramBridge(QObject):
    messageReceived = Signal(str, str)
    commandResult = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_id = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll_messages)
        self._timer.start(3000)

    @Slot(str, str)
    def send_chat(self, agent, message):
        try:
            req = urllib.request.Request(
                f"{API_BASE}/api/messages",
                data=json.dumps({"agent": agent, "message": message}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[Bridge] send_chat error: {e}")

    @Slot(str)
    def exec_command(self, command):
        def worker():
            try:
                req = urllib.request.Request(
                    f"{API_BASE}/api/exec",
                    data=json.dumps({"command": command}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as res:
                    self.commandResult.emit(res.read().decode())
            except Exception as e:
                self.commandResult.emit(json.dumps({"status": "error", "message": str(e)}))
        threading.Thread(target=worker, daemon=True).start()

    @Slot(result=str)
    def get_system_status(self):
        try:
            req = urllib.request.Request(f"{API_BASE}/api/system/status", method="GET")
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.read().decode()
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def poll_messages(self):
        try:
            req = urllib.request.Request(f"{API_BASE}/api/messages", method="GET")
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
                for msg in data:
                    msg_id = msg.get("id", 0)
                    if msg_id > self._last_id:
                        self._last_id = msg_id
                        agent = msg.get("agent", "")
                        message = msg.get("message", "")
                        if "ロドリン" not in agent and "司令官" not in agent:
                            self.messageReceived.emit(agent, message)
        except Exception:
            pass


def main():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    bridge = GramBridge()
    engine.rootContext().setContextProperty("gramBridge", bridge)

    engine.load(QUrl.fromLocalFile("gram_terminal.qml"))

    if not engine.rootObjects():
        print("❌ QML読み込み失敗！gram_terminal.qmlが見つからないよ！")
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
