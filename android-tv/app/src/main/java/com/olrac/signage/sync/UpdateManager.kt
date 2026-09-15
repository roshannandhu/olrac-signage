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

    private const val PREFS = "signage_prefs"
    private const val KEY_IN_FLIGHT = "update_in_flight_"
    private const val KEY_ATTEMPTS = "update_attempts_"
    private const val KEY_RETRY_AT = "update_retry_at_"
    private const val KEY_FULL_SYNC_AT = "update_full_sync_at"
    private const val FIRST_RETRY_MS = 60_000L
    private const val MAX_RETRY_MS = 60 * 60_000L

    /**
     * An update attempt did not end in an installed build: try again later, on its own.
     *
     * A screen coming back online is exactly the one most likely to lose its connection
     * part-way through a ten-megabyte download. Releasing the in-flight guard was not enough
     * to recover from that, because the offer only arrives in a full sync body and the screen
     * had already saved the marker that turns every later sync into a 204 -- so it sat on
     * the old build until an unrelated playlist change happened to break the marker.
     *
     * Backs off 1, 2, 4 ... 60 minutes so a build that genuinely cannot install (a full disk,
     * a bad digest) is not fetched every minute for ever.
     */
    fun scheduleRetry(context: Context, versionCode: Int) {
        if (versionCode <= 0) return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val attempts = prefs.getInt("$KEY_ATTEMPTS$versionCode", 0) + 1
        val delay = (FIRST_RETRY_MS shl (attempts - 1).coerceAtMost(6)).coerceAtMost(MAX_RETRY_MS)
        val retryAt = System.currentTimeMillis() + delay
        prefs.edit()
            .remove("$KEY_IN_FLIGHT$versionCode")
            .putInt("$KEY_ATTEMPTS$versionCode", attempts)
            .putLong("$KEY_RETRY_AT$versionCode", retryAt)
            // Asked for no earlier than the retry itself: a full sync that arrived before the
            // backoff expired would hand over the offer, be skipped, and save the marker again.
            .putLong(KEY_FULL_SYNC_AT, retryAt)
            .apply()
        Log.w(TAG, "Update $versionCode attempt $attempts did not install; retrying in ${delay / 1000}s")
    }

    @Volatile private var staleGuardsCleared = false

    /**
     * Drop in-flight guards left behind by a process that no longer exists.
     *
     * The guard means "a download is running in THIS process" -- downloads live in-process
     * and die with it. A TV that lost power mid-download came back with the guard still set
     * and nothing running behind it, and since only a success or a reported failure ever
     * cleared it, that version was never attempted again. Once per process is exactly right:
     * nothing can be in flight before the first sync of a fresh process.
     */
    fun clearStaleGuards(context: Context) {
        if (staleGuardsCleared) return
        staleGuardsCleared = true
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val stale = prefs.all.keys.filter { it.startsWith(KEY_IN_FLIGHT) }
        if (stale.isEmpty()) return
        val edit = prefs.edit()
        stale.forEach { edit.remove(it) }
        edit.apply()
        Log.i(TAG, "Cleared ${stale.size} update guard(s) left by a previous process")
    }

    /** Whether the backoff for this version has run out. */
    fun retryDue(context: Context, versionCode: Int): Boolean =
        System.currentTimeMillis() >= context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getLong("$KEY_RETRY_AT$versionCode", 0L)

    /** True once, when a retry needs the next sync to carry the full body and its offer. */
    fun consumeFullSyncRequest(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!prefs.contains(KEY_FULL_SYNC_AT)) return false
        if (System.currentTimeMillis() < prefs.getLong(KEY_FULL_SYNC_AT, 0L)) return false
        prefs.edit().remove(KEY_FULL_SYNC_AT).apply()
        return true
    }

    /**
     * An operator pressed "Update now": forget any backoff and look for a build immediately.
     *
     * The backoff exists to stop a screen hammering a download on its own. A person asking
     * for the update is the opposite case, and making them wait out an hour-long retry
     * window would make the button look broken.
     */
    fun requestUpdateCheck(context: Context) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val edit = prefs.edit()
        prefs.all.keys
            .filter { it.startsWith(KEY_RETRY_AT) || it.startsWith(KEY_ATTEMPTS) || it.startsWith(KEY_IN_FLIGHT) }
            .forEach { edit.remove(it) }
        edit.putLong(KEY_FULL_SYNC_AT, 0L).apply()
        Log.i(TAG, "Update check requested by the server")
    }

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
            val apkFile = File(context.cacheDir, "update_${update.version_code}.apk")

            // An earlier attempt may already have fetched this build and then failed at the
            // install step. Re-verifying the file on disk costs a hash; re-downloading it
            // costs ten megabytes on a venue's connection every time the retry comes round.
            if (apkFile.isFile && UpdateGate.digestMatches(update.sha256, computeSha256(apkFile))) {
                Log.d(TAG, "Reusing verified download for ${update.version_code}")
                installUpdate(context, apkFile, update.version_code)
                return@withContext true
            }

            val request = Request.Builder().url(apkUrl).build()
            val response = client.newCall(request).execute()

            if (!response.isSuccessful) {
                Log.e(TAG, "Failed to download update: ${response.code}")
                recordStatus(context, "failed: download http ${response.code}")
                return@withContext false
            }

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
        // Declares the build as coming from an app store rather than a downloaded file.
        //
        // Android 13 put "restricted settings" on anything installed from a local or
        // downloaded file: the accessibility toggle for such an app is greyed out and cannot
        // be switched on. The watchdog that keeps this player in front on Realtek TV
        // firmware IS an accessibility service, so a player the platform classed as
        // sideloaded could never have it enabled -- reported simply as "accessibility is not
        // working". A session that says nothing is left to the platform's guess; saying
        // STORE is accurate (this is a managed update channel) and keeps each update from
        // re-applying the restriction.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            params.setPackageSource(PackageInstaller.PACKAGE_SOURCE_STORE)
        }
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
