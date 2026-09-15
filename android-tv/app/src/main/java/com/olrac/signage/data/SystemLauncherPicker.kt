package com.olrac.signage.data

/**
 * Which app to hand the screen to when an operator exits the player.
 *
 * "Go home" is not enough: on a kiosked device this player IS the home app, so the HOME intent
 * just reopens it. The exit has to name another launcher explicitly -- and not just any app that
 * answers HOME. The KONKA 2K D5STV lists TV Settings, the setup wizard and a Realtek system
 * service as home apps alongside Google TV's real launcher, and landing an operator in the setup
 * wizard is not an exit.
 */
object SystemLauncherPicker {
    /** A candidate HOME activity: its package and activity class. */
    data class Candidate(val packageName: String, val className: String)

    private val NOT_A_LAUNCHER = listOf("settings", "setup", "systemservice", "packageinstaller")

    fun pick(candidates: List<Candidate>, ownPackage: String): Candidate? {
        val others = candidates.filter { it.packageName != ownPackage }
        return others.firstOrNull { candidate -> NOT_A_LAUNCHER.none { candidate.packageName.contains(it) } }
            ?: others.firstOrNull()
    }
}
