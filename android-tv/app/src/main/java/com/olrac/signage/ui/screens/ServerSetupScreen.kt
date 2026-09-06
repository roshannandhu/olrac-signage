package com.olrac.signage.ui.screens

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

@Composable
fun ServerSetupScreen(
    serverUrl: String,
    serverError: String?,
    defaultHome: Boolean,
    onSave: (String) -> Unit,
    onChooseHome: () -> Unit,
    onUnlink: () -> Unit,
    onClose: () -> Unit
) {
    SetupSurface {
        Text(text = "Player setup", color = Color.White)
        Text(
            text = "Configure this TV's control-plane address.",
            color = Color.LightGray,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(24.dp))
        ServerControls(serverUrl, serverError, defaultHome, onSave, onChooseHome)
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = onUnlink,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFEF4444), contentColor = Color.White),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Switch Account / Unlink Screen")
        }
        Spacer(modifier = Modifier.height(10.dp))
        Button(onClick = onClose, colors = secondaryButtonColors(), modifier = Modifier.fillMaxWidth()) {
            Text("Return to player")
        }
    }
}

@Composable
fun ServerControls(
    serverUrl: String,
    serverError: String?,
    defaultHome: Boolean,
    onSave: (String) -> Unit,
    onChooseHome: () -> Unit
) {
    var value by remember(serverUrl) { mutableStateOf(serverUrl) }

    OutlinedTextField(
        value = value,
        onValueChange = { value = it },
        modifier = Modifier.fillMaxWidth(),
        label = { Text("Server URL") },
        supportingText = serverError?.let { error -> { Text(error) } },
        isError = serverError != null,
        singleLine = true,
        colors = setupFieldColors()
    )
    Spacer(modifier = Modifier.height(12.dp))
    Button(
        onClick = { onSave(value) },
        modifier = Modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(containerColor = AccentGreen, contentColor = Color.Black)
    ) {
        Text("Save and reconnect")
    }
    Spacer(modifier = Modifier.height(18.dp))
    Text(
        text = if (defaultHome) {
            "Default TV launcher: enabled"
        } else {
            "Default TV launcher: not enabled — required for reliable reboot recovery"
        },
        color = if (defaultHome) AccentGreen else Color(0xFFFFC46B),
        textAlign = TextAlign.Center
    )
    if (!defaultHome) {
        Spacer(modifier = Modifier.height(10.dp))
        Button(onClick = onChooseHome, colors = secondaryButtonColors()) {
            Text("Choose OLRAC as TV launcher")
        }
    }
    
    val context = LocalContext.current
    Spacer(modifier = Modifier.height(18.dp))
    Button(
        onClick = { 
            val intent = Intent(Settings.ACTION_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            try { context.startActivity(intent) } catch (e: Exception) {}
        }, 
        colors = secondaryButtonColors()
    ) {
        Text("Open Android System Settings")
    }
}
