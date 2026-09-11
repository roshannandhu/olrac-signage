package com.olrac.signage.sync

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MediaCacheFreshnessTest {

    @Test
    fun reusesTheCachedFileWhenTheDigestIsUnchanged() {
        assertTrue(MediaCacheFreshness.canReuseCachedFile("abc123", "abc123"))
        assertTrue("digest case must not force a re-download",
            MediaCacheFreshness.canReuseCachedFile("ABC123", "abc123"))
    }

    @Test
    fun refetchesWhenTheServerAdvertisesDifferentBytes() {
        // The transcode worker replacing a master, or a different rendition being selected:
        // same content id, new bytes. Reusing here is what left screens on a stale advert.
        assertFalse(MediaCacheFreshness.canReuseCachedFile("oldhash", "newhash"))
    }

    @Test
    fun refetchesOnceWhenNothingWasEverRecorded() {
        assertFalse(MediaCacheFreshness.canReuseCachedFile(null, "newhash"))
        assertFalse(MediaCacheFreshness.canReuseCachedFile("", "newhash"))
    }

    @Test
    fun trustsTheCacheWhenTheServerOffersNoDigest() {
        // Nothing to compare against; refusing here would re-download every sync forever.
        assertTrue(MediaCacheFreshness.canReuseCachedFile("oldhash", null))
        assertTrue(MediaCacheFreshness.canReuseCachedFile(null, null))
        assertTrue(MediaCacheFreshness.canReuseCachedFile("oldhash", ""))
    }
}
