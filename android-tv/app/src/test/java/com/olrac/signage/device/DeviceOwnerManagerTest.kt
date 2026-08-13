package com.olrac.signage.device

import android.app.admin.DevicePolicyManager
import android.content.Context
import io.mockk.*
import org.junit.Test
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue

class DeviceOwnerManagerTest {

    @Test
    fun `isDeviceOwner returns true when package is device owner`() {
        val context = mockk<Context>()
        val dpm = mockk<DevicePolicyManager>()

        every { context.getSystemService(Context.DEVICE_POLICY_SERVICE) } returns dpm
        every { context.packageName } returns "com.olrac.signage"
        every { dpm.isDeviceOwnerApp("com.olrac.signage") } returns true

        assertTrue(DeviceOwnerManager.isDeviceOwner(context))
    }

    @Test
    fun `isDeviceOwner returns false when package is not device owner`() {
        val context = mockk<Context>()
        val dpm = mockk<DevicePolicyManager>()

        every { context.getSystemService(Context.DEVICE_POLICY_SERVICE) } returns dpm
        every { context.packageName } returns "com.olrac.signage"
        every { dpm.isDeviceOwnerApp("com.olrac.signage") } returns false

        assertFalse(DeviceOwnerManager.isDeviceOwner(context))
    }

    @Test
    fun `applyKioskPolicy does nothing if not device owner`() {
        val context = mockk<Context>()
        val dpm = mockk<DevicePolicyManager>()

        every { context.getSystemService(Context.DEVICE_POLICY_SERVICE) } returns dpm
        every { context.packageName } returns "com.olrac.signage"
        every { dpm.isDeviceOwnerApp("com.olrac.signage") } returns false

        DeviceOwnerManager.applyKioskPolicy(context)

        // Verify none of the kiosk methods were called
        verify(exactly = 0) { dpm.setLockTaskPackages(any(), any()) }
        verify(exactly = 0) { dpm.addPersistentPreferredActivity(any(), any(), any()) }
        verify(exactly = 0) { dpm.setKeyguardDisabled(any(), any()) }
    }

    @Test
    fun `applyKioskPolicy applies policies when device owner`() {
        val context = mockk<Context>()
        val dpm = mockk<DevicePolicyManager>(relaxed = true)

        every { context.getSystemService(Context.DEVICE_POLICY_SERVICE) } returns dpm
        every { context.packageName } returns "com.olrac.signage"
        every { dpm.isDeviceOwnerApp("com.olrac.signage") } returns true

        DeviceOwnerManager.applyKioskPolicy(context)

        // Verify key policies were applied
        verify { dpm.setLockTaskPackages(any(), arrayOf("com.olrac.signage")) }
        verify { dpm.addPersistentPreferredActivity(any(), any(), any()) }
        verify { dpm.setKeyguardDisabled(any(), true) }
        verify { dpm.setStatusBarDisabled(any(), true) }
        verify { dpm.setPermissionPolicy(any(), DevicePolicyManager.PERMISSION_POLICY_AUTO_GRANT) }
        verify { dpm.setUninstallBlocked(any(), "com.olrac.signage", true) }
    }
}
