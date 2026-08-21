package com.olrac.signage.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class RegisterRequest(val device_id: String)
data class ScreenResponse(
    val pair_code: String? = null,
    val status: String,
    val name: String? = null
)

/** Credentials typed on the TV. Held in memory for the duration of the call only. */
data class SignInRequest(
    val username: String,
    val password: String,
    val device_id: String,
    val name: String?
)

data class EnrollRequest(
    val device_id: String,
    val enrollment_token: String,
    /** Survives reinstall, so the server reclaims this TV's screen instead of duplicating it. */
    val installation_id: String? = null
)

data class EnrollResponse(
    val device_id: String,
    val device_secret: String,
    val organization_id: Int,
    val screen_id: Int
)

data class HeartbeatRequest(
    val device_id: String,
    val device_version: String?,
    val storage_used: String?,
    val playback_state: String? = null,
    val current_item_id: Int? = null,
    val last_error: String? = null,
    val app_version: String? = null,
    val version_code: Int? = null,
    val update_status: String? = null,
    val screen_width: Int? = null,
    val screen_height: Int? = null,
    val refresh_rate: Float? = null,
    val orientation: Int? = null,
    val total_ram_mb: Int? = null,
    val available_ram_mb: Int? = null,
    val total_storage_mb: Int? = null,
    val free_storage_mb: Int? = null,
    val supported_video_codecs: List<String>? = null,
    val max_decode_width: Int? = null,
    val max_decode_height: Int? = null,
    val manufacturer: String? = null,
    val model: String? = null,
    val android_version: String? = null,
    val sdk_int: Int? = null,
    val network_type: String? = null,
    val timezone: String? = null
)

data class SyncResponse(
    val playlist: PlaylistDto?,
    val playlist_updated_at: String?,
    val status: String?,
    val app_version: AppVersionDto?,
    val sync_interval_seconds: Int?
,
    val fit_mode: String? = null,
    val maintenance_pin: String? = null
)

data class AppVersionDto(
    val version_code: Int,
    val version_name: String,
    val apk_url: String?,
    val sha256: String?,
    val mandatory: Boolean
)

data class PlaylistDto(
    val id: Int,
    val name: String,
    val default_transition: String?,
    val default_transition_ms: Int?,
    val items: List<PlaylistItemDto>
)

data class PlaylistItemDto(
    val id: Int,
    val content: ContentDto,
    val duration: Int,
    val order: Int,
    val start_at: String?,
    val end_at: String?,
    val transition: String?,
    val transition_ms: Int?,
    val rotation: Int? = null,
    val schedule: ScheduleDto?
)

data class ScheduleDto(
    val days_of_week: List<Int>,
    val start_time: String?,
    val end_time: String?
)

data class ContentDto(
    val id: Int,
    val type: String,
    val file_url: String,
    val name: String,
    val sha256: String? = null,
    val file_size_bytes: Long? = 0L
)

data class HeartbeatResponse(
    val status: String,
    val screen_status: String?,
    val server_time_ms: Long?,
    val screen_id: Int?,
    val organization_id: Int?
)

interface ApiService {
    @POST("api/screens/register")
    suspend fun register(@Body request: RegisterRequest): Response<ScreenResponse>

    @POST("api/screens/sign-in")
    suspend fun signIn(@Body request: SignInRequest): Response<ScreenResponse>

    @POST("api/screens/enroll")
    suspend fun enroll(@Body request: EnrollRequest): Response<EnrollResponse>

    @POST("api/screens/heartbeat")
    suspend fun heartbeat(@Body request: HeartbeatRequest): Response<HeartbeatResponse>

    @GET("api/screens/{device_id}/sync")
    suspend fun sync(
        @Path("device_id") deviceId: String,
        @Query("since") since: String? = null
    ): Response<SyncResponse>

    // Proof of play. Must live on this interface: Retrofit's proxy only implements the
    // interface it was created from, so calling it through any other one throws.
    @POST("api/screens/play-logs/batch")
    suspend fun uploadPlayLogs(
        @Body request: com.olrac.signage.service.PlayLogBatchRequest
    ): Response<Unit>

    @retrofit2.http.Multipart
    @POST("api/screenshots/device/{device_id}/screenshot")
    suspend fun uploadScreenshot(
        @Path("device_id") deviceId: String,
        @retrofit2.http.Part file: okhttp3.MultipartBody.Part
    ): Response<Void>
}
