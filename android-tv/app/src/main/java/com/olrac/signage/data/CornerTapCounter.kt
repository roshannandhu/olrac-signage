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
        /** How far in from each edge, as a fraction of the screen, still counts as a corner. */
        const val CORNER_FRACTION = 0.12f

        /**
         * Whether a touch at (x, y) lands in ANY of the four corners of a w x h screen.
         *
         * Only the top-left used to count, while the dashboard told operators to "tap any corner
         * 7 times". Tapping any other corner reset the run on every tap, so on a kiosked tablet
         * -- where Back and Home are swallowed -- there was, as far as the operator could tell,
         * no way out at all. Every corner counts now, and taps may move between corners.
         */
        fun isCorner(x: Float, y: Float, w: Int, h: Int): Boolean {
            if (w <= 0 || h <= 0) return false
            val nearLeftOrRight = x < w * CORNER_FRACTION || x > w * (1 - CORNER_FRACTION)
            val nearTopOrBottom = y < h * CORNER_FRACTION || y > h * (1 - CORNER_FRACTION)
            return nearLeftOrRight && nearTopOrBottom
        }
    }
}
