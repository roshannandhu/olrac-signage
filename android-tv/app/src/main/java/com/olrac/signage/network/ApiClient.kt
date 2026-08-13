package com.olrac.signage.network

import android.content.Context
import com.olrac.signage.BuildConfig
import com.olrac.signage.data.DeviceState
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.net.URI

object ApiClient {
    @Volatile
    private var cachedBaseUrl: String? = null

    @Volatile
    private var cachedService: ApiService? = null

    fun effectiveBaseUrl(context: Context): String {
        val stored = DeviceState(context).apiBaseUrlOverride
        return try {
            normalizeBaseUrl(stored ?: BuildConfig.API_BASE_URL)
        } catch (_: IllegalArgumentException) {
            normalizeBaseUrl(BuildConfig.API_BASE_URL)
        }
    }

    fun service(context: Context): ApiService {
        val baseUrl = effectiveBaseUrl(context)
        cachedService?.takeIf { cachedBaseUrl == baseUrl }?.let { return it }

        return synchronized(this) {
            cachedService?.takeIf { cachedBaseUrl == baseUrl } ?: Retrofit.Builder()
                .baseUrl(baseUrl)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(ApiService::class.java)
                .also {
                    cachedBaseUrl = baseUrl
                    cachedService = it
                }
        }
    }

    fun normalizeBaseUrl(value: String): String {
        val candidate = value.trim()
        require(candidate.isNotEmpty()) { "Server URL is required" }

        val parsed = try {
            URI(candidate)
        } catch (_: Exception) {
            throw IllegalArgumentException("Enter a valid http:// or https:// URL")
        }
        require(parsed.scheme == "http" || parsed.scheme == "https") {
            "Server URL must start with http:// or https://"
        }
        require(!parsed.host.isNullOrBlank()) { "Server URL must include a host" }
        require(parsed.query == null && parsed.fragment == null) {
            "Server URL cannot include a query or fragment"
        }

        val path = when {
            parsed.path.isNullOrBlank() -> "/"
            parsed.path.endsWith('/') -> parsed.path
            else -> "${parsed.path}/"
        }
        return URI(parsed.scheme, parsed.userInfo, parsed.host, parsed.port, path, null, null)
            .toASCIIString()
    }

    fun resolveMediaUrl(context: Context, value: String): String =
        rewriteLoopbackMediaUrl(value, effectiveBaseUrl(context))

    fun rewriteLoopbackMediaUrl(mediaUrl: String, baseUrl: String): String {
        val media = try {
            URI(mediaUrl)
        } catch (_: Exception) {
            return mediaUrl
        }
        if (media.host !in setOf("localhost", "127.0.0.1")) return mediaUrl

        val base = URI(normalizeBaseUrl(baseUrl))
        return URI(
            base.scheme,
            null,
            base.host,
            base.port,
            media.path,
            media.query,
            media.fragment
        ).toASCIIString()
    }
}
