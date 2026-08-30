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

            val androidId = try {
                Settings.Secure.getString(appContext.contentResolver, Settings.Secure.ANDROID_ID)
            } catch (_: Exception) {
                null
            }

            val stableId = if (!androidId.isNullOrBlank() && androidId != "9774d56d682e549c") {
                UUID.nameUUIDFromBytes("olrac_screen_${androidId}".toByteArray()).toString()
            } else {
                UUID.randomUUID().toString()
            }

            preferences.edit().putString(KEY_DEVICE_ID, stableId).commit()
            return stableId
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
        get() = hardwareSerial()?.let { "sn_${it}" } ?: androidId()?.let { "hw_${it}" } ?: deviceId

    /**
     * Which of the identity sources actually answered, reported to the server so an
     * operator can tell WHY a screen did or did not come back as itself.
     *
     * "serial" survives a factory reset. "android_id" survives a reinstall but not a reset.
     * "random" survives nothing -- a screen on that tier will duplicate if it is ever wiped,
     * and the fleet list is where that has to be visible rather than a surprise later.
     */
    val identitySource: String
        get() = when {
            hardwareSerial() != null -> "serial"
            androidId() != null -> "android_id"
            else -> "random"
        }

    private fun androidId(): String? {
        val value = try {
            Settings.Secure.getString(appContext.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (_: Exception) {
            null
        }
        // That literal is a well-known broken value shipped on a batch of devices; treating
        // it as real would collapse every one of them onto a single identity.
        return value?.takeIf { it.isNotBlank() && it != "9774d56d682e549c" }
    }

    /**
     * The hardware serial, tried FIRST because it is the only identifier here that survives
     * a factory reset.
     *
     * The previous ordering had ANDROID_ID first and this as a fallback "for factory
     * resets" -- which never fired, because a reset does not make ANDROID_ID unavailable,
     * it gives it a NEW value. The first branch always won and the panel came back as a
     * brand new screen: a duplicate row, another slot off the quota, and its playlist and
     * play history stranded on a screen that no longer exists.
     *
     * Availability, which decides whether a reset is recoverable at all:
     *   API 26-28  READ_PHONE_STATE is enough (declared in the manifest).
     *   API 29+    restricted to device-owner and privileged apps. This player IS the
     *              device owner on a zero-touch provisioned panel, which is the deployment
     *              this matters for; a sideloaded install on Android 10+ gets a
     *              SecurityException and falls through to ANDROID_ID.
     *
     * Deliberately does NOT mix in Build.MODEL. Every panel in an estate is usually the
     * same model, so it adds no uniqueness -- and including it means a firmware update that
     * edits the model string silently changes the identity of the whole fleet at once.
     */
    private fun hardwareSerial(): String? = try {
        @Suppress("DEPRECATION")
        val raw = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            android.os.Build.getSerial()
        } else {
            android.os.Build.SERIAL
        }
        raw?.takeIf {
            it.isNotBlank() && !it.equals(android.os.Build.UNKNOWN, ignoreCase = true)
        }
    } catch (_: Exception) {
        // SecurityException on API 29+ without device-owner privilege is the normal path
        // on a sideloaded install, not an error worth surfacing.
        null
    }

    val deviceModel: String
        get() = android.os.Build.MODEL ?: "Android TV"

    val manufacturer: String
        get() = android.os.Build.MANUFACTURER ?: "Android"

    val hardwareName: String
        get() {
            val m = manufacturer.trim()
            val mod = deviceModel.trim()
            return if (mod.startsWith(m, ignoreCase = true)) mod else "$m $mod"
        }

    val isPaired: Boolean
        get() = preferences.getBoolean(KEY_IS_PAIRED, false)

    val screenName: String?
        get() = preferences.getString(KEY_SCREEN_NAME, null) ?: hardwareName

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

    /**
     * This screen's own credential, issued once by the route that bound it.
     *
     * Null on a screen paired by an older build of the app; the server still accepts those
     * while ALLOW_LEGACY_DEVICE_AUTH is on, and they pick a secret up the next time they
     * are paired or signed in.
     */
    val deviceSecret: String?
        get() = preferences.getString(KEY_DEVICE_SECRET, null)

    fun setDeviceSecret(secret: String) {
        // commit, not apply: this is the credential the screen needs to come back after a
        // power cut, and losing it to an unflushed write means a manual re-pair on site.
        preferences.edit().putString(KEY_DEVICE_SECRET, secret).commit()
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

    fun clearPairing() {
        preferences.edit()
            .putBoolean(KEY_IS_PAIRED, false)
            .remove(KEY_SCREEN_NAME)
            .remove(KEY_MAINTENANCE_PIN)
            .remove(KEY_DEVICE_SECRET)
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
        const val KEY_DEVICE_SECRET = "device_secret"
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
