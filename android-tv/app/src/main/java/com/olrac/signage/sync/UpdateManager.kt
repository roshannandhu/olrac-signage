package com.olrac.signage.sync

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
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
        // Silent when this player is the device owner, which is the only way Android lets an
        // app install a package without a human. Everything else -- the session, the digest,
        // the download -- is identical either way; the difference is entirely whether the
        // platform trusts the caller, so the attempt is made the same way regardless and the
        // fallback exists only for panels that were never provisioned.
        val silent = DeviceOwnerManager.isDeviceOwner(context)
        Log.d(TAG, "Installing $versionCode (deviceOwner=$silent, unattended=${silent})")
        val packageInstaller = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
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
