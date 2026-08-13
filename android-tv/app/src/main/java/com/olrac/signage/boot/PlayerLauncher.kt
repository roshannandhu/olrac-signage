package com.olrac.signage.boot

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import android.util.Log

/**
 * Brings the player to the foreground after boot.
 *
 * Ported from the field-proven `com.ablesign.bootlauncher` watchdog, which runs on
 * Realtek "2K D5STV" Android 14 panels. Three details there were load-bearing and are
 * kept verbatim in spirit here:
 *
 *  1. AlarmManager, not startActivity. Since Android 10 a BroadcastReceiver or a
 *     background foreground-service cannot start an activity. A PendingIntent handed to
 *     AlarmManager is dispatched by the *system* process, which is exempt — this is the
 *     only path that reliably survives on budget OEM firmware.
 *  2. Explicit ComponentName, never getLaunchIntentForPackage(). Since Android 11
 *     package-visibility rules make that lookup return null, and the failure is silent.
 *  3. Fire both paths. Direct startActivity works on stock/Realtek and simply no-ops on
 *     restricted OEMs, so attempting both costs nothing and widens device coverage.
 *
 * ponytail: inexact AlarmManager.set() on purpose — it needs no SCHEDULE_EXACT_ALARM
 * permission, and a second or two of drift is irrelevant when the TV just booted.
 */
object PlayerLauncher {
    private const val TAG = "PlayerLauncher"

    /** Give the system time to settle before grabbing the foreground. */
    const val BOOT_SETTLE_MS = 12_000L

    /** Shorter delay when the app is already alive (supervisor restart, package replaced). */
    const val WARM_RESTART_MS = 2_000L

    fun launch(context: Context, delayMs: Long = BOOT_SETTLE_MS, reason: String = "unspecified") {
        val intent = playerIntent(context)
        scheduleViaAlarm(context, intent, delayMs, reason)
        attemptDirectStart(context, intent, reason)
    }

    fun playerIntent(context: Context): Intent = Intent(Intent.ACTION_MAIN).apply {
        // Explicit component: getLaunchIntentForPackage() returns null on Android 11+.
        component = ComponentName(context.packageName, "com.olrac.signage.MainActivity")
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
    }

    private fun scheduleViaAlarm(context: Context, intent: Intent, delayMs: Long, reason: String) {
        try {
            val pending = PendingIntent.getActivity(
                context,
                REQUEST_BOOT_LAUNCH,
                intent,
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
            )
            val alarms = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            alarms.set(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                SystemClock.elapsedRealtime() + delayMs,
                pending,
            )
            Log.i(TAG, "Launch alarm scheduled in ${delayMs}ms (reason=$reason)")
        } catch (exception: Exception) {
            Log.e(TAG, "Alarm scheduling failed (reason=$reason)", exception)
        }
    }

    private fun attemptDirectStart(context: Context, intent: Intent, reason: String) {
        try {
            context.startActivity(intent)
            Log.i(TAG, "Direct startActivity accepted (reason=$reason)")
        } catch (exception: Exception) {
            // Expected on Android 10+ from a background context; the alarm above is the
            // real path. Logged at debug so it does not read as a failure.
            Log.d(TAG, "Direct startActivity refused, relying on alarm (reason=$reason)")
        }
    }

    private const val REQUEST_BOOT_LAUNCH = 1001
}
