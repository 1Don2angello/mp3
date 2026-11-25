$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android\Sdk" }
$BuildTools = Get-ChildItem -LiteralPath (Join-Path $SdkRoot "build-tools") -Directory | Sort-Object Name -Descending | Select-Object -First 1
$Platform = Get-ChildItem -LiteralPath (Join-Path $SdkRoot "platforms") -Directory | Sort-Object Name -Descending | Select-Object -First 1
if (-not $BuildTools -or -not $Platform) { throw "Falta Android SDK o Build Tools." }

$AndroidJar = Join-Path $Platform.FullName "android.jar"
$BuildDir = Join-Path $ProjectRoot "build"
$ClassesDir = Join-Path $BuildDir "classes"
$DexDir = Join-Path $BuildDir "dex"
$DistDir = Join-Path $ProjectRoot "dist"
$KeyDir = Join-Path $ProjectRoot ".debug"
$KeyFile = Join-Path $KeyDir "debug.keystore"
$Unsigned = Join-Path $BuildDir "unsigned.apk"
$Aligned = Join-Path $BuildDir "aligned.apk"
$Final = Join-Path $DistDir "Spotisaver-Voz-Prueba.apk"

New-Item -ItemType Directory -Force -Path $ClassesDir, $DexDir, $DistDir, $KeyDir | Out-Null

$Source = Join-Path $ProjectRoot "src\org\spotisaver\ttsprueba\MainActivity.java"
$Manifest = Join-Path $ProjectRoot "AndroidManifest.xml"
$Aapt2 = Join-Path $BuildTools.FullName "aapt2.exe"
$D8 = Join-Path $BuildTools.FullName "d8.bat"
$ZipAlign = Join-Path $BuildTools.FullName "zipalign.exe"
$ApkSigner = Join-Path $BuildTools.FullName "apksigner.bat"

& javac -encoding UTF-8 -source 8 -target 8 -classpath $AndroidJar -d $ClassesDir $Source
if ($LASTEXITCODE -ne 0) { throw "Fallo javac." }

$ClassFiles = @(Get-ChildItem -LiteralPath $ClassesDir -Filter "*.class" -Recurse | ForEach-Object FullName)
& $D8 --min-api 23 --lib $AndroidJar --output $DexDir @ClassFiles
if ($LASTEXITCODE -ne 0) { throw "Fallo d8." }

& $Aapt2 link --manifest $Manifest -I $AndroidJar -o $Unsigned
if ($LASTEXITCODE -ne 0) { throw "Fallo aapt2." }

& jar uf $Unsigned -C $DexDir classes.dex
if ($LASTEXITCODE -ne 0) { throw "Fallo jar." }

& $ZipAlign -f 4 $Unsigned $Aligned
if ($LASTEXITCODE -ne 0) { throw "Fallo zipalign." }

if (-not (Test-Path -LiteralPath $KeyFile)) {
    & keytool -genkeypair -keystore $KeyFile -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Spotisaver Debug,O=Spotisaver,C=MX"
    if ($LASTEXITCODE -ne 0) { throw "Fallo keytool." }
}

& $ApkSigner sign --ks $KeyFile --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out $Final $Aligned
if ($LASTEXITCODE -ne 0) { throw "Fallo apksigner." }
& $ApkSigner verify --verbose $Final
if ($LASTEXITCODE -ne 0) { throw "La firma del APK no paso la verificacion." }

Write-Output "APK listo: $Final"
