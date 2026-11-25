"""Interfaz Android que usa el mismo motor de descargas que la app de PC."""

from __future__ import annotations

import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from yt_dlp.postprocessor.ffmpeg import ACODECS

from motor.download_playlist import (
    find_ffmpeg,
    get_playlist_details,
    get_spotify_api_details,
    get_spotify_oembed,
    is_spotify_url,
    main as download_main,
    search_youtube_matches,
    spotify_credentials_available,
)


class SpotisaverMobile(App):
    def build(self) -> BoxLayout:
        self.title = "Spotisaver"
        self.downloads_dir = Path(self.user_data_dir) / "downloads"

        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
        root.add_widget(Label(text="SPOTISAVER", font_size="26sp", bold=True, size_hint_y=None, height=dp(48)))
        root.add_widget(Label(text="Descargas en este teléfono", size_hint_y=None, height=dp(28)))

        self.url = TextInput(hint_text="Pega un enlace de video o playlist", multiline=False, size_hint_y=None, height=dp(50))
        root.add_widget(self.url)

        options = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.kind = Spinner(text="MP3", values=("MP3", "MP4"))
        options.add_widget(self.kind)
        self.preview_button = Button(text="Cargar lista")
        self.preview_button.bind(on_release=self.preview)
        options.add_widget(self.preview_button)
        root.add_widget(options)

        self.summary = Label(
            text="Pega una URL para revisar el contenido.",
            halign="left",
            valign="top",
            text_size=(0, None),
        )
        self.summary.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        root.add_widget(self.summary)

        self.download_button = Button(text="Descargar", size_hint_y=None, height=dp(56))
        self.download_button.bind(on_release=self.download)
        root.add_widget(self.download_button)
        self.status = Label(text="Listo", size_hint_y=None, height=dp(60), halign="center")
        root.add_widget(self.status)
        return root

    def _show(self, message: str, *, busy: bool = False) -> None:
        def update(_dt: float) -> None:
            self.status.text = message
            self.preview_button.disabled = busy
            self.download_button.disabled = busy

        Clock.schedule_once(update)

    def preview(self, _button: Button) -> None:
        url = self.url.text.strip()
        if not url:
            self._show("Pega una URL primero.")
            return
        self._show("Leyendo lista...", busy=True)
        threading.Thread(target=self._preview_worker, args=(url,), daemon=True).start()

    def _preview_worker(self, url: str) -> None:
        try:
            if is_spotify_url(url):
                if spotify_credentials_available():
                    try:
                        title, rows, _thumbnail = get_spotify_api_details(url)
                        query = str(rows[0]["title"]) if rows else title
                    except Exception:
                        title = str(get_spotify_oembed(url).get("title") or "Spotify")
                        query = title
                else:
                    title = str(get_spotify_oembed(url).get("title") or "Spotify")
                    query = title
                matches = search_youtube_matches(f"{query} official audio", limit=5)
                if not matches:
                    raise RuntimeError("No encontré una fuente pública compatible.")
                match = matches[0]

                def show_spotify(_dt: float) -> None:
                    self.url.text = match["url"]
                    self.summary.text = f"{title}\nCoincidencia sugerida: {match['title']}\nRevisa el enlace antes de descargar."

                Clock.schedule_once(show_spotify)
                self._show("Spotify se usó solo para metadatos.")
                return

            title, rows, _thumbnail = get_playlist_details(url)
            names = "\n".join(f"{row['index']}. {row['title']}" for row in rows[:20])
            extra = f"\n... y {len(rows) - 20} más" if len(rows) > 20 else ""
            summary = f"{title}\n{len(rows)} elementos\n{names}{extra}" if rows else f"{title}\nVideo individual"
            Clock.schedule_once(lambda _dt: setattr(self.summary, "text", summary))
            self._show("Lista cargada.")
        except Exception as exc:
            self._show(f"Error al cargar: {exc}")

    def download(self, _button: Button) -> None:
        url = self.url.text.strip()
        if not url:
            self._show("Pega una URL primero.")
            return
        if is_spotify_url(url):
            self._show("Carga el enlace y revisa la coincidencia antes de descargar.")
            return
        kind = self.kind.text.lower()
        if kind == "mp3" and find_ffmpeg() is None:
            self._show("Esta instalación no incluye ffmpeg; no puede convertir a MP3.")
            return
        self._show("Descargando...", busy=True)
        threading.Thread(target=self._download_worker, args=(url, kind), daemon=True).start()

    def _download_worker(self, url: str, kind: str) -> None:
        try:
            if kind == "mp3":
                # python-for-android empaqueta libshine como codificador MP3.
                ACODECS["mp3"] = ("mp3", "libshine", ())
            code = download_main([url, "--kind", kind, "--output", str(self.downloads_dir)])
            if code == 0:
                self._show(f"Listo. Archivos en: {self.downloads_dir}")
            else:
                self._show(f"La descarga terminó con error ({code}).")
        except Exception as exc:
            self._show(f"Error al descargar: {exc}")


def main() -> None:
    SpotisaverMobile().run()


if __name__ == "__main__":
    main()
