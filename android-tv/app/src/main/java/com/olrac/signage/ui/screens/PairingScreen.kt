package com.olrac.signage.ui.screens

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.olrac.signage.data.LaunchState

@Composable
fun PairingScreen(
    state: LaunchState.Pairing,
    serverUrl: String,
    serverError: String?,
    defaultHome: Boolean,
    onSaveServer: (String) -> Unit,
    onChooseHome: () -> Unit
) {
    val detail = when {
        state.pairCode != null && state.connectionMessage != null ->
            "Pairing Code: ${state.pairCode}\n${state.connectionMessage}"

        state.pairCode != null ->
            "Pairing Code: ${state.pairCode}\nEnter this code in the admin dashboard."

        else -> state.connectionMessage ?: "Requesting a pairing code..."
    }

    SetupSurface {
        Text(text = "OLRAC Signage", color = Color.White, textAlign = TextAlign.Center)
        Text(text = detail, color = Color.LightGray, textAlign = TextAlign.Center)
        Spacer(modifier = Modifier.height(28.dp))
        ServerControls(
            serverUrl = serverUrl,
            serverError = serverError,
            defaultHome = defaultHome,
            onSave = onSaveServer,
            onChooseHome = onChooseHome
        )
    }
}
