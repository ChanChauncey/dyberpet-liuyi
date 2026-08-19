import sys, os
sys.path.insert(0, os.path.dirname(__file__))


# ---- 优先加载安装目录下的松散 DyberPet 源码（增量更新的覆盖目标）----
# one-folder 构建下 exe 与 DyberPet/ 松散包同处安装目录。PyInstaller 同时把
# DyberPet 源码打包进 PYZ（冻结副本）。本查找器拦截 "DyberPet" 及其所有子模块
# （含任意嵌套层级），确保优先从安装目录的 DyberPet/ 加载（增量更新覆盖后的新版），
# 而不是冻结副本。若某模块在松散目录中不存在，返回 None 让 FrozenImporter 回退到
# 冻结副本；若安装目录根本没有松散 DyberPet 包，整个查找器不生效，走冻结版。
if getattr(sys, 'frozen', False):
    try:
        _install_dir = os.path.dirname(sys.executable)
        _loose_dyberpet = os.path.join(_install_dir, 'DyberPet')
        if os.path.isfile(os.path.join(_loose_dyberpet, '__init__.py')):
            from importlib.machinery import (
                FileFinder, SourceFileLoader, SourcelessFileLoader,
                SOURCE_SUFFIXES, BYTECODE_SUFFIXES, ModuleSpec,
            )
            # 顶层 DyberPet 包在安装目录根下查找
            _root_finder = FileFinder(
                _install_dir,
                (SourceFileLoader, SOURCE_SUFFIXES),
                (SourcelessFileLoader, BYTECODE_SUFFIXES),
            )

            class _LooseDyberPetFinder:
                def find_spec(self, fullname, path=None, target=None):
                    if fullname == 'DyberPet':
                        return _root_finder.find_spec(fullname, target=target)
                    if fullname.startswith('DyberPet.'):
                        if path:
                            # 导入系统传入父包 __path__（如
                            # [install_dir/DyberPet/DyberSettings]），取最后一
                            # 个分量到该目录下查找，从而正确解析任意嵌套子模块。
                            leaf = fullname.rpartition('.')[2]
                            _f = FileFinder(
                                path[0],
                                (SourceFileLoader, SOURCE_SUFFIXES),
                                (SourcelessFileLoader, BYTECODE_SUFFIXES),
                            )
                            spec = _f.find_spec(leaf, target=target)
                        else:
                            # 防御：无 path 时按相对名在 DyberPet/ 下查找
                            rel = fullname[len('DyberPet.'):]
                            _f = FileFinder(
                                _loose_dyberpet,
                                (SourceFileLoader, SOURCE_SUFFIXES),
                                (SourcelessFileLoader, BYTECODE_SUFFIXES),
                            )
                            spec = _f.find_spec(rel, target=target)
                        if spec is None:
                            return None
                        # FileFinder 返回的 spec/loader 名字是叶子名（如
                        # "utils"），直接改名会导致 "loader for utils cannot
                        # handle DyberPet.utils"。重建以全名为名的 loader/spec。
                        if isinstance(spec.loader, SourceFileLoader):
                            _loader = SourceFileLoader(fullname, spec.origin)
                        elif isinstance(spec.loader, SourcelessFileLoader):
                            _loader = SourcelessFileLoader(fullname, spec.origin)
                        else:
                            _loader = spec.loader
                        _new = ModuleSpec(
                            fullname, _loader, origin=spec.origin,
                            loader_state=spec.loader_state,
                            is_package=spec.submodule_search_locations is not None,
                        )
                        _new.submodule_search_locations = spec.submodule_search_locations
                        _new.cached = spec.cached
                        _new.has_location = spec.has_location
                        return _new
                    return None

            sys.meta_path.insert(0, _LooseDyberPetFinder())
    except Exception:
        pass


from sys import platform
import ctypes
from tendo import singleton
import os
import time
from DyberPet.utils import read_json
from DyberPet.DyberPet import PetWidget
from DyberPet.Notification import DPNote
from DyberPet.Accessory import DPAccessory

from PySide6.QtWidgets import QApplication
from PySide6 import QtCore
from PySide6.QtCore import Qt, QLocale, QTimer, QDateTime, QDate, Signal, QTime

from qfluentwidgets import  FluentTranslator, setThemeColor
from DyberPet.DyberSettings.DyberControlPanel import ControlMainWindow
from DyberPet.Dashboard.DashboardUI import DashboardMainWindow

try:
    size_factor = 1 #ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
except:
    size_factor = 1

import DyberPet.settings as settings


# For translation:
# pylupdate5 langs.pro
# lrelease langs.zh_CN.ts

# For .exe:
# Now we use pyinstaller 6.5.0
# pyinstaller --noconsole --icon="000.ico" --hidden-import="pynput.mouse._win32" --hidden-import="pynput.keyboard._win32" run_DyberPet.py

# For Mac:
# pyinstaller --windowed --icon 000.icns --add-data="res:res" --add-data="DyberPet:DyberPet" --hidden-import="pynput.mouse._darwin" --hidden-import="pynput.keyboard._darwin" run_DyberPet.py

# tooltip 瞬间浮出
os.environ['QT_TOOLTIP_SHOW_DELAY'] = '0'


class DyberPetApp(QApplication):
    date_changed = Signal(QDate)

    def __init__(self, *args, **kwargs):
        super(DyberPetApp, self).__init__(*args, **kwargs)

        self.setApplicationName('六一桌宠')
        self.setQuitOnLastWindowClosed(False)
        screens = self.screens()
        primary_screen = self.primaryScreen()

        if primary_screen in screens:
            screens.insert(0, screens.pop(screens.index(primary_screen)))
        else:
            screens.insert(0, primary_screen)

        # internationalization
        t0 = time.time()
        fluentTranslator = FluentTranslator(QLocale(settings.language_code))
        self.installTranslator(fluentTranslator)
        self.installTranslator(settings.translator)
        if settings.themeColor:
            setThemeColor(settings.themeColor)
        print(f"[启动] 国际化: {time.time()-t0:.2f}s")

        # Pet Object
        t1 = time.time()
        self.p = PetWidget(screens=screens)
        print(f"[启动] PetWidget: {time.time()-t1:.2f}s")

        # Notification System
        t2 = time.time()
        self.note = DPNote()
        print(f"[启动] DPNote: {time.time()-t2:.2f}s")

        # Accessory System
        t3 = time.time()
        self.acc = DPAccessory()
        print(f"[启动] DPAccessory: {time.time()-t3:.2f}s")

        # 延迟初始化控制面板；Dashboard 需要立即创建以便接收掉落/金币/升级奖励
        self.conp = None
        self.board = DashboardMainWindow()
        self._connect_board_signals()

        # Midnight Timer
        self.current_date = QDate.currentDate()
        self.set_midnight_timer()

        # Signal Links (延迟绑定)
        self.__connectSignalToSlot()
        print(f"[启动] 总耗时: {time.time()-t0:.2f}s")

        # 启动后自动检测更新（延迟 6s，避免影响启动；后台联网，不阻塞 UI）。
        # 发现新版本会直接弹出 Cherry Studio 风格更新卡片（由 SettingInterface 处理），
        # 全程不打开浏览器、不打扰（无更新则保持静默）。
        QTimer.singleShot(6000, self._auto_check_update)

    def _auto_check_update(self):
        """启动自动检测 GitHub Release 是否有新版本；有则弹更新卡片。

        走与手动点击「检查更新」完全相同的路径（SettingInterface._onCheckUpdateClicked），
        最终弹出 UpdateDialog（Cherry Studio 风格增量更新卡片）。绝不调用 webbrowser，
        绝不自动打开 GitHub 网页。无更新或检测失败均静默，不打扰用户。
        """
        def _trigger():
            try:
                # 只创建控制面板对象，不显示窗口（更新卡片由 UpdateDialog.exec 自行弹出）
                self._ensure_conp(show=False)
                self.conp.settingInterface._onCheckUpdateClicked(silent=True)
            except Exception as e:
                print('[AutoCheckUpdate]', repr(e))
        QTimer.singleShot(0, _trigger)

    def _ensure_conp(self, show=True):
        """延迟初始化 ControlMainWindow。show=False 时只创建对象不显示窗口。"""
        if self.conp is None:
            self.conp = ControlMainWindow()
            self._connect_conp_signals()
        if show:
            self.conp.show_window()

    def _ensure_board(self):
        """延迟初始化 DashboardMainWindow"""
        if self.board is None:
            self.board = DashboardMainWindow()
            self._connect_board_signals()
        self.board.show_window()

    def _ensure_board_panel(self, panel_name):
        """延迟初始化 DashboardMainWindow 并切换到指定面板"""
        if self.board is None:
            self.board = DashboardMainWindow()
            self._connect_board_signals()
        self.board.show_and_switch(panel_name)

    def __connectSignalToSlot(self):
        # Main Widget - others
        self.p.setup_notification.connect(self.note.setup_notification)
        self.p.setup_bubbleText.connect(self.note.setup_bubbleText)
        self.p.change_note.connect(self.note.change_pet)
        self.p.close_bubble.connect(self.note.close_bubble)
        self.p.hptier_changed_main_note.connect(self.note.hpchange_note)
        self.p.fvlvl_changed_main_note.connect(self.note.fvchange_note)
        self.p.setup_acc.connect(self.acc.setup_accessory)
        self.p.move_sig.connect(self.acc.send_main_movement)
        self.p.move_sig.connect(self.note.send_main_movement)
        self.p.close_all_accs.connect(self.acc.closeAll)

        # 延迟打开面板
        self.p.show_controlPanel.connect(self._ensure_conp)
        self.p.show_dashboard.connect(self._ensure_board)
        self.p.show_dashboard_panel.connect(self._ensure_board_panel)

        # Midnight Trigger
        self.date_changed.connect(self.p._mightEventTrigger)

    def _connect_conp_signals(self):
        """绑定 ControlPanel 相关信号"""
        if self.conp is None:
            return
        self.p.change_note.connect(self.conp.charCardInterface._finishStateTooltip)
        self.conp.settingInterface.ontop_changed.connect(self.acc.ontop_changed)
        self.conp.settingInterface.scale_changed.connect(self.acc.reset_size_sig)
        self.conp.settingInterface.ontop_changed.connect(self.p.ontop_update)
        self.conp.settingInterface.scale_changed.connect(self.p.reset_size)
        self.conp.settingInterface.lang_changed.connect(self.p.lang_changed)
        self.p.change_note.connect(self.conp.settingInterface._update_scale)
        self.conp.charCardInterface.change_pet.connect(self.p._change_pet)
        self.conp.gamesaveInterface.refresh_pet.connect(self.p.refresh_pet)

    def _connect_board_signals(self):
        """绑定 Dashboard 相关信号"""
        if self.board is None:
            return
        self.note.noteToLog.connect(self.board.statusInterface._addNote)
        self.p.hp_updated.connect(self.board.statusInterface.StatusCard._updateHP)
        self.p.fv_updated.connect(self.board.statusInterface.StatusCard._updateFV)
        self.p.change_note.connect(self.board.statusInterface._changePet)
        self.board.statusInterface.changeStatus.connect(self.p._change_status)
        self.p.stopAllThread.connect(self.board.statusInterface.stopBuffThread)

        self.acc.acc_withdrawed.connect(self.board.backpackInterface.acc_withdrawed)
        self.board.backpackInterface.use_item_inven.connect(self.p.use_item)
        self.board.backpackInterface.item_note.connect(self.p.register_notification)
        self.board.backpackInterface.item_drop.connect(self.p.item_drop_anim)
        # 掉落/金币/升级奖励统一交给 Dashboard 背包处理；extra_windows.Inventory 不再监听，
        # 避免一次掉落被两个背包各自随机出不同物品（弹两个通知但只在一个背包显示）。
        self.p.fvlvl_changed_main_inve.connect(self.board.backpackInterface.fvchange)
        self.p.fvlvl_changed_main_inve.connect(self.board.shopInterface.fvchange)
        self.p.addItem_toInven.connect(self.board.backpackInterface.add_items)
        self.p.compensate_rewards.connect(self.board.backpackInterface.compensate_rewards)
        self.p.refresh_bag.connect(self.board.backpackInterface.refresh_bag)
        self.p.autofeed.connect(self.board.backpackInterface.autofeed)
        self.p.refresh_bag.connect(self.board.shopInterface.refresh_shop)
        self.p.addCoins.connect(self.board.backpackInterface.addCoins)

        self.board.taskInterface.focusPanel.start_pomodoro.connect(self.p.run_tomato)
        self.board.taskInterface.focusPanel.cancel_pomodoro.connect(self.p.cancel_tomato)
        self.board.taskInterface.focusPanel.start_focus.connect(self.p.run_focus)
        self.board.taskInterface.focusPanel.cancel_focus.connect(self.p.cancel_focus)
        self.p.taskUI_Timer_update.connect(self.board.taskInterface.focusPanel.update_Timer)
        self.p.taskUI_task_end.connect(self.board.taskInterface.focusPanel.taskFinished)
        self.p.single_pomo_done.connect(self.board.taskInterface.focusPanel.single_pomo_done)

    def set_midnight_timer(self):
        now = QDateTime.currentDateTime()
        midnight = QDateTime(QDate.currentDate().addDays(1), QTime(0, 0, 0))  # Next midnight
        msecs_until_midnight = now.msecsTo(midnight)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check_date)
        self.timer.start(msecs_until_midnight)
    
    def check_date(self):
        new_date = QDate.currentDate()
        if new_date != self.current_date:
            self.current_date = new_date
            self.date_changed.emit(new_date)
        self.set_midnight_timer()  # Reset the timer for the next midnight


        


if platform == 'win32':
    basedir = ''
else:
    basedir = os.path.dirname(__file__)

if __name__ == '__main__':

    # Avoid multiple process
    try:
        # 自重启更新时带上 DYBERPET_RELAUNCH，跳过单例锁（旧进程即将退出）
        if not os.environ.get('DYBERPET_TEST_NO_SINGLETON') and not os.environ.get('DYBERPET_RELAUNCH'):
            me = singleton.SingleInstance()
    except:
        sys.exit()


    # Create App
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    #QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    #QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = DyberPetApp(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    sys.exit(app.exec())


