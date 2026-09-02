#!/usr/bin/env python3
"""Run the self-contained v6 per-layer Golden bit-exact gate on hardware."""

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
PROVISION_TCL = RELEASE_DIR / "provisioning" / "provision_golden.tcl"

PASS_RE = re.compile(
    r"LAYER_GOLDEN_PASS,id=(\d+),name=([^,]+),values=(\d+),mismatches=0"
)
FAIL_RE = re.compile(
    r"LAYER_GOLDEN_FAIL,id=(\d+),name=([^,]+),values=(\d+),mismatches=(\d+)"
)


def stream_output(proc: subprocess.Popen[str], lines: list[str]) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        lines.append(line)
        print(f"[v6 XSCT] {line}", end="", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    if not XSCT.is_file():
        raise RuntimeError(f"XSCT not found: {XSCT}")
    if not PROVISION_TCL.is_file():
        raise RuntimeError(f"provisioning script not found: {PROVISION_TCL}")

    log_dir = SCRIPT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    uart_data = bytearray()
    xsct_lines: list[str] = []

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
            if (
                b"MODEL_GOLDEN_GATE: PASS" in uart_data
                or b"MODEL_GOLDEN_GATE: FAIL" in uart_data
            ):
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

    uart_text = uart_data.decode("utf-8", errors="replace")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uart_path = log_dir / f"{stamp}_v6_release_golden_uart.log"
    xsct_path = log_dir / f"{stamp}_v6_release_golden_xsct.log"
    summary_path = log_dir / f"{stamp}_v6_release_golden_summary.json"
    uart_path.write_text(uart_text, encoding="utf-8", newline="\n")
    xsct_path.write_text("".join(xsct_lines), encoding="utf-8", newline="\n")

    passes = [
        {"id": int(m.group(1)), "name": m.group(2), "values": int(m.group(3))}
        for m in PASS_RE.finditer(uart_text)
    ]
    failure = FAIL_RE.search(uart_text)
    result = {
        "release": "ASM_NPU_Audio_v6",
        "xsct_returncode": xsct_rc,
        "elapsed_s": round(time.monotonic() - start, 3),
        "passed_layers": passes,
        "failed_layer": (
            {
                "id": int(failure.group(1)),
                "name": failure.group(2),
                "values": int(failure.group(3)),
                "mismatches": int(failure.group(4)),
            }
            if failure
            else None
        ),
        "golden_gate_pass": "MODEL_GOLDEN_GATE: PASS" in uart_text,
        "golden_gate_fail": "MODEL_GOLDEN_GATE: FAIL" in uart_text,
    }
    summary_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    expected_ids = list(range(12))
    actual_ids = [entry["id"] for entry in passes]
    ok = (
        xsct_rc == 0
        and actual_ids == expected_ids
        and result["golden_gate_pass"]
        and not result["golden_gate_fail"]
        and result["failed_layer"] is None
    )
    print("GOLDEN_RESULT," + json.dumps(result, ensure_ascii=False))
    print(f"GOLDEN_SUMMARY_JSON={summary_path}")
    print("V6_RELEASE_GOLDEN_PASS" if ok else "V6_RELEASE_GOLDEN_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
