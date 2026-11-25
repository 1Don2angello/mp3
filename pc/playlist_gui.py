from __future__ import annotations

import hashlib
import os
import queue
import re
import ssl
import subprocess
import sys
import tempfile
import threading
from urllib.request import Request, urlopen
from pathlib import Path
from tkinter import END, StringVar, Tk, filedialog, messagebox
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk
import certifi

SOURCE_ROOT = Path(__file__).resolve().parent.parent
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from motor.download_playlist import (
    find_ffmpeg,
    get_playlist_details,
    get_playlist_table,
    get_spotify_api_details,
    get_spotify_oembed,
    is_spotify_url,
    search_youtube_matches,
    spotify_credentials_available,
    main as download_main,
)


PROJECT_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else SOURCE_ROOT


class PlaylistDownloaderApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Spotisaver - Playlist Downloader")
        self.root.geometry("980x760")
        self.root.minsize(760, 560)
        self.root.configure(bg="#f4f4f5")

        self.url = StringVar()
        self.kind = StringVar(value="mp3")
        self.output = StringVar(value=str(PROJECT_ROOT / "downloads"))
        self.cookies = StringVar(value="")
        self.audio_quality = StringVar(value="192")
        self.video_quality = StringVar(value="1080")
        self.limit = StringVar(value="")
        self.block_size = StringVar(value="50")
        self.status = StringVar(value="Listo")
        self.playlist_title = StringVar(value="Sin playlist cargada")
        self.playlist_summary = StringVar(value="Pega una URL y carga la lista para revisar contenido.")
        self.theme_mode = StringVar(value="light")
        self.show_advanced = False
        self.process: subprocess.Popen[str] | None = None
        self.messages: queue.Queue[object] = queue.Queue()
        self.thumbnail_image: ImageTk.PhotoImage | None = None
        self.cover_label: tk.Label | None = None

        self.colors = self._theme_colors(self.theme_mode.get())
        self.fonts = self._select_fonts()

        self._configure_styles()
        self._build_ui()
        self._sync_quality_controls()
        self._check_ffmpeg()
        self.root.after(150, self._drain_messages)

    def _select_fonts(self) -> dict[str, str]:
        available = set(tkfont.families(self.root))

        def pick(*families: str) -> str:
            for family in families:
                if family in available:
                    return family
            return families[-1]

        return {
            "display": pick("Segoe UI Variable Display", "Segoe UI Black", "Arial"),
            "ui": pick("Segoe UI Variable Text", "Segoe UI", "Arial"),
            "mono": pick("Cascadia Mono", "Consolas", "Courier New"),
        }

    def _font(self, role: str = "ui", size: int = 10, weight: str = "normal") -> tuple[str, int, str]:
        return (self.fonts.get(role, self.fonts["ui"]), size, weight)

    def _short_text(self, value: str, limit: int = 62) -> str:
        value = " ".join((value or "").split())
        if len(value) <= limit:
            return value
        return f"{value[: limit - 3].rstrip()}..."

    def _theme_colors(self, mode: str) -> dict[str, str]:
        if mode == "dark":
            return {
                "bg": "#090909",
                "bg2": "#1a0d0f",
                "card": "#181818",
                "card_dark": "#050505",
                "text": "#ffffff",
                "text_on_dark": "#ffffff",
                "muted": "#cfcfcf",
                "accent": "#ff2f3a",
                "accent_dark": "#ff6b74",
                "success": "#16a34a",
                "success_hover": "#22c55e",
                "danger": "#dc2626",
                "danger_hover": "#ef4444",
                "warning": "#2a1114",
                "button": "#e11d2e",
                "button_hover": "#ff3446",
                "secondary": "#2f2f2f",
                "stop": "#555555",
                "field": "#242424",
                "border": "#3b3b3b",
                "log": "#0f0f0f",
                "disabled": "#1a1a1a",
                "disabled_text": "#777777",
                "scrollbar": "#202020",
                "scrollbar_trough": "#080808",
            }

        return {
            "bg": "#f4f4f5",
            "bg2": "#ffffff",
            "card": "#ffffff",
            "card_dark": "#111111",
            "text": "#121212",
            "text_on_dark": "#ffffff",
            "muted": "#5e5e66",
            "accent": "#e50914",
            "accent_dark": "#b80710",
            "success": "#16a34a",
            "success_hover": "#15803d",
            "danger": "#dc2626",
            "danger_hover": "#b91c1c",
            "warning": "#fff1f2",
            "button": "#e50914",
            "button_hover": "#b80710",
            "secondary": "#111111",
            "stop": "#6b7280",
            "field": "#f1f1f3",
            "border": "#dedee3",
            "log": "#fafafa",
            "disabled": "#e4e4e7",
            "disabled_text": "#8a8a91",
            "scrollbar": "#d4d4d8",
            "scrollbar_trough": "#f4f4f5",
        }

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TCombobox",
            fieldbackground=self.colors["field"],
            background=self.colors["field"],
            foreground=self.colors["text"],
            arrowcolor=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["field"],
            darkcolor=self.colors["field"],
            padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["field"]), ("disabled", self.colors["disabled"])],
            foreground=[("readonly", self.colors["text"]), ("disabled", self.colors["disabled_text"])],
            background=[("readonly", self.colors["field"]), ("disabled", self.colors["disabled"])],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=self.colors["scrollbar"],
            troughcolor=self.colors["scrollbar_trough"],
            bordercolor=self.colors["scrollbar_trough"],
            arrowcolor=self.colors["text"],
        )

    def _build_ui(self) -> None:
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._draw_background)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.shell = tk.Frame(self.canvas, bg=self.colors["bg"])
        self.window_id = self.canvas.create_window(0, 0, window=self.shell, anchor="nw")
        self.shell.bind("<Configure>", self._resize_shell)

        self.shell.columnconfigure(0, weight=1)

        tk.Label(
            self.shell,
            text="SPOTISAVER",
            fg=self.colors["accent"],
            bg=self.colors["bg"],
            font=self._font("display", 31, "bold"),
        ).grid(row=0, column=0, pady=(16, 0))
        self.theme_button = self._button(self.shell, self._theme_button_text(), self._toggle_theme, bg=self.colors["secondary"])
        self.theme_button.grid(row=0, column=0, sticky="ne", padx=44, pady=(18, 0))
        tk.Label(
            self.shell,
            text="Descargador de playlists y videos",
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            font=self._font("ui", 12, "bold"),
        ).grid(row=1, column=0, pady=(2, 14))

        self._build_search_card()
        self._build_preview_card()
        self._build_controls_card()
        self._build_log_card()
        self._build_footer()

    def _draw_background(self, event: tk.Event) -> None:
        width = max(event.width, 1)
        height = max(event.height, 1)
        self.canvas.delete("gradient")
        start = self._hex_to_rgb(self.colors["bg"])
        end = self._hex_to_rgb(self.colors["bg2"])
        for y in range(height):
            ratio = y / height
            red = int(start[0] + (end[0] - start[0]) * ratio)
            green = int(start[1] + (end[1] - start[1]) * ratio)
            blue = int(start[2] + (end[2] - start[2]) * ratio)
            self.canvas.create_line(0, y, width, y, fill=f"#{red:02x}{green:02x}{blue:02x}", tags="gradient")
        self.canvas.tag_lower("gradient")
        self.canvas.itemconfigure(self.window_id, width=width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_shell(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)

    def _theme_button_text(self) -> str:
        return "Modo claro" if self.theme_mode.get() == "dark" else "Modo oscuro"

    def _toggle_theme(self) -> None:
        log_text = ""
        if hasattr(self, "log"):
            log_text = self.log.get("1.0", END)

        self.theme_mode.set("dark" if self.theme_mode.get() == "light" else "light")
        self.colors = self._theme_colors(self.theme_mode.get())
        self.root.configure(bg=self.colors["bg"])
        self._configure_styles()

        if hasattr(self, "canvas"):
            self.canvas.destroy()
        if hasattr(self, "scrollbar"):
            self.scrollbar.destroy()

        self._build_ui()
        self._sync_quality_controls()
        if log_text.strip():
            self.log.insert(END, log_text)
            self.log.see(END)

    def _toggle_advanced(self) -> None:
        self.show_advanced = not self.show_advanced
        if self.show_advanced:
            self.advanced_frame.grid()
            self.advanced_button.configure(text="Ocultar opciones")
        else:
            self.advanced_frame.grid_remove()
            self.advanced_button.configure(text="Opciones avanzadas")
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _card(self, parent: tk.Widget, row: int, pady: tuple[int, int]) -> tk.Frame:
        card = tk.Frame(parent, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        card.grid(row=row, column=0, sticky="ew", padx=44, pady=pady)
        card.columnconfigure(0, weight=1)
        return card

    def _field(self, parent: tk.Widget, textvariable: StringVar, width: int | None = None) -> tk.Entry:
        entry = tk.Entry(
            parent,
            textvariable=textvariable,
            bg=self.colors["field"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            font=self._font("ui", 11),
            width=width or 20,
        )
        return entry

    def _button(self, parent: tk.Widget, text: str, command, bg: str | None = None, fg: str = "#ffffff") -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg or self.colors["button"],
            fg=fg,
            activebackground=self.colors["button_hover"],
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            cursor="hand2",
            font=self._font("ui", 10, "bold"),
        )
        return button

    def _label(self, parent: tk.Widget, text: str, size: int = 10, bold: bool = False, muted: bool = False) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            fg=self.colors["muted"] if muted else self.colors["text"],
            bg=parent["bg"],
            font=self._font("ui", size, "bold" if bold else "normal"),
        )

    def _build_search_card(self) -> None:
        card = self._card(self.shell, row=2, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        row = tk.Frame(card, bg=self.colors["card"])
        row.grid(row=0, column=0, sticky="ew", padx=18, pady=18)
        row.columnconfigure(0, weight=1)

        self.url_entry = self._field(row, self.url)
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12), ipady=11)
        self._button(row, "X", self._clear_url, bg=self.colors["secondary"]).grid(row=0, column=1, padx=(0, 12))
        self.preview_button = self._button(row, "CARGAR", self._start_preview, bg=self.colors["button"])
        self.preview_button.grid(row=0, column=2, padx=(0, 12))
        self.txt_button = self._button(row, "CARGAR TXT", self._choose_txt, bg=self.colors["secondary"])
        self.txt_button.grid(row=0, column=3)

    def _build_preview_card(self) -> None:
        card = self._card(self.shell, row=3, pady=(0, 14))
        card.grid_columnconfigure(1, weight=1)

        cover = tk.Frame(card, bg=self.colors["card_dark"], highlightthickness=1, highlightbackground=self.colors["accent"], width=128, height=128)
        cover.grid(row=0, column=0, padx=(18, 20), pady=18, sticky="nw")
        cover.grid_propagate(False)
        self.cover_label = tk.Label(
            cover,
            text="Preview",
            fg=self.colors["text_on_dark"],
            bg=self.colors["card_dark"],
            font=self._font("display", 18, "bold"),
        )
        self.cover_label.place(relx=0.5, rely=0.5, anchor="center")

        info = tk.Frame(card, bg=self.colors["card"])
        info.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=20)
        info.columnconfigure(0, weight=1)

        title_label = tk.Label(
            info,
            textvariable=self.playlist_title,
            fg=self.colors["text"],
            bg=self.colors["card"],
            font=self._font("display", 20, "bold"),
            anchor="w",
            justify="left",
            wraplength=620,
        )
        title_label.grid(row=0, column=0, sticky="ew")
        tk.Label(
            info,
            textvariable=self.playlist_summary,
            fg=self.colors["muted"],
            bg=self.colors["card"],
            font=self._font("ui", 10, "bold"),
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        warning = tk.Label(
            info,
            text="Solo descarga contenido propio, autorizado o para respaldo personal.",
            fg=self.colors["accent_dark"],
            bg=self.colors["warning"],
            font=self._font("ui", 9, "bold"),
            padx=12,
            pady=5,
        )
        warning.grid(row=2, column=0, sticky="w", pady=(0, 10))

    def _build_controls_card(self) -> None:
        card = self._card(self.shell, row=4, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(card, bg=self.colors["card"])
        controls.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        self._label(controls, "Formato", bold=True).grid(row=0, column=0, sticky="w", pady=(0, 6))
        format_row = tk.Frame(controls, bg=self.colors["card"])
        format_row.grid(row=1, column=0, sticky="w", pady=(0, 12))
        for label, value in (("MP3", "mp3"), ("MP4", "mp4")):
            tk.Radiobutton(
                format_row,
                text=label,
                variable=self.kind,
                value=value,
                command=self._sync_quality_controls,
                bg=self.colors["card"],
                fg=self.colors["text"],
                selectcolor=self.colors["field"],
                activebackground=self.colors["card"],
                activeforeground=self.colors["text"],
                font=self._font("ui", 10, "bold"),
            ).pack(side="left", padx=(0, 12))

        self._label(controls, "Calidad MP3", bold=True).grid(row=0, column=1, sticky="w", pady=(0, 6))
        self.audio_combo = ttk.Combobox(controls, textvariable=self.audio_quality, values=["128", "192", "256", "320"], width=12, state="readonly")
        self.audio_combo.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=(0, 12))

        self._label(controls, "Calidad MP4", bold=True).grid(row=0, column=2, sticky="w", pady=(0, 6))
        self.video_combo = ttk.Combobox(
            controls,
            textvariable=self.video_quality,
            values=["best", "2160", "1440", "1080", "720", "480", "360"],
            width=12,
            state="readonly",
        )
        self.video_combo.grid(row=1, column=2, sticky="w", padx=(0, 16), pady=(0, 12))

        self._label(controls, "Limite", bold=True).grid(row=0, column=3, sticky="w", pady=(0, 6))
        self._field(controls, self.limit, width=10).grid(row=1, column=3, sticky="w", pady=(0, 12), ipady=5)

        self._label(controls, "Bloque", bold=True).grid(row=2, column=0, sticky="w", pady=(4, 6))
        ttk.Combobox(controls, textvariable=self.block_size, values=["25", "50", "75", "100"], width=12, state="readonly").grid(row=3, column=0, sticky="w")

        self._label(controls, "Guardar en", bold=True).grid(row=2, column=1, sticky="w", pady=(4, 6))
        self._field(controls, self.output).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(0, 12), ipady=5)
        self._button(controls, "Elegir", self._choose_output, bg=self.colors["secondary"]).grid(row=3, column=3, sticky="w")

        self.advanced_button = self._button(
            controls,
            "Ocultar opciones" if self.show_advanced else "Opciones avanzadas",
            self._toggle_advanced,
            bg=self.colors["secondary"],
        )
        self.advanced_button.grid(row=4, column=0, columnspan=2, sticky="w", pady=(14, 0))

        self.advanced_frame = tk.Frame(controls, bg=self.colors["card"])
        self.advanced_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        self.advanced_frame.columnconfigure(0, weight=1)
        self._label(self.advanced_frame, "Cookies para contenido privado o con sesion", bold=True).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._field(self.advanced_frame, self.cookies).grid(row=1, column=0, sticky="ew", padx=(0, 12), ipady=5)
        self._button(self.advanced_frame, "Elegir cookies.txt", self._choose_cookies, bg=self.colors["secondary"]).grid(row=1, column=1, sticky="w")
        if not self.show_advanced:
            self.advanced_frame.grid_remove()

        actions = tk.Frame(card, bg=self.colors["card"])
        actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(6, 20))
        actions.columnconfigure(0, weight=1)
        self.download_button = self._button(actions, "Descargar", self._start_download, bg=self.colors["success"])
        self.download_button.configure(activebackground=self.colors["success_hover"])
        self.download_button.grid(row=0, column=1, padx=(0, 10))
        self.blocks_button = self._button(actions, "Descargar por bloques", self._start_blocks, bg=self.colors["secondary"])
        self.blocks_button.grid(row=0, column=2, padx=(0, 10))
        self.open_button = self._button(actions, "Abrir carpeta", self._open_output, bg=self.colors["secondary"])
        self.open_button.grid(row=0, column=3, padx=(0, 10))
        self.stop_button = self._button(actions, "Detener", self._stop_download, bg="#e5e7eb", fg="#111111")
        self.stop_button.grid(row=0, column=4)

    def _build_log_card(self) -> None:
        card = self._card(self.shell, row=5, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        tk.Label(
            card,
            text="Actividad",
            fg=self.colors["text"],
            bg=self.colors["card"],
            font=self._font("display", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))
        self.log = ScrolledText(
            card,
            wrap="word",
            height=9,
            bg=self.colors["log"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            font=self._font("mono", 10),
        )
        self.log.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def _build_footer(self) -> None:
        footer = tk.Frame(self.shell, bg=self.colors["bg"])
        footer.grid(row=6, column=0, sticky="ew", padx=44, pady=(0, 16))
        footer.columnconfigure(0, weight=1)
        tk.Label(
            footer,
            textvariable=self.status,
            fg=self.colors["text"],
            bg=self.colors["bg"],
            font=self._font("ui", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")

    def _sync_quality_controls(self) -> None:
        if self.kind.get() == "mp3":
            self.audio_combo.configure(state="readonly")
            self.video_combo.configure(state="disabled")
        else:
            self.audio_combo.configure(state="disabled")
            self.video_combo.configure(state="readonly")

    def _check_ffmpeg(self) -> None:
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            self._write(f"ffmpeg detectado: {ffmpeg}\n")
        else:
            self._write("Aviso: no detecte ffmpeg. MP3 y algunos MP4 pueden fallar hasta instalarlo.\n")

    def _clear_url(self) -> None:
        self.url.set("")

    def _choose_output(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output.get() or str(PROJECT_ROOT))
        if folder:
            self.output.set(folder)

    def _choose_txt(self) -> None:
        file = filedialog.askopenfilename(
            title="Elegir lista TXT",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if not file:
            return
        self._set_busy(True, "Cargando TXT...")
        self._write("\n--- Cargando TXT ---\n")
        threading.Thread(target=self._load_txt_tracks, args=(Path(file),), daemon=True).start()

    def _choose_cookies(self) -> None:
        file = filedialog.askopenfilename(
            title="Elegir cookies.txt",
            filetypes=[("Cookies txt", "*.txt"), ("Todos", "*.*")],
        )
        if file:
            self.cookies.set(file)

    def _open_output(self) -> None:
        path = Path(self.output.get().strip() or str(PROJECT_ROOT / "downloads"))
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def _download_thumbnail(self, thumbnail_url: str | None) -> Path | None:
        if not thumbnail_url:
            return None
        cache_dir = Path(tempfile.gettempdir()) / "spotisaver_thumbnails"
        cache_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(thumbnail_url.encode("utf-8")).hexdigest()
        target = cache_dir / f"{digest}.jpg"
        if target.exists() and target.stat().st_size > 0:
            return target

        request = Request(thumbnail_url, headers={"User-Agent": "Mozilla/5.0"})
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=15, context=context) as response:
            target.write_bytes(response.read())
        return target

    def _set_thumbnail(self, image_path: Path | None) -> None:
        if not self.cover_label:
            return
        if not image_path or not image_path.exists():
            self.thumbnail_image = None
            self.cover_label.configure(image="", text="Preview")
            return

        image = Image.open(image_path).convert("RGB")
        image.thumbnail((128, 128), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (128, 128), self.colors["card_dark"])
        x = (128 - image.width) // 2
        y = (128 - image.height) // 2
        canvas.paste(image, (x, y))
        self.thumbnail_image = ImageTk.PhotoImage(canvas)
        self.cover_label.configure(image=self.thumbnail_image, text="")

    def _base_command(self, url: str) -> list[str]:
        cmd = [sys.executable]
        if getattr(sys, "frozen", False):
            cmd.append("--download")
        else:
            cmd.extend(["-m", "motor.download_playlist"])
        cmd.extend([
            url,
            "--kind",
            self.kind.get(),
            "--output",
            self.output.get().strip() or str(PROJECT_ROOT / "downloads"),
            "--audio-quality",
            self.audio_quality.get(),
            "--video-quality",
            self.video_quality.get(),
        ])
        cookies = self.cookies.get().strip()
        if cookies:
            cmd.extend(["--cookies", cookies])
        return cmd

    def _parse_txt_tracks(self, path: Path) -> list[dict[str, str | int]]:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        rows: list[dict[str, str | int]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^\d+\.\s*", "", line)
            if not line:
                continue
            rows.append(
                {
                    "index": len(rows) + 1,
                    "title": line,
                    "status": "Disponible",
                }
            )
        return rows

    def _load_txt_tracks(self, path: Path) -> None:
        try:
            rows = self._parse_txt_tracks(path)
            if not rows:
                self.messages.put("No encontre canciones en el TXT.\n")
                return

            title = path.stem
            self.playlist_title.set(self._short_text(title))
            self.playlist_summary.set(f"{len(rows)} tracks leidos desde TXT | metadatos locales")
            self.messages.put(("thumbnail", None))
            self.messages.put(f"TXT: {title}\n")
            self.messages.put(f"Tracks leidos: {len(rows)}\n")
            for row in rows[:120]:
                self.messages.put(f"{int(row['index']):02d} - {row['title']}\n")
            if len(rows) > 120:
                self.messages.put(f"... y {len(rows) - 120} mas.\n")

            query = str(rows[0]["title"])
            matches = search_youtube_matches(f"{query} official audio", limit=5)
            if not matches:
                self.messages.put("\nNo encontre coincidencias para el primer track.\n")
                return

            self.messages.put(f"\nCoincidencias en YouTube para: {query}\n")
            for index, match in enumerate(matches, start=1):
                channel = f" | {match['channel']}" if match.get("channel") else ""
                duration = f" | {match['duration']}" if match.get("duration") else ""
                self.messages.put(f"{index}. {match['title']}{channel}{duration}\n")

            best = matches[0]
            self.url.set(best["url"])
            self.playlist_summary.set(f"{len(rows)} tracks leidos desde TXT | primera coincidencia preparada")
            self.messages.put(f"\nURL preparada: {best['url']}\n")
        except Exception as exc:
            self.messages.put(f"\nERROR cargando TXT: {exc}\n")
        finally:
            self.messages.put(None)

    def _start_download(self) -> None:
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("Falta URL", "Pega la URL de la playlist primero.")
            return

        limit = self._validated_limit()
        if limit is None:
            return

        cmd = self._base_command(url)
        if limit:
            cmd.extend(["--limit", str(limit)])

        self._set_busy(True, "Descargando...")
        self._write("\n--- Nueva descarga ---\n")
        threading.Thread(target=self._run_command, args=(cmd,), daemon=True).start()

    def _start_preview(self) -> None:
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("Falta URL", "Pega la URL de la playlist primero.")
            return

        limit = self._validated_limit()
        if limit is None:
            return

        self._set_busy(True, "Cargando lista...")
        self._write("\n--- Cargando lista ---\n")
        threading.Thread(target=self._load_preview, args=(url, limit), daemon=True).start()

    def _start_blocks(self) -> None:
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("Falta URL", "Pega la URL de la playlist primero.")
            return

        block_size = self._validated_block_size()
        if block_size is None:
            return

        self._set_busy(True, "Preparando bloques...")
        self._write("\n--- Descarga por bloques ---\n")
        threading.Thread(target=self._run_blocks, args=(url, block_size), daemon=True).start()

    def _run_blocks(self, url: str, block_size: int) -> None:
        try:
            cookies = self.cookies.get().strip() or None
            title, rows = get_playlist_table(url, cookies=cookies)
            total = len(rows)
            if total == 0:
                self.messages.put("No encontre elementos para descargar.\n")
                return

            unavailable = sum(1 for row in rows if row["status"] == "No disponible")
            repeated = sum(1 for row in rows if row["status"] == "Repetido")
            self.messages.put(f"Playlist: {title}\n")
            self.messages.put(f"Total detectado: {total}\n")
            self.messages.put(f"No disponibles: {unavailable}\n")
            self.messages.put(f"Repetidos: {repeated}\n")
            self.messages.put(f"Tamano de bloque: {block_size}\n\n")

            start = 1
            while start <= total:
                end = min(start + block_size - 1, total)
                self.messages.put(f"\n=== Bloque {start:03d}-{end:03d} ===\n")
                cmd = self._base_command(url)
                cmd.extend(["--start", str(start), "--end", str(end)])
                code = self._run_subprocess_sync(cmd)
                if code != 0:
                    self.messages.put(f"\nSe detuvo en bloque {start:03d}-{end:03d}, codigo {code}.\n")
                    return
                start = end + 1

            self.messages.put("\nTodos los bloques terminaron.\n")
        except Exception as exc:
            self.messages.put(f"\nERROR en bloques: {exc}\n")
        finally:
            self.process = None
            self.messages.put(None)

    def _run_subprocess_sync(self, cmd: list[str]) -> int:
        self.process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.messages.put(line)
        return self.process.wait()

    def _load_preview(self, url: str, limit: int) -> None:
        try:
            cookies = self.cookies.get().strip() or None
            if is_spotify_url(url):
                if spotify_credentials_available():
                    try:
                        title, rows, thumbnail_url = get_spotify_api_details(url)
                        source = "Spotify Web API"
                    except Exception as exc:
                        self.messages.put(f"Spotify Web API no permitio leer este enlace: {exc}\n")
                        self.messages.put("Uso oEmbed como respaldo. Para listas completas, usa CARGAR TXT.\n")
                        metadata = get_spotify_oembed(url)
                        title = str(metadata.get("title") or "Spotify")
                        rows = []
                        thumbnail_url = metadata.get("thumbnail_url")
                        source = "Spotify oEmbed"
                else:
                    metadata = get_spotify_oembed(url)
                    title = str(metadata.get("title") or "Spotify")
                    rows = []
                    thumbnail_url = metadata.get("thumbnail_url")
                    source = "Spotify oEmbed"

                thumbnail_path = self._download_thumbnail(thumbnail_url)
                self.playlist_title.set(self._short_text(title))
                if rows:
                    self.playlist_summary.set(f"{len(rows)} tracks leidos desde Spotify | metadatos solamente")
                else:
                    self.playlist_summary.set("Spotify usado como referencia | buscando coincidencias publicas")
                self.messages.put(("thumbnail", thumbnail_path))
                self.messages.put(f"{source}: {title}\n")
                self.messages.put("Spotify solo se usa para metadatos; no se descarga audio desde Spotify.\n")

                if rows:
                    self.messages.put(f"\nTracks leidos: {len(rows)}\n")
                    for row in rows[:100]:
                        self.messages.put(f"{int(row['index']):02d} - {row['title']}\n")
                    if len(rows) > 100:
                        self.messages.put(f"... y {len(rows) - 100} mas.\n")
                    query = str(rows[0]["title"])
                else:
                    query = title

                matches = search_youtube_matches(f"{query} official audio", limit=5)
                if not matches:
                    self.messages.put("No encontre coincidencias en YouTube. Prueba con artista - cancion.\n")
                    return

                self.messages.put(f"\nCoincidencias en YouTube para: {query}\n")
                for index, match in enumerate(matches, start=1):
                    channel = f" | {match['channel']}" if match.get("channel") else ""
                    duration = f" | {match['duration']}" if match.get("duration") else ""
                    self.messages.put(f"{index}. {match['title']}{channel}{duration}\n")

                best = matches[0]
                self.url.set(best["url"])
                if rows:
                    self.playlist_summary.set(f"{len(rows)} tracks leidos | primera coincidencia preparada")
                else:
                    self.playlist_summary.set("Coincidencia encontrada en YouTube | revisa y descarga si es correcta")
                self.messages.put(f"\nURL preparada: {best['url']}\n")
                return

            title, rows, thumbnail_url = get_playlist_details(url, limit=limit or None, cookies=cookies)
            thumbnail_path = self._download_thumbnail(thumbnail_url)

            self.playlist_title.set(self._short_text(title))
            unavailable = sum(1 for row in rows if row["status"] == "No disponible")
            repeated = sum(1 for row in rows if row["status"] == "Repetido")
            if rows:
                self.playlist_summary.set(f"{len(rows)} elementos detectados | {unavailable} no disponibles | {repeated} repetidos")
            else:
                self.playlist_summary.set("Video individual detectado | listo para descargar")
            self.messages.put(("thumbnail", thumbnail_path))

            self.messages.put(f"Playlist: {title}\n")
            if not rows:
                self.messages.put("Video individual listo para descargar.\n")
            else:
                for row in rows:
                    self.messages.put(f"{row['index']:02d} - {row['title']} [{row['status']}]\n")
                self.messages.put(f"\nElementos mostrados: {len(rows)}\n")
                self.messages.put(f"No disponibles: {unavailable}\n")
                self.messages.put(f"Repetidos: {repeated}\n")
        except Exception as exc:
            self.messages.put(f"\nERROR cargando lista: {exc}\n")
        finally:
            self.messages.put(None)

    def _validated_limit(self) -> int | None:
        limit = self.limit.get().strip()
        if limit and (not limit.isdigit() or int(limit) <= 0):
            messagebox.showwarning("Limite invalido", "El limite debe ser un numero mayor que 0.")
            return None
        return int(limit) if limit else 0

    def _validated_block_size(self) -> int | None:
        value = self.block_size.get().strip()
        if not value.isdigit() or int(value) <= 0:
            messagebox.showwarning("Bloque invalido", "El bloque debe ser un numero mayor que 0.")
            return None
        return int(value)

    def _run_command(self, cmd: list[str]) -> None:
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.messages.put(line)
            code = self.process.wait()
            self.messages.put(f"\nProceso terminado con codigo {code}.\n")
        except Exception as exc:
            self.messages.put(f"\nERROR: {exc}\n")
        finally:
            self.process = None
            self.messages.put(None)

    def _stop_download(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._write("\nDeteniendo descarga...\n")

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        state = "disabled" if busy else "normal"
        self.preview_button.configure(state=state)
        self.txt_button.configure(state=state)
        self.download_button.configure(state=state)
        self.blocks_button.configure(state=state)
        if busy:
            self.stop_button.configure(
                bg=self.colors["danger"],
                fg="#ffffff",
                activebackground=self.colors["danger_hover"],
                activeforeground="#ffffff",
            )
        else:
            self.stop_button.configure(bg="#e5e7eb", fg="#111111", activeforeground="#111111")
        self.status.set(status or ("Listo" if not busy else "Trabajando..."))

    def _drain_messages(self) -> None:
        try:
            while True:
                item = self.messages.get_nowait()
                if item is None:
                    self._set_busy(False, "Listo")
                elif isinstance(item, tuple) and item[0] == "thumbnail":
                    self._set_thumbnail(item[1])
                else:
                    self._write(item)
        except queue.Empty:
            pass
        self.root.after(150, self._drain_messages)

    def _write(self, text: str) -> None:
        self.log.insert(END, text)
        self.log.see(END)


def main() -> None:
    root = Tk()
    PlaylistDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--download":
        raise SystemExit(download_main(sys.argv[2:]))
    main()
