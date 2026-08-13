package com.olrac.signage.service

import android.content.Context
import android.util.Log
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.olrac.signage.boot.PlayerLauncher
import com.olrac.signage.telemetry.PlaybackTelemetry
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.WeakHashMap

/**
 * Keeps something on screen no matter what the media does.
 *
 * Recovery ladder, escalating on *consecutive* failures:
 *   1. retry the current item
 *   2. skip the damaged item
 *   3. reload the playlist
 *   4. restart the player activity
 *
 * The ladder is driven by a failure counter, not by exceptions. ExoPlayer is
 * asynchronous: `prepare()` and `play()` return immediately and report problems later
 * through `Player.Listener.onPlayerError`, so they essentially never throw. An earlier
 * version wrapped each rung in try/catch and returned after the retry, which meant the
 * skip/reload/restart rungs were unreachable and a permanently corrupt file looped
 * error -> prepare -> error forever. The counter below is what makes escalation real.
 */
class PlayerSupervisor(
    private val context: Context,
    private val players: List<ExoPlayer>,
    private val telemetry: PlaybackTelemetry,
    private val currentItemId: () -> Int?,
    private val onSkipItem: () -> Unit,
    private val onReloadPlaylist: () -> Unit
) {
    private var livenessJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Main)
    private val lastPositions = WeakHashMap<ExoPlayer, Long>()
    private val frozenCounts = WeakHashMap<ExoPlayer, Int>()
    private val listeners = mutableMapOf<ExoPlayer, Player.Listener>()

    /** Consecutive failures since playback was last observed healthy. Drives the ladder. */
    private var consecutiveFailures = 0
    private var healthyTicks = 0

    init {
        players.forEach { player ->
            val listener = object : Player.Listener {
                override fun onPlayerError(error: PlaybackException) {
                    handlePlayerError(player, error)
                }
            }
            listeners[player] = listener
            player.addListener(listener)
        }
    }

    fun start() {
        if (livenessJob?.isActive == true) return
        livenessJob = scope.launch {
            while (isActive) {
                delay(LIVENESS_INTERVAL_MS)
                checkLiveness()
            }
        }
    }

    fun stop() {
        livenessJob?.cancel()
        livenessJob = null
        listeners.forEach { (player, listener) -> player.removeListener(listener) }
        listeners.clear()
    }

    private fun handlePlayerError(player: ExoPlayer, error: PlaybackException) {
        consecutiveFailures++
        healthyTicks = 0
        val itemId = currentItemId()
        Log.e(TAG, "Playback failure #$consecutiveFailures on item $itemId: ${error.errorCodeName}", error)
        telemetry.reportError(itemId, "${error.errorCodeName}: ${error.message ?: "playback failed"}")

        when (consecutiveFailures) {
            1 -> {
                Log.w(TAG, "Recovery 1/4: retrying current item")
                player.prepare()
                player.play()
            }
            2 -> {
                Log.w(TAG, "Recovery 2/4: skipping damaged item $itemId")
                onSkipItem()
            }
            3 -> {
                Log.w(TAG, "Recovery 3/4: reloading playlist")
                onReloadPlaylist()
            }
            else -> {
                Log.w(TAG, "Recovery 4/4: restarting player activity")
                restartPlayerActivity("supervisor_escalation")
                // Reset so a later, unrelated fault starts the ladder from the top
                // instead of restarting the activity on every single error.
                consecutiveFailures = 0
            }
        }
    }

    private fun checkLiveness() {
        val activePlayer = players.find { it.playWhenReady && it.playbackState == Player.STATE_READY }
        if (activePlayer == null || !activePlayer.isPlaying) return

        val currentPos = activePlayer.currentPosition
        val lastPos = lastPositions[activePlayer] ?: -1L

        if (currentPos == lastPos && currentPos > 0) {
            val count = (frozenCounts[activePlayer] ?: 0) + 1
            frozenCounts[activePlayer] = count
            Log.w(TAG, "Position stuck at $currentPos (tick $count/$FROZEN_TICKS_BEFORE_RECOVERY)")

            if (count >= FROZEN_TICKS_BEFORE_RECOVERY) {
                frozenCounts[activePlayer] = 0
                // A wedged decoder emits no error, so synthesise one and enter the same
                // ladder — including its escalation, so a repeatedly wedging item is
                // eventually skipped rather than re-prepared forever.
                handlePlayerError(
                    activePlayer,
                    PlaybackException(
                        "Decoder wedged at ${currentPos}ms",
                        null,
                        PlaybackException.ERROR_CODE_DECODER_INIT_FAILED
                    )
                )
            }
            return
        }

        lastPositions[activePlayer] = currentPos
        frozenCounts[activePlayer] = 0

        // Only forgive past failures once playback has genuinely run for a while;
        // resetting on the first healthy tick would let a flapping item ride rung 1
        // indefinitely without ever being skipped.
        if (consecutiveFailures > 0) {
            healthyTicks++
            if (healthyTicks >= HEALTHY_TICKS_TO_CLEAR) {
                Log.i(TAG, "Playback healthy again; clearing recovery state")
                consecutiveFailures = 0
                healthyTicks = 0
            }
        }
    }

    private fun restartPlayerActivity(reason: String) {
        Log.w(TAG, "Restarting player activity for recovery: $reason")
        PlayerLauncher.launch(context, delayMs = PlayerLauncher.WARM_RESTART_MS, reason = reason)
    }

    companion object {
        private const val TAG = "PlayerSupervisor"
        private const val LIVENESS_INTERVAL_MS = 10_000L
        private const val FROZEN_TICKS_BEFORE_RECOVERY = 3
        private const val HEALTHY_TICKS_TO_CLEAR = 2
    }
}
