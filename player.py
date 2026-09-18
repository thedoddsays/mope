"""
player.py — QtMultimedia-based audio playback engine for Mope (Windows port).

Same public API as the Linux/GStreamer version's player.py, so main_window.py
and everything above it needed no changes:
  - play_file / play_pause / stop / seek
  - is_playing / get_position / get_duration / set_volume
  - on_track_end / on_error / on_position callbacks
"""

from PySide6.QtCore import QObject, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class Player(QObject):
    """Thin wrapper around QMediaPlayer + QAudioOutput."""

    def __init__(self):
        super().__init__()

        self._audio_output = QAudioOutput()
        self._media_player = QMediaPlayer()
        self._media_player.setAudioOutput(self._audio_output)

        # Callbacks the UI can register (same names/shape as the GTK version)
        self.on_track_end = None        # called with no args when playback ends
        self.on_error     = None        # called with (error_string)
        self.on_position  = None        # called with (pos_seconds, dur_seconds) ~every 500 ms

        self._media_player.mediaStatusChanged.connect(self._on_media_status)
        self._media_player.errorOccurred.connect(self._on_error_occurred)

        # Periodic position polling (500 ms), same cadence as the GStreamer version
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_position)
        self._poll_timer.start()

        self._is_playing = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play_file(self, filepath: str):
        """Load and immediately play a file."""
        url = QUrl.fromLocalFile(filepath)
        self._media_player.setSource(url)
        self._media_player.play()
        self._is_playing = True

    def play_pause(self):
        """Toggle between playing and paused."""
        if self._is_playing:
            self._media_player.pause()
            self._is_playing = False
        else:
            self._media_player.play()
            self._is_playing = True

    def stop(self):
        """Stop playback and reset position."""
        self._media_player.stop()
        self._is_playing = False

    def seek(self, seconds: float):
        """Seek to an absolute position in seconds."""
        self._media_player.setPosition(int(seconds * 1000))

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def get_position(self) -> float:
        """Return current position in seconds (0.0 if unknown)."""
        return self._media_player.position() / 1000.0

    def get_duration(self) -> float:
        """Return track duration in seconds (0.0 if unknown)."""
        return self._media_player.duration() / 1000.0

    def set_volume(self, volume: float):
        """Set volume from 0.0 (silent) to 1.0 (full)."""
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._is_playing = False
            if self.on_track_end:
                self.on_track_end()

    def _on_error_occurred(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self._is_playing = False
            if self.on_error:
                self.on_error(error_string)

    def _poll_position(self):
        if self._is_playing and self.on_position:
            self.on_position(self.get_position(), self.get_duration())
