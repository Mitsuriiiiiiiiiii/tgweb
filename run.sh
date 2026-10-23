#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null 2>&1 || pkg install -y python

python3 serve.py &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
sleep 1

if command -v am >/dev/null 2>&1; then
  am start -a android.intent.action.VIEW -d "http://127.0.0.1:8080/" >/dev/null 2>&1 || true
else
  termux-open-url "http://127.0.0.1:8080/" || true
fi

echo
echo "== Page ouverte dans le navigateur =="
echo "== 1) tape sur Ouvrir Telegram Web =="
echo "== 2) reviens ici, puis tape sur Recuperer (ou attends) =="
echo
python3 wait.py
