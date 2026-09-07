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

    @Test
    fun unverifiedClockFailsSafeToActive() {
        val clock = io.mockk.mockk<SignageClock>()
        io.mockk.every { clock.isClockVerified() } returns false

        val scheduledFuture = item(startAt = "2026-10-01T09:00:00", endAt = "2026-10-30T17:00:00")
        assertTrue(ScheduleEvaluator.isActive(scheduledFuture, clock))
    }

    @Test
    fun verifiedClockAppliesScheduleWindows() {
        val clock = io.mockk.mockk<SignageClock>()
        io.mockk.every { clock.isClockVerified() } returns true
        io.mockk.every { clock.nowLocal() } returns LocalDateTime.parse("2026-08-06T10:00:00")

        val scheduled = item(startAt = "2026-08-01T09:00:00", endAt = "2026-08-10T17:00:00")
        assertTrue(ScheduleEvaluator.isActive(scheduled, clock))

        io.mockk.every { clock.nowLocal() } returns LocalDateTime.parse("2026-08-15T10:00:00")
        assertFalse(ScheduleEvaluator.isActive(scheduled, clock))
    }

    @Test
    fun diffTvForDiffTimePeriodWorksAsAssigned() {
        val clock = io.mockk.mockk<SignageClock>()
        io.mockk.every { clock.isClockVerified() } returns true

        // TV 1: Mall TV assigned for 30 days
        val mallTvItem = item(startAt = "2026-10-01T00:00:00", endAt = "2026-10-31T00:00:00")
        // TV 2: Shop TV assigned for 10 days
        val shopTvItem = item(startAt = "2026-10-01T00:00:00", endAt = "2026-10-11T00:00:00")

        // Day 5: Both TVs are within their assigned time period -> Both ACTIVE
        io.mockk.every { clock.nowLocal() } returns LocalDateTime.parse("2026-10-06T12:00:00")
        assertTrue("Mall TV must be active on day 5", ScheduleEvaluator.isActive(mallTvItem, clock))
        assertTrue("Shop TV must be active on day 5", ScheduleEvaluator.isActive(shopTvItem, clock))

        // Day 15: Shop TV (10 days) has expired, Mall TV (30 days) is still active
        io.mockk.every { clock.nowLocal() } returns LocalDateTime.parse("2026-10-16T12:00:00")
        assertTrue("Mall TV must still be active on day 15", ScheduleEvaluator.isActive(mallTvItem, clock))
        assertFalse("Shop TV must be INACTIVE on day 15 (its 10-day run finished)", ScheduleEvaluator.isActive(shopTvItem, clock))

        // Day 35: Both TVs have concluded their campaign
        io.mockk.every { clock.nowLocal() } returns LocalDateTime.parse("2026-11-05T12:00:00")
        assertFalse("Mall TV must be inactive after day 30", ScheduleEvaluator.isActive(mallTvItem, clock))
        assertFalse("Shop TV must be inactive after day 10", ScheduleEvaluator.isActive(shopTvItem, clock))
    }
}
