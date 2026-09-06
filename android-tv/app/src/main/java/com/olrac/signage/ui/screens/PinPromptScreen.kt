package com.olrac.signage.ui.screens

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.olrac.signage.data.MaintenanceGesture

@Composable
fun PinPromptScreen(
    expectedPin: String,
    onUnlocked: () -> Unit,
    onCancel: () -> Unit
) {
    var entered by remember { mutableStateOf("") }
    var attemptsLeft by remember { mutableIntStateOf(MaintenanceGesture.MAX_PIN_ATTEMPTS) }
    var error by remember { mutableStateOf<String?>(null) }

    fun submit() {
        if (entered == expectedPin) {
            onUnlocked()
            return
        }
        attemptsLeft -= 1
        entered = ""
        if (attemptsLeft <= 0) onCancel() else error = "Incorrect pin. $attemptsLeft left."
    }

    SetupSurface {
        Text(text = "Maintenance access", color = Color.White)
        Text(
            text = "Enter this screen's 4-digit pin. It is shown on the screen's page in the dashboard.",
            color = Color.LightGray,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(24.dp))
        OutlinedTextField(
            value = entered,
            onValueChange = { typed ->
                entered = typed.filter { it.isDigit() }.take(4)
                error = null
            },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Pin") },
            supportingText = error?.let { message -> { Text(message) } },
            isError = error != null,
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            colors = setupFieldColors()
        )
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = { submit() },
            enabled = entered.length == 4,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = AccentGreen, contentColor = Color.Black)
        ) {
            Text("Unlock")
        }
        Spacer(modifier = Modifier.height(8.dp))
        TextButton(onClick = onCancel) {
            Text("Back to player", color = Color.LightGray)
        }
    }
}
