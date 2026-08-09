"""
地面位置调节器 — 拖拽猫到想要的出生位置，保存偏移量。

使用：D:\Python\python.exe tools/adjust_floor.py
操作：拖拽猫上下移动 | Enter 保存 | Esc 取消
"""

import sys
import json
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QPixmap


BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "dyberpet" / "DyberPet" / "settings.py"
SPRITE_DIR = BASE_DIR / "dyberpet" / "res" / "role" / "六一" / "action"
CONFIG_PATH = BASE_DIR / "assets" / "configs" / "pet_conf.json"
STATBAR_H = 20


def load_offset():
    try:
        text = SETTINGS_PATH.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("floor_y_offset"):
                return int(line.split("=")[1].strip())
    except Exception:
        pass
    return 0


def save_offset(offset):
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("floor_y_offset"):
            lines[i] = f"floor_y_offset = {offset}"
            break
    SETTINGS_PATH.write_text("\n".join(lines), encoding="utf-8")


class FloorAdjuster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("拖拽猫到想要的位置，Enter 保存")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        avail = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(avail)  # 和 DyberPet 一致，不含任务栏
        self.screen_h = avail.height()

        pet_conf = json.load(open(CONFIG_PATH, encoding="utf-8"))
        self.pet_w = pet_conf.get("width", 640)
        self.pet_h = pet_conf.get("height", 360)
        self.win_h = 2 * STATBAR_H + self.pet_h  # 400

        self.cat_pixmap = QPixmap(str(SPRITE_DIR / "stand_40.png"))

        # 默认地面线 = 屏幕底部 - 窗口高度
        self.default_floor_y = self.screen_h - self.win_h

        # 读取当前 offset，换算成 floor_y
        self.offset = load_offset()
        self.floor_y = self.default_floor_y - self.offset  # 和 DyberPet 公式一致

        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_floor_y = 0

        self.setMouseTracking(True)

    def _cat_rect(self):
        x = int(self.width() * 0.8) - self.pet_w // 2
        y = self.floor_y
        return QRect(x, y, self.pet_w, self.win_h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        # 默认地面线（灰色虚线）
        p.setPen(QPen(QColor(150, 150, 150, 120), 1, Qt.DotLine))
        p.drawLine(0, self.default_floor_y, self.width(), self.default_floor_y)
        p.setFont(QFont("Microsoft YaHei", 9))
        p.setPen(QColor(150, 150, 150, 150))
        p.drawText(self.width() - 220, self.default_floor_y - 6, "默认位置")

        # 猫窗口背景
        cat_rect = self._cat_rect()
        p.setBrush(QColor(255, 255, 255, 30))
        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.drawRect(cat_rect)

        # 猫精灵图（底部对齐窗口底部）
        if not self.cat_pixmap.isNull():
            sprite_rect = QRect(
                cat_rect.x(),
                cat_rect.bottom() - self.pet_h,
                self.pet_w,
                self.pet_h,
            )
            p.drawPixmap(sprite_rect, self.cat_pixmap)

        # 当前地面线（红色）
        p.setPen(QPen(QColor(255, 80, 80, 220), 2, Qt.DashLine))
        p.drawLine(0, self.floor_y, self.width(), self.floor_y)

        # 偏移标签
        diff = self.default_floor_y - self.floor_y
        if diff > 0:
            label = f"上移 {diff}px"
        elif diff < 0:
            label = f"下移 {-diff}px"
        else:
            label = "默认位置"

        font = QFont("Microsoft YaHei", 14, QFont.Bold)
        p.setFont(font)
        fm = p.fontMetrics()
        tr = fm.boundingRect(label)
        pad = 12
        bg = QRect(
            self.width() // 2 - tr.width() // 2 - pad,
            max(0, cat_rect.top() - tr.height() - pad * 2 - 10),
            tr.width() + pad * 2,
            tr.height() + pad * 2,
        )
        p.setBrush(QColor(30, 30, 30, 200))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(bg, 8, 8)
        p.setPen(QColor(255, 255, 255))
        p.drawText(bg, Qt.AlignCenter, label)

        # 提示
        p.setFont(QFont("Microsoft YaHei", 10))
        p.setPen(QColor(200, 200, 200, 180))
        p.drawText(20, self.screen_h - 20, "拖拽猫上下移动 | Enter 保存 | Esc 取消")

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cat_rect = self._cat_rect()
            if cat_rect.contains(int(event.position().x()), int(event.position().y())):
                self.dragging = True
                self.drag_start_y = event.position().y()
                self.drag_start_floor_y = self.floor_y
                self.setCursor(Qt.SizeAllCursor)

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.position().y() - self.drag_start_y
            self.floor_y = self.drag_start_floor_y + delta
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        if event.key() == Qt.Key_Up:
            self.floor_y -= step
            self.update()
        elif event.key() == Qt.Key_Down:
            self.floor_y += step
            self.update()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            offset = self.default_floor_y - self.floor_y
            save_offset(int(offset))
            print(f"[OK] floor_y_offset = {int(offset)}  (上移{int(offset)}px)" if offset > 0
                  else f"[OK] floor_y_offset = {int(offset)}  (下移{int(-offset)}px)" if offset < 0
                  else f"[OK] floor_y_offset = 0  (默认位置)")
            self.close()
        elif event.key() == Qt.Key_Escape:
            print("[取消]")
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FloorAdjuster()
    w.show()
    sys.exit(app.exec())
