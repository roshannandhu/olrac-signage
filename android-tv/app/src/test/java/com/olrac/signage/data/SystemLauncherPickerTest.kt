package com.olrac.signage.data

import com.olrac.signage.data.SystemLauncherPicker.Candidate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SystemLauncherPickerTest {
    private val own = "com.olrac.signage"

    @Test
    fun konkaPicksGoogleTvLauncherNotSettingsOrSetup() {
        // The exact HOME list the KONKA 2K D5STV reported, in that order.
        val candidates = listOf(
            Candidate("com.google.android.tungsten.setupwraith", "SetupActivity"),
            Candidate(own, "com.olrac.signage.MainActivity"),
            Candidate("com.realtek.systemservice", "Home"),
            Candidate("com.android.tv.settings", "Settings"),
            Candidate("com.google.android.apps.tv.launcherx", "LauncherActivity"),
        )
        assertEquals("com.google.android.apps.tv.launcherx", SystemLauncherPicker.pick(candidates, own)?.packageName)
    }

    @Test
    fun tabletPicksLauncher3() {
        val candidates = listOf(
            Candidate(own, "com.olrac.signage.MainActivity"),
            Candidate("com.android.settings", "FallbackHome"),
            Candidate("com.android.launcher3", "Launcher"),
        )
        assertEquals("com.android.launcher3", SystemLauncherPicker.pick(candidates, own)?.packageName)
    }

    @Test
    fun neverPicksThePlayerItself() {
        assertNull(SystemLauncherPicker.pick(listOf(Candidate(own, "MainActivity")), own))
    }

    @Test
    fun settlesForWhatExistsWhenNothingLooksLikeALauncher() {
        val candidates = listOf(Candidate(own, "MainActivity"), Candidate("com.android.settings", "FallbackHome"))
        assertEquals("com.android.settings", SystemLauncherPicker.pick(candidates, own)?.packageName)
    }
}
