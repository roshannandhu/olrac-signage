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
import com.olrac.signage.MainActivity
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
        instance = this
        Log.d(TAG, "WatchdogAccessibilityService onCreate")
        launchOlracSignage("onCreate")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.d(TAG, "WatchdogAccessibilityService onServiceConnected")
        launchOlracSignage("onServiceConnected")
    }

    override fun onDestroy() {
        super.onDestroy()
        if (instance == this) instance = null
    }

    fun forceBringToFront(reason: String = "remote_command"): Boolean {
        return try {
            val intent = Intent(this, MainActivity::class.java).apply {
                addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or
                    Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED
                )
            }
            startActivity(intent)
            Log.i(TAG, "forceBringToFront executed via AccessibilityService (reason=$reason)")
            true
        } catch (e: Exception) {
            Log.e(TAG, "forceBringToFront failed via AccessibilityService", e)
            false
        }
    }

    private fun launchOlracSignage(from: String) {
        forceBringToFront(from)

        // Ensure PlaybackService is active
        try {
            PlaybackService.start(applicationContext, launchPlayer = false)
        } catch (e: Exception) {
            Log.e(TAG, "PlaybackService.start failed from $from", e)
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null || event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return
        val currentPkg = event.packageName?.toString() ?: return

        // If the system returns to launcher or another non-system app, and the screen is paired, restore player
        if (currentPkg != packageName &&
            !currentPkg.startsWith("com.android.systemui") &&
            !currentPkg.startsWith("android") &&
            !currentPkg.contains("settings") &&
            !currentPkg.contains("packageinstaller")) {
            val deviceState = com.olrac.signage.data.DeviceState(applicationContext)
            if (deviceState.isPaired) {
                Log.d(TAG, "Watchdog detected foreground package $currentPkg, ensuring OLRAC Signage remains active")
                forceBringToFront("watchdog_window_event")
            }
        }
    }

    override fun onInterrupt() {
        Log.w(TAG, "WatchdogAccessibilityService onInterrupt")
    }

    companion object {
        private const val TAG = "WatchdogA11y"
        private var instance: WatchdogAccessibilityService? = null

        fun bringToFront(context: Context, reason: String = "remote_command"): Boolean {
            return instance?.forceBringToFront(reason) ?: false
        }
    }
}
