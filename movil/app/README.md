# Spotisaver Android · fase 1

APK nativo de prueba basado en las cuatro pantallas del mockup: Inicio, Sonando, Cola y Biblioteca. Permite elegir uno o varios archivos de audio del teléfono, reproducirlos en orden, pausar, avanzar, retroceder y buscar dentro de la canción. El locutor TTS se puede encender o apagar; cuando está encendido, presenta el siguiente tema antes de que empiece la música.

La Biblioteca recuerda los archivos elegidos entre aperturas mediante permisos de acceso a sus ubicaciones. Desde ella puedes volver a agregar temas a la cola. Los archivos no se copian ni se borran, incluso si vacías la cola o la biblioteca. La cola solo dura mientras la app está abierta. Esta fase no usa internet, no descarga canciones y no incluye aún el algoritmo de gustos ni la biblioteca automática.

## Compilar e instalar

Requiere Java y Android SDK con Build Tools en Windows.

```powershell
.\movil\app\build-apk.ps1
```

El APK queda en `movil/app/dist/Spotisaver-Fase-1.apk`. Usa una firma local de depuración para pruebas.

```powershell
adb install -r .\movil\app\dist\Spotisaver-Fase-1.apk
adb shell am start -n org.spotisaver.app/.MainActivity
```

En Inicio, pulsa **Elegir canciones del teléfono** y selecciona archivos de audio. En Sonando, activa el locutor para que anuncie el siguiente tema. En Cola puedes tocar cualquier canción o vaciar la selección; esto no elimina los archivos del teléfono.

La reproducción depende de que la app siga abierta. El servicio de audio para reproducción persistente y controles de pantalla bloqueada corresponde a una fase posterior.
