#!/usr/bin/env python3
"""Headless smoke test for continuous MIC and four demo commands."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT / "pc_ui"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from main import BOARD_COMMAND_NAMES, MonitorWindow, ResultPacket  # noqa: E402


def main() -> None:
    app = QApplication.instance() or QApplication([])
    temp_dir = tempfile.TemporaryDirectory(prefix="asm_v6_ui_test_")
    output_dir = Path(temp_dir.name)
    window = MonitorWindow({}, demo_mode=False, log_dir=output_dir / "logs")
    sent = []
    window.set_command_handler(lambda command: sent.append(command) is None)
    window.set_uart_connected(True, "COM4")

    window.mic_button.click()
    app.processEvents()
    assert sent[-1] == "m"
    assert window.pending_command == "m"
    window.mark_command_sent("m")
    window.mark_mic_stream_started()
    assert window.mic_streaming
    assert window.mic_button.text() == "MIC 연속 정지"
    assert all(not button.isEnabled() for button in window.demo_buttons)

    window.mark_mic_window_complete(
        "WINDOW_COMPLETE,mode=MIC_STREAM,index=2,hop_sec=5"
    )
    assert window.mic_window_count == 2
    window.mic_button.click()
    app.processEvents()
    assert sent[-1] == "x"
    assert window.pending_command == "x"
    window.mark_command_sent("x")
    window.mark_mic_stream_stopped()
    assert not window.mic_streaming
    assert window.mic_button.text() == "MIC 연속 시작"

    for button, command in zip(window.demo_buttons, ("k", "g", "s", "f")):
        button.click()
        app.processEvents()
        assert sent[-1] == command
        assert window.pending_command == command
        window.mark_run_finished(True)

    assert set(BOARD_COMMAND_NAMES) == {"m", "x", "k", "g", "s", "f"}

    window.apply_result(ResultPacket(
        seq=1, level=3, cls=428, prob=0.72,
        activity=0.01, damage=0.02, critical=0.72,
        emergency=0.01, inference_us=2500000,
    ))
    assert window.event_mgr.active is not None
    assert int((window.event_mgr.active.last_detected -
                window.event_mgr.active.first_detected).total_seconds()) == 10
    assert window.history.rowCount() == 0
    window.mark_run_finished(True)
    assert window.event_mgr.active is None
    assert window.history.rowCount() == 1
    assert window.history.item(0, 4).text() == "00:10"
    assert window.m_elapsed.value.text() == "00:10"
    assert window.event_badge.text() == "감지 완료"
    assert window.level.text() == "중대 위험"
    window._tick()
    assert window.m_elapsed.value.text() == "00:10"
    assert window.event_badge.text() == "감지 완료"
    assert window.level.text() == "중대 위험"
    window.resize(1440, 900)
    window.show()
    app.processEvents()
    held_screenshot = output_dir / "pc_ui_completed_event_hold.png"
    assert window.grab().save(str(held_screenshot))
    window._clear_completed_event_display()
    assert window.m_elapsed.value.text() == "-"
    assert window.event_badge.text() == "대기 중"
    assert window.level.text() == "정상"

    app.processEvents()
    screenshot = output_dir / "pc_ui_four_demo_buttons.png"
    assert window.grab().save(str(screenshot))
    window.close()
    print(
        f"PC_UI_COMMAND_TEST_PASS commands={','.join(sent)} "
        "screenshots=tempdir"
    )
    temp_dir.cleanup()


if __name__ == "__main__":
    main()
