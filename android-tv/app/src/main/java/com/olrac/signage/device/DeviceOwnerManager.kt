package com.olrac.signage.device

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.util.Log
import com.olrac.signage.receivers.SignageDeviceAdminReceiver

object DeviceOwnerManager {
    private const val TAG = "DeviceOwnerManager"

    /**
     * Checks whether this app is the device owner.
     */
    fun isDeviceOwner(context: Context): Boolean {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        return dpm.isDeviceOwnerApp(context.packageName)
    }

    /**
     * Call on first run when device owner to lock down the device into kiosk mode.
     */
    fun applyKioskPolicy(context: Context) {
        if (!isDeviceOwner(context)) {
            Log.w(TAG, "Not applying kiosk policy: App is not device owner")
            return
        }

        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val adminName = ComponentName(context, SignageDeviceAdminReceiver::class.java)

        try {
            // 1. LockTask Mode
            dpm.setLockTaskPackages(adminName, arrayOf(context.packageName))
            Log.d(TAG, "Lock task packages set")

            // 2. Persistent preferred activity for HOME intent
            val intentFilter = IntentFilter(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_HOME)
                addCategory(Intent.CATEGORY_DEFAULT)
            }
            val activityName = ComponentName(context, com.olrac.signage.MainActivity::class.java)
            dpm.addPersistentPreferredActivity(adminName, intentFilter, activityName)
            Log.d(TAG, "Persistent preferred activity set")

            // 3. Disable keyguard and status bar
            dpm.setKeyguardDisabled(adminName, true)
            dpm.setStatusBarDisabled(adminName, true)
            Log.d(TAG, "Keyguard and status bar disabled")

            // 4. Auto-grant runtime permissions
            dpm.setPermissionPolicy(adminName, DevicePolicyManager.PERMISSION_POLICY_AUTO_GRANT)
            Log.d(TAG, "Permission policy set to auto grant")

            // 5. Block uninstalls
            dpm.setUninstallBlocked(adminName, context.packageName, true)
            Log.d(TAG, "Uninstall blocked")

            Log.i(TAG, "Kiosk policy applied successfully")
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException while applying kiosk policy. Ensure app is truly device owner.", e)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to apply kiosk policy", e)
        }
    }
}
