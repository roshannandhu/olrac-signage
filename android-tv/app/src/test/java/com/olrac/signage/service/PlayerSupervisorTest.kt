package com.olrac.signage.service

import android.content.Context
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.olrac.signage.boot.PlayerLauncher
import com.olrac.signage.telemetry.PlaybackTelemetry
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkObject
import io.mockk.unmockkAll
import io.mockk.verify
import io.mockk.verifyOrder
import org.junit.After
import org.junit.Before
import org.junit.Test

class PlayerSupervisorTest {

    private lateinit var context: Context
    private lateinit var player: ExoPlayer
    private lateinit var telemetry: PlaybackTelemetry
    private lateinit var supervisor: PlayerSupervisor

    private var currentItemId: Int? = 1
    private var skipItemCalled = false
    private var reloadPlaylistCalled = false

    @Before
    fun setup() {
        context = mockk(relaxed = true)
        player = mockk(relaxed = true)
        telemetry = mockk(relaxed = true)

        skipItemCalled = false
        reloadPlaylistCalled = false

        mockkObject(PlayerLauncher)
        every { PlayerLauncher.launch(any(), any(), any()) } returns Unit

        supervisor = PlayerSupervisor(
            context = context,
            players = listOf(player),
            telemetry = telemetry,
            currentItemId = { currentItemId },
            onSkipItem = { skipItemCalled = true },
            onReloadPlaylist = { reloadPlaylistCalled = true }
        )
    }

    @After
    fun teardown() {
        unmockkAll()
    }

    @Test
    fun `escalates recovery ladder on consecutive errors`() {
        // Capture the listener added to the player
        val listenerCapture = mutableListOf<Player.Listener>()
        verify { player.addListener(capture(listenerCapture)) }
        val listener = listenerCapture.first()

        val exception = PlaybackException("test error", null, PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED)

        // 1st error -> retry
        listener.onPlayerError(exception)
        verify { player.prepare() }
        verify { player.play() }
        assert(!skipItemCalled)
        assert(!reloadPlaylistCalled)

        // 2nd error -> skip
        listener.onPlayerError(exception)
        assert(skipItemCalled)
        assert(!reloadPlaylistCalled)

        // 3rd error -> reload
        listener.onPlayerError(exception)
        assert(reloadPlaylistCalled)
        verify(exactly = 0) { PlayerLauncher.launch(any(), any(), any()) }

        // 4th error -> restart activity
        listener.onPlayerError(exception)
        verify(exactly = 1) { PlayerLauncher.launch(context, PlayerLauncher.WARM_RESTART_MS, "supervisor_escalation") }
        
        // 5th error -> resets and starts ladder from top (retry)
        listener.onPlayerError(exception)
        verify(exactly = 2) { player.prepare() } // 1st and 5th
    }
}
