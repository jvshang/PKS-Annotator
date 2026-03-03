# Real-time Annotation Tool (Stage 1)
# Author: Jiayu Shang
# Implemented for Stage 1 in-situ annotation in the PKS project
# © 2026 Jiayu Shang. Released under the MIT License.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import json
import csv
import os
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

# -----------------------------
# Config: loaded from protocol.json (same directory as this script)
# -----------------------------
# Edit protocol.json to add, remove, or reorder tasks.
# Each task entry:
#   "id"      — protocol number shown in the UI (e.g. "1", "3.1")
#   "name"    — displayed task title
#   "actions" — action buttons shown when this task is active

_PROTOCOL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "protocol.json")

try:
    with open(_PROTOCOL_PATH, encoding="utf-8") as _f:
        TASKS: List[Dict] = json.load(_f)
except FileNotFoundError:
    raise SystemExit(f"ERROR: protocol.json not found.\nExpected at: {_PROTOCOL_PATH}")
except json.JSONDecodeError as _e:
    raise SystemExit(f"ERROR: protocol.json is not valid JSON.\n{_e}")

# Optional keyboard shortcuts (action -> key) — disabled for now, re-enable when ready
# SHORTCUTS = {
#     "Sit-to-stand": "1",
#     "Stand-to-sit": "2",
#     "Turn": "3",
#     "Walk": "4",
#     "Freezing of Gait (FoG)": "5",
# }


@dataclass
class Event:
    context: str             # task label (id + name)
    action: str              # atomic action label
    start_abs: float         # absolute time.time()
    end_abs: float
    start_rel: float         # relative to sync t0 (seconds)
    end_rel: float
    duration: float
    note: str = ""


class RealTimeAnnotatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Real-time Annotation Tool (Stage 1)")

        # Timing
        self.session_start_abs = time.time()
        self.sync_t0_abs: Optional[float] = None

        # Data
        self.events: List[Event] = []
        # active: action_label -> {"context": context, "start_abs": t, "note": ""}
        self.active: Dict[str, Dict] = {}

        # File log buffer (detailed, saved to _log.txt)
        self._file_log: List[str] = []

        # Output
        self.output_dir = os.getcwd()
        self.session_name = "session"

        # Task navigation state
        self.task_index: int = 0
        self._task_announced: bool = False

        self._build_ui()
        # self._bind_shortcuts()  # shortcuts disabled; re-enable when ready

        self._tick()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -----------------------------
    # Current task helpers
    # -----------------------------
    @property
    def current_task(self) -> Dict:
        return TASKS[self.task_index]

    @property
    def current_context(self) -> str:
        t = self.current_task
        return f"{t['id']}. {t['name']}"

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

        # Task navigation row
        task_frame = ttk.LabelFrame(self.root, text="Task", padding=10)
        task_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.prev_btn = ttk.Button(task_frame, text="◀", width=4, command=self.prev_task)
        self.prev_btn.pack(side="left")

        self.task_label_var = tk.StringVar()
        ttk.Label(
            task_frame, textvariable=self.task_label_var,
            font=("Arial", 12, "bold"), anchor="center"
        ).pack(side="left", expand=True, fill="x", padx=10)

        self.next_btn = ttk.Button(task_frame, text="▶", width=4, command=self.next_task)
        self.next_btn.pack(side="left")

        ttk.Button(task_frame, text="Finish Here", command=self.finish_here).pack(side="right", padx=(12, 0))

        # Keyboard arrow keys for task navigation
        self.root.bind("<Left>", lambda e: self._arrow_key_handler("left"))
        self.root.bind("<Right>", lambda e: self._arrow_key_handler("right"))

        self._update_task_ui()

        # Main panels
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        # Action buttons — rebuilt dynamically when task changes
        self.action_frame = ttk.LabelFrame(left, text="Actions (toggle start/stop)", padding=10)
        self.action_frame.pack(fill="both", expand=True)

        # Notes (below actions)
        notes_frame = ttk.LabelFrame(left, text="Note (optional)", padding=10)
        notes_frame.pack(fill="x", pady=(10, 0))

        self.note_entry = ttk.Entry(notes_frame)
        self.note_entry.pack(fill="x")
        self.note_entry.bind("<Return>", self.attach_note)

        hint = "Type a note and press Enter to attach it to the current active event."
        ttk.Label(notes_frame, text=hint).pack(anchor="w", pady=(6, 0))

        self._build_label_buttons(self.action_frame, labels=self.current_task["actions"])

        # Log (right panel)
        log_frame = ttk.LabelFrame(main, text="Log", padding=10)
        log_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.log = tk.Text(log_frame, width=40, wrap="word")
        self.log.pack(fill="both", expand=True)

        self._log_ui("Ready. Mark Sync (Clap) at the beginning.")

        # Footer hint
        footer = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        footer.pack(fill="x")
        ttk.Label(
            footer,
            text="Shortcuts: disabled  |  ◀ / ▶ buttons or ← / → arrow keys to navigate tasks",
            foreground="#444"
        ).pack(anchor="w")

    def _build_label_buttons(self, parent, labels: List[str]):
        for label in labels:
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=4)

            ttk.Label(row, text=label, width=36).pack(side="left")

            btn = ttk.Button(row, text="START", command=lambda l=label: self.toggle_event(l))
            btn.pack(side="left")

            status = ttk.Label(row, text="inactive", width=12)
            status.pack(side="left", padx=10)

            attr_label = label.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
            setattr(self, f"btn_{attr_label}", btn)
            setattr(self, f"status_{attr_label}", status)

    def attach_note(self, event=None):
        text = self.note_entry.get().strip()
        if not text:
            return

        t_abs = self.now_abs()
        t_rel = self.rel_time(t_abs)
        stamped_note = f"[@t={t_rel:.3f}s] {text}"

        if not self.active:
            self._log_ui("Note ignored (no active event)")
            self._log_full(f"NOTE IGNORED (no active event): '{text}'")
            self.note_entry.delete(0, tk.END)
            return

        for info in self.active.values():
            if info["note"]:
                info["note"] += " | " + stamped_note
            else:
                info["note"] = stamped_note

        self._log_ui(f"Note: {text}")
        self._log_full(f"NOTE added: {stamped_note}")
        self.note_entry.delete(0, tk.END)

    def _bind_shortcuts(self):
        # Shortcuts are disabled. Uncomment and re-enable when ready.
        # for label, key in SHORTCUTS.items():
        #     try:
        #         self.root.bind(f"<KeyPress-{key}>", lambda e, l=label: self._shortcut_handler(l))
        #     except Exception:
        #         pass
        pass

    def _shortcut_handler(self, label: str):
        # Shortcuts are disabled. Uncomment when re-enabling.
        # if self.root.focus_get() == self.note_entry:
        #     return
        # if label in self.current_task["actions"]:
        #     self.toggle_event(label)
        pass

    def _arrow_key_handler(self, direction: str):
        if self.root.focus_get() == self.note_entry:
            return
        if direction == "left":
            self.prev_task()
        else:
            self.next_task()

    # -----------------------------
    # Logic
    # -----------------------------
    def now_abs(self) -> float:
        return time.time()

    def rel_time(self, t_abs: float) -> float:
        base = self.sync_t0_abs if self.sync_t0_abs is not None else self.session_start_abs
        return t_abs - base

    def mark_sync(self):
        self.sync_t0_abs = self.now_abs()
        self.sync_var.set(
            f"Sync t0: SET at elapsed {self.rel_time(self.sync_t0_abs):.3f} s (this will show as 0.000s base)"
        )
        self._log_ui("Sync marked  (t = 0)")
        self._log_full("SYNC marked. Relative timestamps now reference this moment (t=0).")

    def prev_task(self):
        if self.task_index > 0:
            self._go_to_task(self.task_index - 1)

    def next_task(self):
        if self.task_index < len(TASKS) - 1:
            self._go_to_task(self.task_index + 1)

    def _go_to_task(self, new_index: int):
        if new_index == self.task_index:
            return

        if self.active:
            for label in list(self.active.keys()):
                self.stop_event(label)
            self._log_full("All active events automatically closed due to task switch.")

        self.task_index = new_index
        self._task_announced = False
        self._update_task_ui()
        self._rebuild_action_buttons()
        self._log_full(f"Task switched to: {self.current_context}")

    def _rebuild_action_buttons(self):
        for widget in self.action_frame.winfo_children():
            widget.destroy()
        self._build_label_buttons(self.action_frame, labels=self.current_task["actions"])

    def _update_task_ui(self):
        t = self.current_task
        self.task_label_var.set(f"{t['id']}. {t['name']}")

        if hasattr(self, "prev_btn"):
            self.prev_btn.state(["disabled"] if self.task_index == 0 else ["!disabled"])
        if hasattr(self, "next_btn"):
            self.next_btn.state(["disabled"] if self.task_index == len(TASKS) - 1 else ["!disabled"])

    def finish_here(self):
        if not self.active:
            return
        for label in list(self.active.keys()):
            self.stop_event(label)
        self._log_full("Finish Here: all events stopped.")

    def toggle_event(self, label: str):
        if label in self.active:
            self.stop_event(label)
        else:
            self.start_event(label)

    def start_event(self, label: str):
        t = self.now_abs()
        note = self.note_entry.get().strip()
        self.active[label] = {
            "context": self.current_context,
            "start_abs": t,
            "note": note
        }

        attr_label = label.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
        try:
            getattr(self, f"btn_{attr_label}").config(text="STOP")
            getattr(self, f"status_{attr_label}").config(text="ACTIVE")
        except Exception:
            pass

        if not self._task_announced:
            self._log_ui(f"→ {self.current_context}")
            self._task_announced = True
        self._log_ui(f"▶  START  {label}")
        self._log_full(f"START ACTION | {label} | context={self.current_context} | t_rel={self.rel_time(t):.3f}s")

    def stop_event(self, label: str):
        if label not in self.active:
            return

        start_info = self.active[label]
        t_end = self.now_abs()
        t_start = start_info["start_abs"]
        note = start_info.get("note", "")

        ev = Event(
            context=start_info["context"],
            action=label,
            start_abs=t_start,
            end_abs=t_end,
            start_rel=self.rel_time(t_start),
            end_rel=self.rel_time(t_end),
            duration=t_end - t_start,
            note=note
        )
        self.events.append(ev)
        del self.active[label]

        attr_label = label.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
        try:
            getattr(self, f"btn_{attr_label}").config(text="START")
            getattr(self, f"status_{attr_label}").config(text="inactive")
        except Exception:
            pass

        self._log_ui(f"■  STOP   {label}  ({ev.duration:.2f}s)")
        self._log_full(
            f"END   ACTION | {label} | context={ev.context} | "
            f"[{ev.start_rel:.3f}, {ev.end_rel:.3f}] (dur={ev.duration:.3f}s) | note='{note}'"
        )

    def _tick(self):
        self.elapsed_var.set(f"Elapsed: {self.now_abs() - self.session_start_abs:.3f} s")
        self.root.after(50, self._tick)

    def _log_ui(self, msg: str):
        """Write a simple human-readable line to the UI log widget only."""
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _log_full(self, msg: str):
        """Write a detailed timestamped line to the file log buffer only."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self._file_log.append(f"[{ts}] {msg}\n")

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
        log_path = os.path.join(self.output_dir, f"{name}_log.txt")
        return csv_path, json_path, meta_path, log_path

    def save_files(self):
        if self.active:
            active_list = ", ".join(self.active.keys())
            if not messagebox.askyesno(
                "Active events running",
                f"These events are still ACTIVE: {active_list}\n\nSave anyway?"
            ):
                return

        csv_path, json_path, meta_path, log_path = self._make_paths()
        os.makedirs(self.output_dir, exist_ok=True)

        # CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "context", "action",
                "start_rel_s", "end_rel_s", "duration_s",
                "start_abs_epoch", "end_abs_epoch",
                "start_datetime", "end_datetime",
                "note"
            ])
            for ev in self.events:
                w.writerow([
                    ev.context, ev.action,
                    f"{ev.start_rel:.6f}", f"{ev.end_rel:.6f}", f"{ev.duration:.6f}",
                    f"{ev.start_abs:.6f}", f"{ev.end_abs:.6f}",
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev.start_abs)),
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev.end_abs)),
                    ev.note
                ])

        # JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([asdict(ev) for ev in self.events], f, ensure_ascii=False, indent=2)

        # Meta
        meta = {
            "session_name": self.session_name,
            "created_local_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_start_abs_epoch": self.session_start_abs,
            "sync_t0_abs_epoch": self.sync_t0_abs,
            "relative_time_base": "sync_t0 if set else session_start",
            "tasks": TASKS,
            "schema_version": 3,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Log
        with open(log_path, "w", encoding="utf-8") as f:
            f.writelines(self._file_log)

        self._log_full(f"SAVED: {csv_path}")
        self._log_full(f"SAVED: {json_path}")
        self._log_full(f"SAVED: {meta_path}")
        self._log_full(f"SAVED: {log_path}")
        self._log_ui("Saved.")
        messagebox.showinfo("Saved", "Annotations saved successfully.")

    def on_close(self):
        if self.events or self.active:
            if messagebox.askyesno("Exit", "Do you want to save before exiting?"):
                self.save_files()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.tk.call('tk', 'scaling', 1.2)
    except Exception:
        pass
    app = RealTimeAnnotatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
