package com.olrac.signage.sync

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.core.content.FileProvider
import com.olrac.signage.device.DeviceOwnerManager
import com.olrac.signage.network.AppVersionDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream

object UpdateManager {
    private const val TAG = "UpdateManager"

    suspend fun downloadAndInstallUpdate(context: Context, update: AppVersionDto, client: OkHttpClient): Boolean = withContext(Dispatchers.IO) {
        val apkUrl = update.apk_url
        if (apkUrl.isNullOrBlank()) return@withContext false

        // Refuse before spending bandwidth on a download that could never be trusted.
        UpdateGate.rejectionFor(apkUrl, update.sha256)?.let { reason ->
            Log.e(TAG, "Refusing update ${update.version_code}: $reason")
            recordStatus(context, "failed: $reason")
            return@withContext false
        }

        try {
            val request = Request.Builder().url(apkUrl).build()
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                Log.e(TAG, "Failed to download update: ${response.code}")
                recordStatus(context, "failed: download http ${response.code}")
                return@withContext false
            }

            val apkFile = File(context.cacheDir, "update_${update.version_code}.apk")
            val body = response.body
            if (body == null) {
                recordStatus(context, "failed: empty download")
                return@withContext false
            }

            // Previous attempts' APKs are dead weight in a cache the TV never clears itself.
            context.cacheDir.listFiles { f ->
                f.name.startsWith("update_") && f.name != "update_${update.version_code}.apk"
            }?.forEach { it.delete() }

            body.byteStream().use { input ->
                FileOutputStream(apkFile).use { output ->
                    input.copyTo(output)
                }
            }

            // Fail closed. This check used to run only `if (!update.sha256.isNullOrBlank())`,
            // so a release published without a digest was installed unverified -- and on a
            // device-owner TV that install is silent. An unpinned APK is now never run.
            val computedHash = computeSha256(apkFile)
            if (!UpdateGate.digestMatches(update.sha256, computedHash)) {
                Log.e(TAG, "SHA256 mismatch for update. Expected: ${update.sha256}, Got: $computedHash")
                apkFile.delete()
                recordStatus(context, "failed: sha256 mismatch")
                return@withContext false
            }

            Log.d(TAG, "Update downloaded successfully to ${apkFile.absolutePath}")
            installUpdate(context, apkFile, update.version_code)
            return@withContext true
        } catch (e: Exception) {
            Log.e(TAG, "Error downloading update", e)
            recordStatus(context, "failed: ${e.javaClass.simpleName}")
            return@withContext false
        }
    }

    private fun installUpdate(context: Context, apkFile: File, versionCode: Int) {
        // Two separate routes to installing without a human, and a panel only needs ONE.
        //
        // Device owner is the one this started with, and it is the only route on Android 11
        // and below. It also has to be set up before the screen is used -- a provisioned TV
        // cannot become device owner later without a factory reset -- so every panel that
        // was put into service by installing the APK by hand is permanently ineligible, and
        // those are exactly the ones nobody wants to drive to.
        //
        // The second route is a SELF-update, which Android 12 added and which needs no
        // provisioning at all: an app holding UPDATE_PACKAGES_WITHOUT_USER_ACTION may
        // replace itself with no dialog as long as it asks, via setRequireUserAction. The
        // manifest has declared that permission the whole time -- nothing ever asked, so
        // the platform applied its default of USER_ACTION_UNSPECIFIED and put up the
        // confirmation prompt on every non-device-owner screen.
        //
        // The hint is only that. The system ignores it if this build is not the package's
        // installer of record, and the fallback below still catches that -- so the first
        // update on a hand-installed panel may ask once, and after it lands this player is
        // the installer of record and every later one is silent.
        val deviceOwner = DeviceOwnerManager.isDeviceOwner(context)
        val packageInstaller = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
        }
        // Says this replacement is policy rather than something a person chose, which is
        // what keeps some OEM firmware from raising its own prompt over the platform's.
        runCatching { params.setInstallReason(PackageManager.INSTALL_REASON_POLICY) }
        // Logged separately per route so a screen that installs without asking can be told
        // apart from one that only managed it because it happened to be provisioned.
        val selfUpdateSilent = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
        Log.d(TAG, "Installing $versionCode (deviceOwner=$deviceOwner, selfUpdateSilent=$selfUpdateSilent, unattended=${deviceOwner || selfUpdateSilent})")
        var session: PackageInstaller.Session? = null

        try {
            val sessionId = packageInstaller.createSession(params)
            session = packageInstaller.openSession(sessionId)

            apkFile.inputStream().use { input ->
                session.openWrite("package", 0, apkFile.length()).use { output ->
                    input.copyTo(output)
                    session.fsync(output)
                }
            }

            val intent = Intent(context, InstallReceiver::class.java)
                .putExtra(InstallReceiver.EXTRA_VERSION_CODE, versionCode)
            // requestCode is the version: two PendingIntents that differ only in extras are
            // "the same" to the system, so a shared request code would silently hand the
            // second version's result the first version's extras.
            val pendingIntent = PendingIntent.getBroadcast(
                context, versionCode, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            )

            Log.d(TAG, "Committing session")
            recordStatus(context, "installing")
            session.commit(pendingIntent.intentSender)

        } catch (e: SecurityException) {
            Log.w(TAG, "Not device owner, falling back to Intent install", e)
            session?.abandon()
            fallbackToIntentInstall(context, apkFile, versionCode)
        } catch (e: Exception) {
            Log.e(TAG, "Error during silent install", e)
            session?.abandon()
            fallbackToIntentInstall(context, apkFile, versionCode)
        } finally {
            runCatching { session?.close() }
        }
    }

    private fun fallbackToIntentInstall(context: Context, apkFile: File, versionCode: Int) {
        // Only reachable on a panel that is not the device owner. It always asks, and on an
        // unattended screen nobody answers -- so the retry guard is released first, or one
        // ignored dialog freezes that television on its current build for good.
        context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
            .edit().remove("update_in_flight_$versionCode").apply()
        try {
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                apkFile
            )
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION
            }
            context.startActivity(intent)
            // Not a success: this needs someone standing at the TV to confirm the prompt.
            recordStatus(context, "awaiting manual install")
        } catch (e: Exception) {
            Log.e(TAG, "Error launching install intent", e)
            recordStatus(context, "failed: no installer (${e.javaClass.simpleName})")
        }
    }

    private fun recordStatus(context: Context, status: String) {
        context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
            .edit()
            .putString("update_status", status)
            .apply()
    }

    private fun computeSha256(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { fis ->
            val buffer = ByteArray(8192)
            var bytesRead = fis.read(buffer)
            while (bytesRead != -1) {
                digest.update(buffer, 0, bytesRead)
                bytesRead = fis.read(buffer)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
