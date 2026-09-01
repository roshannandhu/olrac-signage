package com.olrac.signage.network

import java.net.URI
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object R2Presigner {
    private const val ENDPOINT = "https://3fe4487a2b8fd1e2e541bf0e0f4c7c42.r2.cloudflarestorage.com"
    private const val BUCKET = "olrac"
    private const val ACCESS_KEY_ID = "734d432aeb20a3f4bbd484ca83a8a82b"
    private const val SECRET_ACCESS_KEY = "ef6c0c74667843ec08f396b12ab0e8929d409c8c8062713da09cd17c6c628acf"
    private const val REGION = "auto"
    private const val SERVICE = "s3"

    private val DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC)
    private val DATE_ONLY_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd").withZone(ZoneOffset.UTC)

    fun presign(s3OrR2Url: String, expiresInSeconds: Long = 7 * 24 * 3600L): String {
        return try {
            val key = s3OrR2Url
                .removePrefix("s3://")
                .removePrefix("r2://")
                .removePrefix("$BUCKET/")
                .trimStart('/')

            val now = Instant.now()
            val amzDate = DATE_FORMATTER.format(now)
            val dateStamp = DATE_ONLY_FORMATTER.format(now)

            val endpointUri = URI(ENDPOINT)
            val host = endpointUri.host
            val canonicalUri = "/$BUCKET/$key"

            val credentialScope = "$dateStamp/$REGION/$SERVICE/aws4_request"
            val queryParams = sortedMapOf(
                "X-Amz-Algorithm" to "AWS4-HMAC-SHA256",
                "X-Amz-Credential" to "$ACCESS_KEY_ID/$credentialScope",
                "X-Amz-Date" to amzDate,
                "X-Amz-Expires" to expiresInSeconds.toString(),
                "X-Amz-SignedHeaders" to "host"
            )

            val canonicalQueryString = queryParams.entries.joinToString("&") { (k, v) ->
                "${urlEncode(k)}=${urlEncode(v)}"
            }

            val canonicalHeaders = "host:$host\n"
            val signedHeaders = "host"
            val payloadHash = "UNSIGNED-PAYLOAD"

            val canonicalRequest = listOf(
                "GET",
                canonicalUri,
                canonicalQueryString,
                canonicalHeaders,
                signedHeaders,
                payloadHash
            ).joinToString("\n")

            val stringToSign = listOf(
                "AWS4-HMAC-SHA256",
                amzDate,
                credentialScope,
                sha256Hex(canonicalRequest)
            ).joinToString("\n")

            val signingKey = getSignatureKey(SECRET_ACCESS_KEY, dateStamp, REGION, SERVICE)
            val signature = hmacHex(signingKey, stringToSign)

            "$ENDPOINT$canonicalUri?$canonicalQueryString&X-Amz-Signature=$signature"
        } catch (e: Exception) {
            val cleanKey = s3OrR2Url.removePrefix("s3://").removePrefix("r2://").removePrefix("$BUCKET/").trimStart('/')
            "$ENDPOINT/$BUCKET/$cleanKey"
        }
    }

    private fun urlEncode(value: String): String =
        URLEncoder.encode(value, StandardCharsets.UTF_8.name())
            .replace("+", "%20")
            .replace("*", "%2A")
            .replace("%7E", "~")

    private fun sha256Hex(data: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(data.toByteArray(StandardCharsets.UTF_8))
        return hash.joinToString("") { "%02x".format(it) }
    }

    private fun hmacSha256(key: ByteArray, data: String): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        return mac.doFinal(data.toByteArray(StandardCharsets.UTF_8))
    }

    private fun hmacHex(key: ByteArray, data: String): String {
        val hash = hmacSha256(key, data)
        return hash.joinToString("") { "%02x".format(it) }
    }

    private fun getSignatureKey(key: String, dateStamp: String, regionName: String, serviceName: String): ByteArray {
        val kSecret = ("AWS4$key").toByteArray(StandardCharsets.UTF_8)
        val kDate = hmacSha256(kSecret, dateStamp)
        val kRegion = hmacSha256(kDate, regionName)
        val kService = hmacSha256(kRegion, serviceName)
        return hmacSha256(kService, "aws4_request")
    }
}
