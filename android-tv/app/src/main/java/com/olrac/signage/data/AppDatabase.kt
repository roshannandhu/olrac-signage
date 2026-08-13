package com.olrac.signage.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(entities = [PlaylistItemEntity::class, PlayEventEntity::class], version = 6, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun playlistDao(): PlaylistDao
    abstract fun playEventDao(): PlayEventDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "signage_database"
                ).addMigrations(
                    MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4, MIGRATION_4_5, MIGRATION_5_6
                ).build()
                INSTANCE = instance
                instance
            }
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN contentId INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN startAt TEXT")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN endAt TEXT")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN daysOfWeek TEXT")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN windowStart TEXT")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN windowEnd TEXT")
            }
        }

        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN transition TEXT")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN transitionMs INTEGER")
                db.execSQL(
                    "ALTER TABLE playlist_items ADD COLUMN playlistDefaultTransition TEXT NOT NULL DEFAULT 'fade'"
                )
                db.execSQL(
                    "ALTER TABLE playlist_items ADD COLUMN playlistDefaultTransitionMs INTEGER NOT NULL DEFAULT 600"
                )
            }
        }

        private val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN sha256 TEXT")
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN fileSizeBytes INTEGER")
            }
        }
        
        // Nullable so existing rows survive; the next sync repopulates every item with
        // its real playlist id.
        private val MIGRATION_5_6 = object : Migration(5, 6) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE playlist_items ADD COLUMN playlistId INTEGER")
            }
        }

        private val MIGRATION_4_5 = object : Migration(4, 5) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `play_events` (
                        `eventId` TEXT NOT NULL, 
                        `mediaId` INTEGER, 
                        `playlistId` INTEGER, 
                        `campaignId` INTEGER, 
                        `deviceStartedAt` TEXT NOT NULL, 
                        `deviceFinishedAt` TEXT NOT NULL, 
                        `correctedStartedAt` TEXT NOT NULL, 
                        `correctedFinishedAt` TEXT NOT NULL, 
                        `durationMs` INTEGER NOT NULL, 
                        `status` TEXT NOT NULL, 
                        `errorMessage` TEXT, 
                        PRIMARY KEY(`eventId`)
                    )
                    """.trimIndent()
                )
            }
        }
    }
}
