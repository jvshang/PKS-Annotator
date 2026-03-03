# Real-time Annotation Tool (Version 3)

## Author
**Jiayu Shang**

---

## What's New in Version 3

### Protocol-driven configuration
Labels and actions are no longer hardcoded in the script. They are loaded from `protocol.json` in the same directory. To add, remove, or reorder tasks, edit `protocol.json` — no code changes needed.

Each entry in `protocol.json` has three fields:
- `"id"` — protocol step number shown in the UI (e.g. `"1"`, `"3.1"`)
- `"name"` — task title
- `"actions"` — list of action buttons shown for that task

### Task navigator replaces room buttons
The static room/context buttons are replaced by a sequential task navigator with **◀** and **▶** buttons. Keyboard left/right arrow keys also navigate between tasks. Action buttons update dynamically when the task changes.

### Layout change
The log panel is now displayed side-by-side with the action buttons (right panel), instead of below.

### Output schema updated
`schema_version` in `_meta.json` is now `3`. The meta file stores `tasks` (from `protocol.json`) instead of the old `action_labels` / `room_labels` fields.

---

## Requirements
- Python **3.10 or higher**
- Tkinter (included with standard Python)

```bash
python -c "import tkinter; print('tk ok')"
```

---

## How to Run

```bash
python realtime_annotator.py
```

`protocol.json` must be in the same folder as `realtime_annotator.py`.

---

## Workflow

1. Set session name and output folder.
2. Click **Mark Sync (Clap)** at the synchronisation event (t = 0).
3. Use **◀ ▶** (or arrow keys) to navigate to the current task.
4. Toggle **START / STOP** action buttons in real time.
5. Click **Save Now** when done (or save on window close).

---

## Output Files

For a session named `<session>`:

- `<session>_annotations.csv`
- `<session>_annotations.json`
- `<session>_meta.json`
- `<session>_log.txt`

All timestamps are in seconds, relative to sync t0 if set, otherwise relative to session start.
