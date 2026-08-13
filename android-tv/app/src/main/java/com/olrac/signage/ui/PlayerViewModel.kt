package com.olrac.signage.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.olrac.signage.data.AppDatabase
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

    private fun activeItems(items: List<PlaylistItemEntity>) =
        items.filter { it.localPath != null && ScheduleEvaluator.isActive(it) }
}
