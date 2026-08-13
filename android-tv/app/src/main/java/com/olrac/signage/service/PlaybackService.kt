package com.olrac.signage.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.os.UserManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.olrac.signage.MainActivity
import com.olrac.signage.R
import com.olrac.signage.boot.PlayerLauncher
import com.olrac.signage.network.ConnectivityWatcher
import com.olrac.signage.sync.PlaylistSynchronizer
import com.olrac.signage.sync.SyncBackoffPolicy
import com.olrac.signage.telemetry.HeartbeatReporter
import com.olrac.signage.workers.HeartbeatWorker
import com.olrac.signage.workers.SyncWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import java.util.concurrent.TimeUnit

class PlaybackService : Service() {
    private var wakeLock: PowerManager.WakeLock? = null
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val immediateSyncSignals = Channel<Unit>(capacity = Channel.CONFLATED)
    private var pollingJob: Job? = null
    private var connectivityWatcher: ConnectivityWatcher? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        promoteToForeground()
        acquireWakeLock()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (isUserUnlocked()) {
            scheduleWorkers(this)
            startPollingLoop()
        }
        if (intent?.action == ACTION_SYNC_NOW) immediateSyncSignals.trySend(Unit)
        if (intent?.getBooleanExtra(EXTRA_LAUNCH_PLAYER, false) == true) {
            launchPlayer()
        }
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        launchPlayer()
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        connectivityWatcher?.stop()
        connectivityWatcher = null
        pollingJob = null
        serviceScope.cancel()
        wakeLock?.takeIf(PowerManager.WakeLock::isHeld)?.release()
        wakeLock = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun promoteToForeground() {
        val activityIntent = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        val contentIntent = PendingIntent.getActivity(
            this,
            0,
            activityIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.olrac_icon)
            .setContentTitle(getString(R.string.app_name))
            .setContentText("Signage playback protection is active")
            .setContentIntent(contentIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Playback protection",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Keeps managed signage playback alive"
        }
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun acquireWakeLock() {
        val powerManager = getSystemService(PowerManager::class.java)
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "$packageName:playback"
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun launchPlayer() {
        // A foreground service is still a background context for activity-start purposes
        // on Android 10+, so a bare startActivity() here is silently dropped on budget
        // OEM firmware. PlayerLauncher routes through an AlarmManager PendingIntent,
        // which the system process dispatches and is therefore permitted.
        PlayerLauncher.launch(this, PlayerLauncher.WARM_RESTART_MS, reason = "service")
    }

    private fun isUserUnlocked(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return true
        return getSystemService(UserManager::class.java).isUserUnlocked
    }

    private fun startPollingLoop() {
        if (pollingJob?.isActive == true) return

        connectivityWatcher = ConnectivityWatcher(this) {
            immediateSyncSignals.trySend(Unit)
        }.also(ConnectivityWatcher::start)

        pollingJob = serviceScope.launch {
            val synchronizer = PlaylistSynchronizer(this@PlaybackService)
            var consecutiveFailures = 0
            while (isActive) {
                val outcome = synchronizer.sync()
                try {
                    HeartbeatReporter.send(this@PlaybackService)
                } catch (exception: Exception) {
                    Log.d(TAG, "Telemetry heartbeat unavailable", exception)
                }
                val nextDelaySeconds = if (outcome.successful) {
                    consecutiveFailures = 0
                    outcome.intervalSeconds
                } else {
                    val delay = SyncBackoffPolicy.failureDelaySeconds(consecutiveFailures)
                    consecutiveFailures++
                    delay
                }

                val networkOrManualSignal = withTimeoutOrNull(nextDelaySeconds * 1_000L) {
                    immediateSyncSignals.receive()
                    true
                } ?: false
                if (networkOrManualSignal) consecutiveFailures = 0
            }
        }
    }

    companion object {
        private const val TAG = "PlaybackService"
        private const val CHANNEL_ID = "playback-protection"
        private const val NOTIFICATION_ID = 1001
        private const val EXTRA_LAUNCH_PLAYER = "launch_player"
        private const val ACTION_SYNC_NOW = "com.olrac.signage.action.SYNC_NOW"

        fun start(context: Context, launchPlayer: Boolean) {
            val intent = Intent(context, PlaybackService::class.java)
                .putExtra(EXTRA_LAUNCH_PLAYER, launchPlayer)
            ContextCompat.startForegroundService(context, intent)
        }

        fun scheduleWorkers(context: Context) {
            val syncRequest = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES).build()
            val heartbeatRequest =
                PeriodicWorkRequestBuilder<HeartbeatWorker>(15, TimeUnit.MINUTES).build()
            val proofOfPlayRequest =
                PeriodicWorkRequestBuilder<ProofOfPlayWorker>(15, TimeUnit.MINUTES).build()
            
            WorkManager.getInstance(context).apply {
                enqueueUniquePeriodicWork(
                    "sync",
                    ExistingPeriodicWorkPolicy.KEEP,
                    syncRequest
                )
                enqueueUniquePeriodicWork(
                    "heartbeat",
                    ExistingPeriodicWorkPolicy.KEEP,
                    heartbeatRequest
                )
                enqueueUniquePeriodicWork(
                    "proof_of_play",
                    ExistingPeriodicWorkPolicy.KEEP,
                    proofOfPlayRequest
                )
            }
        }

        fun requestImmediateSync(context: Context) {
            val intent = Intent(context, PlaybackService::class.java).setAction(ACTION_SYNC_NOW)
            ContextCompat.startForegroundService(context, intent)
        }
    }
}
