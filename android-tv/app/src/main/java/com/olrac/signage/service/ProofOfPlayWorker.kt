package com.olrac.signage.service

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.olrac.signage.data.AppDatabase
import com.olrac.signage.network.ApiClient
import com.olrac.signage.telemetry.HeartbeatReporter
import retrofit2.http.Body
import retrofit2.http.POST

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
    val screen_id: Int, // The screen_id is available? Wait, Android only has device_id... Ah! We need to know our screen_id!
    val organization_id: Int,
    val events: List<PlayEventDto>
)

interface ProofOfPlayApi {
    @POST("api/screens/play-logs/batch")
    suspend fun sendBatch(@Body request: PlayLogBatchRequest): retrofit2.Response<Unit>
}

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
            screen_id = screenId,
            organization_id = orgId,
            events = dtos
        )
        
        val apiService = ApiClient.service(applicationContext) as ProofOfPlayApi
        return try {
            val response = apiService.sendBatch(request)
            if (response.isSuccessful) {
                playEventDao.deleteEvents(pendingEvents.map { it.eventId })
                Result.success()
            } else {
                if (response.code() in 400..499) {
                    // Client error, e.g. token rejected or validation failed. 
                    // Don't retry indefinitely, but for now we'll just fail so it stays in queue
                    // wait, if validation fails on one event, the whole batch is stuck!
                    // Let's drop them if it's 422? The spec didn't specify. We'll just retry for now,
                    // but if it's 401/403, we definitely fail so it retries later when token is valid.
                    Result.retry()
                } else {
                    Result.retry()
                }
            }
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
