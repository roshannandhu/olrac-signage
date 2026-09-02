package com.olrac.signage.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.olrac.signage.data.AppDatabase
import com.olrac.signage.data.DeviceState
import com.olrac.signage.data.OperatingHours
import com.olrac.signage.data.PlaylistItemEntity
import com.olrac.signage.data.ScheduleEvaluator
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class PlayerViewModel(application: Application) : AndroidViewModel(application) {
    private val dao = AppDatabase.getDatabase(application).playlistDao()

    private val _playlist = MutableStateFlow<List<PlaylistItemEntity>>(emptyList())
    val playlist: StateFlow<List<PlaylistItemEntity>> = _playlist

    init {
        viewModelScope.launch {
            dao.observeAllItems().collectLatest { items ->
                _playlist.value = activeItems(items)
            }
        }
        viewModelScope.launch {
            while (true) {
                delay(30_000)
                loadPlaylist()
            }
        }
    }

    fun reloadPlaylist() {
        viewModelScope.launch {
            loadPlaylist()
        }
    }

    private suspend fun loadPlaylist() {
        val items = dao.getAllItems()
        _playlist.value = activeItems(items)
    }

    /**
     * What may play right now: nothing at all outside the screen's opening hours,
     * otherwise the items whose own booking window is open.
     *
     * Two levels, deliberately. OperatingHours is a property of the venue -- a shop that
     * closes at 21:00 goes dark whatever is in the loop. ScheduleEvaluator is a property
     * of the booking -- whether this particular advert has been paid to run today.
     *
     * The screen-level check is new: the backend has always sent operating_mode and
     * operating_hours, but SyncResponse had no field for them, so a screen set to "never"
     * kept playing and the Hours dialog's promise that it would go black was untrue. The
     * existing 30-second reload below is what makes a window boundary take effect without
     * waiting for a sync.
     */
    private fun activeItems(items: List<PlaylistItemEntity>): List<PlaylistItemEntity> {
        val state = DeviceState(getApplication())
        if (OperatingHours.isOff(state.operatingMode, state.operatingHours)) return emptyList()
        return items.filter { it.localPath != null && ScheduleEvaluator.isActive(it) }
    }
}
