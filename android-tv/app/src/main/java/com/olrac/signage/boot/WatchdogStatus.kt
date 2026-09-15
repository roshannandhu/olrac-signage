package com.olrac.signage.boot

import android.content.ComponentName
import android.content.Context
import android.provider.Settings

/**
 * Whether the watchdog accessibility service is switched on for this TV.
 *
 * Android 13 put "restricted settings" on any app installed from a file -- a USB stick, a
 * browser download -- which is exactly how a TV is commissioned. For such an app the
 * accessibility switch is greyed out, and tapping it only says "Restricted setting". The
 * platform deliberately gives the app no way to lift that itself: a person has to, from App
 * info.
 *
 * Only "is it on" is reported, because only that can be read honestly. The restriction
 * itself lives in a hidden app-op an ordinary app is not allowed to read: a check for it
 * came back "not restricted" on a tablet whose `appops` said deny. So the setup screen shows
 * the unlock steps whenever the watchdog is off, rather than trusting a guess.
 */
object WatchdogStatus {
    fun isEnabled(context: Context): Boolean {
        val enabled = Settings.Secure.getString(
            context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        val ours = ComponentName(context, WatchdogAccessibilityService::class.java)
        return enabled.split(':').any { ComponentName.unflattenFromString(it) == ours }
    }
}
