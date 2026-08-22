# coding:utf-8
import os
import json
import zipfile
import shutil
import threading
import urllib.request
import urllib.error
from sys import platform
import sys
import subprocess
import tempfile
import ctypes

from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, HyperlinkCard, InfoBar,
                            ComboBoxSettingCard, ScrollArea, ExpandLayout, InfoBarPosition,
                            PushSettingCard, setThemeColor, TitleLabel, ProgressBar,
                            PrimaryPushButton, PushButton)

from qfluentwidgets import FluentIcon as FIF
from PySide6.QtCore import Qt, Signal, QUrl, QStandardPaths, QLocale, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QWidget, QLabel, QApplication, QProgressDialog, QMessageBox,
                               QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser)
#from qframelesswindow import FramelessWindow

from .custom_utils import (Dyber_RangeSettingCard, Dyber_ComboBoxSettingCard,
                             CustomColorSettingCard, Dyber_ShortcutCard)
import DyberPet.settings as settings

basedir = settings.BASEDIR
module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')

# ---------- 开机自启（与安装程序共用 HKCU\...\Run\六一桌宠 注册表项）----------
AUTOSTART_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_REG_VALUE = "六一桌宠"   # 与安装程序 installer.py 保持一致


def _autostart_exe_path():
    """返回当前 exe 的完整路径（仅 frozen 安装态有效）。"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "六一桌宠.exe")
    return None


def get_autostart():
    """读取注册表，判断是否已设为开机自启。"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY)
        val, _ = winreg.QueryValueEx(key, AUTOSTART_REG_VALUE)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


def set_autostart(enable):
    """写入或删除开机自启注册表项。enable=True 写入，False 删除。"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY,
                             0, winreg.KEY_SET_VALUE)
        if enable:
            exe = _autostart_exe_path()
            if exe:
                winreg.SetValueEx(key, AUTOSTART_REG_VALUE, 0, winreg.REG_SZ,
                                  '"{}"'.format(exe))
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_REG_VALUE)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass

'''
if platform == 'win32':
    basedir = ''
    module_path = 'DyberPet/DyberSettings/'
else:
    #from pathlib import Path
    basedir = os.path.dirname(__file__) #Path(os.path.dirname(__file__))
    #basedir = basedir.parent
    basedir = basedir.replace('\\','/')
    basedir = '/'.join(basedir.split('/')[:-2])

    module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')
'''


class SettingInterface(ScrollArea):
    """ Setting interface """

    ontop_changed = Signal(name='ontop_changed')
    scale_changed = Signal(name='scale_changed')
    lang_changed = Signal(name='lang_changed')
    checkUpdateFinished = Signal(bool, str, object, object, str)  # (has_update, info, full_urls, src_urls, notes)
    downloadProgress = Signal(int, str)
    downloadFinished = Signal(bool, str)
    patchProgress = Signal(int, str)   # 应用更新（解压+覆盖）进度/状态
    restartRequested = Signal()        # 增量更新应用完成后请求主线程重启

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel(self.tr("Settings"), self)
        
        # Mode =========================================================================================
        self.ModeGroup = SettingCardGroup(self.tr('Mode'), self.scrollWidget)
        # Always on top
        self.AlwaysOnTopCard = SwitchSettingCard(
            FIF.PIN,
            self.tr("Always-On-Top"),
            self.tr("Pet will be displayed on top of the other Apps"),
            parent=self.ModeGroup #DisplayModeGroup
        )
        if settings.on_top_hint:
            self.AlwaysOnTopCard.setChecked(True)
        else:
            self.AlwaysOnTopCard.setChecked(False)
        self.AlwaysOnTopCard.switchButton.checkedChanged.connect(self._AlwaysOnTopChanged)

        # Allow drop — 已禁用，代码保留
        #self.AllowDropCard = SwitchSettingCard(...)

        # Auto-Lock
        self.AutoLockCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/lock.svg')),
            self.tr("Auto-Lock"),
            self.tr("When screen is locked, HP and FV will be locked too (currently only works in Windows)"),
            parent=self.ModeGroup #DisplayModeGroup
        )
        if settings.auto_lock:
            self.AutoLockCard.setChecked(True)
        else:
            self.AutoLockCard.setChecked(False)
        self.AutoLockCard.switchButton.checkedChanged.connect(self._AutoLockChanged)
        if platform != 'win32':
            self.AutoLockCard.switchButton.indicator.setEnabled(False)

        # Auto-Start (Windows 开机自启，与安装程序共享注册表项)
        self.AutoStartCard = SwitchSettingCard(
            FIF.POWER_BUTTON,
            self.tr("开机自动启动"),
            self.tr("Windows 启动时自动运行六一桌宠"),
            parent=self.ModeGroup
        )
        if platform == 'win32' and getattr(sys, 'frozen', False):
            self.AutoStartCard.setChecked(get_autostart())
            self.AutoStartCard.switchButton.checkedChanged.connect(self._AutoStartChanged)
        else:
            # 非 Windows 或未安装（开发态）不提供此开关
            self.AutoStartCard.switchButton.indicator.setEnabled(False)


        # Interaction parameters =======================================================================
        self.InteractionGroup = SettingCardGroup(self.tr('Interaction'), self.scrollWidget)
        self.GravityCard = Dyber_RangeSettingCard(
            1, 200, 0.01,
            QIcon(os.path.join(basedir, 'res/icons/system/gravity.svg')),
            self.tr("Gravity"),
            self.tr("Pet falling down acceleration"),
            parent=self.InteractionGroup
        )

        self.GravityCard.setValue(int(settings.gravity*100))
        self.GravityCard.slider.valueChanged.connect(self._GravityChanged)

        self.DragCard = Dyber_RangeSettingCard(
            0, 200, 0.01,
            QIcon(os.path.join(basedir, 'res/icons/system/mousedrag.svg')),
            self.tr("Drag Speed"),
            self.tr("Mouse speed factor"),
            parent=self.InteractionGroup
        )
        self.DragCard.setValue(int(settings.fixdragspeedx*100))
        self.DragCard.slider.valueChanged.connect(self._DragChanged)


        # Notification parameters ======================================================================
        self.VolumnGroup = SettingCardGroup(self.tr('Notification'), self.scrollWidget)
        self.VolumnCard = Dyber_RangeSettingCard(
            0, 10, 0.1,
            QIcon(os.path.join(basedir, 'res/icons/system/speaker.svg')),
            self.tr("Volumn"),
            self.tr("Volumn of notification and pet"),
            parent=self.VolumnGroup
        )
        self.VolumnCard.setValue(int(settings.volume*10))
        self.VolumnCard.slider.valueChanged.connect(self._VolumnChanged)

        self.AllowToasterCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/popup.svg')),
            self.tr("Pop-up Toaster"),
            self.tr("When turned on, notification will pop-up at the bottom right corner"),
            parent=self.VolumnGroup
        )
        if settings.toaster_on:
            self.AllowToasterCard.setChecked(True)
        else:
            self.AllowToasterCard.setChecked(False)
        self.AllowToasterCard.switchButton.checkedChanged.connect(self._AllowToasterChanged)

        self.AllowBubbleCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/bubble.svg')),
            self.tr("Dialogue Bubble"),
            self.tr("When turned on, various kinds of bubbles will pop-up above the pet"),
            parent=self.VolumnGroup
        )
        if settings.bubble_on:
            self.AllowBubbleCard.setChecked(True)
        else:
            self.AllowBubbleCard.setChecked(False)
        self.AllowBubbleCard.switchButton.checkedChanged.connect(self._AllowBubbleChanged)

        # 允许拉屎开关
        self.AllowPoopCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/falldown.svg')),
            self.tr("允许拉屎"),
            self.tr("开启后，宠物会在任务栏随机拉屎"),
            parent=self.ModeGroup
        )
        if settings.poop_enabled:
            self.AllowPoopCard.setChecked(True)
        else:
            self.AllowPoopCard.setChecked(False)
        self.AllowPoopCard.switchButton.checkedChanged.connect(self._AllowPoopChanged)

        # Personalization ==============================================================================
        self.PersonalGroup = SettingCardGroup(self.tr('Personalization'), self.scrollWidget)
        self.ScaleCard = Dyber_RangeSettingCard(
            1, 50, 0.1,
            QIcon(os.path.join(basedir, 'res/icons/system/resize.svg')),
            self.tr("Pet Scale"),
            self.tr("Adjust size of the pet"),
            parent=self.PersonalGroup
        )
        self.ScaleCard.setValue(int(settings.tunable_scale*10))
        self.ScaleCard.slider.valueChanged.connect(self._ScaleChanged)

        pet_list = settings.pets
        self.DefaultPetCard = Dyber_ComboBoxSettingCard(
            pet_list,
            pet_list,
            QIcon(os.path.join(basedir, 'res/icons/system/homestar.svg')),
            self.tr('Default Pet'),
            self.tr('Pet to show everytime App starts'),
            parent=self.PersonalGroup
        )
        self.DefaultPetCard.comboBox.currentTextChanged.connect(self._DefaultPetChanged)

        lang_choices = list(settings.lang_dict.keys())
        lang_now = lang_choices[list(settings.lang_dict.values()).index(settings.language_code)]
        lang_choices.remove(lang_now)
        lang_choices = [lang_now] + lang_choices
        self.languageCard = Dyber_ComboBoxSettingCard(
            lang_choices,
            lang_choices,
            FIF.LANGUAGE,
            self.tr('Language/语言'),
            self.tr('Set your preferred language for UI'),
            parent=self.PersonalGroup
        )
        self.languageCard.comboBox.currentTextChanged.connect(self._LanguageChanged)

        self.themeColorCard = CustomColorSettingCard(
            FIF.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            self.PersonalGroup
        )
        self.themeColorCard.colorChanged.connect(self.colorChanged)

        # Shortcuts ===================================================================================
        # 键盘快捷键（操作宠物动作）完整清单
        self.ShortcutGroup = SettingCardGroup(self.tr('快捷键 (Shortcuts)'), self.scrollWidget)
        self.ShortcutCard = Dyber_ShortcutCard(
            FIF.GAME,
            self.tr('操作宠物的键盘快捷键'),
            [
                ('A', '向左走（仅当宠物在屏幕右半边时生效）'),
                ('D', '向右走（仅当宠物在屏幕左半边时生效）'),
                ('S', '触发睡觉'),
                ('空格', '触发跳跃'),
                ('Q', '舔毛'),
                ('E', '摇尾巴'),
                ('R', '抓苍蝇'),
                ('0', '拉屎'),
                ('小键盘 *', '弹出喂食气泡'),
            ],
            self.tr('宠物窗口需处于焦点状态；A/D 受屏幕半区限制'),
            parent=self.ShortcutGroup
        )

        # About / 更新 =================================================================================
        self.AboutGroup = SettingCardGroup(self.tr('关于 / About'), self.scrollWidget)

        self.VersionCard = HyperlinkCard(
            settings.RELEASE_URL,
            self.tr('前往 Releases'),
            FIF.INFO,
            self.tr('当前版本'),
            self.tr(settings.VERSION),
            parent=self.AboutGroup
        )

        self.CheckUpdateCard = PushSettingCard(
            self.tr('检查更新'),
            FIF.SYNC,
            self.tr('检查更新'),
            self.tr('检查是否有新版本可下载'),
            parent=self.AboutGroup
        )
        self.CheckUpdateCard.clicked.connect(self._onCheckUpdateClicked)
        self.checkUpdateFinished.connect(self._showUpdateResult)
        self.restartRequested.connect(self._onRestartRequested)

        self.__initWidget()

    def __initWidget(self):
        #self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 75, 0, 20)
        self.setWidget(self.scrollWidget)
        #self.scrollWidget.resize(1000, 800)
        self.setWidgetResizable(True)

        # initialize style sheet
        self.__setQss()

        # initialize layout
        self.__initLayout()
        #self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(50, 20)

        # add cards to group
        self.ModeGroup.addSettingCard(self.AlwaysOnTopCard)
        self.ModeGroup.addSettingCard(self.AutoLockCard)
        self.ModeGroup.addSettingCard(self.AutoStartCard)
        self.ModeGroup.addSettingCard(self.AllowPoopCard)

        self.InteractionGroup.addSettingCard(self.GravityCard)
        self.InteractionGroup.addSettingCard(self.DragCard)

        self.VolumnGroup.addSettingCard(self.VolumnCard)
        self.VolumnGroup.addSettingCard(self.AllowToasterCard)
        self.VolumnGroup.addSettingCard(self.AllowBubbleCard)

        self.PersonalGroup.addSettingCard(self.ScaleCard)
        self.PersonalGroup.addSettingCard(self.DefaultPetCard)
        self.PersonalGroup.addSettingCard(self.languageCard)
        self.PersonalGroup.addSettingCard(self.themeColorCard)

        self.ShortcutGroup.addSettingCard(self.ShortcutCard)

        self.AboutGroup.addSettingCard(self.VersionCard)
        self.AboutGroup.addSettingCard(self.CheckUpdateCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(60, 10, 60, 0)

        self.expandLayout.addWidget(self.ModeGroup)
        self.expandLayout.addWidget(self.InteractionGroup)
        self.expandLayout.addWidget(self.VolumnGroup)
        self.expandLayout.addWidget(self.PersonalGroup)
        self.expandLayout.addWidget(self.ShortcutGroup)
        self.expandLayout.addWidget(self.AboutGroup)

    def __setQss(self):
        """ set style sheet """
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')

        theme = 'light' #if isDarkTheme() else 'light'
        with open(os.path.join(basedir, 'res/icons/system/qss/', theme, 'setting_interface.qss'), encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def _AlwaysOnTopChanged(self, isChecked):
        if isChecked:
            settings.on_top_hint = True
            settings.save_settings()
            self.ontop_changed.emit()
        else:
            settings.on_top_hint = False
            settings.save_settings()
            self.ontop_changed.emit()

    def _AllowDropChanged(self, isChecked):
        if isChecked:
            settings.set_fall = True
        else:
            settings.set_fall = False
        settings.save_settings()

    def _AutoLockChanged(self, isChecked):
        if isChecked:
            settings.auto_lock = True
        else:
            settings.auto_lock = False
        settings.save_settings()

    def _AutoStartChanged(self, isChecked):
        set_autostart(isChecked)

    def _GravityChanged(self, value):
        settings.gravity = value*0.01
        settings.save_settings()

    def _DragChanged(self, value):
        settings.fixdragspeedx, settings.fixdragspeedy = value*0.01, value*0.01
        settings.save_settings()

    def _VolumnChanged(self, value):
        settings.volume = round(value*0.1, 3)
        settings.save_settings()

    def _ScaleChanged(self, value):
        settings.tunable_scale = value*0.1
        settings.scale_dict[settings.petname] = settings.tunable_scale
        settings.save_settings()
        self.scale_changed.emit()

    def _update_scale(self):
        self.ScaleCard.setValue(int(settings.tunable_scale*10))

    def _DefaultPetChanged(self, value):
        settings.default_pet = value
        settings.save_settings()

    def _LanguageChanged(self, value):
        settings.language_code = settings.lang_dict[value]
        settings.save_settings()
        settings.change_translator(settings.lang_dict[value])
        #self.retranslateUi()
        self.__showRestartTooltip()
        self.lang_changed.emit()
    
    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.warning(
            '',
            self.tr('Configuration takes effect after restart\n此设置在重启后生效'),
            duration=3000,
            position=InfoBarPosition.BOTTOM,
            parent=self.window()
        )

    def colorChanged(self, color_str):
        setThemeColor(color_str)
        settings.themeColor = color_str
        settings.save_settings()

    def _checkUpdate(self):
        local_version = settings.VERSION
        success, github_version, full_urls, src_urls, notes = get_latest_release()
        if success:
            update_needed = compare_versions(local_version, github_version)
            if update_needed:
                # 提示里显示【新版本号】，而不是当前版本号
                return True, github_version + "  " + self.tr("New version available"), full_urls, src_urls, notes
            else:
                return False, local_version + "  " + self.tr("Already the latest"), [], [], ""
        else:
            return False, self.tr("无法连接 GitHub：请检查网络/代理（需与浏览器一致的出口），或手动查看 ") + settings.RELEASE_URL, [], [], ""

    def _onCheckUpdateClicked(self, silent=False):
        # 记住是否静默（启动自动检测时为 True），供 _showUpdateResult 决定是否弹"无更新"提示
        self._update_check_silent = silent
        # 网络请求放到后台线程，避免界面卡顿（GitHub 国内访问可能较慢）
        if not silent:
            InfoBar.info(
                title=self.tr('检查更新'),
                content=self.tr('正在检查新版本...'),
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )

        def _worker():
            try:
                has_update, info, full_urls, src_urls, notes = self._checkUpdate()
            except Exception as e:
                print('[CheckUpdate] worker exception:', e)
                has_update, info, full_urls, src_urls, notes = False, self.tr('检查更新失败：网络异常或无法访问 GitHub，请稍后重试。'), [], [], ""
            # 跨线程用 Signal 回主线程（QTimer 在 worker 线程无事件循环不会触发）。
            # 仅回传结果，是否下载安装交由用户在确认框里决定。
            self.checkUpdateFinished.emit(has_update, info, full_urls, src_urls, notes)
        threading.Thread(target=_worker, daemon=True).start()

    def _showUpdateResult(self, has_update, info, full_urls, src_urls, notes):
        # 同时把结果写回卡片副标题，确保一定可见
        try:
            self.CheckUpdateCard.setContent(info)
        except Exception:
            pass
        if has_update and (full_urls or src_urls):
            # 发现新版本 -> 弹出更新对话框（Cherry Studio 风格）
            self._ask_install_update(info, src_urls, full_urls, notes)
        elif has_update:
            InfoBar.warning(
                title=self.tr('发现新版本'),
                content=self.tr('已检测到新版本，但未获取到安装包下载地址，请前往项目主页手动更新。'),
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )
        else:
            # 静默模式（启动自动检测）下不弹"无更新"提示，避免打扰用户
            if not getattr(self, '_update_check_silent', False):
                InfoBar.info(
                    title=self.tr('检查更新'),
                    content=info,
                    duration=4000,
                    position=InfoBarPosition.TOP,
                    parent=self.window()
                )

    def _ask_install_update(self, info, src_urls, full_urls, notes):
        # 从 info 里取出版本号（形如 "v1.0.2  New version available"）
        ver = info.split()[0] if info else ""
        self._current_src_urls = src_urls
        self._current_full_urls = full_urls
        try:
            dlg = UpdateDialog(self, ver, notes)
            self._update_dlg = dlg
            # 连接下载/应用进度到对话框（先断开旧连接，避免多次检查更新重复绑定）
            for sig in (self.downloadProgress, self.downloadFinished, self.patchProgress):
                try:
                    sig.disconnect()
                except Exception:
                    pass
            self.downloadProgress.connect(dlg.set_progress)
            self.downloadFinished.connect(dlg.on_downloaded)
            self.patchProgress.connect(dlg.set_patch_progress)
            dlg.finished.connect(lambda _=None: self._disconnect_update_signals(dlg))
            # 必须用 exec() 才能强制模态并前置到父窗口之上；show() 在 setModal(True) 下可能
            # 因为父窗口焦点问题导致对话框不显示或被遮挡，表现为"点了没反应"。
            dlg.exec()
        except Exception as e:
            _update_log(f"update dialog failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    def _disconnect_update_signals(self, dlg):
        for sig in (self.downloadProgress, self.downloadFinished, self.patchProgress):
            try:
                sig.disconnect(dlg.set_progress)
                sig.disconnect(dlg.on_downloaded)
                sig.disconnect(dlg.set_patch_progress)
            except Exception:
                pass

    def _startUpdate(self, src_urls, full_urls):
        # 每次开始下载前新建取消事件，旧的（如有）先置取消避免泄漏
        self._dl_cancel_event = threading.Event()

        def _dl_worker():
            try:
                proxies = _detect_system_proxies()
                # 1) 优先增量更新：下载源码包（约几百 KB）覆盖安装目录的 DyberPet/。
                #    安装目录无写权限（如 C:\Program Files）时，_apply_patch 内部自动弹 UAC 提权。
                if src_urls:
                    dest = os.path.join(tempfile.gettempdir(), "LiuYi_source_patch.zip")
                    self.downloadProgress.emit(0, self.tr("开始下载增量更新包..."))
                    download_file(src_urls, dest, proxies,
                                  lambda p, m: self.downloadProgress.emit(p, m),
                                  cancel_event=self._dl_cancel_event)
                    self.downloadFinished.emit(True, dest)
                    return
                # 2) 回退：完整安装包
                if full_urls:
                    dest = os.path.join(tempfile.gettempdir(), "LiuYi_Setup_new.exe")
                    self.downloadProgress.emit(0, self.tr("开始下载完整安装包..."))
                    download_file(full_urls, dest, proxies,
                                  lambda p, m: self.downloadProgress.emit(p, m),
                                  cancel_event=self._dl_cancel_event)
                    self.downloadFinished.emit(True, dest)
                    return
                raise RuntimeError(self.tr("未获取到更新包下载地址，请前往项目主页手动更新。"))
            except Exception as e:
                _update_log(f"auto update failed: {type(e).__name__}: {e}")
                self.downloadFinished.emit(False, str(e))
        threading.Thread(target=_dl_worker, daemon=True).start()

    def _cancelDownload(self):
        if getattr(self, '_dl_cancel_event', None) is not None:
            self._dl_cancel_event.set()

    def _installAndRestart(self, payload):
        """应用增量更新（解压覆盖 DyberPet/）并在完成后重启。后台线程执行。"""
        if not payload:
            return
        self.patchProgress.emit(0, self.tr("正在应用更新..."))
        def _patch_worker():
            try:
                install_dir = os.path.dirname(sys.executable)
                self._apply_patch(payload)  # 覆盖 DyberPet/，无权限时内部弹 UAC
                self.patchProgress.emit(100, self.tr("更新完成，即将重启..."))
                self.restartRequested.emit()
            except Exception as e:
                _update_log(f"apply patch failed: {type(e).__name__}: {e}")
                self.patchProgress.emit(-1, str(e))
        threading.Thread(target=_patch_worker, daemon=True).start()

    def _onRestartRequested(self):
        """增量更新应用完成后，启动新进程并退出当前进程（释放单例锁）。"""
        try:
            env = dict(os.environ)
            env['DYBERPET_RELAUNCH'] = '1'
            subprocess.Popen([sys.executable], env=env)
        except Exception as e:
            _update_log(f"restart failed: {type(e).__name__}: {e}")
        app = QApplication.instance()
        if app is not None:
            app.quit()
        os._exit(0)

    def _launch_installer_exe(self, payload):
        """回退路径：完整安装包（exe）以管理员权限（UAC 提权）静默安装并退出当前程序。
        用于没有增量源码包、或增量失败后的兜底。当前进程必须退出以释放被锁定的 exe。"""
        install_dir = os.path.dirname(sys.executable)
        try:
            params = f'--silent --target "{install_dir}" --keep-data'
            # 使用 ctypes ShellExecuteW("runas") 触发 UAC 提权；直接 Popen 不会弹 UAC。
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", payload, params, None, 1)
            if ret <= 32:
                raise OSError(f"ShellExecuteW failed, ret={ret}")
        except Exception as e:
            _update_log(f"launch installer failed: {type(e).__name__}: {e}")
            InfoBar.error(
                title=self.tr('启动安装失败'),
                content=str(e)[:120],
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )
            return
        # 退出当前程序，释放被锁定的 exe，交由提权后的静默安装接管
        app = QApplication.instance()
        if app is not None:
            app.quit()
        os._exit(0)

    def _apply_patch(self, zip_path):
        """解压源码补丁包并覆盖安装目录的 DyberPet/（增量更新核心步骤）。
        安装目录无写权限（如 C:\\Program Files）时自动弹 UAC 提权完成复制；
        提权仍失败才由调用方回退完整安装包。"""
        tmp = os.path.join(tempfile.gettempdir(), "LiuYi_patch_extract")
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        src = os.path.join(tmp, "DyberPet")
        if not os.path.isdir(src):
            raise FileNotFoundError(self.tr("补丁包结构异常：缺少 DyberPet/"))
        install_dir = os.path.dirname(sys.executable)
        dst = os.path.join(install_dir, "DyberPet")
        try:
            self._copytree_overwrite(src, dst)
        except PermissionError:
            _update_log("patch write denied, try UAC elevation")
            self._apply_patch_elevated(src, dst)
        # 校验：目标目录出现新版 settings.py 才算成功
        if not os.path.isfile(os.path.join(dst, 'settings.py')):
            raise PermissionError(self.tr("更新未完成，请手动以管理员身份运行安装程序更新。"))
        return dst

    def _apply_patch_elevated(self, src, dst):
        """以管理员身份（UAC 提权弹窗）把 src 复制到安装目录 dst。
        用于安装目录受保护（如 C:\\Program Files）且普通用户无写权限的情况。"""
        sys_tmp = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
        os.makedirs(sys_tmp, exist_ok=True)
        stage = os.path.join(sys_tmp, "LiuYi_patch_stage", "DyberPet")
        if os.path.isdir(os.path.dirname(stage)):
            shutil.rmtree(os.path.dirname(stage))
        self._copytree_overwrite(src, stage)
        # 用 ShellExecuteEx + runas 弹 UAC，提权后 robocopy 复制（只动 DyberPet/ 目录）
        params = '/c robocopy "%s" "%s" /E /IS /R:0 /W:0' % (stage, dst)
        try:
            _run_elevated("cmd.exe", params)
        except Exception as e:
            raise PermissionError(self.tr("提权复制失败（已取消或出错）：") + str(e))
        if not os.path.isfile(os.path.join(dst, 'settings.py')):
            raise PermissionError(self.tr("提权复制未完成，请手动以管理员身份运行安装程序更新。"))

    def _copytree_overwrite(self, src, dst):
        """递归覆盖拷贝（仅拷贝文件，目录自动创建）。无写权限会抛 PermissionError。"""
        if not os.path.isdir(dst):
            shutil.copytree(src, dst)
            return
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            target_root = dst if rel == '.' else os.path.join(dst, rel)
            os.makedirs(target_root, exist_ok=True)
            for f in files:
                s = os.path.join(root, f)
                t = os.path.join(target_root, f)
                shutil.copy2(s, t)

    def _AllowToasterChanged(self, isChecked):
        if isChecked:
            settings.toaster_on = True
        else:
            settings.toaster_on = False
        settings.save_settings()

    def _AllowBubbleChanged(self, isChecked):
        if isChecked:
            settings.bubble_on = True
        else:
            settings.bubble_on = False
        settings.save_settings()

    def _AllowPoopChanged(self, isChecked):
        if isChecked:
            settings.poop_enabled = True
        else:
            settings.poop_enabled = False
        settings.save_settings()





def _detect_system_proxies():
    """检测系统代理。优先用 urllib.request.getproxies()（Windows 下读注册表），再读环境变量，最后读注册表。"""
    # 1. Python 内置跨平台代理检测，Windows 下会读 IE/系统代理设置
    try:
        proxies = urllib.request.getproxies()
        if proxies:
            result = {}
            for k in ('http', 'https'):
                if k in proxies and proxies[k]:
                    result[k] = proxies[k]
            if result:
                return result
    except Exception:
        pass

    # 2. 环境变量兜底（兼容用户通过脚本/终端设置代理的场景）
    try:
        result = {}
        for k in ('http', 'https'):
            v = os.environ.get(k + '_proxy') or os.environ.get(k.upper() + '_PROXY')
            if v:
                result[k] = v
        if result:
            return result
    except Exception:
        pass

    # 3. 最后兜底：手动读注册表
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enabled:
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if not server:
                return None
        server = server.strip()
        if "=" in server:
            result = {}
            for part in server.split(";"):
                if "=" in part:
                    scheme, addr = part.split("=", 1)
                    scheme = scheme.strip().lower()
                    addr = addr.strip()
                    if addr:
                        result[scheme] = addr if addr.startswith("http") else f"http://{addr}"
            if "https" not in result and "http" in result:
                result["https"] = result["http"]
            return result if result else None
        else:
            addr = server if server.startswith("http") else f"http://{server}"
            return {"http": addr, "https": addr}
    except Exception:
        return None


def _update_log(message):
    """把检查更新诊断日志写到数据目录，方便排查。"""
    try:
        log_dir = os.path.join(settings.CONFIGDIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'update_check.log')
        from datetime import datetime
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} {message}\n")
    except Exception:
        pass


def _http_get_json(url, proxies=None, timeout=15):
    """发起 GET 请求并返回 (status_code, body_bytes) 或抛出异常。"""
    req = urllib.request.Request(url, headers={
        'User-Agent': f'LiuYiDesktopPet/{settings.VERSION}',
        'Accept': 'application/vnd.github+json',
    })
    if proxies:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
        response = opener.open(req, timeout=timeout)
    else:
        response = urllib.request.urlopen(req, timeout=timeout)
    with response:
        return response.status, response.read()


# 国内 GitHub 镜像加速列表（按可用性排序）。
# 这些镜像通过「前置完整 github 链接」的方式代理 releases 文件下载，例如：
#   https://ghproxy.net/https://github.com/ChanChauncey/dyberpet-liuyi/releases/download/v1.0.4/LiuYi_Setup.exe
# 下载时优先尝试镜像，全部失败再回退官方直链，避免国内直连 GitHub 被限流/卡死。
GITHUB_MIRRORS = [
    "https://ghproxy.net/",
    "https://ghproxy.com/",
    "https://mirror.ghproxy.com/",
    "https://gh.api.99988866.xyz/",
]


def _mirror_urls(browser_url):
    """把官方 browser_download_url 转成各镜像的完整下载地址列表。"""
    if not browser_url:
        return []
    return [m + browser_url for m in GITHUB_MIRRORS]


def get_latest_release():
    """拉取最新 Release：返回 (success, tag_name, full_urls, src_urls, notes)。

    - full_urls / src_urls 均为下载地址列表，已按「国内镜像优先、官方直链兜底」排序，
      download_file() 会依次尝试，因此国内用户首跳即为加速镜像。
    - src_urls 指向增量源码包 DyberPet_source.zip（仅应用源码，覆盖安装目录 DyberPet/ 即可）。
    - notes 为 Release 正文（更新日志，Markdown），供更新弹窗渲染。
    """
    url = settings.RELEASE_API
    try:
        proxies = _detect_system_proxies()
        status, body = _http_get_json(url, proxies=proxies, timeout=20)
        data = json.loads(body)
        tag = data.get('tag_name')
        notes = data.get('body') or ''
        assets = data.get('assets', [])
        full_api = full_browser = None
        src_api = src_browser = None
        for a in assets:
            name = (a.get('name') or '').lower()
            if name.startswith('liuyi_setup') and name.endswith('.exe'):
                full_api = a.get('url')
                full_browser = a.get('browser_download_url')
            elif name == 'dyberpet_source.zip':
                src_api = a.get('url')
                src_browser = a.get('browser_download_url')
        full_urls = _mirror_urls(full_browser) + [u for u in (full_browser, full_api) if u]
        src_urls = _mirror_urls(src_browser) + [u for u in (src_browser, src_api) if u]
        return True, tag, full_urls, src_urls, notes
    except Exception as e:
        _update_log(f"get_latest_release failed: {type(e).__name__}: {e}")
        return False, None, [], [], ''


def download_file(urls, dest, proxies, on_progress, cancel_event=None):
    """流式下载文件并回调进度 (percent, message)。

    urls 可以是单个 URL 字符串或 URL 列表；依次尝试，每个 URL 失败自动重试 2 次。
    支持取消（cancel_event）和低速超时，避免网络被限速时卡死。
    """
    import time
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        raise ValueError("no download URLs provided")

    last_err = None
    # 连接/单次读取超时：30s 足够，过长会让「卡住」感知变差
    IO_TIMEOUT = 30
    # 低速判定：如果 20s 内没有读到任何新数据，视为卡死
    STALL_TIMEOUT = 20

    for url in urls:
        for attempt in range(3):
            try:
                headers = {'User-Agent': f'LiuYiDesktopPet/{settings.VERSION}'}
                # api.github.com 的 asset URL 必须加这个头才会 302 到真实下载地址
                if 'api.github.com' in url:
                    headers['Accept'] = 'application/octet-stream'
                req = urllib.request.Request(url, headers=headers)
                if proxies:
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
                    resp = opener.open(req, timeout=IO_TIMEOUT)
                else:
                    resp = urllib.request.urlopen(req, timeout=IO_TIMEOUT)
                total = resp.headers.get('Content-Length')
                total = int(total) if total else 0
                downloaded = 0
                chunk = 8192 * 4  # 32KB，让进度更新更频繁，也更容易检测低速
                last_data_time = time.time()
                with open(dest, 'wb') as f:
                    while True:
                        if cancel_event and cancel_event.is_set():
                            raise InterruptedError("用户取消下载")
                        # 低速保护：若长时间未读到数据，主动放弃当前连接重试
                        if time.time() - last_data_time > STALL_TIMEOUT:
                            raise TimeoutError(f"下载停滞超过 {STALL_TIMEOUT}s，尝试切换线路")
                        try:
                            buf = resp.read(chunk)
                        except TimeoutError:
                            raise
                        except Exception:
                            # 某些被墙/限速环境 read 会抛 IncompleteRead 等，统一按失败重试
                            raise
                        if not buf:
                            break
                        f.write(buf)
                        downloaded += len(buf)
                        last_data_time = time.time()
                        if total:
                            pct = int(downloaded / total * 100)
                            on_progress(pct, "下载中 {}% ({:.1f} MB / {:.1f} MB)".format(
                                pct, downloaded / 1024 / 1024, total / 1024 / 1024))
                        else:
                            on_progress(0, "下载中 {:.1f} MB".format(downloaded / 1024 / 1024))
                # 简单校验：若服务端给了 Content-Length，下载大小必须一致
                if total and downloaded != total:
                    raise IOError(f"下载不完整：{downloaded}/{total}")
                on_progress(100, "下载完成")
                return
            except Exception as e:
                last_err = e
                _update_log(f"download_file attempt {attempt+1}/3 for {url} failed: {type(e).__name__}: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
    raise last_err if last_err else RuntimeError("all download attempts failed")


def get_latest_version(timeout=20):
    """向 GitHub 拉取最新 Release 版本号。

    返回 (success: bool, version_or_None)
    - 网络不可达 / 超时 / 接口异常 -> (False, None)
    - 拉取成功 -> (True, tag_name 字符串)

    依次尝试：Windows 系统代理 -> 直连（urllib 默认已读 HTTP_PROXY/HTTPS_PROXY 环境变量）。
    国内访问 GitHub 常需经系统代理，而 Python urllib 不会自动继承 Windows 系统代理，故显式读取。
    """
    url = settings.RELEASE_API
    _update_log(f"start checking update, url={url}")

    # 构造候选代理列表：系统代理 -> 环境变量代理 -> 直连
    proxies_list = []
    sys_proxy = _detect_system_proxies()
    if sys_proxy:
        proxies_list.append(sys_proxy)
        _update_log(f"detected system proxy: {sys_proxy}")
    else:
        _update_log("no system proxy detected")
    proxies_list.append(None)

    last_err = None
    for proxies in proxies_list:
        label = str(proxies) if proxies else 'direct'
        try:
            _update_log(f"trying {label}")
            status, body = _http_get_json(url, proxies=proxies, timeout=timeout)
            _update_log(f"success via {label}, status={status}")
            data = json.loads(body)
            return True, data.get('tag_name')
        except Exception as e:
            last_err = e
            _update_log(f"failed via {label}: {type(e).__name__}: {e}")
            continue

    # 全部出口都失败（网络不可达 / DNS / 超时 / 限流）
    _update_log(f"all methods failed, last error: {type(last_err).__name__}: {last_err}")
    return False, None

def compare_versions(local_version, github_version):
    # Remove 'v' prefix from version strings
    local_version = local_version.lstrip('v')
    github_version = github_version.lstrip('v')

    # Split version strings into their components
    local_parts = local_version.split('.')
    github_parts = github_version.split('.')

    # Convert version components to integers
    local_numbers = [int(part) for part in local_parts]
    github_numbers = [int(part) for part in github_parts]

    # Compare each component
    for local, github in zip(local_numbers, github_numbers):
        if local < github:
            return True  # User should update
        elif local > github:
            return False  # Local version is ahead

    # If all components are equal, check for additional components
    if len(local_numbers) < len(github_numbers):
        return True  # User should update
    else:
        return False  # Local version is up to date or ahead


def _run_elevated(cmd, params):
    """以管理员身份（UAC 提权弹窗）运行 cmd + params，并等待其结束。
    UAC 被取消时 ShellExecuteEx 返回 0，抛出异常；否则正常返回。"""
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hKeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    ctypes.windll.shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFO)]
    ctypes.windll.shell32.ShellExecuteExW.restype = wintypes.BOOL
    ctypes.windll.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    ctypes.windll.kernel32.WaitForSingleObject.restype = wintypes.DWORD
    ctypes.windll.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    ctypes.windll.kernel32.CloseHandle.restype = wintypes.BOOL

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "runas"
    sei.lpFile = cmd
    sei.lpParameters = params
    sei.nShow = 0  # SW_HIDE：隐藏提权后的控制台窗口（避免更新时弹黑框）
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        raise PermissionError("ShellExecuteEx failed (UAC 可能被取消)")
    if sei.hProcess:
        ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 0xFFFFFFFF)
        ctypes.windll.kernel32.CloseHandle(sei.hProcess)


class UpdateDialog(QDialog):
    """Cherry Studio 风格的更新弹窗：居中卡片，标题+版本、更新日志、进度条+百分比+速度、状态按钮。"""

    def __init__(self, host, version, notes):
        super().__init__(host.window())
        self.host = host
        self.version = version or ""
        self.notes = notes or ""
        self.payload = None
        self.payload_is_exe = False
        self._build_ui()
        self._apply_style()
        self._set_state('idle')

    def _build_ui(self):
        self.setWindowTitle(self.tr("软件更新"))
        self.setMinimumWidth(460)
        self.setMinimumHeight(520)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 24)
        root.setSpacing(14)

        head = QHBoxLayout()
        icon_lbl = QLabel()
        try:
            pix = QIcon(os.path.join(settings.BASEDIR, 'app_icon.png')).pixmap(44, 44)
            icon_lbl.setPixmap(pix)
        except Exception:
            icon_lbl.setText("🐾")
        head.addWidget(icon_lbl)
        head.addSpacing(12)
        vbox = QVBoxLayout()
        self.title_lbl = TitleLabel(self.tr("发现新版本"))
        self.title_lbl.setObjectName("updateTitle")
        self.ver_lbl = QLabel(self.version)
        self.ver_lbl.setObjectName("updateVersion")
        vbox.addWidget(self.title_lbl)
        vbox.addWidget(self.ver_lbl)
        head.addLayout(vbox)
        head.addStretch(1)
        root.addLayout(head)

        self.sub_lbl = QLabel(self.tr("新版已发布，建议尽快更新以获得更好的体验。"))
        self.sub_lbl.setObjectName("updateSub")
        root.addWidget(self.sub_lbl)

        self.log = QTextBrowser()
        self.log.setOpenExternalLinks(True)
        self.log.setMarkdown(self._clean_md(self.notes))
        self.log.setMinimumHeight(180)
        root.addWidget(self.log, 1)

        self.progress = ProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)
        self.progress_lbl = QLabel("")
        self.progress_lbl.setObjectName("updateProgressLbl")
        root.addWidget(self.progress_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.later_btn = PushButton(self.tr("稍后"))
        self.cancel_btn = PushButton(self.tr("取消"))
        self.start_btn = PrimaryPushButton(self.tr("立即更新"))
        self.restart_btn = PrimaryPushButton(self.tr("安装并重启"))
        btn_row.addWidget(self.later_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.restart_btn)
        root.addLayout(btn_row)

        self.later_btn.clicked.connect(self.reject)
        self.cancel_btn.clicked.connect(lambda: self.host._cancelDownload())
        self.start_btn.clicked.connect(self._on_start)
        self.restart_btn.clicked.connect(self._on_restart)

    def _apply_style(self):
        self.setStyleSheet("""
            #updateTitle { font-size: 20px; font-weight: 700; }
            #updateVersion { font-size: 14px; color: #2b88ff; font-weight: 600; }
            #updateSub { font-size: 12px; color: rgba(128,128,128,0.95); }
            #updateProgressLbl { font-size: 12px; color: rgba(128,128,128,0.95); }
            QTextBrowser { border: 1px solid rgba(128,128,128,0.25); border-radius: 8px;
                           padding: 10px; background: rgba(128,128,128,0.06); }
        """)
        try:
            self.log.document().setDocumentMargin(4)
        except Exception:
            pass

    @staticmethod
    def _clean_md(md):
        # GitHub release body 是 markdown；QTextBrowser.setMarkdown 可渲染标题/列表/加粗/链接。
        return (md or "").strip()

    # ---- 状态机 ----
    def _set_state(self, state):
        self._state = state
        if state == 'idle':
            self.progress.hide(); self.progress_lbl.hide()
            self.start_btn.show(); self.start_btn.setEnabled(True)
            self.cancel_btn.hide(); self.restart_btn.hide(); self.later_btn.show()
            self.start_btn.setText(self.tr("立即更新"))
        elif state == 'downloading':
            self.progress.show(); self.progress_lbl.show()
            self.start_btn.hide(); self.cancel_btn.show()
            self.restart_btn.hide(); self.later_btn.hide()
        elif state == 'ready':
            self.progress.setValue(100); self.progress.show(); self.progress_lbl.show()
            self.start_btn.hide(); self.cancel_btn.hide()
            self.restart_btn.show(); self.later_btn.show()
        elif state == 'applying':
            self.progress.show(); self.progress_lbl.show()
            self.start_btn.hide(); self.cancel_btn.hide()
            self.restart_btn.hide(); self.later_btn.hide()
        elif state == 'error':
            self.start_btn.show(); self.start_btn.setEnabled(True)
            self.cancel_btn.hide(); self.restart_btn.hide(); self.later_btn.show()
            self.start_btn.setText(self.tr("重试"))

    # ---- 由 host 信号驱动 ----
    def set_progress(self, pct, msg):
        if getattr(self, '_state', 'idle') != 'downloading':
            self._set_state('downloading')
        self.progress.setValue(max(0, pct))
        self.progress_lbl.setText(msg)

    def on_downloaded(self, ok, payload):
        if ok:
            self.payload = payload
            self.payload_is_exe = payload.endswith('.exe')
            self._set_state('ready')
            if self.payload_is_exe:
                self.progress_lbl.setText(self.tr("完整安装包已下载，点击「安装并重启」完成更新"))
            else:
                self.progress_lbl.setText(self.tr("下载完成，点击「安装并重启」完成更新"))
        else:
            err = str(payload)
            self.payload = None
            if '取消' in err or 'InterruptedError' in err or 'cancel' in err.lower():
                self.reject()
                return
            self.progress_lbl.setText(self.tr("下载失败：") + err[:80])
            self._set_state('error')

    def set_patch_progress(self, pct, msg):
        if pct < 0:
            self.progress_lbl.setText(self.tr("更新失败：") + str(msg)[:80])
            self._set_state('error')
            return
        self._set_state('applying')
        self.progress.setValue(max(0, min(100, pct)))
        self.progress_lbl.setText(msg)

    # ---- 按钮回调 ----
    def _on_start(self):
        self._set_state('downloading')
        self.host._startUpdate(self.host._current_src_urls, self.host._current_full_urls)

    def _on_restart(self):
        if not self.payload:
            return
        if getattr(self, 'payload_is_exe', False):
            self.host._launch_installer_exe(self.payload)
        else:
            self.host._installAndRestart(self.payload)