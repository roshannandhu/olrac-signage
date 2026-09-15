package com.olrac.signage.ui.screens

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.olrac.signage.boot.WatchdogStatus
import kotlinx.coroutines.delay

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
      // Scrolls because it no longer fits a TV at 48dp padding once the watchdog section is
      // in, and an unscrollable column simply drops "Return to player" off the bottom edge.
      // D-pad focus brings each control into view as it moves.
      Column(
        modifier = Modifier.fillMaxWidth().verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
      ) {
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

    Spacer(modifier = Modifier.height(18.dp))
    WatchdogControls()
}

/**
 * The watchdog's state, and the way to turn it on from the TV itself.
 *
 * Installed from a file, this app has its accessibility switch locked by Android 13+ and the
 * only unlock is a person in App info. The order below is the one Android enforces: "Allow
 * restricted settings" does not appear in App info until someone has first tried the locked
 * switch and been refused, so sending an installer straight to App info finds nothing there.
 */
@Composable
private fun WatchdogControls() {
    val context = LocalContext.current
    var state by remember { mutableStateOf(WatchdogStatus.state(context)) }
    var openError by remember { mutableStateOf<String?>(null) }

    // Re-read while this screen is up: the change happens in Settings, and the installer
    // comes back here expecting to see it. Two cheap reads, so polling is fine.
    LaunchedEffect(Unit) {
        while (true) {
            delay(2_000)
            state = WatchdogStatus.state(context)
        }
    }

    fun open(intent: Intent, what: String) {
        openError = try {
            context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            null
        } catch (e: Exception) {
            "This TV has no $what screen."
        }
    }
    val openAccessibility = { open(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS), "accessibility settings") }
    val openAppInfo = {
        open(
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${context.packageName}")),
            "app info"
        )
    }

    when (state) {
        WatchdogStatus.State.ON -> Text(
            text = "Watchdog: on — keeps the player in front on this TV",
            color = AccentGreen,
            textAlign = TextAlign.Center
        )

        WatchdogStatus.State.OFF -> {
            Text(
                text = "Watchdog: off — turn it on so the player recovers after a reboot",
                color = Color(0xFFFFC46B),
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(10.dp))
            Button(onClick = openAccessibility, colors = secondaryButtonColors()) {
                Text("Turn on watchdog (Accessibility → OLRAC Signage)")
            }
        }

        WatchdogStatus.State.RESTRICTED -> {
            Text(
                text = "Watchdog: blocked by Android",
                color = Color(0xFFFFC46B),
                textAlign = TextAlign.Center
            )
            Text(
                text = "This app was installed from a file, so Android locks its accessibility " +
                    "switch until you allow it:",
                color = Color.LightGray,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = openAccessibility, colors = secondaryButtonColors(), modifier = Modifier.fillMaxWidth()) {
                Text("1. Try the switch once (Accessibility → OLRAC Signage)")
            }
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = openAppInfo, colors = secondaryButtonColors(), modifier = Modifier.fillMaxWidth()) {
                Text("2. App info → ⋮ menu → Allow restricted settings")
            }
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = openAccessibility, colors = secondaryButtonColors(), modifier = Modifier.fillMaxWidth()) {
                Text("3. Turn on watchdog")
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "No ⋮ menu on this TV? From a computer run:\n" +
                    "adb shell appops set ${context.packageName} ACCESS_RESTRICTED_SETTINGS allow",
                color = Color.Gray,
                textAlign = TextAlign.Center
            )
        }
    }
    openError?.let {
        Spacer(modifier = Modifier.height(6.dp))
        Text(text = it, color = Color(0xFFEF4444), textAlign = TextAlign.Center)
    }
}
