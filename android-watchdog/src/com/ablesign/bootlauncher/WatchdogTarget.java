package com.ablesign.bootlauncher;

import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

/**
 * Which app this watchdog is responsible for starting.
 *
 * The package used to be a constant in three separate files, so retargeting the watchdog
 * meant editing and rebuilding it. It now resolves in this order:
 *
 *   1. a value previously saved by a configure broadcast (survives reboot)
 *   2. the build-time default below
 *
 * That makes one APK universal: install it anywhere and point it at whatever player runs
 * on that TV with
 *
 *   adb shell am broadcast -a com.ablesign.bootlauncher.CONFIGURE \
 *       -e package com.example.player -e activity com.example.player.MainActivity
 *
 * The activity is optional; "&lt;package&gt;.MainActivity" is assumed, which is the
 * convention every build of this player family follows.
 */
public final class WatchdogTarget {

    private static final String TAG = "WatchdogTarget";
    private static final String PREFS = "watchdog_target";
    private static final String KEY_PACKAGE = "target_package";
    private static final String KEY_ACTIVITY = "target_activity";

    /** Build-time default, used until a configure broadcast overrides it. */
    private static final String DEFAULT_PACKAGE = "com.olrac.signage";

    private WatchdogTarget() {}

    public static String packageName(Context context) {
        return prefs(context).getString(KEY_PACKAGE, DEFAULT_PACKAGE);
    }

    /** Fully-qualified launch activity, defaulting to the package's MainActivity. */
    public static String activityName(Context context) {
        String pkg = packageName(context);
        return prefs(context).getString(KEY_ACTIVITY, pkg + ".MainActivity");
    }

    /**
     * The component to launch.
     *
     * Built explicitly rather than via getLaunchIntentForPackage, which returns null on
     * Android 11+ unless the other app is declared visible — the exact failure that made
     * the player's own boot handling silently do nothing.
     */
    public static ComponentName component(Context context) {
        return new ComponentName(packageName(context), activityName(context));
    }

    /** Remember a new target across reboots. */
    public static void configure(Context context, String pkg, String activity) {
        if (pkg == null || pkg.trim().length() == 0) {
            Log.w(TAG, "ignoring configure with an empty package");
            return;
        }
        SharedPreferences.Editor editor = prefs(context).edit();
        editor.putString(KEY_PACKAGE, pkg.trim());
        if (activity != null && activity.trim().length() > 0) {
            editor.putString(KEY_ACTIVITY, activity.trim());
        } else {
            editor.remove(KEY_ACTIVITY);
        }
        // commit, not apply: a configure broadcast can be followed immediately by a reboot,
        // and an async write may not have reached disk by then.
        editor.commit();
        Log.i(TAG, "target set to " + packageName(context) + "/" + activityName(context));
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }
}
