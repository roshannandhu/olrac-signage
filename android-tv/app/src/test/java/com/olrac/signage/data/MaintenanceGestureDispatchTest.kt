package com.olrac.signage.data

import android.view.KeyEvent
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Why the Activity records the gesture in dispatchKeyEvent and NOWHERE else.
 *
 * dispatchKeyEvent sees every key, and onKeyDown sees the ones the view tree did not
 * consume, so an Activity that records in both counts most presses twice.
 */
class MaintenanceGestureDispatchTest {

    private val sequence = MaintenanceGesture.SEQUENCE

    @Test
    fun `one press each completes the sequence`() {
        val gesture = MaintenanceGesture()
        val results = sequence.mapIndexed { i, key -> gesture.record(key, i * 100L) }
        assertTrue(results.last())
        assertFalse(results.dropLast(1).any { it })
    }

    @Test
    fun `recording every press twice never matches`() {
        val gesture = MaintenanceGesture()
        var now = 0L
        var matched = false
        for (key in sequence) {
            // The same physical press arriving from dispatchKeyEvent and then onKeyDown.
            matched = gesture.record(key, now++) || matched
            matched = gesture.record(key, now++) || matched
        }
        assertFalse("double-recorded presses must not reveal the pin prompt", matched)
    }

    @Test
    fun `the four keys before OK are not consumed so focus can still move`() {
        val gesture = MaintenanceGesture()
        sequence.dropLast(1).forEachIndexed { i, key ->
            assertFalse(
                "key $i must fall through to the focused button",
                gesture.record(key, i * 100L)
            )
        }
    }

    @Test
    fun `OK alone does not match so buttons stay clickable`() {
        val gesture = MaintenanceGesture()
        repeat(3) { i ->
            assertFalse(gesture.record(KeyEvent.KEYCODE_DPAD_CENTER, i * 100L))
        }
    }
}
