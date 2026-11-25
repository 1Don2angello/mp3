package org.spotisaver.ttsprueba;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.Locale;

public class MainActivity extends Activity implements TextToSpeech.OnInitListener {
    private static final int INK = Color.rgb(23, 23, 23);
    private static final int PAPER = Color.rgb(250, 249, 245);
    private static final int MUTED = Color.rgb(85, 85, 85);

    private TextToSpeech tts;
    private TextView status;
    private EditText script;
    private Button playButton;
    private boolean voiceReady = false;

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable box(int background, int border, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(background);
        shape.setStroke(dp(1), border);
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private TextView label(String text, int size, boolean bold) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(INK);
        view.setTextSize(size);
        if (bold) view.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        return view;
    }

    private LinearLayout.LayoutParams spacing(int bottom) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.bottomMargin = dp(bottom);
        return params;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(INK);
        getWindow().setNavigationBarColor(INK);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(PAPER);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(24), dp(30), dp(24), dp(24));
        scroll.addView(content);
        setContentView(scroll);

        TextView brand = label("SPOTISAVER  /  PRUEBA DE VOZ", 13, true);
        content.addView(brand, spacing(32));

        TextView title = label("La voz de tu\nestación.", 38, false);
        title.setTypeface(Typeface.SERIF);
        content.addView(title, spacing(14));

        TextView intro = label("Escribe una frase y escucha cómo sonaría el locutor en tu teléfono. Esta prueba no necesita internet ni descarga música.", 15, false);
        intro.setTextColor(MUTED);
        content.addView(intro, spacing(28));

        TextView fieldLabel = label("TEXTO DEL LOCUTOR", 12, true);
        content.addView(fieldLabel, spacing(9));

        script = new EditText(this);
        script.setText("Estamos en el aire. Soy tu locutor y te acompaño en esta nueva emisión de Spotisaver.");
        script.setTextSize(17);
        script.setTextColor(INK);
        script.setGravity(Gravity.TOP);
        script.setMinLines(4);
        script.setBackground(box(Color.WHITE, INK, 0));
        script.setPadding(dp(14), dp(14), dp(14), dp(14));
        content.addView(script, spacing(20));

        playButton = new Button(this);
        playButton.setText("ESCUCHAR VOZ");
        playButton.setTextColor(Color.WHITE);
        playButton.setBackground(box(INK, INK, 0));
        playButton.setEnabled(false);
        content.addView(playButton, spacing(10));

        Button stopButton = new Button(this);
        stopButton.setText("DETENER");
        stopButton.setTextColor(INK);
        stopButton.setBackground(box(PAPER, INK, 0));
        content.addView(stopButton, spacing(24));

        status = label("Preparando la voz del teléfono...", 13, false);
        status.setTextColor(MUTED);
        content.addView(status, spacing(20));

        View rule = new View(this);
        rule.setBackgroundColor(INK);
        content.addView(rule, new LinearLayout.LayoutParams(-1, dp(1)));
        TextView foot = label("BOCETO FUNCIONAL · SOLO TTS", 11, true);
        LinearLayout.LayoutParams footParams = spacing(0);
        footParams.topMargin = dp(12);
        content.addView(foot, footParams);

        playButton.setOnClickListener(v -> speak());
        stopButton.setOnClickListener(v -> {
            if (tts != null) tts.stop();
            status.setText("Voz detenida.");
        });

        tts = new TextToSpeech(this, this);
    }

    @Override
    public void onInit(int result) {
        if (result != TextToSpeech.SUCCESS || tts == null) {
            status.setText("No se pudo iniciar la voz TTS. Revisa el motor de voz del teléfono.");
            return;
        }
        int language = tts.setLanguage(new Locale("es", "MX"));
        if (language == TextToSpeech.LANG_MISSING_DATA || language == TextToSpeech.LANG_NOT_SUPPORTED) {
            status.setText("Falta la voz en español. Instálala en los ajustes de texto a voz del teléfono.");
            return;
        }
        tts.setSpeechRate(0.95f);
        tts.setPitch(1.0f);
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override public void onStart(String id) {
                runOnUiThread(() -> status.setText("Hablando..."));
            }
            @Override public void onDone(String id) {
                runOnUiThread(() -> status.setText("Prueba terminada."));
            }
            @Override public void onError(String id) {
                runOnUiThread(() -> status.setText("No se pudo reproducir la voz."));
            }
        });
        voiceReady = true;
        playButton.setEnabled(true);
        status.setText("Voz en español lista. Pulsa Escuchar voz.");
    }

    private void speak() {
        if (!voiceReady || tts == null) return;
        String text = script.getText().toString().trim();
        if (text.isEmpty()) {
            status.setText("Escribe una frase para escucharla.");
            return;
        }
        int result = tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "spotisaver-tts-test");
        if (result == TextToSpeech.ERROR) status.setText("El motor de voz no aceptó el texto.");
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        super.onDestroy();
    }
}
