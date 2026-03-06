# Real-time Annotation Tool — Version 2

> For setup, requirements, and basic usage, see the [main branch README](../../blob/main/README.md) (Version 1).

This branch introduces a **room/context-aware** annotation model to replace the two-panel (action + activity) design of Version 1.

---

## What Changed in Version 2

### 1. Context (Room) replaces Activity-level

Version 1 had two separate panels: **Action-level** and **Activity-level**.

Version 2 removes the Activity panel entirely and adds a **Context (Room)** button row at the top:

```
[ Hall ]  [ Living Room ]  [ Kitchen ]  [ TUG ]  [ Turning Task ]  [ Finish Here ]
```

You first select the current room/context, then annotate actions as before.

---

### 2. Context switching auto-closes active events

When you click a different room button, all currently active events are **automatically stopped** before the context switches. This prevents events from spanning across rooms.

A **"Finish Here"** button is also provided to stop all active events without switching context.

---

### 3. Parallel events supported

Multiple action-level events can be active simultaneously (e.g. Walk and FoG at the same time).

---

### 4. Notes captured at event start

In Version 1, notes were appended to the most recent active event after the fact.
In Version 2, the note field content is **captured at event start** (when you press START / shortcut), so the note is stored with the event from the beginning.

Pressing Enter in the note field still attaches a timestamped note to all currently active events.

---

### 5. Data schema changes

The output CSV and JSON now use `context` and `action` instead of `level` and `label`:

| Version 1 columns | Version 2 columns |
|---|---|
| `level`, `label` | `context`, `action` |
| — | `start_datetime`, `end_datetime` (human-readable) |

`meta.json` now includes `"schema_version": 2` and `room_labels` instead of `activity_labels`.

---

### 6. New output file: session log

A `<session>_log.txt` file is now saved alongside the CSV/JSON/meta files, containing the full in-app log with full date-time timestamps.

---

### 7. Minor label change

`FoG` is renamed to `Freezing of Gait (FoG)` for clarity.

---

## Output Files (Version 2)

For a session named `<session>`:

- `<session>_annotations.csv`
- `<session>_annotations.json`
- `<session>_meta.json`
- `<session>_log.txt` *(new in v2)*
