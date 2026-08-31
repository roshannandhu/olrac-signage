package com.olrac.signage.boot

import android.app.ActivityOptions
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import android.util.Log
import androidx.core.app.NotificationCompat
import com.olrac.signage.R
import com.olrac.signage.data.AppDatabase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

/**
 * Brings the player to the foreground after boot, or on remote "bring_to_front" commands.
 *
 * Employs a multi-layer strategy:
 *  1. Full-Screen Intent Notification: On Android 10-14, Foreground Services can reliably
 *     pop an activity to the foreground using high-priority fullScreenIntent.
 *  2. AlarmManager Dispatch: Routed via AlarmManager PendingIntent which is dispatched by
 *     the system process. Includes Android 14+ MODE_BACKGROUND_ACTIVITY_START_ALLOWED.
 *  3. Direct startActivity: For Device Owner / unconstrained OEMs.
 */
object PlayerLauncher {
    private const val TAG = "PlayerLauncher"
    private const val CHANNEL_BRING_TO_FRONT = "olrac_bring_to_front"
    private const val NOTIFICATION_ID_BRING_TO_FRONT = 9991

    /** Fast system settle before grabbing the foreground on boot. */
    const val BOOT_SETTLE_MS = 2_000L

    /** Immediate delay when the app is already alive (supervisor restart, package replaced). */
    const val WARM_RESTART_MS = 1_000L

    fun launch(context: Context, delayMs: Long = BOOT_SETTLE_MS, reason: String = "unspecified") {
        warnIfBackgroundStartsWillBeRefused(context, reason)
        val intent = playerIntent(context)

        // 1. Direct startActivity (works on Device Owner and stock devices)
        attemptDirectStart(context, intent, reason)

        // 2. High-priority Full-Screen Intent Notification (guaranteed foreground takeover on Android 10-14)
        triggerFullScreenNotification(context, intent, reason)

        // 3. System-level AlarmManager dispatch (with Android 14+ background launch allowance)
        scheduleViaAlarm(context, intent, delayMs, reason)
    }

    /**
     * Whether this panel can actually raise its own window.
     */
    fun canStartFromBackground(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.Q || Settings.canDrawOverlays(context)

    private fun warnIfBackgroundStartsWillBeRefused(context: Context, reason: String) {
        if (canStartFromBackground(context)) return
        Log.w(
            TAG,
            "SYSTEM_ALERT_WINDOW is not granted (reason=$reason). Full-screen notification & alarm fallback active.",
        )
    }

    fun playerIntent(context: Context): Intent = Intent(Intent.ACTION_MAIN).apply {
        component = ComponentName(context.packageName, "com.olrac.signage.MainActivity")
        addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK or
            Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or
            Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED
        )
    }

    private fun createLaunchPendingIntent(context: Context, intent: Intent): PendingIntent {
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            val options = ActivityOptions.makeBasic().apply {
                setPendingIntentBackgroundActivityStartMode(
                    ActivityOptions.MODE_BACKGROUND_ACTIVITY_START_ALLOWED
                )
            }.toBundle()
            PendingIntent.getActivity(context, REQUEST_BOOT_LAUNCH, intent, flags, options)
        } else {
            PendingIntent.getActivity(context, REQUEST_BOOT_LAUNCH, intent, flags)
        }
    }

    private fun triggerFullScreenNotification(context: Context, intent: Intent, reason: String) {
        try {
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel = NotificationChannel(
                    CHANNEL_BRING_TO_FRONT,
                    "Screen Bring To Front",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Brings signage player to foreground when requested remotely"
                    setSound(null, null)
                    enableVibration(false)
                }
                notificationManager.createNotificationChannel(channel)
            }

            val pending = createLaunchPendingIntent(context, intent)
            val notification = NotificationCompat.Builder(context, CHANNEL_BRING_TO_FRONT)
                .setSmallIcon(R.drawable.olrac_icon)
                .setContentTitle(context.getString(R.string.app_name))
                .setContentText("Activating player display...")
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setFullScreenIntent(pending, true)
                .setAutoCancel(true)
                .setOngoing(false)
                .build()

            notificationManager.notify(NOTIFICATION_ID_BRING_TO_FRONT, notification)
            Log.i(TAG, "Full-screen launch notification posted (reason=$reason)")

            // Auto-clear the notification after 3 seconds so the notification tray stays clean
            Handler(Looper.getMainLooper()).postDelayed({
                try {
                    notificationManager.cancel(NOTIFICATION_ID_BRING_TO_FRONT)
                } catch (_: Exception) {}
            }, 3000L)
        } catch (exception: Exception) {
            Log.e(TAG, "Failed to post full-screen notification (reason=$reason)", exception)
        }
    }

    private fun scheduleViaAlarm(context: Context, intent: Intent, delayMs: Long, reason: String) {
        try {
            val pending = createLaunchPendingIntent(context, intent)
            val alarms = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val triggerTime = SystemClock.elapsedRealtime() + delayMs

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                try {
                    alarms.setExactAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerTime, pending)
                } catch (_: SecurityException) {
                    alarms.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerTime, pending)
                }
            } else {
                alarms.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerTime, pending)
            }
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
            Log.d(TAG, "Direct startActivity refused, relying on full-screen intent/alarm (reason=$reason)")
        }
    }

    fun handleUnpairedOrDeleted(context: Context) {
        val appContext = context.applicationContext
        Log.w(TAG, "Device unpair/deletion initiated. Clearing state and returning to setup.")
        try {
            // 1. Clear pairing state & device secret.
            //
            // clearWorkspace rather than clearPairing: this path is also reached when an
            // operator REMOVES the screen from their fleet, not only when it is unlinked
            // for re-pairing. clearPairing deliberately keeps the cached playlist so the
            // same panel resumes after re-linking, which is wrong here -- the screen no
            // longer belongs to that tenant, and their ads must not keep playing on it.
            com.olrac.signage.data.DeviceState(appContext).clearWorkspace()
            com.olrac.signage.network.ApiClient.clearToken()

            // 2. Clear the cached playlist AND the media it points at, in the background.
            //    Dropping only the rows leaves the downloaded files on disk, where they
            //    survive until something else happens to sweep them.
            @Suppress("OPT_IN_USAGE")
            GlobalScope.launch(Dispatchers.IO) {
                try {
                    AppDatabase.getDatabase(appContext).playlistDao().replaceAll(emptyList())
                    appContext.filesDir.listFiles()
                        ?.filter { it.name.startsWith("content-") }
                        ?.forEach { it.delete() }
                } catch (_: Exception) {}
            }

            // 3. Stop PlaybackService
            try {
                appContext.stopService(Intent(appContext, com.olrac.signage.service.PlaybackService::class.java))
            } catch (_: Exception) {}

            // 4. Launch MainActivity with clean task flags to show Google Sign-In / Pairing
            val intent = Intent(appContext, com.olrac.signage.MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            appContext.startActivity(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Error while unpairing device", e)
        }
    }

    private const val REQUEST_BOOT_LAUNCH = 1001
}
