# coding:utf-8
import os
import json
import threading
import urllib.request
import urllib.error
from sys import platform
import sys
import subprocess
import tempfile

from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, HyperlinkCard,InfoBar,
                            ComboBoxSettingCard, ScrollArea, ExpandLayout, InfoBarPosition,
                            PushSettingCard, setThemeColor)

from qfluentwidgets import FluentIcon as FIF
from PySide6.QtCore import Qt, Signal, QUrl, QStandardPaths, QLocale, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QProgressDialog, QMessageBox
#from qframelesswindow import FramelessWindow

from .custom_utils import (Dyber_RangeSettingCard, Dyber_ComboBoxSettingCard,
                             CustomColorSettingCard, Dyber_ShortcutCard)
import DyberPet.settings as settings

basedir = settings.BASEDIR
module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')
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
    checkUpdateFinished = Signal(bool, str, str, str)
    downloadProgress = Signal(int, str)
    downloadFinished = Signal(bool, str)

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
        self.downloadProgress.connect(self._onDownloadProgress)
        self.downloadFinished.connect(self._onDownloadFinished)

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
        success, github_version, api_asset_url, browser_url = get_latest_release()
        if success:
            update_needed = compare_versions(local_version, github_version)
            if update_needed:
                # 提示里显示【新版本号】，而不是当前版本号
                return True, github_version + "  " + self.tr("New version available"), api_asset_url or "", browser_url or ""
            else:
                return False, local_version + "  " + self.tr("Already the latest"), "", ""
        else:
            return False, self.tr("无法连接 GitHub：请检查网络/代理（需与浏览器一致的出口），或手动查看 ") + settings.RELEASE_URL, "", ""

    def _onCheckUpdateClicked(self):
        # 网络请求放到后台线程，避免界面卡顿（GitHub 国内访问可能较慢）
        InfoBar.info(
            title=self.tr('检查更新'),
            content=self.tr('正在检查新版本...'),
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=self.window()
        )

        def _worker():
            try:
                has_update, info, api_asset_url, browser_url = self._checkUpdate()
            except Exception as e:
                print('[CheckUpdate] worker exception:', e)
                has_update, info, api_asset_url, browser_url = False, self.tr('检查更新失败：网络异常或无法访问 GitHub，请稍后重试。'), "", ""
            # 跨线程用 Signal 回主线程（QTimer 在 worker 线程无事件循环不会触发）。
            # 仅回传结果，是否下载安装交由用户在确认框里决定。
            self.checkUpdateFinished.emit(has_update, info, api_asset_url or "", browser_url or "")
        threading.Thread(target=_worker, daemon=True).start()

    def _showUpdateResult(self, has_update, info, api_asset_url, browser_url):
        # 同时把结果写回卡片副标题，确保一定可见
        try:
            self.CheckUpdateCard.setContent(info)
        except Exception:
            pass
        # 优先用 api.github.com 的 asset URL（国内通常比 github.com 更稳），失败再回退 browser_download_url
        urls = [u for u in (api_asset_url, browser_url) if u]
        if has_update and urls:
            # 发现新版本 -> 弹出「是否安装」确认框，确认后才下载
            self._ask_install_update(info, urls)
        elif has_update and not urls:
            InfoBar.warning(
                title=self.tr('发现新版本'),
                content=self.tr('已检测到新版本，但未获取到安装包下载地址，请前往项目主页手动更新。'),
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )
        else:
            InfoBar.info(
                title=self.tr('检查更新'),
                content=info,
                duration=4000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )

    def _ask_install_update(self, info, urls):
        # 从 info 里取出版本号（形如 "v1.0.2  New version available"）
        ver = info.split()[0] if info else ""
        box = QMessageBox(self.window())
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(self.tr('发现新版本'))
        box.setText(self.tr('发现新版本 {ver}，是否下载并安装？').format(ver=ver))
        box.setInformativeText(self.tr('安装包将自动下载并静默安装，完成后会自动重启，你的存档数据会保留。'))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setButtonText(QMessageBox.Yes, self.tr('安装'))
        box.setButtonText(QMessageBox.No, self.tr('取消'))
        box.setDefaultButton(QMessageBox.Yes)
        ret = box.exec()
        if ret == QMessageBox.Yes:
            self._startDownload(urls)
        else:
            InfoBar.info(
                title=self.tr('检查更新'),
                content=self.tr('已取消更新，你可以稍后在「关于」中再次检查更新。'),
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )

    def _startDownload(self, urls):
        def _dl_worker():
            try:
                dest = os.path.join(tempfile.gettempdir(), "LiuYi_Setup_new.exe")
                proxies = _detect_system_proxies()
                self.downloadProgress.emit(0, self.tr("开始下载更新..."))
                download_file(urls, dest, proxies,
                              lambda p, m: self.downloadProgress.emit(p, m))
                self.downloadFinished.emit(True, dest)
            except Exception as e:
                _update_log(f"auto download failed: {type(e).__name__}: {e}")
                self.downloadFinished.emit(False, str(e))
        threading.Thread(target=_dl_worker, daemon=True).start()

    def _onDownloadProgress(self, pct, msg):
        if not hasattr(self, '_dl_dlg') or self._dl_dlg is None:
            self._dl_dlg = QProgressDialog(self.tr("正在下载更新..."), "", 0, 100, self.window())
            self._dl_dlg.setWindowTitle(self.tr("自动更新"))
            self._dl_dlg.setAutoClose(False)
            self._dl_dlg.setCancelButton(None)
            self._dl_dlg.show()
        if self._dl_dlg is not None:
            self._dl_dlg.setValue(pct if pct > 0 else 1)

    def _onDownloadFinished(self, ok, payload):
        if getattr(self, '_dl_dlg', None) is not None:
            try:
                self._dl_dlg.close()
            except Exception:
                pass
            self._dl_dlg = None
        if not ok:
            InfoBar.error(
                title=self.tr('下载更新失败'),
                content=self.tr('无法自动下载安装包：') + str(payload)[:120],
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )
            return
        install_dir = os.path.dirname(sys.executable)
        InfoBar.info(
            title=self.tr('下载完成'),
            content=self.tr('即将自动安装更新，请稍候...'),
            duration=1200,
            position=InfoBarPosition.TOP,
            parent=self.window()
        )
        # 延迟一点点让提示可见，然后调起静默安装并退出当前程序
        # （退出是为了释放被锁定的 exe，交给静默安装覆盖写入）
        QTimer.singleShot(1400, lambda: self._launch_installer(payload, install_dir))

    def _launch_installer(self, payload, install_dir):
        try:
            subprocess.Popen([payload, '--silent', '--target', install_dir, '--keep-data'])
        except Exception as e:
            InfoBar.error(
                title=self.tr('启动安装失败'),
                content=str(e)[:120],
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self.window()
            )
            return
        # 退出当前程序，释放被锁定的 exe，交由静默安装接管
        app = QApplication.instance()
        if app is not None:
            app.quit()
        os._exit(0)

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


def get_latest_release():
    """拉取最新 Release：返回 (success, tag_name, api_asset_url, browser_download_url)。

    - api_asset_url: 通过 api.github.com 获取 asset 的下载 URL，在国内通常比 github.com 更稳。
    - browser_download_url: 浏览器下载地址，作为兜底。
    """
    url = settings.RELEASE_API
    try:
        proxies = _detect_system_proxies()
        status, body = _http_get_json(url, proxies=proxies, timeout=20)
        data = json.loads(body)
        tag = data.get('tag_name')
        assets = data.get('assets', [])
        api_asset_url = None
        browser_url = None
        for a in assets:
            if a.get('name', '').lower() == 'liuyi_setup.exe':
                api_asset_url = a.get('url')
                browser_url = a.get('browser_download_url')
                break
        if not browser_url:  # 兜底：取任意 .exe 资产
            for a in assets:
                if a.get('name', '').lower().endswith('.exe'):
                    api_asset_url = a.get('url')
                    browser_url = a.get('browser_download_url')
                    break
        return True, tag, api_asset_url, browser_url
    except Exception as e:
        _update_log(f"get_latest_release failed: {type(e).__name__}: {e}")
        return False, None, None, None


def download_file(urls, dest, proxies, on_progress):
    """流式下载文件并回调进度 (percent, message)。

    urls 可以是单个 URL 字符串或 URL 列表；依次尝试，每个 URL 失败自动重试 2 次。
    优先使用 api.github.com 的 asset URL（带 Accept: application/octet-stream 头），
    它在国内通常比 github.com 的 browser_download_url 更稳。
    """
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        raise ValueError("no download URLs provided")

    last_err = None
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
                    resp = opener.open(req, timeout=60)
                else:
                    resp = urllib.request.urlopen(req, timeout=60)
                total = resp.headers.get('Content-Length')
                total = int(total) if total else 0
                downloaded = 0
                chunk = 8192 * 16
                with open(dest, 'wb') as f:
                    while True:
                        buf = resp.read(chunk)
                        if not buf:
                            break
                        f.write(buf)
                        downloaded += len(buf)
                        if total:
                            on_progress(int(downloaded / total * 100), "下载中 {}%".format(int(downloaded / total * 100)))
                        else:
                            on_progress(0, "下载中 {} KB".format(downloaded // 1024))
                on_progress(100, "下载完成")
                return
            except Exception as e:
                last_err = e
                _update_log(f"download_file attempt {attempt+1}/{3} for {url} failed: {type(e).__name__}: {e}")
                if attempt < 2:
                    import time
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