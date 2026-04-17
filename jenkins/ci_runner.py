#!/usr/bin/env python3
"""Unified CI runner for QEMU and board tests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import serial
import yaml

from terminal import TerminalError, UniversalTerminal


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified Jenkins CI runner")
    parser.add_argument("--mode", required=True, choices=["qemu", "board"])
    parser.add_argument("--test", required=True, help="Comma-separated test item names")
    parser.add_argument("--arch", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--workspace", default=str(ROOT))
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--serial-port", default="/dev/ttyUSB1")
    parser.add_argument("--serial-baudrate", type=int, default=1500000)
    parser.add_argument("--timeout", type=int, default=240)
    return parser.parse_args()


def load_profile(arch: str, board: str) -> dict:
    profile_path = ROOT / "jenkins" / "platform_profiles" / f"{arch}_{board}.yaml"
    if not profile_path.exists():
        return {}
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _run_cmd(cmd: List[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def qemu_prepare(workspace: Path, arch: str, board: str) -> None:
    external_base = os.environ.get("TEST_IMG_BASE")
    if not external_base:
        raise RuntimeError("TEST_IMG_BASE is not set")
    src = Path(external_base) / arch / board
    dst = workspace / "platform" / arch / board
    if not src.exists():
        raise RuntimeError(f"missing test image directory: {src}")
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    prepare_script = dst / "scripts" / "prepare.sh"
    _run_cmd(["chmod", "+x", str(prepare_script)], cwd=workspace)
    _run_cmd(["sudo", "-E", str(prepare_script)], cwd=workspace)


def _expect_write_read(
    term: UniversalTerminal,
    expect_patterns: List[str],
    send: str | None = None,
    timeout: float = 120.0,
) -> str:
    out = term.read_until(expect_patterns, timeout=timeout)
    if send is not None:
        term.write(send)
    return out


def step_zone0_start(term: UniversalTerminal, timeout: float) -> None:
    _expect_write_read(
        term,
        [r"char device redirected to /dev/pts.*\(label X10007000\)"],
        timeout=timeout,
    )
    term.write_ctrl("a")
    term.write("c")
    _expect_write_read(term, [r"\(qemu\)"], send="c\n", timeout=timeout)
    _expect_write_read(term, [r"job control turned off.*#"], send="\x01cbash\n", timeout=timeout)
    _expect_write_read(term, [r"root@\(none\):/# "], send="cd /root\n", timeout=timeout)


def step_zone1_start(term: UniversalTerminal, timeout: float) -> None:
    _expect_write_read(term, [r"root@\(none\):/root# "], send="./boot_zone1.sh\n", timeout=timeout)
    time.sleep(10)
    term.write("\n")
    _expect_write_read(term, [r"root@\(none\):/root# "], send="script /dev/null\n", timeout=timeout)
    _expect_write_read(term, [r"\n# "], send="screen /dev/pts/0\n", timeout=timeout)
    _expect_write_read(term, [r"\n# "], send="ls | grep home\n", timeout=timeout)
    _expect_write_read(term, [r"home"], timeout=timeout)


def step_placeholder(step_name: str) -> None:
    print(f"[{step_name}] placeholder")


def run_qemu_tests(args: argparse.Namespace, tests: List[str], workspace: Path) -> None:
    qemu_prepare(workspace, args.arch, args.board)
    cmd = ["make", "run", f"ARCH={args.arch}", f"BOARD={args.board}"]
    term = UniversalTerminal.for_qemu(command=cmd, cwd=str(workspace), log_file=args.log_file)
    step_map = {
        "zone0_start": step_zone0_start,
        "start_zone0": step_zone0_start,
        "zone1_start": step_zone1_start,
        "start_zone1": step_zone1_start,
    }
    try:
        for step in tests:
            print(f"--- Step: {step} ---")
            handler = step_map.get(step)
            if handler:
                handler(term, float(args.timeout))
            elif step in {"zone0_network", "zone1_shutdown", "zone1_restart"}:
                step_placeholder(step)
            else:
                print(f"[{step}] unknown step, skip")
    finally:
        term.close()


def run_board_tests(args: argparse.Namespace, tests: List[str]) -> None:
    profile = load_profile(args.arch, args.board)
    serial_cfg = profile.get("serial", {})
    port = args.serial_port or serial_cfg.get("port", "/dev/ttyUSB1")
    baud = args.serial_baudrate or int(serial_cfg.get("baudrate", 1500000))
    prompt = profile.get("board_prompt_regex", r"root@localhost:~#")
    login_prompt = profile.get("board_login_prompt_regex", r"ZCU102-petalinux login:")

    term = UniversalTerminal.for_board(port=port, baudrate=baud, log_file=args.log_file)
    try:
        for step in tests:
            print(f"--- Step: {step} ---")
            if step not in {"start_zone1", "zone1_start", "boot"}:
                print(f"[{step}] unknown board step, skip")
                continue
            term.write("\n")
            term.read_until([r"=>"], timeout=300)
            term.write_line(
                "pci enum;setenv serverip 192.168.122.1; setenv ipaddr 192.168.122.2; "
                "setenv loadaddr 0x60800000; setenv fdt_addr 0xa0000000; "
                "setenv zone0_kernel_addr 0x00280000; tftp ${loadaddr} ${serverip}:hvisor.bin; "
                "tftp ${fdt_addr} ${serverip}:rk3568_limit_zone0.dtb; "
                "tftp ${zone0_kernel_addr} ${serverip}:Image_test5; bootm ${loadaddr} - ${fdt_addr};"
            )
            term.read_until([prompt], timeout=1800)
            term.write_line("insmod hvisor.ko")
            term.read_until([prompt], timeout=600)
            term.write_line("./hvisor virtio start virtio.json &")
            term.read_until([prompt], timeout=600)
            term.write_line("./hvisor zone start linux2.json")
            term.read_until([prompt], timeout=600)
            term.write_line("screen /dev/pts/0")
            term.read_until([login_prompt], timeout=300)
    finally:
        term.close()


def main() -> int:
    args = parse_args()
    tests = [x.strip() for x in args.test.split(",") if x.strip()]
    if not tests:
        print("empty --test argument", file=sys.stderr)
        return 2
    workspace = Path(args.workspace).resolve()

    try:
        if args.mode == "qemu":
            run_qemu_tests(args, tests, workspace)
        else:
            run_board_tests(args, tests)
    except (TerminalError, RuntimeError, subprocess.CalledProcessError, serial.SerialException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
