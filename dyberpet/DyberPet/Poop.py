"""
PoopWidget - 猫拉屎的独立窗口组件
屎从猫身体位置以抛物线飞出，落在任务栏上，用户点击消除获得亲密度。
"""
import os
import random
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QPixmap, QCursor

from DyberPet import settings


class PoopWidget(QWidget):
    """猫拉屎的独立窗口，带抛物线物理动画和点击消除"""

    poop_clicked = Signal(str, name='poop_clicked')

    # 屎的显示尺寸
    POOP_SIZE = 80

    def __init__(self, start_x, start_y, cat_bottom_y=0, parent=None):
        super(PoopWidget, self).__init__(parent)

        # 唯一标识
        self.poop_id = str(id(self))

        # 窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.SubWindow
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_MouseTracking, True)

        # hover 缩放动画（逐像素递增，确保均匀）
        self._current_size = self.POOP_SIZE  # 当前 size（像素）
        self._target_size = self.POOP_SIZE   # 目标 size
        self._anchor_x = 0
        self._anchor_y = 0
        self._base_pixmap = None  # 缓存原始 pixmap，避免每帧读磁盘
        self._scale_timer = QTimer(self)
        self._scale_timer.timeout.connect(self._scale_tick)
        self._hover_delay_timer = QTimer(self)
        self._hover_delay_timer.setSingleShot(True)
        self._hover_delay_timer.timeout.connect(self._start_hover_scale)

        # 加载屎的图片
        self._load_image()

        # 初始化位置：从参数传入（猫身体中心）
        self._init_position(start_x, start_y)

        # 抛物线物理参数：从猫身上往天上扔
        self.finished = False
        self.v_x = random.uniform(-8, 8)
        self.v_y = random.uniform(-18, -12)
        self.gravity = 0.5

        # 屏幕边界（全屏 geometry，用于左右上反弹检测）
        self.screen_rect = settings.current_screen.geometry()
        # 地面位置：屎视觉底部对齐猫视觉底部
        if cat_bottom_y > 0:
            # cat_bottom_y 是猫视觉底部的屏幕 Y 坐标
            # 屎落地时：poop.y + poop.height = cat_bottom_y
            self.floor_pos = cat_bottom_y - self.height()
        else:
            # fallback：用默认计算
            avail_geo = settings.current_screen.availableGeometry()
            work_height = avail_geo.height()
            settings.compute_floor_offset(settings.current_screen)
            self.floor_pos = (
                avail_geo.topLeft().y()
                + work_height
                - self.height()
                - settings.floor_y_offset
            )

        # 动画定时器
        self.timer = QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._physics_tick)
        self.timer.start(20)

        # 显示
        self.show()

    def _load_image(self):
        """加载屎的 PNG 图片，缩放到 POOP_SIZE 并缓存"""
        img_path = os.path.join(
            settings.basedir, 'res', 'items', 'Default', 'poop.png'
        )
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            pixmap = QPixmap(self.POOP_SIZE, self.POOP_SIZE)
            pixmap.fill(Qt.transparent)
        else:
            pixmap = pixmap.scaled(
                self.POOP_SIZE, self.POOP_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        self._base_pixmap = pixmap  # 缓存，hover 时直接用
        self.label = QLabel(self)
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.size())
        # label 不接收鼠标事件，全部传给父窗口
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.resize(pixmap.size())

    def _init_position(self, start_x, start_y):
        """初始位置：从 PetWidget 传入的猫身体坐标"""
        self.move(start_x - self.width() // 2, start_y)

    def _physics_tick(self):
        """每 20ms 执行一次物理计算"""
        if self.finished:
            return

        plus_x = self.v_x
        plus_y = self.v_y
        self.v_y += self.gravity

        new_x = self.x() + plus_x
        new_y = self.y() + plus_y

        new_x, new_y = self._limit_in_screen(new_x, new_y)
        self.move(int(new_x), int(new_y))

    def _limit_in_screen(self, new_x, new_y):
        """屏幕边界检测：左右上边界反弹，落地停止"""
        screen_left = self.screen_rect.topLeft().x()
        screen_right = screen_left + self.screen_rect.width()
        screen_top = self.screen_rect.topLeft().y()

        # 左边界反弹
        if new_x + self.width() // 2 < screen_left:
            new_x = screen_left - self.width() // 2
            self.v_x = abs(self.v_x) * 0.8
        # 右边界反弹
        elif new_x + self.width() // 2 > screen_right:
            new_x = screen_right - self.width() // 2
            self.v_x = -abs(self.v_x) * 0.8
        # 上边界反弹
        if new_y < screen_top:
            new_y = screen_top
            self.v_y = abs(self.v_y) * 0.8
        # 落地（任务栏顶部）
        elif new_y >= self.floor_pos:
            self.finished = True
            new_y = self.floor_pos
            self.timer.stop()

        return new_x, new_y

    # ---- 鼠标交互 ----

    def enterEvent(self, event):
        """鼠标进入窗口区域"""
        self._hover_in()

    def leaveEvent(self, event):
        """鼠标离开窗口区域"""
        self._hover_out()

    def mouseMoveEvent(self, event):
        pass

    def mousePressEvent(self, event):
        """左键点击：可消除"""
        if event.button() == Qt.LeftButton:
            self._fade_animation()

    def _hover_in(self):
        """鼠标悬停：延迟 100ms 后放大，避免边缘抖动"""
        if self.finished:
            self._hover_delay_timer.start(100)

    def _hover_out(self):
        """鼠标离开：立即缩小"""
        self._hover_delay_timer.stop()
        self.setCursor(QCursor(Qt.ArrowCursor))
        if self.finished and self._current_size > self.POOP_SIZE:
            self._anchor_x = self.x() + self.width() // 2
            self._anchor_y = self.y() + self.height()
            self._target_size = self.POOP_SIZE
            if not self._scale_timer.isActive():
                self._scale_timer.start(16)

    def _start_hover_scale(self):
        """延迟后开始放大"""
        self._anchor_x = self.x() + self.width() // 2
        self._anchor_y = self.y() + self.height()
        self._target_size = round(self.POOP_SIZE * 1.2)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        if not self._scale_timer.isActive():
            self._scale_timer.start(16)

    def _scale_tick(self):
        """逐像素递增/递减，确保均匀"""
        if self._current_size < self._target_size:
            self._current_size += 1
        elif self._current_size > self._target_size:
            self._current_size -= 1
        else:
            self._scale_timer.stop()
            return
        self._apply_scale()

    def _apply_scale(self):
        """根据当前 size 缩放并显示图片，底部中心点固定"""
        if self._base_pixmap is None:
            return
        s = self._current_size
        scaled = self._base_pixmap.scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        w, h = scaled.width(), scaled.height()
        self.setUpdatesEnabled(False)
        self.label.setPixmap(scaled)
        self.label.setGeometry(0, 0, w, h)
        self.setGeometry(self._anchor_x - w // 2, self._anchor_y - h, w, h)
        self.setUpdatesEnabled(True)

    def _fade_animation(self):
        """200ms 淡出动画"""
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.fade_anim.finished.connect(self._on_fade_done)
        self.fade_anim.start()

    def _on_fade_done(self):
        """淡出完成后发射信号并关闭"""
        self.poop_clicked.emit(self.poop_id)
        self.close()
