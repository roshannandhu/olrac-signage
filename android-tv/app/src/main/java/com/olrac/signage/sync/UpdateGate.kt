package com.olrac.signage.sync

/**
 * The decision half of [UpdateManager], kept free of Android types so it can be tested.
 *
 * Installing an APK is the most dangerous thing this app does: when the TV is provisioned
 * as device owner the install is silent, with no prompt and nobody standing in front of
 * the screen. Every reason to refuse therefore lives here, in one place, and the rules
 * fail closed -- anything not positively verified is rejected.
 */
object UpdateGate {

    private val HEX_64 = Regex("[0-9a-fA-F]{64}")

    /**
     * Why this update must not be installed, or null when it may proceed.
     *
     * Checked before downloading: there is no point spending a budget panel's bandwidth
     * on bytes that could never be trusted.
     */
    fun rejectionFor(apkUrl: String?, sha256: String?): String? = when {
        apkUrl.isNullOrBlank() -> "no apk url"
        // Plain HTTP lets anyone on the path substitute the file. The digest below would
        // catch a swap, but an unencrypted fleet-wide update channel is not defensible
        // on its own terms.
        !apkUrl.startsWith("https://") -> "apk url is not https"
        // The server omitted the digest, or was never given one. Before this, that case
        // skipped verification entirely and installed anyway.
        sha256.isNullOrBlank() -> "release has no sha256 digest"
        !HEX_64.matches(sha256) -> "sha256 is not a 64-character hex digest"
        else -> null
    }

    /**
     * True only when [expected] is a well-formed digest and [actual] equals it.
     *
     * A null or malformed expectation returns false rather than "skip the check", which
     * is the distinction that matters: absence of a digest is a reason to refuse, never
     * a reason to trust.
     */
    fun digestMatches(expected: String?, actual: String): Boolean {
        if (expected.isNullOrBlank() || !HEX_64.matches(expected)) return false
        return expected.equals(actual, ignoreCase = true)
    }
}
