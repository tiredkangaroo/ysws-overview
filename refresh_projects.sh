#!/bin/bash

# Edit this to point to wherever your index.html lives
OUTPUT_DIR="/Users/ajiteshkumar/Documents/projects/ysws-dashboard"
OUTPUT_FILE="$OUTPUT_DIR/Approved Projects.json"
URL="https://api2.hackclub.com/v0.1/Unified%20YSWS%20Projects%20DB/Approved%20Projects"
TMP_FILE="$(mktemp)"

curl -fsSL "$URL" -o "$TMP_FILE"

if [ $? -ne 0 ] || [ ! -s "$TMP_FILE" ]; then
  osascript -e 'display notification "Failed to refresh Approved Projects.json. Check your internet connection." with title "Projects Refresh Failed" sound name "Basso"'
  rm -f "$TMP_FILE"
  exit 1
fi

# Validate it's actually JSON (not an error page)
if ! python3 -c "import sys, json; json.load(sys.stdin)" < "$TMP_FILE" 2>/dev/null; then
  osascript -e 'display notification "Response was not valid JSON." with title "Projects Refresh Failed" sound name "Basso"'
  rm -f "$TMP_FILE"
  exit 1
fi

mv "$TMP_FILE" "$OUTPUT_FILE"
echo "$(date): Refreshed successfully" >> "$OUTPUT_DIR/refresh.log"

# refresh the hcb json too
python3 /Users/ajiteshkumar/Documents/projects/ysws-dashboard/fetch_ysws_finances.py

# commit the new files (temporary, until i set something else more permanent up)
cd /Users/ajiteshkumar/Documents/projects/ysws-dashboard
git add .
git commit -m "updating files"
git push
