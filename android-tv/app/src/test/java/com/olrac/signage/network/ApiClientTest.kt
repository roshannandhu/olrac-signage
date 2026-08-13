package com.olrac.signage.network

import org.junit.Assert.assertEquals
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
}
