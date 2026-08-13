package com.olrac.signage.sync

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.UUID

class StorageManager(private val context: Context) {

    suspend fun downloadWithIntegrityCheck(
        client: OkHttpClient,
        url: String,
        finalFile: File,
        expectedSha256: String?,
        expectedSizeBytes: Long?,
        protectedNames: Set<String> = emptySet()
    ): File? = withContext(Dispatchers.IO) {
        // Enforce quota before downloading
        val requiredSpace = expectedSizeBytes ?: DEFAULT_ASSUMED_SIZE_BYTES
        ensureQuota(requiredSpace, protectedNames + finalFile.name)

        val temporaryFile = File(
            context.filesDir,
            ".olrac-download-${UUID.randomUUID()}-${finalFile.name}"
        )
        try {
            val request = Request.Builder().url(url).build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    temporaryFile.delete()
                    return@withContext null
                }
                val body = response.body ?: run {
                    temporaryFile.delete()
                    return@withContext null
                }
                
                val md = MessageDigest.getInstance("SHA-256")
                var downloadedBytes = 0L
                
                FileOutputStream(temporaryFile).use { output ->
                    body.byteStream().use { input -> 
                        val buffer = ByteArray(8192)
                        var bytesRead: Int
                        while (input.read(buffer).also { bytesRead = it } != -1) {
                            output.write(buffer, 0, bytesRead)
                            md.update(buffer, 0, bytesRead)
                            downloadedBytes += bytesRead
                        }
                    }
                    output.fd.sync()
                }
                
                if (expectedSizeBytes != null && expectedSizeBytes > 0 && downloadedBytes != expectedSizeBytes) {
                    Log.e(TAG, "Size mismatch for ${finalFile.name}: expected $expectedSizeBytes, got $downloadedBytes")
                    temporaryFile.delete()
                    return@withContext null
                }
                
                val actualSha256 = md.digest().joinToString("") { "%02x".format(it) }
                if (!expectedSha256.isNullOrEmpty() && !actualSha256.equals(expectedSha256, ignoreCase = true)) {
                    Log.e(TAG, "SHA256 mismatch for ${finalFile.name}: expected $expectedSha256, got $actualSha256")
                    temporaryFile.delete()
                    return@withContext null
                }
            }
            if (temporaryFile.length() == 0L) {
                temporaryFile.delete()
                null
            } else {
                temporaryFile
            }
        } catch (e: Exception) {
            Log.e(TAG, "Download failed for ${finalFile.name}", e)
            temporaryFile.delete()
            null
        }
    }

    /**
     * Frees room for an incoming download.
     *
     * [protectedNames] must contain every file the player may currently be reading —
     * the active playlist plus the incoming target set. Without it this evicts by age,
     * and during a playlist switch the currently playing files *are* the oldest, so the
     * ad on screen gets deleted mid-frame. Spec: never delete the working offline playlist.
     *
     * Two ceilings apply: a cache budget, and real free space on the device. A fixed
     * budget alone is useless on a budget TV whose whole partition is smaller than it.
     */
    private fun ensureQuota(requiredSpace: Long, protectedNames: Set<String>) {
        val filesDir = context.filesDir
        val cacheFiles = filesDir.listFiles()
            ?.filter { it.isFile && it.name.startsWith(CACHE_PREFIX) }
            ?: emptyList()
        var totalUsed = cacheFiles.sumOf { it.length() }

        fun stillNeedsSpace(): Boolean {
            val overCacheBudget = totalUsed + requiredSpace > QUOTA_BYTES
            val deviceTooFull = filesDir.usableSpace < requiredSpace + DEVICE_RESERVE_BYTES
            return overCacheBudget || deviceTooFull
        }

        if (!stillNeedsSpace()) return

        val evictable = cacheFiles
            .filterNot { it.name in protectedNames }
            .sortedBy { it.lastModified() }

        for (file in evictable) {
            if (!stillNeedsSpace()) break
            val length = file.length()
            if (file.delete()) {
                totalUsed -= length
                Log.i(TAG, "Evicted cached media ${file.name} (${length} bytes)")
            }
        }

        if (stillNeedsSpace()) {
            // Everything left is in use. Report rather than delete a playing file —
            // the download will fail and the current playlist keeps running.
            Log.w(
                TAG,
                "Low storage: need $requiredSpace bytes, ${filesDir.usableSpace} free, " +
                    "${protectedNames.size} files protected and retained"
            )
        }
    }

    companion object {
        private const val TAG = "StorageManager"
        private const val CACHE_PREFIX = "content-"
        private const val QUOTA_BYTES = 10L * 1024 * 1024 * 1024
        /** Never fill the partition completely; Android misbehaves near zero. */
        private const val DEVICE_RESERVE_BYTES = 300L * 1024 * 1024
        private const val DEFAULT_ASSUMED_SIZE_BYTES = 50L * 1024 * 1024
    }
}
