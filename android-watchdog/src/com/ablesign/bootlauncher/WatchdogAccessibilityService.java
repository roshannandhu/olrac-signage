package com.ablesign.bootlauncher;

import android.accessibilityservice.AccessibilityService;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;

public class WatchdogAccessibilityService extends AccessibilityService {
    private static final String TAG = "WatchdogA11y";
    private static final String ABLESIGN = "com.olrac.signage";
    private static boolean launched = false;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "onCreate launched=" + launched);
        if (!launched) {
            launched = true;
            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                @Override
                public void run() {
                    launchAbleSign("onCreate");
                }
            }, 12000);
        }
    }

    @Override
    public void onServiceConnected() {
        Log.d(TAG, "onServiceConnected launched=" + launched);
        // Also try from here in case onCreate path was blocked
        if (!launched) {
            launched = true;
            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                @Override
                public void run() {
                    launchAbleSign("onServiceConnected");
                }
            }, 3000);
        }
    }

    private void launchAbleSign(String from) {
        Log.d(TAG, "launchAbleSign from=" + from);
        Intent i = new Intent(Intent.ACTION_MAIN);
        i.setComponent(new ComponentName(ABLESIGN, ABLESIGN + ".MainActivity"));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);

        // AlarmManager fires via system process — bypasses Realme/OPPO background launch restriction
        try {
            PendingIntent pi = PendingIntent.getActivity(this, 1, i,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
            AlarmManager am = (AlarmManager) getSystemService(ALARM_SERVICE);
            am.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, SystemClock.elapsedRealtime() + 2000, pi);
            Log.d(TAG, "alarm scheduled from=" + from);
        } catch (Exception e) {
            Log.e(TAG, "alarm failed from=" + from + ": " + e);
        }

        // Also try direct — works on stock/Realtek, silently no-ops on restricted OEMs
        try {
            startActivity(i);
            Log.d(TAG, "startActivity ok from=" + from);
        } catch (Exception e) {
            Log.e(TAG, "startActivity failed from=" + from + ": " + e);
        }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {}
}
