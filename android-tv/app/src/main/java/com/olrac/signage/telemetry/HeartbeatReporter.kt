package com.olrac.signage.telemetry

import android.content.Context
import android.os.Environment
import android.os.StatFs
import com.olrac.signage.BuildConfig
import com.olrac.signage.network.ApiClient
import com.olrac.signage.network.HeartbeatRequest
import java.util.Locale

object HeartbeatReporter {
    suspend fun send(context: Context, suppliedSnapshot: PlaybackSnapshot? = null): Boolean {
        val appContext = context.applicationContext
        val preferences = appContext.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
        val deviceId = preferences.getString("device_id", null) ?: return false
        val snapshot = suppliedSnapshot ?: PlaybackTelemetry(appContext).snapshot()

        val stat = StatFs(Environment.getDataDirectory().path)
        val bytesTotal = stat.blockSizeLong * stat.blockCountLong
        val bytesAvailable = stat.blockSizeLong * stat.availableBlocksLong
        val usedGb = (bytesTotal - bytesAvailable) / (1024.0 * 1024.0 * 1024.0)
        val totalGb = bytesTotal / (1024.0 * 1024.0 * 1024.0)

        val tSent = System.currentTimeMillis()
        val updateStatus = preferences.getString("update_status", null)
        val caps = DeviceCapabilities.get(appContext)
        val response = ApiClient.service(appContext).heartbeat(
            HeartbeatRequest(
                device_id = deviceId,
                device_version = BuildConfig.VERSION_NAME,
                storage_used = String.format(Locale.US, "%.1f GB / %.1f GB", usedGb, totalGb),
                playback_state = snapshot.state,
                current_item_id = snapshot.currentItemId,
                last_error = snapshot.lastError,
                app_version = BuildConfig.VERSION_NAME,
                version_code = BuildConfig.VERSION_CODE,
                update_status = updateStatus,
                screen_width = caps.screen_width,
                screen_height = caps.screen_height,
                refresh_rate = caps.refresh_rate,
                orientation = caps.orientation,
                total_ram_mb = caps.total_ram_mb,
                available_ram_mb = caps.available_ram_mb,
                total_storage_mb = caps.total_storage_mb,
                free_storage_mb = caps.free_storage_mb,
                supported_video_codecs = caps.supported_video_codecs,
                max_decode_width = caps.max_decode_width,
                max_decode_height = caps.max_decode_height,
                manufacturer = caps.manufacturer,
                model = caps.model,
                android_version = caps.android_version,
                sdk_int = caps.sdk_int,
                network_type = caps.network_type,
                timezone = caps.timezone
            )
        )
        
        val rtt = System.currentTimeMillis() - tSent
        if (response.isSuccessful) {
            response.body()?.let { body ->
                val edit = preferences.edit()
                body.server_time_ms?.let { serverTime ->
                    val offset = serverTime - (tSent + rtt / 2)
                    edit.putLong("server_time_offset_ms", offset)
                }
                body.screen_id?.let { edit.putInt("screen_id", it) }
                body.organization_id?.let { edit.putInt("organization_id", it) }
                edit.apply()
            }
        }
        
        return response.isSuccessful
    }
}
