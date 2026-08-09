"""在桌面上连续播放 RGBA 帧序列，预览动画效果。"""

import sys
import time
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtGui import QPixmap, QImage, QTransform
from PySide6.QtCore import Qt, QTimer


class AnimationPreview(QWidget):
    def __init__(self, frames_dir: str, fps: int = 12):
        super().__init__()
        self.frames_dir = Path(frames_dir)
        self.fps = fps
        self.current_idx = 0

        # 加载所有帧
        self.frames = []
        png_files = sorted(self.frames_dir.glob("*.png"))
        for f in png_files:
            img = Image.open(f).convert("RGBA")
            # 转换为 QPixmap
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            self.frames.append(QPixmap.fromImage(qimg))

        if not self.frames:
            print("错误：没有找到 PNG 文件")
            sys.exit(1)

        print(f"加载了 {len(self.frames)} 帧，{fps}fps")

        # 窗口设置
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 标签显示图片
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)

        # 调整窗口大小
        first_pixmap = self.frames[0]
        self.setFixedSize(first_pixmap.width(), first_pixmap.height())
        self.label.setGeometry(0, 0, first_pixmap.width(), first_pixmap.height())

        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(1000 // fps)

        # 居中显示在屏幕右下角
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 50, screen.height() - self.height() - 100)

    def next_frame(self):
        """显示下一帧。"""
        self.label.setPixmap(self.frames[self.current_idx])
        self.current_idx = (self.current_idx + 1) % len(self.frames)

    def keyPressEvent(self, event):
        """按 Escape 退出。"""
        if event.key() == Qt.Key_Escape:
            self.close()


def main():
    frames_dir = sys.argv[1] if len(sys.argv) > 1 else "data/pipeline/rgba/stand"
    fps = int(sys.argv[2]) if len(sys.argv) > 2 else 12

    app = QApplication(sys.argv)
    preview = AnimationPreview(frames_dir, fps)
    preview.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
