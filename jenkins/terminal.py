#!/usr/bin/env python3
"""Unified terminal abstraction for QEMU and board serial sessions."""

from __future__ import annotations

import os
import re
import select
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Pattern, Sequence, Union

import serial


PatternLike = Union[str, Pattern[str]]


class TerminalError(RuntimeError):
    """Raised when terminal operations fail."""


@dataclass
class _ReadResult:
    data: str
    matched: Optional[str]


class BaseTerminal:
    """Common read/write interface for process and serial terminals."""

    def write(self, data: str) -> None:
        raise NotImplementedError

    def write_line(self, data: str) -> None:
        self.write(f"{data}\n")

    def write_ctrl(self, key: str) -> None:
        if len(key) != 1 or not key.isalpha():
            raise TerminalError(f"unsupported ctrl key: {key!r}")
        ctrl_code = chr(ord(key.lower()) - 96)
        self.write(ctrl_code)

    def read_until(
        self,
        patterns: Sequence[PatternLike],
        timeout: float,
    ) -> str:
        deadline = time.monotonic() + timeout
        buffer = ""
        compiled = [re.compile(p) if isinstance(p, str) else p for p in patterns]

        while time.monotonic() < deadline:
            chunk = self._read_chunk(timeout=0.2)
            if chunk:
                buffer += chunk
                matched = self._match_patterns(compiled, buffer)
                if matched:
                    return buffer

        raise TerminalError(
            f"timeout waiting for patterns: {[p.pattern for p in compiled]}"
        )

    def read_available(self, timeout: float = 0.2) -> str:
        return self._read_chunk(timeout=timeout) or ""

    def close(self) -> None:
        raise NotImplementedError

    def _read_chunk(self, timeout: float) -> Optional[str]:
        raise NotImplementedError

    @staticmethod
    def _match_patterns(patterns: Sequence[Pattern[str]], text: str) -> Optional[str]:
        for p in patterns:
            if p.search(text):
                return p.pattern
        return None


class QemuTerminal(BaseTerminal):
    """Terminal backend for spawned local process (e.g., make run)."""

    def __init__(self, command: Sequence[str], cwd: Optional[str] = None) -> None:
        self._proc = subprocess.Popen(
            list(command),
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            bufsize=0,
        )
        if self._proc.stdin is None or self._proc.stdout is None:
            raise TerminalError("failed to start process terminal")

    def write(self, data: str) -> None:
        if self._proc.stdin is None:
            raise TerminalError("stdin not available")
        self._proc.stdin.write(data.encode("utf-8", errors="ignore"))
        self._proc.stdin.flush()

    def _read_chunk(self, timeout: float) -> Optional[str]:
        if self._proc.stdout is None:
            return None
        fd = self._proc.stdout.fileno()
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        data = os.read(fd, 4096)
        if not data:
            return None
        return data.decode("utf-8", errors="ignore")

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=5)


class SerialTerminal(BaseTerminal):
    """Terminal backend for physical serial device."""

    def __init__(self, port: str, baudrate: int, timeout: float = 0.1) -> None:
        self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

    def write(self, data: str) -> None:
        self._ser.write(data.encode("utf-8", errors="ignore"))
        self._ser.flush()

    def _read_chunk(self, timeout: float) -> Optional[str]:
        self._ser.timeout = timeout
        data = self._ser.read(4096)
        if not data:
            return None
        return data.decode("utf-8", errors="ignore")

    def close(self) -> None:
        if self._ser.is_open:
            self._ser.close()


class UniversalTerminal:
    """Facade exposing a unified RW interface for QEMU and board."""

    def __init__(self, backend: BaseTerminal, log_file: Optional[str] = None) -> None:
        self._backend = backend
        self._log_file = log_file

    @classmethod
    def for_qemu(
        cls,
        command: Sequence[str],
        cwd: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> "UniversalTerminal":
        return cls(QemuTerminal(command=command, cwd=cwd), log_file=log_file)

    @classmethod
    def for_board(
        cls,
        port: str,
        baudrate: int,
        log_file: Optional[str] = None,
    ) -> "UniversalTerminal":
        return cls(SerialTerminal(port=port, baudrate=baudrate), log_file=log_file)

    def write(self, data: str) -> None:
        self._backend.write(data)
        self._log(f">>> {data}")

    def write_line(self, data: str) -> None:
        self._backend.write_line(data)
        self._log(f">>> {data}\\n")

    def write_ctrl(self, key: str) -> None:
        self._backend.write_ctrl(key)
        self._log(f">>> <CTRL-{key.upper()}>")

    def read_until(self, patterns: Sequence[PatternLike], timeout: float) -> str:
        out = self._backend.read_until(patterns=patterns, timeout=timeout)
        self._log(out)
        return out

    def read_available(self, timeout: float = 0.2) -> str:
        out = self._backend.read_available(timeout=timeout)
        if out:
            self._log(out)
        return out

    def close(self) -> None:
        self._backend.close()

    def _log(self, text: str) -> None:
        if not self._log_file:
            return
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(text)
