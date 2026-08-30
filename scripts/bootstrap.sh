#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
fi
echo "ok: venv ready. dashboard: .venv/bin/python dashboard/app.py"
