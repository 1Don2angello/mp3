package org.spotisaver.app;

import android.app.Activity;
import android.content.Intent;
import android.content.UriPermission;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.provider.DocumentsContract;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.ConsoleMessage;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.TextView;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Locale;

public class MainActivity extends Activity implements TextToSpeech.OnInitListener {
    private static final int PICK_AUDIO = 7;
    private static final int PICK_AUDIO_FOLDER = 8;
    private static final String PUBLIC_PLAYLISTS = "https://www.youtube.com/@engelcouoh9272/playlists";
    private static final String CHANNEL_ID = "UCN-DQJS8p0yJPSnS-amAi9w";
    private static final int INK = Color.rgb(23, 23, 23);
    private static final int PAPER = Color.rgb(250, 249, 245);
    private static final int MUTED = Color.rgb(86, 86, 86);
    private final ArrayList<Track> tracks = new ArrayList<>();
    private final ArrayList<Track> library = new ArrayList<>();
    private final ArrayList<ListeningEvent> history = new ArrayList<>();
    private final ArrayList<PublicPlaylist> publicPlaylists = new ArrayList<>();
    private final HashSet<String> favorites = new HashSet<>();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private MediaPlayer player;
    private TextToSpeech tts;
    private boolean voiceReady;
    private boolean voiceOn;
    private boolean preparing;
    private boolean announcing;
    private int current = -1;
    private int playbackToken;
    private int page;
    private String status = "Elige canciones del teléfono para empezar.";
    private String libraryQuery = "";
    private String selectedPlaylistId;
    private String selectedPlaylistTitle;
    private String radioStatus = "Catálogo público de prueba. Elige una playlist para escucharla online.";
    private WebView radioWebView;
    private LinearLayout content;
    private LinearLayout nav;
    private SeekBar seekBar;
    private TextView timeLabel;

    private static class Track {
        final Uri uri;
        final String title;
        Track(Uri uri, String title) { this.uri = uri; this.title = title; }
    }

    private static class ListeningEvent {
        final String title;
        final String kind;
        final long at;
        ListeningEvent(String title, String kind, long at) {
            this.title = title;
            this.kind = kind;
            this.at = at;
        }
    }

    private static class PublicPlaylist {
        final String id;
        final String title;
        PublicPlaylist(String id, String title) { this.id = id; this.title = title; }
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private GradientDrawable box(boolean dark) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(dark ? INK : PAPER);
        shape.setStroke(dp(1), INK);
        return shape;
    }

    private TextView label(String value, int size, boolean serif, boolean bold) {
        TextView result = new TextView(this);
        result.setText(value);
        result.setTextColor(INK);
        result.setTextSize(size);
        result.setTypeface(serif ? Typeface.SERIF : Typeface.MONOSPACE, bold ? Typeface.BOLD : Typeface.NORMAL);
        return result;
    }

    private void addText(String value, int size, boolean serif, boolean bold, int bottom) {
        TextView view = label(value, size, serif, bold);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.bottomMargin = dp(bottom);
        content.addView(view, params);
    }

    private Button button(String text, boolean dark, Runnable action) {
        Button result = new Button(this);
        result.setText(text);
        result.setTextSize(12);
        result.setAllCaps(false);
        result.setTextColor(dark ? PAPER : INK);
        result.setBackground(box(dark));
        result.setOnClickListener(v -> action.run());
        return result;
    }

    private void addButton(String text, boolean dark, Runnable action, int bottom) {
        Button result = button(text, dark, action);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(48));
        params.bottomMargin = dp(bottom);
        content.addView(result, params);
    }

    private void rule() {
        View line = new View(this);
        line.setBackgroundColor(INK);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(1));
        params.bottomMargin = dp(16);
        content.addView(line, params);
    }

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(INK);
        getWindow().setNavigationBarColor(INK);
        voiceOn = getPreferences(MODE_PRIVATE).getBoolean("locutor", false);
        loadLibrary();
        loadQueue();
        loadFavorites();
        loadHistory();
        loadPublicPlaylists();
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(PAPER);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(22), dp(26), dp(22), dp(12));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        nav = new LinearLayout(this);
        nav.setPadding(dp(10), dp(8), dp(10), dp(10));
        root.addView(nav, new LinearLayout.LayoutParams(-1, dp(62)));
        setContentView(root);
        tts = new TextToSpeech(this, this);
        handler.postDelayed(new Runnable() {
            @Override public void run() {
                updateProgress();
                handler.postDelayed(this, 500);
            }
        }, 500);
        render();
        handleSharedAudio(getIntent());
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleSharedAudio(intent);
    }

    private void render() {
        if (radioWebView != null) {
            radioWebView.stopLoading();
            radioWebView.destroy();
            radioWebView = null;
        }
        content.removeAllViews();
        nav.removeAllViews();
        seekBar = null;
        timeLabel = null;
        addText("SPOTISAVER  /  PAPEL FM", 13, false, true, 25);
        rule();
        if (page == 0) renderHome();
        else if (page == 1) renderPlayer();
        else if (page == 2) renderQueue();
        else if (page == 3) renderLibrary();
        else renderRadio();
        for (int index = 0; index < 4; index++) {
            final int target = index;
            String name = index == 0 ? "Inicio" : index == 1 ? "Sonando" : index == 2 ? "Cola" : "Biblioteca";
            Button tab = button(name, page == index, () -> { page = target; render(); });
            tab.setTextSize(10);
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, -1, 1);
            params.leftMargin = dp(2);
            params.rightMargin = dp(2);
            nav.addView(tab, params);
        }
    }

    private void renderHome() {
        addText("Tu música.\nTu estación.", 38, true, false, 15);
        addText("FASE 2  ·  TU MÚSICA LOCAL", 12, false, true, 15);
        addText("Elige MP3 del teléfono. La cola los reproduce en orden y puedes encender la voz del locutor antes de cada tema.", 15, false, false, 15);
        addText("Telegram: busca Music / Telegram en el selector, o comparte un audio directamente a Spotisaver.", 12, false, false, 20);
        addButton("Elegir canciones del teléfono", true, this::pickAudio, 18);
        addButton("Importar carpeta de Telegram", false, this::pickAudioFolder, 12);
        addButton("Mi radio online →", false, () -> { page = 4; render(); }, 12);
        addButton("Ver canal en YouTube", false, this::openPublicPlaylists, 18);
        rule();
        addText("TU SESIÓN", 12, false, true, 8);
        addText(tracks.size() + " canción(es) en cola", 23, true, false, 9);
        addText(status, 13, false, false, 20);
        if (current >= 0) addButton("Ir a Sonando →", false, () -> { page = 1; render(); }, 12);
        addText("La cola, tus favoritas y el historial se guardan al cerrar la app. Reanuda la música con Reproducir.", 12, false, false, 0);
    }

    private void renderPlayer() {
        addText("Ahora suena.", 38, true, false, 12);
        addText(current < 0 ? "Ninguna canción elegida" : tracks.get(current).title, 26, true, false, 14);
        addText(current < 0 ? "Elige canciones en Inicio." : "PISTA " + (current + 1) + " / " + tracks.size(), 12, false, true, 20);
        seekBar = new SeekBar(this);
        seekBar.setEnabled(player != null && !preparing && !announcing);
        seekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar bar, int value, boolean fromUser) {
                if (fromUser && player != null) player.seekTo(value);
            }
            @Override public void onStartTrackingTouch(SeekBar bar) {}
            @Override public void onStopTrackingTouch(SeekBar bar) {}
        });
        content.addView(seekBar, new LinearLayout.LayoutParams(-1, dp(42)));
        timeLabel = label("0:00 / 0:00", 12, false, false);
        LinearLayout.LayoutParams timeParams = new LinearLayout.LayoutParams(-1, -2);
        timeParams.bottomMargin = dp(20);
        content.addView(timeLabel, timeParams);
        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        Button back = button("|◀", false, () -> move(-1));
        Button play = button(player != null && player.isPlaying() ? "Pausar" : "Reproducir", true, this::togglePlayback);
        Button next = button("▶|", false, () -> move(1));
        controls.addView(back, new LinearLayout.LayoutParams(0, dp(50), 1));
        controls.addView(play, new LinearLayout.LayoutParams(0, dp(50), 2));
        controls.addView(next, new LinearLayout.LayoutParams(0, dp(50), 1));
        LinearLayout.LayoutParams row = new LinearLayout.LayoutParams(-1, -2);
        row.bottomMargin = dp(20);
        content.addView(controls, row);
        if (current >= 0) {
            Track track = tracks.get(current);
            boolean favorite = favorites.contains(track.uri.toString());
            addButton(favorite ? "♥ Favorita · quitar" : "♡ Marcar favorita", false, () -> toggleFavorite(track), 15);
        }
        rule();
        addText("LOCUTOR", 12, false, true, 8);
        addButton(voiceOn ? "Voz encendida · tocar para apagar" : "Voz apagada · tocar para encender", false, () -> {
            voiceOn = !voiceOn;
            getPreferences(MODE_PRIVATE).edit().putBoolean("locutor", voiceOn).apply();
            if (!voiceOn && announcing && tts != null) {
                tts.stop();
                announcing = false;
                startCurrent();
            }
            render();
        }, 10);
        addText("La voz presenta el siguiente tema. Apagarla no detiene la música.", 12, false, false, 17);
        addText(status, 13, false, false, 0);
        updateProgress();
    }

    private void renderQueue() {
        addText("Lo que sigue.", 38, true, false, 13);
        addText("COLA LOCAL  /  " + tracks.size() + " TEMAS", 12, false, true, 20);
        addButton("Agregar más canciones", true, this::pickAudio, 16);
        for (int i = 0; i < tracks.size(); i++) {
            final int position = i;
            String prefix = i == current ? "▶ " : String.format(Locale.ROOT, "%02d  ", i + 1);
            addButton(prefix + tracks.get(i).title, i == current, () -> playAt(position), 6);
        }
        if (!tracks.isEmpty()) addButton("Vaciar cola", false, () -> {
            releasePlayer();
            if (tts != null) tts.stop();
            tracks.clear();
            current = -1;
            saveQueue();
            status = "Cola vacía. Tus MP3 siguen en el teléfono.";
            render();
        }, 10);
        if (tracks.isEmpty()) addText("Todavía no hay canciones. Agrégalas desde tu teléfono.", 15, false, false, 0);
    }

    private void renderLibrary() {
        addText("Tu biblioteca.", 38, true, false, 13);
        addText("ARCHIVOS ELEGIDOS  /  " + library.size(), 12, false, true, 15);
        addText("Tus archivos siguen en su lugar. Aquí puedes volver a agregarlos a la cola y revisar tus gustos.", 13, false, false, 18);
        addButton("Agregar archivos", true, this::pickAudio, 17);
        addButton("Importar carpeta completa", false, this::pickAudioFolder, 17);
        addText(status, 12, false, false, 15);
        addText("FAVORITAS  /  " + favorites.size(), 12, false, true, 8);
        int visibleFavorites = 0;
        for (Track track : library) {
            if (!favorites.contains(track.uri.toString())) continue;
            visibleFavorites++;
            addButton("♥ " + track.title, false, () -> {
                addToQueue(track);
                status = "Agregada a la cola: " + track.title;
                page = 2;
                render();
            }, 6);
        }
        if (visibleFavorites == 0) addText("Todavía no marcas favoritas.", 13, false, false, 15);
        rule();
        addText("BUSCAR EN TUS ARCHIVOS", 12, false, true, 8);
        EditText search = new EditText(this);
        search.setSingleLine(true);
        search.setTextSize(15);
        search.setHint("Nombre de canción...");
        search.setText(libraryQuery);
        LinearLayout.LayoutParams searchParams = new LinearLayout.LayoutParams(-1, dp(48));
        searchParams.bottomMargin = dp(12);
        content.addView(search, searchParams);
        LinearLayout results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        content.addView(results, new LinearLayout.LayoutParams(-1, -2));
        fillLibraryResults(results);
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence value, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence value, int start, int before, int count) {
                libraryQuery = value.toString();
                fillLibraryResults(results);
            }
            @Override public void afterTextChanged(Editable value) {}
        });
        rule();
        addText("HISTORIAL RECIENTE", 12, false, true, 8);
        if (history.isEmpty()) addText("Aún no hay escuchas registradas.", 13, false, false, 12);
        for (int i = history.size() - 1, shown = 0; i >= 0 && shown < 12; i--, shown++) {
            ListeningEvent event = history.get(i);
            addText(event.kind + " · " + event.title, 12, false, false, 7);
        }
        if (!history.isEmpty()) addButton("Borrar historial", false, () -> {
            history.clear();
            saveHistory();
            render();
        }, 10);
        if (!library.isEmpty()) addButton("Olvidar biblioteca", false, () -> {
            releasePlayer();
            if (tts != null) tts.stop();
            for (Track track : library) deleteImportedFile(track);
            library.clear();
            tracks.clear();
            current = -1;
            favorites.clear();
            saveLibrary();
            saveQueue();
            saveFavorites();
            for (UriPermission permission : getContentResolver().getPersistedUriPermissions()) {
                try { getContentResolver().releasePersistableUriPermission(permission.getUri(), Intent.FLAG_GRANT_READ_URI_PERMISSION); }
                catch (SecurityException ignored) {}
            }
            status = "Biblioteca vacía. Los MP3 originales siguen en el teléfono.";
            render();
        }, 8);
    }

    private void fillLibraryResults(LinearLayout results) {
        results.removeAllViews();
        ArrayList<Track> matches = new ArrayList<>();
        String query = libraryQuery.trim().toLowerCase(Locale.ROOT);
        for (Track track : library) {
            if (track.title.toLowerCase(Locale.ROOT).contains(query)) matches.add(track);
        }
        matches.sort((a, b) -> a.title.compareToIgnoreCase(b.title));
        TextView count = label("MOSTRANDO " + Math.min(40, matches.size()) + " DE " + matches.size(), 11, false, true);
        LinearLayout.LayoutParams countParams = new LinearLayout.LayoutParams(-1, -2);
        countParams.bottomMargin = dp(8);
        results.addView(count, countParams);
        for (int i = 0; i < Math.min(40, matches.size()); i++) {
            Track track = matches.get(i);
            Button row = button("+ " + track.title, false, () -> {
                addToQueue(track);
                status = "Agregada a la cola: " + track.title;
                page = 2;
                render();
            });
            LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(-1, dp(48));
            rowParams.bottomMargin = dp(6);
            results.addView(row, rowParams);
        }
        if (matches.isEmpty()) {
            TextView empty = label(library.isEmpty() ? "La biblioteca está vacía." : "No encontré canciones con ese nombre.", 13, false, false);
            results.addView(empty, new LinearLayout.LayoutParams(-1, -2));
        }
    }

    private void renderRadio() {
        addText("Radio online.", 38, true, false, 12);
        addText("PLAYLISTS PÚBLICAS  /  @engelcouoh9272", 12, false, true, 12);
        addText("Escucha una playlist con el reproductor de YouTube. No necesitas iniciar sesión en Spotisaver.", 13, false, false, 17);
        if (selectedPlaylistId != null) {
            addText("SONANDO ONLINE  /  " + selectedPlaylistTitle, 14, false, true, 9);
            radioWebView = new WebView(this);
            radioWebView.setBackgroundColor(INK);
            radioWebView.getSettings().setJavaScriptEnabled(true);
            radioWebView.getSettings().setDomStorageEnabled(true);
            radioWebView.getSettings().setMediaPlaybackRequiresUserGesture(true);
            radioWebView.setWebChromeClient(new WebChromeClient() {
                @Override public boolean onConsoleMessage(ConsoleMessage message) {
                    Log.d("SpotisaverRadio", message.message());
                    return true;
                }
            });
            radioWebView.setWebViewClient(new WebViewClient() {
                @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                    Log.e("SpotisaverRadio", "WebView " + request.getUrl() + ": " + error.getDescription());
                }
                @Override public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse response) {
                    Log.e("SpotisaverRadio", "HTTP " + response.getStatusCode() + " " + request.getUrl());
                }
            });
            LinearLayout.LayoutParams webParams = new LinearLayout.LayoutParams(-1, dp(240));
            webParams.bottomMargin = dp(10);
            content.addView(radioWebView, webParams);
            String embed = "https://www.youtube.com/embed?listType=playlist&list=" + selectedPlaylistId + "&playsinline=1";
            String html = "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>" +
                "<style>html,body{margin:0;width:100%;height:100%;background:#171717}iframe{width:100%;height:100%;border:0}</style>" +
                "</head><body><iframe src='" + embed.replace("&", "&amp;") +
                "' allow='autoplay; encrypted-media; picture-in-picture' allowfullscreen></iframe></body></html>";
            radioWebView.loadDataWithBaseURL("https://org.spotisaver.app/", html, "text/html", "UTF-8", null);
            addText("Toca Play en el reproductor. La playlist avanza con los controles de YouTube.", 12, false, false, 10);
            addButton("Cerrar reproductor", false, () -> {
                selectedPlaylistId = null;
                selectedPlaylistTitle = null;
                render();
            }, 15);
        }
        addText(radioStatus, 12, false, false, 13);
        for (PublicPlaylist playlist : publicPlaylists) {
            addButton("▶ " + playlist.title, false, () -> {
                if (player != null && player.isPlaying()) { player.pause(); status = "MP3 local en pausa."; }
                selectedPlaylistId = playlist.id;
                selectedPlaylistTitle = playlist.title;
                render();
            }, 6);
        }
        rule();
        addText("ACTUALIZAR EL CATÁLOGO", 12, false, true, 8);
        addText("La lista inicial se confirmó el 25 de noviembre de 2026. Para traer cambios del canal, introduce una clave de YouTube Data API de esta app. Tu cuenta de Google no se conecta al reproductor.", 12, false, false, 10);
        EditText key = new EditText(this);
        key.setSingleLine(true);
        key.setTextSize(13);
        key.setHint("Clave API (opcional)");
        key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        key.setText(getPreferences(MODE_PRIVATE).getString("youtubeApiKey", ""));
        LinearLayout.LayoutParams keyParams = new LinearLayout.LayoutParams(-1, dp(48));
        keyParams.bottomMargin = dp(10);
        content.addView(key, keyParams);
        addButton("Actualizar playlists públicas", true, () -> {
            String value = key.getText().toString().trim();
            if (value.isEmpty()) { radioStatus = "Escribe una clave API para actualizar la lista."; render(); return; }
            getPreferences(MODE_PRIVATE).edit().putString("youtubeApiKey", value).apply();
            refreshPublicPlaylists(value);
        }, 12);
        addButton("Abrir canal en YouTube", false, this::openPublicPlaylists, 0);
    }

    private void pickAudio() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("audio/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        startActivityForResult(intent, PICK_AUDIO);
    }

    private void pickAudioFolder() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(intent, PICK_AUDIO_FOLDER);
    }

    private void openPublicPlaylists() {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(PUBLIC_PLAYLISTS))); }
        catch (Exception error) { status = "No encontré un navegador para abrir las playlists."; render(); }
    }

    private void loadPublicPlaylists() {
        String stored = getPreferences(MODE_PRIVATE).getString("publicPlaylists", "");
        if (!stored.isEmpty()) {
            try {
                JSONArray items = new JSONArray(stored);
                for (int i = 0; i < items.length(); i++) {
                    JSONObject item = items.getJSONObject(i);
                    publicPlaylists.add(new PublicPlaylist(item.getString("id"), item.getString("title")));
                }
            } catch (Exception ignored) { publicPlaylists.clear(); }
        }
        if (!publicPlaylists.isEmpty()) {
            radioStatus = publicPlaylists.size() + " playlists públicas guardadas de la última actualización.";
            return;
        }
        publicPlaylists.add(new PublicPlaylist("PLcEvheUNWQII", "titkok 2027"));
        publicPlaylists.add(new PublicPlaylist("PLTv6FFCAZpFA", "corridos onichan"));
        publicPlaylists.add(new PublicPlaylist("PLFb5HncgHkow", "Tik toks song 2026"));
        publicPlaylists.add(new PublicPlaylist("PLCkOn60wZua793aOjI4bpn_o23lbWoy-f", "TikTok Songs"));
        publicPlaylists.add(new PublicPlaylist("PLCkOn60wZua4F89R7007lXvPBjMCdTLeL", "^o^"));
        publicPlaylists.add(new PublicPlaylist("PLCkOn60wZua671_X-BLDJXhD4ULJlme_W", "phonk"));
        publicPlaylists.add(new PublicPlaylist("PLCkOn60wZua6HFCrYXPIFkQLmzIz_zb21", "Arduino proyecto plantas de sol"));
        publicPlaylists.add(new PublicPlaylist("PLCkOn60wZua4sec3QqyndOeNzJ7CGbbWe", "Música viejita"));
        publicPlaylists.add(new PublicPlaylist("PLCkOn60wZua5iMLJEQNAU9NyEh_Cj1CVt", "Música para Meditar"));
    }

    private void savePublicPlaylists() {
        JSONArray items = new JSONArray();
        for (PublicPlaylist playlist : publicPlaylists) {
            JSONObject item = new JSONObject();
            try { item.put("id", playlist.id); item.put("title", playlist.title); items.put(item); }
            catch (Exception ignored) {}
        }
        getPreferences(MODE_PRIVATE).edit().putString("publicPlaylists", items.toString()).apply();
    }

    private void refreshPublicPlaylists(String apiKey) {
        radioStatus = "Consultando playlists públicas...";
        render();
        new Thread(() -> {
            ArrayList<PublicPlaylist> fresh = new ArrayList<>();
            String pageToken = "";
            String error = null;
            try {
                for (int pageNumber = 0; pageNumber < 5; pageNumber++) {
                    Uri.Builder address = Uri.parse("https://www.googleapis.com/youtube/v3/playlists").buildUpon()
                        .appendQueryParameter("part", "snippet")
                        .appendQueryParameter("channelId", CHANNEL_ID)
                        .appendQueryParameter("maxResults", "50")
                        .appendQueryParameter("key", apiKey);
                    if (!pageToken.isEmpty()) address.appendQueryParameter("pageToken", pageToken);
                    HttpURLConnection connection = (HttpURLConnection) new URL(address.build().toString()).openConnection();
                    connection.setConnectTimeout(10000);
                    connection.setReadTimeout(15000);
                    try {
                        int code = connection.getResponseCode();
                        if (code != 200) throw new IllegalStateException("HTTP " + code);
                        StringBuilder body = new StringBuilder();
                        try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), "UTF-8"))) {
                            String line;
                            while ((line = reader.readLine()) != null) body.append(line);
                        }
                        JSONObject response = new JSONObject(body.toString());
                        JSONArray items = response.optJSONArray("items");
                        if (items != null) for (int i = 0; i < items.length(); i++) {
                            JSONObject item = items.getJSONObject(i);
                            String id = item.optString("id");
                            JSONObject snippet = item.optJSONObject("snippet");
                            String title = snippet == null ? "" : snippet.optString("title");
                            if (id.matches("[A-Za-z0-9_-]{10,}") && !title.isEmpty()) fresh.add(new PublicPlaylist(id, title));
                        }
                        pageToken = response.optString("nextPageToken");
                        if (pageToken.isEmpty()) break;
                    } finally { connection.disconnect(); }
                }
            } catch (Exception failure) { error = failure.getMessage(); }
            final String resultError = error;
            runOnUiThread(() -> {
                if (resultError == null) {
                    publicPlaylists.clear();
                    publicPlaylists.addAll(fresh);
                    savePublicPlaylists();
                    radioStatus = fresh.size() + " playlists públicas actualizadas.";
                } else radioStatus = "No se pudo actualizar (" + resultError + "). Revisa la clave API y la conexión.";
                render();
            });
        }, "spotisaver-playlists").start();
    }

    private void handleSharedAudio(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        if (!Intent.ACTION_SEND.equals(action) && !Intent.ACTION_SEND_MULTIPLE.equals(action)) return;
        int imported = 0;
        if (Intent.ACTION_SEND_MULTIPLE.equals(action)) {
            ArrayList<Uri> shared = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
            if (shared != null) for (Uri uri : shared) if (importSharedTrack(uri)) imported++;
        } else {
            Uri shared = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            if (importSharedTrack(shared)) imported++;
        }
        if (imported > 0) {
            saveLibrary();
            saveQueue();
            status = imported + " audio(s) importado(s) de Telegram u otra app.";
            page = 2;
        } else status = "No se pudo importar el audio compartido.";
        render();
        intent.setAction(null); // Evita importar otra vez al recrear esta pantalla.
    }

    private boolean importSharedTrack(Uri source) {
        if (source == null) return false;
        File imports = new File(getFilesDir(), "imports");
        if (!imports.exists() && !imports.mkdirs()) return false;
        String title = source.getLastPathSegment();
        try (Cursor cursor = getContentResolver().query(source, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) title = cursor.getString(0);
        } catch (Exception ignored) {}
        if (title == null || title.trim().isEmpty()) title = "Audio compartido.mp3";
        String suffix = title.matches("(?i).*\\.[a-z0-9]{2,5}$")
            ? title.substring(title.lastIndexOf('.')) : ".audio";
        File copy = null;
        try {
            copy = File.createTempFile("spotisaver-", suffix, imports);
            try (InputStream input = getContentResolver().openInputStream(source);
                 FileOutputStream output = new FileOutputStream(copy)) {
                if (input == null) throw new IllegalStateException("Audio sin datos");
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            }
            Track track = new Track(Uri.fromFile(copy), title);
            library.add(track);
            addToQueue(track);
            return true;
        } catch (Exception ignored) {
            if (copy != null) copy.delete();
            return false;
        }
    }

    private void deleteImportedFile(Track track) {
        if (!"file".equals(track.uri.getScheme())) return;
        File file = new File(track.uri.getPath());
        File imports = new File(getFilesDir(), "imports");
        if (imports.equals(file.getParentFile())) file.delete();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null) return;
        if (requestCode == PICK_AUDIO_FOLDER) {
            importAudioFolder(data.getData());
            return;
        }
        if (requestCode != PICK_AUDIO) return;
        int before = tracks.size();
        if (data.getClipData() != null) {
            for (int i = 0; i < data.getClipData().getItemCount(); i++) addTrack(data.getClipData().getItemAt(i).getUri());
        } else if (data.getData() != null) addTrack(data.getData());
        saveLibrary();
        saveQueue();
        int added = tracks.size() - before;
        status = added + " canción(es) agregada(s).";
        if (current < 0 && added > 0) playAt(0);
        else render();
    }

    private void addTrack(Uri uri) {
        try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); }
        catch (SecurityException ignored) {}
        String title = uri.getLastPathSegment();
        try (Cursor cursor = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) title = cursor.getString(0);
        } catch (Exception ignored) {}
        if (title == null || title.trim().isEmpty()) title = "Canción sin título";
        Track track = new Track(uri, title);
        addToQueue(track);
        addToLibrary(track);
    }

    private void addToLibrary(Track track) {
        for (Track saved : library) if (saved.uri.equals(track.uri)) return;
        library.add(track);
    }

    private void importAudioFolder(Uri tree) {
        if (tree == null) return;
        try { getContentResolver().takePersistableUriPermission(tree, Intent.FLAG_GRANT_READ_URI_PERMISSION); }
        catch (SecurityException error) {
            status = "No se pudo conservar el acceso a esa carpeta.";
            render();
            return;
        }
        status = "Leyendo carpeta de música...";
        page = 3;
        render();
        new Thread(() -> {
            ArrayList<Track> found = scanAudioFolder(tree);
            runOnUiThread(() -> {
                int before = library.size();
                for (Track track : found) addToLibrary(track);
                saveLibrary();
                int added = library.size() - before;
                status = added > 0
                    ? added + " audio(s) agregados a Biblioteca. Busca uno para añadirlo a la cola."
                    : "Los audios de esta carpeta ya estaban en Biblioteca.";
                render();
            });
        }, "spotisaver-folder-scan").start();
    }

    private ArrayList<Track> scanAudioFolder(Uri tree) {
        ArrayList<Track> found = new ArrayList<>();
        ArrayList<String> pending = new ArrayList<>();
        pending.add(DocumentsContract.getTreeDocumentId(tree));
        String[] columns = {
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE
        };
        for (int position = 0; position < pending.size() && found.size() < 2000; position++) {
            Uri children = DocumentsContract.buildChildDocumentsUriUsingTree(tree, pending.get(position));
            try (Cursor cursor = getContentResolver().query(children, columns, null, null, null)) {
                if (cursor == null) continue;
                while (cursor.moveToNext() && found.size() < 2000) {
                    String id = cursor.getString(0);
                    String name = cursor.getString(1);
                    String mime = cursor.getString(2);
                    if (DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)) {
                        pending.add(id);
                    } else if ((mime != null && mime.startsWith("audio/")) ||
                        (name != null && name.matches("(?i).*\\.(mp3|m4a|aac|flac|wav|ogg|opus|wma)$"))) {
                        Uri document = DocumentsContract.buildDocumentUriUsingTree(tree, id);
                        found.add(new Track(document, name == null ? "Audio" : name));
                    }
                }
            } catch (Exception ignored) {}
        }
        return found;
    }

    private void addToQueue(Track track) {
        for (Track queued : tracks) if (queued.uri.equals(track.uri)) return;
        tracks.add(track);
        saveQueue();
    }

    private void saveQueue() {
        JSONArray items = new JSONArray();
        for (Track track : tracks) {
            JSONObject item = new JSONObject();
            try {
                item.put("uri", track.uri.toString());
                item.put("title", track.title);
                items.put(item);
            } catch (Exception ignored) {}
        }
        getPreferences(MODE_PRIVATE).edit()
            .putString("queue", items.toString())
            .putInt("current", current).apply();
    }

    private void loadQueue() {
        try {
            JSONArray items = new JSONArray(getPreferences(MODE_PRIVATE).getString("queue", "[]"));
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.getJSONObject(i);
                tracks.add(new Track(Uri.parse(item.getString("uri")), item.getString("title")));
            }
            int saved = getPreferences(MODE_PRIVATE).getInt("current", -1);
            current = saved >= 0 && saved < tracks.size() ? saved : -1;
            if (!tracks.isEmpty()) status = "Cola restaurada. Pulsa Reproducir para continuar.";
        } catch (Exception ignored) { tracks.clear(); current = -1; }
    }

    private void toggleFavorite(Track track) {
        String key = track.uri.toString();
        if (!favorites.add(key)) favorites.remove(key);
        saveFavorites();
        render();
    }

    private void saveFavorites() {
        JSONArray items = new JSONArray();
        for (String key : favorites) items.put(key);
        getPreferences(MODE_PRIVATE).edit().putString("favorites", items.toString()).apply();
    }

    private void loadFavorites() {
        try {
            JSONArray items = new JSONArray(getPreferences(MODE_PRIVATE).getString("favorites", "[]"));
            for (int i = 0; i < items.length(); i++) favorites.add(items.getString(i));
        } catch (Exception ignored) { favorites.clear(); }
    }

    private void recordEvent(String kind) {
        if (current < 0 || current >= tracks.size()) return;
        history.add(new ListeningEvent(tracks.get(current).title, kind, System.currentTimeMillis()));
        while (history.size() > 100) history.remove(0);
        saveHistory();
    }

    private void saveHistory() {
        JSONArray items = new JSONArray();
        for (ListeningEvent event : history) {
            JSONObject item = new JSONObject();
            try {
                item.put("title", event.title);
                item.put("kind", event.kind);
                item.put("at", event.at);
                items.put(item);
            } catch (Exception ignored) {}
        }
        getPreferences(MODE_PRIVATE).edit().putString("history", items.toString()).apply();
    }

    private void loadHistory() {
        try {
            JSONArray items = new JSONArray(getPreferences(MODE_PRIVATE).getString("history", "[]"));
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.getJSONObject(i);
                history.add(new ListeningEvent(item.getString("title"), item.getString("kind"), item.getLong("at")));
            }
        } catch (Exception ignored) { history.clear(); }
    }

    private void saveLibrary() {
        JSONArray items = new JSONArray();
        for (Track track : library) {
            JSONObject item = new JSONObject();
            try {
                item.put("uri", track.uri.toString());
                item.put("title", track.title);
                items.put(item);
            } catch (Exception ignored) {}
        }
        getPreferences(MODE_PRIVATE).edit().putString("library", items.toString()).apply();
    }

    private void loadLibrary() {
        String stored = getPreferences(MODE_PRIVATE).getString("library", "[]");
        try {
            JSONArray items = new JSONArray(stored);
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.getJSONObject(i);
                library.add(new Track(Uri.parse(item.getString("uri")), item.getString("title")));
            }
        } catch (Exception ignored) { library.clear(); }
    }

    private void playAt(int position) {
        if (position < 0 || position >= tracks.size()) return;
        if (position != current && player != null && !preparing && player.isPlaying()) recordEvent("Saltada");
        playbackToken++;
        releasePlayer();
        if (tts != null) tts.stop();
        current = position;
        saveQueue();
        announcing = voiceOn && voiceReady;
        if (announcing) {
            status = "El locutor presenta el tema...";
            String speech = "Ahora escuchas " + tracks.get(current).title.replaceFirst("(?i)\\.mp3$", "");
            int result = tts.speak(speech, TextToSpeech.QUEUE_FLUSH, null, "track-" + playbackToken);
            if (result == TextToSpeech.ERROR) { announcing = false; startCurrent(); }
        } else startCurrent();
        page = 1;
        render();
    }

    private void startCurrent() {
        if (current < 0 || current >= tracks.size()) return;
        announcing = false;
        preparing = true;
        final int token = playbackToken;
        try {
            player = new MediaPlayer();
            player.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build());
            player.setDataSource(this, tracks.get(current).uri);
            player.setOnPreparedListener(media -> {
                if (token != playbackToken) return;
                preparing = false;
                media.start();
                recordEvent("Iniciada");
                status = "Reproduciendo.";
                render();
            });
            player.setOnCompletionListener(media -> {
                if (token != playbackToken) return;
                recordEvent("Terminada");
                releasePlayer();
                if (current + 1 < tracks.size()) playAt(current + 1);
                else { status = "Terminó la cola."; render(); }
            });
            player.setOnErrorListener((media, what, extra) -> {
                if (token == playbackToken) { preparing = false; status = "No se pudo abrir este audio."; render(); }
                return true;
            });
            player.prepareAsync();
        } catch (Exception error) {
            preparing = false;
            releasePlayer();
            status = "No se pudo abrir este archivo de audio.";
            render();
        }
    }

    private void togglePlayback() {
        if (current < 0) { page = 0; render(); return; }
        if (announcing || preparing) return;
        if (player == null) { startCurrent(); return; }
        if (player.isPlaying()) { player.pause(); status = "En pausa."; }
        else { player.start(); status = "Reproduciendo."; }
        render();
    }

    private void move(int delta) {
        if (current < 0) return;
        int position = current + delta;
        if (position >= 0 && position < tracks.size()) playAt(position);
    }

    private void updateProgress() {
        if (seekBar == null || timeLabel == null || player == null || preparing) return;
        try {
            int total = Math.max(0, player.getDuration());
            int position = Math.max(0, player.getCurrentPosition());
            seekBar.setMax(Math.max(1, total));
            seekBar.setProgress(position);
            timeLabel.setText(clock(position) + " / " + clock(total));
        } catch (IllegalStateException ignored) {}
    }

    private String clock(int milliseconds) {
        int seconds = milliseconds / 1000;
        return (seconds / 60) + ":" + String.format(Locale.ROOT, "%02d", seconds % 60);
    }

    private void releasePlayer() {
        preparing = false;
        announcing = false;
        if (player != null) { player.release(); player = null; }
    }

    @Override public void onInit(int result) {
        if (result != TextToSpeech.SUCCESS || tts == null) { status = "Voz no disponible. La música sí funciona."; render(); return; }
        int language = tts.setLanguage(new Locale("es", "MX"));
        voiceReady = language != TextToSpeech.LANG_MISSING_DATA && language != TextToSpeech.LANG_NOT_SUPPORTED;
        if (!voiceReady) status = "Falta la voz en español. La música sí funciona.";
        tts.setSpeechRate(0.95f);
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override public void onStart(String id) {}
            @Override public void onDone(String id) { finishAnnouncement(id); }
            @Override public void onError(String id) { finishAnnouncement(id); }
        });
        render();
    }

    private void finishAnnouncement(String id) {
        handler.post(() -> {
            if (announcing && id.equals("track-" + playbackToken)) startCurrent();
        });
    }

    @Override protected void onDestroy() {
        playbackToken++;
        releasePlayer();
        if (radioWebView != null) { radioWebView.stopLoading(); radioWebView.destroy(); radioWebView = null; }
        if (tts != null) { tts.stop(); tts.shutdown(); }
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }

    @Override public void onBackPressed() {
        if (page == 4) {
            if (selectedPlaylistId != null) { selectedPlaylistId = null; selectedPlaylistTitle = null; }
            else page = 0;
            render();
            return;
        }
        super.onBackPressed();
    }
}
