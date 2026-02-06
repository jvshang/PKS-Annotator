import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import json
import csv
import os
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

# -----------------------------
# Config: labels (edit as needed)
# -----------------------------
ACTION_LABELS = [
    "Sit-to-stand",
    "Stand-to-sit",
    "Turn",  # turning start/end (duration)
    "Walk",
    "FoG",   # if applicable; can be used as duration too
]

ACTIVITY_LABELS = [
    "TUG",
    "Turning-in-place task",
    "Living room activity",
    "Kitchen activity",
]

# Optional keyboard shortcuts (label -> key)
# You can customize these. Press key to toggle start/stop for that label.
SHORTCUTS = {
    "Sit-to-stand": "1",
    "Stand-to-sit": "2",
    "Turn": "3",
    "Walk": "4",
    "FoG": "5",
    "TUG": "q",
    "Turning-in-place task": "w",
    "Living room activity": "e",
    "Kitchen activity": "r",
}


@dataclass
class Event:
    level: str               # "action" or "activity"
    label: str
    start_abs: float         # absolute time.time()
    end_abs: float
    start_rel: float         # relative to sync t0 (seconds)
    end_rel: float
    duration: float
    note: str = ""


class RealTimeAnnotatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Real-time Annotation Tool (Action/Activity)")

        # Timing
        self.session_start_abs = time.time()
        self.sync_t0_abs: Optional[float] = None

        # Data
        self.events: List[Event] = []
        self.active: Dict[str, Dict] = {}  # label -> {level, start_abs, note}

        # Output
        self.output_dir = os.getcwd()
        self.session_name = "session"

        self._build_ui()
        self._bind_shortcuts()

        self._tick()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -----------------------------
    # UI
    # -----------------------------
    def _build_ui(self):
        # Top controls
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Session name:").pack(side="left")
        self.session_entry = ttk.Entry(top, width=24)
        self.session_entry.insert(0, self.session_name)
        self.session_entry.pack(side="left", padx=(6, 12))

        ttk.Button(top, text="Choose Output Folder", command=self.choose_output_dir).pack(side="left")
        self.out_label = ttk.Label(top, text=f"  {self.output_dir}")
        self.out_label.pack(side="left", padx=8)

        # Timing row
        timing = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        timing.pack(fill="x")

        self.elapsed_var = tk.StringVar(value="Elapsed: 0.000 s")
        self.sync_var = tk.StringVar(value="Sync t0: NOT SET")

        ttk.Label(timing, textvariable=self.elapsed_var, font=("Arial", 12, "bold")).pack(side="left")
        ttk.Label(timing, text="   ").pack(side="left")
        ttk.Label(timing, textvariable=self.sync_var, font=("Arial", 11)).pack(side="left")

        ttk.Button(timing, text="Mark Sync (Clap)", command=self.mark_sync).pack(side="right")
        ttk.Button(timing, text="Save Now", command=self.save_files).pack(side="right", padx=(0, 8))

        # Main panels
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Notes
        notes_frame = ttk.LabelFrame(left, text="Note (optional)", padding=10)
        notes_frame.pack(fill="x", pady=(0, 10))

        self.note_entry = ttk.Entry(notes_frame)
        self.note_entry.pack(fill="x")
        self.note_entry.bind("<Return>", self.attach_note)

        hint = "Hint: Type a note and press Enter. It will be attached to the CURRENT active event with timestamp."
        ttk.Label(notes_frame, text=hint).pack(anchor="w", pady=(6, 0))

        # Action buttons
        action_frame = ttk.LabelFrame(left, text="Action-level (toggle start/stop)", padding=10)
        action_frame.pack(fill="both", expand=True)

        self._build_label_buttons(action_frame, level="action", labels=ACTION_LABELS)

        # Activity buttons
        activity_frame = ttk.LabelFrame(right, text="Activity-level (toggle start/stop)", padding=10)
        activity_frame.pack(fill="both", expand=True)

        self._build_label_buttons(activity_frame, level="activity", labels=ACTIVITY_LABELS)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log = tk.Text(log_frame, height=10, wrap="word")
        self.log.pack(fill="both", expand=True)

        self._log_line("Ready. Mark Sync (Clap) at the beginning for alignment (recommended).")

        # Shortcut help
        shortcut_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        shortcut_frame.pack(fill="x")
        self.shortcut_var = tk.StringVar(value=self._shortcut_help_text())
        ttk.Label(shortcut_frame, textvariable=self.shortcut_var, foreground="#444").pack(anchor="w")

    def _build_label_buttons(self, parent, level: str, labels: List[str]):
        for i, label in enumerate(labels):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=4)

            key = SHORTCUTS.get(label, "")
            key_txt = f"[{key}]" if key else ""
            lbl = ttk.Label(row, text=f"{label} {key_txt}", width=28)
            lbl.pack(side="left")

            btn = ttk.Button(row, text="START", command=lambda l=label, lv=level: self.toggle_event(lv, l))
            btn.pack(side="left")

            status = ttk.Label(row, text="inactive", width=12)
            status.pack(side="left", padx=10)

            # store references
            setattr(self, f"btn_{level}_{label}", btn)
            setattr(self, f"status_{level}_{label}", status)

    def attach_note(self, event=None):
        text = self.note_entry.get().strip()
        if not text:
            return

        t_abs = self.now_abs()
        t_rel = self.rel_time(t_abs)
        stamped_note = f"[@t={t_rel:.3f}s] {text}"

        if not self.active:
            self._log_line(f"NOTE IGNORED (no active event): '{text}'")
            self.note_entry.delete(0, tk.END)
            return

        for info in self.active.values():
            if info["note"]:
                info["note"] += " | " + stamped_note
            else:
                info["note"] = stamped_note

        self._log_line(f"NOTE added: {stamped_note}")
        self.note_entry.delete(0, tk.END)

    def _bind_shortcuts(self):
        # bind all keys in SHORTCUTS
        for label, key in SHORTCUTS.items():
            self.root.bind(f"<KeyPress-{key}>", lambda e, l=label: self.toggle_by_label(l))

    def _shortcut_help_text(self) -> str:
        items = []
        for label, key in SHORTCUTS.items():
            items.append(f"{key}={label}")
        return "Shortcuts: " + ", ".join(items)

    # -----------------------------
    # Logic
    # -----------------------------
    def now_abs(self) -> float:
        return time.time()

    def rel_time(self, t_abs: float) -> float:
        # relative to sync t0 if set, else relative to session start
        base = self.sync_t0_abs if self.sync_t0_abs is not None else self.session_start_abs
        return t_abs - base

    def mark_sync(self):
        self.sync_t0_abs = self.now_abs()
        self.sync_var.set(f"Sync t0: SET at elapsed {self.rel_time(self.sync_t0_abs):.3f} s (this will show as 0.000s base)")
        self._log_line("SYNC marked. Relative timestamps now reference this moment (t=0).")

    def toggle_by_label(self, label: str):
        # decide its level from config
        if label in ACTION_LABELS:
            self.toggle_event("action", label)
        elif label in ACTIVITY_LABELS:
            self.toggle_event("activity", label)
        else:
            self._log_line(f"Unknown label shortcut: {label}")

    def toggle_event(self, level: str, label: str):
        if label in self.active:
            self.stop_event(level, label)
        else:
            self.start_event(level, label)

    def start_event(self, level: str, label: str):
        t = self.now_abs()
        note = self.note_entry.get().strip()
        self.active[label] = {"level": level, "start_abs": t, "note": note}

        self._set_ui_active(level, label, True)
        self._log_line(f"START {level.upper()} | {label} | t_rel={self.rel_time(t):.3f}s | note='{note}'")

        # clear note after attaching to start
        self.note_entry.delete(0, tk.END)

    def stop_event(self, level: str, label: str):
        if label not in self.active:
            return

        start_info = self.active[label]
        t_end = self.now_abs()
        t_start = start_info["start_abs"]
        note = start_info.get("note", "")

        ev = Event(
            level=level,
            label=label,
            start_abs=t_start,
            end_abs=t_end,
            start_rel=self.rel_time(t_start),
            end_rel=self.rel_time(t_end),
            duration=t_end - t_start,
            note=note
        )
        self.events.append(ev)
        del self.active[label]

        self._set_ui_active(level, label, False)
        self._log_line(f"END   {level.upper()} | {label} | [{ev.start_rel:.3f}, {ev.end_rel:.3f}] (dur={ev.duration:.3f}s) | note='{note}'")

    def _set_ui_active(self, level: str, label: str, is_active: bool):
        btn: ttk.Button = getattr(self, f"btn_{level}_{label}")
        status: ttk.Label = getattr(self, f"status_{level}_{label}")

        if is_active:
            btn.config(text="STOP")
            status.config(text="ACTIVE")
        else:
            btn.config(text="START")
            status.config(text="inactive")

    def _tick(self):
        t = self.now_abs()
        base = self.session_start_abs
        elapsed = t - base
        self.elapsed_var.set(f"Elapsed: {elapsed:.3f} s")

        # update active durations in log line? (keep simple)

        self.root.after(50, self._tick)

    def _log_line(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {msg}\n")
        self.log.see(tk.END)

    # -----------------------------
    # Save / Export
    # -----------------------------
    def choose_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir)
        if d:
            self.output_dir = d
            self.out_label.config(text=f"  {self.output_dir}")

    def _make_paths(self):
        name = self.session_entry.get().strip() or "session"
        self.session_name = name
        csv_path = os.path.join(self.output_dir, f"{name}_annotations.csv")
        json_path = os.path.join(self.output_dir, f"{name}_annotations.json")
        meta_path = os.path.join(self.output_dir, f"{name}_meta.json")
        return csv_path, json_path, meta_path

    def save_files(self):
        # warn about active events
        if self.active:
            active_list = ", ".join(self.active.keys())
            if not messagebox.askyesno(
                "Active events running",
                f"These events are still ACTIVE: {active_list}\n\nSave anyway?"
            ):
                return

        csv_path, json_path, meta_path = self._make_paths()
        os.makedirs(self.output_dir, exist_ok=True)

        # CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "level", "label",
                "start_rel_s", "end_rel_s", "duration_s",
                "start_abs_epoch", "end_abs_epoch",
                "note"
            ])
            for ev in self.events:
                w.writerow([
                    ev.level, ev.label,
                    f"{ev.start_rel:.6f}", f"{ev.end_rel:.6f}", f"{ev.duration:.6f}",
                    f"{ev.start_abs:.6f}", f"{ev.end_abs:.6f}",
                    ev.note
                ])

        # JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([asdict(ev) for ev in self.events], f, ensure_ascii=False, indent=2)

        # Meta (sync + session info)
        meta = {
            "session_name": self.session_name,
            "created_local_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_start_abs_epoch": self.session_start_abs,
            "sync_t0_abs_epoch": self.sync_t0_abs,
            "relative_time_base": "sync_t0 if set else session_start",
            "action_labels": ACTION_LABELS,
            "activity_labels": ACTIVITY_LABELS,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self._log_line(f"SAVED: {csv_path}")
        self._log_line(f"SAVED: {json_path}")
        self._log_line(f"SAVED: {meta_path}")
        messagebox.showinfo("Saved", "Annotations saved successfully.")

    def on_close(self):
        if self.events or self.active:
            if messagebox.askyesno("Exit", "Do you want to save before exiting?"):
                self.save_files()
        self.root.destroy()


def main():
    root = tk.Tk()
    # Better scaling on high-DPI screens
    try:
        root.tk.call('tk', 'scaling', 1.2)
    except Exception:
        pass
    app = RealTimeAnnotatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()