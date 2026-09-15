package com.olrac.signage.boot

import android.app.AppOpsManager
import android.content.ComponentName
import android.content.Context
import android.os.Build
import android.os.Process
import android.provider.Settings

/**
 * Whether the watchdog accessibility service is running on this TV, and if not, why.
 *
 * Android 13 put "restricted settings" on any app installed from a file -- a USB stick, a
 * browser download -- which is exactly how a TV is commissioned. For such an app the
 * accessibility switch is greyed out, and tapping it only says "Restricted setting". The
 * platform deliberately gives the app no way to lift that itself: a person has to, from App
 * info. Nothing on the TV said so, so the report was simply "the watchdog will not turn on".
 */
object WatchdogStatus {
    enum class State { ON, RESTRICTED, OFF }

    // Not in the public SDK as a constant; checking an op on our own uid needs no permission.
    private const val OP_ACCESS_RESTRICTED_SETTINGS = "android:access_restricted_settings"

    fun state(context: Context): State = when {
        isEnabled(context) -> State.ON
        isRestricted(context) -> State.RESTRICTED
        else -> State.OFF
    }

    fun isEnabled(context: Context): Boolean {
        val enabled = Settings.Secure.getString(
            context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        val ours = ComponentName(context, WatchdogAccessibilityService::class.java)
        return enabled.split(':').any { ComponentName.unflattenFromString(it) == ours }
    }

    /**
     * True when Android has locked this app's accessibility switch.
     *
     * An unreadable op reports false rather than guessing: the screen then offers the plain
     * "turn it on" path, which is still correct on every device that is not restricted.
     */
    fun isRestricted(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return false
        val appOps = context.getSystemService(AppOpsManager::class.java) ?: return false
        val mode = runCatching {
            appOps.unsafeCheckOpNoThrow(OP_ACCESS_RESTRICTED_SETTINGS, Process.myUid(), context.packageName)
        }.getOrNull() ?: return false
        return mode == AppOpsManager.MODE_ERRORED || mode == AppOpsManager.MODE_IGNORED
    }
}
