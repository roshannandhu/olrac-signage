package com.olrac.signage

import android.app.role.RoleManager
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.KeyEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
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
import com.olrac.signage.network.GooglePollRequest
import com.olrac.signage.network.GoogleStartRequest
import com.olrac.signage.network.GoogleStartResponse
import com.olrac.signage.network.SignInRequest
import com.olrac.signage.service.PlaybackService
import com.olrac.signage.ui.PlayerScreen
import com.olrac.signage.ui.screens.*
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        volumeControlStream = android.media.AudioManager.STREAM_MUSIC
        ScreenshotManager.registerActivity(this)

        configurePlayerWindow()
        deviceState = DeviceState(this)
        val deviceId = deviceState.deviceId

        // The persisted flag is intentionally read before rendering or touching the network.
        val forceSignIn = intent?.getBooleanExtra("show_signin", false) ?: false
        launchState = if (forceSignIn) {
            LaunchState.SignIn()
        } else if (deviceState.isPaired) {
            LaunchState.Playing(deviceState.screenName)
        } else {
            LaunchState.CheckingLocalState
        }

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
                if (intent?.getBooleanExtra("show_signin", false) != true) {
                    resolveAndRefreshPairing(deviceId)
                }
            }

            if (showPinPrompt) {
                PinPromptScreen(
                    expectedPin = deviceState.maintenancePin,
                    onUnlocked = {
                        showPinPrompt = false
                        // Correct pin: only now is it safe to drop kiosk pinning so the
                        // setup screen's system dialogs can open.
                        enterMaintenance()
                        showServerSetup = true
                    },
                    onCancel = {
                        showPinPrompt = false
                        // Nothing was unpinned (the gesture no longer does that), but re-arm
                        // defensively in case the lock was dropped by an earlier path.
                        rearmLockTask()
                    }
                )
            } else if (showServerSetup) {
                ServerSetupScreen(
                    serverUrl = ApiClient.effectiveBaseUrl(this),
                    serverError = serverError,
                    defaultHome = defaultHome,
                    onSave = ::saveServerUrl,
                    onChooseHome = ::requestHomeRole,
                    onUnlink = {
                        deviceState.clearPairing()
                        showServerSetup = false
                        launchState = LaunchState.SignIn()
                        rearmLockTask()
                    },
                    onClose = {
                        showServerSetup = false
                        rearmLockTask()
                    }
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
                        // Ask once per visit which routes this server offers. Keyed on the
                        // base URL so pointing the TV at a different server re-asks rather
                        // than keeping the previous server's answer.
                        LaunchedEffect(ApiClient.effectiveBaseUrl(this@MainActivity)) {
                            refreshAuthMethods()
                        }
                        SignInScreen(
                            state = state,
                            serverUrl = ApiClient.effectiveBaseUrl(this),
                            serverError = serverError,
                            defaultHome = defaultHome,
                            defaultScreenName = deviceState.hardwareName,
                            onUseGoogle = { screenName ->
                                scope.launch { startGoogleSignIn(deviceId, screenName) }
                            },
                            onSaveServer = ::saveServerUrl,
                            onChooseHome = ::requestHomeRole
                        )
                    }

                    is LaunchState.GoogleSignIn -> GoogleSignInScreen(
                        state = state,
                        serverUrl = ApiClient.effectiveBaseUrl(this),
                        serverError = serverError,
                        defaultHome = defaultHome,
                        onCancel = { launchState = LaunchState.SignIn() },
                        onSaveServer = ::saveServerUrl,
                        onChooseHome = ::requestHomeRole
                    )

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

    /** Drop kiosk pinning so the setup screen's system dialogs (launcher-role chooser,
     *  sign-in browser) can open. Called only AFTER a correct maintenance pin. */
    private fun enterMaintenance() {
        if (DeviceOwnerManager.isDeviceOwner(this)) {
            try { stopLockTask() } catch (e: Exception) {}
        }
    }

    /** Re-pin the kiosk once no maintenance surface is open. Safe to call when already
     *  pinned (a no-op). This is what closes the hole where the gesture alone, or a
     *  cancelled/failed pin, left the TV un-pinned until the next reboot. */
    private fun rearmLockTask() {
        if (DeviceOwnerManager.isDeviceOwner(this) && !showPinPrompt && !showServerSetup) {
            try { startLockTask() } catch (e: Exception) {}
        }
    }

    override fun onResume() {
        super.onResume()
        defaultHome = isDefaultHomeLauncher()
        hideSystemBars()
        // Backstop: re-pin whenever we are back on the player with no maintenance surface
        // open -- covers a cancelled pin, a wrong pin, and returning from the system
        // launcher-role chooser.
        rearmLockTask()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    private val maintenanceGesture = MaintenanceGesture()
    private val homePressTimes = ArrayDeque<Long>()

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)

        // Handle Google OAuth Deep Link Return
        val data = intent?.data
        if (data != null && data.scheme == "olrac" && data.host == "auth") {
            val screenName = data.getQueryParameter("screen_name")
            val screenId = data.getQueryParameter("screen_id")
            if (data.path == "/success" || screenId != null) {
                completePairing(screenName ?: deviceState.hardwareName, pairCode = null)
                return
            } else if (data.path == "/failed") {
                val errorMsg = data.getQueryParameter("error") ?: "Google authentication failed"
                launchState = LaunchState.SignIn(error = errorMsg)
                return
            }
        }

        // If the user presses the HOME button and this app is the default launcher, 
        // the OS routes the intent here instead of onKeyDown. 
        // We detect 3 presses within 3 seconds to trigger the PIN prompt.
        if (intent?.hasCategory(Intent.CATEGORY_HOME) == true) {
            val now = System.currentTimeMillis()
            homePressTimes.addLast(now)
            while (homePressTimes.isNotEmpty() && now - homePressTimes.first() > 3000L) {
                homePressTimes.removeFirst()
            }
            if (homePressTimes.size >= 3) {
                homePressTimes.clear()
                // Reveal the PIN prompt only; lock-task is dropped after a correct pin
                // (onUnlocked), not here -- otherwise three HOME presses defeat the kiosk.
                showPinPrompt = true
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        // Only while the player is on screen: inside the setup surfaces these keys are
        // navigation, and matching there would swallow a press mid-form.
        // Auto-repeat from a held key would otherwise flood the gesture buffer.
        if (!showPinPrompt && !showServerSetup && (event == null || event.repeatCount == 0)) {
            if (maintenanceGesture.record(keyCode, System.currentTimeMillis())) {
                // Reveal the PIN prompt only. The kiosk stays pinned until a CORRECT pin is
                // entered (see onUnlocked). Dropping lock-task here let the gesture alone
                // un-pin the TV, and cancelling then left it open until the next reboot.
                showPinPrompt = true
                return true
            }
        }

        when (keyCode) {
            KeyEvent.KEYCODE_VOLUME_DOWN -> {
                val audioManager = getSystemService(android.content.Context.AUDIO_SERVICE) as? android.media.AudioManager
                audioManager?.adjustStreamVolume(
                    android.media.AudioManager.STREAM_MUSIC,
                    android.media.AudioManager.ADJUST_LOWER,
                    android.media.AudioManager.FLAG_SHOW_UI
                )
                return true
            }
            KeyEvent.KEYCODE_VOLUME_UP -> {
                val audioManager = getSystemService(android.content.Context.AUDIO_SERVICE) as? android.media.AudioManager
                audioManager?.adjustStreamVolume(
                    android.media.AudioManager.STREAM_MUSIC,
                    android.media.AudioManager.ADJUST_RAISE,
                    android.media.AudioManager.FLAG_SHOW_UI
                )
                return true
            }
            KeyEvent.KEYCODE_VOLUME_MUTE, KeyEvent.KEYCODE_MUTE -> {
                val audioManager = getSystemService(android.content.Context.AUDIO_SERVICE) as? android.media.AudioManager
                audioManager?.adjustStreamVolume(
                    android.media.AudioManager.STREAM_MUSIC,
                    android.media.AudioManager.ADJUST_TOGGLE_MUTE,
                    android.media.AudioManager.FLAG_SHOW_UI
                )
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

        val registration = try { register(deviceId) } catch (_: Exception) { null }
        if (registration != null && registration.status != LaunchStateResolver.WAITING_PAIRING) {
            completePairing(registration.screenName, pairCode = null)
            return
        }

        // Unprovisioned: wait for someone to sign in.
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
                    name = screenName.trim().ifBlank { null },
                    installation_id = deviceState.installationId,
                    model = deviceState.deviceModel,
                    manufacturer = deviceState.manufacturer
                )
            )
        } catch (_: Exception) {
            launchState = LaunchState.SignIn(
                error = "No connection. Check the server address and try again."
            )
            return
        }

        if (response.isSuccessful) {
            completePairing(response.body()?.name, pairCode = null, deviceSecret = response.body()?.device_secret)
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

    /**
     * Learn which sign-in routes this deployment offers, and hide the ones it does not.
     *
     * Failure is deliberately silent and leaves googleEnabled false: this runs on a TV that
     * may have no network yet, and an error toast about an optional button would be noise
     * on top of the connection problem the installer is already looking at.
     */
    private suspend fun refreshAuthMethods() {
        val enabled = try {
            ApiClient.service(this).authMethods().body()?.google ?: false
        } catch (_: Exception) {
            false
        }
        (launchState as? LaunchState.SignIn)?.let { current ->
            if (current.googleEnabled != enabled) {
                launchState = current.copy(googleEnabled = enabled)
            }
        }
    }

    /**
     * Bind this screen from a Google account, via the device authorisation grant.
     *
     * The TV shows a code and polls; the installer approves on their own phone. No OAuth
     * secret and no Google SDK live here -- the server does both halves of the exchange,
     * which is what lets this work on the AOSP boxes that have no Play Services at all.
     */
    private suspend fun startGoogleSignIn(deviceId: String, screenName: String) {
        launchState = LaunchState.SignIn(busy = true)

        // 1. Fetch direct Google OAuth URL from backend
        val oauthResp = try {
            ApiClient.service(this).getGoogleOAuthUrl(
                deviceId = deviceId,
                name = screenName.trim().ifBlank { null },
                installationId = deviceState.installationId,
                model = deviceState.deviceModel,
                manufacturer = deviceState.manufacturer
            )
        } catch (_: Exception) {
            null
        }

        val baseUrl = ApiClient.effectiveBaseUrl(this)
        val fallbackOAuthUrl = "${baseUrl}api/screens/google/oauth-callback"
        val oauthUrl = oauthResp?.body()?.oauth_url ?: "${baseUrl}api/screens/google/oauth-page?redirect_uri=${Uri.encode(fallbackOAuthUrl)}"

        // Open direct Google OAuth redirect in Browser / Custom Tab
        try {
            val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(oauthUrl)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(browserIntent)
        } catch (e: Exception) {
            try {
                val customTabsIntent = CustomTabsIntent.Builder().build()
                customTabsIntent.launchUrl(this, Uri.parse(oauthUrl))
            } catch (_: Exception) {}
        }

        // 2. Also start background polling so if approved on web or device flow, it auto-transitions
        val started = try {
            ApiClient.service(this).googleStart(
                GoogleStartRequest(
                    device_id = deviceId,
                    name = screenName.trim().ifBlank { null },
                    installation_id = deviceState.installationId,
                    model = deviceState.deviceModel,
                    manufacturer = deviceState.manufacturer
                )
            )
        } catch (_: Exception) {
            null
        }

        val body = started?.body()
        if (body != null) {
            // Check immediate poll for instant 1-tap Google binding
            val initialPoll = try {
                ApiClient.service(this).googlePoll(GooglePollRequest(body.poll_token))
            } catch (_: Exception) {
                null
            }

            if (initialPoll?.isSuccessful == true && initialPoll.body()?.status == "bound") {
                completePairing(
                    initialPoll.body()?.screen?.name,
                    pairCode = null,
                    deviceSecret = initialPoll.body()?.screen?.device_secret,
                )
                return
            }

            launchState = LaunchState.GoogleSignIn(
                userCode = body.user_code,
                verificationUrl = body.verification_url
            )
            pollGoogleSignIn(body)
        } else {
            // The device grant is not configured on this server -- google/start answers 503
            // "Google sign-in is not enabled" -- while the browser opened above IS, and it
            // binds the screen server side.
            //
            // With nothing polling here, the only route back into the app was the olrac://
            // deep link, and a TV browser is free to refuse it ("App deeplink blocked" on
            // TCL). The browser showed "Display Connected" while this dropped straight back
            // to the sign-in form, and the panel stayed there through every relaunch.
            awaitBrowserSignIn(deviceId)
        }
    }

    /**
     * Wait for the browser half to finish, asking OUR server rather than Google.
     *
     * register() reports the binding whoever made it -- the TV's own browser, a phone, or
     * an operator redeeming a pairing code -- so this needs neither a device grant nor a
     * deep link the browser is allowed to block.
     */
    private suspend fun awaitBrowserSignIn(deviceId: String) {
        val deadline = System.currentTimeMillis() + BROWSER_SIGN_IN_TIMEOUT_MS
        while (System.currentTimeMillis() < deadline) {
            delay(PAIRING_RETRY_MS)
            // The installer backed out to the form; stop waiting with them.
            if (launchState !is LaunchState.SignIn) return
            val registration = try {
                register(deviceId)
            } catch (_: Exception) {
                // A dropped connection is not a refusal -- the browser half may still be
                // mid-flow on a flaky panel. Keep waiting until the deadline.
                continue
            }
            if (registration.status != LaunchStateResolver.WAITING_PAIRING) {
                completePairing(registration.screenName, pairCode = null)
                return
            }
        }
        launchState = LaunchState.SignIn(busy = false)
    }

    /** Ask the server whether the phone half has finished, until it has or time runs out. */
    private suspend fun pollGoogleSignIn(started: GoogleStartResponse) {
        // Googles own floor, echoed back by the server. Polling faster earns `slow_down`,
        // not a token, so the interval is widened rather than ignored when that arrives.
        var intervalMs = started.interval.coerceAtLeast(5) * 1_000L
        val deadline = System.currentTimeMillis() + started.expires_in * 1_000L

        while (System.currentTimeMillis() < deadline) {
            delay(intervalMs)
            // The installer backed out to the sign-in form; stop polling with them.
            val showing = launchState as? LaunchState.GoogleSignIn ?: return

            val response = try {
                ApiClient.service(this).googlePoll(GooglePollRequest(started.poll_token))
            } catch (_: Exception) {
                // A dropped connection mid-approval is not a refusal. Keep waiting: the
                // code on screen is still valid and the installer still holds a phone.
                continue
            }

            if (!response.isSuccessful) {
                launchState = showing.copy(
                    error = when (response.code()) {
                        403 -> "That Google account cannot add screens here. " +
                            "Check it is on your OLRAC profile, with an owner or editor role."
                        401 -> "This sign-in expired. Go back and start again."
                        409 -> "This workspace has reached its screen limit."
                        else -> "Sign in failed (error ${response.code()})."
                    }
                )
                return
            }

            when (val status = response.body()?.status) {
                "bound" -> {
                    completePairing(
                        response.body()?.screen?.name,
                        pairCode = null,
                        deviceSecret = response.body()?.screen?.device_secret,
                    )
                    return
                }
                "pending" -> Unit
                "slow_down" -> intervalMs += 5_000L
                "denied" -> {
                    launchState = showing.copy(error = "That request was declined on the phone.")
                    return
                }
                "expired" -> {
                    launchState = showing.copy(error = "This code expired. Go back and start again.")
                    return
                }
                else -> {
                    launchState = showing.copy(error = "Unexpected reply from the server ($status).")
                    return
                }
            }
        }

        (launchState as? LaunchState.GoogleSignIn)?.let {
            launchState = it.copy(error = "This code expired. Go back and start again.")
        }
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
        val response = ApiClient.service(this).register(
            RegisterRequest(
                device_id = deviceId,
                installation_id = deviceState.installationId,
                hardware_name = deviceState.hardwareName,
                device_model = deviceState.deviceModel,
                manufacturer = deviceState.manufacturer
            )
        )
        if (!response.isSuccessful) {
            throw IOException("Registration failed with HTTP ${response.code()}")
        }

        val screen = response.body() ?: throw IOException("Registration returned no screen")
        // Delivered exactly once, on the first poll after an operator redeemed the pairing
        // code. The /pair response goes to their dashboard, so this is the only channel a
        // pair-code screen has for learning its own credential.
        screen.device_secret?.takeIf { it.isNotBlank() }?.let {
            deviceState.setDeviceSecret(it)
            ApiClient.clearToken()
        }
        return RegistrationSnapshot(
            status = screen.status,
            pairCode = screen.pair_code,
            screenName = screen.name
        )
    }

    private fun completePairing(screenName: String?, pairCode: String?, deviceSecret: String? = null) {
        val fallbackName = pairCode?.let { "Screen $it" } ?: DeviceState.DEFAULT_SCREEN_NAME
        // The server returns this exactly once, from whichever route bound the screen. It
        // is the credential every later request authenticates with, so it is stored before
        // anything else and any token cached against a previous pairing is dropped.
        if (!deviceSecret.isNullOrBlank()) {
            deviceState.setDeviceSecret(deviceSecret)
            ApiClient.clearToken()
        }
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
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN)
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

        // How long to keep watching for the browser half to bind this screen. Generous
        // because it is a person signing into Google on a TV remote, which is slow.
        private const val BROWSER_SIGN_IN_TIMEOUT_MS = 10 * 60_000L
        private const val PAIR_CODE_REFRESH_MS = 4 * 60_000L
    }
}

