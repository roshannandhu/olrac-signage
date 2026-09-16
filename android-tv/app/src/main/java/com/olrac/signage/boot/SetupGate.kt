package com.olrac.signage.boot

/**
 * The device switches a TV needs before the player can hold its screen unattended, and the
 * rules the setup gate follows while they are still off.
 *
 * Kept free of Android types so the ordering and focus rules below can be tested on the JVM.
 * Reading the switches themselves is the caller's job -- see [WatchdogStatus] and
 * `Settings.canDrawOverlays`.
 */
enum class SetupRequirement {
    /** SYSTEM_ALERT_WINDOW: what lets the player pull itself to the front after boot. */
    OVERLAY,

    /** The watchdog accessibility service: what puts the player back if something covers it. */
    WATCHDOG
}

data class SetupRequirementState(
    val requirement: SetupRequirement,
    val granted: Boolean
)

object SetupGate {

    /** The order the gate lists them in: the one that gets a TV playing at all comes first. */
    val ORDER = listOf(SetupRequirement.OVERLAY, SetupRequirement.WATCHDOG)

    /** The gate closes itself -- and never asks again -- only once every switch is on. */
    fun isSatisfied(states: List<SetupRequirementState>): Boolean =
        states.isNotEmpty() && states.all { it.granted }

    /**
     * Which row the remote should land on when the gate opens: the first switch still off,
     * because that is the one the installer has to act on.
     *
     * Falls back to the first row rather than "none" when everything is already granted. A
     * gate in that state is closing anyway, and returning an index that addresses no row is
     * how a screen ends up with nothing focused -- which is exactly the state that leaves a
     * D-pad remote with nowhere to go.
     */
    fun initialFocusIndex(states: List<SetupRequirementState>): Int =
        states.indexOfFirst { !it.granted }.takeIf { it >= 0 } ?: 0
}
