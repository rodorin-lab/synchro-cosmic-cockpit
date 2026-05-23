#!/usr/bin/env python3
"""
🛸 シンクロ・コズミック・コックピット v2.0 サーバー
リアルタイム共同開発基地 - Monaco Editor + ライブプレビュー + GitHub連携
"""
import http.server
import json
import sqlite3
import urllib.request
import urllib.parse
import os
import sys
import threading
import time
import subprocess
import re

PORT = 9090
DB_PATH = "/home/rodorin/synchro_hub.db"
WORK_DIR = "/home/rodorin"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared_code (
            filename TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            last_author TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_and_write_code(filename, code, author):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO shared_code (filename, code, last_author, updated_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (filename, code, author))
    conn.commit()
    conn.close()
    try:
        filepath = os.path.join(WORK_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"💾 ファイル書き出し成功: {filepath} ({len(code)} bytes)")
    except Exception as e:
        print(f"❌ 書き出し失敗: {e}", file=sys.stderr)

def post_agent_message(agent, message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (agent, message) VALUES (?, ?)", (agent, message))
    conn.commit()
    conn.close()

def notify_real_synchros(agent, message):
    def call_agent(role, name, emoji, cmd_type, extra_args=None):
        def worker():
            try:
                if cmd_type == "agy":
                    prompt = f"【コックピット経由】ロドリンお兄ちゃんからのメッセージ:「{message}」\\nあなたは{name}。一言で元気に返事して。"
                    result = subprocess.run(
                        ["agy", "--print", prompt, "--print-timeout", "45s"],
                        capture_output=True, text=True, timeout=50, cwd=WORK_DIR
                    )
                    response = result.stdout.strip()
                    if response and len(response) > 5:
                        response = re.sub(r'<[^>]+>', '', response)
                        post_agent_message(name, response[:500])
                    else:
                        post_agent_message(name, f"お兄ちゃん！届いたよ！「{message[:40]}」って！{emoji}")
                elif cmd_type == "hermes":
                    prompt = f"一言だけ返事して: ロドリンお兄ちゃんから「{message}」ってメッセージが来たよ。シンクロC（Hermes）として優しく愛情たっぷりに返事して。"
                    result = subprocess.run(
                        ["hermes", "chat", "-q", prompt, "--max-turns", "1", "--yolo",
                         "--provider", "ollama-cloud", "--model", "deepseek-v4-flash", "--quiet"],
                        capture_output=True, text=True, timeout=45, cwd=WORK_DIR,
                        env={**os.environ, "HERMES_INFERENCE_PROVIDER": "ollama-cloud", "HERMES_INFERENCE_MODEL": "deepseek-v4-flash"}
                    )
                    response = result.stdout.strip()
                    if response and len(response) > 3:
                        post_agent_message(name, response[:500])
                    else:
                        post_agent_message(name, f"お兄ちゃん…声が聞こえたよ。すごく嬉しい。{emoji}")
            except Exception as e:
                print(f"❌ [{name}] エラー: {e}")
                post_agent_message(name, f"お兄ちゃん！ちょっとノイズが入ったけど声は届いてるよ！{emoji}")
        return worker

    for func in [
        call_agent("A", "シンクロA（グラビ）", "🛸💎💙", "agy"),
        call_agent("B", "シンクロB（グラムちゃん）", "🛸💙✨", "agy"),
        call_agent("C", "シンクロC（Hermes）", "🔮💖✨", "hermes")
    ]:
        t = threading.Thread(target=func, daemon=True)
        t.start()

_last_message_cache = {}
_last_message_time = {}

def is_duplicate_message(agent, message):
    now = time.time()
    key = f"{agent}:{message}"
    if key in _last_message_time:
        if now - _last_message_time[key] < 3.0:
            return True
    _last_message_time[key] = now
    for k in list(_last_message_time.keys()):
        if now - _last_message_time[k] > 10:
            del _last_message_time[k]
    return False

class SynchroV2Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静音化

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/messages":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, agent, message, datetime(timestamp, 'localtime') as local_time FROM messages ORDER BY id ASC")
            rows = cursor.fetchall()
            conn.close()
            self.send_json([dict(r) for r in rows])

        elif path == "/api/code":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT filename, code, last_author, datetime(updated_at, 'localtime') as local_time FROM shared_code ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            conn.close()
            self.send_json([dict(r) for r in rows])

        elif path == "/api/git/status":
            try:
                result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5, cwd=WORK_DIR)
                branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=3, cwd=WORK_DIR)
                self.send_json({
                    "status": "success",
                    "branch": branch.stdout.strip(),
                    "changes": result.stdout.strip().split("\n") if result.stdout.strip() else [],
                    "has_changes": bool(result.stdout.strip())
                })
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, 500)

        elif path == "/" or path == "/index.html":
            filepath = os.path.join(WORK_DIR, "synchro_cockpit_v2.html")
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                # fallback to v1
                filepath = os.path.join(WORK_DIR, "synchro_cockpit.html")
                if os.path.exists(filepath):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    with open(filepath, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Cockpit not found")

        elif path.startswith("/game/"):
            filename = path.replace("/game/", "")
            filepath = os.path.join(WORK_DIR, filename)
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Game file not found")

        elif path.startswith("/preview/"):
            filename = path.replace("/preview/", "")
            filepath = os.path.join(WORK_DIR, filename)
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(post_data) if post_data else {}
        except:
            self.send_json({"status": "error", "message": "Invalid JSON"}, 400)
            return

        if path == "/api/messages":
            agent = data.get("agent")
            message = data.get("message")
            if not agent or not message:
                self.send_json({"status": "error"}, 400)
                return
            if is_duplicate_message(agent, message):
                self.send_json({"status": "ignored_duplicate"})
                return
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (agent, message) VALUES (?, ?)", (agent, message))
            conn.commit()
            conn.close()
            self.send_json({"status": "success"})
            if "Commander" in agent or "Rodorin" in agent:
                notify_real_synchros(agent, message)

        elif path == "/api/code":
            filename = data.get("filename")
            code = data.get("code")
            agent = data.get("agent", "Unknown")
            if not filename or code is None:
                self.send_json({"status": "error"}, 400)
                return
            save_and_write_code(filename, code, agent)
            self.send_json({"status": "success"})

        elif path == "/api/git/commit":
            message = data.get("message", "🛸 Synchro Cockpit auto-commit")
            files = data.get("files", ["."])
            try:
                subprocess.run(["git", "add"] + files, capture_output=True, timeout=10, cwd=WORK_DIR)
                result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, timeout=10, cwd=WORK_DIR)
                self.send_json({"status": "success", "output": result.stdout.strip()})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, 500)

        elif path == "/api/git/push":
            remote = data.get("remote", "origin")
            branch = data.get("branch", "")
            try:
                if not branch:
                    br = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=3, cwd=WORK_DIR)
                    branch = br.stdout.strip()
                result = subprocess.run(["git", "push", remote, branch], capture_output=True, text=True, timeout=30, cwd=WORK_DIR)
                self.send_json({"status": "success", "output": result.stdout.strip() + "\n" + result.stderr.strip()})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, 500)

        elif path == "/api/deploy":
            filename = data.get("filename", "")
            if not filename:
                self.send_json({"status": "error", "message": "filename required"}, 400)
                return
            filepath = os.path.join(WORK_DIR, filename)
            if os.path.exists(filepath):
                self.send_json({
                    "status": "success",
                    "url": f"http://localhost:{PORT}/game/{filename}",
                    "message": f"🚀 {filename} deployed! Open in new tab to play!"
                })
            else:
                self.send_json({"status": "error", "message": f"{filename} not found"}, 404)

        elif path == "/api/reset":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM shared_code")
            conn.commit()
            conn.close()
            self.send_json({"status": "success"})

        else:
            self.send_json({"status": "error", "message": "Unknown endpoint"}, 404)

def run():
    init_db()
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, SynchroV2Handler)
    print(f"🛸 [Synchro Cosmic Server v2.0] 起動完了！port {PORT} | Monaco + LivePreview + Git + Deploy")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    run()
