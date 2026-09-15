package com.olrac.signage.telemetry

import android.content.Context

/**
 * Keeps the last crash where a remote diagnostics report can read it.
 *
 * A TV that nobody can reach cannot hand over a logcat. If the player dies -- on a restart above
 * all, where it shows only as a TV that did not come back to the player -- this is the one
 * record of why. Chains to the existing handler so the process still crashes as normal.
 */
object CrashRecorder {
    const val PREF_LAST_CRASH = "last_crash"
    @Volatile private var installed = false

    fun install(context: Context) {
        if (installed) return
        installed = true
        val appContext = context.applicationContext
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, error ->
            runCatching {
                val frames = error.stackTrace.take(6).joinToString(" < ") { "${it.className.substringAfterLast('.')}.${it.methodName}:${it.lineNumber}" }
                val summary = "${System.currentTimeMillis()} ${thread.name} ${error.javaClass.name}: ${error.message?.take(160)} @ $frames"
                // commit, not apply: the process is about to die and apply would lose it.
                appContext.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
                    .edit().putString(PREF_LAST_CRASH, summary.take(700)).commit()
            }
            previous?.uncaughtException(thread, error)
        }
    }
}
