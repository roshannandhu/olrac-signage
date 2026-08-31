package com.olrac.signage.sync

import android.content.Context
import android.net.Uri
import com.olrac.signage.BuildConfig
import com.olrac.signage.data.AppDatabase
import com.olrac.signage.data.DeviceState
import com.olrac.signage.data.PlaylistItemEntity
import com.olrac.signage.network.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.UUID
import java.util.concurrent.TimeUnit

data class SyncOutcome(
    val successful: Boolean,
    val retryable: Boolean,
    val changed: Boolean,
    val intervalSeconds: Int,
    val error: String? = null
)

class PlaylistSynchronizer(context: Context) {
    private val appContext = context.applicationContext
    private val preferences = appContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
    private val api by lazy { ApiClient.service(appContext) }
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.MINUTES)
        .callTimeout(10, TimeUnit.MINUTES)
        .build()
    private val storageManager = StorageManager(appContext)

    suspend fun sync(): SyncOutcome = GLOBAL_SYNC_MUTEX.withLock {
        withContext(Dispatchers.IO) {
            val currentInterval = SyncBackoffPolicy.serverIntervalSeconds(
                preferences.getInt(KEY_SYNC_INTERVAL_SECONDS, 60)
            )
            // Via DeviceState, which derives and persists the id on first access. Reading
            // the preference raw returned null on a fresh install whenever the service
            // started before MainActivity ever ran -- which is exactly what BootReceiver
            // does -- and this reported "Device is not registered" with retryable = false,
            // so sync stayed dead until someone opened the app by hand.
            val deviceId = DeviceState(appContext).deviceId

            cleanupStaleDownloads()
            try {
                val dao = AppDatabase.getDatabase(appContext).playlistDao()
                // An empty local playlist must always request a full snapshot. This
                // prevents a matching version marker from trapping a repaired or
                // newly provisioned database in an empty state.
                val since = preferences.getString(KEY_PLAYLIST_UPDATED_AT, null)
                    .takeIf { dao.hasItems() }
                val response = api.sync(
                    deviceId = deviceId,
                    since = since
                )
                val responseInterval = response.headers()[SYNC_INTERVAL_HEADER]?.toIntOrNull()

                if (response.code() == 204) {
                    val interval = saveInterval(responseInterval ?: currentInterval)
                    return@withContext SyncOutcome(true, false, false, interval)
                }
                if (response.code() == 404 || response.code() == 401 || response.code() == 403) {
                    android.util.Log.w("PlaylistSynchronizer", "Screen deleted or credentials revoked (HTTP ${response.code()}); signing out")
                    com.olrac.signage.boot.PlayerLauncher.handleUnpairedOrDeleted(appContext)
                    return@withContext SyncOutcome(false, false, true, currentInterval, "Screen unlinked")
                }
                // 404 is not a transient failure and must not be retried like one. It means
                // the server has no screen for this device id -- the operator removed this TV
                // from their fleet. Treated as retryable (which it was) the panel keeps
                // playing the removed tenant's cached playlist forever, reconnecting every
                // minute to a workspace it no longer belongs to.
                if (response.code() == 404) {
                    com.olrac.signage.boot.PlayerLauncher.handleUnpairedOrDeleted(appContext)
                    return@withContext SyncOutcome(
                        successful = false,
                        retryable = false,
                        changed = true,
                        intervalSeconds = currentInterval,
                        error = "This screen was removed from its workspace"
                    )
                }
                if (!response.isSuccessful) {
                    return@withContext SyncOutcome(
                        successful = false,
                        retryable = true,
                        changed = false,
                        intervalSeconds = currentInterval,
                        error = "Sync failed with HTTP ${response.code()}"
                    )
                }

                val syncData = response.body() ?: return@withContext SyncOutcome(
                    successful = false,
                    retryable = true,
                    changed = false,
                    intervalSeconds = currentInterval,
                    error = "Sync response was empty"
                )
                val interval = saveInterval(syncData.sync_interval_seconds ?: responseInterval)

                if (syncData.screen_id != null || syncData.organization_id != null) {
                    preferences.edit().apply {
                        syncData.screen_id?.let { putInt("screen_id", it) }
                        syncData.organization_id?.let { putInt("organization_id", it) }
                        apply()
                    }
                }

                syncData.pending_command?.let { cmd ->
                    if (cmd == "deregister") {
                        com.olrac.signage.boot.PlayerLauncher.handleUnpairedOrDeleted(appContext)
                        return@withContext SyncOutcome(
                            successful = true,
                            retryable = false,
                            changed = true,
                            intervalSeconds = interval,
                        )
                    }
                    if (cmd == "bring_to_front" || cmd == "launch_app") {
                        android.util.Log.i("PlaylistSynchronizer", "Received $cmd command from sync; bringing app to front")
                        com.olrac.signage.boot.PlayerLauncher.launch(appContext, delayMs = 500L, reason = "sync_command")
                    } else if (cmd == "reset" || cmd == "unpair") {
                        android.util.Log.w("PlaylistSynchronizer", "Received $cmd command from sync; signing out")
                        com.olrac.signage.boot.PlayerLauncher.handleUnpairedOrDeleted(appContext)
                        return@withContext SyncOutcome(false, false, true, interval, "Screen reset command")
                    }
                }

                syncData.app_version?.let { version ->
                    if (version.version_code > BuildConfig.VERSION_CODE && !version.apk_url.isNullOrBlank()) {
                        val inFlightKey = "$KEY_UPDATE_IN_FLIGHT${version.version_code}"
                        if (!preferences.getBoolean(inFlightKey, false)) {
                            preferences.edit().putBoolean(inFlightKey, true).apply()

                            // Download off the sync path so playback and polling continue.
                            @Suppress("OPT_IN_USAGE")
                            GlobalScope.launch(Dispatchers.IO) {
                                val installed = UpdateManager.downloadAndInstallUpdate(
                                    appContext, version, client
                                )
                                if (!installed) {
                                    // Clear the guard on failure, otherwise one dropped
                                    // download permanently blocks this version and the TV
                                    // can never be updated remotely again — which is the
                                    // entire point of staged rollout. On success the flag
                                    // stays set: the install replaces the process, and a
                                    // higher version_code uses a different key anyway.
                                    preferences.edit().remove(inFlightKey).apply()
                                }
                            }
                        }
                    }
                }

                // Cached ahead of the empty-playlist return: a screen with nothing scheduled
                // still has to be serviceable from the remote.
                syncData.maintenance_pin?.takeIf { it.isNotBlank() }?.let {
                    DeviceState(appContext).setMaintenancePin(it)
                }

                val playlist = syncData.playlist
                if (playlist == null) {
                    dao.replaceAll(emptyList())
                    cleanupOldCache(emptySet())
                    preferences.edit()
                        .putString(KEY_PLAYLIST_UPDATED_AT, syncData.playlist_updated_at)
                        .apply()
                    return@withContext SyncOutcome(true, false, true, interval)
                }

                val targets = playlist.items.map { item ->
                    val fileName = cacheFileName(item.content.id, item.content.file_url)
                    val finalFile = File(appContext.filesDir, fileName)
                    val entity = PlaylistItemEntity(
                        id = item.id,
                        contentId = item.content.id,
                        playlistId = playlist.id,
                        type = item.content.type,
                        fileUrl = item.content.file_url,
                        localPath = null,
                        duration = item.duration,
                        orderIndex = item.order,
                        startAt = item.start_at,
                        endAt = item.end_at,
                        daysOfWeek = item.schedule?.days_of_week?.joinToString(","),
                        windowStart = item.schedule?.start_time,
                        windowEnd = item.schedule?.end_time,
                        transition = item.transition,
                        transitionMs = item.transition_ms,
                        rotation = item.rotation ?: 0,
                        fitMode = syncData.fit_mode ?: "contain",
                        playlistDefaultTransition = playlist.default_transition ?: "fade",
                        playlistDefaultTransitionMs = playlist.default_transition_ms ?: 600,
                        sha256 = item.content.sha256,
                        fileSizeBytes = item.content.file_size_bytes
                    )
                    ActivationTarget(entity, finalFile)
                }

                // Files the player may be reading right now, plus everything this sync
                // intends to activate. Eviction must never touch these, or a playlist
                // switch under storage pressure deletes the ad currently on screen.
                val protectedNames = buildSet {
                    dao.getAllItems().forEach { existing ->
                        existing.localPath?.let { add(File(it).name) }
                    }
                    targets.forEach { add(it.finalFile.name) }
                }

                val staged = mutableListOf<StagedDownload>()
                for (target in targets) {
                    if (!target.finalFile.isFile || target.finalFile.length() == 0L) {
                        val tempFile = storageManager.downloadWithIntegrityCheck(
                            client = client,
                            url = ApiClient.resolveMediaUrl(appContext, target.entity.fileUrl),
                            finalFile = target.finalFile,
                            expectedSha256 = target.entity.sha256,
                            expectedSizeBytes = target.entity.fileSizeBytes,
                            protectedNames = protectedNames
                        )
                        if (tempFile == null) {
                            staged.forEach { it.temporaryFile.delete() }
                            return@withContext SyncOutcome(
                                successful = false,
                                retryable = true,
                                changed = false,
                                intervalSeconds = interval,
                                error = "Media download failed"
                            )
                        }
                        staged += StagedDownload(tempFile, target.finalFile)
                    }
                }

                staged.forEach(::promoteStagedFile)
                val activatedItems = targets.map { target ->
                    target.entity.copy(localPath = target.finalFile.absolutePath)
                }

                // This Room transaction is the activation boundary. The currently
                // playing rows remain untouched until every new file is durable.
                dao.replaceAll(activatedItems)
                cleanupOldCache(targets.mapTo(mutableSetOf()) { it.finalFile.name })
                preferences.edit()
                    .putString(KEY_PLAYLIST_UPDATED_AT, syncData.playlist_updated_at)
                    .apply()
                SyncOutcome(true, false, true, interval)
            } catch (exception: Exception) {
                SyncOutcome(
                    successful = false,
                    retryable = true,
                    changed = false,
                    intervalSeconds = currentInterval,
                    error = exception.message ?: exception.javaClass.simpleName
                )
            }
        }
    }

    private fun saveInterval(value: Int?): Int {
        val interval = SyncBackoffPolicy.serverIntervalSeconds(value)
        preferences.edit().putInt(KEY_SYNC_INTERVAL_SECONDS, interval).apply()
        return interval
    }

    private fun cacheFileName(contentId: Int, url: String): String {
        val segment = Uri.parse(url).lastPathSegment ?: "media"
        val extension = segment.substringAfterLast('.', "bin").take(8)
        return "content-$contentId.$extension"
    }

    // `downloadToStaging` removed, logic is in StorageManager

    private fun promoteStagedFile(download: StagedDownload) {
        try {
            Files.move(
                download.temporaryFile.toPath(),
                download.finalFile.toPath(),
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING
            )
        } catch (_: AtomicMoveNotSupportedException) {
            Files.move(
                download.temporaryFile.toPath(),
                download.finalFile.toPath(),
                StandardCopyOption.REPLACE_EXISTING
            )
        }
    }

    private fun cleanupOldCache(validFileNames: Set<String>) {
        appContext.filesDir.listFiles()?.forEach { file ->
            if (file.name.startsWith("content-") && file.name !in validFileNames) {
                file.delete()
            }
        }
    }

    private fun cleanupStaleDownloads() {
        val yesterday = System.currentTimeMillis() - 24 * 60 * 60 * 1000L
        appContext.filesDir.listFiles()?.forEach { file ->
            if (file.name.startsWith(StorageManager.PART_PREFIX) && file.lastModified() < yesterday) {
                file.delete()
            }
        }
    }

    private data class ActivationTarget(
        val entity: PlaylistItemEntity,
        val finalFile: File
    )

    private data class StagedDownload(
        val temporaryFile: File,
        val finalFile: File
    )

    companion object {
        private val GLOBAL_SYNC_MUTEX = Mutex()
        private const val PREFERENCES_NAME = "signage_prefs"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_PLAYLIST_UPDATED_AT = "playlist_updated_at"
        private const val KEY_SYNC_INTERVAL_SECONDS = "sync_interval_seconds"
        private const val KEY_PENDING_UPDATE_URL = "pending_update_url"
        private const val KEY_PENDING_UPDATE_VERSION = "pending_update_version"
        /** Prefix; the target version_code is appended. Cleared if the download fails. */
        private const val KEY_UPDATE_IN_FLIGHT = "update_in_flight_"
        private const val SYNC_INTERVAL_HEADER = "X-Sync-Interval-Seconds"
    }
}
