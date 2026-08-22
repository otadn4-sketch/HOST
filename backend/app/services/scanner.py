from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScanResult:
    clean: bool
    signature: str = ""
    error: str = ""
    skipped: bool = False


class ClamAVError(Exception):
    pass


def _read_response(sock: socket.socket) -> str:
    chunks: list[bytes] = []
    while True:
        data = sock.recv(4096)
        if not data:
            break
        chunks.append(data)
        if b"\x00" in data or data.endswith(b"\n"):
            break
    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def ping(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"nPING\n")
            return "PONG" in _read_response(sock).upper()
    except OSError:
        return False


def scan_file(path: Path, host: str, port: int, timeout: float = 120.0) -> ScanResult:
    chunk_size = 1024 * 1024
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"nINSTREAM\n")
            with path.open("rb") as fh:
                while True:
                    chunk = fh.read(chunk_size)
                    if not chunk:
                        break
                    sock.sendall(struct.pack(">I", len(chunk)) + chunk)
            sock.sendall(struct.pack(">I", 0))
            response = _read_response(sock)
    except OSError as exc:
        raise ClamAVError(str(exc)) from exc

    upper = response.upper()
    if "FOUND" in upper:
        sig = response.split(":", 1)[-1].replace("FOUND", "").strip()
        return ScanResult(clean=False, signature=sig or "malware")
    if "ERROR" in upper:
        raise ClamAVError(response)
    if "OK" in upper or "stream:" in response.lower():
        return ScanResult(clean=True)
    raise ClamAVError(response or "empty clamav response")
