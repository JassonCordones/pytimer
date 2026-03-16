# timer_overlay.py
import sys, json, os, time, signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QDialog, QFormLayout, QSpinBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QPoint, QMetaType
from PySide6.QtGui import QFont, QIcon, QPixmap


CFG = "timer_config.json"
DEFAULT = {
    "duration": 300,
    "unit": "seconds",   # or "minutes"
    "green": 0.6,
    "yellow": 0.3
}

def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

# ---------------- Config ----------------
def load_cfg():
    return json.load(open(CFG)) if os.path.exists(CFG) else DEFAULT.copy()

def save_cfg(cfg):
    json.dump(cfg, open(CFG, "w"), indent=2)



class ConfigDialog(QDialog):
    def _sync_limits(self):
            # yellow can never exceed green
            self.y_spinbox.setMaximum(self.g.value())

            # optional: auto-clamp if user reduces green below yellow
            if self.y_spinbox.value() > self.g.value():
                self.y_spinbox.setValue(self.g.value())

    def __init__(self, cfg) -> None:
        super().__init__()
        
        self.setWindowTitle("Settings")
        self.cfg = cfg

        logo = QLabel()
        pixmap = QPixmap(resource_path("logo.png"))
        logo.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value = QSpinBox(); self.value.setRange(1, 9999)
        self.value.setValue(cfg["duration"])

        self.unit = QComboBox()
        self.unit.addItems(["seconds", "minutes"])
        self.unit.setCurrentText(cfg["unit"])

        self.g: QSpinBox = QSpinBox(); self.g.setRange(1, 99)
        self.g.setValue(int(cfg["green"] * 100))

        self.y_spinbox: QSpinBox = QSpinBox(); self.y_spinbox.setRange(1, 99)
        self.y_spinbox.setValue(int(cfg["yellow"] * 100))

        self.g.valueChanged.connect(self._sync_limits)
        self.y_spinbox.valueChanged.connect(self._sync_limits)
        
        self._sync_limits()

        form = QFormLayout()
        form.addRow("Duration", self.value)
        form.addRow("Unit", self.unit)
        form.addRow("Green ≥ %", self.g)
        form.addRow("Yellow ≥ %", self.y_spinbox)

        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        form.addWidget(save)

        shortcuts = QLabel(
            "<b>Shortcuts:</b><br>"
            "Space bar - Start/Pause<br>"
            "R - Reset<br>"
            "<span><br><br></span>"
            "Created by JassonCordones"
        )

        shortcuts.setAlignment(Qt.AlignmentFlag.AlignLeft)
        shortcuts.setStyleSheet("padding:8px;border-radius:4px;")

        right_layout = QVBoxLayout()
        right_layout.addWidget(shortcuts)
        right_layout.addWidget(logo)
        
        main_layout = QHBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addLayout(right_layout)

# ---------------- Overlay ----------------
class Overlay(QWidget):
    def __init__(self):
        super().__init__()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.cfg = load_cfg()
        self.running = False
        self.remaining = self.total_seconds()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Consolas", 42, QFont.Weight.Bold))

        self.units_label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.units_label.setFont(QFont("Consolas", 12, QFont.Weight.Normal))

        btn = lambda t, f: (b := QPushButton(t), b.clicked.connect(f), b)[0]
        self.start_btn = btn("Start", self.start)
        self.pause_btn = btn("Pause", self.pause)
        self.stop_btn = btn("Stop", self.stop)
        self.cfg_btn = btn("⚙", self.open_cfg)
        self.close_btn = btn("✕", self.close)
        button_style = "border-radius:5px;max-width:45px;"
        self.start_btn.setStyleSheet(button_style)
        self.pause_btn.setStyleSheet(button_style)
        self.stop_btn.setStyleSheet(button_style)
        self.cfg_btn.setStyleSheet(button_style)
        self.close_btn.setStyleSheet("background-color:#c1c1c1;color:#e74c3c;border-radius:5px;max-width:45px;")

        bar = QHBoxLayout()
        bar.setContentsMargins(0,0,0,0)
        for b in (self.start_btn, self.pause_btn, self.stop_btn, self.cfg_btn, self.close_btn):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
            # if self.remaining <= 0:
            #     self.remaining = 0
            #     self.running = False
        self.update_ui()

    # -------- UI --------
    def update_ui(self):
        r = int(self.remaining)
        total = self.total_seconds()
        ratio = max(0, r) / total if total else 0

        sign = "-" if r < 0 else ""
        abs_r = abs(r)

        minutes = abs_r // 60
        seconds = abs_r % 60

        
        if r < 0:
            color = "#8e44ad"   # purple for overtime
        elif ratio >= self.cfg["green"]:
            color = "#2ecc71"
        elif ratio >= self.cfg["yellow"]:
            color = "#f1c40f"
        else:
            color = "#e74c3c"

        self.label.setText(f"{sign}{minutes:02}:{seconds:02}")
        self.units_label.setText(self.cfg["unit"])
        self.setStyleSheet(f"background:{color}; border-radius:10px;")

    # -------- Dragging --------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()
            self.setFocus()

    def mouseMoveEvent(self, e) -> None:
        if self.drag_pos:
            delta = e.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, _):
        self.drag_pos = None

    # -------- Keyboard --------
    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Space:
            self.pause() if self.running else self.start()
        elif e.key() == Qt.Key.Key_R:
            self.stop()
       

    # -------- Config --------
    def open_cfg(self) -> None:
        dlg = ConfigDialog(self.cfg)
        dlg.resize(250,150)
        dlg.move(self.pos() + QPoint(-200,0))
        if dlg.exec():
            green = dlg.g.value()
            yellow = min(dlg.y_spinbox.value(), green)
            self.cfg.update({
                "duration": dlg.value.value(),
                "unit": dlg.unit.currentText(),
                "green": green / 100,
                "yellow": yellow / 100,
            })
            save_cfg(self.cfg)
            self.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()


# ---------------- Main ----------------
app = QApplication(sys.argv)
app.setWindowIcon(QIcon(resource_path("timer.ico")))
w = Overlay()
w.resize(260, 140)
w.show()
def handle_sigint(signum, frame):
    app.quit()

signal.signal(signal.SIGINT, handle_sigint)
sys.exit(app.exec())
