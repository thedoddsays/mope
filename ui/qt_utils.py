"""
ui/qt_utils.py — Small cross-thread helper for Mope's Qt UI.

Background work (library scanning, MusicBrainz lookups, art fetching) runs
on plain Python threading.Thread instances, not Qt-managed threads. Calling
QTimer.singleShot() or touching widgets directly from those threads is not
safe — Qt objects must be driven from a thread with a running Qt event loop.

invoke_later() is the Qt equivalent of GLib.idle_add(): it's safe to call
from any thread, and always runs the given callable on the main/GUI thread
on the next event-loop iteration.
"""

from PySide6.QtCore import QObject, Signal, Qt


class _MainThreadInvoker(QObject):
    _invoke = Signal(object)

    def __init__(self):
        super().__init__()
        # Qt auto-detects that emitter/receiver may be on different threads
        # and queues the call onto the thread this object was created in
        # (the main thread, since the module-level instance below is created
        # at import time, before any worker threads exist).
        self._invoke.connect(self._run, Qt.ConnectionType.QueuedConnection)

    def _run(self, fn):
        fn()

    def call(self, fn):
        self._invoke.emit(fn)


_invoker = _MainThreadInvoker()


def invoke_later(fn):
    """Schedule fn to run on the main thread. Safe to call from any thread."""
    _invoker.call(fn)
