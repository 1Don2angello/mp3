# Spotisaver Android · fase 2

APK nativo de prueba basado en las cuatro pantallas del mockup: Inicio, Sonando, Cola y Biblioteca. Permite elegir uno o varios archivos de audio del teléfono, reproducirlos en orden, pausar, avanzar, retroceder y buscar dentro de la canción. El locutor TTS se puede encender o apagar; cuando está encendido, presenta el siguiente tema antes de que empiece la música. Puedes marcar favoritas en Sonando; Biblioteca muestra las favoritas y las últimas escuchas, incluidos los saltos y temas terminados.

La Biblioteca y la cola recuerdan los archivos elegidos entre aperturas mediante permisos de acceso a sus ubicaciones. La reproducción no empieza sola al abrir la app: pulsa Reproducir para continuar. Si eliges un archivo con el selector de Android, Spotisaver no lo copia ni lo borra. Si compartes un audio desde Telegram u otra app, Spotisaver guarda una copia privada para poder reproducirla después; **Olvidar biblioteca** elimina esas copias y vacía la cola, pero deja intactos los archivos originales. Esta fase no usa internet, no descarga canciones y no incluye aún el algoritmo de gustos ni la biblioteca automática.

## Compilar e instalar

Requiere Java y Android SDK con Build Tools en Windows.

```powershell
.\movil\app\build-apk.ps1
```

El APK queda en `movil/app/dist/Spotisaver-Fase-2.apk`. Usa una firma local de depuración para pruebas.

```powershell
adb install -r .\movil\app\dist\Spotisaver-Fase-2.apk
adb shell am start -n org.spotisaver.app/.MainActivity
```

En Inicio, pulsa **Importar carpeta de Telegram** y elige **moto g24 power → Music → Telegram**. La app agrega los audios de esa carpeta a Biblioteca de una sola vez, sin copiarlos ni poner todos en la cola. También puedes elegir archivos sueltos o abrir un audio en Telegram, usar **Compartir** y elegir **Spotisaver**. En Sonando, activa el locutor o marca la canción como favorita. En Cola puedes tocar cualquier canción o vaciar la selección; esto no elimina los archivos del teléfono. Biblioteca muestra tus favoritas y un historial local de hasta 100 eventos (los 12 más recientes en pantalla), que puedes borrar por separado.

El botón **Ver mis playlists públicas** abre `https://www.youtube.com/@engelcouoh9272/playlists` en el navegador o la app de YouTube. Spotisaver no pide inicio de sesión; esta versión todavía no incorpora las listas al reproductor.

La reproducción depende de que la app siga abierta. El servicio de audio para reproducción persistente y controles de pantalla bloqueada corresponde a una fase posterior.
