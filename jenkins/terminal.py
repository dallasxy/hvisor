#!/usr/bin/env python3
"""Unified terminal helpers for QEMU UNIX socket and physical serial ports."""

from __future__ import annotations

import select
import socket
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import serial


class TerminalTimeoutError(TimeoutError):
    """Raised when send_until_get times out."""


class TerminalBackend(ABC):
    """Backend abstraction for terminal IO."""

    @abstractmethod
    def open(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def read(self, max_bytes: int = 4096) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes) -> None:
        pass


@dataclass
class QemuSocketBackend(TerminalBackend):
    path: str
    connect_timeout: float = 10.0
    io_timeout: float = 0.2
    _sock: socket.socket | None = None

    def open(self) -> None:
        if self._sock is not None:
            return
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.connect_timeout)
        sock.connect(self.path)
        sock.setblocking(False)
        self._sock = sock

    def close(self) -> None:
        if self._sock is None:
            return
        self._sock.close()
        self._sock = None

    def read(self, max_bytes: int = 4096) -> bytes:
        if self._sock is None:
            raise RuntimeError("QEMU socket is not open")
        ready, _, _ = select.select([self._sock], [], [], self.io_timeout)
        if not ready:
            return b""
        try:
            return self._sock.recv(max_bytes)
        except BlockingIOError:
            return b""

    def write(self, data: bytes) -> None:
        if self._sock is None:
            raise RuntimeError("QEMU socket is not open")
        self._sock.sendall(data)


@dataclass
class SerialBackend(TerminalBackend):
    port: str
    baudrate: int = 115200
    timeout: float = 0.2
    _serial: serial.Serial | None = None

    def open(self) -> None:
        if self._serial is not None:
            return
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.timeout,
        )

    def close(self) -> None:
        if self._serial is None:
            return
        self._serial.close()
        self._serial = None

    def read(self, max_bytes: int = 4096) -> bytes:
        if self._serial is None:
            raise RuntimeError("Serial device is not open")
        return self._serial.read(max_bytes)

    def write(self, data: bytes) -> None:
        if self._serial is None:
            raise RuntimeError("Serial device is not open")
        self._serial.write(data)
        self._serial.flush()


class Terminal:
    """High level terminal wrapper with command helpers."""

    def __init__(self, backend: TerminalBackend, encoding: str = "utf-8") -> None:
        self.backend = backend
        self.encoding = encoding
        self._opened = False

    @classmethod
    def from_qemu_socket(
        cls,
        path: str,
        connect_timeout: float = 10.0,
        io_timeout: float = 0.2,
        encoding: str = "utf-8",
    ) -> "Terminal":
        return cls(
            QemuSocketBackend(path=path, connect_timeout=connect_timeout, io_timeout=io_timeout),
            encoding=encoding,
        )

    @classmethod
    def from_serial(
        cls,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.2,
        encoding: str = "utf-8",
    ) -> "Terminal":
        return cls(SerialBackend(port=port, baudrate=baudrate, timeout=timeout), encoding=encoding)

    def open(self) -> None:
        if self._opened:
            return
        self.backend.open()
        self._opened = True

    def close(self) -> None:
        if not self._opened:
            return
        self.backend.close()
        self._opened = False

    def __enter__(self) -> "Terminal":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def send(self, command: str) -> None:
        self._ensure_open()
        payload = command.rstrip("\n") + "\n"
        self.backend.write(payload.encode(self.encoding, errors="replace"))

    def send_until_get(
        self,
        command: str,
        timeout: float = 30.0,
        poll_interval: float = 0.05,
        include_marker_line: bool = False,
    ) -> str:
        self._ensure_open()
        marker = f"__HV_TERMINAL_DONE_{uuid.uuid4().hex}__"
        self.send(f"{command}; echo {marker}")

        deadline = time.monotonic() + timeout
        buf = ""
        while time.monotonic() < deadline:
            chunk = self.backend.read()
            if chunk:
                buf += chunk.decode(self.encoding, errors="replace")
                if marker in buf:
                    if include_marker_line:
                        return buf
                    return self._trim_after_marker(buf, marker)
            time.sleep(poll_interval)
        raise TerminalTimeoutError(f"timed out waiting for terminal marker: {marker}")

    def _ensure_open(self) -> None:
        if not self._opened:
            self.open()

    @staticmethod
    def _trim_after_marker(output: str, marker: str) -> str:
        idx = output.find(marker)
        if idx < 0:
            return output
        return output[:idx]
