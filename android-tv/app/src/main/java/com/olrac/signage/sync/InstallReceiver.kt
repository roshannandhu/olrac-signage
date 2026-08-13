package com.olrac.signage.sync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log

class InstallReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)
        val message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)

        val preferences = context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
        when (status) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                Log.d("InstallReceiver", "Requesting user confirmation for install")
                val confirmationIntent = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                if (confirmationIntent != null) {
                    confirmationIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(confirmationIntent)
                }
            }
            PackageInstaller.STATUS_SUCCESS -> {
                Log.d("InstallReceiver", "Install succeeded!")
                preferences.edit().putString("update_status", "success").apply()
                // The app will be restarted automatically by the system
            }
            else -> {
                Log.e("InstallReceiver", "Install failed: $status, $message")
                preferences.edit().putString("update_status", "failed: $message").apply()
            }
        }
    }
}
