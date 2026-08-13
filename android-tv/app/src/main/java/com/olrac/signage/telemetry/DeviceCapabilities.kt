package com.olrac.signage.telemetry

import android.app.ActivityManager
import android.content.Context
import android.media.MediaCodecList
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.StatFs
import android.util.DisplayMetrics
import android.view.WindowManager
import org.json.JSONArray
import org.json.JSONObject
import java.util.TimeZone

data class DeviceCapabilities(
    val screen_width: Int,
    val screen_height: Int,
    val refresh_rate: Float,
    val orientation: Int,
    val total_ram_mb: Int,
    val available_ram_mb: Int,
    val total_storage_mb: Int,
    val free_storage_mb: Int,
    val supported_video_codecs: List<String>,
    val max_decode_width: Int,
    val max_decode_height: Int,
    val manufacturer: String,
    val model: String,
    val android_version: String,
    val sdk_int: Int,
    val network_type: String,
    val timezone: String
) {
    companion object {
        fun get(context: Context): DeviceCapabilities {
            val prefs = context.getSharedPreferences("signage_prefs", Context.MODE_PRIVATE)
            val cached = prefs.getString("device_capabilities", null)
            val lastVersion = prefs.getInt("capabilities_version_code", -1)
            val currentVersion = com.olrac.signage.BuildConfig.VERSION_CODE
            
            if (cached != null && lastVersion == currentVersion) {
                try {
                    val json = JSONObject(cached)
                    val codecsArray = json.optJSONArray("supported_video_codecs")
                    val codecs = mutableListOf<String>()
                    if (codecsArray != null) {
                        for (i in 0 until codecsArray.length()) {
                            codecs.add(codecsArray.getString(i))
                        }
                    }
                    return DeviceCapabilities(
                        screen_width = json.getInt("screen_width"),
                        screen_height = json.getInt("screen_height"),
                        refresh_rate = json.getDouble("refresh_rate").toFloat(),
                        orientation = json.getInt("orientation"),
                        total_ram_mb = json.getInt("total_ram_mb"),
                        available_ram_mb = json.getInt("available_ram_mb"),
                        total_storage_mb = json.getInt("total_storage_mb"),
                        free_storage_mb = json.getInt("free_storage_mb"),
                        supported_video_codecs = codecs,
                        max_decode_width = json.getInt("max_decode_width"),
                        max_decode_height = json.getInt("max_decode_height"),
                        manufacturer = json.getString("manufacturer"),
                        model = json.getString("model"),
                        android_version = json.getString("android_version"),
                        sdk_int = json.getInt("sdk_int"),
                        network_type = json.getString("network_type"),
                        timezone = json.getString("timezone")
                    )
                } catch (e: Exception) {
                    // Ignore, compute again
                }
            }

            val cap = compute(context)
            
            try {
                val json = JSONObject()
                json.put("screen_width", cap.screen_width)
                json.put("screen_height", cap.screen_height)
                json.put("refresh_rate", cap.refresh_rate.toDouble())
                json.put("orientation", cap.orientation)
                json.put("total_ram_mb", cap.total_ram_mb)
                json.put("available_ram_mb", cap.available_ram_mb)
                json.put("total_storage_mb", cap.total_storage_mb)
                json.put("free_storage_mb", cap.free_storage_mb)
                json.put("supported_video_codecs", JSONArray(cap.supported_video_codecs))
                json.put("max_decode_width", cap.max_decode_width)
                json.put("max_decode_height", cap.max_decode_height)
                json.put("manufacturer", cap.manufacturer)
                json.put("model", cap.model)
                json.put("android_version", cap.android_version)
                json.put("sdk_int", cap.sdk_int)
                json.put("network_type", cap.network_type)
                json.put("timezone", cap.timezone)
                
                prefs.edit()
                    .putString("device_capabilities", json.toString())
                    .putInt("capabilities_version_code", currentVersion)
                    .apply()
            } catch (e: Exception) {
                // Ignore
            }
            
            return cap
        }

        private fun compute(context: Context): DeviceCapabilities {
            val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val display = wm.defaultDisplay
            val metrics = DisplayMetrics()
            display.getRealMetrics(metrics)
            val screenWidth = metrics.widthPixels
            val screenHeight = metrics.heightPixels
            val refreshRate = display.refreshRate
            val orientation = if (screenWidth > screenHeight) 0 else 90

            val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val memInfo = ActivityManager.MemoryInfo()
            am.getMemoryInfo(memInfo)
            val totalRamMb = (memInfo.totalMem / (1024 * 1024)).toInt()
            val availableRamMb = (memInfo.availMem / (1024 * 1024)).toInt()

            val stat = StatFs(context.filesDir.path)
            val bytesTotal = stat.blockSizeLong * stat.blockCountLong
            val bytesAvailable = stat.blockSizeLong * stat.availableBlocksLong
            val totalStorageMb = (bytesTotal / (1024 * 1024)).toInt()
            val freeStorageMb = (bytesAvailable / (1024 * 1024)).toInt()

            val codecList = MediaCodecList(MediaCodecList.REGULAR_CODECS)
            val codecs = mutableSetOf<String>()
            var maxDecodeWidth = 0
            var maxDecodeHeight = 0

            for (info in codecList.codecInfos) {
                if (info.isEncoder) continue
                for (type in info.supportedTypes) {
                    codecs.add(type)
                    if (type.equals("video/avc", ignoreCase = true)) {
                        try {
                            val caps = info.getCapabilitiesForType(type)
                            val videoCaps = caps.videoCapabilities
                            if (videoCaps != null) {
                                maxDecodeWidth = maxOf(maxDecodeWidth, videoCaps.supportedWidths.upper)
                                maxDecodeHeight = maxOf(maxDecodeHeight, videoCaps.supportedHeights.upper)
                            }
                        } catch (e: Exception) {
                            // Ignore
                        }
                    }
                }
            }

            val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val network = connectivityManager.activeNetwork
            val netCaps = connectivityManager.getNetworkCapabilities(network)
            var networkType = "unknown"
            if (netCaps != null) {
                if (netCaps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                    networkType = "wifi"
                } else if (netCaps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) {
                    networkType = "ethernet"
                } else if (netCaps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
                    networkType = "cellular"
                } else {
                    networkType = "other"
                }
            }

            return DeviceCapabilities(
                screen_width = screenWidth,
                screen_height = screenHeight,
                refresh_rate = refreshRate,
                orientation = orientation,
                total_ram_mb = totalRamMb,
                available_ram_mb = availableRamMb,
                total_storage_mb = totalStorageMb,
                free_storage_mb = freeStorageMb,
                supported_video_codecs = codecs.toList(),
                max_decode_width = maxDecodeWidth,
                max_decode_height = maxDecodeHeight,
                manufacturer = Build.MANUFACTURER ?: "Unknown",
                model = Build.MODEL ?: "Unknown",
                android_version = Build.VERSION.RELEASE ?: "Unknown",
                sdk_int = Build.VERSION.SDK_INT,
                network_type = networkType,
                timezone = TimeZone.getDefault().id
            )
        }
    }
}
