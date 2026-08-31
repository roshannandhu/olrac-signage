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

class StorageManager(private val context: Context) {

    suspend fun downloadWithIntegrityCheck(
        client: OkHttpClient,
        url: String,
        finalFile: File,
        expectedSha256: String?,
        expectedSizeBytes: Long?,
        protectedNames: Set<String> = emptySet()
    ): File? = withContext(Dispatchers.IO) {
        val requiredSpace = expectedSizeBytes ?: DEFAULT_ASSUMED_SIZE_BYTES

        // Fixed temporary file name so retries target the same file for resuming
        val temporaryFile = File(context.filesDir, "$PART_PREFIX${finalFile.name}.part")
        // Named before the sweep, and protected during it: partial downloads are now
        // evictable (see ensureQuota), and the one we are about to resume must not be the
        // file we free space by deleting.
        ensureQuota(requiredSpace, protectedNames + finalFile.name + temporaryFile.name)
        var downloadedBytes = 0L
        var append = false
        
        if (temporaryFile.exists()) {
            downloadedBytes = temporaryFile.length()
            if (expectedSizeBytes != null && expectedSizeBytes > 0 && downloadedBytes >= expectedSizeBytes) {
                // Stale or exceeded part file; start fresh
                temporaryFile.delete()
                downloadedBytes = 0L
            } else if (downloadedBytes > 0) {
                append = true
            }
        }

        try {
            val requestBuilder = Request.Builder().url(url)
            if (append) {
                requestBuilder.header("Range", "bytes=$downloadedBytes-")
            }
            
            client.newCall(requestBuilder.build()).execute().use { response ->
                if (!response.isSuccessful && response.code != 206) {
                    Log.e(TAG, "Download failed for ${finalFile.name}: HTTP ${response.code} (url: $url)")
                    if (response.code == 416) temporaryFile.delete() // Range Not Satisfiable
                    return@withContext null
                }
                val body = response.body ?: return@withContext null

                // If the server ignored the Range header (returned 200 instead of 206), we must overwrite
                if (append && response.code != 206) {
                    append = false
                    downloadedBytes = 0L
                    temporaryFile.delete()
                }

                FileOutputStream(temporaryFile, append).use { output ->
                    body.byteStream().use { input -> 
                        val buffer = ByteArray(8192)
                        var bytesRead: Int
                        while (input.read(buffer).also { bytesRead = it } != -1) {
                            output.write(buffer, 0, bytesRead)
                            downloadedBytes += bytesRead
                        }
                    }
                    output.fd.sync()
                }

                if (expectedSizeBytes != null && expectedSizeBytes > 0 && downloadedBytes != expectedSizeBytes) {
                    Log.e(TAG, "Size mismatch for ${finalFile.name}: expected $expectedSizeBytes, got $downloadedBytes")
                    // Do NOT delete the temporary file if it's truncated, allow it to resume next sync
                    if (downloadedBytes > expectedSizeBytes) temporaryFile.delete()
                    return@withContext null
                }

                // Do a single SHA-256 pass over the completed file
                val md = MessageDigest.getInstance("SHA-256")
                temporaryFile.inputStream().use { input ->
                    val buffer = ByteArray(8192)
                    var bytesRead: Int
                    while (input.read(buffer).also { bytesRead = it } != -1) {
                        md.update(buffer, 0, bytesRead)
                    }
                }
                
                val actualSha256 = md.digest().joinToString("") { "%02x".format(it) }
                if (!expectedSha256.isNullOrEmpty() && !actualSha256.equals(expectedSha256, ignoreCase = true)) {
                    Log.e(TAG, "SHA256 mismatch for ${finalFile.name}: expected $expectedSha256, got $actualSha256")
                    temporaryFile.delete()
                    return@withContext null
                }
            }
            temporaryFile
        } catch (e: Exception) {
            Log.e(TAG, "Download failed for ${finalFile.name}", e)
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
        // Partial downloads are counted and evicted alongside finished media. They used to
        // be deleted on every failure path, so they never accumulated; now they are kept
        // deliberately so a download can resume, and a flaky link can leave a day's worth of
        // them on disk. Counting only "content-" files made that storage invisible here:
        // usableSpace kept shrinking, nothing in the list was evictable, and every further
        // download failed until the 24h sweep — with the screen unable to free itself.
        val cacheFiles = filesDir.listFiles()
            ?.filter { it.isFile && (it.name.startsWith(CACHE_PREFIX) || it.name.startsWith(PART_PREFIX)) }
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
        const val PART_PREFIX = ".olrac-download-"
        private const val QUOTA_BYTES = 10L * 1024 * 1024 * 1024
        /** Never fill the partition completely; Android misbehaves near zero. */
        private const val DEVICE_RESERVE_BYTES = 300L * 1024 * 1024
        private const val DEFAULT_ASSUMED_SIZE_BYTES = 50L * 1024 * 1024
    }
}
