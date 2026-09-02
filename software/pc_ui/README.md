# PC Monitoring UI

PySide6 UI for the v6 acoustic-security demo. It receives `RESULT` packets from the Zybo Z7-20 over PS UART1 and can also send runtime commands to the board.

## Install

```bash
pip install -r requirements.txt
```

## Run

Windows helper (default `COM4`):

```bat
run_ui.cmd
run_ui.cmd COM5
```

Portable invocation:

```bash
python main.py --port COM4 --baud 115200 --labels ../../model/metadata/class_labels_indices.csv
```

Omit `--port` to use the keyboard demo mode.

## Board commands

- `m`: start continuous microphone monitoring
- `x`: stop microphone monitoring
- `k`: knock demo
- `g`: glass-break demo
- `s`: gunshot demo
- `f`: fire-alarm demo

The UART link carries inference/event results, not audio waveform samples. The waveform graphic in the UI is decorative. Runtime CSV logs are written under `logs/` and are ignored by Git.
