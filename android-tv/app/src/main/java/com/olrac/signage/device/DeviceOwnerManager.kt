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
    private const val PREFS = "signage_prefs"
    private const val KEY_EXIT_LAUNCHER = "kiosk_exit_launcher_package"

    private fun homeFilter() = IntentFilter(Intent.ACTION_MAIN).apply {
        addCategory(Intent.CATEGORY_HOME)
        addCategory(Intent.CATEGORY_DEFAULT)
    }

    /**
     * Checks whether this app is the device owner.
     */
    fun isDeviceOwner(context: Context): Boolean {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        return dpm.isDeviceOwnerApp(context.packageName)
    }

    /**
     * Undo the parts of kiosk mode that would stop an operator actually leaving the player:
     * the forced home screen (every HOME press reopened the player) and the disabled status bar.
     * Lock task is stopped by the activity itself. `applyKioskPolicy` puts all of it back the
     * next time the player comes to the front, so this is an exit, not a way to disable kiosk.
     */
    fun releaseKioskPolicy(context: Context, homeLauncher: ComponentName? = null) {
        if (!isDeviceOwner(context)) return
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val adminName = ComponentName(context, SignageDeviceAdminReceiver::class.java)
        try {
            dpm.clearPackagePersistentPreferredActivities(adminName, context.packageName)
            // Clearing ours is not enough when this player also holds the HOME role: Home would
            // still come straight back here. Point Home at the launcher the operator exited to,
            // and remember it so applyKioskPolicy can take that back off.
            if (homeLauncher != null) {
                dpm.addPersistentPreferredActivity(adminName, homeFilter(), homeLauncher)
                context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                    .putString(KEY_EXIT_LAUNCHER, homeLauncher.packageName).apply()
            }
            dpm.setStatusBarDisabled(adminName, false)
            Log.i(TAG, "Kiosk policy released for an operator exit (home -> ${homeLauncher?.packageName})")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to release kiosk policy", e)
        }
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
            // Undo an operator exit first: the launcher it pointed Home at must not keep winning.
            // Isolated, so a failure here can never stop the rest of kiosk being applied.
            runCatching {
                val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                prefs.getString(KEY_EXIT_LAUNCHER, null)?.let { launcherPackage ->
                    dpm.clearPackagePersistentPreferredActivities(adminName, launcherPackage)
                    prefs.edit().remove(KEY_EXIT_LAUNCHER).apply()
                }
            }.onFailure { Log.w(TAG, "Could not undo a previous operator exit", it) }
            val activityName = ComponentName(context, com.olrac.signage.MainActivity::class.java)
            dpm.addPersistentPreferredActivity(adminName, homeFilter(), activityName)
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
