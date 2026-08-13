package com.olrac.signage.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface PlaylistDao {
    @Query("SELECT * FROM playlist_items ORDER BY orderIndex ASC")
    suspend fun getAllItems(): List<PlaylistItemEntity>

    @Query("SELECT * FROM playlist_items ORDER BY orderIndex ASC")
    fun observeAllItems(): Flow<List<PlaylistItemEntity>>

    @Query("SELECT EXISTS(SELECT 1 FROM playlist_items LIMIT 1)")
    suspend fun hasItems(): Boolean

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertItems(items: List<PlaylistItemEntity>)

    @Query("DELETE FROM playlist_items")
    suspend fun deleteAll()

    @Query("UPDATE playlist_items SET localPath = :path WHERE id = :id")
    suspend fun updateLocalPath(id: Int, path: String)

    @Transaction
    suspend fun replaceAll(items: List<PlaylistItemEntity>) {
        deleteAll()
        insertItems(items)
    }
}
