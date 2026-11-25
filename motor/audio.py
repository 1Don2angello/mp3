"""Coordinación de audio online compartida por las interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Callable, Protocol

from motor.download_playlist import resolve_audio_preview


@dataclass(frozen=True)
class AudioStream:
    title: str
    url: str
    headers: dict[str, str]


@dataclass(frozen=True)
class PlaybackResult:
    title: str
    exit_code: int | None
    stopped: bool


class AudioBackend(Protocol):
    def play(
        self,
        stream: AudioStream,
        duration_seconds: int | None,
        stop_event: Event,
        on_output: Callable[[str], None] | None,
    ) -> int | None: ...

    def stop(self) -> None: ...


class OnlineAudioEngine:
    """Resuelve la fuente y delega la salida de sonido al dispositivo."""

    def __init__(self, backend: AudioBackend) -> None:
        self.backend = backend
        self._stop_event = Event()

    def play(
        self,
        url: str,
        *,
        cookies: str | None = None,
        duration_seconds: int | None = None,
        on_start: Callable[[str], None] | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> PlaybackResult:
        if duration_seconds is not None and duration_seconds <= 0:
            raise ValueError("La duracion debe ser mayor que cero.")
        title, stream_url, headers = resolve_audio_preview(url, cookies)
        if self._stop_event.is_set():
            return PlaybackResult(title, None, True)
        stream = AudioStream(title, stream_url, headers)
        if on_start:
            on_start(title)
        code = self.backend.play(stream, duration_seconds, self._stop_event, on_output)
        return PlaybackResult(title, code, self._stop_event.is_set())

    def stop(self) -> None:
        self._stop_event.set()
        self.backend.stop()
