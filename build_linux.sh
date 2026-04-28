#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

source .venv/bin/activate

rm -rf build dist ResearchRadar.spec

pyinstaller \
  --name ResearchRadar \
  --onefile \
  --add-data "app.py:." \
  --add-data "main.py:." \
  --add-data "config:config" \
  --add-data "collectors:collectors" \
  --add-data "core:core" \
  launcher.py

echo ""
echo "Build complete:"
echo "dist/ResearchRadar"
