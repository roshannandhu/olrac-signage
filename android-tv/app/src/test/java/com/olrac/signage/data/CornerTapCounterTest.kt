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
    fun everyCornerCountsAndTheMiddleDoesNot() {
        // The tablet in portrait, 800 x 1280. The dashboard says "tap any corner".
        val w = 800
        val h = 1280
        assertTrue("top-left", CornerTapCounter.isCorner(30f, 30f, w, h))
        assertTrue("top-right", CornerTapCounter.isCorner(770f, 30f, w, h))
        assertTrue("bottom-left", CornerTapCounter.isCorner(30f, 1250f, w, h))
        assertTrue("bottom-right, which used to be ignored", CornerTapCounter.isCorner(770f, 1250f, w, h))
        assertFalse("centre", CornerTapCounter.isCorner(400f, 640f, w, h))
        assertFalse("middle of the top edge", CornerTapCounter.isCorner(400f, 30f, w, h))
        assertFalse("middle of the left edge", CornerTapCounter.isCorner(30f, 640f, w, h))
        assertFalse("no window yet", CornerTapCounter.isCorner(0f, 0f, 0, 0))
    }

    @Test
    fun unlockResetsTheRun() {
        val c = CornerTapCounter(windowMs = 3_000L)
        repeat(7) { i -> c.record(i * 100L) }   // first unlock
        // Immediately after, a single tap must not re-fire.
        assertFalse(c.record(750L))
    }
}
