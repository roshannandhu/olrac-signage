package com.olrac.signage.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.olrac.signage.boot.SetupGate
import com.olrac.signage.boot.SetupRequirement
import com.olrac.signage.boot.SetupRequirementState

/**
 * The screen a TV shows when it cannot hold its own display yet: one row per switch that is
 * still off, each with a button that opens the exact settings page for it.
 *
 * Two things about this screen exist because of the remote, not the design:
 *
 * 1. Something must ask for focus. A freshly composed screen has no focused node, and a
 *    D-pad has nowhere to move from nowhere -- so every key is dropped and the remote looks
 *    broken. Nothing else in this app had hit it, because every other setup screen is
 *    reached by someone already touching the panel. Here the remote is all there is.
 *
 * 2. No row's button is ever removed or disabled, not even once its switch is on. A disabled
 *    Button is not focusable, so switching one on while it held focus would drop focus back
 *    to nowhere and kill the remote a second time -- with the installer standing in front of
 *    a half-finished gate. A granted row keeps an enabled button that reopens the same page,
 *    which is also how someone checks what they just did.
 */
@Composable
fun PermissionGateScreen(
    states: List<SetupRequirementState>,
    onTurnOn: (SetupRequirement) -> Unit
) {
    // Captured once: which row to land on is answered when the gate opens. Recomputing it as
    // switches flip would yank focus out from under whoever is moving the remote.
    val initialFocus = remember { SetupGate.initialFocusIndex(states) }
    val focusRequester = remember { FocusRequester() }
    var focusLanded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        // Asked for until a row reports it actually has focus, not asked for once and hoped.
        //
        // requestFocus throws if its node is not attached yet, and whether it is attached on
        // the first pass is a timing detail that differs between devices. A single guarded
        // call would swallow that failure and leave the screen with nothing focused -- the
        // dead remote again, and silent, which is the hard version to diagnose from a TV on
        // a wall. Retrying across the first frames costs nothing when it lands immediately.
        repeat(FOCUS_ATTEMPTS) {
            if (focusLanded) return@LaunchedEffect
            runCatching { focusRequester.requestFocus() }
            withFrameNanos { }
        }
    }

    SetupSurface {
        val countWord = when (states.size) {
            1 -> "One"
            2 -> "Two"
            3 -> "Three"
            else -> states.size.toString()
        }
        Text(
            text = "$countWord switches to turn on",
            color = Color.White,
            fontSize = 30.sp,
            fontWeight = FontWeight.SemiBold
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "This TV needs all required switches on before it can show your ads on its own. " +
                "Use the arrow keys and OK on the remote.",
            color = Color.LightGray,
            fontSize = 16.sp
        )
        Spacer(modifier = Modifier.height(32.dp))

        states.forEachIndexed { index, state ->
            RequirementRow(
                position = index + 1,
                state = state,
                onTurnOn = { onTurnOn(state.requirement) },
                onFocused = { if (index == initialFocus) focusLanded = true },
                modifier = if (index == initialFocus) {
                    Modifier.focusRequester(focusRequester)
                } else {
                    Modifier
                }
            )
            Spacer(modifier = Modifier.height(16.dp))
        }

        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "This screen closes by itself once all are on.",
            color = Color.Gray,
            fontSize = 14.sp
        )
    }
}

@Composable
private fun RequirementRow(
    position: Int,
    state: SetupRequirementState,
    onTurnOn: () -> Unit,
    onFocused: () -> Unit,
    modifier: Modifier = Modifier
) {
    var focused by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .border(
                width = if (focused) 2.dp else 1.dp,
                color = if (focused) AccentGreen else Color(0xFF243043),
                shape = RoundedCornerShape(12.dp)
            )
            .padding(20.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "$position. ${title(state.requirement)}",
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = detail(state.requirement), color = Color.LightGray, fontSize = 14.sp)
            if (state.granted) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(text = "On", color = AccentGreen, fontSize = 14.sp)
            }
        }

        Spacer(modifier = Modifier.width(24.dp))

        Button(
            onClick = onTurnOn,
            modifier = modifier.onFocusChanged {
                focused = it.isFocused
                if (it.isFocused) onFocused()
            },
            colors = if (state.granted) {
                secondaryButtonColors()
            } else {
                ButtonDefaults.buttonColors(
                    containerColor = AccentGreen,
                    contentColor = Color(0xFF06210F)
                )
            },
            shape = RoundedCornerShape(8.dp)
        ) {
            Text(
                text = if (state.granted) "Change" else "Turn on",
                fontSize = 16.sp,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
            )
        }
    }
}

private fun title(requirement: SetupRequirement): String = when (requirement) {
    SetupRequirement.OVERLAY -> "Display over other apps"
    SetupRequirement.WATCHDOG -> "Keep player on screen"
    SetupRequirement.AUTO_UPDATE -> "Allow auto-updates"
}

private fun detail(requirement: SetupRequirement): String = when (requirement) {
    SetupRequirement.OVERLAY ->
        "Lets the player bring itself back to the front after the TV restarts."
    SetupRequirement.WATCHDOG ->
        "Puts the player back if a system message or another app covers it."
    SetupRequirement.AUTO_UPDATE ->
        "Lets the TV install player updates unattended without manual intervention."
}

/** Frames to keep asking for focus before giving up -- about half a second at 60fps. */
private const val FOCUS_ATTEMPTS = 30
