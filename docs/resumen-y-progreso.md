# Spotisaver: resumen y progreso

Actualizado el 25 de noviembre de 2026. Spotisaver busca convertirse en un reproductor MP3 para PC y Android con una radio personal: partir de una canción o playlist pública, escuchar online, aprender de favoritas, saltos y escuchas completas, y usar un locutor TTS opcional. El algoritmo musical debe seguir activo aunque el locutor esté apagado.

## Objetivo del producto

- **Modo MP3:** reproducir archivos guardados por el usuario, con biblioteca, cola, favoritas e historial.
- **Modo radio:** preparar una cola continua según los gustos del usuario. El locutor TTS presenta canciones solo si se activa.
- **Almacenamiento:** conservar lo guardado manualmente y las favoritas; limitar y limpiar el audio temporal, incluidos temas saltados, ya escuchados o que llevan tiempo sin sonar.
- **Origen de gustos:** usar playlists o canciones públicas como punto de partida. El canal de prueba es [@engelcouoh9272](https://www.youtube.com/@engelcouoh9272/playlists). El inicio de sesión con Google no es necesario para ver ese canal público; una futura consulta dinámica mediante YouTube Data API sí requiere una clave de aplicación.
- **Diseño:** blanco y negro, estilo papel, con Inicio, Sonando, Cola y Biblioteca. El [mockup](../movil/mockups/index.html) muestra la dirección visual.

## Organización del proyecto

| Carpeta | Papel actual |
| --- | --- |
| `motor/` | Metadatos y descargas Python; coordinación de muestras de audio online. |
| `pc/` | Interfaz Tkinter, reproducción de muestras con FFplay y compilación del EXE. |
| `movil/app/` | APK nativo Android en Java, compilable en Windows. Es la app que se instala y prueba ahora. |
| `movil/tts-prueba/` | APK independiente usado para validar la voz TTS de Android. |
| `movil/main.py` | Prototipo Kivy que usa el motor Python; todavía no se ha compilado ni probado como APK. |
| `docs/frases-locutor-radio.md` | Frases de referencia del locutor para adaptar más adelante. |

La app Java de Android todavía no comparte en tiempo de ejecución el motor Python de PC. Los cambios del motor no aparecen automáticamente en el APK.

## Funciones comprobadas

### PC

El EXE permite cargar un enlace, distinguir playlist, canción o coincidencia sugerida, limpiar la selección, descargar en los formatos admitidos y escuchar una muestra online de 20 segundos antes de descargar. Esa muestra usa FFplay y se probó con un video público. Spotify se usa como referencia de metadatos; el programa no toma audio de Spotify.

### Android

La fase 0 validó TTS en español de México en el teléfono `moto g24 power`. La fase 1 añadió reproducción de MP3 locales, controles y locutor opcional. La fase 2 añadió cola persistente, favoritas, historial de temas iniciados, terminados y saltados, importación de audio compartido y selección de una carpeta completa.

En el teléfono se comprobó que `Music/Telegram` se puede seleccionar de una vez: **279 audios** aparecieron en Biblioteca sin copiarlos ni agregarlos todos a la cola. La búsqueda por nombre filtró esa biblioteca. También se probaron la restauración de la cola, favoritas, historial, un salto y una importación de audio compartido mediante Android. Compartir desde la interfaz de Telegram queda por probar directamente con el usuario.

El APK que se está construyendo ahora es `movil/app/dist/Spotisaver-Fase-3.apk`; el script es `movil/app/build-apk.ps1`. La firma es local de depuración.

## Fase 3 en curso: playlists y radio online

El motor de PC identificó **9 playlists públicas** en el canal de prueba. El APK ya muestra esos nueve títulos como catálogo inicial y ofrece actualizar el catálogo mediante una clave de YouTube Data API introducida en el teléfono. Esta actualización no se ha probado porque todavía no hay una clave configurada. [YouTube distingue la clave de aplicación para datos públicos del inicio de sesión OAuth para datos privados](https://developers.google.com/youtube/data/guides/authentication).

La primera integración del [reproductor incrustado de YouTube](https://developers.google.com/youtube/iframe_api_reference) aparece **en negro en el teléfono**, incluso tras cambiar la forma de cargarlo en WebView. La fase 3 no está terminada: hay que resolver la reproducción visible, probar que una playlist avanza y definir los controles cuando la app está en segundo plano. El APK de prueba de esta fase no debe presentarse como una radio online funcional todavía. El botón que abre el canal en el navegador sí funcionó.

## Modelo de voz propuesto

El usuario propuso [XTTS v2 Argentine Spanish de marianbasti](https://huggingface.co/marianbasti/XTTS-v2-argentinian-spanish). Es un modelo de clonación de voz con acento argentino; su repositorio ocupa aproximadamente **5,61 GB**, el ejemplo de uso ejecuta el modelo con CUDA y la página indica que no está desplegado por un proveedor de inferencia. También muestra una advertencia de lectura de `config.json`. Por tamaño y requisitos, no se ha integrado al APK. La voz TTS nativa de Android sigue siendo el locutor funcional; XTTS queda como opción para evaluar en PC o en un servicio de generación de voz.

## Siguientes pasos

1. Resolver el reproductor online de fase 3 y probarlo con una playlist pública real en el teléfono. Mantener una salida al navegador si el WebView de ese dispositivo no reproduce.
2. Probar la actualización de playlists con una clave API de aplicación, sin pedir inicio de sesión al oyente. Evitar mostrar o registrar la clave.
3. Integrar el modo radio con la cola y la voz opcional, manteniendo separados los MP3 locales y el contenido de YouTube.
4. Implementar la selección que aprenda de favoritas, saltos y escuchas completas.
5. Definir un límite de almacenamiento temporal y la limpieza automática sin borrar MP3 guardados manualmente.

El detalle de estados por etapa está en [fases del APK](fases-apk.md).
