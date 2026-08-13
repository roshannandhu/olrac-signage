package com.olrac.signage.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "play_events")
data class PlayEventEntity(
    @PrimaryKey
    val eventId: String,
    val mediaId: Int?,
    val playlistId: Int?,
    val campaignId: Int?,
    val deviceStartedAt: String,
    val deviceFinishedAt: String,
    val correctedStartedAt: String,
    val correctedFinishedAt: String,
    val durationMs: Int,
    val status: String,
    val errorMessage: String? = null
)
