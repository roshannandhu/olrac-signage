package com.olrac.signage.telemetry

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.ActivityManager
import android.app.AlarmManager
import android.app.AppOpsManager
import android.app.NotificationManager
import android.app.role.RoleManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.PowerManager
import android.os.Process
import android.provider.Settings
import android.util.Log
import android.view.accessibility.AccessibilityManager
import androidx.core.app.NotificationManagerCompat
import com.olrac.signage.BuildConfig
import com.olrac.signage.boot.WatchdogAccessibilityService
import com.olrac.signage.device.DeviceOwnerManager
import com.olrac.signage.network.ApiClient
import com.olrac.signage.network.DiagnosticsRequest

/**
 * What this TV can say about itself that nobody standing in front of it is there to read.
 *
 * Screens are installed in venues, far from support. Whether the watchdog can run is decided
 * entirely by device state -- an accessibility switch Android may have locked, how the app was
 * installed, which permissions and roles it holds -- and none of that was visible remotely, so
 * "the watchdog will not turn on" could only be diagnosed by going there. Every probe is
 * wrapped: a report that throws is worth less than one with a field missing.
 */
object DeviceDiagnostics {
    private const val TAG = "DeviceDiagnostics"
    private const val RESEND_AFTER_MS = 30 * 60_000L
    private const val PREFS = "signage_prefs"

    @Volatile private var lastSent: String? = null
    @Volatile private var lastSentAt = 0L

    fun collect(context: Context): Map<String, Any?> {
        val ctx = context.applicationContext
        val pkg = ctx.packageName
        val watchdog = ComponentName(ctx, WatchdogAccessibilityService::class.java)
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val report = linkedMapOf<String, Any?>()

        fun probe(name: String, block: () -> Any?) {
            report[name] = try { block() } catch (e: Throwable) { "error: ${e.javaClass.simpleName}: ${e.message?.take(120)}" }
        }

        probe("app_version") { BuildConfig.VERSION_NAME }
        probe("sdk") { Build.VERSION.SDK_INT }
        probe("is_tv") { ctx.packageManager.hasSystemFeature(PackageManager.FEATURE_LEANBACK) }
        probe("device_owner") { DeviceOwnerManager.isDeviceOwner(ctx) }

        // --- the watchdog itself -------------------------------------------------------
        probe("watchdog_in_enabled_setting") {
            val enabled = Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES)
            enabled?.split(':')?.any { ComponentName.unflattenFromString(it) == watchdog } == true
        }
        probe("accessibility_enabled_flag") {
            Settings.Secure.getInt(ctx.contentResolver, Settings.Secure.ACCESSIBILITY_ENABLED, -1)
        }
        val a11y = ctx.getSystemService(AccessibilityManager::class.java)
        probe("watchdog_listed_by_system") {
            a11y.installedAccessibilityServiceList.any { it.resolveInfo.serviceInfo.name == watchdog.className }
        }
        // In the enabled setting but not bound = it was switched on and then died or was refused.
        probe("watchdog_bound") {
            a11y.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
                .any { it.resolveInfo.serviceInfo.name == watchdog.className }
        }
        probe("watchdog_last_connected_at") { prefs.getLong(WatchdogAccessibilityService.PREF_CONNECTED_AT, 0L).takeIf { it > 0 } }
        probe("watchdog_last_destroyed_at") { prefs.getLong(WatchdogAccessibilityService.PREF_DESTROYED_AT, 0L).takeIf { it > 0 } }
        probe("watchdog_last_unbound_at") { prefs.getLong(WatchdogAccessibilityService.PREF_UNBOUND_AT, 0L).takeIf { it > 0 } }
        probe("watchdog_connected_after_boot") {
            if (prefs.contains(WatchdogAccessibilityService.PREF_CONNECTED_AFTER_BOOT)) prefs.getBoolean(WatchdogAccessibilityService.PREF_CONNECTED_AFTER_BOOT, false) else null
        }
        // Newest first, "package@HH:mm:ss" -- what was on screen around the switch turning off.
        probe("watchdog_recent_packages") { prefs.getString(WatchdogAccessibilityService.PREF_RECENT_PACKAGES, null) }
        probe("home_screen_packages") {
            ctx.packageManager.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME), PackageManager.MATCH_DEFAULT_ONLY)
                .joinToString(",") { it.activityInfo.packageName }
        }
        probe("last_crash") { prefs.getString(CrashRecorder.PREF_LAST_CRASH, null) }

        // --- the Android 13+ lock ------------------------------------------------------
        // Recorded raw, including a refusal: whether this op is readable at all differs by
        // build, and on the test tablet it read as allowed while `appops` said deny.
        val appOps = ctx.getSystemService(AppOpsManager::class.java)
        probe("restricted_settings_op") {
            appOps.unsafeCheckOpNoThrow("android:access_restricted_settings", Process.myUid(), pkg)
        }
        probe("restricted_settings_op_raw") {
            appOps.unsafeCheckOpRawNoThrow("android:access_restricted_settings", Process.myUid(), pkg)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            probe("install_source") {
                val info = ctx.packageManager.getInstallSourceInfo(pkg)
                buildString {
                    append("installing=").append(info.installingPackageName)
                    append(" initiating=").append(info.initiatingPackageName)
                    append(" originating=").append(info.originatingPackageName)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) append(" source=").append(info.packageSource)
                }
            }
        }
        probe("accessibility_settings_activity") {
            ctx.packageManager.resolveActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS), 0)
                ?.activityInfo?.let { "${it.packageName}/${it.name}" }
        }

        // --- the other ways the player keeps itself in front -----------------------------
        probe("overlay_allowed") { Settings.canDrawOverlays(ctx) }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            probe("home_role_held") { ctx.getSystemService(RoleManager::class.java).isRoleHeld(RoleManager.ROLE_HOME) }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            probe("exact_alarms_allowed") { ctx.getSystemService(AlarmManager::class.java).canScheduleExactAlarms() }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            probe("full_screen_intent_allowed") { ctx.getSystemService(NotificationManager::class.java).canUseFullScreenIntent() }
        }
        probe("notifications_enabled") { NotificationManagerCompat.from(ctx).areNotificationsEnabled() }
        probe("battery_optimisation_ignored") { ctx.getSystemService(PowerManager::class.java).isIgnoringBatteryOptimizations(pkg) }
        probe("lock_task_mode") { ctx.getSystemService(ActivityManager::class.java).lockTaskModeState }
        return report
    }

    /** Send when something changed, and at least every half hour so a stale report is visible. */
    suspend fun sendIfDue(context: Context, deviceId: String?) {
        if (deviceId.isNullOrBlank()) return
        val report = collect(context)
        val serialised = report.toString()
        val now = System.currentTimeMillis()
        if (serialised == lastSent && now - lastSentAt < RESEND_AFTER_MS) return
        try {
            val response = ApiClient.service(context.applicationContext)
                .reportDiagnostics(DiagnosticsRequest(device_id = deviceId, report = report))
            if (response.isSuccessful) {
                lastSent = serialised
                lastSentAt = now
            } else {
                Log.d(TAG, "Diagnostics refused: HTTP ${response.code()}")
            }
        } catch (e: Exception) {
            Log.d(TAG, "Diagnostics unavailable", e)
        }
    }
}
