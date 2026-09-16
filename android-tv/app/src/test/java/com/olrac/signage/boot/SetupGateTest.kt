package com.olrac.signage.boot

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SetupGateTest {

    private fun states(overlay: Boolean, watchdog: Boolean, autoUpdate: Boolean = true) = listOf(
        SetupRequirementState(SetupRequirement.OVERLAY, overlay),
        SetupRequirementState(SetupRequirement.WATCHDOG, watchdog),
        SetupRequirementState(SetupRequirement.AUTO_UPDATE, autoUpdate)
    )

    @Test
    fun `gate stays up until every switch is on`() {
        assertFalse(SetupGate.isSatisfied(states(overlay = false, watchdog = false, autoUpdate = false)))
        assertFalse(SetupGate.isSatisfied(states(overlay = true, watchdog = false, autoUpdate = false)))
        assertFalse(SetupGate.isSatisfied(states(overlay = false, watchdog = true, autoUpdate = false)))
        assertFalse(SetupGate.isSatisfied(states(overlay = true, watchdog = true, autoUpdate = false)))
        assertFalse(SetupGate.isSatisfied(states(overlay = false, watchdog = true, autoUpdate = true)))
        assertFalse(SetupGate.isSatisfied(states(overlay = true, watchdog = false, autoUpdate = true)))
        assertTrue(SetupGate.isSatisfied(states(overlay = true, watchdog = true, autoUpdate = true)))
    }

    @Test
    fun `an empty list is not a satisfied gate`() {
        // Guards the order of reads: "nothing to do" must not come from "nothing read yet".
        assertFalse(SetupGate.isSatisfied(emptyList()))
    }

    @Test
    fun `focus lands on the first switch still off`() {
        assertEquals(0, SetupGate.initialFocusIndex(states(overlay = false, watchdog = false, autoUpdate = false)))
        assertEquals(0, SetupGate.initialFocusIndex(states(overlay = false, watchdog = true, autoUpdate = true)))
        assertEquals(1, SetupGate.initialFocusIndex(states(overlay = true, watchdog = false, autoUpdate = true)))
        assertEquals(2, SetupGate.initialFocusIndex(states(overlay = true, watchdog = true, autoUpdate = false)))
    }

    @Test
    fun `focus still addresses a real row when nothing is pending`() {
        // The remote-dead bug: an index addressing no row leaves the screen with nothing
        // focused. Such a gate is closing anyway, but it must never be the thing that
        // produces a focusless screen.
        val all = states(overlay = true, watchdog = true, autoUpdate = true)
        assertTrue(SetupGate.initialFocusIndex(all) in all.indices)
    }

    @Test
    fun `the switch that gets a TV playing at all is listed first`() {
        assertEquals(
            listOf(SetupRequirement.OVERLAY, SetupRequirement.WATCHDOG, SetupRequirement.AUTO_UPDATE),
            SetupGate.ORDER
        )
    }
}
