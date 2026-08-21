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
    private static final long MIN_RELAUNCH_MS = 10000;
    private static long lastLaunchTime = 0;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean showingSetup = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // No setup gate. The accessibility service is an optional extra, not a
        // requirement: boot is handled by BootReceiver's AlarmManager and recovery by this
        // activity being HOME, neither of which needs it. Refusing to start the player
        // until someone walked into Settings on each TV was the reason the watchdog
        // appeared dead on arrival.
        // The launch itself is left to onResume, which always follows onCreate.
    }

    /**
     * This activity is the TV's HOME app and never finishes, so being resumed means the
     * player is no longer in front — it crashed, was force-stopped, or someone pressed
     * Home. Whatever the cause, the screen should be showing signage rather than this.
     *
     * The relaunch used to hang off onNewIntent, which the system does not deliver when it
     * simply resumes an already-running HOME activity. That is the common case after a
     * crash, so the watchdog would come to the foreground and sit there indefinitely —
     * a dead screen in a shop, with the watchdog running exactly as designed.
     */
    @Override
    protected void onResume() {
        super.onResume();
        if (showingSetup) return;   // only ever true if openAccessibilitySettings() was used
        maybeLaunch();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        // Home pressed while this activity is already resident and in front.
        if (!showingSetup) maybeLaunch();
    }

    /**
     * Start the player unless an attempt is already in flight.
     *
     * The timestamp is claimed at scheduling time, not after the launch, so overlapping
     * triggers collapse into one attempt and a player that refuses to start cannot spin
     * the TV in a relaunch loop.
     */
    private void maybeLaunch() {
        long now = SystemClock.elapsedRealtime();
        if (now - lastLaunchTime < MIN_RELAUNCH_MS) return;
        lastLaunchTime = now;
        scheduleAbleSign(2000);
    }

    /** Whether the optional accessibility service is on. Nothing gates on this. */
    private boolean isServiceEnabled() {
        String enabled = Settings.Secure.getString(getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;

        // Settings stores a colon-separated list of flattened components, but *which*
        // flattening depends on the build: Android 16 writes the fully-qualified
        // "pkg/pkg.Class", while others write the short "pkg/.Class". Matching only the
        // short form made this return false while the service was demonstrably running,
        // so the watchdog — which is the HOME app on a TV — sat on its setup screen
        // instead of returning to the player. Both forms are accepted.
        ComponentName self = new ComponentName(this, WatchdogAccessibilityService.class);
        return enabled.contains(self.flattenToString())
                || enabled.contains(self.flattenToShortString());
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
        try {
            Intent i = new Intent(Intent.ACTION_MAIN);
            i.setComponent(WatchdogTarget.component(this));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            startActivity(i);
            // The accessibility state is logged rather than acted on: a TV that is
            // misbehaving can then be told apart from one that simply never had the
            // optional extra switched on.
            Log.i(TAG, "AbleSign launched (accessibility extra "
                    + (isServiceEnabled() ? "on" : "off") + ")");
        } catch (Exception e) {
            Log.e(TAG, "launch failed: " + e.getMessage());
        }
        // No finish() — stay resident so HOME intents come back here
    }
}
