# timer_overlay.py
import sys, json, os, time
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QDialog, QFormLayout, QSpinBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont

CFG = "timer_config.json"
DEFAULT = {
    "duration": 300,
    "unit": "seconds",   # or "minutes"
    "green": 0.6,
    "yellow": 0.3
}

# ---------------- Config ----------------
def load_cfg():
    return json.load(open(CFG)) if os.path.exists(CFG) else DEFAULT.copy()

def save_cfg(cfg):
    json.dump(cfg, open(CFG, "w"), indent=2)

class ConfigDialog(QDialog):
    def __init__(self, cfg) -> None:
        super().__init__()
        self.setWindowTitle("Settings")
        self.cfg = cfg

        self.value = QSpinBox(); self.value.setRange(1, 9999)
        self.value.setValue(cfg["duration"])

        self.unit = QComboBox()
        self.unit.addItems(["seconds", "minutes"])
        self.unit.setCurrentText(cfg["unit"])

        self.g = QSpinBox(); self.g.setRange(1, 99)
        self.g.setValue(int(cfg["green"] * 100))

        self.y = QSpinBox(); self.y.setRange(1, 99)
        self.y.setValue(int(cfg["yellow"] * 100))

        form = QFormLayout(self)
        form.addRow("Duration", self.value)
        form.addRow("Unit", self.unit)
        form.addRow("Green ≥ %", self.g)
        form.addRow("Yellow ≥ %", self.y)

        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        form.addWidget(save)

        label = QLabel("Created by JassonCordones")
        label.setAlignment(Qt.AlignCenter)
        form.addRow(label)

# ---------------- Overlay ----------------
class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.running = False
        self.remaining = self.total_seconds()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel("", alignment=Qt.AlignCenter)
        self.label.setFont(QFont("Consolas", 42, QFont.Bold))

        btn = lambda t, f: (b := QPushButton(t), b.clicked.connect(f), b)[0]
        self.start_btn = btn("Start", self.start)
        self.pause_btn = btn("Pause", self.pause)
        self.stop_btn = btn("Stop", self.stop)
        self.cfg_btn = btn("⚙", self.open_cfg)
        self.close_btn = btn("✕", self.close)

        bar = QHBoxLayout()
        for b in (self.start_btn, self.pause_btn, self.stop_btn, self.cfg_btn, self.close_btn):
            bar.addWidget(b)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(bar)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(250)

        self.drag_pos: QPoint | None = None
        self.update_ui()

    # -------- Timer logic --------
    def total_seconds(self):
        return self.cfg["duration"] * (60 if self.cfg["unit"] == "minutes" else 1)

    def start(self):
        self.running = True
        self.last = time.time()

    def pause(self):
        self.running = False

    def stop(self):
        self.running = False
        self.remaining = self.total_seconds()
        self.update_ui()

    def tick(self):
        if self.running:
            now = time.time()
            self.remaining -= now - self.last
            self.last = now
            if self.remaining <= 0:
                self.remaining = 0
                self.running = False
        self.update_ui()

    # -------- UI --------
    def update_ui(self):
        r = max(0, int(self.remaining))
        total = self.total_seconds()
        ratio = r / total if total else 0

        if ratio >= self.cfg["green"]:
            color = "#2ecc71"
        elif ratio >= self.cfg["yellow"]:
            color = "#f1c40f"
        else:
            color = "#e74c3c"

        self.label.setText(f"{r//60:02}:{r%60:02}")
        self.setStyleSheet(f"background:{color}; border-radius:10px;")

    # -------- Dragging --------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e) -> None:
        if self.drag_pos:
            delta = e.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, _):
        self.drag_pos = None

    # -------- Keyboard --------
    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Space:
            self.pause() if self.running else self.start()
        elif e.key() == Qt.Key_R:
            self.stop()
        elif e.key() == Qt.Key_Escape:
            self.close()

    # -------- Config --------
    def open_cfg(self) -> None:
        dlg = ConfigDialog(self.cfg)
        dlg.move(self.pos() + QPoint(-200,0))
        if dlg.exec():
            self.cfg.update({
                "duration": dlg.value.value(),
                "unit": dlg.unit.currentText(),
                "green": dlg.g.value() / 100,
                "yellow": dlg.y.value() / 100,
            })
            save_cfg(self.cfg)
            self.stop()

# ---------------- Main ----------------
app = QApplication(sys.argv)
w = Overlay()
w.resize(260, 140)
w.show()
sys.exit(app.exec())
