package com.olrac.signage.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "playlist_items")
data class PlaylistItemEntity(
    @PrimaryKey val id: Int,
    val contentId: Int = 0,
    // Which playlist this item came from. Proof-of-play events are attributed with it,
    // and without it every play log has playlist_id = null, so "plays by campaign" and
    // "plays by playlist" — the reports advertisers are actually shown — cannot be built.
    val playlistId: Int? = null,
    val type: String, // "video", "image", "website"
    val fileUrl: String,
    val localPath: String?, // Null if not downloaded yet
    val duration: Int,
    val orderIndex: Int,
    val startAt: String? = null,
    val endAt: String? = null,
    val daysOfWeek: String? = null,
    val windowStart: String? = null,
    val windowEnd: String? = null,
    val transition: String? = null,
    val transitionMs: Int? = null,
    val playlistDefaultTransition: String = "fade",
    val playlistDefaultTransitionMs: Int = 600,
    val sha256: String? = null,
    val fileSizeBytes: Long? = 0L,
    // Degrees to turn this item on this panel, already resolved by the server from the
    // per-item override and the screen's orientation. The player must not re-derive it.
    val rotation: Int = 0,
    // "contain" letterboxes the whole frame, "cover" fills the panel and crops.
    val fitMode: String = "contain"
) {
    val isVideo: Boolean get() = type.startsWith("video", ignoreCase = true)
    val isImage: Boolean get() = type.startsWith("image", ignoreCase = true)
}
