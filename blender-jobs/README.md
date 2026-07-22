# Blender Autonomous Jobs

Genererar 3D-scener i Blender medans du sover.

## Köstruktur

```
blender-jobs/queue/
  ├── pending/    ← jobb som väntar (.md med prompt)
  ├── active/     ← pågående jobb
  ├── done/       ← klara jobb (+ screenshot-länk)
  └── failed/     ← misslyckade jobb (+ felmeddelande)
```

## Kom igång

```bash
# 1. Starta Blender → tryck N → BlenderMCP → Connect
# 2. Seeda första jobben:
python3 blender-jobs/worker.py

# 3. Eller lägg till egna jobb manuellt:
echo "Create a low-poly castle with a dragon" > blender-jobs/queue/pending/min-ide.md

# 4. Kör worker manuellt:
./blender-jobs/run-next.sh
```

## Automatiskt var 30:e minut (macOS)

```bash
# Installera launchd-tjänsten:
cp blender-jobs/com.suparays.blender-worker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.suparays.blender-worker.plist

# Kolla loggar:
tail -f ~/Library/Logs/blender-worker.log

# Stoppa:
launchctl unload ~/Library/LaunchAgents/com.suparays.blender-worker.plist
```

## Galleri

Färdiga scener hamnar i `blender-jobs/gallery.md` med screenshots.

## Seed-ideas

Redigera `blender-jobs/seed-ideas.md` för att påverka vad systemet skapar.
