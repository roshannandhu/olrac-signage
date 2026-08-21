package com.olrac.signage

import android.app.role.RoleManager
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.KeyEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.olrac.signage.data.AppDatabase
import com.olrac.signage.data.DeviceState
import com.olrac.signage.data.LaunchState
import com.olrac.signage.data.LaunchStateResolver
import com.olrac.signage.data.MaintenanceGesture
import com.olrac.signage.data.RegistrationSnapshot
import com.olrac.signage.network.ApiClient
import com.olrac.signage.network.RegisterRequest
import com.olrac.signage.network.SignInRequest
import com.olrac.signage.service.PlaybackService
import com.olrac.signage.ui.PlayerScreen
import com.olrac.signage.telemetry.ScreenshotManager
import com.olrac.signage.network.RealtimeClient
import com.olrac.signage.device.DeviceOwnerManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.IOException

class MainActivity : ComponentActivity() {
    private lateinit var deviceState: DeviceState
    private var launchState by mutableStateOf<LaunchState>(LaunchState.CheckingLocalState)
    private var serverRevision by mutableIntStateOf(0)
    private var serverError by mutableStateOf<String?>(null)
    private var showServerSetup by mutableStateOf(false)
    private var showPinPrompt by mutableStateOf(false)
    private var defaultHome by mutableStateOf(false)
    private var realtimeClient: RealtimeClient? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ScreenshotManager.registerActivity(this)

        configurePlayerWindow()
        deviceState = DeviceState(this)
        val deviceId = deviceState.deviceId

        // The persisted flag is intentionally read before rendering or touching the network.
        launchState = if (deviceState.isPaired) {
            LaunchState.Playing(deviceState.screenName)
        } else {
            LaunchState.CheckingLocalState
        }

        realtimeClient = RealtimeClient(this) { msg ->
            if (msg.optString("type") == "request_screenshot") {
                ScreenshotManager.requestScreenshot()
            }
        }
        realtimeClient?.start()

        PlaybackService.start(this, launchPlayer = false)
        
        DeviceOwnerManager.applyKioskPolicy(this)
        if (DeviceOwnerManager.isDeviceOwner(this)) {
            try {
                startLockTask()
            } catch (e: Exception) {
                // Ignore if it fails
            }
        }

        setContent {
            LaunchedEffect(deviceId, serverRevision) {
                resolveAndRefreshPairing(deviceId)
            }

            if (showPinPrompt) {
                PinPromptScreen(
                    expectedPin = deviceState.maintenancePin,
                    onUnlocked = {
                        showPinPrompt = false
                        showServerSetup = true
                    },
                    onCancel = { showPinPrompt = false }
                )
            } else if (showServerSetup) {
                ServerSetupScreen(
                    serverUrl = ApiClient.effectiveBaseUrl(this),
                    serverError = serverError,
                    defaultHome = defaultHome,
                    onSave = ::saveServerUrl,
                    onChooseHome = ::requestHomeRole,
                    onClose = { showServerSetup = false }
                )
            } else {
                when (val state = launchState) {
                    LaunchState.CheckingLocalState -> BrandedMessage(
                        title = "OLRAC Signage",
                        detail = "Preparing player..."
                    )

                    is LaunchState.Playing -> PlayerScreen()
                    is LaunchState.SignIn -> {
                        val scope = rememberCoroutineScope()
                        SignInScreen(
                            state = state,
                            serverUrl = ApiClient.effectiveBaseUrl(this),
                            serverError = serverError,
                            defaultHome = defaultHome,
                            onSignIn = { username, password, screenName ->
                                scope.launch { submitSignIn(deviceId, username, password, screenName) }
                            },
                            onUsePairingCode = { scope.launch { usePairingCode(deviceId) } },
                            onSaveServer = ::saveServerUrl,
                            onChooseHome = ::requestHomeRole
                        )
                    }

                    is LaunchState.Pairing -> PairingScreen(
                        state = state,
                        serverUrl = ApiClient.effectiveBaseUrl(this),
                        serverError = serverError,
                        defaultHome = defaultHome,
                        onSaveServer = ::saveServerUrl,
                        onChooseHome = ::requestHomeRole
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        defaultHome = isDefaultHomeLauncher()
        hideSystemBars()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    private val maintenanceGesture = MaintenanceGesture()

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        // Only while the player is on screen: inside the setup surfaces these keys are
        // navigation, and matching there would swallow a press mid-form.
        // Auto-repeat from a held key would otherwise flood the gesture buffer.
        if (!showPinPrompt && !showServerSetup && (event == null || event.repeatCount == 0)) {
            if (maintenanceGesture.record(keyCode, System.currentTimeMillis())) {
                // The gesture only asks the question; DeviceState's pin answers it.
                showPinPrompt = true
                return true
            }
        }

        if (keyCode == KeyEvent.KEYCODE_HOME || keyCode == KeyEvent.KEYCODE_APP_SWITCH) {
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onDestroy() {
        super.onDestroy()
        realtimeClient?.stop()
    }

    private suspend fun resolveAndRefreshPairing(deviceId: String) {
        val hasLocalPlaylist = AppDatabase.getDatabase(this).playlistDao().hasItems()
        val localState = LaunchStateResolver.resolveLocal(
            isPaired = deviceState.isPaired,
            hasLocalPlaylist = hasLocalPlaylist
        )

        if (localState is LaunchState.Playing) {
            deviceState.markPaired(deviceState.screenName ?: DeviceState.DEFAULT_SCREEN_NAME)
            launchState = LaunchState.Playing(deviceState.screenName)
            PlaybackService.requestImmediateSync(this)

            val refreshed = LaunchStateResolver.refresh(localState) { register(deviceId) }
            if (refreshed is LaunchState.Playing && !refreshed.screenName.isNullOrBlank()) {
                deviceState.markPaired(refreshed.screenName)
            }
            return
        }

        // Unprovisioned: wait for someone to sign in. Registering here would mint a fresh
        // pairing code on every boot that nobody is looking at, and the old flow refreshed
        // it every four minutes forever.
        launchState = LaunchState.SignIn()
    }

    /**
     * Bind this screen using the operator's own account. The password is passed straight
     * to the call and never persisted — only the fact that the screen is now claimed is.
     */
    private suspend fun submitSignIn(
        deviceId: String,
        username: String,
        password: String,
        screenName: String
    ) {
        launchState = LaunchState.SignIn(busy = true)
        val response = try {
            ApiClient.service(this).signIn(
                SignInRequest(
                    username = username.trim(),
                    password = password,
                    device_id = deviceId,
                    name = screenName.trim().ifBlank { null }
                )
            )
        } catch (_: Exception) {
            launchState = LaunchState.SignIn(
                error = "No connection. Check the server address and try again."
            )
            return
        }

        if (response.isSuccessful) {
            completePairing(response.body()?.name, pairCode = null)
            return
        }

        launchState = LaunchState.SignIn(
            error = when (response.code()) {
                401 -> "That username or password is not right."
                403 -> "That account cannot add screens. Use an owner or editor account."
                409 -> "This workspace has reached its screen limit."
                else -> "Sign in failed (error ${response.code()}). Please try again."
            }
        )
    }

    /** Fallback route: mint a code here and let a dashboard user claim it, as before. */
    private suspend fun usePairingCode(deviceId: String) {
        launchState = LaunchState.Pairing()
        val resolved = LaunchStateResolver.refresh(LaunchState.Pairing()) { register(deviceId) }
        if (resolved is LaunchState.Playing) {
            completePairing(resolved.screenName, pairCode = null)
            return
        }

        launchState = resolved
        waitForPairing(deviceId, resolved as LaunchState.Pairing)
    }

    private suspend fun waitForPairing(deviceId: String, initialState: LaunchState.Pairing) {
        var pairCode = initialState.pairCode
        var codeIssuedAt = if (pairCode == null) 0L else System.currentTimeMillis()

        while (true) {
            try {
                if (pairCode == null || System.currentTimeMillis() - codeIssuedAt >= PAIR_CODE_REFRESH_MS) {
                    val registration = register(deviceId)
                    if (registration.status != LaunchStateResolver.WAITING_PAIRING) {
                        completePairing(registration.screenName, pairCode)
                        return
                    }

                    pairCode = registration.pairCode
                    codeIssuedAt = System.currentTimeMillis()
                    launchState = LaunchState.Pairing(pairCode = pairCode)
                } else {
                    val response = ApiClient.service(this).sync(deviceId)
                    val body = response.body()
                    if (response.isSuccessful &&
                        body?.status != null &&
                        body.status != LaunchStateResolver.WAITING_PAIRING
                    ) {
                        completePairing(screenName = null, pairCode = pairCode)
                        return
                    }

                    if (!response.isSuccessful) {
                        throw IOException("Pairing check failed with HTTP ${response.code()}")
                    }
                }
            } catch (_: Exception) {
                launchState = LaunchState.Pairing(
                    pairCode = pairCode,
                    connectionMessage = "No connection. Pairing will resume automatically."
                )
            }

            delay(PAIRING_RETRY_MS)
        }
    }

    private suspend fun register(deviceId: String): RegistrationSnapshot {
        val response = ApiClient.service(this).register(RegisterRequest(deviceId))
        if (!response.isSuccessful) {
            throw IOException("Registration failed with HTTP ${response.code()}")
        }

        val screen = response.body() ?: throw IOException("Registration returned no screen")
        return RegistrationSnapshot(
            status = screen.status,
            pairCode = screen.pair_code,
            screenName = screen.name
        )
    }

    private fun completePairing(screenName: String?, pairCode: String?) {
        val fallbackName = pairCode?.let { "Screen $it" } ?: DeviceState.DEFAULT_SCREEN_NAME
        deviceState.markPaired(screenName ?: fallbackName)
        launchState = LaunchState.Playing(deviceState.screenName)
        PlaybackService.requestImmediateSync(this)
    }

    private fun saveServerUrl(value: String) {
        try {
            val normalized = ApiClient.normalizeBaseUrl(value)
            deviceState.setApiBaseUrlOverride(normalized)
            serverError = null
            serverRevision += 1
            if (!deviceState.isPaired) launchState = LaunchState.CheckingLocalState
        } catch (exception: IllegalArgumentException) {
            serverError = exception.message ?: "Invalid server URL"
        }
    }

    private fun requestHomeRole() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            if (roleManager.isRoleAvailable(RoleManager.ROLE_HOME)) {
                startActivity(roleManager.createRequestRoleIntent(RoleManager.ROLE_HOME))
                return
            }
        }
        startActivity(Intent(Settings.ACTION_HOME_SETTINGS))
    }

    private fun isDefaultHomeLauncher(): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            return roleManager.isRoleAvailable(RoleManager.ROLE_HOME) &&
                roleManager.isRoleHeld(RoleManager.ROLE_HOME)
        }
        val homeIntent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        return packageManager.resolveActivity(homeIntent, 0)?.activityInfo?.packageName == packageName
    }

    private fun configurePlayerWindow() {
        window.addFlags(
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or
            WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
        )
        WindowCompat.setDecorFitsSystemWindows(window, false)
        hideSystemBars()
    }

    private fun hideSystemBars() {
        WindowInsetsControllerCompat(window, window.decorView).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }

    companion object {
        private const val PAIRING_RETRY_MS = 5_000L
        private const val PAIR_CODE_REFRESH_MS = 4 * 60_000L
    }
}

@Composable
private fun SignInScreen(
    state: LaunchState.SignIn,
    serverUrl: String,
    serverError: String?,
    defaultHome: Boolean,
    onSignIn: (String, String, String) -> Unit,
    onUsePairingCode: () -> Unit,
    onSaveServer: (String) -> Unit,
    onChooseHome: () -> Unit
) {
    var username by remember { mutableStateOf("") }
    // Held only for the duration of the call; nothing writes it to DeviceState.
    var password by remember { mutableStateOf("") }
    var screenName by remember { mutableStateOf("") }
    val canSubmit = username.isNotBlank() && password.isNotEmpty() && !state.busy

    SetupSurface {
        Text(text = "Sign in to OLRAC", color = Color.White, textAlign = TextAlign.Center)
        Text(
            text = "Use your OLRAC account and this screen joins that workspace.",
            color = Color.LightGray,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(24.dp))

        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Username") },
            singleLine = true,
            enabled = !state.busy,
            colors = setupFieldColors()
        )
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Password") },
            singleLine = true,
            enabled = !state.busy,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            colors = setupFieldColors()
        )
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = screenName,
            onValueChange = { screenName = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Name this screen (optional)") },
            supportingText = state.error?.let { message -> { Text(message) } },
            isError = state.error != null,
            singleLine = true,
            enabled = !state.busy,
            colors = setupFieldColors()
        )

        Spacer(modifier = Modifier.height(20.dp))
        Button(
            onClick = {
                onSignIn(username, password, screenName)
                // Clear the credential from composition as soon as it has been handed over.
                password = ""
            },
            enabled = canSubmit,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = AccentGreen, contentColor = Color.Black)
        ) {
            Text(if (state.busy) "Signing in..." else "Sign in")
        }

        Spacer(modifier = Modifier.height(8.dp))
        TextButton(onClick = onUsePairingCode, enabled = !state.busy) {
            Text("Use a pairing code instead", color = Color.LightGray)
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

@Composable
private fun PairingScreen(
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

/**
 * Pin gate in front of [ServerSetupScreen], which can repoint the TV at another server.
 *
 * Verified against the locally cached pin rather than the server, because the screen it
 * guards is the one an installer needs when the server is exactly what is broken.
 */
@Composable
private fun PinPromptScreen(
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
        // Closing after a few misses keeps a 4-digit pin out of reach of someone
        // patiently trying codes on the remote: each round costs them the gesture again.
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

@Composable
private fun ServerSetupScreen(
    serverUrl: String,
    serverError: String?,
    defaultHome: Boolean,
    onSave: (String) -> Unit,
    onChooseHome: () -> Unit,
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
        Button(onClick = onClose, colors = secondaryButtonColors()) {
            Text("Return to player")
        }
    }
}

@Composable
private fun ServerControls(
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
}

/** Shared field styling for every text input on the dark setup surfaces. */
@Composable
private fun setupFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = Color.White,
    unfocusedTextColor = Color.White,
    focusedBorderColor = AccentGreen,
    unfocusedBorderColor = Color.DarkGray,
    focusedLabelColor = AccentGreen,
    unfocusedLabelColor = Color.LightGray,
    cursorColor = AccentGreen,
    errorTextColor = Color(0xFFFF8A80)
)

@Composable
private fun SetupSurface(content: @Composable () -> Unit) {
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
private fun BrandedMessage(title: String, detail: String) {
    SetupSurface {
        Text(text = title, color = Color.White, textAlign = TextAlign.Center)
        Text(text = detail, color = Color.LightGray, textAlign = TextAlign.Center)
    }
}

@Composable
private fun secondaryButtonColors() = ButtonDefaults.buttonColors(
    containerColor = Color(0xFF202A38),
    contentColor = Color.White
)

private val AccentGreen = Color(0xFF68E0A0)
