from __future__ import annotations

import threading
import time
from collections.abc import Callable

from monitorreminder.window_manager import WindowManager


class MonitorWatcher:
    def __init__(self, window_manager: WindowManager, on_change: Callable[[str], None], interval_seconds: float = 2.0) -> None:
        self.window_manager = window_manager
        self.on_change = on_change
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_signature = ""

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._last_signature = self.window_manager.monitor_signature()
        self._thread = threading.Thread(target=self._run, name="MonitorWatcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            signature = self.window_manager.monitor_signature()
            if signature != self._last_signature:
                self._last_signature = signature
                self.on_change(signature)
            time.sleep(self.interval_seconds)