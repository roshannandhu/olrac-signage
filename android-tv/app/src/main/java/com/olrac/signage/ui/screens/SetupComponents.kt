package com.olrac.signage.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

val AccentGreen = Color(0xFF68E0A0)

@Composable
fun SetupSurface(content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF070A0F))
            .padding(48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 760.dp)
                .fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            content()
        }
    }
}

@Composable
fun BrandedMessage(title: String, detail: String) {
    SetupSurface {
        Text(text = title, color = Color.White, textAlign = TextAlign.Center)
        Text(text = detail, color = Color.LightGray, textAlign = TextAlign.Center)
    }
}

@Composable
fun secondaryButtonColors() = ButtonDefaults.buttonColors(
    containerColor = Color(0xFF202A38),
    contentColor = Color.White
)

@Composable
fun setupFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = Color.White,
    unfocusedTextColor = Color.White,
    focusedBorderColor = AccentGreen,
    unfocusedBorderColor = Color.DarkGray,
    focusedLabelColor = AccentGreen,
    unfocusedLabelColor = Color.LightGray,
    cursorColor = AccentGreen,
    errorTextColor = Color(0xFFFF8A80)
)
