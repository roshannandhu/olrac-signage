package com.olrac.signage.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PlayEventDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(event: PlayEventEntity)

    @Query("SELECT * FROM play_events ORDER BY deviceStartedAt ASC LIMIT :limit")
    suspend fun getPendingEvents(limit: Int): List<PlayEventEntity>

    @Query("DELETE FROM play_events WHERE eventId IN (:eventIds)")
    suspend fun deleteEvents(eventIds: List<String>)
}
