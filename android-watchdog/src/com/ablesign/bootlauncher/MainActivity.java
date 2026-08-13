package com.ablesign.bootlauncher;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String TAG = "BootLauncher";
    private static final String ABLESIGN = "com.olrac.signage";
    private static final long MIN_RELAUNCH_MS = 10000;
    private static long lastLaunchTime = 0;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean showingSetup = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (!isServiceEnabled()) {
            showingSetup = true;
            showSetupUI();
        } else {
            scheduleAbleSign(3000);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (showingSetup && isServiceEnabled()) {
            showingSetup = false;
            scheduleAbleSign(1000);
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (showingSetup) return;
        long now = SystemClock.elapsedRealtime();
        if (now - lastLaunchTime > MIN_RELAUNCH_MS) {
            scheduleAbleSign(3000);
        }
    }

    private boolean isServiceEnabled() {
        String s = Settings.Secure.getString(getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        return s != null && s.contains(getPackageName() + "/.WatchdogAccessibilityService");
    }

    private void showSetupUI() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(Color.parseColor("#1a1a2e"));
        root.setPadding(80, 80, 80, 80);

        TextView title = new TextView(this);
        title.setText("AbleSign Watchdog — Setup");
        title.setTextSize(28);
        title.setTextColor(Color.WHITE);
        title.setGravity(Gravity.CENTER);

        TextView msg = new TextView(this);
        msg.setText("Tap the button below, then find\n\"AbleSign Watchdog\" and turn it ON.");
        msg.setTextSize(20);
        msg.setTextColor(Color.LTGRAY);
        msg.setGravity(Gravity.CENTER);
        msg.setPadding(0, 40, 0, 60);

        Button btn = new Button(this);
        btn.setText("Open Accessibility Settings");
        btn.setTextSize(18);
        btn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
            }
        });

        root.addView(title);
        root.addView(msg);
        root.addView(btn);
        setContentView(root);
    }

    private void scheduleAbleSign(long delayMs) {
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                launchAbleSign();
            }
        }, delayMs);
    }

    private void launchAbleSign() {
        lastLaunchTime = SystemClock.elapsedRealtime();
        try {
            Intent i = new Intent(Intent.ACTION_MAIN);
            i.setComponent(new ComponentName(ABLESIGN, ABLESIGN + ".MainActivity"));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            startActivity(i);
            Log.i(TAG, "AbleSign launched");
        } catch (Exception e) {
            Log.e(TAG, "launch failed: " + e.getMessage());
        }
        // No finish() — stay resident so HOME intents come back here
    }
}
