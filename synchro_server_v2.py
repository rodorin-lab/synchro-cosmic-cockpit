#!/usr/bin/env python3
"""
🛸 Synchro Cosmic Server v2.1 — シェル実行フォールバック(最小・ハードニング版)

v2.1 の位置づけ:
  グラムちゃんとのチャットは今やヘルメスの api_server (127.0.0.1:18642, 認証付き)
  が担う。システム状態はコックピットが /proc を直読みする。よってこのサーバは
  「コックピットからの生シェルコマンド実行フォールバック」だけを提供する最小構成に
  絞った(旧 v2.0 の Monaco プレビュー / DuckDuckGo / git push / SQLite ブリテン
  ボード / notify_real_synchros による hermes chat 起動 などは全て撤去)。

ハードニング:
  - 127.0.0.1 のみにバインド(旧版の '' = 全インターフェース公開を廃止)
  - CORS ヘッダを一切出さない(同一マシンの PySide6/PyQt6 クライアント専用)
  - /api/exec は X-Cockpit-Secret ヘッダの共有シークレット照合を必須化
    (~/.hermes/.env の COCKPIT_SHELL_SECRET と一致しなければ 403)

これは LLM の主経路ではなく、ユーザーが意図的に叩く手動エスケープハッチ。
"""
import hmac
import http.server
import json
import os
import subprocess
import sys

HOST = "127.0.0.1"
PORT = 9090
WORK_DIR = "/home/rodorin"


def _load_env_value(key: str) -> str:
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


_SHELL_SECRET = _load_env_value("COCKPIT_SHELL_SECRET")


class SynchroV2Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # 静かに(標準の stderr スパムを抑制)
        pass

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_secret(self) -> bool:
        """定数時間比較で共有シークレットを照合。"""
        if not _SHELL_SECRET:
            return False
        provided = self.headers.get("X-Cockpit-Secret", "")
        return hmac.compare_digest(provided, _SHELL_SECRET)

    def do_POST(self):
        if self.path == "/api/reach":
            if not self._check_secret():
                self.send_json({"status": "error", "message": "Forbidden (bad or missing X-Cockpit-Secret)"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length)) if length else {}
            except Exception as e:
                self.send_json({"status": "error", "message": f"Bad request: {e}"}, 400)
                return

            reach_type = data.get("type", "web")
            query = data.get("query", "")
            if not query:
                self.send_json({"status": "error", "message": "query is required"}, 400)
                return

            if reach_type == "web":
                command = f"curl -s https://r.jina.ai/{query}"
            elif reach_type == "youtube":
                command = f"yt-dlp --write-auto-sub --skip-download --sub-lang ja,en -o '/tmp/%(title)s.%(ext)s' '{query}' && cat /tmp/*.vtt 2>/dev/null || echo '字幕取得失敗'"
            elif reach_type == "search":
                command = f"curl -s 'https://r.jina.ai/https://www.google.com/search?q={query}'"
            else:
                self.send_json({"status": "error", "message": "Unknown reach type"}, 400)
                return

            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True,
                    timeout=30, cwd=WORK_DIR,
                )
                self.send_json({
                    "status": "success",
                    "content": result.stdout[:4000]
                })
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, 500)
            return

        if self.path != "/api/exec":
            self.send_json({"status": "error", "message": "Unknown endpoint"}, 404)
            return

        if not self._check_secret():
            self.send_json({"status": "error", "message": "Forbidden (bad or missing X-Cockpit-Secret)"}, 403)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length)) if length else {}
        except Exception as e:
            self.send_json({"status": "error", "message": f"Bad request: {e}"}, 400)
            return

        command = data.get("command", "")
        if not command:
            self.send_json({"status": "error", "message": "command is required"}, 400)
            return

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=WORK_DIR,
            )
            self.send_json({
                "status": "success",
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            })
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)}, 500)


def run():
    if not _SHELL_SECRET:
        print("⚠️  COCKPIT_SHELL_SECRET が ~/.hermes/.env に無いため、/api/exec は常に 403 になります。")
    httpd = http.server.HTTPServer((HOST, PORT), SynchroV2Handler)
    print(f"🛸 [Synchro Cosmic Server v2.1] 起動 — {HOST}:{PORT} (shell-exec fallback only, secret-gated)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()
