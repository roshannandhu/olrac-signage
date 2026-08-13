package com.olrac.signage.workers

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.olrac.signage.telemetry.HeartbeatReporter

class HeartbeatWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return try {
            if (HeartbeatReporter.send(context)) Result.success() else Result.retry()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
