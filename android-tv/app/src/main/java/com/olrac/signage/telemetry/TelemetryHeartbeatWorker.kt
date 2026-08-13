package com.olrac.signage.telemetry

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters

class TelemetryHeartbeatWorker(
    context: Context,
    workerParameters: WorkerParameters
) : CoroutineWorker(context, workerParameters) {
    override suspend fun doWork(): Result {
        val suppliedState = inputData.getString(KEY_STATE)
        val snapshot = suppliedState?.let {
            PlaybackSnapshot(
                state = it,
                currentItemId = inputData.getInt(KEY_ITEM_ID, NO_ITEM).takeUnless { id -> id == NO_ITEM },
                lastError = inputData.getString(KEY_LAST_ERROR)
            )
        }
        return try {
            if (HeartbeatReporter.send(applicationContext, snapshot)) Result.success() else Result.retry()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    companion object {
        private const val KEY_STATE = "playback_state"
        private const val KEY_ITEM_ID = "current_item_id"
        private const val KEY_LAST_ERROR = "last_error"
        private const val NO_ITEM = -1

        fun enqueue(context: Context, snapshot: PlaybackSnapshot) {
            val data = Data.Builder()
                .putString(KEY_STATE, snapshot.state)
                .putInt(KEY_ITEM_ID, snapshot.currentItemId ?: NO_ITEM)
                .putString(KEY_LAST_ERROR, snapshot.lastError)
                .build()
            WorkManager.getInstance(context).enqueue(
                OneTimeWorkRequestBuilder<TelemetryHeartbeatWorker>()
                    .setInputData(data)
                    .build()
            )
        }
    }
}
