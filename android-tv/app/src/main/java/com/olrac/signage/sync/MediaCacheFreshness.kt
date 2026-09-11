package com.olrac.signage.sync

/**
 * Whether a media file already on disk can be trusted for the bytes the server is now
 * advertising for that content id.
 *
 * The cache is keyed on content id alone (`content-<id>.<ext>`), and a content id's bytes
 * DO change underneath it: the sync payload ships items while they are still `processing`
 * and the transcode worker then replaces the master, and `select_rendition` can hand the
 * same id a different per-screen encode. Reusing a cached file on existence alone -- which
 * is what this replaces -- left a screen playing the superseded advert indefinitely, and
 * reported proof-of-play against a creative that never appeared.
 */
object MediaCacheFreshness {
    fun canReuseCachedFile(recordedSha256: String?, advertisedSha256: String?): Boolean = when {
        // The server offers no digest for this item, so there is nothing to check against.
        // Trusting the file is the old behaviour and the only option.
        advertisedSha256.isNullOrBlank() -> true
        // Cached before a digest was ever recorded: we cannot prove what is on disk, so
        // fetch once and the recorded digest makes every later sync decidable.
        recordedSha256.isNullOrBlank() -> false
        else -> recordedSha256.equals(advertisedSha256, ignoreCase = true)
    }
}
