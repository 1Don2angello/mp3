package org.spotisaver.app;

import android.app.Activity;
import android.content.Intent;
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
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends Activity implements TextToSpeech.OnInitListener {
    private static final int PICK_AUDIO = 7;
    private static final int INK = Color.rgb(23, 23, 23);
    private static final int PAPER = Color.rgb(250, 249, 245);
    private static final int MUTED = Color.rgb(86, 86, 86);
    private final ArrayList<Track> tracks = new ArrayList<>();
    private final ArrayList<Track> library = new ArrayList<>();
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
    private LinearLayout content;
    private LinearLayout nav;
    private SeekBar seekBar;
    private TextView timeLabel;

    private static class Track {
        final Uri uri;
        final String title;
        Track(Uri uri, String title) { this.uri = uri; this.title = title; }
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
    }

    private void render() {
        content.removeAllViews();
        nav.removeAllViews();
        seekBar = null;
        timeLabel = null;
        addText("SPOTISAVER  /  PAPEL FM", 13, false, true, 25);
        rule();
        if (page == 0) renderHome();
        else if (page == 1) renderPlayer();
        else if (page == 2) renderQueue();
        else renderLibrary();
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
        addText("FASE 1  ·  REPRODUCTOR LOCAL", 12, false, true, 15);
        addText("Elige MP3 del teléfono. La cola los reproduce en orden y puedes encender la voz del locutor antes de cada tema.", 15, false, false, 25);
        addButton("Elegir canciones del teléfono", true, this::pickAudio, 18);
        rule();
        addText("TU SESIÓN", 12, false, true, 8);
        addText(tracks.size() + " canción(es) en cola", 23, true, false, 9);
        addText(status, 13, false, false, 20);
        if (current >= 0) addButton("Ir a Sonando →", false, () -> { page = 1; render(); }, 12);
        addText("Los archivos elegidos aparecen en Biblioteca al volver a abrir la app. La cola actual se reinicia al cerrar.", 12, false, false, 0);
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
            status = "Cola vacía. Tus MP3 siguen en el teléfono.";
            render();
        }, 10);
        if (tracks.isEmpty()) addText("Todavía no hay canciones. Agrégalas desde tu teléfono.", 15, false, false, 0);
    }

    private void renderLibrary() {
        addText("Tu biblioteca.", 38, true, false, 13);
        addText("ARCHIVOS ELEGIDOS  /  " + library.size(), 12, false, true, 15);
        addText("Estos enlaces a tus archivos se guardan en la app. Tus MP3 permanecen en su lugar.", 13, false, false, 18);
        addButton("Agregar archivos", true, this::pickAudio, 17);
        for (int i = 0; i < library.size(); i++) {
            Track track = library.get(i);
            addButton("+ " + track.title, false, () -> {
                addToQueue(track);
                status = "Agregada a la cola: " + track.title;
                page = 2;
                render();
            }, 6);
        }
        if (library.isEmpty()) addText("La biblioteca está vacía. Elige canciones del teléfono para empezar.", 15, false, false, 12);
        if (!library.isEmpty()) addButton("Olvidar biblioteca", false, () -> {
            library.clear();
            saveLibrary();
            status = "Biblioteca vacía. Los archivos siguen en el teléfono.";
            render();
        }, 8);
    }

    private void pickAudio() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("audio/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        startActivityForResult(intent, PICK_AUDIO);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_AUDIO || resultCode != RESULT_OK || data == null) return;
        int before = tracks.size();
        if (data.getClipData() != null) {
            for (int i = 0; i < data.getClipData().getItemCount(); i++) addTrack(data.getClipData().getItemAt(i).getUri());
        } else if (data.getData() != null) addTrack(data.getData());
        saveLibrary();
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
        boolean known = false;
        for (Track saved : library) if (saved.uri.equals(uri)) { known = true; break; }
        if (!known) library.add(track);
    }

    private void addToQueue(Track track) {
        for (Track queued : tracks) if (queued.uri.equals(track.uri)) return;
        tracks.add(track);
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
        playbackToken++;
        releasePlayer();
        if (tts != null) tts.stop();
        current = position;
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
                status = "Reproduciendo.";
                render();
            });
            player.setOnCompletionListener(media -> {
                if (token != playbackToken) return;
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
        if (tts != null) { tts.stop(); tts.shutdown(); }
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
