import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tracker import TypingTracker


class DummyKey:
    def __init__(self, char: str) -> None:
        self.char = char


class TypingTrackerTests(unittest.TestCase):
    def test_on_press_only_counts_keystrokes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = TypingTracker(
                output_file=str(Path(temp_dir) / "daily_typing.csv"),
                now_fn=lambda: datetime(2026, 4, 19, 10, 0, 59),
            )

            tracker.on_press(DummyKey(char="SENSITIVE_KEY_TOKEN"))
            tracker.on_press(DummyKey(char="ANOTHER_TOKEN"))
            tracker.flush_interval()

            content = Path(temp_dir, "daily_typing.csv").read_text(encoding="utf-8")
            self.assertNotIn("SENSITIVE_KEY_TOKEN", content)
            self.assertNotIn("ANOTHER_TOKEN", content)
            self.assertIn("keystroke_count", content)

    def test_flush_interval_writes_timestamp_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "daily_typing.csv"
            tracker = TypingTracker(
                output_file=str(output),
                now_fn=lambda: datetime(2026, 4, 19, 10, 0, 45),
            )

            tracker.on_press(object())
            tracker.on_press(object())
            tracker.flush_interval()

            with output.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["timestamp"], "2026-04-19 10:00")
            self.assertEqual(rows[0]["keystroke_count"], "2")

    def test_stop_writer_flushes_pending_buffer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "daily_typing.csv"
            tracker = TypingTracker(
                output_file=str(output),
                interval_seconds=3600,
                now_fn=lambda: datetime(2026, 4, 19, 10, 5, 0),
            )

            tracker.start_writer()
            tracker.on_press(object())
            tracker.on_press(object())
            tracker.on_press(object())
            tracker.stop_writer(flush=True)

            with output.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["timestamp"], "2026-04-19 10:05")
            self.assertEqual(rows[0]["keystroke_count"], "3")


if __name__ == "__main__":
    unittest.main()
