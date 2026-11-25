from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import ssl
import sys
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

import yt_dlp
import certifi
from dotenv import load_dotenv
from yt_dlp.utils import DownloadError


INVALID_PATH_CHARS = r'<>:"/\|?*'
SPOTIFY_URL_RE = re.compile(r"https?://(?:open\.spotify\.com|spotify\.link)/\S+", re.IGNORECASE)
SPOTIFY_RESOURCE_RE = re.compile(r"open\.spotify\.com/(track|album|playlist)/([A-Za-z0-9]+)", re.IGNORECASE)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def clean_name(value: str, fallback: str = "playlist") -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = "".join("_" if ch in INVALID_PATH_CHARS else ch for ch in value)
    value = value.strip(" .")
    return value or fallback


def is_spotify_url(url: str) -> bool:
    return bool(SPOTIFY_URL_RE.search(url or ""))


def spotify_credentials_available() -> bool:
    return bool(os.environ.get("SPOTIFY_CLIENT_ID") and os.environ.get("SPOTIFY_CLIENT_SECRET"))


def spotify_resource_from_url(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    match = SPOTIFY_RESOURCE_RE.search(f"{parsed.netloc}{parsed.path}")
    if not match:
        return None
    return match.group(1).lower(), match.group(2)


def spotify_request_json(url: str, headers: dict[str, str] | None = None, data: bytes | None = None) -> dict:
    request = Request(url, headers=headers or {}, data=data)
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=25, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def get_spotify_access_token() -> str:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("Faltan SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en .env")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    data = b"grant_type=client_credentials"
    result = spotify_request_json(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=data,
    )
    return str(result["access_token"])


def spotify_api_get(path_or_url: str, token: str) -> dict:
    url = path_or_url if path_or_url.startswith("https://") else f"https://api.spotify.com/v1/{path_or_url.lstrip('/')}"
    return spotify_request_json(url, headers={"Authorization": f"Bearer {token}"})


def spotify_image_url(images: list[dict] | None) -> str | None:
    if not images:
        return None
    return str(images[0].get("url") or "") or None


def spotify_track_row(track: dict) -> dict[str, str | int]:
    artists = ", ".join(artist.get("name", "") for artist in track.get("artists") or [] if artist.get("name"))
    title = str(track.get("name") or "Sin titulo")
    album = track.get("album") or {}
    return {
        "index": 0,
        "title": f"{artists} - {title}" if artists else title,
        "status": "Disponible",
        "artist": artists,
        "track": title,
        "album": str(album.get("name") or ""),
        "duration_ms": int(track.get("duration_ms") or 0),
    }


def get_spotify_api_details(url: str) -> tuple[str, list[dict[str, str | int]], str | None]:
    resource = spotify_resource_from_url(url)
    if not resource:
        raise RuntimeError("No pude identificar si el link de Spotify es track, album o playlist.")

    token = get_spotify_access_token()
    kind, resource_id = resource

    if kind == "track":
        track = spotify_api_get(f"tracks/{resource_id}", token)
        row = spotify_track_row(track)
        row["index"] = 1
        title = str(row["title"])
        return title, [row], spotify_image_url((track.get("album") or {}).get("images"))

    if kind == "album":
        album = spotify_api_get(f"albums/{resource_id}", token)
        rows: list[dict[str, str | int]] = []
        items = list((album.get("tracks") or {}).get("items") or [])
        next_url = (album.get("tracks") or {}).get("next")
        while next_url:
            page = spotify_api_get(str(next_url), token)
            items.extend(page.get("items") or [])
            next_url = page.get("next")

        album_name = str(album.get("name") or "Album")
        album_images = album.get("images") or []
        for index, track in enumerate(items, start=1):
            track["album"] = {"name": album_name, "images": album_images}
            row = spotify_track_row(track)
            row["index"] = index
            rows.append(row)
        return album_name, rows, spotify_image_url(album_images)

    playlist = spotify_api_get(f"playlists/{resource_id}", token)
    rows = []
    items = list((playlist.get("tracks") or {}).get("items") or [])
    next_url = (playlist.get("tracks") or {}).get("next")
    while next_url:
        page = spotify_api_get(str(next_url), token)
        items.extend(page.get("items") or [])
        next_url = page.get("next")

    for item in items:
        track = item.get("track") or {}
        if not track or track.get("is_local"):
            continue
        row = spotify_track_row(track)
        row["index"] = len(rows) + 1
        rows.append(row)
    return str(playlist.get("name") or "Playlist"), rows, spotify_image_url(playlist.get("images"))


def get_spotify_oembed(url: str) -> dict[str, str | None]:
    endpoint = f"https://open.spotify.com/oembed?url={quote_plus(url)}"
    request = Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=20, context=context) as response:
        data = json.loads(response.read().decode("utf-8"))

    return {
        "title": data.get("title"),
        "thumbnail_url": data.get("thumbnail_url"),
        "provider_name": data.get("provider_name"),
    }


def youtube_url_from_entry(entry: dict) -> str | None:
    url = entry.get("webpage_url") or entry.get("url")
    if not url:
        video_id = entry.get("id")
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else None
    url = str(url)
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://www.youtube.com/watch?v={url}"


def search_youtube_matches(query: str, limit: int = 5) -> list[dict[str, str]]:
    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }
    node_location = find_node()
    if node_location:
        options["js_runtimes"] = {"node": {"path": node_location}}

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    matches: list[dict[str, str]] = []
    for entry in info.get("entries") or []:
        if not entry:
            continue
        url = youtube_url_from_entry(entry)
        if not url:
            continue
        matches.append(
            {
                "title": str(entry.get("title") or "Sin titulo"),
                "url": url,
                "channel": str(entry.get("channel") or entry.get("uploader") or ""),
                "duration": str(entry.get("duration_string") or ""),
            }
        )
    return matches


def get_playlist_title(url: str, cookies: str | None = None) -> str:
    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "noplaylist": False,
    }
    if cookies:
        options["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return clean_name(
        info.get("playlist_title")
        or info.get("title")
        or info.get("playlist")
        or "playlist"
    )


def get_playlist_preview(url: str, limit: int | None = None, cookies: str | None = None) -> tuple[str, list[str]]:
    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "noplaylist": False,
    }
    if cookies:
        options["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    title = clean_name(
        info.get("playlist_title")
        or info.get("title")
        or info.get("playlist")
        or "playlist"
    )
    entries = info.get("entries") or []
    names: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if limit and len(names) >= limit:
            break
        item = playlist_entry_row(index, entry)
        names.append(f"{item['index']:02d} - {item['title']} [{item['status']}]")
    return title, names


def playlist_entry_row(index: int, entry: dict | None) -> dict[str, str | int]:
    if not entry:
        return {"index": index, "title": "No disponible", "status": "No disponible"}

    title = str(entry.get("title") or entry.get("url") or entry.get("id") or "Sin titulo").strip()
    low_title = title.lower()
    availability = str(entry.get("availability") or "").lower()
    availability_reason = str(entry.get("availability_reason") or "").strip()

    unavailable_words = (
        "deleted video",
        "private video",
        "unavailable video",
        "video unavailable",
        "this video is unavailable",
        "[deleted",
        "[private",
    )
    unavailable_states = {"private", "premium_only", "subscriber_only", "needs_auth", "unlisted"}

    if any(word in low_title for word in unavailable_words) or availability in unavailable_states:
        title = title if title and title != "Sin titulo" else "No disponible"
        if availability_reason:
            title = f"{title} - {availability_reason}"
        return {"index": index, "title": title, "status": "No disponible"}

    return {"index": index, "title": title, "status": "Disponible"}


def duplicate_key(title: str) -> str:
    value = clean_name(title, fallback="")
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\[[^\]]+\]$", "", value).strip()
    return value


def mark_duplicate_titles(rows: list[dict[str, str | int]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        if row["status"] == "No disponible":
            continue
        key = duplicate_key(str(row["title"]))
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1

    for row in rows:
        if row["status"] == "No disponible":
            continue
        key = duplicate_key(str(row["title"]))
        if key and counts.get(key, 0) > 1:
            row["status"] = "Repetido"


def thumbnail_from_info(info: dict) -> str | None:
    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        best = sorted(
            thumbnails,
            key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0),
            reverse=True,
        )[0]
        if best.get("url"):
            return str(best["url"])

    if info.get("thumbnail"):
        return str(info["thumbnail"])

    entries = info.get("entries") or []
    for entry in entries:
        if not entry:
            continue
        thumbnail = thumbnail_from_info(entry)
        if thumbnail:
            return thumbnail
    return None


def extract_playlist_info(url: str, cookies: str | None = None) -> dict:
    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "noplaylist": False,
    }
    if cookies:
        options["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def get_playlist_table(url: str, limit: int | None = None, cookies: str | None = None) -> tuple[str, list[dict[str, str | int]]]:
    info = extract_playlist_info(url, cookies)

    title = clean_name(
        info.get("playlist_title")
        or info.get("title")
        or info.get("playlist")
        or "playlist"
    )
    rows: list[dict[str, str | int]] = []
    for index, entry in enumerate(info.get("entries") or [], start=1):
        if limit and len(rows) >= limit:
            break
        rows.append(playlist_entry_row(index, entry))
    mark_duplicate_titles(rows)
    return title, rows


def get_playlist_details(
    url: str,
    limit: int | None = None,
    cookies: str | None = None,
) -> tuple[str, list[dict[str, str | int]], str | None]:
    info = extract_playlist_info(url, cookies)
    title = clean_name(
        info.get("playlist_title")
        or info.get("title")
        or info.get("playlist")
        or "playlist"
    )
    rows: list[dict[str, str | int]] = []
    for index, entry in enumerate(info.get("entries") or [], start=1):
        if limit and len(rows) >= limit:
            break
        rows.append(playlist_entry_row(index, entry))
    mark_duplicate_titles(rows)
    return title, rows, thumbnail_from_info(info)


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found

    local_app_data = os.environ.get("LOCALAPPDATA")
    candidates: list[Path] = []
    if local_app_data:
        candidates.append(Path(local_app_data) / "Microsoft" / "WinGet" / "Packages")
    candidates.append(Path("C:/Program Files"))
    candidates.append(Path("C:/Program Files (x86)"))

    for root in candidates:
        if not root.exists():
            continue
        try:
            for path in root.rglob("ffmpeg.exe"):
                return str(path.parent)
        except OSError:
            continue
    return None


def find_ffplay() -> str | None:
    found = shutil.which("ffplay")
    if found:
        return found
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return None
    location = Path(ffmpeg)
    directory = location if location.is_dir() else location.parent
    for name in ("ffplay.exe", "ffplay"):
        candidate = directory / name
        if candidate.is_file():
            return str(candidate)
    return None


def resolve_audio_preview(url: str, cookies: str | None = None) -> tuple[str, str, dict[str, str]]:
    """Obtiene la URL temporal de audio sin descargar el archivo."""
    if is_spotify_url(url):
        raise ValueError("Carga primero el enlace de Spotify y revisa la coincidencia sugerida.")
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio/best",
        "playlist_items": "1",
        "noplaylist": False,
    }
    if cookies:
        options["cookiefile"] = cookies
    node_location = find_node()
    if node_location:
        options["js_runtimes"] = {"node": {"path": node_location}}

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("No se encontro audio para escuchar.")
        if info.get("entries") is not None:
            info = next((entry for entry in info["entries"] if entry), None)
        if not info:
            raise RuntimeError("La lista no contiene elementos disponibles.")
        if info.get("_type") in {"url", "url_transparent"}:
            info = ydl.extract_info(info["url"], download=False)
        stream_url = info.get("url") if info else None
        if not stream_url:
            raise RuntimeError("La fuente no entrego un enlace de audio reproducible.")
        headers = {
            str(key): str(value)
            for key, value in (info.get("http_headers") or {}).items()
            if "\r" not in str(key) + str(value) and "\n" not in str(key) + str(value)
        }
        return str(info.get("title") or "Muestra"), str(stream_url), headers


def find_node() -> str | None:
    return shutil.which("node")


def build_options(args: argparse.Namespace, output_dir: Path) -> dict:
    base = {
        "outtmpl": str(output_dir / "%(playlist_index|00)s - %(title).180s [%(id)s].%(ext)s"),
        "ignoreerrors": True,
        "skip_unavailable_fragments": True,
        "noplaylist": False,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "windowsfilenames": True,
        "restrictfilenames": False,
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }

    if args.cookies:
        base["cookiefile"] = args.cookies

    if args.limit:
        base["playlistend"] = args.limit
    if args.start:
        base["playliststart"] = args.start
    if args.end:
        base["playlistend"] = args.end

    ffmpeg_location = find_ffmpeg()
    if ffmpeg_location:
        base["ffmpeg_location"] = ffmpeg_location

    node_location = find_node()
    if node_location:
        base["js_runtimes"] = {"node": {"path": node_location}}

    if args.kind == "mp3":
        base.update(
            {
                "format": "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": str(args.audio_quality),
                    }
                ],
            }
        )
    else:
        video_quality = getattr(args, "video_quality", "best")
        if video_quality == "best":
            video_format = "bv*[ext=mp4]+ba[ext=m4a]/22/18/b[ext=mp4]/best"
        else:
            video_format = (
                f"bv*[height<={video_quality}][ext=mp4]+ba[ext=m4a]/"
                f"18/b[height<={video_quality}][ext=mp4]/best[height<={video_quality}]"
            )
        base.update(
            {
                "format": video_format,
                "merge_output_format": "mp4",
            }
        )

    return base


def filter_rows_for_current_download(
    rows: list[dict[str, str | int]],
    args: argparse.Namespace,
) -> list[dict[str, str | int]]:
    start = args.start or 1
    end = args.end or args.limit or (rows[-1]["index"] if rows else 0)

    filtered = []
    for row in rows:
        idx = int(row["index"])
        if start <= idx <= end:
            filtered.append(row)
    return filtered


def download_indexes(
    args: argparse.Namespace,
    output_dir: Path,
    indexes: list[int],
) -> int:
    if not indexes:
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    options = build_options(args, output_dir)
    options.pop("playliststart", None)
    options.pop("playlistend", None)
    options["playlist_items"] = ",".join(str(index) for index in indexes)

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.download([args.url])


def download_direct(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    options = build_options(args, output_dir)
    options.pop("playliststart", None)
    options.pop("playlistend", None)
    options["ignoreerrors"] = False
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.download([args.url])
    except DownloadError as exc:
        print("Aviso: fallo el formato elegido. Reintentando con formato compatible...", file=sys.stderr)
        fallback_options = dict(options)
        fallback_options["format"] = "18/best[ext=mp4]/best"
        try:
            with yt_dlp.YoutubeDL(fallback_options) as ydl:
                return ydl.download([args.url])
        except DownloadError:
            raise exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descarga una playlist autorizada en MP3 o MP4."
    )
    parser.add_argument("url", help="URL de la playlist o video.")
    parser.add_argument(
        "--kind",
        choices=["mp3", "mp4"],
        default="mp3",
        help="Formato de salida. Default: mp3.",
    )
    parser.add_argument(
        "--output",
        default="downloads",
        help="Carpeta base de descargas. Default: downloads.",
    )
    parser.add_argument(
        "--audio-quality",
        type=int,
        default=192,
        help="Calidad MP3 en kbps. Default: 192.",
    )
    parser.add_argument(
        "--video-quality",
        choices=["best", "2160", "1440", "1080", "720", "480", "360"],
        default="best",
        help="Calidad maxima para MP4. Default: best.",
    )
    parser.add_argument(
        "--cookies",
        help="Archivo cookies.txt si la playlist requiere sesión.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Descarga solo los primeros N elementos, útil para probar.",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="Número inicial de la playlist para descargar.",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="Número final de la playlist para descargar.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ffmpeg_location = find_ffmpeg()

    if args.kind == "mp3" and ffmpeg_location is None:
        print(
            "ERROR: Para convertir a MP3 necesitas ffmpeg instalado y en el PATH.",
            file=sys.stderr,
        )
        print(
            "Puedes instalarlo con winget: winget install Gyan.FFmpeg",
            file=sys.stderr,
        )
        return 2

    if args.kind == "mp4" and ffmpeg_location is None:
        print(
            "Aviso: ffmpeg no está en PATH. Algunos videos MP4 pueden requerirlo para unir audio y video.",
            file=sys.stderr,
        )

    playlist_title, playlist_rows = get_playlist_table(args.url, args.limit, args.cookies)
    playlist_dir = Path(args.output).expanduser().resolve() / playlist_title
    output_dir = playlist_dir
    if args.start and args.end:
        output_dir = output_dir / f"Bloque {args.start:03d}-{args.end:03d}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Playlist: {playlist_title}")
    print(f"Destino:  {output_dir}")
    print(f"Formato:  {args.kind.upper()}")

    current_rows = filter_rows_for_current_download(playlist_rows, args)
    if not current_rows:
        print("Video individual detectado.")
        code = download_direct(args, output_dir)
        if code:
            print("ERROR: La descarga no termino correctamente.", file=sys.stderr)
            return code
        print("Listo.")
        return 0

    normal_indexes = [
        int(row["index"])
        for row in current_rows
        if row["status"] == "Disponible"
    ]
    repeated_indexes = [
        int(row["index"])
        for row in current_rows
        if row["status"] == "Repetido"
    ]
    unavailable_count = sum(1 for row in current_rows if row["status"] == "No disponible")

    if unavailable_count:
        print(f"No disponibles omitidos: {unavailable_count}")
    if repeated_indexes:
        print(f"Repetidos a carpeta separada: {len(repeated_indexes)}")

    normal_code = download_indexes(args, output_dir, normal_indexes)
    repeated_code = download_indexes(args, output_dir / "Repetidos", repeated_indexes)
    if normal_code or repeated_code:
        print("ERROR: Una o mas descargas no terminaron correctamente.", file=sys.stderr)
        return normal_code or repeated_code

    print("Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
