package com.olrac.signage.sync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log
import com.olrac.signage.device.DeviceOwnerManager

/**
 * What became of an install the player asked for.
 *
 * Also the place the retry guard is released. `PlaylistSynchronizer` sets
 * `update_in_flight_<version>` before starting so a slow download is not started twice, and
 * `UpdateManager.downloadAndInstallUpdate` returns true the moment the session is COMMITTED
 * -- which is before anyone knows whether it installed. So an install that ended in anything
 * other than success left that flag set for ever, and the screen never offered itself that
 * version again: one missed confirmation and a television stayed on its old build permanently,
 * with nothing on the dashboard saying why.
 */
class InstallReceiver : BroadcastReceiver() {
    companion object {
        /** Which version this result belongs to, so the right retry guard is released. */
        const val EXTRA_VERSION_CODE = "com.olrac.signage.UPDATE_VERSION_CODE"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)
        val message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)
        val versionCode = intent.getIntExtra(EXTRA_VERSION_CODE, -1)

        val preferences = context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)

        fun allowRetry(reason: String) {
            if (versionCode > 0) {
                preferences.edit().remove("update_in_flight_$versionCode").apply()
                Log.d("InstallReceiver", "Cleared retry guard for $versionCode ($reason)")
            }
        }

        when (status) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                // A device owner never lands here -- the platform installs without asking.
                // Anything else has to put a dialog on a television that usually has nobody
                // in front of it, which is why this is logged as the misconfiguration it is
                // rather than treated as a normal step.
                Log.w(
                    "InstallReceiver",
                    "Android is asking a human to confirm this install, which means this " +
                        "player is not the device owner (isDeviceOwner=" +
                        "${DeviceOwnerManager.isDeviceOwner(context)}). Provision the panel " +
                        "as device owner for unattended updates."
                )
                preferences.edit().putString("update_status", "awaiting confirmation").apply()
                // Released BEFORE showing the prompt: if nobody is there to tap it, the next
                // sync must be free to try again rather than the screen being stuck for ever.
                allowRetry("user confirmation required")

                val confirmationIntent = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                if (confirmationIntent != null) {
                    confirmationIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(confirmationIntent)
                }
            }
            PackageInstaller.STATUS_SUCCESS -> {
                Log.d("InstallReceiver", "Install succeeded")
                preferences.edit().putString("update_status", "success").apply()
                // The guard is deliberately NOT cleared: the process is about to be replaced,
                // and a newer build uses a different key anyway.
            }
            else -> {
                Log.e("InstallReceiver", "Install failed: $status, $message")
                preferences.edit().putString("update_status", "failed: $message").apply()
                allowRetry("install failed")
            }
        }
    }
}
