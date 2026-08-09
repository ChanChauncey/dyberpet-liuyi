import sys
import os
from sys import platform
import time
import math
import types
import random
import inspect
import webbrowser
import threading
import ctypes
from typing import List
from pathlib import Path
import pynput.mouse as mouse

from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer, QObject, QPoint, QEvent, QElapsedTimer
from PySide6.QtCore import QObject, QThread, Signal, QRectF, QRect, QSize, QPropertyAnimation, QAbstractAnimation
from PySide6.QtGui import QImage, QPixmap, QIcon, QCursor, QPainter, QFont, QFontMetrics, QAction, QBrush, QPen, QColor, QFontDatabase, QPainterPath, QRegion, QIntValidator, QDoubleValidator
from PySide6.QtWidgets import QGraphicsOpacityEffect

from qfluentwidgets import CaptionLabel, setFont, Action #,RoundMenu
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBar, InfoBarPosition
from DyberPet.custom_widgets import SystemTray
from .custom_roundmenu import RoundMenu

from DyberPet.conf import *
from DyberPet.utils import *
from DyberPet.modules import *
from DyberPet.Accessory import MouseMoveManager
from DyberPet.custom_widgets import RoundBarBase, LevelBadge
from DyberPet.bubbleManager import BubbleManager

# initialize settings
import DyberPet.settings as settings
settings.init()

basedir = settings.BASEDIR
configdir = settings.CONFIGDIR


# version
dyberpet_version = settings.VERSION
vf = open(os.path.join(configdir,'data/version'), 'w')
vf.write(dyberpet_version)
vf.close()

# some UI size parameters
status_margin = int(3)
statbar_h = settings.STATBAR_H  # 与 settings.py 保持一致，确保落地计算正确
icons_wh = 20

# system config
sys_hp_tiers = settings.HP_TIERS 
sys_hp_interval = settings.HP_INTERVAL
sys_lvl_bar = settings.LVL_BAR
sys_pp_heart = settings.PP_HEART
sys_pp_item = settings.PP_ITEM
sys_pp_audio = settings.PP_AUDIO


# Pet HP progress bar
class DP_HpBar(QProgressBar):
    hptier_changed = Signal(int, str, name='hptier_changed')
    hp_updated = Signal(int, name='hp_updated')

    def __init__(self, *args, **kwargs):

        super(DP_HpBar, self).__init__(*args, **kwargs)

        self.setFormat('0/100')
        self.setValue(0)
        self.setAlignment(Qt.AlignCenter)
        self.hp_tiers = sys_hp_tiers #[0,50,80,100]

        self.hp_max = 100
        self.interval = 1
        self.hp_inner = 0
        self.hp_perct = 0

        # Custom colors and sizes
        self.bar_color = QColor("#FAC486")  # Fill color
        self.border_color = QColor(0, 0, 0) # Border color
        self.border_width = 1               # Border width in pixels
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Full widget rect minus border width to avoid overlap
        full_rect = QRectF(self.border_width / 2.0, self.border_width / 2.0,
                           self.width() - self.border_width, self.height() - self.border_width)
        radius = (self.height() - self.border_width) / 2.0

        # Draw the background rounded rectangle
        painter.setBrush(QBrush(QColor(240, 240, 240)))  # Light gray background
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawRoundedRect(full_rect, radius, radius)

        # Create a clipping path for the filled progress that is inset by the border width
        clip_path = QPainterPath()
        inner_rect = full_rect.adjusted(self.border_width, self.border_width, -self.border_width, -self.border_width)
        clip_path.addRoundedRect(inner_rect, radius - self.border_width, radius - self.border_width)
        painter.setClipPath(clip_path)

        # Calculate progress rect and draw it within the clipping region
        progress_width = (self.width() - 2 * self.border_width) * self.value() / self.maximum()
        progress_rect = QRectF(self.border_width, self.border_width,
                               progress_width, self.height() - 2 * self.border_width)

        painter.setBrush(QBrush(self.bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(progress_rect)
        
        # Text drawing
        painter.setClipping(False)  # Disable clipping to draw text over entire bar
        text = self.format()  # Use the format string directly
        painter.setPen(QColor(0, 0, 0))  # Set text color
        font = QFont("Segoe UI", 9, QFont.Normal)
        painter.setFont(font)
        #painter.drawText(full_rect, Qt.AlignCenter, text)
        font_metrics = QFontMetrics(font)
        text_height = font_metrics.height()
        # Draw text in the calculated position
        painter.drawText(full_rect.adjusted(0, -font_metrics.descent()//2, 0, 0), Qt.AlignCenter, text)

    def init_HP(self, change_value, interval_time):
        self.hp_max = int(100*interval_time)
        self.interval = interval_time
        if change_value == -1:
            self.hp_inner = self.hp_max
            settings.pet_data.change_hp(self.hp_inner)
        else:
            self.hp_inner = change_value
        self.hp_perct = math.ceil(round(self.hp_inner/self.interval, 1))
        self.setFormat('%i/100'%self.hp_perct)
        self.setValue(self.hp_perct)
        self._onTierChanged()
        self.hp_updated.emit(self.hp_perct)

    def updateValue(self, change_value, from_mod):

        before_value = self.value()

        if from_mod == 'Scheduler':
            if settings.HP_stop:
                return
            new_hp_inner = max(self.hp_inner + change_value, 0)

        else:

            if change_value > 0:
                new_hp_inner = min(self.hp_inner + change_value*self.interval, self.hp_max)

            elif change_value < 0:
                new_hp_inner = max(self.hp_inner + change_value*self.interval, 0)

            else:
                return 0


        if new_hp_inner == self.hp_inner:
            return 0
        else:
            self.hp_inner = new_hp_inner

        new_hp_perct = math.ceil(round(self.hp_inner/self.interval, 1))
            
        if new_hp_perct == self.hp_perct:
            settings.pet_data.change_hp(self.hp_inner)
            return 0
        else:
            self.hp_perct = new_hp_perct
            self.setFormat('%i/100'%self.hp_perct)
            self.setValue(self.hp_perct)
        
        after_value = self.value()

        hp_tier = sum([int(after_value>i) for i in self.hp_tiers])

        #告知动画模块、通知模块
        if hp_tier > settings.pet_data.hp_tier:
            self.hptier_changed.emit(hp_tier,'up')
            settings.pet_data.change_hp(self.hp_inner, hp_tier)
            self._onTierChanged()

        elif hp_tier < settings.pet_data.hp_tier:
            self.hptier_changed.emit(hp_tier,'down')
            settings.pet_data.change_hp(self.hp_inner, hp_tier)
            self._onTierChanged()
            
        else:
            settings.pet_data.change_hp(self.hp_inner) #.hp = current_value

        self.hp_updated.emit(self.hp_perct)
        return int(after_value - before_value)

    def _onTierChanged(self):
        colors = ["#f8595f", "#f8595f", "#FAC486", "#abf1b7"]
        self.bar_color = QColor(colors[settings.pet_data.hp_tier])  # Fill color
        self.update()
        



# Favorability Progress Bar
class DP_FvBar(QProgressBar):
    fvlvl_changed = Signal(int, name='fvlvl_changed')
    fv_updated = Signal(int, int, name='fv_updated')

    def __init__(self, *args, **kwargs):

        super(DP_FvBar, self).__init__(*args, **kwargs)

        # Custom colors and sizes
        self.bar_color = QColor("#F4665C")  # Fill color
        self.border_color = QColor(0, 0, 0) # Border color
        self.border_width = 1               # Border width in pixels

        self.fvlvl = 0
        self.lvl_bar = sys_lvl_bar #[20, 120, 300, 600, 1200]
        self.points_to_lvlup = self.lvl_bar[self.fvlvl]
        self.setMinimum(0)
        self.setMaximum(self.points_to_lvlup)
        self.setFormat('lv%s: 0/%s'%(int(self.fvlvl), self.points_to_lvlup))
        self.setValue(0)
        self.setAlignment(Qt.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Full widget rect minus border width to avoid overlap
        full_rect = QRectF(self.border_width / 2.0, self.border_width / 2.0,
                           self.width() - self.border_width, self.height() - self.border_width)
        radius = (self.height() - self.border_width) / 2.0

        # Draw the background rounded rectangle
        painter.setBrush(QBrush(QColor(240, 240, 240)))  # Light gray background
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawRoundedRect(full_rect, radius, radius)

        # Create a clipping path for the filled progress that is inset by the border width
        clip_path = QPainterPath()
        inner_rect = full_rect.adjusted(self.border_width, self.border_width, -self.border_width, -self.border_width)
        clip_path.addRoundedRect(inner_rect, radius - self.border_width, radius - self.border_width)
        painter.setClipPath(clip_path)

        # Calculate progress rect and draw it within the clipping region
        progress_width = (self.width() - 2 * self.border_width) * self.value() / self.maximum()
        progress_rect = QRectF(self.border_width, self.border_width,
                               progress_width, self.height() - 2 * self.border_width)

        painter.setBrush(QBrush(self.bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(progress_rect)
        
        # Text drawing
        painter.setClipping(False)  # Disable clipping to draw text over entire bar
        text = self.format()  # Use the format string directly
        painter.setPen(QColor(0, 0, 0))  # Set text color
        font = QFont("Segoe UI", 9, QFont.Normal)
        painter.setFont(font)
        #painter.drawText(full_rect, Qt.AlignCenter, text)
        font_metrics = QFontMetrics(font)
        text_height = font_metrics.height()
        # Draw text in the calculated position
        painter.drawText(full_rect.adjusted(0, -font_metrics.descent()//2, 0, 0), Qt.AlignCenter, text)

    def init_FV(self, fv_value, fv_lvl):
        self.fvlvl = fv_lvl
        self.points_to_lvlup = self.lvl_bar[self.fvlvl]
        self.setMinimum(0)
        self.setMaximum(self.points_to_lvlup)
        self.setFormat('lv%s: %i/%s'%(int(self.fvlvl), fv_value, self.points_to_lvlup))
        self.setValue(fv_value)
        self.fv_updated.emit(self.value(), self.fvlvl)

    def updateValue(self, change_value, from_mod):

        before_value = self.value()

        if from_mod == 'Scheduler':
            if settings.pet_data.hp_tier > 1:
                prev_value = self.value()
                current_value = self.value() + change_value #, self.maximum())
            elif settings.pet_data.hp_tier == 0 and not settings.FV_stop:
                prev_value = self.value()
                current_value = self.value() - 5
            else:
                return 0

        elif change_value != 0:
            prev_value = self.value()
            current_value = self.value() + change_value

        else:
            return 0


        if current_value < 0:
            # 好感度降级
            if self.fvlvl > 0:
                addedValue = self._level_down(current_value, prev_value)
                self.fv_updated.emit(self.value(), self.fvlvl)
                return addedValue
            else:
                # 已经是最低级，设为 0
                self.setValue(0)
                self.setFormat('lv%s: 0/%s'%(int(self.fvlvl), int(self.maximum())))
                settings.pet_data.change_fv(0, self.fvlvl)
                self.fv_updated.emit(0, self.fvlvl)
                return int(0 - before_value)

        elif current_value < self.maximum():
            self.setValue(current_value)

            current_value = self.value()
            if current_value == prev_value:
                return 0
            else:
                self.setFormat('lv%s: %s/%s'%(int(self.fvlvl), int(current_value), int(self.maximum())))
                settings.pet_data.change_fv(current_value)
            after_value = self.value()

            self.fv_updated.emit(self.value(), self.fvlvl)
            return int(after_value - before_value)

        else: #好感度升级
            addedValue = self._level_up(current_value, prev_value)
            self.fv_updated.emit(self.value(), self.fvlvl)
            return addedValue

    def _level_up(self, newValue, oldValue, added=0):
        if self.fvlvl == (len(self.lvl_bar)-1):
            current_value = self.maximum()
            if current_value == oldValue:
                return 0
            self.setFormat('lv%s: %s/%s'%(int(self.fvlvl),int(current_value),self.points_to_lvlup))
            self.setValue(current_value)
            settings.pet_data.change_fv(current_value, self.fvlvl)
            #告知动画模块、通知模块
            self.fvlvl_changed.emit(-1)
            return current_value - oldValue + added

        else:
            #after_value = newValue
            added_tmp = self.maximum() - oldValue
            newValue -= self.maximum()
            self.fvlvl += 1
            self.points_to_lvlup = self.lvl_bar[self.fvlvl]
            self.setMinimum(0)
            self.setMaximum(self.points_to_lvlup)
            self.setFormat('lv%s: %s/%s'%(int(self.fvlvl),int(newValue),self.points_to_lvlup))
            self.setValue(newValue)
            settings.pet_data.change_fv(newValue, self.fvlvl)
            #告知动画模块、通知模块
            self.fvlvl_changed.emit(self.fvlvl)

            if newValue < self.maximum():
                return newValue + added_tmp + added
            else:
                return self._level_up(newValue, 0, added_tmp)

    def _level_down(self, newValue, oldValue):
        """好感度降级：当前等级归零后进入上一级"""
        # 计算需要扣减的总量
        deduct_total = oldValue - newValue  # newValue 是负数，所以这是正数
        # 扣减当前等级的值
        current_deduct = min(oldValue, deduct_total)
        remaining = deduct_total - current_deduct
        new_value = oldValue - current_deduct

        # 如果还需要继续扣减，降级
        if remaining > 0 and self.fvlvl > 0:
            self.fvlvl -= 1
            self.points_to_lvlup = self.lvl_bar[self.fvlvl]
            self.setMinimum(0)
            self.setMaximum(self.points_to_lvlup)
            # 用上一级的满值继续扣
            new_value = self.points_to_lvlup - remaining

        self.setValue(max(0, new_value))
        self.setFormat('lv%s: %s/%s'%(int(self.fvlvl), int(self.value()), int(self.maximum())))
        settings.pet_data.change_fv(self.value(), self.fvlvl)
        # 告知动画模块、通知模块
        self.fvlvl_changed.emit(self.fvlvl)
        return int(self.value() - oldValue)




# 恢复按钮：穿透模式下显示的小圆按钮，独立窗口，始终置顶
class RestoreButton(QWidget):
    clicked = Signal()
    position_saved = Signal(int, int)  # 拖拽保存时发射

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(48, 26)
        self._hovered = False
        self._adjust_mode = False  # 调整模式：拖拽保存位置
        self._dragging = False
        self._drag_offset = QPoint()
        self.setCursor(Qt.PointingHandCursor)

    def set_adjust_mode(self, on):
        """开启/关闭调整模式（拖拽保存位置）"""
        self._adjust_mode = on
        self.setCursor(Qt.SizeAllCursor if on else Qt.PointingHandCursor)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._adjust_mode:
            bg_color = QColor(0, 150, 255, 170 if self._hovered else 120)
            border_color = QColor(0, 120, 220, 230)
        else:
            bg_color = QColor(255, 255, 255, 190 if self._hovered else 130)
            border_color = QColor(170, 170, 170, 210)
        # 圆角矩形背景
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(1, 1, 46, 24, 8, 8)
        # "恢复"文字
        text_color = QColor(55, 55, 55, 230 if self._hovered else 170)
        painter.setPen(QPen(text_color))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, 48, 26, Qt.AlignCenter, "恢复")
        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._adjust_mode:
                self._dragging = True
                self._drag_offset = event.globalPos() - self.pos()
            else:
                self.clicked.emit()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            # 保存位置（相对于主窗口 label 左上角的偏移）
            self.position_saved.emit(self.pos().x(), self.pos().y())


# Pet Object
class PetWidget(QWidget):
    setup_notification = Signal(str, str, name='setup_notification')
    setup_bubbleText = Signal(dict, int, int, name="setup_bubbleText")
    close_bubble = Signal(str, name="close_bubble")
    addItem_toInven = Signal(int, list, name='addItem_toInven')
    fvlvl_changed_main_note = Signal(int, name='fvlvl_changed_main_note')
    fvlvl_changed_main_inve = Signal(int, name='fvlvl_changed_main_inve')
    hptier_changed_main_note = Signal(int, str, name='hptier_changed_main_note')

    setup_acc = Signal(dict, int, int, int, name='setup_acc')
    change_note = Signal(name='change_note')
    close_all_accs = Signal(name='close_all_accs')

    move_sig = Signal(int, int, name='move_sig')
    #acc_withdrawed = Signal(str, name='acc_withdrawed')
    send_positions = Signal(list, list, name='send_positions')

    lang_changed = Signal(name='lang_changed')
    show_controlPanel = Signal(name='show_controlPanel')

    show_dashboard = Signal(name='show_dashboard')
    show_dashboard_panel = Signal(str, name='show_dashboard_panel')
    hp_updated = Signal(int, name='hp_updated')
    fv_updated = Signal(int, int, name='fv_updated')

    compensate_rewards = Signal(name="compensate_rewards")
    refresh_bag = Signal(name="refresh_bag")
    addCoins = Signal(int, name='addCoins')
    autofeed = Signal(name='autofeed')

    stopAllThread = Signal(name='stopAllThread')

    taskUI_Timer_update = Signal(name="taskUI_Timer_update")
    taskUI_task_end = Signal(name="taskUI_task_end")
    single_pomo_done = Signal(name="single_pomo_done")

    refresh_acts = Signal(name='refresh_acts')

    def __init__(self, parent=None, curr_pet_name=None, pets=(), screens=[]):
        """
        宠物组件
        :param parent: 父窗口
        :param curr_pet_name: 当前宠物名称
        :param pets: 全部宠物列表
        """
        super(PetWidget, self).__init__(parent) #, flags=Qt.WindowFlags())
        self.setFocusPolicy(Qt.StrongFocus)  # 允许接收键盘事件
        self.pets = settings.pets
        if curr_pet_name is None:
            self.curr_pet_name = settings.default_pet
        else:
            self.curr_pet_name = curr_pet_name
        #self.pet_conf = PetConfig()

        self.image = None
        self.tray = None

        # 鼠标拖拽初始属性
        self.is_follow_mouse = False
        self.mouse_moving = False
        self.mouse_drag_pos = self.pos()
        self.mouse_pos = [0, 0]
        self.drag_started = False  # 是否已触发拖拽动画
        self.was_onfloor = 1  # 按下时的地面状态

        # 地面位置调整模式
        self.adjusting_floor = False
        self.adjust_dragging = False

        # 隐身模式调试：显示活跃区域
        self._show_active_rect = False

        # 隐身模式活跃区域编辑器
        self._editing_active_rects = False  # 编辑模式
        self._active_rects = []  # 多个矩形列表 [QRect, ...]
        self._active_rects_file = None  # 配置文件路径
        self._dragging_rect_idx = -1  # 正在拖拽的矩形索引
        self._dragging_rect_offset = None  # 拖拽偏移量
        self._selected_rect_idx = -1  # 选中的矩形索引

        # Record too frequent mouse clicking
        self.click_timer = QElapsedTimer()
        self.click_interval = 1000  # Max interval in ms to consider consecutive clicks
        self.click_count = 0
        self.is_entertainment_playing = False  # 自娱自乐动画播放锁定
        self.is_land_anim_playing = False  # land 动画播放锁定
        self._prev_fv_lvl = 0  # 上一次的好感度等级，用于判断升级/降级

        # Screen info
        settings.screens = screens #[i.geometry() for i in screens]
        self.current_screen = settings.screens[0].availableGeometry() #geometry()
        settings.current_screen = settings.screens[0]
        #self.screen_geo = QDesktopWidget().availableGeometry() #screenGeometry()
        self.screen_width = self.current_screen.width() #self.screen_geo.width()
        self.screen_height = self.current_screen.height() #self.screen_geo.height()
        settings.screen_width = self.screen_width

        # 自动计算地面偏移量（基于当前屏幕的任务栏高度）
        settings.compute_floor_offset(settings.current_screen)

        self._init_ui()
        self._init_widget()
        self.init_conf(self.curr_pet_name) # if curr_pet_name else self.pets[0])

        #self._set_menu(pets)
        #self._set_tray()
        self.show()
        self.setFocus()  # 确保窗口获取焦点

        self._setup_ui()

        # 开始动画模块和交互模块
        self.threads = {}
        self.workers = {}
        self.runAnimation()
        self.runInteraction()
        self.runScheduler()

        # 拉屎功能：存活的屎实例列表
        self.poop_list = []

        # 初始化重复提醒任务 - feature deleted
        #self.remind_window.initial_task()

        # 启动完毕10s后检查好感度等级奖励补偿
        self.compensate_timer = None

        # 弹跳物理已合并到 Interaction 线程的 animat 中

        self._setup_compensate()

        # 启动后自动检测新版本（延迟4s，避免影响启动；网络请求在后台线程）
        QTimer.singleShot(4000, self._autoCheckUpdate)

    def _autoCheckUpdate(self):
        """启动后自动检测 GitHub Release 是否有新版本，结果均弹窗反馈（不阻塞启动）"""
        def _worker():
            try:
                from DyberPet.DyberSettings.BasicSettingUI import get_latest_version, compare_versions
                success, github_version = get_latest_version()
                if success:
                    if compare_versions(settings.VERSION, github_version):
                        QTimer.singleShot(0, lambda: InfoBar.success(
                            title='发现新版本',
                            content='最新版本 ' + github_version + ' 已发布，到「设置 → 关于」下载',
                            duration=6000,
                            position=InfoBarPosition.TOP,
                            parent=self))
                    else:
                        QTimer.singleShot(0, lambda: InfoBar.info(
                            title='已是最新版本',
                            content='当前 ' + settings.VERSION + ' 无需更新',
                            duration=4000,
                            position=InfoBarPosition.TOP,
                            parent=self))
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _setup_compensate(self):
        self._stop_compensate()
        self.compensate_timer = QTimer(singleShot=True, timeout=self._compensate_rewards)
        self.compensate_timer.start(10000)

    def _stop_compensate(self):
        if self.compensate_timer:
            self.compensate_timer.stop()

    def moveEvent(self, event):
        """窗口移动时自动同步位置到 settings，供 InteractionThread 读取。"""
        super().moveEvent(event)
        pos = event.pos()
        settings.widget_pos = [pos.x(), pos.y()]

    def _move_bounce(self, dx, dy):
        """弹跳移动：增量方式，从 bounce_start_pos 累加。
        弹跳期间不走 limit_in_screen，避免 current_anchor 变化导致地板参考点漂移。"""
        new_x = settings.bounce_start_pos[0] + dx
        new_y = settings.bounce_start_pos[1] + dy
        # 只做屏幕边界钳制（左右+上），不做地板钳制
        screen = self.current_screen
        if new_x + self.width() // 2 < screen.topLeft().x():
            new_x = screen.topLeft().x() - self.width() // 2
        elif new_x + self.width() // 2 > screen.topLeft().x() + self.screen_width:
            new_x = screen.topLeft().x() + self.screen_width - self.width() // 2
        if new_y + self.height() - self.label.height() // 2 < screen.topLeft().y():
            new_y = screen.topLeft().y() + self.label.height() // 2 - self.height()
        settings.bounce_start_pos = [new_x, new_y]
        floor = self.floor_pos + settings.current_anchor[1]
        pass
        self.move(new_x, new_y)

    def moveEvent(self, event):
        self.move_sig.emit(self.pos().x()+self.width()//2, self.pos().y()+self.height())
        # 穿透模式下同步恢复按钮位置
        if settings.click_through_mode and hasattr(self, '_restore_btn') and self._restore_btn.isVisible():
            self._position_restore_button()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen, QFont
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 编辑模式下绘制活跃区域
        if self._editing_active_rects:
            self._draw_active_rects(painter)

        if not self.adjusting_floor:
            painter.end()
            return

        # 地面线位置（局部坐标）
        floor_local_y = self.height() - settings.floor_y_offset
        # 红色虚线
        painter.setPen(QPen(QColor(255, 80, 80, 200), 2, Qt.DashLine))
        painter.drawLine(0, floor_local_y, self.width(), floor_local_y)
        # 标签
        offset = settings.floor_y_offset
        if offset > 0:
            label = f"↓ {offset}px"
        elif offset < 0:
            label = f"↑ {-offset}px"
        else:
            label = "default"
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        painter.setPen(QColor(255, 80, 80))
        painter.drawText(4, floor_local_y - 5, label)
        painter.end()

    def _draw_active_rects(self, painter):
        """绘制隐身模式的活跃区域（多矩形）"""
        from PySide6.QtGui import QColor, QPen, QBrush
        from PySide6.QtCore import QRect

        # 如果没有自定义矩形，绘制默认的单一矩形
        if not self._active_rects:
            label_pos_in_widget = self.label.pos()
            label_rect = QRect(label_pos_in_widget, self.label.size())
            btn_rect = QRect()
            if hasattr(self, '_restore_btn') and self._restore_btn.isVisible():
                btn_global = self._restore_btn.pos()
                btn_local = self.mapFromGlobal(btn_global)
                btn_rect = QRect(btn_local, self._restore_btn.size())
            active_rect = label_rect.united(btn_rect).adjusted(-3, -3, 3, 3)

            painter.setPen(QPen(QColor(255, 165, 0, 200), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 165, 0, 30)))
            painter.drawRect(active_rect)
            return

        # 绘制所有自定义矩形
        for i, rect in enumerate(self._active_rects):
            # 选中状态用实线，未选中用虚线
            if i == self._selected_rect_idx:
                painter.setPen(QPen(QColor(255, 100, 0, 255), 3, Qt.SolidLine))
                painter.setBrush(QBrush(QColor(255, 165, 0, 60)))
            else:
                painter.setPen(QPen(QColor(255, 165, 0, 200), 2, Qt.DashLine))
                painter.setBrush(QBrush(QColor(255, 165, 0, 30)))
            painter.drawRect(rect)

            # 标注序号
            painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect.x() + 3, rect.y() + 12, f"#{i}")

        # 编辑模式提示
        if self._editing_active_rects:
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.setPen(QColor(255, 200, 0))
            painter.drawText(5, 15, "编辑模式: 双击添加 | 右键删除 | 拖拽移动")

    def enterEvent(self, event):
        # Change the cursor when it enters the window
        self.setCursor(self.cursor_default)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Restore the original cursor when it leaves the window
        self.setCursor(self.cursor_user)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """
        鼠标点击事件
        :param event: 事件
        :return:
        """
        # 活跃区域编辑模式：拦截鼠标事件
        if self._editing_active_rects:
            if event.button() == Qt.LeftButton:
                # 检查是否点击了某个矩形
                idx = self._get_rect_at_pos(event.globalPos())
                if idx >= 0:
                    # 选中并开始拖拽
                    self._selected_rect_idx = idx
                    local_pos = self.mapFromGlobal(event.globalPos())
                    rect = self._active_rects[idx]
                    self._dragging_rect_offset = (local_pos.x() - rect.x(), local_pos.y() - rect.y())
                    self._dragging_rect_idx = idx
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    # 点击空白处：添加新矩形
                    self._add_active_rect(event.globalPos())
                self.update()
                event.accept()
                return
            elif event.button() == Qt.RightButton:
                # 右键：显示菜单
                self._show_active_rect_menu(event.globalPos())
                event.accept()
                return

        # 地面调整模式：拦截所有鼠标事件
        if self.adjusting_floor:
            if event.button() == Qt.LeftButton:
                self.adjust_dragging = True
                self.setCursor(Qt.SizeAllCursor)
            return

        if event.button() == Qt.RightButton:
            # 打开右键菜单
            if settings.draging:
                return
            #self.setContextMenuPolicy(Qt.CustomContextMenu)
            #self.customContextMenuRequested.connect(self._show_Staus_menu)
            self._show_Staus_menu()
            
        # 睡觉状态下，左键点击无反应
        if settings.is_sleeping and event.button() == Qt.LeftButton:
            # 记录拖拽位置，允许 X 轴移动
            self.mouse_drag_pos = event.globalPos() - self.pos()
            self.is_follow_mouse = True  # 跟随鼠标，但 mouseMoveEvent 会限制为 X 轴
            self.was_onfloor = settings.onfloor  # 初始化，避免松手时未定义
            event.accept()
            return

        # 启动阶段，左键只允许 X 轴拖拽
        if settings.is_starting_up and event.button() == Qt.LeftButton:
            self.mouse_drag_pos = event.globalPos() - self.pos()
            self.is_follow_mouse = True
            self.was_onfloor = settings.onfloor
            event.accept()
            return

        # 自娱自乐动画播放期间，只允许 X 轴拖拽
        if self.is_entertainment_playing and event.button() == Qt.LeftButton:
            self.mouse_drag_pos = event.globalPos() - self.pos()
            self.is_follow_mouse = True
            self.was_onfloor = settings.onfloor
            event.accept()
            return

        # land_bounce 动画期间，禁止拖拽（弹跳有自己移动逻辑）
        # land_stay 动画期间，只允许 X 轴拖拽
        if self.is_land_anim_playing and event.button() == Qt.LeftButton:
            if settings.bouncing:
                event.accept()
                return
            self.mouse_drag_pos = event.globalPos() - self.pos()
            self.is_follow_mouse = True
            self.was_onfloor = settings.onfloor
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            # 左键绑定拖拽
            self.is_follow_mouse = True
            self.mouse_drag_pos = event.globalPos() - self.pos()
            self.drag_started = False  # 重置拖拽状态
            self.was_onfloor = settings.onfloor  # 保存按下时的地面状态

            # 按下时立即设置 onfloor=0，让 mousedrag 条件满足
            if settings.set_fall:
                settings.onfloor = 0
            settings.draging=1
            settings.bouncing = False  # 打断弹跳
            settings.land_bounce_done = False  # 允许下次落地弹跳
            # 空中按住：跳过 drag_start，直接 drag_loop
            if settings.prefall or self.was_onfloor == 0:
                settings.drag_start_done = True
            self.workers['Animation'].pause()

            # Record click
            if self.click_timer.isValid() and self.click_timer.elapsed() <= self.click_interval:
                self.click_count += 1
            else:
                self.click_count = 1
                self.click_timer.restart()

            event.accept()
            #self.setCursor(QCursor(Qt.ArrowCursor))
            self.setCursor(self.cursor_clicked)

    def mouseMoveEvent(self, event):
        """
        鼠标移动事件, 左键且绑定跟随, 移动窗体
        :param event:
        :return:
        """
        # 活跃区域编辑模式：拖拽矩形
        if self._editing_active_rects and self._dragging_rect_idx >= 0:
            local_pos = self.mapFromGlobal(event.globalPos())
            rect = self._active_rects[self._dragging_rect_idx]
            new_x = local_pos.x() - self._dragging_rect_offset[0]
            new_y = local_pos.y() - self._dragging_rect_offset[1]
            rect.moveTopLeft(QPoint(int(new_x), int(new_y)))
            self.update()
            event.accept()
            return

        # 地面调整模式
        if self.adjusting_floor:
            if self.adjust_dragging:
                global_y = event.globalPos().y()
                # taskbar_feet_gap = 猫脚到任务栏顶部的距离（正值=脚在任务栏上方）
                avail_bottom = self.current_screen.topLeft().y() + self.screen_height
                settings.taskbar_feet_gap = int(avail_bottom - global_y)
                settings.compute_floor_offset(settings.current_screen)
                self.reset_size(setImg=False)
                self.update()
            return

        if Qt.LeftButton and self.is_follow_mouse:
            # 睡觉状态下，只能在 X 轴方向移动
            if settings.is_sleeping:
                new_pos = QPoint(event.globalPos().x() - self.mouse_drag_pos.x(), self.pos().y())
                self.move(new_pos)
                event.accept()
                return

            # 启动阶段，只能在 X 轴方向移动
            if settings.is_starting_up:
                new_pos = QPoint(event.globalPos().x() - self.mouse_drag_pos.x(), self.pos().y())
                self.move(new_pos)
                event.accept()
                return

            # 自娱自乐动画播放期间，只能在 X 轴方向移动
            if self.is_entertainment_playing:
                new_pos = QPoint(event.globalPos().x() - self.mouse_drag_pos.x(), self.pos().y())
                self.move(new_pos)
                event.accept()
                return

            # land 动画播放期间，只能在 X 轴方向移动（land_bounce 期间禁止）
            if self.is_land_anim_playing:
                if settings.bouncing:
                    event.accept()
                    return
                new_pos = QPoint(event.globalPos().x() - self.mouse_drag_pos.x(), self.pos().y())
                self.move(new_pos)
                event.accept()
                return

            self.move(event.globalPos() - self.mouse_drag_pos)

            self.mouse_moving = True
            self.setCursor(self.cursor_dragged)

            if settings.mouseposx3 == 0:
                
                settings.mouseposx1=QCursor.pos().x()
                settings.mouseposx2=settings.mouseposx1
                settings.mouseposx3=settings.mouseposx2
                settings.mouseposx4=settings.mouseposx3

                settings.mouseposy1=QCursor.pos().y()
                settings.mouseposy2=settings.mouseposy1
                settings.mouseposy3=settings.mouseposy2
                settings.mouseposy4=settings.mouseposy3
            else:
                #mouseposx5=mouseposx4
                settings.mouseposx4=settings.mouseposx3
                settings.mouseposx3=settings.mouseposx2
                settings.mouseposx2=settings.mouseposx1
                settings.mouseposx1=QCursor.pos().x()
                #mouseposy5=mouseposy4
                settings.mouseposy4=settings.mouseposy3
                settings.mouseposy3=settings.mouseposy2
                settings.mouseposy2=settings.mouseposy1
                settings.mouseposy1=QCursor.pos().y()

            if self.was_onfloor == 1:
                if settings.set_fall:
                    settings.onfloor=0
                settings.draging=1
                self.workers['Animation'].pause()
                # 只在第一次移动时触发拖拽动画
                if not self.drag_started:
                    self.drag_started = True
                    self.workers['Interaction'].start_interact('mousedrag')
            

            event.accept()
            #print(self.pos().x(), self.pos().y())

    def mouseReleaseEvent(self, event):
        """
        松开鼠标操作
        :param event:
        :return:
        """
        # 活跃区域编辑模式：结束拖拽
        if self._editing_active_rects and self._dragging_rect_idx >= 0:
            if event.button() == Qt.LeftButton:
                self._dragging_rect_idx = -1
                self._dragging_rect_offset = None
                self.setCursor(Qt.ArrowCursor)
                self._save_active_rects()  # 保存位置
                self.update()
            event.accept()
            return

        # 地面调整模式
        if self.adjusting_floor:
            if event.button() == Qt.LeftButton:
                self.adjust_dragging = False
                self.setCursor(Qt.SizeVerCursor)
            return

        if event.button()==Qt.LeftButton:

            # 睡觉状态下，松手只清除拖拽状态，不打断睡觉
            if settings.is_sleeping:
                self.is_follow_mouse = False
                self.setCursor(self.cursor_default)
                self.mouse_moving = False
                event.accept()
                return

            # 启动阶段，松手只清除拖拽状态
            if settings.is_starting_up:
                self.is_follow_mouse = False
                self.setCursor(self.cursor_default)
                self.mouse_moving = False
                event.accept()
                return

            self.is_follow_mouse = False
            self.setCursor(self.cursor_default)

            # 安全机制：如果动画已停止但标志位未重置，强制重置
            if not self.workers['Interaction'].interact:
                self.is_entertainment_playing = False
                self.is_land_anim_playing = False

            #print(self.mouse_moving, settings.onfloor)
            if self.was_onfloor == 1 and not self.mouse_moving:
                # 短促单击：触发 patpat，恢复状态
                settings.onfloor = 1
                settings.draging = 0
                # 自娱自乐或 land 动画播放期间，不恢复状态
                if not self.is_entertainment_playing and not self.is_land_anim_playing:
                    # 如果不在播放 patpat 动画，才重置图片和恢复动画
                    if self.workers['Interaction'].interact != 'patpat':
                        settings.current_img = self.pet_conf.default.images[0]
                        self.set_img()
                        self.workers['Animation'].resume()
                self.patpat()

            else:
                # land 动画期间，松手只清除拖拽状态，不触发掉落
                if self.is_land_anim_playing:
                    self.mouse_moving = False
                    event.accept()
                    return

                anim_area = QRect(self.pos() + QPoint(self.width()//2-self.label.width()//2,
                                                      self.height()-self.label.height()),
                                  QSize(self.label.width(), self.label.height()))
                intersected = self.current_screen.intersected(anim_area)
                area = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                if area > 0.5:
                    pass
                else:
                    for screen in settings.screens:
                        if screen.geometry() == self.current_screen:
                            continue
                        intersected = screen.geometry().intersected(anim_area)
                        area_tmp = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                        if area_tmp > 0.5:
                            self.switch_screen(screen)


                if settings.set_fall:
                    settings.onfloor=0
                    settings.draging=0
                    settings.drag_start_done=False
                    # 直接进入坠落阶段1（从 frame_start 开始，避免 0~17 帧空转）
                    settings.fall_frame = 18
                    settings.fall_direction = 1
                    settings.fall_tick = 0
                    settings.fall_phase = 'fall'
                    settings.fall_loop_frame = 123

                    settings.dragspeedx=(settings.mouseposx1-settings.mouseposx3)/2*settings.fixdragspeedx
                    settings.dragspeedy=(settings.mouseposy1-settings.mouseposy3)/2*settings.fixdragspeedy
                    settings.mouseposx1=settings.mouseposx3=0
                    settings.mouseposy1=settings.mouseposy3=0

                    if settings.dragspeedx > 0:
                        settings.fall_right = True
                    else:
                        settings.fall_right = False

                else:
                    settings.draging=0
                    self._move_customized(0,0)
                    settings.current_img = self.pet_conf.default.images[0]
                    self.set_img()
                    self.workers['Animation'].resume()
            self.mouse_moving = False


    def keyPressEvent(self, event):
        """
        键盘按键事件（测试用）
        A: 向左走（仅右半屏可用）
        D: 向右走（仅左半屏可用）
        S: 触发睡觉（测试用）
        空格: 触发跳跃（测试用）
        Q: 舔毛（测试用）
        E: 摇尾巴（测试用）
        R: 抓苍蝇（测试用）
        0: 触发拉屎（测试用，主键盘数字 0，不含小键盘）
        小键盘*: 触发feed_required气泡（测试用）
        """
        half = settings.screen_width / 2
        if event.key() == Qt.Key_A:
            if settings.pet_center_x >= half:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('animat', 'left_walk')
        elif event.key() == Qt.Key_D:
            if settings.pet_center_x < half:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('animat', 'right_walk')
        elif event.key() == Qt.Key_S:
            # S 键触发睡觉（测试用）
            if not settings.is_sleeping:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('sleep')
        elif event.key() == Qt.Key_Space:
            # 空格键触发跳跃（测试用）
            if not settings.is_sleeping and not settings.is_starting_up:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('animat', 'jump')
        elif event.key() == Qt.Key_Q:
            # Q 键触发舔毛（测试用）
            if not settings.is_sleeping and not settings.is_starting_up:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('animat', 'groom')
        elif event.key() == Qt.Key_E:
            # E 键触发摇尾巴（测试用）
            if not settings.is_sleeping and not settings.is_starting_up:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('animat', 'tailshake')
        elif event.key() == Qt.Key_R:
            # R 键触发抓苍蝇（测试用）
            if not settings.is_sleeping and not settings.is_starting_up:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('animat', 'flycatch')
        elif event.key() == Qt.Key_0 and not (event.modifiers() & Qt.KeypadModifier):
            # 主键盘 0 触发拉屎（测试用）；排除小键盘 0
            self._on_poop_trigger()
        elif event.key() == Qt.Key_Asterisk and event.modifiers() & Qt.KeypadModifier:
            # 小键盘* 触发feed_required气泡（测试用）
            self.bubble_manager.trigger_bubble('feed_required')
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """事件过滤器：调整模式下捕获全局按键，label 键盘事件转发到主窗口"""
        if self.adjusting_floor and event.type() == QEvent.KeyPress:
            self._handle_floor_key(event)
            return True
        if obj == self.label and event.type() == QEvent.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(obj, event)

    def _handle_floor_key(self, event):
        """处理调整模式下的按键"""
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        if event.key() == Qt.Key_Up:
            # 向上移动猫脚（增大与任务栏顶部的间距）
            settings.taskbar_feet_gap += step
            settings.compute_floor_offset(settings.current_screen)
            self.reset_size(setImg=False)
            self.update()
        elif event.key() == Qt.Key_Down:
            # 向下移动猫脚（减小与任务栏顶部的间距）
            settings.taskbar_feet_gap -= step
            settings.compute_floor_offset(settings.current_screen)
            self.reset_size(setImg=False)
            self.update()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            settings.save_taskbar_feet_gap(settings.taskbar_feet_gap)
            print(f"[OK] taskbar_feet_gap = {settings.taskbar_feet_gap}")
            self.adjusting_floor = False
            QApplication.instance().removeEventFilter(self)
            self.update()
        elif event.key() == Qt.Key_Escape:
            settings.taskbar_feet_gap = self._saved_feet_gap
            settings.compute_floor_offset(settings.current_screen)
            self.reset_size(setImg=False)
            self.adjusting_floor = False
            QApplication.instance().removeEventFilter(self)
            self.update()


    def _init_widget(self) -> None:
        """
        初始化窗体, 无边框半透明窗口
        :return:
        """
        if settings.on_top_hint:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        else:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.repaint()
        # 是否跟随鼠标
        self.is_follow_mouse = False
        self.mouse_drag_pos = self.pos()

    def ontop_update(self):
        if settings.on_top_hint:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        else:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
                
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.show()


    def _init_ui(self):
        # The Character ----------------------------------------------------------------------------
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.label.setFocusPolicy(Qt.StrongFocus)  # 允许接收键盘事件
        self.label.installEventFilter(self)
        #self.label.setStyleSheet("border : 2px solid blue")

        # system animations
        self.sys_src = _load_all_pic('sys')
        self.sys_conf = PetConfig.init_sys(self.sys_src) 
        # ------------------------------------------------------------------------------------------

        # Hover Timer --------------------------------------------------------
        self.status_frame = QFrame()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)

        # 番茄时钟
        h_box3 = QHBoxLayout()
        h_box3.setContentsMargins(0,0,0,0)
        h_box3.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.tomatoicon = QLabel(self)
        self.tomatoicon.setFixedSize(statbar_h,statbar_h)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/Tomato_icon.png'))
        self.tomatoicon.setScaledContents(True)
        self.tomatoicon.setPixmap(image)
        self.tomatoicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box3.addWidget(self.tomatoicon)
        self.tomato_time = RoundBarBase(fill_color="#ef4e50", parent=self) #QProgressBar(self, minimum=0, maximum=25, objectName='PetTM')
        self.tomato_time.setFormat('')
        self.tomato_time.setValue(25)
        self.tomato_time.setAlignment(Qt.AlignCenter)
        self.tomato_time.hide()
        self.tomatoicon.hide()
        h_box3.addWidget(self.tomato_time)

        # 专注时间
        h_box4 = QHBoxLayout()
        h_box4.setContentsMargins(0,status_margin,0,0)
        h_box4.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.focusicon = QLabel(self)
        self.focusicon.setFixedSize(statbar_h,statbar_h)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/Timer_icon.png'))
        self.focusicon.setScaledContents(True)
        self.focusicon.setPixmap(image)
        self.focusicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box4.addWidget(self.focusicon)
        self.focus_time = RoundBarBase(fill_color="#47c0d2", parent=self) #QProgressBar(self, minimum=0, maximum=0, objectName='PetFC')
        self.focus_time.setFormat('')
        self.focus_time.setValue(0)
        self.focus_time.setAlignment(Qt.AlignCenter)
        self.focus_time.hide()
        self.focusicon.hide()
        h_box4.addWidget(self.focus_time)

        vbox.addStretch()
        vbox.addLayout(h_box3)
        vbox.addLayout(h_box4)

        self.status_frame.setLayout(vbox)
        #self.status_frame.setStyleSheet("border : 2px solid blue")
        self.status_frame.setContentsMargins(0,0,0,0)
        #self.status_box.addWidget(self.status_frame)
        #self.status_frame.hide()
        # ------------------------------------------------------------

        #Layout_1 ----------------------------------------------------
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)

        self.petlayout = QVBoxLayout()
        self.petlayout.addWidget(self.status_frame)

        image_hbox = QHBoxLayout()
        image_hbox.setContentsMargins(0,0,0,0)
        image_hbox.addStretch()
        image_hbox.addWidget(self.label, Qt.AlignBottom | Qt.AlignHCenter)
        image_hbox.addStretch()

        self.petlayout.addLayout(image_hbox, Qt.AlignBottom | Qt.AlignHCenter)
        self.petlayout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.petlayout.setContentsMargins(0,0,0,0)
        self.layout.addLayout(self.petlayout, Qt.AlignBottom | Qt.AlignHCenter)
        # ------------------------------------------------------------

        self.setLayout(self.layout)
        # ------------------------------------------------------------


        # 初始化背包
        #self.items_data = ItemData(HUNGERSTR=settings.HUNGERSTR, FAVORSTR=settings.FAVORSTR)
        settings.items_data = ItemData(HUNGERSTR=settings.HUNGERSTR, FAVORSTR=settings.FAVORSTR)
        self._init_Inventory()
        #self.showing_comp = 0

        # 客制化光标
        self.cursor_user = self.cursor()
        system_cursor_size = 32
        if os.path.exists(os.path.join(basedir, 'res/icons/cursor_default.png')):
            self.cursor_default = QCursor(QPixmap("res/icons/cursor_default.png").scaled(system_cursor_size, system_cursor_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cursor_default = self.cursor_user
        if os.path.exists(os.path.join(basedir, 'res/icons/cursor_clicked.png')):
            self.cursor_clicked = QCursor(QPixmap("res/icons/cursor_clicked.png").scaled(system_cursor_size, system_cursor_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cursor_clicked = self.cursor_user
        if os.path.exists(os.path.join(basedir, 'res/icons/cursor_dragged.png')):
            self.cursor_dragged = QCursor(QPixmap("res/icons/cursor_dragged.png").scaled(system_cursor_size, system_cursor_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cursor_dragged = self.cursor_user

    def _init_Inventory(self):
        from DyberPet.extra_windows import Inventory
        self.items_data = ItemData(HUNGERSTR=settings.HUNGERSTR, FAVORSTR=settings.FAVORSTR)
        self.inventory_window = Inventory(self.items_data)
        self.inventory_window.close_inventory.connect(self.show_inventory)
        self.inventory_window.use_item_inven.connect(self.use_item)
        self.inventory_window.item_note.connect(self.register_notification)
        self.inventory_window.item_anim.connect(self.item_drop_anim)
        self.addCoins.connect(self.inventory_window.addCoins)
        self.addItem_toInven.connect(self.inventory_window.add_items)
        self.fvlvl_changed_main_inve.connect(self.inventory_window.fvchange)


    def _set_menu(self, pets=()):
        """
        Option Menu
        """
        #menu = RoundMenu(self.tr("More Options"), self)
        #menu.setIcon(FIF.MENU)

        # Select action
        self.act_menu = RoundMenu(self.tr("Select Action"))
        self.act_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/jump.svg')))

        if platform == 'win32':
            self.start_follow_mouse = Action(QIcon(os.path.join(basedir,'res/icons/cursor.svg')),
                                            self.tr('Follow Cursor'),
                                            triggered = self.follow_mouse_act)
            self.act_menu.addAction(self.start_follow_mouse)
            self.act_menu.addSeparator()

        acts_config = settings.act_data.allAct_params[settings.petname]
        self.select_acts = [ _build_act(k, self.act_menu, self._show_act) for k,v in acts_config.items() if v['unlocked']]
        if self.select_acts:
            self.act_menu.addActions(self.select_acts)

        #menu.addMenu(self.act_menu)

        # Change Character
        self.change_menu = RoundMenu(self.tr("Change Character"))
        self.change_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/system/character.svg')))
        change_acts = [_build_act(name, self.change_menu, self._change_pet) for name in pets if name != self.curr_pet_name]
        self.change_menu.addActions(change_acts)

        # Drop on/off
        '''
        if settings.set_fall == 1:
            self.switch_fall = Action(QIcon(os.path.join(basedir,'res/icons/on.svg')),
                                      self.tr('Allow Drop'), menu)
        else:
            self.switch_fall = Action(QIcon(os.path.join(basedir,'res/icons/off.svg')),
                                      self.tr("Don't Drop"), menu)
        self.switch_fall.triggered.connect(self.fall_onoff)
        '''
        #menu.addAction(self.switch_fall)

        
        # Visit website - feature deprecated
        '''
        web_file = os.path.join(basedir, 'res/role/sys/webs.json')
        if os.path.isfile(web_file):
            web_dict = json.load(open(web_file, 'r', encoding='UTF-8'))

            self.web_menu = RoundMenu(self.tr("Website"), menu)
            self.web_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/website.svg')))

            web_acts = [_build_act_param(name, web_dict[name], self.web_menu, self.open_web) for name in web_dict]
            self.web_menu.addActions(web_acts)
            menu.addMenu(self.web_menu)
        '''
            
        #menu.addSeparator()
        #self.menu = menu
        #self.menu.addAction(Action(FIF.POWER_BUTTON, self.tr('Exit'), triggered=self.quit))


    def _update_fvlock(self):

        # Update selectable animations
        acts_config = settings.act_data.allAct_params[settings.petname]
        for act_name, act_conf in acts_config.items():
            if act_conf['unlocked']:
                if act_name not in [acti.text() for acti in self.select_acts]:
                    new_act = _build_act(act_name, self.act_menu, self._show_act)
                    self.act_menu.addAction(new_act)
                    self.select_acts.append(new_act)
            else:
                if act_name in [acti.text() for acti in self.select_acts]:
                    act_index = [acti.text() for acti in self.select_acts].index(act_name)
                    self.act_menu.removeAction(self.select_acts[act_index])
                    self.select_acts.remove(self.select_acts[act_index])


    def _set_Statusmenu(self):

        # Character Name
        self.statusTitle = QWidget()
        hboxTitle = QHBoxLayout(self.statusTitle)
        hboxTitle.setContentsMargins(0,0,0,0)
        self.nameLabel = CaptionLabel(self.curr_pet_name, self)
        setFont(self.nameLabel, 14, QFont.DemiBold)
        #self.nameLabel.setFixedWidth(75)

        daysText = self.tr(" (Fed for ") + str(settings.pet_data.days) +\
                   self.tr(" days)")
        self.daysLabel = CaptionLabel(daysText, self)
        setFont(self.daysLabel, 14, QFont.Normal)

        hboxTitle.addStretch(1)
        hboxTitle.addWidget(self.nameLabel, Qt.AlignLeft | Qt.AlignVCenter)
        hboxTitle.addStretch(1)
        hboxTitle.addWidget(self.daysLabel, Qt.AlignRight | Qt.AlignVCenter)
        #hboxTitle.addStretch(1)
        self.statusTitle.setFixedSize(225, 25)

        # # Status Title
        # hp_tier = settings.pet_data.hp_tier
        # statusText = self.tr("Status: ") + f"{settings.TIER_NAMES[hp_tier]}"
        # self.statLabel = CaptionLabel(statusText, self)
        # setFont(self.statLabel, 14, QFont.Normal)

        # Level Badge
        lvlWidget = QWidget()
        h_box0 = QHBoxLayout(lvlWidget)
        h_box0.setContentsMargins(0,0,0,0)
        h_box0.setSpacing(5)
        h_box0.setAlignment(Qt.AlignCenter)
        lvlLable = CaptionLabel(self.tr("Level"))
        setFont(lvlLable, 13, QFont.Normal)
        lvlLable.adjustSize()
        lvlLable.setFixedSize(43, lvlLable.height())
        self.lvl_badge = LevelBadge(settings.pet_data.fv_lvl)
        h_box0.addWidget(lvlLable)
        #h_box0.addStretch(1)
        h_box0.addWidget(self.lvl_badge)
        h_box0.addStretch(1)
        lvlWidget.setFixedSize(250, 25)

        # Hunger status
        hpWidget = QWidget()
        h_box1 = QHBoxLayout(hpWidget)
        h_box1.setContentsMargins(0,0,0,0) #status_margin,0,0)
        h_box1.setSpacing(5)
        h_box1.setAlignment(Qt.AlignCenter) #AlignBottom | Qt.AlignHCenter)
        hpLable = CaptionLabel(self.tr("Satiety"))
        setFont(hpLable, 13, QFont.Normal)
        hpLable.adjustSize()
        hpLable.setFixedSize(43, hpLable.height())
        self.hpicon = QLabel(self)
        self.hpicon.setFixedSize(icons_wh,icons_wh)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/HP_icon.png'))
        self.hpicon.setScaledContents(True)
        self.hpicon.setPixmap(image)
        self.hpicon.setAlignment(Qt.AlignCenter) #AlignBottom | Qt.AlignRight)
        h_box1.addWidget(hpLable)
        h_box1.addStretch(1)
        h_box1.addWidget(self.hpicon)
        #h_box1.addStretch(1)
        self.pet_hp = DP_HpBar(self, minimum=0, maximum=100, objectName='PetHP')
        self.pet_hp.hp_updated.connect(self._hp_updated)
        h_box1.addWidget(self.pet_hp)
        h_box1.addStretch(1)

        # favor status
        fvWidget = QWidget()
        h_box2 = QHBoxLayout(fvWidget)
        h_box2.setContentsMargins(0,0,0,0) #status_margin,0,0)
        h_box2.setSpacing(5)
        h_box2.setAlignment(Qt.AlignCenter) #Qt.AlignBottom | Qt.AlignHCenter)
        fvLable = CaptionLabel(self.tr("Favor"))
        setFont(fvLable, 13, QFont.Normal)
        fvLable.adjustSize()
        fvLable.setFixedSize(43, fvLable.height())
        self.emicon = QLabel(self)
        self.emicon.setFixedSize(icons_wh,icons_wh)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/Fv_icon.png'))
        self.emicon.setScaledContents(True)
        self.emicon.setPixmap(image)
        #self.emicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box2.addWidget(fvLable, Qt.AlignHCenter | Qt.AlignTop)
        h_box2.addStretch(1)
        h_box2.addWidget(self.emicon)
        self.pet_fv = DP_FvBar(self, minimum=0, maximum=100, objectName='PetEM')
        self.pet_fv.fv_updated.connect(self._fv_updated)

        self.pet_hp.hptier_changed.connect(self.hpchange)
        self.pet_fv.fvlvl_changed.connect(self.fvchange)
        h_box2.addWidget(self.pet_fv)
        h_box2.addStretch(1)

        self.pet_hp.init_HP(settings.pet_data.hp, sys_hp_interval) #2)
        self.pet_fv.init_FV(settings.pet_data.fv, settings.pet_data.fv_lvl)
        self._prev_fv_lvl = settings.pet_data.fv_lvl
        self.pet_hp.setFixedSize(145, 15)
        self.pet_fv.setFixedSize(145, 15)

        # 好感度提示
        fvWidget.setToolTip(self.tr('提高亲密度会解锁更多动作哦！'))

        # Status Widget
        self.statusWidget = QWidget()
        StatVbox = QVBoxLayout(self.statusWidget)
        StatVbox.setContentsMargins(0,5,30,10)
        StatVbox.setSpacing(5)
        
        #StatVbox.addWidget(self.statusTitle, Qt.AlignVCenter)
        StatVbox.addStretch(1)
        #StatVbox.addWidget(self.daysLabel)
        StatVbox.addWidget(hpWidget, Qt.AlignLeft | Qt.AlignVCenter)
        StatVbox.addWidget(fvWidget, Qt.AlignLeft | Qt.AlignVCenter)
        StatVbox.addStretch(1)
        #statusWidget.setLayout(StatVbox)
        #statusWidget.setContentsMargins(0,0,0,0)
        self.statusWidget.setFixedSize(250, 70)
        
        self.StatMenu = RoundMenu(parent=self)

        # 睡觉状态下只显示唤醒、隐身和退出选项
        if settings.is_sleeping:
            pet_name = settings.petname
            wake_action = QAction(self.tr(f"唤醒{pet_name}"), self)
            wake_action.triggered.connect(self.wake_up_pet)
            self.StatMenu.addAction(wake_action)
            if platform == 'win32':
                ct_action = QAction(self.tr('隐身模式'), self)
                ct_action.setCheckable(True)
                ct_action.setChecked(settings.click_through_mode)
                ct_action.triggered.connect(self.toggle_click_through)
                self.StatMenu.addAction(ct_action)
            self.StatMenu.addSeparator()
            self.StatMenu.addActions([
                Action(FIF.POWER_BUTTON, self.tr('Exit'), triggered=self.quit),
            ])
        else:
            self.StatMenu.addWidget(self.statusTitle, selectable=False)
            self.StatMenu.addSeparator()
            #self.StatMenu.addWidget(self.statLabel, selectable=False)
            self.StatMenu.addWidget(lvlWidget, selectable=False)
            self.StatMenu.addWidget(self.statusWidget, selectable=False)
            #self.StatMenu.addWidget(fvbar, selectable=False)
            self.StatMenu.addSeparator()

            #self.StatMenu.addMenu(self.menu)

            # 角色面板子菜单
            dashboard_menu = RoundMenu(self.tr('角色面板'), self.StatMenu)
            dashboard_menu.setIcon(QIcon(os.path.join(basedir, 'res/icons/dashboard.svg')))
            dashboard_menu.addActions([
                Action(QIcon(os.path.join(basedir, 'res/icons/Dashboard/progress.svg')), self.tr('状态'), triggered=lambda: self._show_dashboard_panel('status')),
                Action(QIcon(os.path.join(basedir, 'res/icons/Dashboard/backpack.svg')), self.tr('背包'), triggered=lambda: self._show_dashboard_panel('backpack')),
                Action(QIcon(os.path.join(basedir, 'res/icons/Dashboard/shop.svg')), self.tr('商店'), triggered=lambda: self._show_dashboard_panel('shop')),
                Action(QIcon(os.path.join(basedir, 'res/icons/Dashboard/task.svg')), self.tr('每日任务'), triggered=lambda: self._show_dashboard_panel('task')),
            ])
            self.StatMenu.addMenu(dashboard_menu)

            self.StatMenu.addActions([
                Action(QIcon(os.path.join(basedir,'res/icons/SystemPanel.png')), self.tr('系统设置'), triggered=self._show_controlPanel),
            ])
            self.StatMenu.addSeparator()

            if len(self.pets) > 1:
                self.StatMenu.addMenu(self.change_menu)
                self.StatMenu.addSeparator()

            # 穿透模式开关
            if platform == 'win32':
                ct_action = QAction(self.tr('隐身模式'), self)
                ct_action.setCheckable(True)
                ct_action.setChecked(settings.click_through_mode)
                ct_action.triggered.connect(self.toggle_click_through)
                self.StatMenu.addAction(ct_action)

                # 编辑活跃区域
                # 编辑活跃区域（已隐藏，通过代码直接调用 _toggle_edit_active_rects）
                # self._edit_active_rects_action = QAction(self.tr('编辑活跃区域'), self)
                # self._edit_active_rects_action.setCheckable(True)
                # self._edit_active_rects_action.setChecked(getattr(self, '_editing_active_rects', False))
                # self._edit_active_rects_action.triggered.connect(self._toggle_edit_active_rects)
                # self.StatMenu.addAction(self._edit_active_rects_action)
                self.StatMenu.addSeparator()

            # Exit
            self.StatMenu.addActions([
                Action(FIF.POWER_BUTTON, self.tr('Exit'), triggered=self.quit),
            ])


    # def _update_statusTitle(self, hp_tier):
    #     statusText = self.tr("Status: ") + f"{settings.TIER_NAMES[hp_tier]}"
    #     self.statLabel.setText(statusText)


    def _show_Staus_menu(self):
        """
        展示右键菜单
        :return:
        """
        # 重新构建菜单以反映当前状态
        self._set_Statusmenu()
        # 光标位置弹出菜单
        self.StatMenu.popup(QCursor.pos()-QPoint(0, self.StatMenu.height()-20))

    def _toggle_floor_adjust(self):
        """切换地面位置调整模式"""
        if not self.adjusting_floor:
            self.adjusting_floor = True
            self.adjust_dragging = False
            self._saved_feet_gap = settings.taskbar_feet_gap
            QApplication.instance().installEventFilter(self)
            self.setCursor(Qt.SizeVerCursor)
            print("[调整模式] 拖拽红线/方向键调整，Enter 保存，Esc 取消")
        else:
            self.adjusting_floor = False
            QApplication.instance().removeEventFilter(self)
            self.update()

    def wake_up_pet(self):
        """唤醒睡觉的猫"""
        if not settings.is_sleeping:
            return

        # 通过 Interaction worker 唤醒
        self.workers['Interaction'].wake_up()

    def _add_pet(self, pet_name: str):
        pet_acc = {'name':'pet', 'pet_name':pet_name}
        #self.setup_acc.emit(pet_acc, int(self.current_screen.topLeft().x() + random.uniform(0.4,0.7)*self.screen_width), self.pos().y())
        # To accomodate any subpet that always follows main, change the position to top middle pos of pet
        self.setup_acc.emit(pet_acc, int( self.pos().x() + self.width()/2 ), self.pos().y(), 0)

    def open_web(self, web_address):
        try:
            webbrowser.open(web_address)
        except:
            return
    '''
    def freeze_pet(self):
        """stop all thread, function for save import"""
        self.stop_thread('Animation')
        self.stop_thread('Interaction')
        self.stop_thread('Scheduler')
        #del self.threads, self.workers
    '''
    
    def refresh_pet(self):
        # stop animation thread and start again
        self.stop_thread('Animation')
        self.stop_thread('Interaction')

        # Change status
        self.pet_hp.init_HP(settings.pet_data.hp, sys_hp_interval) #2)
        self.pet_fv.init_FV(settings.pet_data.fv, settings.pet_data.fv_lvl)
        self._prev_fv_lvl = settings.pet_data.fv_lvl

        # Change status related behavior
        #self.workers['Animation'].hpchange(settings.pet_data.hp_tier, None)
        #self.workers['Animation'].fvchange(settings.pet_data.fv_lvl)

        # Animation config data update
        settings.act_data._pet_refreshed(settings.pet_data.fv_lvl)
        self.refresh_acts.emit()

        # cancel default animation if any
        '''
        defaul_act = settings.defaultAct[self.curr_pet_name]
        if defaul_act is not None:
            self._set_defaultAct(self, defaul_act)
        self._update_fvlock()
        # add default animation back
        if defaul_act in [acti.text() for acti in self.defaultAct_menu.actions()]:
            self._set_defaultAct(self, defaul_act)
        '''

        # Update BackPack
        #self._init_Inventory()
        self.refresh_bag.emit()
        self._set_menu(self.pets)
        self._set_Statusmenu()
        self._set_tray()

        # restart animation and interaction
        self.runAnimation()
        self.runInteraction()
        
        # restore data system
        settings.pet_data.frozen_data = False

        # Compensate items if any
        self._setup_compensate()
    

    def _change_pet(self, pet_name: str) -> None:
        """
        改变宠物
        :param pet_name: 宠物名称
        :return:
        """
        if self.curr_pet_name == pet_name:
            return
        
        # close all accessory widgets (subpet, accessory animation, etc.)
        self.close_all_accs.emit()

        # stop animation thread and start again
        self.stop_thread('Animation')
        self.stop_thread('Interaction')

        # reload pet data
        settings.pet_data._change_pet(pet_name)

        # reload new pet
        self.init_conf(pet_name)

        # Change status
        self.pet_hp.init_HP(settings.pet_data.hp, sys_hp_interval) #2)
        self.pet_fv.init_FV(settings.pet_data.fv, settings.pet_data.fv_lvl)
        self._prev_fv_lvl = settings.pet_data.fv_lvl

        # Change status related behavior
        #self.workers['Animation'].hpchange(settings.pet_data.hp_tier, None)
        #self.workers['Animation'].fvchange(settings.pet_data.fv_lvl)

        # Update Backpack
        #self._init_Inventory()
        self.refresh_bag.emit()
        self.refresh_acts.emit()

        self.change_note.emit()
        self.repaint()
        self._setup_ui()

        self.runAnimation()
        self.runInteraction()

        self.workers['Scheduler'].send_greeting()
        # Compensate items if any
        self._setup_compensate()
        # Due to Qt internal behavior, sometimes has to manually correct the position back
        pos_x, pos_y = self.pos().x(), self.pos().y()
        QTimer.singleShot(10, lambda: self.move(pos_x, pos_y))

    def init_conf(self, pet_name: str) -> None:
        """
        初始化宠物窗口配置
        :param pet_name: 宠物名称
        :return:
        """
        import time as _time
        self.curr_pet_name = pet_name
        settings.petname = pet_name
        settings.tunable_scale = settings.scale_dict.get(pet_name, 1.0)
        t0 = _time.time()
        pic_dict = _load_all_pic(pet_name)
        print(f"[启动] 图片加载: {_time.time()-t0:.2f}s ({len(pic_dict)} 张)")
        t1 = _time.time()
        self.pet_conf = PetConfig.init_config(self.curr_pet_name, pic_dict) #settings.size_factor)
        print(f"[启动] PetConfig: {_time.time()-t1:.2f}s")
        
        self.margin_value = 0 #0.1 * max(self.pet_conf.width, self.pet_conf.height) # 用于将widgets调整到合适的大小
        # Add customized animation
        settings.act_data.init_actData(pet_name, settings.pet_data.hp_tier, settings.pet_data.fv_lvl)
        self._load_custom_anim()
        settings.pet_conf = self.pet_conf

        # Update coin name and image according to the pet config
        if self.pet_conf.coin_config:
            coin_config = self.pet_conf.coin_config.copy()
            if not coin_config['image']:
                coin_config['image'] = settings.items_data.default_coin['image']
            settings.items_data.coin = coin_config
        else:
            settings.items_data.coin = settings.items_data.default_coin.copy()

        # Init bubble behavior manager
        self.bubble_manager = BubbleManager()
        self.bubble_manager.register_bubble.connect(self.register_bubbleText)

        # 加载活跃区域配置
        self._load_active_rects(pet_name)

        self._set_menu(self.pets)
        self._set_Statusmenu()
        self._set_tray()

        # 提前计算默认动作的脚底边距，让 _setup_ui 里的 reset_size 首次定位就准确，
        # 避免窗口先出现在错误高度再瞬间跳到正确位置。
        self._compute_pet_feet_bottom_pad()


    def _compute_pet_feet_bottom_pad(self):
        """加载默认动作首帧，计算当前缩放下的脚底透明边距与 floor_y_offset。"""
        from PySide6.QtGui import QPixmap as _QPixmap
        import glob as _glob, re as _re, os as _os, json as _json
        _img_dir = _os.path.join(basedir, 'res/role/{}/action'.format(self.curr_pet_name))
        _act_conf_path = _os.path.join(basedir, 'res/role/{}/act_conf.json'.format(self.curr_pet_name))
        _act_conf = _json.load(open(_act_conf_path, 'r', encoding='UTF-8'))
        _default_prefix = _act_conf.get(self.pet_conf.default.act_name, {}).get('images', 'stand')
        _default_files = _glob.glob(f'{_img_dir}/{_default_prefix}_*.png')
        if _default_files:
            _default_pattern = _re.compile(rf'^{_re.escape(_default_prefix)}_(\d+)\.png$')
            _default_idx = min([_default_pattern.match(_os.path.basename(f)).group(1) for f in _default_files if _default_pattern.match(_os.path.basename(f))], key=lambda x: int(x))
            _default_pixmap = _QPixmap()
            _default_pixmap.load(_os.path.join(_img_dir, f'{_default_prefix}_{_default_idx}.png'))
            raw_bottom_pad = settings.compute_pet_feet_bottom_pad(_default_pixmap)
            settings.pet_feet_bottom_pad = int(raw_bottom_pad * settings.tunable_scale)
        else:
            settings.pet_feet_bottom_pad = 0
        settings.compute_floor_offset(settings.current_screen)


    def _load_custom_anim(self):
        acts_conf = settings.act_data.allAct_params[settings.petname]
        for act_name, act_conf in acts_conf.items():
            if act_conf['act_type'] == 'customized' and act_name not in self.pet_conf.custom_act:
                # generate new Act objects for cutomized animation
                acts = []
                for act in act_conf.get('act_list', []):
                    acts.append(self._prepare_act_obj(act))
                accs = []
                for act in act_conf.get('acc_list', []):
                    accs.append(self._prepare_act_obj(act))
                # save the new animation config with same format as self.pet_conf.accessory_act
                self.pet_conf.custom_act[act_name] = {"act_list": acts,
                                                      "acc_list": accs,
                                                      "anchor": act_conf.get('anchor_list',[]),
                                                      "act_type": act_conf['status_type']}

    def _prepare_act_obj(self, actobj):
        
        # if this act is a skipping act e.g. [60, 20]
        if len(actobj) == 2:
            return actobj
        else:
            act_conf_name = actobj[0]
            act_idx_start = actobj[1]
            act_idx_end = actobj[2]+1
            act_repeat_num = actobj[3]
            new_actobj = self.pet_conf.act_dict[act_conf_name].customized_copy(act_idx_start, act_idx_end, act_repeat_num)
            return new_actobj

    def updateList(self):
        self.workers['Animation'].update_prob()

    def _addNewAct(self, act_name):
        acts_config = settings.act_data.allAct_params[settings.petname]
        act_conf = acts_config[act_name]

        # Add to pet_conf
        acts = []
        for act in act_conf.get('act_list', []):
            acts.append(self._prepare_act_obj(act))
        accs = []
        for act in act_conf.get('acc_list', []):
            accs.append(self._prepare_act_obj(act))
        self.pet_conf.custom_act[act_name] = {"act_list": acts,
                                                "acc_list": accs,
                                                "anchor": act_conf.get('anchor_list',[]),
                                                "act_type": act_conf['status_type']}
        # update random action prob
        self.updateList()
        # Add to menu
        if act_conf['unlocked']:
            select_act = _build_act(act_name, self.act_menu, self._show_act)
            self.select_acts.append(select_act)
            self.act_menu.addAction(select_act)
    
    def _deleteAct(self, act_name):
        # delete from self.pet_config
        self.pet_conf.custom_act.pop(act_name)
        # update random action prob
        self.updateList()

        # delete from menu
        act_index = [acti.text() for acti in self.select_acts].index(act_name)
        self.act_menu.removeAction(self.select_acts[act_index])
        self.select_acts.remove(self.select_acts[act_index])


    def _setup_ui(self):

        #bar_width = int(max(100*settings.size_factor, 0.5*self.pet_conf.width))
        bar_width = int(max(100, 0.5*self.pet_conf.width))
        bar_width = int(min(200, bar_width))
        self.tomato_time.setFixedSize(bar_width, statbar_h-5)
        self.focus_time.setFixedSize(bar_width, statbar_h-5)

        self.reset_size(setImg=False)

        settings.previous_img = settings.current_img
        # 启动首帧显示 fallasleep_wake 第一帧，与紧随其后的启动醒来动画衔接
        _wake_act = self.pet_conf.act_dict.get('fallasleep_wake')
        _first_pixmap = _wake_act.images[0] if _wake_act else self.pet_conf.default.images[0]
        if settings.tunable_scale != 1:
            _first_pixmap = _first_pixmap.scaled(int(_first_pixmap.width() * settings.tunable_scale),
                                                  int(_first_pixmap.height() * settings.tunable_scale),
                                                  aspectMode=Qt.KeepAspectRatio,
                                                  mode=Qt.SmoothTransformation)
        settings.current_img = _first_pixmap
        settings.previous_anchor = [0, 0]
        settings.current_anchor = [int(i*settings.tunable_scale) for i in self.pet_conf.default.anchor]
        self.set_img()
        self.border = self.pet_conf.width/2

        # 预加载 fallasleep_wake（启动醒来动画必需）
        wake_act = self.pet_conf.act_dict.get('fallasleep_wake')
        if wake_act is not None:
            _ = wake_act.images

        # 启动后台预加载：醒来动画播放期间加载其余全部动作（由 runAnimation 中的 QTimer 触发）

        
        # 初始位置
        #screen_geo = QDesktopWidget().availableGeometry() #QDesktopWidget().screenGeometry()
        screen_width = self.screen_width #screen_geo.width()
        work_height = self.screen_height #screen_geo.height()
        x = self.current_screen.topLeft().x() + int(screen_width*0.8) - self.width()//2
        y = self.current_screen.topLeft().y() + work_height - self.height() - settings.floor_y_offset
        self.move(x,y)
        settings.pet_center_x = x + self.width() // 2
        pass
        if settings.previous_anchor != settings.current_anchor:
            self.move(self.pos().x() - settings.previous_anchor[0] + settings.current_anchor[0],
                      self.pos().y() - settings.previous_anchor[1] + settings.current_anchor[1])
            #self.move(self.pos().x()-settings.previous_anchor[0]*settings.tunable_scale+self.current_anchor[0]*settings.tunable_scale,
            #          self.pos().y()-settings.previous_anchor[1]*settings.tunable_scale+settings.current_anchor[1]*settings.tunable_scale)

    '''
    def eventFilter(self, object, event):
        return
    
        if event.type() == QEvent.Enter:
            self.status_frame.show()
            return True
        elif event.type() == QEvent.Leave:
            self.status_frame.hide()
        return False
    '''

    def _set_tray(self) -> None:
        """
        设置最小化托盘
        :return:
        """
        if self.tray is None:
            self.tray = SystemTray(self.StatMenu, self) #QSystemTrayIcon(self)
            self.tray.setIcon(QIcon(os.path.join(basedir, 'res/icons/icon.png')))
            self.tray.setToolTip('六一桌宠')
            self.tray.show()
        else:
            self.tray.setMenu(self.StatMenu)
            self.tray.show()

    def reset_size(self, setImg=True):
        #self.setFixedSize((max(self.pet_hp.width()+statbar_h,self.pet_conf.width)+self.margin_value)*max(1.0,settings.tunable_scale),
        #                  (self.margin_value+4*statbar_h+self.pet_conf.height)*max(1.0, settings.tunable_scale))
        self.setFixedSize( int(max(self.tomato_time.width()+statbar_h,self.pet_conf.width*settings.tunable_scale)),
                           int(2*statbar_h+self.pet_conf.height*settings.tunable_scale)
                         )

        #self.label.setFixedWidth(self.width())

        # 初始位置
        #screen_geo = QDesktopWidget().availableGeometry() #QDesktopWidget().screenGeometry()
        screen_width = self.screen_width #screen_geo.width()
        work_height = self.screen_height #screen_geo.height()
        x = self.pos().x() + settings.current_anchor[0]
        if settings.set_fall:
            y = self.current_screen.topLeft().y() + work_height-self.height()+settings.current_anchor[1]-settings.floor_y_offset
        else:
            y = self.pos().y() + settings.current_anchor[1]
        # make sure that for all stand png, png bottom is the ground
        #self.floor_pos = work_height-self.height()
        self.floor_pos = self.current_screen.topLeft().y() + work_height - self.height() - settings.floor_y_offset
        self.move(x,y)
        settings.pet_center_x = self.pos().x() + self.width() // 2
        self.move_sig.emit(self.pos().x()+self.width()//2, self.pos().y()+self.height())

        if setImg:
            self.set_img()

    def set_img(self): #, img: QImage) -> None:
        """
        为窗体设置图片
        :param img: 图片
        :return:
        """
        #print(settings.previous_anchor, settings.current_anchor)
        if settings.previous_anchor != settings.current_anchor:
            self.move(self.pos().x()-settings.previous_anchor[0]+settings.current_anchor[0],
                      self.pos().y()-settings.previous_anchor[1]+settings.current_anchor[1])

        width_tmp = int(settings.current_img.width()*settings.tunable_scale)
        height_tmp = int(settings.current_img.height()*settings.tunable_scale)

        # HighDPI-compatible scaling solution
        # self.label.setScaledContents(True)
        self.label.setFixedSize(width_tmp, height_tmp)
        self.label.setPixmap(settings.current_img) #QPixmap.fromImage(settings.current_img))
        # previous scaling soluton
        #self.label.resize(width_tmp, height_tmp)
        #self.label.setPixmap(QPixmap.fromImage(settings.current_img.scaled(width_tmp, height_tmp,
        #                                                                 aspectMode=Qt.KeepAspectRatio,
        #                                                                 mode=Qt.SmoothTransformation)))
        self.image = settings.current_img

    def _compensate_rewards(self):
        self.compensate_rewards.emit()

    def register_notification(self, note_type, message):
        self.setup_notification.emit(note_type, message)


    def register_bubbleText(self, bubble_dict:dict):
        self.setup_bubbleText.emit(bubble_dict, self.pos().x()+self.width()//2, self.pos().y()+self.height())

    def _process_greeting_mssg(self, bubble_dict:dict):
        # 穿透模式下禁用所有气泡
        if settings.click_through_mode:
            return

        if bubble_dict.pop('_no_usertag', False):
            if settings.bubble_on:
                self.bubble_manager.register_bubble.emit(bubble_dict)
        else:
            self.bubble_manager.add_usertag(bubble_dict, 'end', send=True)

    def register_accessory(self, accs):
        self.setup_acc.emit(accs, self.pos().x()+self.width()//2, self.pos().y()+self.height(), 0)


    def _change_status(self, status, change_value, from_mod='Scheduler', send_note=False):
        # Check system status
        if from_mod == 'Scheduler' and is_system_locked() and settings.auto_lock:
            pass
            return
        if status not in ['hp','fv']:
            return
        elif status == 'hp':
            
            diff = self.pet_hp.updateValue(change_value, from_mod)

        elif status == 'fv':
            
            diff = self.pet_fv.updateValue(change_value, from_mod)

        if send_note:

            if diff > 0:
                diff = '+%s'%diff
            elif diff < 0:
                diff = str(diff)
            else:
                return
            if status == 'hp':
                message = self.tr('Satiety') + " " f'{diff}'
            else:
                message = self.tr('Favorability') + " " f'{diff}' #'好感度 %s'%diff
            self.register_notification('status_%s'%status, message)
        
        # Periodically triggered events
        if status == 'hp' and from_mod == 'Scheduler': # avoid being called in both hp and fv
            # Random Bubble
            if random.uniform(0, 1) < settings.PP_BUBBLE:
                self.bubble_manager.trigger_scheduled()

            # Auto-Feed
            if settings.pet_data.hp <= settings.AUTOFEED_THRESHOLD*settings.HP_INTERVAL:
                self.autofeed.emit()

    def _on_poop_trigger(self):
        """Scheduler 触发拉屎，从猫当前位置创建 PoopWidget"""
        from DyberPet.Poop import PoopWidget
        start_x = self.pos().x() + self.width() // 2
        start_y = self.pos().y() + self.height() // 3
        # 猫视觉底部 = 窗口Y + statbar高度 + label实际高度
        statbar_h = int(2 * settings.tunable_scale)
        cat_bottom_y = self.pos().y() + statbar_h + self.label.height()
        poop = PoopWidget(start_x, start_y, cat_bottom_y=cat_bottom_y)
        poop.poop_clicked.connect(self._on_poop_clicked)
        self.poop_list.append(poop)
        # 右下角通知
        self.register_notification(
            'poop',
            f'{settings.petname}拉屎啦！点击清理获得亲密度'
        )
        # 确保焦点回到猫窗口，不阻断键盘事件
        self.activateWindow()
        self.setFocus()

    def _on_poop_clicked(self, poop_id):
        """用户点击消除屎，增加亲密度"""
        # 直接增加 FV 并通知
        self._change_status('fv', settings.POOP_FV_REWARD, 'inventory', False)
        self.register_notification(
            'poop',
            f'清理便便 +{settings.POOP_FV_REWARD} 好感度'
        )
        # 从列表移除
        self.poop_list = [p for p in self.poop_list if p.poop_id != poop_id]

    def _hp_updated(self, hp):
        self.hp_updated.emit(hp)

    def _fv_updated(self, fv, fv_lvl):
        self.fv_updated.emit(fv, fv_lvl)


    def _change_time(self, status, timeleft):
        if status not in ['tomato','tomato_start','tomato_rest','tomato_end',
                          'focus_start','focus','focus_end','tomato_cencel','focus_cancel']:
            return

        if status in ['tomato','tomato_rest','tomato_end','focus','focus_end']:
            self.taskUI_Timer_update.emit()

        if status == 'tomato_start':
            self.tomato_time.setMaximum(25)
            self.tomato_time.setValue(timeleft)
            self.tomato_time.setFormat('%s min'%(int(timeleft)))
            #self.tomato_window.newTomato()
        elif status == 'tomato_rest':
            self.tomato_time.setMaximum(5)
            self.tomato_time.setValue(timeleft)
            self.tomato_time.setFormat('%s min'%(int(timeleft)))
            self.single_pomo_done.emit()
        elif status == 'tomato':
            self.tomato_time.setValue(timeleft)
            self.tomato_time.setFormat('%s min'%(int(timeleft)))
        elif status == 'tomato_end':
            self.tomato_time.setValue(0)
            self.tomato_time.setFormat('')
            #self.tomato_window.endTomato()
            self.taskUI_task_end.emit()
        elif status == 'tomato_cencel':
            self.tomato_time.setValue(0)
            self.tomato_time.setFormat('')

        elif status == 'focus_start':
            if timeleft == 0:
                self.focus_time.setMaximum(1)
                self.focus_time.setValue(0)
                self.focus_time.setFormat('%s min'%(int(timeleft)))
            else:
                self.focus_time.setMaximum(timeleft)
                self.focus_time.setValue(timeleft)
                self.focus_time.setFormat('%s min'%(int(timeleft)))
        elif status == 'focus':
            self.focus_time.setValue(timeleft)
            self.focus_time.setFormat('%s min'%(int(timeleft)))
        elif status == 'focus_end':
            self.focus_time.setValue(0)
            self.focus_time.setMaximum(0)
            self.focus_time.setFormat('')
            #self.focus_window.endFocus()
            self.taskUI_task_end.emit()
        elif status == 'focus_cancel':
            self.focus_time.setValue(0)
            self.focus_time.setMaximum(0)
            self.focus_time.setFormat('')

    def use_item(self, item_name):
        # Check if it's pet-required item
        if item_name == settings.required_item:
            reward_factor = settings.FACTOR_FEED_REQ
            self.close_bubble.emit('feed_required')
        else:
            reward_factor = 1

        # 食物
        if settings.items_data.item_dict[item_name]['item_type']=='consumable':
            # 如果正在播放喂食动画，不打断，只应用效果
            interaction_worker = self.workers['Interaction']
            if interaction_worker.interact == 'animat' and interaction_worker.act_name and interaction_worker.act_name.startswith('feed_'):
                # 效果已在上面处理，不播放动画
                pass
            else:
                self.workers['Animation'].pause()
                # 物品 → 动画映射（共用动画的食物）
                feed_map = {
                    '芝士汉堡': '汉堡',
                    '牛奶': '酸奶',
                }
                feed_item = feed_map.get(item_name, item_name)
                act_name = f'feed_{feed_item}'
                # 检查 act_conf.json 里有没有这个动画
                if act_name in self.pet_conf.act_dict:
                    interaction_worker.start_interact('animat', act_name)
                else:
                    # 没有专属动画，播放 stand
                    interaction_worker.start_interact('animat', 'stand')
            self.bubble_manager.trigger_bubble('feed_done')

        # 附件物品
        elif item_name in self.pet_conf.act_name or item_name in self.pet_conf.acc_name:
            self.workers['Animation'].pause()
            self.workers['Interaction'].start_interact('use_clct', item_name)

        # 对话物品
        elif settings.items_data.item_dict[item_name]['item_type']=='dialogue':
            if item_name in self.pet_conf.msg_dict:
                accs = {'name':'dialogue', 'msg_dict':self.pet_conf.msg_dict[item_name]}
                x = self.pos().x() #+self.width()//2
                y = self.pos().y() #+self.height()
                self.setup_acc.emit(accs, x, y, 0)
                return

        # 系统附件物品
        elif item_name in self.sys_conf.acc_name:
            accs = self.sys_conf.accessory_act[item_name]
            x = self.pos().x()+self.width()//2
            y = self.pos().y()+self.height()
            self.setup_acc.emit(accs, x, y, 0)
        
        # Subpet（已禁用）
        # elif settings.items_data.item_dict[item_name]['item_type']=='subpet':
        #     pet_acc = {'name':'subpet', 'pet_name':item_name}
        #     x = self.pos().x()+self.width()//2
        #     y = self.pos().y()+self.height()
        #     self.setup_acc.emit(pet_acc, x, y)
        #     return

        else:
            pass

        # 鼠标挂件 - currently gave up :(
        '''
        elif item_name in self.sys_conf.mouseDecor:
            accs = {'name':'mouseDecor', 'config':self.sys_conf.mouseDecor[item_name]}
            x = self.pos().x()+self.width()//2
            y = self.pos().y()+self.height()
            self.setup_acc.emit(accs, x, y)
        '''
        
        # 使用物品 改变数值
        self._change_status('hp', 
                            int(settings.items_data.item_dict[item_name]['effect_HP']*reward_factor),
                            from_mod='inventory', send_note=True)
        
        if item_name in self.pet_conf.item_favorite:
            self._change_status('fv',
                                int(settings.items_data.item_dict[item_name]['effect_FV']*self.pet_conf.item_favorite[item_name]*reward_factor),
                                from_mod='inventory', send_note=True)

        elif item_name in self.pet_conf.item_dislike:
            self._change_status('fv', 
                                int(settings.items_data.item_dict[item_name]['effect_FV']*self.pet_conf.item_dislike[item_name]*reward_factor),
                                from_mod='inventory', send_note=True)

        else:
            self._change_status('fv', 
                                int(settings.items_data.item_dict[item_name]['effect_FV']*reward_factor),
                                from_mod='inventory', send_note=True)

    def add_item(self, n_items, item_names=[]):
        self.addItem_toInven.emit(n_items, item_names)

    def patpat(self):
        # 自娱自乐或 land 动画播放期间，跳过动画触发，但保留金币和爱心
        if not self.is_entertainment_playing and not self.is_land_anim_playing:
            # 摸摸动画
            if self.click_count >= 7:
                self.bubble_manager.trigger_bubble("pat_frequent")
            elif self.workers['Interaction'].interact != 'patpat':
                if settings.focus_timer_on:
                    self.bubble_manager.trigger_bubble("pat_focus")
                else:
                    # 只有当前不在播放 patpat 动画时才触发
                    if not self.workers['Interaction'].interact or self.workers['Interaction'].interact != 'patpat':
                        # 25% 概率触发自娱自乐池（动画播放期间锁定）
                        if random.uniform(0, 1) < 0.25:
                            self.is_entertainment_playing = True
                            # 从随机池动态读取，按亲密度过滤
                            # 只保留单动作(status_type[0]>=2)的互动动画
                            # 排除 stand(status_type[0]==1)、walk/多段动画(act_prob!=0.114)
                            fv_lvl = settings.pet_data.fv_lvl
                            act_conf = settings.act_data.allAct_params[settings.petname]
                            entertainment_acts = [
                                name for name, conf in act_conf.items()
                                if conf['act_type'] == 'random_act'
                                and conf.get('entertainment', False)
                                and conf['status_type'][1] <= fv_lvl
                                and conf['unlocked']
                            ]
                            if not entertainment_acts:
                                entertainment_acts = ['sneeze']
                            act_name = random.choice(entertainment_acts)
                            self.workers['Animation'].pause()
                            self.workers['Interaction'].start_interact('animat', act_name)
                        else:
                            self.is_entertainment_playing = False
                            self.workers['Animation'].pause()
                            self.workers['Interaction'].start_interact('patpat')

        # 概率触发浮动的心心
        prob_num_0 = random.uniform(0, 1)
        if prob_num_0 < sys_pp_heart:
            try:
                accs = self.sys_conf.accessory_act['heart']
            except:
                return
            x = QCursor.pos().x()
            y = QCursor.pos().y()
            self.setup_acc.emit(accs, x, y, 0)

        elif prob_num_0 < settings.PP_COIN:
            # Drop random amount of coins
            self.addCoins.emit(0)

        else:
            # 动态物品掉落概率：基础 8% + 每级好感度 +2%，上限 25%
            pp_item = max(0.75, 0.92 - settings.pet_data.fv_lvl * 0.02)
            if prob_num_0 > pp_item:
                self.addItem_toInven.emit(1, [])

        if prob_num_0 > sys_pp_audio:
            #随机语音
            if random.uniform(0, 1) > 0.5:
                self.register_notification('random', '')
            else:
                self.bubble_manager.trigger_patpat_random()

    def item_drop_anim(self, item_name):
        if item_name == 'coin':
            accs = {"name":"item_drop", "item_image":[settings.items_data.coin['image']]}
        else:
            item = settings.items_data.item_dict[item_name]
            accs = {"name":"item_drop", "item_image":[item['image']]}
        # 猫视觉底部 = 窗口Y + statbar高度 + label实际高度
        statbar_h = int(2 * settings.tunable_scale)
        cat_bottom_y = self.pos().y() + statbar_h + self.label.height()
        # 从猫身体中心抛出（和便便同一起点逻辑）
        x = self.pos().x() + self.width() // 2
        y = self.pos().y() + self.height() // 3
        self.setup_acc.emit(accs, x, y, cat_bottom_y)



    def quit(self) -> None:
        """
        关闭窗口, 系统退出
        :return:
        """
        # 1) 保存数据（失败也不影响退出）
        try:
            settings.pet_data.save_data()
            settings.pet_data.frozen()
        except Exception as e:
            print('[quit] save data error:', e)

        # 2) 通知 worker 自行结束循环
        try:
            for name in ('Animation', 'Interaction', 'Scheduler'):
                w = self.workers.get(name)
                if w is not None:
                    w.kill()
        except Exception as e:
            print('[quit] kill worker error:', e)

        try:
            self.stopAllThread.emit()
        except Exception as e:
            print('[quit] stopAllThread error:', e)

        # 3) 终止后台线程（带超时，避免 wait() 永久阻塞 UI 导致点退出卡死）
        for name in ('Animation', 'Interaction', 'Scheduler'):
            try:
                th = self.threads.get(name)
                if th is not None and th.isRunning():
                    th.terminate()
                    th.wait(2000)  # 最多等待 2 秒，超时即放弃
            except Exception as e:
                print('[quit] terminate thread error:', e)

        # 4) 关闭窗口并退出事件循环
        try:
            self.close()
            QApplication.instance().quit()
        except Exception as e:
            print('[quit] close/quit error:', e)

        # 5) 兜底：若 1.5 秒后仍未退出，强制结束进程
        def _force_exit():
            try:
                os._exit(0)
            except Exception:
                pass
        timer = threading.Timer(1.5, _force_exit)
        timer.daemon = True
        timer.start()

    def stop_thread(self, module_name):
        self.workers[module_name].kill()
        self.threads[module_name].terminate()
        self.threads[module_name].wait()
        #self.threads[module_name].wait()

    def follow_mouse_act(self):
        sender = self.sender()
        if settings.onfloor == 0:
            return
        if sender.text()==self.tr("Follow Cursor"):
            sender.setText(self.tr("Stop Follow"))
            self.MouseTracker = MouseMoveManager()
            self.MouseTracker.moved.connect(self.update_mouse_position)
            self.get_positions('mouse')
            self.workers['Animation'].pause()
            self.workers['Interaction'].start_interact('followTarget', 'mouse')
        else:
            sender.setText(self.tr("Follow Cursor"))
            self.MouseTracker._listener.stop()
            self.workers['Interaction'].stop_interact()

    def get_positions(self, object_name):

        main_pos = [int(self.pos().x() + self.width()//2), int(self.pos().y() + self.height() - self.label.height())]

        if object_name == 'mouse':
            self.send_positions.emit(main_pos, self.mouse_pos)

    def update_mouse_position(self, x, y):
        self.mouse_pos = [x, y]

    def stop_trackMouse(self):
        self.start_follow_mouse.setText(self.tr("Follow Cursor"))
        self.MouseTracker._listener.stop()

    '''
    def fall_onoff(self):
        #global set_fall
        sender = self.sender()
        if settings.set_fall==1:
            sender.setText(self.tr("Don't Drop"))
            sender.setIcon(QIcon(os.path.join(basedir,'res/icons/off.svg')))
            settings.set_fall=0
        else:
            sender.setText(self.tr("Allow Drop"))
            sender.setIcon(QIcon(os.path.join(basedir,'res/icons/on.svg')))
            settings.set_fall=1
    '''

    def _show_controlPanel(self):
        self.show_controlPanel.emit()

    def _show_dashboard(self):
        self.show_dashboard.emit()

    def _show_dashboard_panel(self, panel_name):
        """打开角色面板并切换到指定子页面"""
        self.show_dashboard_panel.emit(panel_name)

    '''
    def show_compday(self):
        sender = self.sender()
        if sender.text()=="显示陪伴天数":
            acc = {'name':'compdays', 
                   'height':self.label.height(),
                   'message': "这是%s陪伴你的第 %i 天"%(settings.petname,settings.pet_data.days)}
            sender.setText("关闭陪伴天数")
            x = self.pos().x() + self.width()//2
            y = self.pos().y() + self.height() - self.label.height() - 20 #*settings.size_factor
            self.setup_acc.emit(acc, x, y)
            self.showing_comp = 1
        else:
            sender.setText("显示陪伴天数")
            self.setup_acc.emit({'name':'compdays'}, 0, 0)
            self.showing_comp = 0
    '''

    def show_tomato(self):
        if self.tomato_window.isVisible():
            self.tomato_window.hide()

        else:
            self.tomato_window.move(max(self.current_screen.topLeft().y(),self.pos().x()-self.tomato_window.width()//2),
                                    max(self.current_screen.topLeft().y(),self.pos().y()-self.tomato_window.height()))
            self.tomato_window.show()

        '''
        elif self.tomato_clock.text()=="取消番茄时钟":
            self.tomato_clock.setText("番茄时钟")
            self.workers['Scheduler'].cancel_tomato()
            self.tomatoicon.hide()
            self.tomato_time.hide()
        '''

    def run_tomato(self, nt):
        self.workers['Scheduler'].add_tomato(n_tomato=int(nt))
        self.tomatoicon.show()
        self.tomato_time.show()
        settings.focus_timer_on = True

    def cancel_tomato(self):
        self.workers['Scheduler'].cancel_tomato()

    def change_tomato_menu(self):
        self.tomatoicon.hide()
        self.tomato_time.hide()
        settings.focus_timer_on = False

    
    def show_focus(self):
        if self.focus_window.isVisible():
            self.focus_window.hide()
        
        else:
            self.focus_window.move(max(self.current_screen.topLeft().y(),self.pos().x()-self.focus_window.width()//2),
                                   max(self.current_screen.topLeft().y(),self.pos().y()-self.focus_window.height()))
            self.focus_window.show()


    def run_focus(self, task, hs, ms):
        if task == 'range':
            if hs<=0 and ms<=0:
                return
            self.workers['Scheduler'].add_focus(time_range=[hs,ms])
        elif task == 'point':
            self.workers['Scheduler'].add_focus(time_point=[hs,ms])
        self.focusicon.show()
        self.focus_time.show()
        settings.focus_timer_on = True

    def pause_focus(self, state):
        if state: # 暂停
            self.workers['Scheduler'].pause_focus()
        else: # 继续
            self.workers['Scheduler'].resume_focus(int(self.focus_time.value()), int(self.focus_time.maximum()))


    def cancel_focus(self):
        self.workers['Scheduler'].cancel_focus(int(self.focus_time.maximum()-self.focus_time.value()))

    def change_focus_menu(self):
        self.focusicon.hide()
        self.focus_time.hide()
        settings.focus_timer_on = False


    def show_remind(self):
        if self.remind_window.isVisible():
            self.remind_window.hide()
        else:
            self.remind_window.move(max(self.current_screen.topLeft().y(),self.pos().x()-self.remind_window.width()//2),
                                    max(self.current_screen.topLeft().y(),self.pos().y()-self.remind_window.height()))
            self.remind_window.show()

    ''' Reminder function deleted from v0.3.7
    def run_remind(self, task_type, hs=0, ms=0, texts=''):
        if task_type == 'range':
            self.workers['Scheduler'].add_remind(texts=texts, time_range=[hs,ms])
        elif task_type == 'point':
            self.workers['Scheduler'].add_remind(texts=texts, time_point=[hs,ms])
        elif task_type == 'repeat_interval':
            self.workers['Scheduler'].add_remind(texts=texts, time_range=[hs,ms], repeat=True)
        elif task_type == 'repeat_point':
            self.workers['Scheduler'].add_remind(texts=texts, time_point=[hs,ms], repeat=True)
    '''

    def show_inventory(self):
        if self.inventory_window.isVisible():
            self.inventory_window.hide()
        else:
            self.inventory_window.move(max(self.current_screen.topLeft().y(), self.pos().x()-self.inventory_window.width()//2),
                                    max(self.current_screen.topLeft().y(), self.pos().y()-self.inventory_window.height()))
            self.inventory_window.show()
            #print(self.inventory_window.size())

    '''
    def show_settings(self):
        if self.setting_window.isVisible():
            self.setting_window.hide()
        else:
            #self.setting_window.move(max(self.current_screen.topLeft().y(), self.pos().x()-self.setting_window.width()//2),
            #                        max(self.current_screen.topLeft().y(), self.pos().y()-self.setting_window.height()))
            #self.setting_window.resize(800,800)
            self.setting_window.show()
    '''

    '''
    def show_settingstest(self):
        self.settingUI = SettingMainWindow()
        
        if sys.platform == 'win32':
            self.settingUI.setWindowFlags(
                Qt.FramelessWindowHint | Qt.SubWindow | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        else:
            self.settingUI.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.settingUI.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        cardShadowSE = QtWidgets.QGraphicsDropShadowEffect(self.settingUI)
        cardShadowSE.setColor(QColor(189, 167, 165))
        cardShadowSE.setOffset(0, 0)
        cardShadowSE.setBlurRadius(20)
        self.settingUI.setGraphicsEffect(cardShadowSE)
        
        self.settingUI.show()
    '''

    def runAnimation(self):
        # Create thread for Animation Module
        self.threads['Animation'] = QThread()
        self.workers['Animation'] = Animation_worker(self.pet_conf)
        self.workers['Animation'].moveToThread(self.threads['Animation'])

        # Connect signals and slots
        self.threads['Animation'].started.connect(self.workers['Animation'].run)
        self.workers['Animation'].sig_setimg_anim.connect(self.set_img)
        self.workers['Animation'].sig_move_anim.connect(self._move_customized)
        self.workers['Animation'].sig_repaint_anim.connect(self.repaint)
        self.workers['Animation'].acc_regist.connect(self.register_accessory)
        self.workers['Animation'].sig_start_sleep.connect(self._start_sleep)

        # Start the thread
        self.threads['Animation'].start()
        self.threads['Animation'].setTerminationEnabled()

        # 猫出现后，后台加载剩余动作（利用 5 秒延迟窗口）
        QTimer.singleShot(100, self._preload_remaining_acts)


    def _preload_remaining_acts(self):
        """后台加载未预加载的动作"""
        def _do_preload():
            for act_name, act in self.pet_conf.act_dict.items():
                if not act._loaded:
                    act.preload()
            print("[预加载] 剩余动作图片已全部加载")
        t = threading.Thread(target=_do_preload, daemon=True)
        t.start()


    # ========== 穿透模式（Click-Through）==========

    def toggle_click_through(self):
        """切换穿透模式"""
        if settings.click_through_mode:
            self._exit_click_through()
        else:
            self._enter_click_through()

    def _enter_click_through(self):
        """进入穿透模式：窗口鼠标穿透 + 启动鼠标位置监控"""
        if platform != 'win32':
            return
        settings.click_through_mode = True
        # Windows API: WS_EX_TRANSPARENT 让窗口鼠标穿透
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_TRANSPARENT)
        # Qt 层也停止处理鼠标事件
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # 初始化淡入淡出效果
        self._init_fade_effect()
        # 确保恢复按钮已创建（不显示，等猫消失时自动出现）
        self._ensure_restore_btn()
        # 如果鼠标已在猫身上，立即隐藏
        self._check_mouse_position()
        # 启动鼠标位置监控（复用已有定时器）
        if not hasattr(self, '_mouse_timer'):
            self._mouse_timer = QTimer(self)
            self._mouse_timer.timeout.connect(self._check_mouse_position)
        self._mouse_timer.start(50)

    def _init_fade_effect(self):
        """初始化淡入淡出效果（透明度动画）"""
        # 创建透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(self.label)
        self._opacity_effect.setOpacity(1.0)
        self.label.setGraphicsEffect(self._opacity_effect)
        # 淡出动画（1.0 -> 0.0）
        self._fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_anim.setDuration(100)  # 100ms
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.finished.connect(lambda: self.label.hide())
        # 淡入动画（0.0 -> 1.0）
        self._fade_in_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_anim.setDuration(100)  # 100ms
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        # 标记当前是否正在淡出
        self._is_fading_out = False

    def _exit_click_through(self):
        """退出穿透模式：恢复正常鼠标交互"""
        if platform != 'win32':
            return
        settings.click_through_mode = False
        # 停止鼠标监控
        if hasattr(self, '_mouse_timer') and self._mouse_timer.isActive():
            self._mouse_timer.stop()
        # 停止动画并清理效果
        if hasattr(self, '_fade_out_anim'):
            self._fade_out_anim.stop()
        if hasattr(self, '_fade_in_anim'):
            self._fade_in_anim.stop()
        if hasattr(self, '_opacity_effect'):
            self._opacity_effect.setOpacity(1.0)
        # Windows API: 移除 WS_EX_TRANSPARENT
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style & ~WS_EX_TRANSPARENT)
        # Qt 层恢复鼠标事件处理
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        # 确保猫可见
        self.label.show()
        # 隐藏恢复按钮
        self._hide_restore_button()

    def _check_mouse_position(self):
        """检测鼠标是否在猫轮廓或恢复按钮区域内，控制猫的淡入淡出"""
        if not settings.click_through_mode:
            return
        cursor_pos = QCursor.pos()

        # 使用自定义多矩形或默认单一矩形
        if self._active_rects:
            # 多矩形模式：检查鼠标是否在任意一个矩形内
            in_active_rect = False
            for rect in self._active_rects:
                # 转换为全局坐标进行检测
                global_rect = QRect(self.mapToGlobal(rect.topLeft()), rect.size())
                if global_rect.contains(cursor_pos):
                    in_active_rect = True
                    break
        else:
            # 默认模式：猫轮廓区域 + 按钮区域 + 3px 缓冲带
            label_pos_in_widget = self.label.pos()
            label_global_top_left = self.mapToGlobal(label_pos_in_widget)
            label_rect = QRect(label_global_top_left, self.label.size())
            btn_rect = QRect()
            if hasattr(self, '_restore_btn') and self._restore_btn.isVisible():
                btn_rect = self._restore_btn.geometry()
            active_rect = label_rect.united(btn_rect).adjusted(-3, -3, 3, 3)
            in_active_rect = active_rect.contains(cursor_pos)

        if not in_active_rect:
            # 鼠标完全离开活跃区域：淡入恢复猫，隐藏按钮
            self._fade_in()
            if hasattr(self, '_restore_btn') and self._restore_btn.isVisible():
                self._restore_btn.hide()
            self.update()
            return

        # 编辑模式下不进行像素级检测
        if self._editing_active_rects:
            self.update()
            return

        # 鼠标在活跃区域内：检查是否在猫轮廓上（像素级）
        on_cat = False
        label_pos_in_widget = self.label.pos()
        label_global_top_left = self.mapToGlobal(label_pos_in_widget)
        label_rect = QRect(label_global_top_left, self.label.size())
        if label_rect.contains(cursor_pos):
            local_x = cursor_pos.x() - label_global_top_left.x()
            local_y = cursor_pos.y() - label_global_top_left.y()
            pixmap = self.label.pixmap()
            if pixmap and not pixmap.isNull():
                pixmap_id = id(pixmap)
                if not hasattr(self, '_ct_cached_img_id') or self._ct_cached_img_id != pixmap_id:
                    self._ct_cached_img = pixmap.toImage()
                    self._ct_cached_img_id = pixmap_id
                img = self._ct_cached_img
                scale_x = img.width() / self.label.width()
                scale_y = img.height() / self.label.height()
                px = int(local_x * scale_x)
                py = int(local_y * scale_y)
                if 0 <= px < img.width() and 0 <= py < img.height():
                    on_cat = img.pixelColor(px, py).alpha() > 30

        if on_cat:
            # 在猫轮廓上：淡出隐藏猫，显示按钮
            self._fade_out()
            if not self._restore_btn.isVisible():
                self._position_restore_button()
                self._restore_btn.show()
        # 在活跃区域但不在猫上（按钮上或缓冲带）：保持当前状态不变
        self.update()

    def _fade_out(self):
        """淡出动画（猫消失）"""
        if not hasattr(self, '_opacity_effect'):
            return
        # 如果已经在淡出或已经隐藏，跳过
        if self._is_fading_out or not self.label.isVisible():
            return
        # 如果正在淡入，先停止
        if self._fade_in_anim.state() == QAbstractAnimation.Running:
            self._fade_in_anim.stop()
        self._is_fading_out = True
        self.label.show()
        self._fade_out_anim.start()

    def _fade_in(self):
        """淡入动画（猫恢复）"""
        if not hasattr(self, '_opacity_effect'):
            return
        # 如果已经在显示且完全不透明，跳过
        if self.label.isVisible() and self._opacity_effect.opacity() >= 1.0:
            return
        # 如果正在淡出，先停止
        if self._fade_out_anim.state() == QAbstractAnimation.Running:
            self._fade_out_anim.stop()
        self._is_fading_out = False
        self.label.show()
        self._fade_in_anim.start()

    def _show_restore_button(self, adjust_mode=False):
        """显示恢复按钮在猫旁边"""
        if not hasattr(self, '_restore_btn'):
            self._restore_btn = RestoreButton()
            self._restore_btn.clicked.connect(self._exit_click_through)
            self._restore_btn.position_saved.connect(self._save_btn_offset)
        self._restore_btn.set_adjust_mode(adjust_mode)
        self._position_restore_button()
        self._restore_btn.show()

    def _adjust_btn_position(self):
        """右键菜单：调整恢复按钮位置（显示可拖拽按钮，松手保存）"""
        self._ensure_restore_btn()
        self._restore_btn.set_adjust_mode(True)
        self._position_restore_button()
        self._restore_btn.show()

    def _adjust_mirror_position(self):
        """右键菜单：显示镜像按钮位置（自动计算，不可拖拽）"""
        self._ensure_restore_btn()
        # 直接定位到自动计算的镜像位置
        self._position_restore_button()
        self._restore_btn.show()
        # 临时显示提示
        print("[按钮位置] 镜像位置已自动计算（以猫窗口中线为对称轴）")

    def _ensure_restore_btn(self):
        """确保恢复按钮已创建并连接信号"""
        if not hasattr(self, '_restore_btn'):
            self._restore_btn = RestoreButton()
            self._restore_btn.clicked.connect(self._exit_click_through)
            self._restore_btn.position_saved.connect(self._save_btn_offset)

    def _save_btn_offset(self, abs_x, abs_y):
        """保存按钮偏移量（从拖拽松手事件）"""
        label_global = self.mapToGlobal(self.label.pos())
        dx = abs_x - label_global.x()
        dy = abs_y - label_global.y()
        import json
        # 只保存主位置配置（镜像位置现在是自动计算的）
        key = 'restore_btn_offset'
        # 写入 dyberpet/res/role/{curr_pet_name}/pet_conf.json
        conf_path = os.path.join(basedir, 'res/role/{}/pet_conf.json'.format(self.curr_pet_name))
        with open(conf_path, 'r', encoding='utf-8') as f:
            conf = json.load(f)
        conf[key] = [dx, dy]
        with open(conf_path, 'w', encoding='utf-8') as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)
        # 同步写入 assets/configs/pet_conf.json
        assets_path = os.path.join(basedir, '..', '..', 'assets', 'configs', 'pet_conf.json')
        if os.path.exists(assets_path):
            with open(assets_path, 'r', encoding='utf-8') as f:
                assets_conf = json.load(f)
            assets_conf[key] = [dx, dy]
            with open(assets_path, 'w', encoding='utf-8') as f:
                json.dump(assets_conf, f, ensure_ascii=False, indent=2)
        # 更新内存
        setattr(self.pet_conf, key, [dx, dy])
        print(f"[按钮位置] 已保存 {key}: [{dx}, {dy}]")
        # 退出调整模式
        self._restore_btn.set_adjust_mode(False)
        self._restore_btn.hide()

    def _hide_restore_button(self):
        """隐藏恢复按钮"""
        if hasattr(self, '_restore_btn'):
            self._restore_btn.hide()

    def _toggle_active_rect_debug(self, checked):
        """切换活跃区域调试显示"""
        self._show_active_rect = checked
        self.update()  # 触发重绘

    def _load_active_rects(self, pet_name):
        """加载活跃区域配置"""
        import json
        self._active_rects_file = os.path.join(basedir, f'res/role/{pet_name}/active_rects.json')
        if os.path.exists(self._active_rects_file):
            try:
                with open(self._active_rects_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._active_rects = [QRect(r['x'], r['y'], r['w'], r['h']) for r in data.get('rects', [])]
                print(f"[隐身模式] 加载 {len(self._active_rects)} 个活跃区域矩形")
            except Exception as e:
                print(f"[隐身模式] 加载活跃区域配置失败: {e}")
                self._active_rects = []
        else:
            self._active_rects = []

    def _save_active_rects(self):
        """保存活跃区域配置"""
        import json
        if not self._active_rects_file:
            return
        data = {
            'rects': [{'x': r.x(), 'y': r.y(), 'w': r.width(), 'h': r.height()} for r in self._active_rects]
        }
        try:
            with open(self._active_rects_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[隐身模式] 保存 {len(self._active_rects)} 个活跃区域矩形")
        except Exception as e:
            print(f"[隐身模式] 保存活跃区域配置失败: {e}")

    def _toggle_edit_active_rects(self, checked):
        """切换活跃区域编辑模式"""
        self._editing_active_rects = checked
        if checked:
            # 进入编辑模式：显示所有矩形，启用鼠标交互
            self._show_active_rect = True
            print("[隐身模式] 进入编辑模式 - 左键添加/拖拽，右键删除")
        else:
            # 退出编辑模式
            self._selected_rect_idx = -1
            self._dragging_rect_idx = -1
            print("[隐身模式] 退出编辑模式")
        self.update()

    def _clear_active_rects(self):
        """清空所有活跃区域矩形"""
        self._active_rects.clear()
        self._selected_rect_idx = -1
        self._save_active_rects()
        self.update()
        print("[隐身模式] 已清空所有活跃区域矩形")

    def _add_active_rect(self, pos):
        """在鼠标位置添加新矩形"""
        # 转换为 widget 本地坐标
        local_pos = self.mapFromGlobal(pos)
        # 默认大小 80x80，居中在鼠标位置
        rect = QRect(local_pos.x() - 40, local_pos.y() - 40, 80, 80)
        self._active_rects.append(rect)
        self._selected_rect_idx = len(self._active_rects) - 1
        self._save_active_rects()
        self.update()
        print(f"[隐身模式] 添加矩形 #{self._selected_rect_idx}: {rect.x()},{rect.y()} {rect.width()}x{rect.height()}")

    def _delete_active_rect(self, idx):
        """删除指定索引的矩形"""
        if 0 <= idx < len(self._active_rects):
            rect = self._active_rects.pop(idx)
            self._selected_rect_idx = -1
            self._save_active_rects()
            self.update()
            print(f"[隐身模式] 删除矩形: {rect.x()},{rect.y()} {rect.width()}x{rect.height()}")

    def _get_rect_at_pos(self, pos):
        """获取鼠标位置下的矩形索引，从后往前检测（后添加的优先）"""
        local_pos = self.mapFromGlobal(pos)
        for i in range(len(self._active_rects) - 1, -1, -1):
            if self._active_rects[i].contains(local_pos):
                return i
        return -1

    def _show_active_rect_menu(self, pos):
        """显示活跃区域编辑右键菜单"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        menu = QMenu(self)

        # 添加矩形
        add_action = QAction("添加矩形", self)
        add_action.triggered.connect(lambda: self._add_active_rect(pos))
        menu.addAction(add_action)

        # 清空所有矩形
        if self._active_rects:
            clear_action = QAction("清空所有矩形", self)
            clear_action.triggered.connect(self._clear_active_rects)
            menu.addAction(clear_action)

        menu.exec(pos)

    def _position_restore_button(self):
        """将恢复按钮定位到配置中指定的偏移位置，超出屏幕时以猫窗口中线为对称轴镜像"""
        label_global = self.mapToGlobal(self.label.pos())
        offset = getattr(self.pet_conf, 'restore_btn_offset', [0, 0])
        btn_w = self._restore_btn.width()
        btn_h = self._restore_btn.height()

        # 使用猫当前所在的屏幕
        screen = self.current_screen

        # 猫窗口中线的 X 坐标（对称轴）
        label_center_x = label_global.x() + self.label.width() // 2

        # 尝试主位置
        x = label_global.x() + offset[0]
        y = label_global.y() + offset[1]

        # 检查是否超出屏幕边界
        out_of_bounds = (x + btn_w > screen.right() or x < screen.left() or
                        y + btn_h > screen.bottom() or y < screen.top())

        if out_of_bounds:
            # 以猫窗口中线为对称轴，计算镜像位置
            # 原位置相对于中线的偏移
            offset_from_center = x - label_center_x
            # 镜像位置 = 中线 - 偏移 - 按钮宽度
            x = label_center_x - offset_from_center - btn_w
            # Y 坐标保持不变

            # 如果镜像位置也超出边界，钳制到屏幕内
            if x < screen.left():
                x = screen.left()
            elif x + btn_w > screen.right():
                x = screen.right() - btn_w

            if y < screen.top():
                y = screen.top()
            elif y + btn_h > screen.bottom():
                y = screen.bottom() - btn_h

        self._restore_btn.move(x, y)


    def hpchange(self, hp_tier, direction):
        self.workers['Animation'].hpchange(hp_tier, direction)
        self.hptier_changed_main_note.emit(hp_tier, direction)
        #self._update_statusTitle(hp_tier)

    def fvchange(self, fv_lvl):
        if fv_lvl == -1:
            # 满级，不处理
            self.fvlvl_changed_main_note.emit(fv_lvl)
        elif fv_lvl > self._prev_fv_lvl:
            # 好感度升级
            self.workers['Animation'].fvchange(fv_lvl)
            self.fvlvl_changed_main_note.emit(fv_lvl)
            self.fvlvl_changed_main_inve.emit(fv_lvl)
            self._update_fvlock()
            self.lvl_badge.set_level(fv_lvl)
            self._prev_fv_lvl = fv_lvl
            self.refresh_acts.emit()
            # 亲密度升级弹窗
            _msg = self.tr('好感度升级啦，PETNAME好像对你更感兴趣了！').replace('PETNAME', settings.petname)
            InfoBar.success(
                '',
                _msg,
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )
        else:
            # 好感度降级
            self.workers['Animation'].fvchange(fv_lvl)
            self.fvlvl_changed_main_inve.emit(fv_lvl)
            self._update_fvlock()
            self.lvl_badge.set_level(fv_lvl)
            self._prev_fv_lvl = fv_lvl
            self.refresh_acts.emit()
            _msg = self.tr('PETNAME太饿了，对你的好感度下降了...').replace('PETNAME', settings.petname)
            InfoBar.warning(
                '',
                _msg,
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def runInteraction(self):
        # Create thread for Interaction Module
        self.threads['Interaction'] = QThread()
        self.workers['Interaction'] = Interaction_worker(self.pet_conf)
        self.workers['Interaction'].moveToThread(self.threads['Interaction'])

        # Connect signals and slots
        self.workers['Interaction'].sig_setimg_inter.connect(self.set_img)
        self.workers['Interaction'].sig_move_inter.connect(self._move_customized)
        self.workers['Interaction'].sig_bounce_move.connect(self._move_bounce)
        self.workers['Interaction'].sig_act_finished.connect(self.resume_animation)
        self.workers['Interaction'].sig_interact_note.connect(self.register_notification)
        self.workers['Interaction'].acc_regist.connect(self.register_accessory)
        self.workers['Interaction'].query_position.connect(self.get_positions)
        self.workers['Interaction'].stop_trackMouse.connect(self.stop_trackMouse)
        self.send_positions.connect(self.workers['Interaction'].receive_pos)
        self.threads['Interaction'].started.connect(self._start_startup_wake)

        # Start the thread
        self.threads['Interaction'].start()
        self.threads['Interaction'].setTerminationEnabled()

    def _start_startup_wake(self):
        """Interaction 线程启动后，立即开始启动醒来动画"""
        self.workers['Interaction'].start_interact('startup_wake')

    def runScheduler(self):
        # Create thread for Scheduler Module
        self.threads['Scheduler'] = QThread()
        self.workers['Scheduler'] = Scheduler_worker()
        self.workers['Scheduler'].moveToThread(self.threads['Interaction'])

        # Connect signals and slots
        self.threads['Scheduler'].started.connect(self.workers['Scheduler'].run)
        self.workers['Scheduler'].sig_settext_sche.connect(self.register_notification) #_set_dialogue_dp)
        self.workers['Scheduler'].sig_setact_sche.connect(self._show_act)
        self.workers['Scheduler'].sig_setstat_sche.connect(self._change_status)
        self.workers['Scheduler'].sig_focus_end.connect(self.change_focus_menu)
        self.workers['Scheduler'].sig_tomato_end.connect(self.change_tomato_menu)
        self.workers['Scheduler'].sig_settime_sche.connect(self._change_time)
        self.workers['Scheduler'].sig_addItem_sche.connect(self.add_item)
        self.workers['Scheduler'].sig_setup_bubble.connect(self._process_greeting_mssg)
        self.workers['Scheduler'].sig_wake_sche.connect(self._wake_pet)
        self.workers['Scheduler'].sig_poop_trigger.connect(self._on_poop_trigger)

        # Start the thread
        self.threads['Scheduler'].start()
        self.threads['Scheduler'].setTerminationEnabled()



    def _move_customized(self, plus_x, plus_y):

        #print(act_list)
        #direction, frame_move = str(act_list[0]), float(act_list[1])
        pos = self.pos()
        new_x = pos.x() + plus_x
        new_y = pos.y() + plus_y

        # 正在下落的情况，可以切换屏幕
        if settings.onfloor == 0:
            # 落地情况
            if new_y > self.floor_pos+settings.current_anchor[1]:
                settings.onfloor = 1
                new_x, new_y = self.limit_in_screen(new_x, new_y)
                # 强制归位到地面（避免 limit_in_screen 的微小偏差）
                target_y = self.floor_pos + settings.current_anchor[1]
                self.move(new_x, target_y)
                # 触地：初始化弹跳（只在这里执行一次）
                if not settings.bouncing and not getattr(settings, 'land_bounce_done', False):
                    settings.bouncing = True
                    settings.land_bounce_done = True
                    settings.bounce_tick = 0
                    settings.bounce_prev_offset_x = 0.0
                    settings.bounce_prev_offset_y = 0.0
                    settings.bounce_start_pos = [new_x, target_y]
                    # 物理参数：弹跳总帧数动态匹配当前角色 land_bounce 的实际帧数，
                    # 避免硬编码 22 与真实帧数（六一=30）不一致导致末尾缺帧。
                    _land_act = self.pet_conf.act_dict.get('land_bounce')
                    if _land_act is not None and len(_land_act.images) > 0:
                        settings.bounce_total_frames = len(_land_act.images)
                    vy = abs(settings.dragspeedy)
                    vx = settings.dragspeedx
                    dt_frames = settings.bounce_total_frames
                    settings.bounce_peak_height = max(15, vy * dt_frames * 0.25)
                    settings.bounce_drift_x = vx * dt_frames * 0.5
                    pass
                    # 发射信号启动弹跳动画
                    if hasattr(self.workers['Interaction'], '_fall_logged'):
                        del self.workers['Interaction']._fall_logged
                    self.is_land_anim_playing = True  # land 动画开始
                    self.workers['Interaction'].start_interact('animat', 'land_bounce')
            # 在空中
            else:
                anim_area = QRect(self.pos() + QPoint(self.width()//2-self.label.width()//2, 
                                                      self.height()-self.label.height()), 
                                  QSize(self.label.width(), self.label.height()))
                intersected = self.current_screen.intersected(anim_area)
                area = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                if area > 0.5:
                    pass
                    #new_x, new_y = self.limit_in_screen(new_x, new_y)
                else:
                    switched = False
                    for screen in settings.screens:
                        if screen.geometry() == self.current_screen:
                            continue
                        intersected = screen.geometry().intersected(anim_area)
                        area_tmp = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                        if area_tmp > 0.5:
                            self.switch_screen(screen)
                            switched = True
                    if not switched:
                        new_x, new_y = self.limit_in_screen(new_x, new_y)

        # 正在做动作的情况，局限在当前屏幕内
        else:
            new_x, new_y = self.limit_in_screen(new_x, new_y, on_action=True)

        self.move(new_x, new_y)
        settings.pet_center_x = new_x + self.width() // 2


    def switch_screen(self, screen):
        self.current_screen = screen.availableGeometry() # 与初始化一致：用排除任务栏的工作区，避免底边陷入任务栏
        settings.current_screen = screen
        self.screen_geo = screen.availableGeometry() #screenGeometry()
        self.screen_width = self.screen_geo.width()
        self.screen_height = self.screen_geo.height()
        settings.compute_floor_offset(screen)
        self.floor_pos = self.current_screen.topLeft().y() + self.screen_height -self.height() - settings.floor_y_offset


    def limit_in_screen(self, new_x, new_y, on_action=False):
        # 超出当前屏幕左边界
        if new_x+self.width()//2 < self.current_screen.topLeft().x():
            #surpass_x = 'Left'
            new_x = self.current_screen.topLeft().x()-self.width()//2
            if not on_action:
                settings.dragspeedx = -settings.dragspeedx * settings.SPEED_DECAY
                settings.fall_right = not settings.fall_right

        # 超出当前屏幕右边界
        elif new_x+self.width()//2 > self.current_screen.topLeft().x() + self.screen_width:
            #surpass_x = 'Right'
            new_x = self.current_screen.topLeft().x() + self.screen_width-self.width()//2
            if not on_action:
                settings.dragspeedx = -settings.dragspeedx * settings.SPEED_DECAY
                settings.fall_right = not settings.fall_right

        # 超出当前屏幕上边界
        if new_y+self.height()-self.label.height()//2 < self.current_screen.topLeft().y():
            #surpass_y = 'Top'
            new_y = self.current_screen.topLeft().y() + self.label.height()//2 - self.height()
            if not on_action:
                settings.dragspeedy = abs(settings.dragspeedy) * settings.SPEED_DECAY

        # 超出当前屏幕下边界
        elif new_y > self.floor_pos+settings.current_anchor[1]:
            #surpass_y = 'Bottom'
            new_y = self.floor_pos+settings.current_anchor[1]

        return new_x, new_y


    def _show_act(self, act_name):
        self.workers['Animation'].pause()
        self.workers['Interaction'].start_interact('actlist', act_name)

    def _start_sleep(self):
        """开始睡觉（由 Animation_worker 信号触发，Animation_worker 已自行暂停）"""
        self.workers['Interaction'].start_interact('sleep')

    def _wake_pet(self):
        """触发唤醒动画"""
        self.workers['Animation'].pause()
        self.workers['Interaction'].start_interact('wake')
    '''
    def _show_acc(self, acc_name):
        self.workers['Animation'].pause()
        self.workers['Interaction'].start_interact('anim_acc', acc_name)
    '''
    def _set_defaultAct(self, act_name):

        if act_name == settings.defaultAct[self.curr_pet_name]:
            settings.defaultAct[self.curr_pet_name] = None
            settings.save_settings()
            for action in self.defaultAct_menu.menuActions():
                if action.text() == act_name:
                    action.setIcon(QIcon(os.path.join(basedir, 'res/icons/dot.png')))
        else:
            for action in self.defaultAct_menu.menuActions():
                if action.text() == settings.defaultAct[self.curr_pet_name]:
                    action.setIcon(QIcon(os.path.join(basedir, 'res/icons/dot.png')))
                elif action.text() == act_name:
                    action.setIcon(QIcon(os.path.join(basedir, 'res/icons/dotfill.png'))) #os.path.join(basedir, 'res/icons/check_icon.png')))

            settings.defaultAct[self.curr_pet_name] = act_name
            settings.save_settings()


    def move(self, *args, **kwargs):
        """Override move to trace suspicious position changes after bounce."""
        super().move(*args, **kwargs)

    def resume_animation(self):
        # 如果鼠标仍然按住，停止拖拽
        if self.is_follow_mouse:
            self.is_follow_mouse = False
            self.setCursor(self.cursor_default)
            self.mouse_moving = False
        # 强制归位到地面并重置状态
        settings.onfloor = 1
        settings.draging = 0
        target_y = self.floor_pos + settings.current_anchor[1]
        self.move(self.pos().x(), target_y)
        settings.pet_center_x = self.pos().x() + self.width() // 2
        # 不再强制闪回 stand 第 0 帧：交给 Animation_worker 的断点续播，
        # 交互结束后从被打断的那一帧继续，而不是从头播。
        self.workers['Animation'].resume()
        # 解锁自娱自乐动画
        self.is_entertainment_playing = False
        # 解锁 land 动画
        self.is_land_anim_playing = False
    
    def _mightEventTrigger(self):
        # Update date
        settings.pet_data.update_date()
        # Update companion days
        daysText = self.tr(" (Fed for ") + str(settings.pet_data.days) +\
                   self.tr(" days)")
        self.daysLabel.setText(daysText)




class LazyPicDict:
    """懒加载图片字典：按需加载图片，带缓存"""
    def __init__(self, pet_name):
        self._pet_name = pet_name
        self._img_dir = os.path.join(basedir, 'res/role/{}/action/'.format(pet_name))
        self._cache = {}
        self._file_map = {}  # key -> file_path

        # 建立索引（不加载图片）
        for root, dirs, files in os.walk(self._img_dir):
            for image in files:
                if image.endswith('.png'):
                    key = image.split('.')[0]
                    self._file_map[key] = os.path.join(root, image)

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]

        if key not in self._file_map:
            raise KeyError(key)

        pixmap = QPixmap()
        pixmap.load(self._file_map[key])
        if not pixmap.isNull():
            self._cache[key] = pixmap
            return pixmap
        return QPixmap()  # 返回空 pixmap

    def __contains__(self, key):
        return key in self._file_map

    def keys(self):
        return self._file_map.keys()

    def values(self):
        for key in self._file_map:
            yield self[key]

    def items(self):
        for key in self._file_map:
            yield key, self[key]

    def __len__(self):
        return len(self._file_map)


def _load_all_pic(pet_name: str) -> dict:
    """
    返回懒加载图片字典
    :param pet_name: 宠物名称
    :return: LazyPicDict
    """
    return LazyPicDict(pet_name)

def _build_act(name: str, parent: QObject, act_func, icon=None) -> Action:
    """
    构建改变菜单动作
    :param pet_name: 菜单动作名称
    :param parent 父级菜单
    :param act_func: 菜单动作函数
    :return:
    """
    if icon:
        act = Action(icon, name, parent)
    else:
        act = Action(name, parent)
    act.triggered.connect(lambda: act_func(name))
    return act

def _build_act_param(name: str, param: str, parent: QObject, act_func) -> Action:
    """
    构建改变菜单动作
    :param pet_name: 菜单动作名称
    :param parent 父级菜单
    :param act_func: 菜单动作函数
    :return:
    """
    act = Action(name, parent)
    act.triggered.connect(lambda: act_func(param))
    return act


