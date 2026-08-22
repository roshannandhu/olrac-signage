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

    @Query("SELECT COUNT(*) FROM play_events")
    suspend fun countEvents(): Int

    /**
     * Drop the oldest events, keeping the newest [keep].
     *
     * Nothing bounded this table. A screen that cannot reach the server keeps recording --
     * correctly, that is the point -- but the queue grew without limit in the same
     * `filesDir` the media cache lives in, so a long outage could starve the cache that
     * keeps playback running. Losing the oldest proof of play is bad; losing playback
     * because the disk filled is worse, and it takes the newer evidence with it.
     *
     * Oldest-first because a report that is missing its far tail is still usable, whereas
     * one missing the last few days is the one nobody can explain.
     */
    @Query(
        """
        DELETE FROM play_events WHERE eventId IN (
            SELECT eventId FROM play_events ORDER BY deviceStartedAt DESC LIMIT -1 OFFSET :keep
        )
        """
    )
    suspend fun trimOldest(keep: Int): Int
}
