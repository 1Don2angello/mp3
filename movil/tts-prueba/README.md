# Prueba de voz TTS en Android

APK mínimo para comprobar la voz del locutor en un teléfono antes de integrarla con la música. Permite editar una frase, escucharla con la voz española de Android y detenerla. La interfaz sigue el boceto blanco y negro tipo papel. No descarga ni reproduce canciones.

## Compilar en Windows

Requiere Android SDK con Build Tools y una JDK disponible en `PATH`.

```powershell
.\movil\tts-prueba\build-apk.ps1
```

El archivo generado queda en `movil/tts-prueba/dist/Spotisaver-Voz-Prueba.apk`. El script crea una firma de depuración local en `.debug/`, excluida de Git. Esta firma es solo para pruebas.

## Probar con un teléfono conectado por ADB

```powershell
adb install -r .\movil\tts-prueba\dist\Spotisaver-Voz-Prueba.apk
adb shell am start -n org.spotisaver.ttsprueba/.MainActivity
```

En la pantalla, edita el texto si quieres y pulsa **Escuchar voz**. Si Android no tiene una voz española instalada, la app lo indicará en lugar de intentar hablar.
