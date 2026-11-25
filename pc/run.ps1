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
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$OutputPath = if ([System.IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $ProjectRoot $Output }

if (!(Test-Path $VenvPython)) {
  python -m venv (Join-Path $ProjectRoot ".venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

$argsList = @(
  "-m", "motor.download_playlist", $Url,
  "--kind", $Kind,
  "--output", $OutputPath,
  "--audio-quality", "$AudioQuality",
  "--video-quality", "$VideoQuality"
)

if ($Cookies) {
  $argsList += @("--cookies", $Cookies)
}

if ($Limit -gt 0) {
  $argsList += @("--limit", "$Limit")
}

Push-Location $ProjectRoot
try {
  & $VenvPython @argsList
} finally {
  Pop-Location
}
