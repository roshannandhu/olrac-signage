package com.olrac.signage.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlayCompletionTest {

    @Test
    fun `reaching the end is a completed play`() {
        assertEquals("completed", PlayCompletion.status(PlayEndReason.PLAYED_TO_END, null))
    }

    @Test
    fun `a short advert played in full is completed`() {
        // The regression this class exists for. A five-second advert was compared against
        // PlaylistItem.duration, which defaults to ten seconds when the media has never
        // been probed: 5000 < 10000 - 2000 made a complete play read as partial, and
        // completion rate is the number advertisers are billed on.
        //
        // Length is no longer part of the decision at all -- the player reports why it
        // moved on -- so the same call is correct for a 5-second and a 5-minute advert.
        assertEquals("completed", PlayCompletion.status(PlayEndReason.PLAYED_TO_END, null))
        assertEquals(5_000, PlayCompletion.durationMs(1_000_000L, 1_005_000L))
    }

    @Test
    fun `a skipped item is never completed`() {
        // The supervisor only skips what it could not play; claiming delivery here would
        // bill an advertiser for an advert nobody saw.
        assertEquals("partial", PlayCompletion.status(PlayEndReason.SKIPPED, null))
    }

    @Test
    fun `an interrupted item is partial`() {
        assertEquals("partial", PlayCompletion.status(PlayEndReason.INTERRUPTED, null))
    }

    @Test
    fun `a failure is an error however it ended`() {
        assertEquals("error", PlayCompletion.status(PlayEndReason.FAILED, null))
        assertEquals("error", PlayCompletion.status(PlayEndReason.FAILED, "decoder failed"))
        // An error message wins even when the loop thought it had reached the end.
        assertEquals("error", PlayCompletion.status(PlayEndReason.PLAYED_TO_END, "decoder failed"))
    }

    @Test
    fun `duration clamps a backwards clock jump to zero`() {
        // NTP correcting a cheap panel's clock mid-advert produced a negative span, which
        // went onto the wire as a negative Int and poisoned the duration totals.
        assertEquals(0, PlayCompletion.durationMs(1_000_000L, 900_000L))
    }

    @Test
    fun `duration clamps an absurd forward jump`() {
        val tenDays = 10L * 24 * 60 * 60 * 1000
        assertEquals(
            PlayCompletion.MAX_PLAUSIBLE_MS.toInt(),
            PlayCompletion.durationMs(0L, tenDays)
        )
    }

    @Test
    fun `plausibility rejects spans a play cannot have had`() {
        assertTrue(PlayCompletion.isPlausible(1_000L, 31_000L))
        assertTrue(PlayCompletion.isPlausible(1_000L, 1_000L))
        assertFalse(PlayCompletion.isPlausible(1_000L, 999L))
        assertFalse(PlayCompletion.isPlausible(0L, PlayCompletion.MAX_PLAUSIBLE_MS + 1))
    }

    @Test
    fun `boundary of the plausible window is accepted`() {
        assertTrue(PlayCompletion.isPlausible(0L, PlayCompletion.MAX_PLAUSIBLE_MS))
    }
}
