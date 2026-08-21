package com.olrac.signage.data

import android.view.KeyEvent
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MaintenanceGestureTest {

    /** Feeds every key but the last, asserting none of them match early. */
    private fun MaintenanceGesture.typePrefix(startMs: Long = 0L, stepMs: Long = 100L) {
        MaintenanceGesture.SEQUENCE.dropLast(1).forEachIndexed { index, key ->
            assertFalse(record(key, startMs + index * stepMs))
        }
    }

    @Test
    fun `full sequence in order unlocks`() {
        val gesture = MaintenanceGesture()
        gesture.typePrefix()
        assertTrue(gesture.record(MaintenanceGesture.SEQUENCE.last(), 400L))
    }

    @Test
    fun `sequence spread beyond the window does not unlock`() {
        val gesture = MaintenanceGesture()
        gesture.typePrefix(stepMs = 10L)
        // Last key arrives after the first presses have aged out.
        assertFalse(gesture.record(MaintenanceGesture.SEQUENCE.last(), MaintenanceGesture.WINDOW_MS + 1))
    }

    @Test
    fun `an unrelated key in the middle breaks the sequence`() {
        val gesture = MaintenanceGesture()
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_UP, 0L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_UP, 100L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_LEFT, 200L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_DOWN, 300L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_DOWN, 400L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_CENTER, 500L))
    }

    @Test
    fun `remotes sending ENTER for OK still unlock`() {
        val gesture = MaintenanceGesture()
        gesture.typePrefix()
        assertTrue(gesture.record(KeyEvent.KEYCODE_ENTER, 400L))
    }

    @Test
    fun `the old back-heavy sequence no longer unlocks`() {
        val gesture = MaintenanceGesture()
        assertFalse(gesture.record(KeyEvent.KEYCODE_BACK, 0L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_BACK, 100L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_BACK, 200L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_RIGHT, 300L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_RIGHT, 400L))
    }

    @Test
    fun `noise before the sequence does not prevent a match`() {
        val gesture = MaintenanceGesture()
        assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_LEFT, 0L))
        assertFalse(gesture.record(KeyEvent.KEYCODE_BACK, 50L))
        gesture.typePrefix(startMs = 100L)
        assertTrue(gesture.record(MaintenanceGesture.SEQUENCE.last(), 500L))
    }

    @Test
    fun `matching twice requires typing the sequence again`() {
        val gesture = MaintenanceGesture()
        gesture.typePrefix()
        assertTrue(gesture.record(MaintenanceGesture.SEQUENCE.last(), 400L))
        // Buffer cleared on match, so one more OK must not re-open it.
        assertFalse(gesture.record(MaintenanceGesture.SEQUENCE.last(), 450L))
    }
}
