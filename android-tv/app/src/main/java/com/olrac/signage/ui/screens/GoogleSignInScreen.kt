package com.olrac.signage.ui.screens

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.olrac.signage.data.LaunchState

@Composable
fun GoogleSignInScreen(
    state: LaunchState.GoogleSignIn,
    serverUrl: String,
    serverError: String?,
    defaultHome: Boolean,
    onCancel: () -> Unit,
    onSaveServer: (String) -> Unit,
    onChooseHome: () -> Unit
) {
    SetupSurface {
        Text(text = "Sign in with Google", color = Color.White, textAlign = TextAlign.Center)
        Text(
            text = "On your phone, open ${state.verificationUrl} and enter this code.",
            color = Color.LightGray,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = state.userCode,
            color = AccentGreen,
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.displaySmall
        )

        Spacer(modifier = Modifier.height(20.dp))
        Text(
            text = state.error
                ?: "Waiting for approval... this screen joins the workspace of whoever approves.",
            color = if (state.error != null) Color(0xFFFF8A80) else Color.LightGray,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(16.dp))
        TextButton(onClick = onCancel) {
            Text("Back to sign in", color = Color.LightGray)
        }

        Spacer(modifier = Modifier.height(20.dp))
        ServerControls(
            serverUrl = serverUrl,
            serverError = serverError,
            defaultHome = defaultHome,
            onSave = onSaveServer,
            onChooseHome = onChooseHome
        )
    }
}
