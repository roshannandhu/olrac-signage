package com.olrac.signage.telemetry

import android.content.Context

data class PlaybackSnapshot(
    val state: String,
    val currentItemId: Int?,
    val lastError: String?
)

class PlaybackTelemetry(context: Context) {
    private val appContext = context.applicationContext
    private val preferences = appContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    fun reportIdle() = update(state = "idle", currentItemId = null)

    fun reportPlaying(itemId: Int) = update(state = "playing", currentItemId = itemId)

    fun reportError(itemId: Int?, message: String) {
        val cleaned = message.trim().ifBlank { "Unknown playback error" }.take(1000)
        update(state = "error", currentItemId = itemId, lastError = cleaned)
        TelemetryHeartbeatWorker.enqueue(appContext, snapshot())
    }

    fun snapshot(): PlaybackSnapshot = PlaybackSnapshot(
        state = preferences.getString(KEY_PLAYBACK_STATE, "idle") ?: "idle",
        currentItemId = preferences.getInt(KEY_CURRENT_ITEM_ID, NO_ITEM).takeUnless { it == NO_ITEM },
        lastError = preferences.getString(KEY_LAST_ERROR, null)
    )

    private fun update(state: String, currentItemId: Int?, lastError: String? = null) {
        preferences.edit()
            .putString(KEY_PLAYBACK_STATE, state)
            .putInt(KEY_CURRENT_ITEM_ID, currentItemId ?: NO_ITEM)
            .apply {
                if (lastError != null) putString(KEY_LAST_ERROR, lastError)
            }
            .commit()
    }

    companion object {
        private const val PREFERENCES_NAME = "signage_prefs"
        private const val KEY_PLAYBACK_STATE = "playback_state"
        private const val KEY_CURRENT_ITEM_ID = "current_item_id"
        private const val KEY_LAST_ERROR = "last_playback_error"
        private const val NO_ITEM = -1
    }
}
