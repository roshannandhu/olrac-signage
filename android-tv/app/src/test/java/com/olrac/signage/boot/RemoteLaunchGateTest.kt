package com.olrac.signage.boot

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class RemoteLaunchGateTest {
    @Before
    fun reset() = RemoteLaunchGate.resetForTest()

    @Test
    fun theQueuedCopyOfOnePressIsIgnored() {
        // Pushed over the socket, then the heartbeat copy 8 s later -- the tablet's real timing.
        assertTrue("the first delivery acts", RemoteLaunchGate.allow(nowMs = 100_000L))
        assertFalse("the late copy must not drag the player back", RemoteLaunchGate.allow(nowMs = 108_000L))
    }

    @Test
    fun aGenuineSecondPressStillWorks() {
        assertTrue(RemoteLaunchGate.allow(nowMs = 100_000L))
        assertTrue("a press after the window acts again", RemoteLaunchGate.allow(nowMs = 100_000L + RemoteLaunchGate.DUPLICATE_WINDOW_MS))
    }

    @Test
    fun ignoredCopiesDoNotExtendTheWindow() {
        assertTrue(RemoteLaunchGate.allow(nowMs = 0L))
        assertFalse(RemoteLaunchGate.allow(nowMs = 20_000L))
        assertTrue("the window runs from the press that acted", RemoteLaunchGate.allow(nowMs = 30_000L))
    }
}
