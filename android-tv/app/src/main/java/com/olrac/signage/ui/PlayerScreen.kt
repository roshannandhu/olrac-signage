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

    val itemIds = playlist.joinToString(",") { it.id.toString() }
    LaunchedEffect(itemIds) {
        val preservedIndex = currentItemId?.let { id -> playlist.indexOfFirst { it.id == id } } ?: -1
        // A re-sync that drops the playing item abandons it mid-play. Clear the clock, because
        // the start-time guards below only stamp it when null: left set, the next advance()
        // would record the *incoming* item using the *outgoing* item's start time, attributing
        // the play to the wrong media and inflating its duration (so completed/partial too).
        if (preservedIndex < 0) currentItemStartedAtMs = null
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

    suspend fun recordPlayEvent(item: PlaylistItemEntity, startedAtMs: Long, error: String? = null) {
        val finishedAtMs = System.currentTimeMillis()
        val durationMs = (finishedAtMs - startedAtMs).toInt()
        val prefs = context.getSharedPreferences("signage_prefs", android.content.Context.MODE_PRIVATE)
        val offset = prefs.getLong("server_time_offset_ms", 0L)
        
        val formatter = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US).apply {
            timeZone = java.util.TimeZone.getTimeZone("UTC")
        }
        
        val status = if (error != null) "error"
            else if (item.type == "video" && durationMs < item.duration * 1000 - 2000) "partial" // rough cut-off check
            else "completed"
            
        val event = com.olrac.signage.data.PlayEventEntity(
            eventId = java.util.UUID.randomUUID().toString(),
            mediaId = item.contentId.takeIf { it > 0 },
            playlistId = item.playlistId,
            campaignId = null, // Campaign not currently linked to item in AppDatabase
            deviceStartedAt = formatter.format(java.util.Date(startedAtMs)),
            deviceFinishedAt = formatter.format(java.util.Date(finishedAtMs)),
            correctedStartedAt = formatter.format(java.util.Date(startedAtMs + offset)),
            correctedFinishedAt = formatter.format(java.util.Date(finishedAtMs + offset)),
            durationMs = durationMs,
            status = status,
            errorMessage = error
        )
        
        val dao = com.olrac.signage.data.AppDatabase.getDatabase(context).playEventDao()
        dao.insert(event)
    }

    suspend fun advance() {
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
                recordPlayEvent(outgoingItem, startedAt, error)
            }
            currentItemStartedAtMs = null

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
            onSkipItem = { scope.launch { advance() } },
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
                advance()
                return@LaunchedEffect
            }
            telemetry.reportPlaying(currentItem.id)
            if (currentItemStartedAtMs == null) currentItemStartedAtMs = System.currentTimeMillis()
            delay(currentItem.duration.coerceAtLeast(1) * 1_000L)
            advance()
        } else if (currentItem.type == "video") {
            val activePlayer = players[currentSlot]
            val transitionLeadMs = if (transitionSpec.type == TransitionType.NONE) {
                100L
            } else {
                transitionSpec.durationMs + 120L
            }
            var reportedPlaying = false
            while (true) {
                val durationMs = activePlayer.duration
                if (!reportedPlaying && activePlayer.playbackState == Player.STATE_READY) {
                    telemetry.reportPlaying(currentItem.id)
                    reportedPlaying = true
                    if (currentItemStartedAtMs == null) currentItemStartedAtMs = System.currentTimeMillis()
                }
                activePlayer.playerError?.let { error ->
                    telemetry.reportError(currentItem.id, error.message ?: "Video playback failed")
                }
                val shouldAdvance = activePlayer.playerError != null ||
                    activePlayer.playbackState == Player.STATE_ENDED ||
                    (durationMs != C.TIME_UNSET &&
                        durationMs > 0 &&
                        activePlayer.currentPosition >= (durationMs - transitionLeadMs).coerceAtLeast(0L))
                if (shouldAdvance) {
                    advance()
                    break
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
