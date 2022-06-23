#!/bin/sh
# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/dmg
# Empty the dmg folder.
rm -r dist/dmg/*
# Copy the app bundle to the dmg folder.
cp -r "dist/USDB Download & Sync.app" dist/dmg
# If the DMG already exists, delete it.
test -f "dist/usdb_dl.dmg" && rm "dist/usdb_dl.dmg"
create-dmg \
  --volname "USDB Download & Sync" \
  --volicon "usdb_dl.icns" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "usdb_dl.icns" 175 120 \
  --hide-extension "USDB Download & Sync.app" \
  --app-drop-link 425 120 \
  --no-internet-enable  \
  "dist/usdb_dl.dmg" \
  "dist/dmg/"