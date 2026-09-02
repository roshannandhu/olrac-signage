package com.olrac.signage.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDateTime

/**
 * Screen opening hours decide whether a panel is lit at all, so both directions of a
 * mistake are expensive: too strict and a shop's screen is dark during trading, too loose
 * and it runs all night in a closed building. The backend already evaluates the same rules
 * for alert suppression (alerting.is_scheduled_off) and the two must agree, or a screen
 * goes dark while the fleet list reports it as faulty.
 *
 * Monday 2026-09-07 is the reference date; DayOfWeek.MONDAY.value is 1, which the
 * implementation maps to the "mon" key.
 */
class OperatingHoursTest {

    private fun monday(hour: Int, minute: Int = 0) = LocalDateTime.of(2026, 9, 7, hour, minute)
    private fun tuesday(hour: Int) = LocalDateTime.of(2026, 9, 8, hour, 0)

    @Test
    fun `always means never off`() {
        assertFalse(OperatingHours.isOff("always", null, monday(3)))
        assertFalse(OperatingHours.isOff(null, null, monday(3)))
    }

    @Test
    fun `never means always off`() {
        assertTrue(OperatingHours.isOff("never", null, monday(12)))
    }

    @Test
    fun `inside the window it plays, outside it does not`() {
        val hours = mapOf("mon" to listOf("09:00", "21:00"))
        assertFalse(OperatingHours.isOff("hours", hours, monday(9)))
        assertFalse(OperatingHours.isOff("hours", hours, monday(14)))
        assertFalse(OperatingHours.isOff("hours", hours, monday(21)))
        assertTrue(OperatingHours.isOff("hours", hours, monday(8, 59)))
        assertTrue(OperatingHours.isOff("hours", hours, monday(21, 1)))
        assertTrue(OperatingHours.isOff("hours", hours, monday(3)))
    }

    @Test
    fun `an overnight window wraps past midnight`() {
        // 22:00-02:00 is a bar or a hotel lobby, not a typo. Read as start greater than
        // end it would otherwise be "off" for the whole day.
        val hours = mapOf("mon" to listOf("22:00", "02:00"))
        assertFalse(OperatingHours.isOff("hours", hours, monday(23)))
        assertFalse(OperatingHours.isOff("hours", hours, monday(1)))
        assertTrue(OperatingHours.isOff("hours", hours, monday(12)))
    }

    @Test
    fun `a day with no window configured is a closed day`() {
        val hours = mapOf("mon" to listOf("09:00", "17:00"))
        assertTrue(OperatingHours.isOff("hours", hours, tuesday(12)))
    }

    @Test
    fun `hours mode with nothing configured is not a licence to go dark forever`() {
        // Matches the server. Read the other way, an operator who selects "hours" and has
        // not yet typed a window would black out the whole estate.
        assertFalse(OperatingHours.isOff("hours", null, monday(12)))
        assertFalse(OperatingHours.isOff("hours", emptyMap(), monday(12)))
    }

    @Test
    fun `a malformed window keeps the screen playing`() {
        // Fail open: a bad string must not silence a live screen, and the server takes the
        // same view for an unparseable window.
        assertFalse(OperatingHours.isOff("hours", mapOf("mon" to listOf("oops", "17:00")), monday(12)))
        assertFalse(OperatingHours.isOff("hours", mapOf("mon" to listOf("25:00", "17:00")), monday(12)))
    }

    @Test
    fun `a day with the wrong number of entries is closed, not crashing`() {
        assertTrue(OperatingHours.isOff("hours", mapOf("mon" to listOf("09:00")), monday(12)))
    }
}
