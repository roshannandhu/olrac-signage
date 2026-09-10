package com.olrac.signage.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CornerTapCounterTest {
    @Test
    fun sevenTapsWithinWindowUnlock() {
        val c = CornerTapCounter(windowMs = 3_000L)
        repeat(6) { i -> assertFalse(c.record(i * 100L)) }
        assertTrue("7th quick tap should unlock", c.record(700L))
    }

    @Test
    fun tapsSpreadPastWindowNeverUnlock() {
        val c = CornerTapCounter(windowMs = 3_000L)
        // One tap every 2s: the 3s window never holds more than two at once.
        var unlocked = false
        for (i in 0 until 12) {
            if (c.record(i * 2_000L)) unlocked = true
        }
        assertFalse("slow taps must not accumulate to an unlock", unlocked)
    }

    @Test
    fun unlockResetsTheRun() {
        val c = CornerTapCounter(windowMs = 3_000L)
        repeat(7) { i -> c.record(i * 100L) }   // first unlock
        // Immediately after, a single tap must not re-fire.
        assertFalse(c.record(750L))
    }
}
