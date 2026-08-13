package com.olrac.signage.network

import android.content.Context
import android.util.Log
import com.olrac.signage.data.DeviceState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class RealtimeClient(
    private val context: Context,
    private val onMessage: (JSONObject) -> Unit
) {
    private val client = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .build()
        
    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(Dispatchers.IO + Job())
    private var isConnected = false
    private var attempt = 0

    private companion object {
        const val KEY_DEVICE_TOKEN = "device_token"
        val RECONNECT_BACKOFF_MS = longArrayOf(5_000, 15_000, 30_000, 60_000, 120_000)
    }

    fun start() {
        connect()
    }

    private fun connect() {
        val deviceState = DeviceState(context)
        val deviceId = deviceState.deviceId
        if (deviceId == null) {
            scope.launch {
                delay(5000)
                connect()
            }
            return
        }

        val baseUrl = ApiClient.effectiveBaseUrl(context).trimEnd('/')
        // Route is /api/ws/{device_id}/ws — the trailing /ws is part of the path. Omitting
        // it 404s, which surfaces as a close and an endless 5-second reconnect loop on
        // every screen in the fleet rather than an obvious error.
        val wsUrl = buildString {
            append(baseUrl.replace("http://", "ws://").replace("https://", "wss://"))
            append("/api/ws/")
            append(deviceId)
            append("/ws")
            // Enrolled devices (P3) carry a secret server-side and must present a device
            // JWT; legacy paired devices have no secret and the server accepts them
            // without one. Send the token whenever we have it.
            deviceToken()?.let { append("?token=").append(it) }
        }

        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("RealtimeClient", "Connected to WS")
                isConnected = true
                attempt = 0
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    Log.d("RealtimeClient", "Received WS: $text")
                    onMessage(JSONObject(text))
                } catch (e: Exception) {
                    Log.e("RealtimeClient", "Error parsing WS message", e)
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("RealtimeClient", "WS closed: $reason")
                isConnected = false
                reconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("RealtimeClient", "WS failure", t)
                isConnected = false
                reconnect()
            }
        })
    }

    private fun deviceToken(): String? =
        context.getSharedPreferences(DeviceState.PREFERENCES_NAME, Context.MODE_PRIVATE)
            .getString(KEY_DEVICE_TOKEN, null)
            ?.takeIf { it.isNotBlank() }

    private fun reconnect() {
        // Backoff, capped. A flat 5s retry means a fleet of 500 screens hammers the
        // server twice a minute each while it is down, which is exactly when it can
        // least afford it. Push is optional anyway — polling still delivers.
        val delayMs = RECONNECT_BACKOFF_MS[
            attempt.coerceIn(0, RECONNECT_BACKOFF_MS.size - 1)
        ]
        attempt++
        scope.launch {
            delay(delayMs)
            if (!isConnected) {
                connect()
            }
        }
    }

    fun stop() {
        webSocket?.close(1000, "Stopping")
        webSocket = null
        isConnected = false
    }
}
