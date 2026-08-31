package com.olrac.signage.boot

import android.accessibilityservice.AccessibilityService
import android.app.ActivityOptions
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.olrac.signage.service.PlaybackService

/**
 * Android Accessibility Service for Realtek & Android TV boot persistence.
 *
 * Realtek Android 14 TV firmware resets standard permissions and drops standard
 * BOOT_COMPLETED broadcasts. Storing this accessibility service in SettingsProvider
 * (via `settings put secure enabled_accessibility_services`) survives 100% of reboots.
 *
 * When Android boots and starts this service process, onCreate / onServiceConnected
 * triggers launching com.olrac.signage.MainActivity after a short system settle delay.
 */
class WatchdogAccessibilityService : AccessibilityService() {

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "WatchdogAccessibilityService onCreate")
        scheduleLaunch("onCreate", BOOT_SETTLE_DELAY_MS)
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(TAG, "WatchdogAccessibilityService onServiceConnected")
        scheduleLaunch("onServiceConnected", WARM_SETTLE_DELAY_MS)
    }

    private fun scheduleLaunch(from: String, delayMs: Long) {
        if (hasLaunched) {
            Log.d(TAG, "Already launched from=$from, skipping duplicate")
            return
        }
        hasLaunched = true

        Log.i(TAG, "Scheduling OLRAC Signage launch in ${delayMs}ms from $from")
        Handler(Looper.getMainLooper()).postDelayed({
            launchOlracSignage(from)
        }, delayMs)
    }

    private fun launchOlracSignage(from: String) {
        Log.i(TAG, "launchOlracSignage executing from $from")
        val intent = Intent(Intent.ACTION_MAIN).apply {
            component = ComponentName(packageName, "com.olrac.signage.MainActivity")
            addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or
                Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED
            )
        }

        // 1. AlarmManager system dispatch (bypasses OEM background activity restrictions)
        try {
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                    (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)

            val pendingIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                val options = ActivityOptions.makeBasic().apply {
                    setPendingIntentBackgroundActivityStartMode(
                        ActivityOptions.MODE_BACKGROUND_ACTIVITY_START_ALLOWED
                    )
                }.toBundle()
                PendingIntent.getActivity(this, 1001, intent, flags, options)
            } else {
                PendingIntent.getActivity(this, 1001, intent, flags)
            }

            val alarmManager = getSystemService(Context.ALARM_SERVICE) as? AlarmManager
            alarmManager?.set(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                SystemClock.elapsedRealtime() + 2000L,
                pendingIntent
            )
            Log.d(TAG, "AlarmManager scheduled successfully from $from")
        } catch (e: Exception) {
            Log.e(TAG, "AlarmManager schedule failed from $from", e)
        }

        // 2. Direct startActivity
        try {
            startActivity(intent)
            Log.d(TAG, "startActivity called successfully from $from")
        } catch (e: Exception) {
            Log.e(TAG, "startActivity failed from $from", e)
        }

        // 3. Ensure PlaybackService is active
        try {
            PlaybackService.start(applicationContext, launchPlayer = false)
        } catch (e: Exception) {
            Log.e(TAG, "PlaybackService.start failed from $from", e)
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // No-op - only used for boot lifecycle anchor
    }

    override fun onInterrupt() {
        Log.w(TAG, "WatchdogAccessibilityService onInterrupt")
    }

    companion object {
        private const val TAG = "WatchdogA11y"
        private const val BOOT_SETTLE_DELAY_MS = 12_000L
        private const val WARM_SETTLE_DELAY_MS = 3_000L
        private var hasLaunched = false
    }
}
