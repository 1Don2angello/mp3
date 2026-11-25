# Fases del APK Spotisaver

El [mockup móvil](../movil/mockups/index.html) guía la interfaz. Cada fase debe producir un APK instalable y una prueba en el teléfono antes de avanzar.

| Fase | Resultado | Estado |
| --- | --- | --- |
| 0 · Voz | Probar TTS español en Android | Terminada: `movil/tts-prueba/` |
| 1 · MP3 local | Inicio, Sonando, Cola y Biblioteca de archivos elegidos; reproducción y locutor opcional | Terminada: `movil/app/` |
| 2 · Biblioteca ampliada | Favoritos, historial, cola persistente e importación de carpeta o audio compartido desde Telegram; acceso al canal público | Terminada: `movil/app/` |
| 3 · Radio online | Escucha online de una fuente compatible y cola continua, con controles de fondo | Pendiente |
| 4 · Personalización | Aprender de favoritos, saltos y temas escuchados; voz opcional sin cambiar el algoritmo | Pendiente |
| 5 · Almacenamiento temporal | Límite de caché y limpieza de audio temporal; nunca borrar MP3 guardados manualmente | Pendiente |

La fase 1 trabaja con audio local para probar el reproductor y la voz juntos. El motor Python de PC y la interfaz Kivy experimental siguen separados; todavía no hay un APK que empaquete ese motor. La fuente online, las condiciones de uso y la estrategia de almacenamiento se definirán antes de implementar las fases 3 y 5.
