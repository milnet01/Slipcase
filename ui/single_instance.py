"""Keep one copy of the app running at a time (SLIP-0049).

Two copies each held a full in-memory copy of the settings, and whichever
saved last overwrote the other -- credentials entered in one were lost when
the other closed. Rather than merging settings between copies, a second
launch hands over to the running copy and exits.

A QLockFile decides who runs. It records the owner's pid, so a lock left
behind by a crash is recognised as stale and taken over. A QLocalServer
beside it lets a second launch ask the running copy to show its window.
STANDARDS.md § 7 says where each lives on each operating system.
"""

import hashlib
import logging
import os
import sys
from collections.abc import Callable

from PyQt6.QtCore import QLockFile, QStandardPaths
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from core.config import config_dir

_log = logging.getLogger(__name__)

_ACTIVATE = b"activate\n"
_CONNECT_MS = 1000


def default_runtime_dir() -> str:
    """The per-user runtime directory, or the config directory without one.

    Windows and macOS always take the config directory: Qt reports a
    general-purpose folder as the runtime directory there (the home folder
    on Windows), and a lock file does not belong loose in one (SLIP-0019).
    """
    path = ""
    if sys.platform not in ("win32", "darwin"):
        path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.RuntimeLocation
        )
    if not path:
        path = str(config_dir())
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


class SingleInstance:
    """The lock and the wake-up socket for one copy of the app."""

    def __init__(self, runtime_dir: str | None = None):
        directory = runtime_dir or default_runtime_dir()
        self._lock = QLockFile(os.path.join(directory, "slipcase.lock"))
        if sys.platform == "win32":
            # A named pipe, not a file: its name is shared by the whole
            # machine and cannot be a path. The digest of the lock directory
            # keeps two users' pipes apart (STANDARDS.md § 7).
            where = os.path.normcase(os.path.abspath(directory))
            digest = hashlib.sha256(where.encode("utf-8")).hexdigest()[:16]
            self._socket_path = f"slipcase-{digest}"
        else:
            self._socket_path = os.path.join(directory, "slipcase.sock")
        self._server: QLocalServer | None = None
        self._on_activate: Callable[[], None] | None = None

    def acquire(self, on_activate: Callable[[], None] | None = None) -> bool:
        """Become the running copy. False if another copy already is.

        `on_activate` is called when a later launch asks this copy to show
        itself.
        """
        if not self._lock.tryLock(0):
            return False
        self._on_activate = on_activate
        # Holding the lock means no live copy owns the socket; a file left
        # there by a crash would make listen() fail.
        QLocalServer.removeServer(self._socket_path)
        self._server = QLocalServer()
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(self._socket_path):
            # Still the only copy -- the lock says so -- but a second launch
            # cannot bring this window forward.
            _log.warning("cannot listen on %s: %s",
                         self._socket_path, self._server.errorString())
        return True

    def activate_running(self) -> bool:
        """Ask the running copy to show its window. False if it did not answer."""
        socket = QLocalSocket()
        socket.connectToServer(self._socket_path)
        if not socket.waitForConnected(_CONNECT_MS):
            return False
        socket.write(_ACTIVATE)
        sent = socket.waitForBytesWritten(_CONNECT_MS)
        socket.disconnectFromServer()
        return sent

    def release(self) -> None:
        """Give up the lock and close the socket."""
        if self._server is not None:
            self._server.close()
            self._server = None
        if self._lock.isLocked():
            self._lock.unlock()

    def _on_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            conn = self._server.nextPendingConnection()
            conn.readyRead.connect(lambda c=conn: self._on_message(c))
            conn.disconnected.connect(conn.deleteLater)

    def _on_message(self, conn: QLocalSocket) -> None:
        if bytes(conn.readAll()).startswith(_ACTIVATE.strip()) and self._on_activate:
            self._on_activate()
