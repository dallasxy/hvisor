#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import socket
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from ci_config import get_bid_entry, load_ci
from terminal import Terminal


CaseFunc = Callable[[dict[str, Any], Terminal | None], int]


def wait_qemu_socket(path: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if Path(path).exists():
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                sock.connect(path)
                sock.close()
                return
            except OSError:
                pass
        time.sleep(0.2)
    raise SystemExit(f"qemu socket not ready: {path}")


def terminate_managed_process(cfg: dict[str, Any]) -> None:
    proc = cfg.get("_managed_proc")
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_and_print(term: Terminal, command: str) -> str:
    output = term.send_until_get(command)
    if output:
        print(output, end="", flush=True)
    return output


def send_and_read_for(term: Terminal, command: str, duration: float = 3.0) -> str:
    term.send(command)
    output = term.read_for(duration=duration)
    if output:
        print(output, end="", flush=True)
    return output


def zone0_start(cfg: dict[str, Any], term: Terminal | None) -> int:
    print("————————————————\ncase: zone0_start\n————————————————\n", flush=True)
    if cfg["mode"] == "qemu":
        cmd = ["make", f"ARCH={cfg['arch']}", f"BOARD={cfg['board']}", "ci-run"]
        proc = subprocess.Popen(cmd, cwd=cfg["workspace"], start_new_session=True)
        cfg["_managed_proc"] = proc
        cfg["_managed_proc_name"] = "qemu ci-run"
        wait_qemu_socket(cfg["socket_path"], timeout=30.0)
        with build_terminal(cfg) as qemu_term:
            boot_output = qemu_term.read_for(duration=3.0)
            if boot_output:
                print(boot_output, end="", flush=True)
            bid = cfg["bid"]
            if bid == "aarch64/qemu-gicv3":
                qemu_term.send("bootm 0x40400000 - 0x40000000")
                output = qemu_term.read_for(duration=8.0)
                if output:
                    print(output, end="", flush=True)
            # if bid == "riscv64/qemu-plic":
            #     # Ctrl+A, then input c and Enter.
            #     qemu_term.send("\x01c")
            #     output = qemu_term.read_for(duration=3.0)
            #     if output:
            #         print(output, end="", flush=True)
        return 0
    if cfg["mode"] == "board":
        # TODO: reboot board
        return 0
    return 0


def zone1_start(cfg: dict[str, Any], term: Terminal | None) -> int:
    print("————————————————\ncase: zone1_start\n————————————————\n", flush=True)
    if term is None:
        raise SystemExit("terminal backend is required")
    _ = send_and_read_for(term, "cd /root", duration=3.0)
    _ = send_and_read_for(term, "ls", duration=3.0)
    _ = send_and_read_for(term, "./boot_zone1.sh", duration=15.0)
    _ = send_and_read_for(term, "script /dev/null", duration=3.0)
    _ = send_and_read_for(term, "screen /dev/pts/0", duration=3.0)
    _ = send_and_read_for(term, "ls", duration=3.0)
    return 0


CASE_HANDLERS: dict[str, CaseFunc] = {
    "zone0_start": zone0_start,
    "zone1_start": zone1_start,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BID test cases from jenkins/ci.yaml")
    parser.add_argument("--bid", required=True, help="BID key in jenkins/ci.yaml, e.g. aarch64/qemu-gicv3")
    return parser.parse_args()


def load_runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    ci = load_ci()
    bid_entry = get_bid_entry(ci, args.bid)
    build_args = bid_entry["build_args"]
    tests = bid_entry["tests"]

    arch = build_args.get("ARCH", "").strip()
    board = build_args.get("BOARD", "").strip()
    mode = bid_entry.get("mode", "").strip()
    cases = bid_entry.get("cases", [])
    if not arch or not board or not mode:
        raise SystemExit(f"incomplete config for bid '{args.bid}': ARCH/BOARD/mode are required")
    if not cases:
        raise SystemExit(f"no test cases configured for bid '{args.bid}'")

    return {
        "bid": args.bid,
        "arch": arch,
        "board": board,
        "mode": mode,
        "cases": cases,
        "workspace": Path(__file__).resolve().parent.parent,
        "socket_path": str((Path(__file__).resolve().parent.parent / ".qemu" / "qemu.sock").resolve()),
        "serial_port": str(tests.get("serial", "/dev/null")),
        "baudrate": int(tests.get("baudrate", 1500000)),
    }


def build_terminal(cfg: dict[str, Any]) -> Terminal:
    if cfg["mode"] == "qemu":
        return Terminal.from_qemu_socket(path=cfg["socket_path"])
    return Terminal.from_serial(port=cfg["serial_port"], baudrate=cfg["baudrate"])


def main() -> int:
    args = parse_args()
    cfg = load_runtime_config(args)
    try:
        for case_name in cfg["cases"]:
            case_fn = CASE_HANDLERS.get(case_name)
            if case_fn is None:
                available = ", ".join(sorted(CASE_HANDLERS.keys()))
                raise SystemExit(f"unknown case '{case_name}', available: {available}")

            if case_name == "zone0_start":
                rc = case_fn(cfg, None)
                if rc != 0:
                    return rc
                time.sleep(5.0)
                continue
            
            with build_terminal(cfg) as term:
                rc = case_fn(cfg, term)
                if rc != 0:
                    return rc
                time.sleep(5.0)
        return 0
    finally:
        terminate_managed_process(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
