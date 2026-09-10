package com.olrac.signage.data

/**
 * Touch-only escape to the maintenance PIN, for devices with no D-pad remote — touch panels
 * and phones — where the [MaintenanceGesture] Up-Up-Down-Down-OK sequence is unreachable and
 * Back/Home are swallowed by the kiosk. The Activity feeds it taps that land in a screen
 * corner; [TAPS] of them within [WINDOW_MS] reveal the same PIN prompt the remote gesture does.
 *
 * As with the remote gesture, secrecy is not the control — the pin on the screen behind this
 * is. A corner and a count only have to be something nobody produces by accident.
 */
class CornerTapCounter(private val windowMs: Long = WINDOW_MS) {
    private val taps = ArrayDeque<Long>()

    /** Returns true when this tap is the [TAPS]th to land within [windowMs]. */
    fun record(nowMs: Long): Boolean {
        taps.addLast(nowMs)
        while (taps.isNotEmpty() && nowMs - taps.first() > windowMs) {
            taps.removeFirst()
        }
        if (taps.size >= TAPS) {
            taps.clear()
            return true
        }
        return false
    }

    /** A tap outside the corner breaks the run. */
    fun reset() = taps.clear()

    companion object {
        const val WINDOW_MS = 3_000L
        const val TAPS = 7
    }
}
