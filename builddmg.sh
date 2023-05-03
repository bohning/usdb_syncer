#!/bin/sh
# If the DMG already exists, delete it.
test -f "dist/USDBSyncer.dmg" && rm "dist/USDBSyncer.dmg"
create-dmg \
  --volname "USDB Syncer" \
  --volicon "src/usdb_syncer/gui/resources/appicon_128x128.png" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 128 \
  --text-size 14 \
  --icon "USDBSyncer.app" 175 120 \
  --hide-extension "USDBSyncer.app" \
  --app-drop-link 425 120 \
  --hdiutil-quiet \
  --no-internet-enable  \
  "dist/USDBSyncer.dmg" \
  "dist/USDBSyncer.app"