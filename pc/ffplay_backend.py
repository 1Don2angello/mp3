"""Salida de audio para PC mediante FFplay."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Callable

from motor.audio import AudioStream


class FFplayBackend:
    def __init__(self, ffplay_path: str, working_directory: Path) -> None:
        self.ffplay_path = ffplay_path
        self.working_directory = working_directory
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def play(
        self,
        stream: AudioStream,
        duration_seconds: int | None,
        stop_event: threading.Event,
        on_output: Callable[[str], None] | None = None,
    ) -> int | None:
        cmd = [self.ffplay_path, "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "error", "-nostats"]
        if duration_seconds is not None:
            cmd.extend(["-t", str(duration_seconds)])
        if stream.headers:
            cmd.extend(["-headers", "\r\n".join(f"{key}: {value}" for key, value in stream.headers.items()) + "\r\n"])
        cmd.extend(["-i", stream.url])

        with self._lock:
            if stop_event.is_set():
                return None
            process = subprocess.Popen(
                cmd,
                cwd=str(self.working_directory),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._process = process

        try:
            assert process.stdout is not None
            for line in process.stdout:
                if on_output:
                    on_output(line)
            return process.wait()
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def stop(self) -> None:
        with self._lock:
            process = self._process
            if process and process.poll() is None:
                process.terminate()
