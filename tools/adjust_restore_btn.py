"""
恢复按钮位置调节器 — 拖拽按钮到猫脚旁边想要的位置，保存偏移量。

使用：D:\Python\python.exe tools/adjust_restore_btn.py
操作：拖拽按钮移动 | Enter 保存 | Esc 取消
"""

import sys
import json
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QBrush


BASE_DIR = Path(__file__).resolve().parent.parent
SPRITE_DIR = BASE_DIR / "dyberpet" / "res" / "role" / "六一" / "action"
CONFIG_PATH = BASE_DIR / "assets" / "configs" / "pet_conf.json"


def load_scale():
    """从 pet_conf.json 读取缩放比例"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            conf = json.load(f)
        return conf.get('scale', 1.0)
    except Exception:
        return 1.0


def load_sprite():
    """加载 stand 动画的第一帧作为参考"""
    import glob, re
    sprites = sorted(glob.glob(str(SPRITE_DIR / "stand_*.png")))
    if not sprites:
        print("找不到 stand 精灵图")
        sys.exit(1)
    return QPixmap(sprites[0])


def load_restore_btn_offset():
    """从 pet_conf.json 读取保存的偏移量"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            conf = json.load(f)
        offset = conf.get('restore_btn_offset', [0, 0])
        return offset[0], offset[1]
    except Exception:
        return 0, 0


def save_restore_btn_offset(dx, dy):
    """保存偏移量到 pet_conf.json"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        conf = json.load(f)
    conf['restore_btn_offset'] = [dx, dy]
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)
    print(f"已保存: restore_btn_offset = [{dx}, {dy}]")
    print("提示：运行 python tools/copy_configs.py 将配置部署到角色目录")


class RestoreBtnAdjuster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("拖拽恢复按钮到猫脚旁边 | Enter 保存 | Esc 取消")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        self.raw_sprite = load_sprite()
        self.scale = load_scale()
        # 缩放后的精灵图（和游戏显示一致）
        self.sprite = self.raw_sprite.scaled(
            int(self.raw_sprite.width() * self.scale),
            int(self.raw_sprite.height() * self.scale),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.btn_size = 28

        # 读取已保存的偏移量（已保存的是缩放后的坐标）
        saved_dx, saved_dy = load_restore_btn_offset()

        # 窗口大小 = 缩放后的精灵图大小
        self.resize(self.sprite.width(), self.sprite.height())

        # 按钮初始位置（相对于缩放后的精灵图左上角）
        self.btn_pos = QPoint(saved_dx, saved_dy) if (saved_dx or saved_dy) else QPoint(
            self.sprite.width() - self.btn_size - 10,
            self.sprite.height() - self.btn_size - 10
        )

        self.dragging = False
        self.drag_offset = QPoint()

        # 位置信息标签
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet(
            "background: rgba(0,0,0,180); color: white; padding: 4px 8px; "
            "border-radius: 4px; font-size: 13px;"
        )
        self._update_info()

    def _update_info(self):
        self.info_label.setText(
            f"  偏移量: [{self.btn_pos.x()}, {self.btn_pos.y()}]  "
            f"| Enter 保存 | Esc 取消  "
        )
        self.info_label.adjustSize()
        self.info_label.move(0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 画精灵图
        painter.drawPixmap(0, 0, self.sprite)

        # 画参考网格（十字线）
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.DotLine))
        painter.drawLine(self.width() // 2, 0, self.width() // 2, self.height())
        painter.drawLine(0, self.height() // 2, self.width(), self.height() // 2)

        # 画恢复按钮（模拟样式）
        bx, by = self.btn_pos.x(), self.btn_pos.y()
        # 背景圆
        painter.setBrush(QBrush(QColor(255, 255, 255, 140)))
        painter.setPen(QPen(QColor(180, 180, 180, 200), 1.5))
        painter.drawEllipse(bx + 2, by + 2, 24, 24)
        # 眼睛图标
        icon_color = QColor(80, 80, 80, 200)
        painter.setPen(QPen(icon_color, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(bx + 7, by + 8, 14, 12)
        painter.setBrush(QBrush(icon_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(bx + 12, by + 12, 5, 5)

        # 画按钮边框（拖拽时高亮）
        if self.dragging:
            painter.setPen(QPen(QColor(0, 150, 255, 200), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(bx, by, self.btn_size, self.btn_size)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            btn_rect = QRect(self.btn_pos, self.btn_pos + QPoint(self.btn_size, self.btn_size))
            if btn_rect.contains(event.pos()):
                self.dragging = True
                self.drag_offset = event.pos() - self.btn_pos
                self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.btn_pos = event.pos() - self.drag_offset
            self._update_info()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(Qt.CrossCursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            save_restore_btn_offset(self.btn_pos.x(), self.btn_pos.y())
            self.close()
        elif event.key() == Qt.Key_Escape:
            print("已取消")
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    adjuster = RestoreBtnAdjuster()
    adjuster.show()
    sys.exit(app.exec())
