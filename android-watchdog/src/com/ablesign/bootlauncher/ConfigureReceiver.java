package com.ablesign.bootlauncher;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/**
 * Retarget the watchdog without rebuilding it.
 *
 *   adb shell am broadcast -a com.ablesign.bootlauncher.CONFIGURE \
 *       -e package com.olrac.signage -e activity com.olrac.signage.MainActivity
 *
 * This is what makes a single APK usable across different players. The choice is stored in
 * SharedPreferences, so it survives reboots exactly like the accessibility-service state
 * the watchdog already relies on.
 */
public class ConfigureReceiver extends BroadcastReceiver {

    private static final String TAG = "WatchdogConfigure";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String pkg = intent.getStringExtra("package");
        String activity = intent.getStringExtra("activity");
        Log.i(TAG, "configure requested package=" + pkg + " activity=" + activity);
        WatchdogTarget.configure(context, pkg, activity);
    }
}
