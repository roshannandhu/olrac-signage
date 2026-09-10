package com.olrac.signage.network

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class ApiClientTest {
    @Test
    fun normalizesServerUrlForRetrofit() {
        assertEquals(
            "https://signage.example.com/api/",
            ApiClient.normalizeBaseUrl(" https://signage.example.com/api ")
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsNonHttpServerUrl() {
        ApiClient.normalizeBaseUrl("ftp://signage.example.com")
    }

    @Test
    fun rewritesBackendLoopbackMediaUrlToConfiguredServer() {
        assertEquals(
            "http://192.168.1.20:8000/uploads/ad.png",
            ApiClient.rewriteLoopbackMediaUrl(
                mediaUrl = "http://localhost:8000/uploads/ad.png",
                baseUrl = "http://192.168.1.20:8000/"
            )
        )
    }

    @Test
    fun leavesCloudMediaUrlUntouched() {
        val mediaUrl = "https://cdn.example.com/media/ad.mp4?signature=abc"
        assertEquals(
            mediaUrl,
            ApiClient.rewriteLoopbackMediaUrl(mediaUrl, "https://api.example.com/")
        )
    }

    @Test
    fun objectStorageKeyResolvesThroughTheApiNotAClientSideSignature() {
        // The app must never mint an R2 signature: no credentials ship in the APK, and the
        // API signs the real URL fresh when this link is followed.
        val resolved = ApiClient.rewriteLoopbackMediaUrl(
            mediaUrl = "s3://tenant/7f3a/ad.mp4",
            baseUrl = "https://api.example.com/"
        )
        assertEquals("https://api.example.com/api/media/tenant/7f3a/ad.mp4", resolved)
        assertFalse("must not carry an AWS signature", resolved.contains("X-Amz-Signature"))
    }

    @Test
    fun alreadyResolvedApiMediaUrlIsLeftAlone() {
        val mediaUrl = "https://api.example.com/api/media/tenant/7f3a/ad.mp4"
        assertEquals(
            mediaUrl,
            ApiClient.rewriteLoopbackMediaUrl(mediaUrl, "https://api.example.com/")
        )
    }

    @Test
    fun loopbackApiMediaUrlIsRepointedAtTheConfiguredServer() {
        assertEquals(
            "http://192.168.1.20:8000/api/media/tenant/ad.mp4",
            ApiClient.rewriteLoopbackMediaUrl(
                mediaUrl = "http://127.0.0.1:8000/api/media/tenant/ad.mp4",
                baseUrl = "http://192.168.1.20:8000/"
            )
        )
    }
}
