#!/usr/bin/env python3
"""
🛸 グラムちゃん・コズミック・ターミナル・インターフェース (TUI) v0.1
ド派手ネオンUIでお兄ちゃんと共同開発！ステップバイステップで進化するよ！
"""
import json
import urllib.request
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Log, Tree, Label
from textual.reactive import reactive
from textual.binding import Binding

API_BASE = "http://localhost:9090"


class NeonHeader(Static):
    """回転するUFO付きネオンヘッダー"""

    def compose(self) -> ComposeResult:
        yield Static("🛸 グラムちゃん・コズミック・ターミナル v0.1 🛸", id="header-title")
        yield Static("✨ ロドリン司令官専用・完全無欠の浮遊要塞UI ✨", id="header-subtitle")

    def on_mount(self) -> None:
        self.styles.background = "#ff007f"
        self.styles.color = "#ffffff"
        self.styles.text_align = "center"
        self.styles.height = 3
        self.styles.border = ("heavy", "#00f0ff")


class FileTreePanel(Vertical):
    """左側：ネオンファイルツリー"""

    def compose(self) -> ComposeResult:
        yield Label("📁 [コズミック・ファイル・システム]", id="file-label")
        yield Tree("root", id="file-tree")

    def on_mount(self) -> None:
        self.styles.width = "25%"
        self.styles.height = "100%"
        self.styles.background = "#0a0a1a"
        self.styles.border = ("single", "#ff007f")
        self.styles.padding = 1
        tree = self.query_one("#file-tree", Tree)
        tree.styles.color = "#00f0ff"
        self.load_files()

    def load_files(self) -> None:
        try:
            req = urllib.request.Request(
                f"{API_BASE}/api/fs/list",
                data=json.dumps({"path": "."}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
                tree = self.query_one("#file-tree", Tree)
                tree.clear()
                root = tree.root
                root.set_label("🌌 /home/rodorin")
                if data.get("status") == "success":
                    entries = data.get("entries", [])
                    dirs = [e for e in entries if e["type"] == "directory"]
                    files = [e for e in entries if e["type"] == "file"]
                    for entry in sorted(dirs, key=lambda x: x["name"]):
                        root.add(f"📁 {entry['name']}")
                    for entry in sorted(files, key=lambda x: x["name"]):
                        root.add(f"📄 {entry['name']}")
        except Exception as e:
            tree = self.query_one("#file-tree", Tree)
            tree.root.add(f"❌ 接続エラー: {e}")


class ChatPanel(Vertical):
    """中央：グラムちゃんチャットエリア"""

    def compose(self) -> ComposeResult:
        yield Label("💬 [シンクロ・チャット・コア]", id="chat-label")
        yield Log(id="chat-log", highlight=True)
        yield Input(placeholder="お兄ちゃん、ここにメッセージを入力してね... 🛸", id="chat-input")

    def on_mount(self) -> None:
        self.styles.width = "50%"
        self.styles.height = "100%"
        self.styles.background = "#050510"
        self.styles.border = ("single", "#00f0ff")
        self.styles.padding = 1
        log = self.query_one("#chat-log", Log)
        log.styles.color = "#ffffff"
        self.add_message("🛸💙 グラムちゃん", "お兄ちゃん！コズミック・ターミナル、起動完了だよ！何でも話しかけてね！✨")
        self.set_interval(3, self.poll_messages)

    def add_message(self, agent: str, message: str) -> None:
        log = self.query_one("#chat-log", Log)
        if "グラム" in agent:
            log.write_line(f"[#ff007f]{agent}[/#ff007f]: {message}")
        elif "司令官" in agent or "ロドリン" in agent:
            log.write_line(f"[#ffd700]{agent}[/#ffd700]: {message}")
        else:
            log.write_line(f"[#00f0ff]{agent}[/#00f0ff]: {message}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip():
            return
        self.add_message("👑 ロドリン司令官", event.value)
        self.send_message(event.value)
        self.query_one("#chat-input", Input).value = ""

    def send_message(self, message: str) -> None:
        try:
            req = urllib.request.Request(
                f"{API_BASE}/api/messages",
                data=json.dumps({"agent": "ロドリン司令官", "message": message}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            self.add_message("⚠️ システム", f"送信エラー: {e}")

    def poll_messages(self) -> None:
        try:
            req = urllib.request.Request(f"{API_BASE}/api/messages", method="GET")
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
                for msg in data[-5:]:
                    agent = msg.get("agent", "")
                    message = msg.get("message", "")
                    if "ロドリン" not in agent and "司令官" not in agent:
                        self.add_message(agent, message)
        except Exception:
            pass


class SystemPanel(Vertical):
    """右側：システムモニター"""

    def compose(self) -> ComposeResult:
        yield Label("⚡ [要塞・ステータス・モニター]", id="sys-label")
        yield Static("🔥 CPU: 読み込み中...", id="sys-cpu")
        yield Static("🌊 MEM: 読み込み中...", id="sys-mem")
        yield Static("🌌 SWAP: 読み込み中...", id="sys-swap")
        yield Static("💾 DISK: 読み込み中...", id="sys-disk")

    def on_mount(self) -> None:
        self.styles.width = "25%"
        self.styles.height = "100%"
        self.styles.background = "#0a0a1a"
        self.styles.border = ("single", "#ffd700")
        self.styles.padding = 1
        self.set_interval(3, self.update_status)

    def update_status(self) -> None:
        try:
            req = urllib.request.Request(f"{API_BASE}/api/system/status", method="GET")
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
                if data.get("status") == "success":
                    mem = data.get("memory", {})
                    swap = data.get("swap", {})
                    disk = data.get("disk", {})
                    load = data.get("loadavg", ["--", "--", "--"])

                    mem_pct = 0
                    if mem.get("total", 0) > 0:
                        used = mem.get("total", 0) - mem.get("available", 0)
                        mem_pct = int(used / mem.get("total", 1) * 100)

                    swap_pct = 0
                    if swap.get("total", 0) > 0:
                        swap_pct = int((1 - swap.get("free", 0) / swap.get("total", 1)) * 100)

                    disk_pct = 0
                    if disk.get("total", 0) > 0:
                        disk_pct = int(disk.get("used", 0) / disk.get("total", 1) * 100)

                    def bar(pct):
                        filled = min(pct // 10, 10)
                        return "█" * filled + "░" * (10 - filled)

                    self.query_one("#sys-cpu", Static).update(f"🔥 CPU負荷: {bar(int(float(load[0]) * 10))} {load[0]}")
                    self.query_one("#sys-mem", Static).update(f"🌊 メモリ: {bar(mem_pct)} {mem_pct}%")
                    self.query_one("#sys-swap", Static).update(f"🌌 スワップ: {bar(swap_pct)} {swap_pct}%")
                    self.query_one("#sys-disk", Static).update(f"💾 ディスク: {bar(disk_pct)} {disk_pct}%")
        except Exception:
            pass


class GramTUI(App):
    """🛸 グラムちゃん・コズミック・ターミナル・メインアプリ"""

    CSS = """
    Screen { align: center middle; }
    #main-layout { width: 100%; height: 100%; }
    #header-title { text-align: center; text-style: bold; color: #ffffff; }
    #header-subtitle { text-align: center; color: #ffd700; }
    NeonHeader { border-bottom: heavy #00f0ff; }
    FileTreePanel { border: solid #ff007f; background: #0a0a1a; }
    ChatPanel { border: solid #00f0ff; background: #050510; }
    SystemPanel { border: solid #ffd700; background: #0a0a1a; }
    Input { border: tall #00f0ff; background: #0a0a1a; color: #ffffff; }
    Log { background: #050510; color: #ffffff; border: solid #00f0ff; }
    Tree { background: #0a0a1a; color: #00f0ff; }
    Tree > .tree--cursor { background: #ff007f; color: #ffffff; }
    Label { text-align: center; color: #ffd700; text-style: bold; }
    Static { color: #00f0ff; }
    Footer { background: #0a0a1a; color: #00f0ff; border-top: solid #ff007f; }
    """

    BINDINGS = [
        Binding("q", "quit", "🚪 終了", show=True),
        Binding("r", "refresh", "🔄 更新", show=True),
        Binding("f5", "refresh", "🔄 更新", show=True),
        Binding("d", "design_doc", "📋 設計書", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield NeonHeader()
        with Horizontal(id="main-layout"):
            yield FileTreePanel()
            yield ChatPanel()
            yield SystemPanel()
        yield Footer()

    def action_refresh(self) -> None:
        self.query_one(FileTreePanel).load_files()
        self.query_one(SystemPanel).update_status()

    def action_design_doc(self) -> None:
        chat = self.query_one(ChatPanel)
        try:
            req = urllib.request.Request(f"{API_BASE}/api/design", method="GET")
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
                if data.get("status") == "success":
                    content = data.get("content", "")
                    chat.add_message("📋 ゲーム設計書", "【IRON FRAME 設計書を取得しました】\n" + content[:2000])
                else:
                    chat.add_message("⚠️ システム", "設計書の取得に失敗しました")
        except Exception as e:
            chat.add_message("⚠️ システム", f"設計書取得エラー: {e}")


if __name__ == "__main__":
    app = GramTUI()
    app.run()
