#!/usr/bin/env python3
"""Program the v6 release and capture one security demo inference."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import serial


SCRIPT_DIR = Path(__file__).resolve().parent
RELEASE_DIR = SCRIPT_DIR.parent
DEFAULT_XSCT = Path(r"C:\Xilinx\Vitis\2024.2\bin\xsct.bat")
XSCT = Path(os.environ.get("ASM_XSCT", str(DEFAULT_XSCT)))
PROVISION_TCL = RELEASE_DIR / "provisioning" / "provision_and_run.tcl"
COMMAND_NAMES = {
    "k": "knock",
    "g": "glass_break",
    "s": "gunshot",
    "f": "fire_alarm",
}
CONV2_RE = re.compile(
    r"CONVN_PROFILE,id=1,name=Conv2,expected_steps=(\d+),"
    r"active_pl_cycles=(\d+),cycles_per_step=([0-9.]+)"
)
CHAIN_RE = re.compile(
    r"CHAIN_RESULT:\s*(PASS|FAIL).*?operation_sum_us=([0-9.]+),"
    r"?\s+wall_us=([0-9.]+)"
)
TOP_RE = re.compile(r"#?\s*Top event\s*:\s*(.*?)\s*\(([0-9.]+)%\)")


def stream_output(proc: subprocess.Popen[str], lines: list[str]) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        lines.append(line)
        print(f"[v6 XSCT] {line}", end="", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--command", choices=tuple(COMMAND_NAMES), default="k")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    if not XSCT.is_file():
        raise RuntimeError(f"XSCT not found: {XSCT}")

    log_dir = SCRIPT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    uart_data = bytearray()
    xsct_lines: list[str] = []
    command_sent = False

    with serial.Serial(args.port, args.baud, timeout=0.1) as uart:
        uart.reset_input_buffer()
        proc = subprocess.Popen(
            [str(XSCT), str(PROVISION_TCL)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        reader = threading.Thread(
            target=stream_output, args=(proc, xsct_lines), daemon=True
        )
        reader.start()

        while time.monotonic() - start < args.timeout:
            chunk = uart.read(uart.in_waiting or 1)
            if chunk:
                uart_data.extend(chunk)
                sys.stdout.write(chunk.decode("utf-8", errors="replace"))
                sys.stdout.flush()
                if not command_sent and b"Select input mode:" in uart_data:
                    uart.write(args.command.encode("ascii"))
                    uart.flush()
                    command_sent = True
                    print(f"\nHOST_COMMAND_SENT,command={args.command}", flush=True)
            if b"RUN_COMPLETE" in uart_data or b"RUN_FAILED" in uart_data:
                time.sleep(0.25)
                trailing = uart.read(uart.in_waiting)
                if trailing:
                    uart_data.extend(trailing)
                break
            if proc.poll() not in (None, 0):
                break

        try:
            xsct_rc = proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.terminate()
            xsct_rc = proc.wait(timeout=10)
        reader.join(timeout=2)

    text = uart_data.decode("utf-8", errors="replace")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{stamp}_v6_release_{COMMAND_NAMES[args.command]}"
    uart_path = log_dir / f"{prefix}_uart.log"
    xsct_path = log_dir / f"{prefix}_xsct.log"
    summary_path = log_dir / f"{prefix}_summary.json"
    uart_path.write_text(text, encoding="utf-8", newline="\n")
    xsct_path.write_text("".join(xsct_lines), encoding="utf-8", newline="\n")

    conv2 = CONV2_RE.search(text)
    chain = CHAIN_RE.search(text)
    top = TOP_RE.search(text)
    result = {
        "release": "ASM_NPU_Audio_v6",
        "command": args.command,
        "demo": COMMAND_NAMES[args.command],
        "xsct_returncode": xsct_rc,
        "elapsed_s": round(time.monotonic() - start, 3),
        "run_complete": "RUN_COMPLETE" in text,
        "run_failed": "RUN_FAILED" in text,
        "chain_status": chain.group(1) if chain else "MISSING",
        "chain_operation_sum_us": float(chain.group(2)) if chain else None,
        "chain_wall_us": float(chain.group(3)) if chain else None,
        "conv2_expected_steps": int(conv2.group(1)) if conv2 else None,
        "conv2_active_pl_cycles": int(conv2.group(2)) if conv2 else None,
        "conv2_cycles_per_step": float(conv2.group(3)) if conv2 else None,
        "top_event": top.group(1).strip() if top else None,
        "top_probability_percent": float(top.group(2)) if top else None,
    }
    ok = (
        xsct_rc == 0
        and result["run_complete"]
        and not result["run_failed"]
        and result["chain_status"] == "PASS"
        and conv2 is not None
        and top is not None
    )
    result["pass"] = ok
    summary_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("RELEASE_DEMO_RESULT," + json.dumps(result, ensure_ascii=False))
    print(f"RELEASE_DEMO_SUMMARY_JSON={summary_path}")
    print("V6_RELEASE_DEMO_PASS" if ok else "V6_RELEASE_DEMO_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
