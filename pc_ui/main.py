#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import queue
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QHeaderView, QSizePolicy
)

try:
    import serial
except ImportError:
    serial = None


# -----------------------------------------------------------------------------
# Security / AudioSet label definitions
# -----------------------------------------------------------------------------

LEVEL_NAMES = {
    0: "정상",
    1: "활동 감지",
    2: "침입 / 파손 위험",
    3: "중대 위험",
    4: "시설 비상",
}

LEVEL_THEME = {
    0: {"bg": "#0f271c", "border": "#2f8d5a", "fg": "#62E394", "soft": "#183829"},
    1: {"bg": "#10233a", "border": "#356fa9", "fg": "#6EB4FF", "soft": "#172d47"},
    2: {"bg": "#2a1115", "border": "#8d2c33", "fg": "#FF5B61", "soft": "#381519"},
    3: {"bg": "#311016", "border": "#a52f3b", "fg": "#FF4D5A", "soft": "#42151d"},
    4: {"bg": "#36100f", "border": "#b43c32", "fg": "#FF574E", "soft": "#491714"},
}

KOREAN_LABELS = {
    0: "말소리", 8: "고함", 11: "큰 외침", 14: "비명",
    51: "달리는 소리", 52: "발을 끄는 소리", 53: "발걸음 소리",
    137: "음악", 354: "문 소리", 355: "초인종", 357: "미닫이문 소리",
    358: "문이 세게 닫히는 소리", 359: "노크 소리",
    388: "경보음", 395: "알람 시계", 396: "사이렌",
    397: "민방위 사이렌", 399: "연기 감지 경보", 400: "화재 경보",
    426: "폭발음", 427: "총성", 428: "기관총 소리", 429: "연속 총성",
    430: "포격음", 436: "굉음", 440: "금 가는 소리", 441: "유리 소리",
    443: "깨지는 소리", 460: "쿵 하는 충격음", 461: "둔탁한 충격음",
    466: "큰 충격음", 469: "충돌 / 파손음", 470: "파손음",
    478: "부서지는 소리", 480: "찢어지는 소리", 481: "전자음",
    500: "무음", 506: "실내 공간음", 513: "잡음", 514: "환경 소음",
}

FALLBACK_LABELS = {
    0: "Speech",
    53: "Walk, footsteps",
    359: "Knock",
    400: "Fire alarm",
    427: "Gunshot, gunfire",
    441: "Glass",
    443: "Shatter",
    469: "Smash, crash",
    470: "Breaking",
    506: "Inside, small room",
}

# 화면 테스트용. 실제 UART 모드에서는 사용하지 않음.
DEMO_CASES = {
    "normal": (0, -1),
    "knock": (1, 359),
    "glass": (2, 441),
    "gunshot": (3, 427),
    "fire": (4, 400),
}


def load_labels(path: str | None):
    labels = dict(FALLBACK_LABELS)
    if not path:
        return labels

    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                labels[int(row["index"])] = row["display_name"]
    except Exception:
        pass
    return labels


def label_of(labels, idx: int):
    if idx < 0:
        return "-"
    return KOREAN_LABELS.get(idx, labels.get(idx, f"AudioSet 클래스 {idx}"))


# -----------------------------------------------------------------------------
# UART protocol
#
# RESULT,<seq>,<level>,<winner_class>,<winner_prob_1e4>,
#        <activity_1e4>,<intrusion_1e4>,<critical_1e4>,<emergency_1e4>,
#        <inference_us>
#
# UI v9에서는 확률을 화면에 표시하지 않지만,
# 기존 PS/Vitis UART 프로토콜과의 호환을 위해 그대로 수신한다.
# -----------------------------------------------------------------------------

@dataclass
class ResultPacket:
    seq: int
    level: int
    cls: int
    prob: float
    activity: float
    damage: float
    critical: float
    emergency: float
    inference_us: int = 0


def parse_result(line: str):
    p = [x.strip() for x in line.split(",")]
    if len(p) != 10 or p[0] != "RESULT":
        return None

    try:
        return ResultPacket(
            seq=int(p[1]),
            level=int(p[2]),
            cls=int(p[3]),
            prob=int(p[4]) / 10000.0,
            activity=int(p[5]) / 10000.0,
            damage=int(p[6]) / 10000.0,
            critical=int(p[7]) / 10000.0,
            emergency=int(p[8]) / 10000.0,
            inference_us=int(p[9]),
        )
    except ValueError:
        return None


class SerialReader:
    def __init__(self, port, baud, out_q):
        self.port = port
        self.baud = baud
        self.out_q = out_q
        self.stop_evt = threading.Event()
        self.ser = None

    def start(self):
        if serial is None:
            self.out_q.put(("error", "pyserial이 설치되어 있지 않습니다."))
            return
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.stop_evt.set()
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass

    def _run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.25)
            self.out_q.put(("connected", self.port))

            while not self.stop_evt.is_set():
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                self.out_q.put(("line", line))

        except Exception as e:
            self.out_q.put(("error", str(e)))


# -----------------------------------------------------------------------------
# Event session manager
# -----------------------------------------------------------------------------

@dataclass
class EventSession:
    event_id: int
    first_detected: datetime
    last_detected: datetime
    level: int
    representative_cls: int
    representative_prob: float
    hits: int = 1
    end_time: datetime | None = None


class EventManager:
    """
    동일 사건의 반복 검출을 하나의 세션으로 묶는다.
    NORMAL이 end_miss_count회 연속 들어오면 세션 종료.
    """
    def __init__(self, end_miss_count=2):
        self.active: EventSession | None = None
        self.next_id = 1
        self.misses = 0
        self.end_miss_count = end_miss_count

    def process(self, p: ResultPacket, ts: datetime):
        closed = None

        if p.level > 0:
            self.misses = 0

            if self.active is None:
                self.active = EventSession(
                    event_id=self.next_id,
                    first_detected=ts,
                    last_detected=ts,
                    level=p.level,
                    representative_cls=p.cls,
                    representative_prob=p.prob,
                    hits=1,
                )
                self.next_id += 1
            else:
                ev = self.active
                ev.last_detected = ts
                ev.hits += 1

                # 세션 동안 가장 높은 심각도 유지
                if p.level > ev.level:
                    ev.level = p.level

                # UI의 대표 감지음은 세션 중 가장 높은 클래스 점수의 클래스 유지.
                # 화면에는 퍼센트를 표시하지 않는다.
                if p.prob > ev.representative_prob:
                    ev.representative_prob = p.prob
                    ev.representative_cls = p.cls

        elif self.active is not None:
            self.misses += 1

            if self.misses >= self.end_miss_count:
                self.active.end_time = ts
                closed = self.active
                self.active = None
                self.misses = 0

        return self.active, closed



# -----------------------------------------------------------------------------
# Persistent CSV logging
# -----------------------------------------------------------------------------

class CsvLogger:
    def __init__(self, log_dir=None):
        base = Path(log_dir) if log_dir else (Path(__file__).resolve().parent / "logs")
        base.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.raw_path = base / f"raw_results_{stamp}.csv"
        self.event_path = base / f"event_sessions_{stamp}.csv"

        with self.raw_path.open("w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerow([
                "pc_timestamp", "seq", "level", "level_name",
                "class_index", "sound", "winner_probability",
                "activity_score", "intrusion_damage_score",
                "critical_score", "facility_emergency_score",
                "inference_us"
            ])

        with self.event_path.open("w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerow([
                "event_id", "first_detected", "last_detected", "end_time",
                "duration_sec", "max_level", "level_name",
                "representative_class_index", "representative_sound",
                "representative_probability", "hit_count"
            ])

    def log_result(self, p, labels, ts):
        with self.raw_path.open("a", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerow([
                ts.isoformat(timespec="milliseconds"),
                p.seq,
                p.level,
                LEVEL_NAMES.get(p.level, str(p.level)),
                p.cls,
                label_of(labels, p.cls),
                f"{p.prob:.6f}",
                f"{p.activity:.6f}",
                f"{p.damage:.6f}",
                f"{p.critical:.6f}",
                f"{p.emergency:.6f}",
                p.inference_us
            ])

    def log_event(self, ev, labels):
        end = ev.end_time or ev.last_detected
        duration = max(0.0, (end - ev.first_detected).total_seconds())

        with self.event_path.open("a", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerow([
                ev.event_id,
                ev.first_detected.isoformat(timespec="milliseconds"),
                ev.last_detected.isoformat(timespec="milliseconds"),
                end.isoformat(timespec="milliseconds"),
                f"{duration:.3f}",
                ev.level,
                LEVEL_NAMES.get(ev.level, str(ev.level)),
                ev.representative_cls,
                label_of(labels, ev.representative_cls),
                f"{ev.representative_prob:.6f}",
                ev.hits
            ])

# -----------------------------------------------------------------------------
# Small visual widgets
# -----------------------------------------------------------------------------

class WaveformWidget(QWidget):
    """장식용 waveform. 실제 waveform 데이터 표시 기능은 아님."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#3C9DFF"), 3, Qt.SolidLine, Qt.RoundCap))

        h = self.height()
        w = self.width()
        center = h / 2

        shape = [
            .12, .18, .28, .35, .48, .33, .44, .30, .38, .25,
            .42, .70, .48, .93, .66, .38, .24, .36, .22, .28,
            .18, .31, .20, .34, .23, .15
        ]

        gap = w / (len(shape) + 1)
        for i, amp in enumerate(shape, 1):
            x = gap * i
            y = max(7.0, amp * h * 0.45)
            painter.drawLine(int(x), int(center - y), int(x), int(center + y))


class MetricCard(QFrame):
    def __init__(self, caption: str, value: str = "-", accent="#FF555B", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setProperty("accent", accent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(7)

        self.caption = QLabel(caption)
        self.caption.setObjectName("metricCaption")

        self.value = QLabel(value)
        self.value.setObjectName("metricValue")

        lay.addWidget(self.caption)
        lay.addWidget(self.value)
        lay.addStretch()

    def set_value(self, text: str):
        self.value.setText(text)


# -----------------------------------------------------------------------------
# Main UI
# -----------------------------------------------------------------------------

class MonitorWindow(QMainWindow):
    def __init__(self, labels, demo_mode=True, log_dir=None):
        super().__init__()

        self.labels = labels
        self.demo_mode = demo_mode
        self.event_mgr = EventManager(end_miss_count=2)
        self.logger = CsvLogger(log_dir)
        self.seq = 0

        self.setWindowTitle("FPGA NPU 기반 실시간 음향 보안 이벤트 모니터링 시스템")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)

        self._build()
        self._style()
        self.connection.setToolTip(
            f"Raw log: {self.logger.raw_path}\nEvent log: {self.logger.event_path}"
        )

        if self.demo_mode:
            self._apply_demo("glass")
            self.connection.setText("● 데모 모드")
        else:
            self.apply_result(ResultPacket(0, 0, -1, 0, 0, 0, 0, 0, 0))

        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(500)

    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(16)

        # ----- header ----------------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(16)

        self.title = QLabel("FPGA NPU 기반 실시간 음향 보안 이벤트 모니터링 시스템")
        self.title.setObjectName("title")

        self.connection = QLabel("● UART 연결 중")
        self.connection.setObjectName("connection")
        self.connection.setAlignment(Qt.AlignCenter)

        header.addWidget(self.title, 1)
        header.addWidget(self.connection)
        root.addLayout(header)

        # ----- top cards -------------------------------------------------------
        top = QGridLayout()
        top.setHorizontalSpacing(18)
        top.setVerticalSpacing(12)
        top.setColumnStretch(0, 1)
        top.setColumnStretch(1, 1)

        # Security status
        self.status_card = QFrame()
        self.status_card.setObjectName("statusCard")
        status_lay = QHBoxLayout(self.status_card)
        status_lay.setContentsMargins(28, 24, 28, 24)
        status_lay.setSpacing(22)

        self.status_icon = QLabel("!")
        self.status_icon.setObjectName("statusIcon")
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setFixedSize(92, 108)

        status_text = QVBoxLayout()
        status_text.setSpacing(7)

        status_cap = QLabel("현재 보안 상태")
        status_cap.setObjectName("cardCaption")

        self.level = QLabel("정상")
        self.level.setObjectName("statusMain")

        self.status_desc = QLabel("보안 관련 이상 이벤트가 감지되지 않았습니다.")
        self.status_desc.setObjectName("cardDesc")
        self.status_desc.setWordWrap(True)

        status_text.addStretch()
        status_text.addWidget(status_cap)
        status_text.addWidget(self.level)
        status_text.addWidget(self.status_desc)
        status_text.addStretch()

        status_lay.addWidget(self.status_icon)
        status_lay.addLayout(status_text, 1)

        # Representative sound
        self.sound_card = QFrame()
        self.sound_card.setObjectName("soundCard")
        sound_lay = QHBoxLayout(self.sound_card)
        sound_lay.setContentsMargins(30, 24, 24, 24)
        sound_lay.setSpacing(18)

        sound_text = QVBoxLayout()
        sound_text.setSpacing(8)

        sound_cap = QLabel("감지된 소리 (대표 감지 음향)")
        sound_cap.setObjectName("soundCaption")

        self.sound = QLabel("-")
        self.sound.setObjectName("soundMain")

        self.sound_desc = QLabel("LeeNet11의 527개 AudioSet 클래스 중 대표 클래스입니다.")
        self.sound_desc.setObjectName("cardDesc")
        self.sound_desc.setWordWrap(True)

        sound_text.addStretch()
        sound_text.addWidget(sound_cap)
        sound_text.addWidget(self.sound)
        sound_text.addWidget(self.sound_desc)
        sound_text.addStretch()

        self.waveform = WaveformWidget()

        sound_lay.addLayout(sound_text, 3)
        sound_lay.addWidget(self.waveform, 2)

        top.addWidget(self.status_card, 0, 0)
        top.addWidget(self.sound_card, 0, 1)
        root.addLayout(top)

        # ----- active security event ------------------------------------------
        self.event_card = QFrame()
        self.event_card.setObjectName("eventCard")
        ev_root = QVBoxLayout(self.event_card)
        ev_root.setContentsMargins(24, 20, 24, 22)
        ev_root.setSpacing(16)

        ev_head = QHBoxLayout()
        ev_head.setSpacing(10)

        ev_title = QLabel("진행 중인 보안 이벤트")
        ev_title.setObjectName("eventTitle")

        self.event_badge = QLabel("진행 중")
        self.event_badge.setObjectName("eventBadge")
        self.event_badge.setAlignment(Qt.AlignCenter)

        ev_head.addWidget(ev_title)
        ev_head.addStretch()
        ev_head.addWidget(self.event_badge)
        ev_root.addLayout(ev_head)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(14)
        metrics.setVerticalSpacing(10)

        self.m_id = MetricCard("이벤트 번호")
        self.m_first = MetricCard("최초 감지 시각")
        self.m_last = MetricCard("최종 감지 시각")
        self.m_elapsed = MetricCard("지속 시간")
        self.m_hits = MetricCard("감지 횟수")

        metrics.addWidget(self.m_id, 0, 0)
        metrics.addWidget(self.m_first, 0, 1)
        metrics.addWidget(self.m_last, 0, 2)
        metrics.addWidget(self.m_elapsed, 0, 3)
        metrics.addWidget(self.m_hits, 0, 4)

        for i in range(5):
            metrics.setColumnStretch(i, 1)

        ev_root.addLayout(metrics)
        root.addWidget(self.event_card)

        # ----- event history ---------------------------------------------------
        self.history_card = QFrame()
        self.history_card.setObjectName("historyCard")
        hist_root = QVBoxLayout(self.history_card)
        hist_root.setContentsMargins(18, 16, 18, 18)
        hist_root.setSpacing(12)

        hist_head = QHBoxLayout()

        hist_title = QLabel("이벤트 발생 기록")
        hist_title.setObjectName("historyTitle")

        self.history_count = QLabel("0건")
        self.history_count.setObjectName("historyCount")
        self.history_count.setAlignment(Qt.AlignCenter)

        hist_head.addWidget(hist_title)
        hist_head.addStretch()
        hist_head.addWidget(self.history_count)
        hist_root.addLayout(hist_head)

        self.history = QTableWidget(0, 6)
        self.history.setHorizontalHeaderLabels([
            "이벤트 번호",
            "보안 상태",
            "감지된 소리",
            "최초 감지 시각",
            "지속 시간",
            "감지 횟수",
        ])
        self.history.verticalHeader().setVisible(False)
        self.history.setShowGrid(False)
        self.history.setAlternatingRowColors(True)
        self.history.setSelectionBehavior(QTableWidget.SelectRows)
        self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history.setFocusPolicy(Qt.NoFocus)

        hh = self.history.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        hist_root.addWidget(self.history)
        root.addWidget(self.history_card, 1)

        # demo mode: 화면에는 버튼을 두지 않고 키보드로만 테스트
        # 0 정상 / 1 노크 / 2 유리 / 3 총성 / 4 화재경보
        self.setFocusPolicy(Qt.StrongFocus)

    # -------------------------------------------------------------------------
    # Style
    # -------------------------------------------------------------------------

    def _style(self):
        self.setStyleSheet("""
        QWidget#central {
            background:#071019;
            color:#edf3f8;
            font-family:"Noto Sans CJK KR","Noto Sans KR","Pretendard","DejaVu Sans",sans-serif;
        }

        QLabel {
            background:transparent;
            border:none;
        }

        QLabel#title {
            color:#f5f7fa;
            font-size:36px;
            font-weight:900;
        }

        QLabel#connection {
            color:#b9c5cf;
            background:#0b151f;
            border:1px solid #263646;
            border-radius:18px;
            padding:9px 16px;
            font-size:13px;
            font-weight:800;
        }

        QFrame#statusCard {
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,
                stop:0 #281114,
                stop:0.55 #1c1013,
                stop:1 #11151a
            );
            border:1px solid #7d282e;
            border-radius:16px;
        }

        QFrame#soundCard {
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,
                stop:0 #0c1d32,
                stop:0.65 #0a1725,
                stop:1 #0b131d
            );
            border:1px solid #2d5f91;
            border-radius:16px;
        }

        QLabel#statusIcon {
            color:#ff5a5f;
            border:4px solid #ff5a5f;
            border-radius:24px;
            font-size:50px;
            font-weight:900;
        }

        QLabel#cardCaption {
            color:#d8e0e7;
            font-size:16px;
            font-weight:800;
        }

        QLabel#soundCaption {
            color:#8fc6ff;
            font-size:17px;
            font-weight:800;
        }

        QLabel#statusMain {
            color:#ff5a5f;
            font-size:40px;
            font-weight:900;
        }

        QLabel#soundMain {
            color:#f1f6fb;
            font-size:42px;
            font-weight:900;
        }

        QLabel#cardDesc {
            color:#aab6c1;
            font-size:14px;
            font-weight:600;
        }

        QFrame#eventCard {
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,
                stop:0 #12171e,
                stop:1 #0c1118
            );
            border:1px solid #493038;
            border-radius:16px;
        }

        QLabel#eventTitle {
            color:#f0f3f6;
            font-size:23px;
            font-weight:900;
        }

        QLabel#eventBadge {
            color:#ff6268;
            background:#2b1115;
            border:1px solid #6e2228;
            border-radius:15px;
            padding:7px 16px;
            font-size:14px;
            font-weight:900;
        }

        QFrame#metricCard {
            background:#171418;
            border:1px solid #743036;
            border-radius:12px;
        }

        QLabel#metricCaption {
            color:#d7dce2;
            font-size:14px;
            font-weight:800;
        }

        QLabel#metricValue {
            color:#f0f3f7;
            font-size:28px;
            font-weight:900;
        }

        QFrame#historyCard {
            background:#0c151f;
            border:1px solid #26394c;
            border-radius:16px;
        }

        QLabel#historyTitle {
            color:#edf3f8;
            font-size:23px;
            font-weight:900;
        }

        QLabel#historyCount {
            color:#7fbaff;
            background:#0b1724;
            border:1px solid #294767;
            border-radius:14px;
            padding:6px 14px;
            font-size:13px;
            font-weight:900;
        }

        QTableWidget {
            color:#dce5ed;
            background:#0a121b;
            alternate-background-color:#0d1721;
            border:1px solid #233548;
            border-radius:9px;
            font-size:15px;
            selection-background-color:#15283a;
            selection-color:#ffffff;
        }

        QTableWidget::item {
            border-bottom:1px solid #1b2b3a;
            padding:8px 10px;
        }

        QHeaderView::section {
            color:#aebdca;
            background:#101c28;
            border:none;
            border-bottom:1px solid #25394b;
            padding:10px 9px;
            font-size:14px;
            font-weight:900;
        }
        """)

        self.history.verticalHeader().setDefaultSectionSize(54)

    # -------------------------------------------------------------------------
    # Dynamic UI updates
    # -------------------------------------------------------------------------

    def apply_result(self, p: ResultPacket):
        ts = datetime.now()
        self.logger.log_result(p, self.labels, ts)
        active, closed = self.event_mgr.process(p, ts)

        self._update_status(p.level)
        self.sound.setText(label_of(self.labels, p.cls))

        if p.cls < 0:
            self.sound_desc.setText("현재 보안 관련 대표 감지 음향이 없습니다.")
        else:
            self.sound_desc.setText(
                f"LeeNet11의 AudioSet 클래스 #{p.cls}가 대표 감지 음향으로 선택되었습니다."
            )

        self._update_active_event(active)

        if closed is not None:
            self.logger.log_event(closed, self.labels)
            self._add_history(closed)

    def _update_status(self, level: int):
        theme = LEVEL_THEME.get(level, LEVEL_THEME[0])
        level_name = LEVEL_NAMES.get(level, "알 수 없음")

        self.level.setText(level_name)

        if level == 0:
            desc = "보안 관련 이상 이벤트가 감지되지 않았습니다."
            badge = "대기 중"
        elif level == 1:
            desc = "활동 관련 음향이 감지되었습니다."
            badge = "진행 중"
        elif level == 2:
            desc = "침입 또는 파손과 관련된 음향이 감지되었습니다."
            badge = "진행 중"
        elif level == 3:
            desc = "중대 위험과 관련된 음향이 감지되었습니다."
            badge = "진행 중"
        else:
            desc = "시설 비상 상황과 관련된 음향이 감지되었습니다."
            badge = "진행 중"

        self.status_desc.setText(desc)
        self.event_badge.setText(badge)

        self.status_card.setStyleSheet(f"""
            QFrame#statusCard {{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 {theme["bg"]},
                    stop:0.60 #151116,
                    stop:1 #101419
                );
                border:1px solid {theme["border"]};
                border-radius:16px;
            }}
        """)
        self.level.setStyleSheet(
            f"color:{theme['fg']}; font-size:40px; font-weight:900;"
        )
        self.status_icon.setStyleSheet(
            f"color:{theme['fg']}; border:4px solid {theme['fg']}; "
            f"border-radius:24px; font-size:50px; font-weight:900;"
        )

        # 진행 이벤트 카드 accent도 현재 severity를 따라감
        self.event_card.setStyleSheet(f"""
            QFrame#eventCard {{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 #12171e,
                    stop:1 #0c1118
                );
                border:1px solid {theme["border"]};
                border-radius:16px;
            }}
        """)

    def _update_active_event(self, ev: EventSession | None):
        if ev is None:
            self.m_id.set_value("-")
            self.m_first.set_value("-")
            self.m_last.set_value("-")
            self.m_elapsed.set_value("-")
            self.m_hits.set_value("-")
            self.event_badge.setText("대기 중")
            return

        elapsed = max(
            0,
            int((datetime.now() - ev.first_detected).total_seconds())
        )

        self.m_id.set_value(f"#{ev.event_id:03d}")
        self.m_first.set_value(f"{ev.first_detected:%H:%M:%S}")
        self.m_last.set_value(f"{ev.last_detected:%H:%M:%S}")
        self.m_elapsed.set_value(f"{elapsed // 60:02d}:{elapsed % 60:02d}")
        self.m_hits.set_value(f"{ev.hits}회")
        self.event_badge.setText("진행 중")

    def _tick(self):
        self._update_active_event(self.event_mgr.active)

    def _add_history(self, ev: EventSession):
        row = self.history.rowCount()
        self.history.insertRow(row)

        end = ev.end_time or ev.last_detected
        duration = max(0, int((end - ev.first_detected).total_seconds()))

        values = [
            f"#{ev.event_id:03d}",
            LEVEL_NAMES.get(ev.level, str(ev.level)),
            label_of(self.labels, ev.representative_cls),
            f"{ev.first_detected:%H:%M:%S}",
            f"{duration // 60:02d}:{duration % 60:02d}",
            f"{ev.hits}회",
        ]

        for col, text in enumerate(values):
            item = QTableWidgetItem(text)

            if col != 2:
                item.setTextAlignment(Qt.AlignCenter)

            # 위험 등급 열만 severity 색상 적용
            if col == 1:
                item.setForeground(QColor(LEVEL_THEME.get(ev.level, LEVEL_THEME[0])["fg"]))
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self.history.setItem(row, col, item)

        self.history_count.setText(f"{self.history.rowCount()}건")
        self.history.scrollToBottom()

    # -------------------------------------------------------------------------
    # Demo shortcuts (UI에는 버튼 없음)
    # -------------------------------------------------------------------------

    def _apply_demo(self, name: str):
        level, cls = DEMO_CASES[name]
        self.seq += 1

        # 확률은 화면에 표시하지 않으므로 데모용 내부값만 둔다.
        fake_prob = {
            "normal": 0.0,
            "knock": 0.73,
            "glass": 0.86,
            "gunshot": 0.93,
            "fire": 0.92,
        }[name]

        p = ResultPacket(
            seq=self.seq,
            level=level,
            cls=cls,
            prob=fake_prob,
            activity=0,
            damage=0,
            critical=0,
            emergency=0,
            inference_us=183500,
        )
        self.apply_result(p)

    def keyPressEvent(self, event):
        if self.demo_mode:
            key_map = {
                Qt.Key_0: "normal",
                Qt.Key_1: "knock",
                Qt.Key_2: "glass",
                Qt.Key_3: "gunshot",
                Qt.Key_4: "fire",
            }
            demo = key_map.get(event.key())
            if demo:
                self._apply_demo(demo)
                return

        super().keyPressEvent(event)


# -----------------------------------------------------------------------------
# Controller
# -----------------------------------------------------------------------------

class Controller:
    def __init__(self, args):
        self.q = queue.Queue()
        self.labels = load_labels(args.labels)

        self.window = MonitorWindow(
            self.labels,
            demo_mode=(args.port is None),
            log_dir=args.log_dir
        )

        self.reader = None
        self.timer = None

        if args.port:
            self.reader = SerialReader(args.port, args.baud, self.q)
            self.reader.start()

            self.timer = QTimer()
            self.timer.timeout.connect(self.poll)
            self.timer.start(40)

    def poll(self):
        while True:
            try:
                kind, payload = self.q.get_nowait()
            except queue.Empty:
                break

            if kind == "connected":
                self.window.connection.setText(f"● UART 연결됨  {payload}")

            elif kind == "error":
                self.window.connection.setText("● UART 오류")
                self.window.connection.setToolTip(payload)

            elif kind == "line":
                p = parse_result(payload)
                if p is not None:
                    self.window.apply_result(p)

    def stop(self):
        if self.reader:
            self.reader.stop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None, help="예: /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--labels", default=None, help="AudioSet class_labels_indices.csv")
    ap.add_argument("--log-dir", default=None, help="CSV 로그 저장 폴더 (기본: UI 폴더/logs)")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    ctl = Controller(args)

    ctl.window.show()

    app.aboutToQuit.connect(ctl.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
