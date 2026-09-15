package com.olrac.signage.boot

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.olrac.signage.MainActivity
import com.olrac.signage.service.PlaybackService
import com.olrac.signage.telemetry.CrashRecorder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Android Accessibility Service for Realtek & Android TV boot persistence.
 *
 * Realtek Android 14 TV firmware resets standard permissions and drops standard
 * BOOT_COMPLETED broadcasts. Storing this accessibility service in SettingsProvider
 * (via `settings put secure enabled_accessibility_services`) survives 100% of reboots.
 *
 * Two things it must never do, because both switched it straight back off on a KONKA 2K
 * D5STV the moment someone turned it on:
 *
 *  - Launch the player the instant it starts. The service connects while TV Settings is
 *    still on screen finishing the enable -- often behind a confirmation -- and throwing the
 *    player over that interrupts it, which Settings treats as a cancel. It now brings the
 *    player forward on connect only when the device has just booted, which is the Realtek
 *    case it exists for; turned on by hand, it simply starts watching.
 *  - Fight system windows. It used to reclaim the screen for every package whose name lacked
 *    "settings", which includes OEM confirmation dialogs, the permission controller and
 *    vendor panels. It now reclaims only from the home screen or a user-installed app.
 */
class WatchdogAccessibilityService : AccessibilityService() {

    private var lastReclaimAt = 0L

    override fun onCreate() {
        super.onCreate()
        instance = this
        CrashRecorder.install(applicationContext)
        Log.d(TAG, "WatchdogAccessibilityService onCreate")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        val justBooted = SystemClock.elapsedRealtime() < BOOT_WINDOW_MS
        Log.i(TAG, "onServiceConnected (justBooted=$justBooted)")
        // Remembered so a remote diagnostics report can tell "never ran" from "ran and died".
        prefs().edit()
            .putLong(PREF_CONNECTED_AT, System.currentTimeMillis())
            .putBoolean(PREF_CONNECTED_AFTER_BOOT, justBooted)
            .apply()
        try {
            PlaybackService.start(applicationContext, launchPlayer = false)
        } catch (e: Exception) {
            Log.e(TAG, "PlaybackService.start failed on connect", e)
        }
        if (justBooted) forceBringToFront("boot")
    }

    override fun onUnbind(intent: Intent?): Boolean {
        prefs().edit().putLong(PREF_UNBOUND_AT, System.currentTimeMillis()).apply()
        Log.w(TAG, "onUnbind -- the system stopped the watchdog")
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        super.onDestroy()
        prefs().edit().putLong(PREF_DESTROYED_AT, System.currentTimeMillis()).apply()
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

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null || event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return
        val currentPkg = event.packageName?.toString() ?: return
        recordRecentPackage(currentPkg)
        if (!shouldReclaimScreen(currentPkg)) return
        if (!com.olrac.signage.data.DeviceState(applicationContext).isPaired) return
        // One reclaim per burst: opening an app fires several window-state events in a row.
        val now = SystemClock.elapsedRealtime()
        if (now - lastReclaimAt < RECLAIM_DEBOUNCE_MS) return
        lastReclaimAt = now
        Log.d(TAG, "Watchdog reclaiming the screen from $currentPkg")
        forceBringToFront("watchdog_window_event")
    }

    /**
     * The home screen, or an app somebody installed -- never a system window.
     *
     * System apps are Settings, confirmation dialogs, keyboards, the permission controller and
     * whatever panels the TV maker ships. Taking the screen back from any of them is what cut
     * short the dialog that turns this very service on. A package that cannot be resolved is
     * left alone for the same reason: the safe failure is not interrupting.
     */
    private fun shouldReclaimScreen(pkg: String): Boolean {
        if (pkg == packageName) return false
        // Checked before anything else. On a KONKA 2K D5STV, TV Settings, the setup wizard and a
        // Realtek system service all answer the HOME intent alongside the real launcher -- so
        // "any home app" included Settings itself, and the watchdog would have pulled the
        // player over the very screen it is switched on from.
        if (NEVER_RECLAIM_FROM.any { pkg.contains(it) }) return false
        if (pkg == defaultHomePackage()) return true
        val info = runCatching { packageManager.getApplicationInfo(pkg, 0) }.getOrNull() ?: return false
        return info.flags and (ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) == 0
    }

    private var defaultHome: String? = null

    /**
     * The launcher the TV actually returns to -- the DEFAULT home activity, not every app that
     * declares HOME. Null when there is no single default (Android shows its chooser, which
     * resolves to the "android" package), or when that default is this player.
     */
    private fun defaultHomePackage(): String? = defaultHome ?: runCatching {
        packageManager.resolveActivity(
            Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME),
            PackageManager.MATCH_DEFAULT_ONLY
        )?.activityInfo?.packageName?.takeIf { it != "android" && it != packageName }
    }.getOrNull().also { defaultHome = it }

    /** The last few foreground packages, so a remote report shows what the watchdog saw. */
    private fun recordRecentPackage(pkg: String) {
        val prefs = prefs()
        val stamp = SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())
        val recent = (prefs.getString(PREF_RECENT_PACKAGES, "") ?: "")
            .split(',').filter { it.isNotBlank() }
        if (recent.firstOrNull()?.substringBefore('@') == pkg) return
        val next = (listOf("$pkg@$stamp") + recent).take(RECENT_PACKAGES_KEPT)
        prefs.edit().putString(PREF_RECENT_PACKAGES, next.joinToString(",")).apply()
    }

    private fun prefs() = getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)

    override fun onInterrupt() {
        Log.w(TAG, "WatchdogAccessibilityService onInterrupt")
    }

    companion object {
        private const val TAG = "WatchdogA11y"
        /** Connecting this soon after boot is the Realtek case: put the player up. */
        private const val BOOT_WINDOW_MS = 5 * 60_000L
        private const val RECLAIM_DEBOUNCE_MS = 2_000L
        private const val RECENT_PACKAGES_KEPT = 10
        /** System UI an operator uses to configure the TV: never taken away from them. */
        private val NEVER_RECLAIM_FROM = listOf(
            "settings", "setup", "packageinstaller", "permissioncontroller", "systemui", "systemservice",
        )
        const val PREF_CONNECTED_AT = "watchdog_connected_at"
        const val PREF_CONNECTED_AFTER_BOOT = "watchdog_connected_after_boot"
        const val PREF_UNBOUND_AT = "watchdog_unbound_at"
        const val PREF_DESTROYED_AT = "watchdog_destroyed_at"
        const val PREF_RECENT_PACKAGES = "watchdog_recent_packages"
        private var instance: WatchdogAccessibilityService? = null

        fun bringToFront(context: Context, reason: String = "remote_command"): Boolean {
            return instance?.forceBringToFront(reason) ?: false
        }
    }
}
