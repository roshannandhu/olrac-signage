package com.olrac.signage.workers

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.olrac.signage.sync.PlaylistSynchronizer

class SyncWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {
    override suspend fun doWork(): Result {
        val outcome = PlaylistSynchronizer(applicationContext).sync()
        return when {
            outcome.successful -> Result.success()
            outcome.retryable -> Result.retry()
            else -> Result.failure()
        }
    }
}
