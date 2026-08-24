package com.olrac.signage.ui

import android.graphics.Color as AndroidColor
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import android.view.LayoutInflater
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import com.olrac.signage.R
import com.olrac.signage.data.PlayCompletion
import com.olrac.signage.data.PlayEndReason
import com.olrac.signage.data.PlaylistItemEntity
import com.olrac.signage.data.TransitionSpec
import com.olrac.signage.data.TransitionSpecResolver
import com.olrac.signage.data.TransitionType
import com.olrac.signage.telemetry.PlaybackTelemetry
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.coroutines.withContext
import java.io.File
import java.util.WeakHashMap
import kotlin.coroutines.resume

@Composable
fun PlayerScreen(viewModel: PlayerViewModel = viewModel()) {
    val playlist by viewModel.playlist.collectAsState()
    val context = LocalContext.current
    val telemetry = remember(context) { PlaybackTelemetry(context) }

    LaunchedEffect(playlist.isEmpty()) {
        if (playlist.isEmpty()) telemetry.reportIdle()
    }

    if (playlist.isEmpty()) {
        Box(
            modifier = Modifier.fillMaxSize().background(Color.Black),
            contentAlignment = Alignment.Center
        ) {
            Text(text = "OLRAC Signage\nWaiting for assigned content", color = Color.White)
        }
        return
    }

    DualSurfacePlayer(playlist, telemetry, onReloadPlaylist = { viewModel.reloadPlaylist() })
}

@Composable
private fun DualSurfacePlayer(
    playlist: List<PlaylistItemEntity>,
    telemetry: PlaybackTelemetry,
    onReloadPlaylist: () -> Unit
) {
    val context = LocalContext.current
    val visiblePlaybackBaselines = remember { WeakHashMap<ExoPlayer, DecoderSnapshot>() }
    val players = remember {
        List(2) {
            ExoPlayer.Builder(context).build().apply {
                videoScalingMode = C.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING
            }
        }
    }
    val transitionProgress = remember { Animatable(0f) }
    val transitionMutex = remember { Mutex() }
    var currentIndex by remember { mutableIntStateOf(0) }
    var currentSlot by remember { mutableIntStateOf(0) }
    var playbackEpoch by remember { mutableIntStateOf(0) }
    var currentItemId by remember { mutableStateOf<Int?>(null) }
    var currentItemStartedAtMs by remember { mutableStateOf<Long?>(null) }

    val scope = androidx.compose.runtime.rememberCoroutineScope()
    // advance() must be declared before supervisor can use it in onSkipItem,
    // but wait, advance() is declared later... Let's declare a reference.
    // Actually, advance() is a suspend function, we can't easily reference it before it's declared if it's a local function.
    // Let's declare it as a var or just move the supervisor down?
    // Wait, let's just insert supervisor AFTER advance() is declared.

    DisposableEffect(players) {
        val listeners = players.associateWith { player ->
            object : Player.Listener {
                override fun onRenderedFirstFrame() {
                    player.videoDecoderCounters?.let { counters ->
                        counters.ensureUpdated()
                        visiblePlaybackBaselines[player] = DecoderSnapshot(
                            rendered = counters.renderedOutputBufferCount,
                            dropped = counters.droppedBufferCount
                        )
                    }
                }
            }.also(player::addListener)
        }
        onDispose {
            listeners.forEach { (player, listener) -> player.removeListener(listener) }
            players.forEach(ExoPlayer::release)
        }
    }

    // Anything left mid-play by a power cut or a process death is written down before the
    // first new item starts, using the last progress the checkpoint recorded.
    LaunchedEffect(Unit) { recoverInterruptedPlay(context) }

    val itemIds = playlist.joinToString(",") { it.id.toString() }
    LaunchedEffect(itemIds) {
        val preservedIndex = currentItemId?.let { id -> playlist.indexOfFirst { it.id == id } } ?: -1
        // A re-sync that drops the playing item abandons it mid-play. Clear the clock, because
        // the start-time guards below only stamp it when null: left set, the next advance()
        // would record the *incoming* item using the *outgoing* item's start time, attributing
        // the play to the wrong media and inflating its duration (so completed/partial too).
        if (preservedIndex < 0) {
            // It was on screen and the audience saw part of it, so it is a partial play
            // rather than nothing. Dropping it here quietly undercounted every screen whose
            // playlist was edited during the day. The checkpoint already holds everything
            // needed to write it, and is the same path a power cut recovers through.
            currentItemStartedAtMs = null
            recoverInterruptedPlay(context)
        }
        currentIndex = when {
            preservedIndex >= 0 -> preservedIndex
            currentIndex in playlist.indices -> currentIndex
            else -> 0
        }
        currentItemId = playlist[currentIndex].id
        playbackEpoch++
    }

    val safeIndex = currentIndex.coerceIn(playlist.indices)
    val nextIndex = (safeIndex + 1) % playlist.size
    val currentItem = playlist[safeIndex]
    val nextItem = playlist[nextIndex]
    val incomingSlot = 1 - currentSlot
    val transitionSpec = TransitionSpecResolver.resolve(currentItem)

    LaunchedEffect(currentItem.id, nextItem.id, currentSlot, playbackEpoch) {
        preparePlayer(players[currentSlot], currentItem, autoPlay = currentItem.type == "video")
        if (playlist.size > 1) {
            preparePlayer(players[incomingSlot], nextItem, autoPlay = false)
        }
    }

    suspend fun recordPlayEvent(
        item: PlaylistItemEntity,
        startedAtMs: Long,
        reason: PlayEndReason,
        error: String? = null,
        finishedAtMs: Long = System.currentTimeMillis()
    ) {
        val durationMs = PlayCompletion.durationMs(startedAtMs, finishedAtMs)
        val prefs = context.getSharedPreferences("signage_prefs", android.content.Context.MODE_PRIVATE)
        // null, not 0, when the device has never reached the server. The upload uses that
        // to tell "corrected with a known offset" apart from "never corrected at all", and
        // repairs only the latter. Storing 0 made the two indistinguishable, so a week of
        // plays from a clock-skewed TV kept its wrong hours forever.
        val offset = if (prefs.contains("server_time_offset_ms")) {
            prefs.getLong("server_time_offset_ms", 0L)
        } else {
            null
        }

        val formatter = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US).apply {
            timeZone = java.util.TimeZone.getTimeZone("UTC")
        }

        // A span that cannot be true tells us nothing about delivery, so it must not be
        // allowed to claim a complete play.
        val effectiveReason = if (
            reason == PlayEndReason.PLAYED_TO_END &&
            !PlayCompletion.isPlausible(startedAtMs, finishedAtMs)
        ) PlayEndReason.INTERRUPTED else reason

        // 1970 Clock Drift Edge Case: If the TV lost power offline and has no RTC battery, 
        // it resets to Jan 1 1970. Day-parting is broken and we cannot mathematically prove 
        // when this ad played if NTP syncs before the next heartbeat. Flag it so it isn't billed.
        val isTimeValid = startedAtMs > 1704067200000L // Jan 1, 2024
        val finalError = if (!isTimeValid && error == null) "time_invalid_rtc_reset" else error
        
        // Also discard any stale offset from a previous timeline if the clock reset.
        val effectiveOffset = if (isTimeValid) offset else null

        // Same id the checkpoint minted for this play, so a crash between this insert and
        // the checkpoint being cleared cannot produce a second record for it.
        val eventId = prefs.getString(CHECKPOINT_EVENT_ID, null)
            ?.takeIf { prefs.getInt(CHECKPOINT_ITEM_ID, -1) == item.id }
            ?: java.util.UUID.randomUUID().toString()

        val event = com.olrac.signage.data.PlayEventEntity(
            eventId = eventId,
            mediaId = item.contentId.takeIf { it > 0 },
            playlistId = item.playlistId,
            campaignId = null, // Derived server side from the playlist; see routers/screens.py
            deviceStartedAt = formatter.format(java.util.Date(startedAtMs)),
            deviceFinishedAt = formatter.format(java.util.Date(finishedAtMs)),
            correctedStartedAt = formatter.format(java.util.Date(startedAtMs + (effectiveOffset ?: 0L))),
            correctedFinishedAt = formatter.format(java.util.Date(finishedAtMs + (effectiveOffset ?: 0L))),
            durationMs = durationMs,
            status = PlayCompletion.status(effectiveReason, finalError),
            errorMessage = finalError,
            clockOffsetMs = effectiveOffset
        )

        val dao = com.olrac.signage.data.AppDatabase.getDatabase(context).playEventDao()
        dao.insert(event)
        clearPlayCheckpoint(context)

        // Keep the queue bounded. Only ever trims when the backlog is already enormous,
        // which the drain loop in ProofOfPlayWorker now makes very unlikely.
        //
        // Checked every QUEUE_CHECK_EVERY plays rather than on each one: COUNT(*) has no
        // index to use, and a full scan of a queue this size on cheap TV storage is real
        // work to repeat for every advert when the answer changes by one each time.
        if (playsSinceQueueCheck.incrementAndGet() >= QUEUE_CHECK_EVERY) {
            playsSinceQueueCheck.set(0)
            trimQueueIfOversized(dao)
        }
    }

    suspend fun advance(reason: PlayEndReason = PlayEndReason.PLAYED_TO_END) {
        transitionMutex.withLock {
            val activeIndex = currentIndex.coerceIn(playlist.indices)
            val outgoingItem = playlist[activeIndex]
            val outgoingSlot = currentSlot
            val outgoingPlayer = players[outgoingSlot]

            if (outgoingItem.type == "video") {
                outgoingPlayer.videoDecoderCounters?.let { counters ->
                    counters.ensureUpdated()
                    val baseline = visiblePlaybackBaselines[outgoingPlayer] ?: DecoderSnapshot(0, 0)
                    Log.i(
                        PERFORMANCE_TAG,
                        "item=${outgoingItem.id} rendered=${counters.renderedOutputBufferCount} " +
                            "dropped=${counters.droppedBufferCount} " +
                            "visibleRendered=${counters.renderedOutputBufferCount - baseline.rendered} " +
                            "visibleDropped=${counters.droppedBufferCount - baseline.dropped} " +
                            "maxConsecutiveDropped=${counters.maxConsecutiveDroppedBufferCount}"
                    )
                }
            }
            
            currentItemStartedAtMs?.let { startedAt ->
                val error = outgoingPlayer.playerError?.message
                recordPlayEvent(outgoingItem, startedAt, reason, error)
            }
            currentItemStartedAtMs = null
            clearPlayCheckpoint(context)

            if (playlist.size == 1) {
                if (outgoingItem.type == "video") {
                    outgoingPlayer.seekTo(0)
                    outgoingPlayer.playWhenReady = true
                }
                playbackEpoch++
                return@withLock
            }

            val targetIndex = (activeIndex + 1) % playlist.size
            val targetItem = playlist[targetIndex]
            val targetSlot = 1 - outgoingSlot
            val targetPlayer = players[targetSlot]
            preparePlayer(targetPlayer, targetItem, autoPlay = false)

            val targetReady = when (targetItem.type) {
                "video" -> awaitPlayerReady(targetPlayer)
                "image" -> isImageDecodable(targetItem.localPath)
                else -> false
            }
            if (!targetReady) {
                telemetry.reportError(
                    targetItem.id,
                    "Unable to prepare ${targetItem.type} item ${targetItem.id}; cached media is missing or corrupt"
                )
                // Retain the last good frame and skip the bad item instead of
                // exposing a black surface.
                val fallbackIndex = (targetIndex + 1) % playlist.size
                if (fallbackIndex == activeIndex) {
                    playbackEpoch++
                } else {
                    currentIndex = fallbackIndex
                    currentItemId = playlist[fallbackIndex].id
                    playbackEpoch++
                }
                return@withLock
            }

            if (targetItem.type == "video") {
                targetPlayer.volume = 0f
                targetPlayer.playWhenReady = true
            }

            val spec = TransitionSpecResolver.resolve(outgoingItem)
            transitionProgress.snapTo(0f)
            if (spec.type != TransitionType.NONE) {
                transitionProgress.animateTo(
                    targetValue = 1f,
                    animationSpec = tween(durationMillis = spec.durationMs)
                ) {
                    outgoingPlayer.volume = 1f - value
                    targetPlayer.volume = value
                }
            }

            outgoingPlayer.playWhenReady = false
            outgoingPlayer.volume = 0f
            targetPlayer.volume = 1f
            currentIndex = targetIndex
            currentItemId = targetItem.id
            currentSlot = targetSlot
            transitionProgress.snapTo(0f)
        }
    }

    val supervisor = remember(players) {
        com.olrac.signage.service.PlayerSupervisor(
            context = context,
            players = players,
            telemetry = telemetry,
            currentItemId = { currentItemId },
            // The supervisor only skips an item it could not play, so this must never be
            // recorded as a completed play -- that is the case the advertiser is paying for.
            onSkipItem = { scope.launch { advance(PlayEndReason.SKIPPED) } },
            onReloadPlaylist = onReloadPlaylist
        )
    }

    DisposableEffect(supervisor) {
        supervisor.start()
        onDispose { supervisor.stop() }
    }

    LaunchedEffect(currentItem.id, currentSlot, playbackEpoch, transitionSpec) {
        if (currentItem.type == "image") {
            if (!isImageDecodable(currentItem.localPath)) {
                telemetry.reportError(
                    currentItem.id,
                    "Unable to decode image item ${currentItem.id}; cached media is missing or corrupt"
                )
                delay(1_000L)
                advance(PlayEndReason.FAILED)
                return@LaunchedEffect
            }
            telemetry.reportPlaying(currentItem.id)
            if (currentItemStartedAtMs == null) currentItemStartedAtMs = System.currentTimeMillis()
            val imageStartedAt = currentItemStartedAtMs ?: System.currentTimeMillis()
            writePlayCheckpoint(context, currentItem, imageStartedAt, imageStartedAt)
            // Slept in slices so the checkpoint stays current; a power cut then loses at
            // most CHECKPOINT_INTERVAL_MS of the record rather than the whole play.
            val totalMs = currentItem.duration.coerceAtLeast(1) * 1_000L
            var elapsed = 0L
            while (elapsed < totalMs) {
                val slice = minOf(CHECKPOINT_INTERVAL_MS, totalMs - elapsed)
                delay(slice)
                elapsed += slice
                writePlayCheckpoint(context, currentItem, imageStartedAt, System.currentTimeMillis())
            }
            advance(PlayEndReason.PLAYED_TO_END)
        } else if (currentItem.type == "video") {
            val activePlayer = players[currentSlot]
            val transitionLeadMs = if (transitionSpec.type == TransitionType.NONE) {
                100L
            } else {
                transitionSpec.durationMs + 120L
            }
            var reportedPlaying = false
            var lastCheckpointMs = 0L
            while (true) {
                val nowMs = System.currentTimeMillis()
                val durationMs = activePlayer.duration
                if (!reportedPlaying && activePlayer.playbackState == Player.STATE_READY) {
                    telemetry.reportPlaying(currentItem.id)
                    reportedPlaying = true
                    if (currentItemStartedAtMs == null) currentItemStartedAtMs = System.currentTimeMillis()
                }
                activePlayer.playerError?.let { error ->
                    telemetry.reportError(currentItem.id, error.message ?: "Video playback failed")
                }
                val failed = activePlayer.playerError != null
                val reachedEnd = activePlayer.playbackState == Player.STATE_ENDED ||
                    (durationMs != C.TIME_UNSET &&
                        durationMs > 0 &&
                        activePlayer.currentPosition >= (durationMs - transitionLeadMs).coerceAtLeast(0L))
                if (failed || reachedEnd) {
                    // The player knows why it is moving on, so the record says so directly.
                    // Reaching the planned hand-over point *is* a complete play: the lead
                    // time exists so the transition can cover the last frames, and the
                    // previous arithmetic check had no way to know that.
                    advance(if (failed) PlayEndReason.FAILED else PlayEndReason.PLAYED_TO_END)
                    break
                }
                currentItemStartedAtMs?.let { startedAt ->
                    if (nowMs - lastCheckpointMs >= CHECKPOINT_INTERVAL_MS) {
                        writePlayCheckpoint(context, currentItem, startedAt, nowMs)
                        lastCheckpointMs = nowMs
                    }
                }
                delay(16L)
            }
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize().background(Color.Black)) {
        val density = LocalDensity.current
        val widthPx = with(density) { maxWidth.toPx() }
        val heightPx = with(density) { maxHeight.toPx() }
        val progress = transitionProgress.value

        // Render by physical slot, not by current/next role. A preloaded video must
        // keep the same PlayerView/TextureView when it becomes current; moving it to
        // another composition position detaches the surface and creates a black flash.
        val slot0IsCurrent = currentSlot == 0
        PlaybackSurface(
            item = if (slot0IsCurrent) currentItem else nextItem,
            player = players[0],
            modifier = Modifier
                .fillMaxSize()
                .transitionLayer(
                    transitionSpec,
                    progress,
                    incoming = !slot0IsCurrent,
                    widthPx,
                    heightPx
                )
        )
        if (playlist.size > 1) {
            PlaybackSurface(
                item = if (slot0IsCurrent) nextItem else currentItem,
                player = players[1],
                modifier = Modifier
                    .fillMaxSize()
                    .transitionLayer(
                        transitionSpec,
                        progress,
                        incoming = slot0IsCurrent,
                        widthPx,
                        heightPx
                    )
            )
        }
    }
}

private const val PERFORMANCE_TAG = "OlracPlaybackMetrics"
private const val TAG = "PlayerScreen"

/**
 * Ceiling on locally queued proof of play. Roughly a fortnight of continuous playback on a
 * six-second loop, so it is only ever reached by a screen that has been unable to reach the
 * server for a very long time.
 */
private const val MAX_QUEUED_PLAY_EVENTS = 200_000

/** How many plays between queue-size checks. */
private const val QUEUE_CHECK_EVERY = 200

private val playsSinceQueueCheck = java.util.concurrent.atomic.AtomicInteger(0)

/** How often the on-screen item's progress is written down. */
private const val CHECKPOINT_INTERVAL_MS = 5_000L

private const val CHECKPOINT_EVENT_ID = "current_play_event_id"
private const val CHECKPOINT_ITEM_ID = "current_play_item_id"
private const val CHECKPOINT_STARTED_AT = "current_play_started_at"
private const val CHECKPOINT_LAST_ALIVE = "current_play_last_alive"
private const val CHECKPOINT_CONTENT_ID = "current_play_content_id"
private const val CHECKPOINT_PLAYLIST_ID = "current_play_playlist_id"

/**
 * Drop the oldest queued plays if the backlog has grown past what the device should hold.
 *
 * Top level rather than a local function: Kotlin resolves local functions in declaration
 * order, so calling this from recordPlayEvent above required it to be declared first, and
 * it needs nothing from the composable's scope anyway.
 */
private suspend fun trimQueueIfOversized(dao: com.olrac.signage.data.PlayEventDao) {
    val queued = dao.countEvents()
    if (queued > MAX_QUEUED_PLAY_EVENTS) {
        val removed = dao.trimOldest(MAX_QUEUED_PLAY_EVENTS)
        Log.w(
            TAG,
            "Play event queue reached $queued; dropped $removed oldest events to protect the media cache"
        )
    }
}

/**
 * Note that an item is on screen, so a play interrupted by a power cut is not lost.
 *
 * A play was only ever written when the *next* one began, inside advance(). Pull the mains
 * lead on a signage screen -- which is how they are usually turned off -- and the advert
 * playing at that moment was never recorded. Always in the operator's favour and never the
 * advertiser's, which is the wrong way round for a number that gets invoiced.
 *
 * `lastAlive` is refreshed as the item plays, so the recovered record can say how far it
 * actually got rather than guessing.
 */
private suspend fun writePlayCheckpoint(
    context: android.content.Context,
    item: PlaylistItemEntity,
    startedAtMs: Long,
    lastAliveMs: Long
): String = withContext(Dispatchers.IO) {
    // Off the main thread. The durable commit below is a synchronous file write, and this
    // is called from the video loop that also drives frame timing -- a blocking write there
    // would show up as a stutter on exactly the cheap panels this app targets.
    val prefs = context.getSharedPreferences("signage_prefs", android.content.Context.MODE_PRIVATE)
    // One id per play, minted when the play starts and reused by whichever path ends up
    // writing the record.
    //
    // Without this the two paths could both fire: recordPlayEvent inserts the real event,
    // the mains is pulled before the checkpoint is cleared, and the next launch recovers
    // the same play as a second event with a fresh UUID -- one play counted twice, in the
    // direction that overstates delivery. Sharing the id makes the pair collapse: Room
    // REPLACEs on the primary key, and the server's ON CONFLICT DO NOTHING ignores the
    // loser. Whichever record lands first wins, and both describe the same play.
    val existing = prefs.getString(CHECKPOINT_EVENT_ID, null)
        ?.takeIf { prefs.getInt(CHECKPOINT_ITEM_ID, -1) == item.id && prefs.getLong(CHECKPOINT_STARTED_AT, 0L) == startedAtMs }
    val eventId = existing ?: java.util.UUID.randomUUID().toString()
    prefs.edit()
        .putString(CHECKPOINT_EVENT_ID, eventId)
        .putInt(CHECKPOINT_ITEM_ID, item.id)
        .putInt(CHECKPOINT_CONTENT_ID, item.contentId)
        .putInt(CHECKPOINT_PLAYLIST_ID, item.playlistId ?: -1)
        .putLong(CHECKPOINT_STARTED_AT, startedAtMs)
        .putLong(CHECKPOINT_LAST_ALIVE, lastAliveMs)
        // commit, not apply: a power cut kills the kernel, so an asynchronous write may
        // never reach disk -- and surviving exactly that is the whole point of this record.
        .commit()
    eventId
}

/**
 * Write down a play that was on screen when the app stopped, then clear the checkpoint.
 *
 * Called at launch (recovering a power cut or a process death) and when a re-sync drops the
 * playing item. Always recorded as a partial play: it demonstrably did not reach its end,
 * and `lastAlive` is the furthest point we can honestly claim it got to.
 *
 * Safe to call when there is nothing to recover, and safe to call twice -- the checkpoint
 * is removed as part of the same operation.
 */
private suspend fun recoverInterruptedPlay(context: android.content.Context) {
    val prefs = context.getSharedPreferences("signage_prefs", android.content.Context.MODE_PRIVATE)
    val itemId = prefs.getInt(CHECKPOINT_ITEM_ID, -1)
    val startedAt = prefs.getLong(CHECKPOINT_STARTED_AT, 0L)
    if (itemId < 0 || startedAt <= 0L) return

    val lastAlive = prefs.getLong(CHECKPOINT_LAST_ALIVE, startedAt).coerceAtLeast(startedAt)
    val contentId = prefs.getInt(CHECKPOINT_CONTENT_ID, -1)
    val playlistId = prefs.getInt(CHECKPOINT_PLAYLIST_ID, -1)
    // The id this play was given when it started. If recordPlayEvent already wrote the
    // real record before the process died, this insert collapses onto it rather than
    // counting the play a second time.
    val eventId = prefs.getString(CHECKPOINT_EVENT_ID, null) ?: java.util.UUID.randomUUID().toString()
    clearPlayCheckpoint(context)

    if (!PlayCompletion.isPlausible(startedAt, lastAlive)) {
        Log.w(TAG, "Discarding interrupted play for item $itemId: implausible timestamps")
        return
    }

    val offset = if (prefs.contains("server_time_offset_ms")) {
        prefs.getLong("server_time_offset_ms", 0L)
    } else {
        null
    }
    val formatter = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US).apply {
        timeZone = java.util.TimeZone.getTimeZone("UTC")
    }
    
    val isTimeValid = startedAt > 1704067200000L // Jan 1, 2024
    val finalError = if (!isTimeValid) "time_invalid_rtc_reset" else null
    val effectiveOffset = if (isTimeValid) offset else null

    val event = com.olrac.signage.data.PlayEventEntity(
        eventId = eventId,
        mediaId = contentId.takeIf { it > 0 },
        playlistId = playlistId.takeIf { it > 0 },
        campaignId = null,
        deviceStartedAt = formatter.format(java.util.Date(startedAt)),
        deviceFinishedAt = formatter.format(java.util.Date(lastAlive)),
        correctedStartedAt = formatter.format(java.util.Date(startedAt + (effectiveOffset ?: 0L))),
        correctedFinishedAt = formatter.format(java.util.Date(lastAlive + (effectiveOffset ?: 0L))),
        durationMs = PlayCompletion.durationMs(startedAt, lastAlive),
        status = PlayCompletion.status(PlayEndReason.INTERRUPTED, finalError),
        errorMessage = finalError,
        clockOffsetMs = effectiveOffset
    )
    com.olrac.signage.data.AppDatabase.getDatabase(context).playEventDao().insert(event)
    Log.i(TAG, "Recovered interrupted play for item $itemId (${event.durationMs}ms)")
}

private suspend fun clearPlayCheckpoint(context: android.content.Context) = withContext(Dispatchers.IO) {
    context.getSharedPreferences("signage_prefs", android.content.Context.MODE_PRIVATE)
        .edit()
        .remove(CHECKPOINT_EVENT_ID)
        .remove(CHECKPOINT_ITEM_ID)
        .remove(CHECKPOINT_CONTENT_ID)
        .remove(CHECKPOINT_PLAYLIST_ID)
        .remove(CHECKPOINT_STARTED_AT)
        .remove(CHECKPOINT_LAST_ALIVE)
        .commit()
    Unit
}

private data class DecoderSnapshot(val rendered: Int, val dropped: Int)

private suspend fun isImageDecodable(localPath: String?): Boolean = withContext(Dispatchers.IO) {
    if (localPath.isNullOrBlank()) return@withContext false
    val file = File(localPath)
    if (!file.isFile || file.length() == 0L) return@withContext false
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, options)
    options.outWidth > 0 && options.outHeight > 0
}

@Composable
private fun PlaybackSurface(
    item: PlaylistItemEntity,
    player: ExoPlayer,
    modifier: Modifier
) {
    // The server already resolved this from the per-item override and the screen's
    // orientation, so a portrait advert on a landscape panel just works. Turning the
    // surface is cheaper and sharper than re-encoding the media rotated.
    // 90/270 swap width and height, so the frame is also scaled to fit the panel's other
    // axis — without that a rotated video is cropped to the panel's short side.
    val rotated = item.rotation == 90 || item.rotation == 270
    val surface = if (item.rotation % 360 == 0) modifier else modifier.then(
        Modifier.graphicsLayer {
            rotationZ = item.rotation.toFloat()
            if (rotated && size.width > 0f && size.height > 0f) {
                val fit = minOf(size.width / size.height, size.height / size.width)
                scaleX = fit
                scaleY = fit
            }
        }
    )
    // "cover" fills the panel and crops; "contain" shows the whole frame letterboxed.
    val imageScale = if (item.fitMode == "cover") ContentScale.Crop else ContentScale.Fit

    when (item.type) {
        "video" -> AndroidView(
            factory = { context ->
                (LayoutInflater.from(context).inflate(R.layout.player_surface, null, false) as PlayerView).apply {
                    setShutterBackgroundColor(AndroidColor.TRANSPARENT)
                    this.player = player
                }
            },
            update = { it.player = player },
            modifier = surface
        )

        "image" -> AsyncImage(
            model = item.localPath?.let(::File),
            contentDescription = "Signage image",
            contentScale = imageScale,
            modifier = surface
        )

        else -> Box(modifier = modifier.background(Color.Black))
    }
}

private fun Modifier.transitionLayer(
    spec: TransitionSpec,
    progress: Float,
    incoming: Boolean,
    widthPx: Float,
    heightPx: Float
): Modifier = graphicsLayer {
    when (spec.type) {
        TransitionType.NONE -> alpha = if (incoming) 0f else 1f
        TransitionType.FADE -> alpha = if (incoming) progress else 1f - progress
        TransitionType.ZOOM -> {
            alpha = if (incoming) progress else 1f - progress
            val scale = if (incoming) 0.9f + (0.1f * progress) else 1f + (0.1f * progress)
            scaleX = scale
            scaleY = scale
        }

        TransitionType.SLIDE_LEFT -> translationX = if (incoming) {
            widthPx * (1f - progress)
        } else {
            -widthPx * progress
        }

        TransitionType.SLIDE_RIGHT -> translationX = if (incoming) {
            -widthPx * (1f - progress)
        } else {
            widthPx * progress
        }

        TransitionType.SLIDE_UP -> translationY = if (incoming) {
            heightPx * (1f - progress)
        } else {
            -heightPx * progress
        }

        TransitionType.SLIDE_DOWN -> translationY = if (incoming) {
            -heightPx * (1f - progress)
        } else {
            heightPx * progress
        }
    }
}

private fun preparePlayer(player: ExoPlayer, item: PlaylistItemEntity, autoPlay: Boolean) {
    if (item.type != "video" || item.localPath.isNullOrBlank()) {
        player.pause()
        player.clearMediaItems()
        return
    }

    val mediaId = item.id.toString()
    if (player.currentMediaItem?.mediaId != mediaId) {
        player.setMediaItem(
            MediaItem.Builder()
                .setMediaId(mediaId)
                .setUri(Uri.fromFile(File(item.localPath)))
                .build()
        )
        player.prepare()
    } else if (player.playbackState == Player.STATE_ENDED) {
        player.seekTo(0)
        player.prepare()
    }
    player.volume = if (autoPlay) 1f else 0f
    player.playWhenReady = autoPlay
}

private suspend fun awaitPlayerReady(player: ExoPlayer): Boolean {
    if (player.playbackState == Player.STATE_READY) return true
    return withTimeoutOrNull(10_000L) {
        suspendCancellableCoroutine { continuation ->
            val listener = object : Player.Listener {
                override fun onPlaybackStateChanged(playbackState: Int) {
                    if (playbackState == Player.STATE_READY && continuation.isActive) {
                        player.removeListener(this)
                        continuation.resume(true)
                    }
                }

                override fun onPlayerError(error: PlaybackException) {
                    if (continuation.isActive) {
                        player.removeListener(this)
                        continuation.resume(false)
                    }
                }
            }
            player.addListener(listener)
            continuation.invokeOnCancellation { player.removeListener(listener) }
        }
    } ?: false
}
