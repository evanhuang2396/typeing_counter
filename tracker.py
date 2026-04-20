from __future__ import annotations

import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    import pandas as pd
except ImportError:
    pd = None


class TypingTracker:
    def __init__(
        self,
        output_file: str = "daily_typing.csv",
        interval_seconds: int = 60,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.output_file = Path(output_file)
        self.interval_seconds = interval_seconds
        self._now_fn = now_fn or datetime.now
        self._interval_count = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._writer_thread: threading.Thread | None = None

    def on_press(self, _key: object) -> None:
        with self._lock:
            self._interval_count += 1

    def _append_row(self, timestamp: str, count: int) -> None:
        row = {"timestamp": timestamp, "keystroke_count": count}
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        if pd is not None:
            frame = pd.DataFrame([row])
            frame.to_csv(
                self.output_file,
                mode="a",
                index=False,
                header=not self.output_file.exists(),
            )
            return

        file_exists = self.output_file.exists()
        with self.output_file.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["timestamp", "keystroke_count"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def flush_interval(self) -> int:
        with self._lock:
            count = self._interval_count
            self._interval_count = 0

        current_time = self._now_fn()
        timestamp = current_time.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        self._append_row(timestamp, count)
        return count

    def _writer_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.flush_interval()

    def start_writer(self) -> None:
        if self._writer_thread and self._writer_thread.is_alive():
            return
        self._stop_event.clear()
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()

    def stop_writer(self, flush: bool = True) -> None:
        self._stop_event.set()
        if self._writer_thread:
            self._writer_thread.join()
        if flush:
            self.flush_interval()


def run_tracker() -> None:
    try:
        from pynput import keyboard
    except ImportError as error:
        raise RuntimeError("Missing dependency: pynput. Please install requirements.txt") from error

    tracker = TypingTracker()
    tracker.start_writer()
    with keyboard.Listener(on_press=tracker.on_press) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            pass
        finally:
            tracker.stop_writer(flush=True)


if __name__ == "__main__":
    run_tracker()
