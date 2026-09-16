package com.olrac.signage.ui.screens

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsFocused
import androidx.compose.ui.test.assertIsNotFocused
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import com.olrac.signage.boot.SetupRequirement
import com.olrac.signage.boot.SetupRequirementState
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * The bug this screen was reported for: on a TV the remote did nothing at all.
 *
 * Not a styling detail -- with no focused node a D-pad has nowhere to move from, so every
 * arrow and every OK is dropped, and the only two buttons on the screen cannot be reached.
 * These tests fail on a gate that opens with nothing focused.
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class PermissionGateFocusTest {

    @get:Rule
    val compose = createComposeRule()

    private fun show(overlay: Boolean, watchdog: Boolean) {
        compose.setContent {
            PermissionGateScreen(
                states = listOf(
                    SetupRequirementState(SetupRequirement.OVERLAY, overlay),
                    SetupRequirementState(SetupRequirement.WATCHDOG, watchdog)
                ),
                onTurnOn = {}
            )
        }
    }

    @Test
    fun `the remote has somewhere to be the moment the gate opens`() {
        show(overlay = false, watchdog = false)
        val buttons = compose.onAllNodes(hasClickAction())
        buttons[0].assertIsFocused()
    }

    @Test
    fun `focus starts on the switch that is still off`() {
        // Overlay already on: the installer's job is the second row, so that is where the
        // remote must land -- not on a row with nothing left to do.
        show(overlay = true, watchdog = false)
        compose.onAllNodes(hasClickAction() and hasText("Turn on"))[0].assertIsFocused()
        compose.onAllNodes(hasClickAction() and hasText("Change"))[0].assertIsNotFocused()
    }

    @Test
    fun `a granted row keeps a focusable button so focus is never orphaned`() {
        // A disabled button is not focusable. If a row dropped its button on being granted,
        // switching it on while it held focus would leave the screen focusless -- the same
        // dead remote, now with the installer halfway through setup.
        show(overlay = true, watchdog = true)
        compose.onAllNodes(hasClickAction()).fetchSemanticsNodes().let { nodes ->
            assert(nodes.size == 2) { "both rows must keep a reachable button, found ${nodes.size}" }
        }
    }

    @Test
    fun `focus survives the once-a-second re-read`() {
        // The gate re-reads both switches every second, so this screen recomposes with a new
        // list while the installer is still holding the remote. If that handed focus back to
        // nowhere -- or bounced it to the other row -- the remote would die, or move under
        // them, precisely as they were about to press OK.
        val states = mutableStateOf(
            listOf(
                SetupRequirementState(SetupRequirement.OVERLAY, false),
                SetupRequirementState(SetupRequirement.WATCHDOG, false)
            )
        )
        compose.setContent {
            PermissionGateScreen(states = states.value, onTurnOn = {})
        }
        compose.onAllNodes(hasClickAction())[0].assertIsFocused()

        // The tick that turns row 1 green while the remote is sitting on it.
        states.value = listOf(
            SetupRequirementState(SetupRequirement.OVERLAY, true),
            SetupRequirementState(SetupRequirement.WATCHDOG, false)
        )
        compose.waitForIdle()

        compose.onAllNodes(hasClickAction())[0].assertIsFocused()
    }
}
