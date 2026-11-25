# Playlist Downloader

## Estructura del proyecto

```text
motor/   Logica de metadatos, descargas y sesiones de audio online
pc/      Interfaz Tkinter, salida de sonido con FFplay y compilacion del EXE
movil/   Interfaz Kivy y configuracion para generar el APK de Android
main.py  Entrada minima que Buildozer requiere en la raiz
```

PC y Android ejecutan el mismo modulo `motor.download_playlist`. `motor.audio` coordina la reproduccion online; cada plataforma aporta su salida de sonido. Cada interfaz guarda sus descargas en el dispositivo donde se ejecuta.

Spotisaver es una herramienta independiente para leer metadatos de playlists, albumes y canciones, y crear respaldos MP3/MP4 para uso personal cuando exista una fuente publica compatible.

Pega un enlace de playlist, album o cancion para leer metadatos, buscar coincidencias de audio en fuentes publicas independientes cuando esten disponibles, y generar archivos MP3 o MP4.

Spotisaver no descarga, ripea, graba ni accede al audio desde Spotify. Los enlaces de Spotify se usan solo como referencia de metadatos.

## Requisitos

- Python 3
- `ffmpeg` instalado para convertir a MP3 o unir algunos MP4

En Windows puedes instalar `ffmpeg` con:

```powershell
winget install Gyan.FFmpeg
```

Despues cierra y abre PowerShell para que aparezca en el PATH.

## Uso rapido

Opcional para Spotify Web API:

1. Copia `.env.example` como `.env`.
2. Llena:

```text
SPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_CLIENT_SECRET=tu_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

El archivo `.env` esta ignorado por Git.

Con interfaz:

```powershell
.\pc\run_gui.ps1
```

Pega la URL, presiona **Cargar lista** para revisar nombres sin descargar, elige `MP3` o `MP4`, y presiona **Descargar**.
En PC, **Escuchar 20 s** reproduce una muestra del enlace actual sin guardar el archivo. Si el enlace es una playlist, escucha su primer elemento; **Detener** corta la muestra. Esta funcion requiere `ffplay` junto a `ffmpeg`.
La etiqueta de la vista previa indica si cargaste una playlist, un enlace individual o una coincidencia sugerida. **Limpiar** borra el enlace, la portada, la vista previa y el registro de actividad para empezar con otra seleccion.
Si pegas un enlace de Spotify, la app intenta leer titulo/miniatura y preparar una coincidencia publica en YouTube para que la revises antes de descargar.
En `MP4` puedes elegir calidad maxima: `best`, `2160`, `1440`, `1080`, `720`, `480` o `360`.

Para playlists grandes, usa **Descargar por bloques**. Crea carpetas como:

```text
downloads/
  Nombre playlist/
    Bloque 001-050/
      Repetidos/
    Bloque 051-100/
```

Si un elemento no esta disponible, queda marcado como `No disponible` y la descarga continua con los demas.
Si el nombre esta repetido, queda marcado como `Repetido` y se descarga en una carpeta `Repetidos`.

Desde esta carpeta:

```powershell
.\pc\run.ps1 "URL_DE_TU_PLAYLIST"
```

Eso descarga en MP3 por defecto.

Para MP4:

```powershell
.\pc\run.ps1 "URL_DE_TU_PLAYLIST" -Kind mp4
```

Para MP4 en 1080p:

```powershell
.\pc\run.ps1 "URL_DE_TU_PLAYLIST" -Kind mp4 -VideoQuality 1080
```

## Crear EXE

Desde esta carpeta:

```powershell
.\.venv\Scripts\python.exe pc\build_exe.py
```

El ejecutable queda en:

```text
pc\dist\Spotisaver.exe
```

El EXE no incluye tus descargas. La carpeta `downloads/` esta ignorada por Git y no se empaqueta.

## Android (APK)

La app Android esta en `movil/main.py` y usa el motor compartido. Incluye carga de listas, revision de coincidencias para enlaces de Spotify y descarga MP3/MP4 al almacenamiento privado de la app. La configuracion de compilacion esta en `movil/buildozer.spec` e incluye la receta Android de FFmpeg con codificador MP3.

La propuesta visual de la futura radio esta en `movil/mockups/index.html`. Abrela en un navegador para ver cuatro pantallas en blanco y negro: inicio, reproductor, cola y biblioteca. Es una maqueta estatica; todavia no esta conectada al APK.
Las frases propuestas para el locutor TTS estan guardadas en `docs/frases-locutor-radio.md` para adaptarlas cuando se implemente la voz.

Hay un APK independiente para probar primero el locutor TTS en `movil/tts-prueba/dist/Spotisaver-Voz-Prueba.apk`. Su codigo y las instrucciones para reconstruirlo estan en `movil/tts-prueba/README.md`. Esta prueba de voz no incluye aun la radio ni el descargador movil.

Para generar el APK se necesita Linux o WSL2. En Windows, [Buildozer recomienda compilar desde el sistema de archivos de WSL](https://buildozer.readthedocs.io/en/latest/installation/). Copia el proyecto a WSL y ejecuta desde alli:

```bash
cd ~/mp3/movil
buildozer android debug
```

El APK resultante aparecera en `movil/bin/`. Esta base movil aun necesita una prueba real en un telefono Android y una opcion para exportar las descargas fuera del almacenamiento privado de la app.

Para probar solo los primeros 3:

```powershell
.\pc\run.ps1 "URL_DE_TU_PLAYLIST" -Kind mp3 -Limit 3
```

Si la playlist requiere sesion, exporta cookies en formato `cookies.txt` y pasalas asi:

```powershell
.\pc\run.ps1 "URL_DE_TU_PLAYLIST" -Kind mp3 -Cookies "C:\ruta\cookies.txt"
```

## Salida

Los archivos quedan asi:

```text
downloads/
  Nombre de la playlist/
    01 - Cancion [id].mp3
    02 - Otra cancion [id].mp3
```
