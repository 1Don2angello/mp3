param(
  [Parameter(Mandatory = $true)]
  [string]$Url,

  [ValidateSet("mp3", "mp4")]
  [string]$Kind = "mp3",

  [string]$Output = "downloads",

  [int]$AudioQuality = 192,

  [ValidateSet("best", "2160", "1440", "1080", "720", "480", "360")]
  [string]$VideoQuality = "best",

  [string]$Cookies = "",

  [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (!(Test-Path $VenvPython)) {
  python -m venv (Join-Path $ProjectRoot ".venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

$argsList = @(
  (Join-Path $ProjectRoot "download_playlist.py"),
  $Url,
  "--kind", $Kind,
  "--output", $Output,
  "--audio-quality", "$AudioQuality",
  "--video-quality", "$VideoQuality"
)

if ($Cookies) {
  $argsList += @("--cookies", $Cookies)
}

if ($Limit -gt 0) {
  $argsList += @("--limit", "$Limit")
}

& $VenvPython @argsList
