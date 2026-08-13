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
        private val SUPPORTED_ACTIONS = setOf(
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED,
            Intent.ACTION_USER_UNLOCKED,
            "android.intent.action.QUICKBOOT_POWERON"
        )
    }
}
