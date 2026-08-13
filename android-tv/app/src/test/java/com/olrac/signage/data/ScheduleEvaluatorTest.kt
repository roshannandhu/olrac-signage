package com.olrac.signage.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDateTime

class ScheduleEvaluatorTest {
    private fun item(
        startAt: String? = null,
        endAt: String? = null,
        days: String? = null,
        windowStart: String? = null,
        windowEnd: String? = null
    ) = PlaylistItemEntity(
        id = 1,
        type = "image",
        fileUrl = "https://example.com/image.png",
        localPath = "/cache/image.png",
        duration = 10,
        orderIndex = 0,
        startAt = startAt,
        endAt = endAt,
        daysOfWeek = days,
        windowStart = windowStart,
        windowEnd = windowEnd
    )

    @Test
    fun weekdayWindowOnlyRunsInsideWindow() {
        val scheduled = item(days = "0,1,2,3,4", windowStart = "09:00:00", windowEnd = "17:00:00")
        assertTrue(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-06T10:00:00")))
        assertFalse(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-06T18:00:00")))
        assertFalse(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-08T10:00:00")))
    }

    @Test
    fun overnightWindowCarriesIntoFollowingDay() {
        val scheduled = item(days = "0", windowStart = "22:00:00", windowEnd = "02:00:00")
        assertTrue(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-03T23:00:00")))
        assertTrue(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-04T01:00:00")))
        assertFalse(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-04T03:00:00")))
    }

    @Test
    fun absoluteBoundsAreStartInclusiveAndEndExclusive() {
        val scheduled = item(startAt = "2026-08-06T09:00:00", endAt = "2026-08-06T17:00:00")
        assertFalse(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-06T08:59:59")))
        assertTrue(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-06T09:00:00")))
        assertFalse(ScheduleEvaluator.isActive(scheduled, LocalDateTime.parse("2026-08-06T17:00:00")))
    }
}
