package com.olrac.signage.service

/**
 * How to treat a server response to a batch of play events.
 *
 * Play events are billing evidence and the server keeps no copy, so "the upload failed" must
 * never be answered by deleting them. The one case that genuinely cannot be retried is a
 * batch the server will refuse forever -- and the old code answered that by dropping the
 * whole batch, destroying up to BATCH_SIZE good events because of one bad row. Callers
 * narrow the batch down instead and drop only the single event actually refused.
 */
object PlayLogUploadPolicy {
    /** 4xx codes that are worth retrying rather than a verdict on the payload. */
    private val RETRYABLE = setOf(401, 403, 408, 429)

    fun isPermanentRejection(code: Int): Boolean = code in 400..499 && code !in RETRYABLE

    /** Events to send next after a permanent rejection of [batchSize]; 1 means "isolated". */
    fun narrowedBatchSize(batchSize: Int): Int = maxOf(1, batchSize / 2)
}
