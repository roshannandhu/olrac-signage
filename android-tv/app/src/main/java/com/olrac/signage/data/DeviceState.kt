package com.olrac.signage.data

import android.content.Context
import android.provider.Settings
import java.util.UUID

class DeviceState(context: Context) {
    private val appContext = context.applicationContext
    private val preferences = context.applicationContext.getSharedPreferences(
        PREFERENCES_NAME,
        Context.MODE_PRIVATE
    )

    val deviceId: String
        get() {
            preferences.getString(KEY_DEVICE_ID, null)?.let { return it }

            val generatedId = UUID.randomUUID().toString()
            preferences.edit().putString(KEY_DEVICE_ID, generatedId).commit()
            return generatedId
        }

    /**
     * An identity that survives reinstalling the app.
     *
     * [deviceId] lives in SharedPreferences, so clearing app data or reinstalling wipes it
     * and the TV comes back looking like a brand new screen — which left a duplicate ghost
     * in the fleet and consumed another slot of the plan's screen quota. ANDROID_ID is
     * stable for the life of the OS install, so the server can recognise the returning TV
     * and reclaim its existing screen.
     *
     * Falls back to the random id when ANDROID_ID is unavailable, which is no worse than
     * the previous behaviour.
     */
    @Suppress("HardwareIds")
    val installationId: String
        get() {
            val androidId = try {
                Settings.Secure.getString(appContext.contentResolver, Settings.Secure.ANDROID_ID)
            } catch (_: Exception) {
                null
            }
            return androidId?.takeIf { it.isNotBlank() && it != "9774d56d682e549c" } ?: deviceId
        }

    val isPaired: Boolean
        get() = preferences.getBoolean(KEY_IS_PAIRED, false)

    val screenName: String?
        get() = preferences.getString(KEY_SCREEN_NAME, null)

    val apiBaseUrlOverride: String?
        get() = preferences.getString(KEY_API_BASE_URL, null)

    /**
     * Gate for the on-TV maintenance screen, issued per screen by the server and refreshed
     * on every sync.
     *
     * Cached locally on purpose: that screen exists to repair a wrong server address, so it
     * has to open when the server cannot be reached. [DEFAULT_MAINTENANCE_PIN] covers a TV
     * that has never completed a sync, which is a device holding no configuration worth
     * protecting yet.
     */
    val maintenancePin: String
        get() = preferences.getString(KEY_MAINTENANCE_PIN, null) ?: DEFAULT_MAINTENANCE_PIN

    fun setMaintenancePin(pin: String) {
        preferences.edit().putString(KEY_MAINTENANCE_PIN, pin).commit()
    }

    fun markPaired(screenName: String?) {
        preferences.edit()
            .putBoolean(KEY_IS_PAIRED, true)
            .apply {
                if (!screenName.isNullOrBlank()) {
                    putString(KEY_SCREEN_NAME, screenName)
                }
            }
            // Pairing is tiny, critical state: persist it before reporting success.
            .commit()
    }

    fun setApiBaseUrlOverride(baseUrl: String) {
        preferences.edit().putString(KEY_API_BASE_URL, baseUrl).commit()
    }

    companion object {
        const val PREFERENCES_NAME = "signage_prefs"
        const val KEY_DEVICE_ID = "device_id"
        const val KEY_IS_PAIRED = "is_paired"
        const val KEY_SCREEN_NAME = "screen_name"
        const val KEY_API_BASE_URL = "api_base_url"
        const val KEY_MAINTENANCE_PIN = "maintenance_pin"
        const val DEFAULT_SCREEN_NAME = "OLRAC Screen"
        // Applies only before the first successful sync; the server's per-screen pin
        // replaces it and every paired screen gets a distinct one.
        const val DEFAULT_MAINTENANCE_PIN = "0000"
    }
}

sealed interface LaunchState {
    data object CheckingLocalState : LaunchState
    data class Playing(val screenName: String? = null) : LaunchState

    /**
     * Default route for an unprovisioned device: the installer signs in with their own
     * OLRAC account and the screen joins that workspace directly. No second person at a
     * dashboard, and no five-minute code to race.
     */
    data class SignIn(
        val error: String? = null,
        val busy: Boolean = false,
        // Defaults false so the button stays hidden until the server says otherwise. A
        // deployment with no Google credentials can only answer /google/start with a 503,
        // and offering a button whose single outcome is an error is worse than not
        // offering it. Shown optimistically would invert that on every offline start-up.
        val googleEnabled: Boolean = false
    ) : LaunchState

    /**
     * Waiting for the installer to approve on their phone.
     *
     * The code shown here is Google's, not ours: on a TV the supported Google flow is the
     * device authorisation grant, so a code still appears. What it removes is typing a
     * password with a D-pad, and needing somebody already signed in at a dashboard.
     */
    data class GoogleSignIn(
        val userCode: String,
        val verificationUrl: String,
        val error: String? = null
    ) : LaunchState

    /** Fallback for when no keyboard is to hand. Reached from a link on [SignIn]. */
    data class Pairing(
        val pairCode: String? = null,
        val connectionMessage: String? = null
    ) : LaunchState
}

data class RegistrationSnapshot(
    val status: String,
    val pairCode: String?,
    val screenName: String?
)

object LaunchStateResolver {
    fun resolveLocal(
        isPaired: Boolean,
        hasLocalPlaylist: Boolean
    ): LaunchState = if (isPaired || hasLocalPlaylist) {
        LaunchState.Playing()
    } else {
        // Sign-in is the default for an unclaimed device; the pairing code is opt-in from
        // there, so a boot no longer mints a code nobody is looking at.
        LaunchState.SignIn()
    }

    suspend fun refresh(
        currentState: LaunchState,
        register: suspend () -> RegistrationSnapshot
    ): LaunchState {
        return try {
            val registration = register()
            when {
                currentState is LaunchState.Playing -> LaunchState.Playing(registration.screenName)
                registration.status != WAITING_PAIRING -> LaunchState.Playing(registration.screenName)
                else -> LaunchState.Pairing(pairCode = registration.pairCode)
            }
        } catch (_: Exception) {
            if (currentState is LaunchState.Playing) {
                currentState
            } else {
                LaunchState.Pairing(
                    connectionMessage = "No connection. Pairing will resume automatically."
                )
            }
        }
    }

    const val WAITING_PAIRING = "waiting_pairing"
}
