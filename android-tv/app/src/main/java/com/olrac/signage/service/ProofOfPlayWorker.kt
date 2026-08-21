package com.olrac.signage.service

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.olrac.signage.data.AppDatabase
import com.olrac.signage.network.ApiClient

data class PlayEventDto(
    val event_id: String,
    val media_id: Int?,
    val playlist_id: Int?,
    val campaign_id: Int?,
    val device_started_at: String,
    val device_finished_at: String,
    val corrected_started_at: String,
    val corrected_finished_at: String,
    val duration_ms: Int,
    val status: String,
    val error_message: String?
)

data class PlayLogBatchRequest(
    // The device id identifies the player; screen_id and organization_id come back from
    // the heartbeat and are cross-checked server side against the device's own screen.
    val device_id: String,
    val screen_id: Int,
    val organization_id: Int,
    val events: List<PlayEventDto>
)

class ProofOfPlayWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val prefs = applicationContext.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
        val deviceId = prefs.getString("device_id", null) ?: return Result.failure()
        val screenId = prefs.getInt("screen_id", -1)
        val orgId = prefs.getInt("organization_id", -1)
        
        if (screenId == -1 || orgId == -1) {
            // Cannot upload without screen context, wait for next heartbeat
            return Result.retry()
        }
        
        val database = AppDatabase.getDatabase(applicationContext)
        val playEventDao = database.playEventDao()
        
        // Grab up to 500 events
        val pendingEvents = playEventDao.getPendingEvents(500)
        if (pendingEvents.isEmpty()) {
            return Result.success()
        }
        
        val dtos = pendingEvents.map {
            PlayEventDto(
                event_id = it.eventId,
                media_id = it.mediaId,
                playlist_id = it.playlistId,
                campaign_id = it.campaignId,
                device_started_at = it.deviceStartedAt,
                device_finished_at = it.deviceFinishedAt,
                corrected_started_at = it.correctedStartedAt,
                corrected_finished_at = it.correctedFinishedAt,
                duration_ms = it.durationMs,
                status = it.status,
                error_message = it.errorMessage
            )
        }
        
        val request = PlayLogBatchRequest(
            device_id = deviceId,
            screen_id = screenId,
            organization_id = orgId,
            events = dtos
        )
        
        return try {
            val response = ApiClient.service(applicationContext).uploadPlayLogs(request)
            when {
                response.isSuccessful -> {
                    playEventDao.deleteEvents(pendingEvents.map { it.eventId })
                    Result.success()
                }
                // 401/403 clear once the device re-authenticates, so those keep their events.
                // Any other 4xx is the server refusing this payload permanently: retrying it
                // wedges the queue and every later play is lost behind it, so drop the batch.
                response.code() in 400..499 && response.code() !in listOf(401, 403, 408, 429) -> {
                    Log.w(TAG, "Server rejected ${pendingEvents.size} play events (${response.code()}); dropping batch")
                    playEventDao.deleteEvents(pendingEvents.map { it.eventId })
                    Result.success()
                }
                else -> Result.retry()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Play log upload failed", e)
            Result.retry()
        }
    }

    private companion object {
        const val TAG = "ProofOfPlay"
    }
}
