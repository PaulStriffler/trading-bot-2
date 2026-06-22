#!/usr/bin/env bash
# Mac/Linux launcher for the mock data sync (no real broker connection).
# Double-click in Finder or run from terminal.

cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q pyyaml 2>/dev/null

echo ""
echo "Starting mock live data sync — Ctrl+C to stop."
echo "Open dashboard/index.html in your browser to see it update."
echo ""
python -m bridge.mock_sync
