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

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    _rich_available = True
except ImportError:
    _rich_available = False


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
        self._session_count = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._writer_thread: threading.Thread | None = None
        self._start_time = datetime.now()

    def on_press(self, _key: object) -> None:
        with self._lock:
            self._interval_count += 1
            self._session_count += 1

    @property
    def session_count(self) -> int:
        with self._lock:
            return self._session_count

    @property
    def interval_count(self) -> int:
        with self._lock:
            return self._interval_count

    def get_today_total_from_csv(self) -> int:
        """Read today's accumulated keystrokes from the CSV (excluding current session)."""
        if not self.output_file.exists():
            return 0
        today = self._now_fn().strftime("%Y-%m-%d")
        total = 0
        try:
            with self.output_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("timestamp", "").startswith(today):
                        total += int(row.get("keystroke_count", 0))
        except Exception:
            pass
        return total

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


def _build_dashboard(tracker: TypingTracker, today_base: int) -> Panel:
    now = datetime.now()
    today_total = today_base + tracker.session_count
    session = tracker.session_count
    elapsed = now - tracker._start_time
    elapsed_min = elapsed.total_seconds() / 60
    kpm = int(session / elapsed_min) if elapsed_min >= 0.5 else 0

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style="bold cyan", no_wrap=True)
    table.add_column(justify="left")

    table.add_row("📅 今日累計", f"[bold yellow]{today_total:,}[/bold yellow] 次按鍵")
    table.add_row("⌨️  本次 Session", f"[bold green]{session:,}[/bold green] 次按鍵")
    table.add_row("⚡ 目前速率", f"[bold magenta]{kpm}[/bold magenta] 次/分鐘")
    table.add_row("⏱️  已追蹤", f"{int(elapsed.total_seconds() // 60):02d}:{int(elapsed.total_seconds() % 60):02d}")
    table.add_row("🕐 更新時間", now.strftime("%H:%M:%S"))

    return Panel(
        table,
        title="[bold white]⌨  DevTypingTracker[/bold white]",
        subtitle="[dim]Ctrl+C 停止追蹤[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    )


def run_tracker() -> None:
    try:
        from pynput import keyboard
    except ImportError as error:
        raise RuntimeError("Missing dependency: pynput. Please install requirements.txt") from error

    tracker = TypingTracker()
    today_base = tracker.get_today_total_from_csv()
    tracker.start_writer()

    if _rich_available:
        console = Console()
        with Live(
            _build_dashboard(tracker, today_base),
            console=console,
            refresh_per_second=1,
            screen=False,
        ) as live:
            def update_loop() -> None:
                while not tracker._stop_event.is_set():
                    tracker._stop_event.wait(1)
                    live.update(_build_dashboard(tracker, today_base))

            update_thread = threading.Thread(target=update_loop, daemon=True)
            update_thread.start()

            with keyboard.Listener(on_press=tracker.on_press) as listener:
                try:
                    while listener.is_alive():
                        listener.join(timeout=0.5)
                except KeyboardInterrupt:
                    pass
                finally:
                    tracker.stop_writer(flush=True)
    else:
        with keyboard.Listener(on_press=tracker.on_press) as listener:
            try:
                while listener.is_alive():
                    listener.join(timeout=0.5)
            except KeyboardInterrupt:
                pass
            finally:
                tracker.stop_writer(flush=True)


if __name__ == "__main__":
    run_tracker()
