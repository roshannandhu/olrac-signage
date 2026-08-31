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

    /**
     * Bearer token for this screen, exchanged from its stored device secret.
     *
     * Cached in memory with a conservative expiry: the server issues these for an hour, and
     * re-exchanging on every heartbeat would triple the request count for no benefit.
     */
    @Volatile
    private var cachedToken: String? = null

    @Volatile
    private var tokenExpiresAt: Long = 0L

    private const val TOKEN_LIFETIME_MS = 45 * 60 * 1000L

    fun clearToken() {
        cachedToken = null
        tokenExpiresAt = 0L
    }

    fun service(context: Context): ApiService {
        val baseUrl = effectiveBaseUrl(context)
        cachedService?.takeIf { cachedBaseUrl == baseUrl }?.let { return it }

        return synchronized(this) {
            cachedService?.takeIf { cachedBaseUrl == baseUrl } ?: Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(buildClient(context.applicationContext))
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(ApiService::class.java)
                .also {
                    cachedBaseUrl = baseUrl
                    cachedService = it
                }
        }
    }

    /**
     * Attaches this screen's credential to every request that has one.
     *
     * Without this the secret issued at pairing would be stored and never used, and the
     * server could never stop accepting unauthenticated device calls -- which is the whole
     * point of issuing it. Screens paired by an older build simply have no secret, send no
     * header, and keep working on the server's legacy path until they are re-paired.
     */
    fun buildClient(appContext: Context): okhttp3.OkHttpClient =
        okhttp3.OkHttpClient.Builder()
            .addInterceptor { chain ->
                val request = chain.request()
                // The token is obtained THROUGH this client, so signing that one call would
                // recurse forever.
                if (request.url.encodedPath.endsWith("/api/screens/auth")) {
                    return@addInterceptor chain.proceed(request)
                }

                val baseUri = try { URI(effectiveBaseUrl(appContext)) } catch (_: Exception) { null }
                val isApiHost = baseUri != null && request.url.host.equals(baseUri.host, ignoreCase = true)

                // Only attach the Bearer token to requests destined for our own API server.
                // Sending Bearer tokens to external object storage (Cloudflare R2 / AWS S3 presigned URLs)
                // causes AWS Signature v4 errors (HTTP 400).
                val token = if (isApiHost) deviceToken(appContext) else null
                val signed = if (token != null) {
                    request.newBuilder().header("Authorization", "Bearer $token").build()
                } else {
                    request
                }
                val response = chain.proceed(signed)
                // A rejected token is almost always an expired one; drop it so the next
                // call re-exchanges rather than repeating the failure until restart.
                if (response.code == 401 && token != null && isApiHost) clearToken()
                response
            }
            .build()

    private fun deviceToken(appContext: Context): String? {
        val secret = DeviceState(appContext).deviceSecret ?: return null
        cachedToken?.takeIf { System.currentTimeMillis() < tokenExpiresAt }?.let { return it }

        return synchronized(this) {
            cachedToken?.takeIf { System.currentTimeMillis() < tokenExpiresAt } ?: runCatching {
                val deviceId = DeviceState(appContext).deviceId
                // Deliberately a bare Retrofit instance with no interceptor: see above.
                val plain = Retrofit.Builder()
                    .baseUrl(effectiveBaseUrl(appContext))
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(ApiService::class.java)
                val response = kotlinx.coroutines.runBlocking {
                    plain.authDevice(DeviceAuthRequest(device_id = deviceId, device_secret = secret))
                }
                response.body()?.access_token?.also {
                    cachedToken = it
                    tokenExpiresAt = System.currentTimeMillis() + TOKEN_LIFETIME_MS
                }
            }.getOrNull()
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
        val base = try {
            URI(normalizeBaseUrl(baseUrl))
        } catch (_: Exception) {
            return mediaUrl
        }
        if (media.host == null || media.host in setOf("localhost", "127.0.0.1") || media.path?.startsWith("/uploads/") == true) {
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

        return mediaUrl
    }
}
