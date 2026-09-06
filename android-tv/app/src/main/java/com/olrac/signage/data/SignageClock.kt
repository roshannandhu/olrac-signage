package com.olrac.signage.data

import android.content.Context
import android.os.SystemClock
import android.util.Log
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/**
 * Robust wall-clock provider for digital signage displays.
 *
 * Hardware digital signage sticks and TVs often lack a real-time clock (RTC) battery.
 * When rebooted cold without an immediate internet connection, Android's system clock resets
 * to epoch (Jan 1, 1970 00:00:00 UTC) or kernel build time.
 *
 * SignageClock maintains a monotonic anchor:
 * [anchorServerTimeMs] + (SystemClock.elapsedRealtime() - [anchorElapsedRealtimeMs])
 *
 * This guarantees:
 * 1. Monotonically increasing time throughout a boot session even without NTP.
 * 2. Instant detection of unverified clock states so [ScheduleEvaluator] can fail-safe
 *    instead of shutting down screens.
 * 3. Exact retroactive calculation of true playback timestamps when internet reconnects.
 */
class SignageClock private constructor(context: Context) {
    private val appContext = context.applicationContext
    private val prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    @Volatile
    private var anchorServerTimeMs: Long = 0L

    @Volatile
    private var anchorElapsedRealtimeMs: Long = 0L

    init {
        val lastServerTime = prefs.getLong(KEY_LAST_SERVER_TIME_MS, 0L)
        val lastElapsed = prefs.getLong(KEY_LAST_ELAPSED_MS, 0L)
        val currentElapsed = SystemClock.elapsedRealtime()

        // If current elapsed is greater than last elapsed and within reasonable bounds,
        // it may be within the same boot.
        if (lastServerTime > 0L && currentElapsed >= lastElapsed && (currentElapsed - lastElapsed) < MAX_IN_BOOT_DRIFT_MS) {
            anchorServerTimeMs = lastServerTime
            anchorElapsedRealtimeMs = lastElapsed
        }
    }

    /**
     * Anchor the clock against a trusted server timestamp.
     */
    fun anchor(serverTimeUtcMillis: Long) {
        if (serverTimeUtcMillis < MIN_PLAUSIBLE_TIMESTAMP) return
        val currentElapsed = SystemClock.elapsedRealtime()
        anchorServerTimeMs = serverTimeUtcMillis
        anchorElapsedRealtimeMs = currentElapsed

        prefs.edit()
            .putLong(KEY_LAST_SERVER_TIME_MS, serverTimeUtcMillis)
            .putLong(KEY_LAST_ELAPSED_MS, currentElapsed)
            .apply()

        Log.i(TAG, "Signage clock anchored: serverTime=$serverTimeUtcMillis, elapsedRealtime=$currentElapsed")
    }

    /**
     * Updates anchor from an HTTP Date header (e.g. from OkHttp response).
     */
    fun updateFromHttpDate(dateHeader: String?) {
        if (dateHeader.isNullOrBlank()) return
        try {
            val zonedDateTime = ZonedDateTime.parse(dateHeader, DateTimeFormatter.RFC_1123_DATE_TIME)
            anchor(zonedDateTime.toInstant().toEpochMilli())
        } catch (e: Exception) {
            Log.w(TAG, "Failed to parse HTTP Date header '$dateHeader': ${e.message}")
        }
    }

    /**
     * Returns whether the clock has a trustworthy modern time reference (>= Jan 1, 2025).
     * If false, the system has booted offline with an RTC reset to 1970/2021 and no server anchor yet.
     */
    fun isClockVerified(): Boolean {
        if (anchorServerTimeMs > 0L) return true
        return System.currentTimeMillis() >= MIN_PLAUSIBLE_TIMESTAMP
    }

    /**
     * Returns best estimated current UTC epoch millis.
     * Uses monotonic elapsedRealtime delta if anchored, or System.currentTimeMillis() if valid,
     * or last saved server time floor.
     */
    fun currentEstimatedUtcMillis(): Long {
        if (anchorServerTimeMs > 0L) {
            val elapsedSinceAnchor = SystemClock.elapsedRealtime() - anchorElapsedRealtimeMs
            return anchorServerTimeMs + elapsedSinceAnchor
        }
        val systemTime = System.currentTimeMillis()
        if (systemTime >= MIN_PLAUSIBLE_TIMESTAMP) {
            return systemTime
        }
        val lastSaved = prefs.getLong(KEY_LAST_SERVER_TIME_MS, 0L)
        return if (lastSaved > 0L) lastSaved else systemTime
    }

    /**
     * Converts an elapsedRealtime timestamp from the current boot session into estimated UTC millis.
     */
    fun elapsedRealtimeToUtcMillis(elapsedMs: Long): Long {
        if (anchorServerTimeMs > 0L) {
            val delta = elapsedMs - anchorElapsedRealtimeMs
            return anchorServerTimeMs + delta
        }
        val currentEstimated = currentEstimatedUtcMillis()
        val currentElapsed = SystemClock.elapsedRealtime()
        return currentEstimated - (currentElapsed - elapsedMs)
    }

    /**
     * Returns current LocalDateTime in system default timezone.
     */
    fun nowLocal(): LocalDateTime {
        val millis = currentEstimatedUtcMillis()
        return LocalDateTime.ofInstant(Instant.ofEpochMilli(millis), ZoneId.systemDefault())
    }

    companion object {
        private const val TAG = "SignageClock"
        private const val PREFS_NAME = "olrac_signage_clock"
        private const val KEY_LAST_SERVER_TIME_MS = "last_server_time_ms"
        private const val KEY_LAST_ELAPSED_MS = "last_elapsed_ms"

        // Jan 1, 2025 00:00:00 UTC in millis
        const val MIN_PLAUSIBLE_TIMESTAMP = 1735689600000L
        private const val MAX_IN_BOOT_DRIFT_MS = 7 * 24 * 60 * 60 * 1000L // 7 days

        @Volatile
        private var instance: SignageClock? = null

        fun getInstance(context: Context): SignageClock =
            instance ?: synchronized(this) {
                instance ?: SignageClock(context).also { instance = it }
            }
    }
}
