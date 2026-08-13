package com.olrac.signage.sync

import android.content.Context
import io.mockk.every
import io.mockk.mockk
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File
import java.nio.file.Files

class StorageManagerTest {

    private lateinit var tempDir: File
    private lateinit var context: Context
    private lateinit var storageManager: StorageManager

    @Before
    fun setup() {
        tempDir = Files.createTempDirectory("mockFilesDir").toFile()
        context = mockk(relaxed = true)
        every { context.filesDir } returns tempDir
        storageManager = StorageManager(context)
    }

    @After
    fun teardown() {
        tempDir.deleteRecursively()
    }

    @Test
    fun `ensureQuota respects protectedNames and deletes older unreferenced files when over budget`() {
        // Create files
        val oldFile = File(tempDir, "content-old.mp4").apply {
            createNewFile()
            setLastModified(1000)
            writeBytes(ByteArray(1024 * 1024)) // 1MB
        }
        val protectedFile = File(tempDir, "content-protected.mp4").apply {
            createNewFile()
            setLastModified(500) // even older, but protected
            writeBytes(ByteArray(1024 * 1024)) // 1MB
        }
        val ignoredFile = File(tempDir, "something-else.txt").apply {
            createNewFile()
            setLastModified(100)
            writeBytes(ByteArray(1024 * 1024)) // 1MB
        }

        // Use reflection to access private method `ensureQuota`
        val ensureQuotaMethod = StorageManager::class.java.getDeclaredMethod(
            "ensureQuota",
            Long::class.java,
            Set::class.java
        )
        ensureQuotaMethod.isAccessible = true

        // Simulate requiring 10GB (which triggers eviction because it exceeds QUOTA_BYTES)
        val QUOTA_BYTES = 10L * 1024 * 1024 * 1024
        val requiredSpace = QUOTA_BYTES // this plus existing files will definitely exceed quota

        ensureQuotaMethod.invoke(storageManager, requiredSpace, setOf("content-protected.mp4"))

        // Assertions
        assertFalse("Unprotected old file should be deleted", oldFile.exists())
        assertTrue("Protected file must never be deleted", protectedFile.exists())
        assertTrue("Non-cache files should be ignored", ignoredFile.exists())
    }
}
