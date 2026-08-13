package com.olrac.signage.telemetry

import android.app.Activity
import android.graphics.Bitmap
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.PixelCopy
import com.olrac.signage.data.DeviceState
import com.olrac.signage.network.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream
import java.lang.ref.WeakReference

object ScreenshotManager {
    private var activityRef: WeakReference<Activity>? = null
    private val scope = CoroutineScope(Dispatchers.IO + Job())

    fun registerActivity(activity: Activity) {
        activityRef = WeakReference(activity)
    }

    fun requestScreenshot() {
        val activity = activityRef?.get() ?: return
        val window = activity.window ?: return

        val bitmap = Bitmap.createBitmap(
            window.decorView.width,
            window.decorView.height,
            Bitmap.Config.ARGB_8888
        )

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            PixelCopy.request(window, bitmap, { copyResult ->
                if (copyResult == PixelCopy.SUCCESS) {
                    uploadScreenshot(activity, bitmap)
                } else {
                    Log.e("ScreenshotManager", "PixelCopy failed: $copyResult")
                }
            }, Handler(Looper.getMainLooper()))
        }
    }

    private fun uploadScreenshot(activity: Activity, bitmap: Bitmap) {
        scope.launch {
            try {
                val file = File(activity.cacheDir, "screenshot.jpg")
                FileOutputStream(file).use { out ->
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 80, out)
                }

                val deviceState = DeviceState(activity)
                val deviceId = deviceState.deviceId ?: return@launch
                
                val requestFile = file.asRequestBody("image/jpeg".toMediaType())
                val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

                val response = ApiClient.service(activity).uploadScreenshot(deviceId, body)
                if (response.isSuccessful) {
                    Log.d("ScreenshotManager", "Screenshot uploaded successfully")
                } else {
                    Log.e("ScreenshotManager", "Upload failed: ${response.code()}")
                }
            } catch (e: Exception) {
                Log.e("ScreenshotManager", "Upload error", e)
            } finally {
                bitmap.recycle()
            }
        }
    }
}
