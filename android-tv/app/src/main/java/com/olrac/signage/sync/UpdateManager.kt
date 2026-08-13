package com.olrac.signage.sync

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.util.Log
import androidx.core.content.FileProvider
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

        try {
            val request = Request.Builder().url(apkUrl).build()
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                Log.e(TAG, "Failed to download update: ${response.code}")
                return@withContext false
            }

            val apkFile = File(context.cacheDir, "update_${update.version_code}.apk")
            val body = response.body
            if (body == null) return@withContext false

            body.byteStream().use { input ->
                FileOutputStream(apkFile).use { output ->
                    input.copyTo(output)
                }
            }

            if (!update.sha256.isNullOrBlank()) {
                val computedHash = computeSha256(apkFile)
                if (!computedHash.equals(update.sha256, ignoreCase = true)) {
                    Log.e(TAG, "SHA256 mismatch for update. Expected: ${update.sha256}, Got: $computedHash")
                    apkFile.delete()
                    val prefs = context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
                    prefs.edit().putString("update_status", "failed: sha256 mismatch").apply()
                    return@withContext false
                }
            }

            Log.d(TAG, "Update downloaded successfully to ${apkFile.absolutePath}")
            installUpdate(context, apkFile)
            return@withContext true
        } catch (e: Exception) {
            Log.e(TAG, "Error downloading update", e)
            return@withContext false
        }
    }

    private fun installUpdate(context: Context, apkFile: File) {
        // Attempt silent install if device owner
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
            val pendingIntent = PendingIntent.getBroadcast(
                context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            )

            Log.d(TAG, "Committing session")
            session.commit(pendingIntent.intentSender)

        } catch (e: SecurityException) {
            Log.w(TAG, "Not device owner, falling back to Intent install", e)
            session?.abandon()
            fallbackToIntentInstall(context, apkFile)
        } catch (e: Exception) {
            Log.e(TAG, "Error during silent install", e)
            session?.abandon()
            fallbackToIntentInstall(context, apkFile)
        }
    }

    private fun fallbackToIntentInstall(context: Context, apkFile: File) {
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
        } catch (e: Exception) {
            Log.e(TAG, "Error launching install intent", e)
        }
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
