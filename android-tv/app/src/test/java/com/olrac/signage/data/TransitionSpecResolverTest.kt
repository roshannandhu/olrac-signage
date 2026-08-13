package com.olrac.signage.data

import org.junit.Assert.assertEquals
import org.junit.Test

class TransitionSpecResolverTest {
    @Test
    fun itemOverrideWinsOverPlaylistDefault() {
        val spec = TransitionSpecResolver.resolve(
            itemTransition = "zoom",
            itemDurationMs = 850,
            playlistTransition = "slide_left",
            playlistDurationMs = 700
        )

        assertEquals(TransitionType.ZOOM, spec.type)
        assertEquals(850, spec.durationMs)
    }

    @Test
    fun playlistDefaultIsUsedWhenItemInherits() {
        val spec = TransitionSpecResolver.resolve(null, null, "slide_up", 900)

        assertEquals(TransitionType.SLIDE_UP, spec.type)
        assertEquals(900, spec.durationMs)
    }

    @Test
    fun malformedOrMissingValuesFallBackAndClamp() {
        val fallback = TransitionSpecResolver.resolve(null, null, "unknown", null)
        val clamped = TransitionSpecResolver.resolve("fade", 9_000, null, null)

        assertEquals(TransitionType.FADE, fallback.type)
        assertEquals(600, fallback.durationMs)
        assertEquals(3_000, clamped.durationMs)
    }
}
