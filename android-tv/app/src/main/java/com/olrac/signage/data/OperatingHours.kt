package com.olrac.signage.data

import java.time.LocalDateTime

/**
 * Whether this screen is meant to be dark right now.
 *
 * Screen-level hours, distinct from the per-item window [ScheduleEvaluator] applies: this
 * answers "should this panel be lit at all" (a property of the venue), not "may this
 * advert play" (a property of the booking). A shop on 09:00-21:00 goes black at closing
 * regardless of what is in the loop.
 *
 * A deliberate port of `backend/alerting.py::is_scheduled_off`, which already decides the
 * same question server-side for alert suppression. Kept behaviourally identical on purpose
 * -- if the two disagreed, a screen would go dark while the fleet list called it a fault,
 * or raise a nightly CRITICAL for a shop that is simply closed.
 *
 * Evaluated on the device rather than filtered by the server because the player must keep
 * observing its hours through an outage, which is the whole point of the offline cache.
 */
object OperatingHours {

    private val WEEKDAYS = listOf("mon", "tue", "wed", "thu", "fri", "sat", "sun")

    /**
     * @param mode "always" (default), "hours", or "never"
     * @param windows day -> ["HH:MM", "HH:MM"]
     * @param now device-local time; the panel is physically at the venue, so its own clock
     *        is the venue's clock.
     */
    fun isOff(
        mode: String?,
        windows: Map<String, List<String>>?,
        now: LocalDateTime = LocalDateTime.now(),
    ): Boolean {
        when (mode ?: "always") {
            "always" -> return false
            "never" -> return true
        }

        // "hours" with nothing configured is not a licence to silence the screen forever.
        if (windows.isNullOrEmpty()) return false

        // DayOfWeek.getValue() is 1=Monday, and WEEKDAYS starts at "mon".
        val window = windows[WEEKDAYS[now.dayOfWeek.value - 1]]
        // A day with no window configured is a closed day. Matches the server, which
        // returns true here.
        if (window == null || window.size != 2) return true

        val start = minutesOf(window[0]) ?: return false
        val end = minutesOf(window[1]) ?: return false
        val minute = now.hour * 60 + now.minute

        // An end before the start is an overnight window (22:00-02:00), the normal shape
        // for a bar or a hotel lobby, not a typo.
        return if (start <= end) {
            !(minute in start..end)
        } else {
            !(minute >= start || minute <= end)
        }
    }

    /** "HH:MM" to minutes past midnight, or null when it is not that. */
    private fun minutesOf(stamp: String?): Int? {
        val parts = stamp?.split(":") ?: return null
        if (parts.size != 2) return null
        val hours = parts[0].toIntOrNull() ?: return null
        val minutes = parts[1].toIntOrNull() ?: return null
        if (hours !in 0..23 || minutes !in 0..59) return null
        return hours * 60 + minutes
    }
}
