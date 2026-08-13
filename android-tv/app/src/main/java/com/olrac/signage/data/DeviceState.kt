package com.olrac.signage.data

import android.content.Context
import java.util.UUID

class DeviceState(context: Context) {
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

    val isPaired: Boolean
        get() = preferences.getBoolean(KEY_IS_PAIRED, false)

    val screenName: String?
        get() = preferences.getString(KEY_SCREEN_NAME, null)

    val apiBaseUrlOverride: String?
        get() = preferences.getString(KEY_API_BASE_URL, null)

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
        const val DEFAULT_SCREEN_NAME = "OLRAC Screen"
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
        val busy: Boolean = false
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
