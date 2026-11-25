[app]
title = Spotisaver
package.name = spotisaver
package.domain = org.spotisaver
source.dir = ..
source.include_exts = py,kv,png,jpg,jpeg,json,txt
source.exclude_dirs = pc,.venv,.git,downloads,dist,build,__pycache__,tests
version = 0.1.0
requirements = python3,kivy,yt-dlp,certifi,python-dotenv,ffmpeg,av_codecs,openssl
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
