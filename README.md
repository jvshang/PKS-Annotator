# Real-time Annotation Tool (Stage 1)

## Purpose
This tool is used for real-time in-situ annotation of
- Action-level events
- Activity-level events
during data collection.

Annotations record start/end timestamps and are later aligned
with video and wearable sensor data.

---

## Requirements
- Python 3.10+
- Tkinter (comes with standard Python / conda)

Test:
```bash
python -c "import tkinter; print('tk ok')"

--

## How to run
-python realtime_annotator.py

Workflow (IMPORTANT)
	1.	Set Session name (e.g. P01_TUG_2026-02-02)
	2.	Choose output folder
	3.	Mark Sync (Clap) at the synchronization event
	4.	Use buttons or shortcuts to START / STOP events
	5.	Click Save Now at the end

Output Files
	•	<session>_annotations.csv
	•	<session>_annotations.json
	•	<session>_meta.json

Timestamps are relative to sync time if set.