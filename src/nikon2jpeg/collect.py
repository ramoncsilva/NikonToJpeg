"""Merge several context-menu launches into one batch.

Explorer starts one process per selected file. The first process becomes the leader (it owns a
loopback listener); the others hand their paths to it and exit, so only one window shows.
"""

from __future__ import annotations

import socket
import sys
import time

PORT = 47831
WINDOW = 0.8  # seconds without a new follower before the leader starts working
ATTEMPTS = 5


def _listener(port: int) -> socket.socket | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform == "win32":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        s.bind(("127.0.0.1", port))
        s.listen()
    except OSError:
        s.close()
        return None
    return s


def _send(port: int, paths: list[str]) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as c:
            c.sendall(("\n".join(paths) + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def collect(paths: list[str], port: int = PORT, window: float = WINDOW) -> list[str] | None:
    """Return every path gathered if this process is the leader, or None if it handed off."""
    for _ in range(ATTEMPTS):
        listener = _listener(port)
        if listener is not None:
            break
        if _send(port, paths):
            return None
        time.sleep(0.2)  # a leader may have just closed; try to take over
    else:
        return paths  # could not coordinate; just work alone

    gathered = list(paths)
    listener.settimeout(window)
    try:
        while True:
            try:
                conn, _ = listener.accept()
            except TimeoutError:
                break
            with conn:
                conn.settimeout(2)
                data = b""
                try:
                    while chunk := conn.recv(65536):
                        data += chunk
                except OSError:
                    pass
            gathered += [p for p in data.decode("utf-8", "replace").splitlines() if p]
    finally:
        listener.close()
    return gathered
