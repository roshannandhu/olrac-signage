package com.olrac.signage.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.olrac.signage.boot.PlayerLauncher
import com.olrac.signage.service.PlaybackService

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action !in SUPPORTED_ACTIONS) return
        // Recorded before anything can fail, so a remote diagnostics report shows whether this
        // TV's firmware delivers the boot broadcast at all -- and, next to the player's own
        // resume time, whether the launch that follows actually put the player on screen.
        context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE).edit()
            .putString(PREF_LAST_BOOT_ACTION, intent.action)
            .putLong(PREF_LAST_BOOT_AT, System.currentTimeMillis())
            .apply()

        // Bring the player forward via AlarmManager first. A receiver cannot start an
        // activity on Android 10+, and neither can the foreground service it starts —
        // the alarm is dispatched by the system process, which is exempt. This is the
        // path proven on Realtek Android 14 panels; see PlayerLauncher.
        val delay = if (intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            PlayerLauncher.WARM_RESTART_MS
        } else {
            PlayerLauncher.BOOT_SETTLE_MS
        }
        PlayerLauncher.launch(context, delay, reason = intent.action ?: "boot")

        try {
            // Service still owns sync, telemetry and the wake lock; it is no longer the
            // mechanism that fronts the UI.
            PlaybackService.start(context, launchPlayer = false)
        } catch (exception: RuntimeException) {
            Log.e(TAG, "Unable to start playback service for ${intent.action}", exception)
        }
    }

    companion object {
        private const val TAG = "BootReceiver"
        const val PREF_LAST_BOOT_ACTION = "last_boot_action"
        const val PREF_LAST_BOOT_AT = "last_boot_at"
        private val SUPPORTED_ACTIONS = setOf(
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED,
            Intent.ACTION_USER_UNLOCKED,
            "android.intent.action.QUICKBOOT_POWERON"
        )
    }
}
