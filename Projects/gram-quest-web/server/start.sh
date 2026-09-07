#!/bin/bash
# ============================================
# ⚕ HERMES ROOM v3 — ワンクリック起動 (macOS / Linux 共通)
# 使い方: このフォルダで terminal を開いて
#   bash start.sh
# これだけ。ブラウザが自動で開く。
# ============================================
cd "$(dirname "$0")"

echo "⚕ HERMES ROOM v3 起動中..."

# python3 探し (macOS は python3, 無ければ python)
PY=""
for c in python3 python; do
  if command -v "$c" > /dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "❌ python が見つかりません。https://www.python.org/downloads/ から入れるか、"
  echo "   ターミナルで 'xcode-select --install' を試してみてね。"
  read -r -p "Enterで閉じる..."
  exit 1
fi
echo "   python: $PY ($($PY --version 2>&1))"

# 依存チェック: rei-v3 フォルダが必要
if [ ! -f "rei-v3/index.html" ]; then
  echo "❌ rei-v3 フォルダがありません。zipを解凍してフォルダごと置いてね。"
  read -r -p "Enterで閉じる..."
  exit 1
fi

echo "   部屋: v3 Voice (全身アバター・家・🎙音声・☎通話)"
echo "   脳: Hermes (あなたのPCのOllama Cloud設定)"
echo ""
echo " ブラウザが開かない場合は手動で http://127.0.0.1:5199 を開いてね"
echo " 止めるとき: このターミナルで Ctrl+C"
echo ""

# 起動 (2秒後にブラウザ自動オープンは server 側でやる)
exec "$PY" hermes_room_server.py