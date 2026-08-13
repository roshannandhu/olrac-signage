package com.olrac.signage.data

enum class TransitionType(val wireName: String) {
    NONE("none"),
    FADE("fade"),
    SLIDE_LEFT("slide_left"),
    SLIDE_RIGHT("slide_right"),
    SLIDE_UP("slide_up"),
    SLIDE_DOWN("slide_down"),
    ZOOM("zoom");

    companion object {
        fun fromWire(value: String?): TransitionType? = entries.firstOrNull { it.wireName == value }
    }
}

data class TransitionSpec(
    val type: TransitionType,
    val durationMs: Int
)

object TransitionSpecResolver {
    const val DEFAULT_DURATION_MS = 600
    const val MIN_DURATION_MS = 100
    const val MAX_DURATION_MS = 3_000

    fun resolve(
        itemTransition: String?,
        itemDurationMs: Int?,
        playlistTransition: String?,
        playlistDurationMs: Int?
    ): TransitionSpec {
        val type = TransitionType.fromWire(itemTransition)
            ?: TransitionType.fromWire(playlistTransition)
            ?: TransitionType.FADE
        val duration = (itemDurationMs ?: playlistDurationMs ?: DEFAULT_DURATION_MS)
            .coerceIn(MIN_DURATION_MS, MAX_DURATION_MS)
        return TransitionSpec(type = type, durationMs = duration)
    }

    fun resolve(item: PlaylistItemEntity): TransitionSpec = resolve(
        itemTransition = item.transition,
        itemDurationMs = item.transitionMs,
        playlistTransition = item.playlistDefaultTransition,
        playlistDurationMs = item.playlistDefaultTransitionMs
    )
}
