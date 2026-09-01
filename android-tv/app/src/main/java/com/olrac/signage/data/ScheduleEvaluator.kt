package com.olrac.signage.data

import java.time.LocalDateTime
import java.time.LocalTime
import java.time.OffsetDateTime

object ScheduleEvaluator {
    fun isActive(item: PlaylistItemEntity, now: LocalDateTime = LocalDateTime.now()): Boolean {
        val absoluteStart = parseDateTime(item.startAt)
        val absoluteEnd = parseDateTime(item.endAt)
        if (absoluteStart != null && now.isBefore(absoluteStart)) return false
        if (absoluteEnd != null && !now.isBefore(absoluteEnd)) return false

        val selectedDays = item.daysOfWeek
            ?.split(",")
            ?.mapNotNull(String::toIntOrNull)
            ?.toSet()
            .orEmpty()
        val start = parseTime(item.windowStart)
        val end = parseTime(item.windowEnd)
        val today = now.dayOfWeek.value - 1

        if (start != null && end != null && start > end) {
            val scheduleDay = if (now.toLocalTime() < end) (today + 6) % 7 else today
            if (selectedDays.isNotEmpty() && scheduleDay !in selectedDays) return false
            return now.toLocalTime() >= start || now.toLocalTime() < end
        }

        if (selectedDays.isNotEmpty() && today !in selectedDays) return false
        if (start != null && now.toLocalTime() < start) return false
        if (end != null && !now.toLocalTime().isBefore(end)) return false
        return true
    }

    private fun parseDateTime(value: String?): LocalDateTime? {
        if (value.isNullOrBlank()) return null
        return runCatching {
            OffsetDateTime.parse(value).atZoneSameInstant(java.time.ZoneId.systemDefault()).toLocalDateTime()
        }.getOrElse {
            runCatching { LocalDateTime.parse(value) }.getOrNull()
        }
    }

    private fun parseTime(value: String?): LocalTime? =
        value?.takeIf { it.isNotBlank() }?.let { runCatching { LocalTime.parse(it) }.getOrNull() }
}
