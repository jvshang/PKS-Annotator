# Real-time Annotation Tool

## Versions

| Branch | Description |
|---|---|
| `main` (this) | Version 1 — action-level + activity-level two-panel annotator |
| [`version2`](../../tree/version2) | Version 2 — context/room-aware annotator; replaces activity panel with room buttons |

---

## Author
This tool was implemented by **Jiayu Shang**.

## Purpose
This tool is used for **real-time, in-situ annotation** during data collection.
It supports:

- **Action-level events** (e.g. sit-to-stand, walking, turning)
- **Activity-level events** (e.g. TUG, daily living activities)

The annotator records **start and end timestamps** as events occur.
These timestamps are later aligned with video recordings and wearable
sensor data for further analysis.

This tool is intended for **Stage 1 annotation**.

---

## Current Function

The current version of the real-time annotator provides the following functionality:

- **Real-time annotation of action-level events**  
  Records the start and end times of observable actions (e.g. sit-to-stand, walking, turning).

- **Real-time annotation of activity-level events**  
  Supports higher-level activities (e.g. TUG, daily living activities) that may consist of multiple action-level events.

- **Start / end timestamp recording with duration computation**  
  Automatically records start and end timestamps for each event and computes event duration.

- **Synchronization event marking**  
  Allows marking a synchronization point (e.g. clapping) to establish a common temporal reference for aligning annotations with video and wearable sensor data.

- **Keyboard shortcut–based interaction**  
  Provides keyboard shortcuts to enable fast, low-distraction annotation during experiments.

- **Session-level metadata logging**  
  Stores session information, annotation labels, and synchronization metadata for downstream analysis.

- **Structured data export**  
  Exports annotations and metadata in CSV and JSON formats for post-processing.

### Scope (Stage 1)

This annotator is designed for **Stage 1 coarse, real-time annotation only**.  
Fine-grained kinematic or clinical parameters—such as turning angle, step count,
angular velocity, or balance-related measures—are **not annotated in this stage**
and are obtained through offline analysis or wearable sensor data in later stages.

---

## Requirements
- Python **3.10 or higher**
- Tkinter (included with standard Python distributions and conda)

Verify Tkinter is available:
```bash
python -c "import tkinter; print('tk ok')"
```

---

## Before You Run
Before starting the annotator, make sure the following conditions are met.

### 1. Run locally
The annotator must be run on a **local machine with a graphical desktop**.

- macOS / Linux: Terminal
- Windows: PowerShell or Command Prompt

Do **not** run on a remote server or headless environment.

---

### 2. Check Python version
Confirm Python ≥ 3.10:

```bash
python --version
```

If both `python` and `python3` exist, ensure you are using the one with
Tkinter support.

---

### 3. Navigate to the annotator directory
Change to the folder containing `realtime_annotator.py`:

```bash
cd path/to/annotator
```

Example:
```bash
cd ~/Downloads
```

---

## How to Run
Start the annotator with:

```bash
python realtime_annotator.py
```

A graphical window should appear.

---

## How to Use

### Workflow

1. **Set Session Name**  
   Example: `P01_TUG_2026-02-02`

2. **Choose Output Folder**  
   Recommended: one folder per participant or session.

3. **Mark Sync (Clap)**  
   At the synchronization event (e.g. participant claps), click  
   **Mark Sync (Clap)** to establish the temporal reference (t = 0).

4. **Annotate events**  
   Use GUI buttons or keyboard shortcuts to **START / STOP** action-level
   and activity-level events in real time.

5. **Save annotations**  
   Click **Save Now** at the end of the session.  
   You will also be prompted to save when closing the window.

---

## Output Files
For a session named `<session>`, the following files are generated:

- `<session>_annotations.csv`
- `<session>_annotations.json`
- `<session>_meta.json`

---

## Timestamp Definition
- All timestamps are recorded in **seconds**
- If a sync event is marked, timestamps are **relative to sync time**
- Otherwise, timestamps are **relative to session start**

Absolute timestamps are also stored for cross-device alignment.

---
