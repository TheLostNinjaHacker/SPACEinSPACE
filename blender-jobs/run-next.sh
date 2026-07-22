#!/bin/bash
# Run the next pending Blender job via opencode
# Usage: ./blender-jobs/run-next.sh
# Designed to be triggered by launchd/cron

cd "$(dirname "$0")/.." || exit 1

# Check if Blender is reachable
python3 -c "
import socket
s = socket.socket()
try:
    s.connect(('localhost', 9876))
    s.close()
    print('BLENDER_OK')
except:
    print('BLENDER_DOWN')
" 2>/dev/null | grep -q BLENDER_OK || {
    echo "Blender MCP not reachable on port 9876"
    echo "Make sure Blender is open with BlenderMCP connected"
    exit 1
}

# Check for pending jobs
PENDING=$(ls blender-jobs/queue/pending/*.md 2>/dev/null | wc -l)
if [ "$PENDING" -eq 0 ]; then
    echo "No pending jobs in blender-jobs/queue/pending/"
    echo "Refilling from seed ideas..."
    python3 blender-jobs/worker.py
    exit 0
fi

echo "Found $PENDING pending job(s)"

# Run the worker
python3 blender-jobs/worker.py 2>&1
echo "---"
echo "Done. Pending left: $(ls blender-jobs/queue/pending/*.md 2>/dev/null | wc -l)"
echo "Gallery: blender-jobs/gallery.md"
