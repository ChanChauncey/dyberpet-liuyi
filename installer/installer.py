# -*- coding: utf-8 -*-
"""六一桌宠 安装向导 (PySide6)
将已冻结的桌宠程序(payload)打包进单文件 exe，运行后引导用户：
  1) 选择安装路径
  2) 选择组件(桌面快捷方式 / 开始菜单 / 开机自启)
  3) 复制文件、创建快捷方式与注册表卸载项
  4) 可选自动运行
"""
import ctypes
import os
import sys
import shutil
import subprocess

from PySide6.QtWidgets import (
    QApplication, QWidget, QStackedWidget, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QProgressBar, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, QCoreApplication, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap

APP_NAME = "六一桌宠"
PUBLISHER = "爱小瑾的小选"
APP_ID = f"{PUBLISHER}.{APP_NAME}"  # 任务栏分组/图标 ID
# payload 在 _MEIPASS/payload 下；开发模式下用本地已打包好的目录
PAYLOAD_DEV = r"C:\DyberPet\dist_pet\六一桌宠"


def get_payload_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "payload")
    return PAYLOAD_DEV


def get_installed_dir():
    """读取已安装实例的安装目录（来自卸载注册表的 InstallLocation）。
    仅当该目录确实存在且含主程序时返回，否则返回 None。"""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            inst = winreg.QueryValueEx(key, "InstallLocation")[0]
        inst = os.path.normpath(inst)
        if os.path.isdir(inst) and os.path.exists(os.path.join(inst, APP_NAME + ".exe")):
            return inst
    except Exception:
        pass
    return None


def get_default_install_dir():
    # 已安装过则默认升级到原位置
    inst = get_installed_dir()
    if inst:
        return inst
    return os.path.join(r"C:\Program Files", APP_NAME)


# 普通用户没有写入权限的受保护目录
SYSTEM_DIRS = [
    r"C:\Program Files", r"C:\Program Files (x86)",
    r"C:\Windows", r"C:\ProgramData",
]


def need_admin_for(path):
    """判断该路径是否落在需要管理员权限才能写入的系统目录。"""
    p = os.path.normcase(os.path.normpath(path))
    for d in SYSTEM_DIRS:
        d = os.path.normcase(os.path.normpath(d))
        if p == d or p.startswith(d + os.sep):
            return True
    # C 盘根目录(如 C:\) 同样需要管理员
    drive, rest = os.path.splitdrive(p)
    if drive and rest in ("", "\\", "/"):
        return True
    return False


def is_path_writable(path):
    """尝试在目标位置创建临时文件，判断当前用户是否可写入。"""
    try:
        parent = path if os.path.isdir(path) else os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        test = os.path.join(parent, ".writetest_" + str(os.getpid()))
        with open(test, "w") as f:
            f.write("x")
        os.remove(test)
        return True
    except Exception:
        return False


def is_admin():
    """当前进程是否以管理员(Administrator)身份运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin(target, opts):
    """以管理员(UAC)身份重启本安装程序并自动继续安装。"""
    params = ['--resume', '"' + target + '"']
    params += ["--o_desktop", "1" if opts.get("desktop") else "0"]
    params += ["--o_startmenu", "1" if opts.get("startmenu") else "0"]
    params += ["--o_autostart", "1" if opts.get("autostart") else "0"]
    params += ["--o_run", "1" if opts.get("run") else "0"]
    params += ["--o_keepdata", "1" if opts.get("keepdata") else "0"]
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(params), None, 1)
        return True
    except Exception:
        return False


def parse_resume():
    """解析 --resume 参数(管理员提权后自动续装)。"""
    if "--resume" not in sys.argv:
        return None
    args = sys.argv
    target = args[args.index("--resume") + 1].strip('"')
    opts = {"desktop": True, "startmenu": True, "autostart": False,
            "run": False, "keepdata": False}

    def getopt(name, key):
        if name in args:
            opts[key] = args[args.index(name) + 1] == "1"

    getopt("--o_desktop", "desktop")
    getopt("--o_startmenu", "startmenu")
    getopt("--o_autostart", "autostart")
    getopt("--o_run", "run")
    getopt("--o_keepdata", "keepdata")
    return {"target": target, "opts": opts}


# ---------- 进程检测/关闭 ----------
def is_program_running():
    """检测桌宠主程序(六一桌宠.exe)是否正在运行。"""
    name = APP_NAME + ".exe"
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq " + name],
            stderr=subprocess.DEVNULL, timeout=10,
        )
        # 中文 Windows 控制台多为 gbk/cp936，多编码兜底解码
        text = None
        for enc in ("gbk", "cp936", "mbcs", "utf-8"):
            try:
                text = out.decode(enc)
                break
            except Exception:
                continue
        if text is None:
            text = out.decode("utf-8", errors="ignore")
        return name.lower() in text.lower()
    except Exception:
        return False


def kill_program():
    """强制结束桌宠主程序，返回是否成功。"""
    name = APP_NAME + ".exe"
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/IM", name],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
            timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


# ---------- 系统操作辅助 ----------
def create_shortcut(lnk_path, target, workdir, icon, desc=""):
    import win32com.client
    os.makedirs(os.path.dirname(lnk_path), exist_ok=True)
    shell = win32com.client.Dispatch("WScript.Shell")
    sc = shell.CreateShortCut(lnk_path)
    sc.TargetPath = target
    sc.WorkingDirectory = workdir
    sc.IconLocation = icon
    sc.Description = desc
    sc.save()


def write_uninstall_registry(install_dir, with_autostart):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                          '"{}"'.format(os.path.join(install_dir, "uninstall.exe")))
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ,
                          os.path.join(install_dir, APP_NAME + ".exe"))
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception as e:
        raise RuntimeError("写入卸载注册表失败: " + str(e))


def write_autostart(install_dir, enable):
    import winreg
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    exe = os.path.join(install_dir, APP_NAME + ".exe")
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, '"{}"'.format(exe))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        raise RuntimeError("写入开机自启失败: " + str(e))


def remove_autostart():
    import winreg
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass


def remove_uninstall_registry():
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
    except Exception:
        pass


# 游戏存档文件(与主程序 fileOp_utils.SAVEFILES 一致)
SAVE_FILES = ["settings.json", "pet_data.json", "version",
              "task_data.json", "act_data.json"]


def backup_saves(install_dir):
    """把已安装目录中的存档读进内存，返回 {文件名: bytes}。"""
    saves = {}
    data_dir = os.path.join(install_dir, "data")
    if not os.path.isdir(data_dir):
        return saves
    for name in SAVE_FILES:
        p = os.path.join(data_dir, name)
        try:
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    saves[name] = f.read()
        except Exception:
            pass
    return saves


def restore_saves(install_dir, saves):
    """把内存中的存档写回新安装目录。"""
    if not saves:
        return
    data_dir = os.path.join(install_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    for name, blob in saves.items():
        try:
            with open(os.path.join(data_dir, name), "wb") as f:
                f.write(blob)
        except Exception:
            pass


def copy_tree_progress(src, dst, on_progress):
    """复制目录树并回调进度 (percent, message)。"""
    total = sum(len(fs) for _, _, fs in os.walk(src))
    done = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(target, f)
            shutil.copy2(s, d)
            done += 1
            if total:
                on_progress(int(done / total * 100), "复制文件 {} / {}".format(done, total))


# ---------- 安装工作线程 ----------
class InstallWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, src, dst, opts):
        super().__init__()
        self.src = src
        self.dst = dst
        self.opts = opts  # dict: desktop, startmenu, autostart, run

    def run(self):
        try:
            dst = self.dst
            # 重装时可选保留原有存档(等级/好感度/背包等)
            saved = {}
            if self.opts.get("keepdata") and os.path.isdir(dst):
                self.progress.emit(0, "备份原有游戏数据...")
                saved = backup_saves(dst)
            # 目标已存在则先清空(升级/重装)
            if os.path.exists(dst):
                self.progress.emit(0, "清理旧安装目录...")
                shutil.rmtree(dst, ignore_errors=True)
            os.makedirs(dst, exist_ok=True)

            self.progress.emit(2, "开始复制程序文件...")
            copy_tree_progress(self.src, dst, lambda p, m: self.progress.emit(max(2, p * 0.9), m))

            exe = os.path.join(dst, APP_NAME + ".exe")
            if not os.path.exists(exe):
                raise RuntimeError("未找到主程序 " + APP_NAME + ".exe")

            # 还原存档(仅当用户选择保留)
            if saved:
                self.progress.emit(91, "还原原有游戏数据...")
                restore_saves(dst, saved)

            self.progress.emit(92, "创建快捷方式...")
            if self.opts.get("desktop"):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                create_shortcut(
                    os.path.join(desktop, APP_NAME + ".lnk"),
                    exe, dst, exe, APP_NAME)
            if self.opts.get("startmenu"):
                programs = os.path.join(os.environ.get("APPDATA", ""),
                                       "Microsoft", "Windows", "Start Menu", "Programs")
                sm_dir = os.path.join(programs, APP_NAME)
                create_shortcut(
                    os.path.join(sm_dir, APP_NAME + ".lnk"),
                    exe, dst, exe, APP_NAME)
                create_shortcut(
                    os.path.join(sm_dir, "卸载" + APP_NAME + ".lnk"),
                    os.path.join(dst, "uninstall.exe"), dst,
                    os.path.join(dst, "uninstall.exe"), "卸载" + APP_NAME)

            self.progress.emit(96, "写入注册表...")
            write_autostart(dst, self.opts.get("autostart", False))
            write_uninstall_registry(dst, self.opts.get("autostart", False))

            self.progress.emit(100, "安装完成")
            self.finished.emit(True, "安装成功！")
        except Exception as e:
            self.finished.emit(False, "安装失败: " + str(e))


# ---------- 通用样式 ----------
STYLE = """
QWidget {
    background-color: #f5f7fa;
    color: #1f2329;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
}
QLabel#Title { font-size: 22px; font-weight: bold; color: #2b6cb0; }
QLabel#Sub { font-size: 13px; color: #5a6573; }
QLabel#Warn { font-size: 12px; color: #c0392b; font-weight: bold; }
QLineEdit { border: 1px solid #c5ccd6; border-radius: 6px; padding: 6px 8px; background:#ffffff; }
QPushButton {
    background-color: #2b6cb0; color: white; border:none;
    border-radius: 6px; padding: 8px 18px; font-size: 13px;
}
QPushButton:hover { background-color: #2c5282; }
QPushButton#Ghost { background-color: #e2e8f0; color: #2d3748; }
QPushButton#Ghost:hover { background-color: #cbd5e0; }
QPushButton:disabled { background-color: #cbd5e0; color:#718096; }
QCheckBox { spacing: 6px; font-size: 13px; }
QProgressBar { border: 1px solid #c5ccd6; border-radius: 6px; text-align:center; background:#e2e8f0; height: 18px; }
QProgressBar::chunk { background-color: #2b6cb0; border-radius: 5px; }
QPlainTextEdit { border: 1px solid #c5ccd6; border-radius: 6px; background:#ffffff; font-size: 11px; }
QFrame#Sep { background-color: #c5ccd6; }
"""

ACCENT = "#2b6cb0"
LIGHT = "#f5f7fa"


class Page(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(36, 28, 36, 20)
        self.layout.setSpacing(14)


class WelcomePage(Page):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = QLabel("欢迎安装 " + APP_NAME, self)
        t.setObjectName("Title")
        s = QLabel("这是一个会陪你在桌面上散步的小宠物。\n本向导将引导你完成安装。", self)
        s.setObjectName("Sub")
        self.layout.addWidget(t)
        self.layout.addWidget(s)
        self.layout.addStretch(1)
        note = QLabel("点击“下一步”继续。", self)
        note.setObjectName("Sub")
        self.layout.addWidget(note)


class LocationPage(Page):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = QLabel("选择安装位置", self)
        t.setObjectName("Title")
        self.layout.addWidget(t)
        row = QHBoxLayout()
        self.edit = QLineEdit(get_default_install_dir(), self)
        self.browse = QPushButton("浏览...", self)
        self.browse.setObjectName("Ghost")
        self.browse.clicked.connect(self.do_browse)
        row.addWidget(self.edit, 1)
        row.addWidget(self.browse)
        self.layout.addLayout(row)
        self.space = QLabel("", self)
        self.space.setObjectName("Sub")
        self.layout.addWidget(self.space)
        self.warn = QLabel("", self)
        self.warn.setObjectName("Warn")
        self.layout.addWidget(self.warn)
        self.info = QLabel("", self)
        self.info.setObjectName("Sub")
        self.layout.addWidget(self.info)
        if get_installed_dir():
            self.info.setText("检测到已安装版本，将默认升级到以上位置（可手动修改）")
        self.layout.addStretch(1)
        self.edit.textChanged.connect(self.refresh_warn)
        self.refresh_space()
        self.refresh_warn()

    def refresh_space(self):
        try:
            d = os.path.splitdrive(self.edit.text())[0] or "C:"
            total, used, free = shutil.disk_usage(d)
            self.space.setText("目标磁盘剩余空间: {:.1f} GB".format(free / 1024**3))
        except Exception:
            self.space.setText("")

    def refresh_warn(self):
        p = self.get_path()
        if need_admin_for(p) and not is_path_writable(p):
            self.warn.setText("⚠ 该目录受 Windows 保护，需要管理员权限。"
                              "点击“安装”时会自动请求授权（UAC 提权）。")
        else:
            self.warn.setText("")

    def do_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择安装文件夹", self.edit.text())
        if d:
            # Qt 返回的路径用正斜杠，统一转为 Windows 原生反斜杠显示
            d = os.path.normpath(d)
            # 用户选的目录作为父目录，程序装在其中的子目录
            self.edit.setText(os.path.join(d, APP_NAME))
            self.refresh_space()
            self.refresh_warn()

    def get_path(self):
        return os.path.normpath(self.edit.text().strip())


class OptionsPage(Page):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = QLabel("选择组件", self)
        t.setObjectName("Title")
        self.layout.addWidget(t)
        self.cb_desktop = QCheckBox("创建桌面快捷方式", self)
        self.cb_startmenu = QCheckBox("创建开始菜单快捷方式(含卸载)", self)
        self.cb_keepdata = QCheckBox("保留原有游戏数据", self)
        self.cb_autostart = QCheckBox("开机自动启动", self)
        self.cb_desktop.setChecked(True)
        self.cb_startmenu.setChecked(True)
        self.cb_keepdata.setChecked(True)
        self.cb_autostart.setChecked(False)
        for cb in (self.cb_desktop, self.cb_startmenu,
                   self.cb_keepdata, self.cb_autostart):
            self.layout.addWidget(cb)
        self.layout.addStretch(1)

    def get_opts(self):
        return {
            "desktop": self.cb_desktop.isChecked(),
            "startmenu": self.cb_startmenu.isChecked(),
            "autostart": self.cb_autostart.isChecked(),
            "keepdata": self.cb_keepdata.isChecked(),
        }


class ReadyPage(Page):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = QLabel("准备安装", self)
        t.setObjectName("Title")
        self.layout.addWidget(t)
        self.summary = QLabel("", self)
        self.summary.setWordWrap(True)
        self.summary.setObjectName("Sub")
        self.layout.addWidget(self.summary)
        self.layout.addStretch(1)


class ProgressPage(Page):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = QLabel("正在安装...", self)
        t.setObjectName("Title")
        self.layout.addWidget(t)
        self.bar = QProgressBar(self)
        self.bar.setValue(0)
        self.layout.addWidget(self.bar)
        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.layout.addWidget(self.log)
        self.layout.addStretch(1)

    def set_progress(self, pct, msg):
        self.bar.setValue(pct)
        self.log.appendPlainText(msg)


class FinishPage(Page):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = QLabel("安装完成", self)
        t.setObjectName("Title")
        self.layout.addWidget(t)
        self.msg = QLabel("", self)
        self.msg.setObjectName("Sub")
        self.msg.setWordWrap(True)
        self.layout.addWidget(self.msg)
        self.cb_run = QCheckBox("立即启动 " + APP_NAME, self)
        self.cb_run.setChecked(True)
        self.layout.addWidget(self.cb_run)
        self.layout.addStretch(1)


class MainWindow(QWidget):
    def __init__(self, resume=None):
        super().__init__()
        self.resume = resume
        self.setWindowTitle(APP_NAME + " 安装向导")
        self.setMinimumSize(560, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # 标题区
        hdr = QHBoxLayout()
        hdr.setContentsMargins(24, 18, 24, 14)
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setScaledContents(False)
        try:
            # 优先用高清 PNG 显示，避免 ICO 小帧被拉伸
            icon_png = os.path.join(get_payload_dir(), "app_icon.png")
            icon_ico = os.path.join(get_payload_dir(), "app_icon.ico")
            icon_path = icon_png if os.path.exists(icon_png) else icon_ico
            if os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                if not pm.isNull():
                    self.icon_label.setPixmap(
                        pm.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                # 窗口标题栏/任务栏图标用 ICO（含多尺寸）
                if os.path.exists(icon_ico):
                    self.setWindowIcon(QIcon(icon_ico))
        except Exception:
            pass
        hdr.addWidget(self.icon_label)
        htitle = QLabel(APP_NAME + " 安装向导", self)
        htitle.setObjectName("Title")
        hdr.addWidget(htitle)
        hdr.addStretch(1)
        root.addLayout(hdr)
        sep = QFrame(self)
        sep.setObjectName("Sep")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        self.stack = QStackedWidget(self)
        self.p_welcome = WelcomePage()
        self.p_loc = LocationPage()
        self.p_opt = OptionsPage()
        self.p_ready = ReadyPage()
        self.p_prog = ProgressPage()
        self.p_finish = FinishPage()
        for p in (self.p_welcome, self.p_loc, self.p_opt, self.p_ready, self.p_prog, self.p_finish):
            self.stack.addWidget(p)
        root.addWidget(self.stack, 1)

        sep2 = QFrame(self)
        sep2.setObjectName("Sep")
        sep2.setFixedHeight(1)
        root.addWidget(sep2)

        self.nav = QHBoxLayout()
        self.nav.setContentsMargins(24, 14, 24, 18)
        self.btn_cancel = QPushButton("取消", self)
        self.btn_cancel.setObjectName("Ghost")
        self.btn_cancel.clicked.connect(self.on_cancel)
        self.nav.addWidget(self.btn_cancel)
        self.nav.addStretch(1)
        self.btn_back = QPushButton("上一步", self)
        self.btn_back.setObjectName("Ghost")
        self.btn_back.clicked.connect(self.on_back)
        self.btn_next = QPushButton("下一步", self)
        self.btn_next.clicked.connect(self.on_next)
        self.nav.addWidget(self.btn_back)
        self.nav.addWidget(self.btn_next)
        root.addLayout(self.nav)

        self.worker = None
        self.update_nav()
        if resume:
            self.p_loc.edit.setText(resume["target"])
            self.p_loc.refresh_warn()
            o = resume["opts"]
            self.p_opt.cb_desktop.setChecked(o["desktop"])
            self.p_opt.cb_startmenu.setChecked(o["startmenu"])
            self.p_opt.cb_autostart.setChecked(o["autostart"])
            QTimer.singleShot(400, self.start_install)

    def update_nav(self):
        i = self.stack.currentIndex()
        self.btn_back.setVisible(i > 0 and i < 5)
        self.btn_cancel.setVisible(i < 5)
        if i < 3:
            self.btn_next.setText("下一步")
            self.btn_next.setVisible(True)
        elif i == 3:
            self.btn_next.setText("安装")
            self.btn_next.setVisible(True)
        else:
            self.btn_next.setVisible(False)
        # 非完成页：确保“取消”按钮回到导航栏左侧首位
        if i < 5 and self.nav.indexOf(self.btn_cancel) != 0:
            self.nav.removeWidget(self.btn_cancel)
            self.nav.insertWidget(0, self.btn_cancel)

    def on_next(self):
        i = self.stack.currentIndex()
        if i == 2:  # 选项 -> 准备
            opts = self.p_opt.get_opts()
            lines = ["安装位置: " + self.p_loc.get_path()]
            lines.append("桌面快捷方式: " + ("是" if opts["desktop"] else "否"))
            lines.append("开始菜单: " + ("是" if opts["startmenu"] else "否"))
            lines.append("开机自启: " + ("是" if opts["autostart"] else "否"))
            self.p_ready.summary.setText("\n".join(lines))
        if i == 3:  # 准备 -> 开始安装
            self.start_install()
            return
        self.stack.setCurrentIndex(i + 1)
        self.update_nav()

    def on_back(self):
        i = self.stack.currentIndex()
        if i > 0:
            self.stack.setCurrentIndex(i - 1)
            self.update_nav()

    def on_cancel(self):
        if self.worker and self.worker.isRunning():
            return
        # 完成页：点“完成”时按勾选决定是否启动程序
        if self.stack.currentIndex() == 5:
            try:
                if getattr(self.p_finish, "cb_run", None) and self.p_finish.cb_run.isChecked():
                    exe = os.path.join(getattr(self, "install_dst", ""), APP_NAME + ".exe")
                    if exe and os.path.exists(exe):
                        subprocess.Popen([exe], cwd=self.install_dst)
            except Exception:
                pass
        self.close()

    def start_install(self):
        dst = self.p_loc.get_path()
        self.install_dst = dst
        if not dst:
            QMessageBox.warning(self, "提示", "请先选择安装位置。")
            return
        # 安装前检测桌宠是否在运行：运行中的 exe 会被系统锁文件，
        # 覆盖写入会导致安装异常/旧文件残留，故先提醒并可由安装程序代为关闭
        if is_program_running():
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("检测到程序正在运行")
            msg.setText("安装程序检测到「" + APP_NAME + "」正在运行。")
            msg.setInformativeText(
                "继续安装会覆盖其文件，可能导致安装异常或程序崩溃。\n\n"
                "建议先关闭正在运行的程序再继续。是否由安装程序自动关闭它？")
            btn_close = msg.addButton("自动关闭并继续", QMessageBox.AcceptRole)
            msg.addButton("返回", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() == btn_close:
                kill_program()
                # 等进程退出，避免文件仍被占用
                QThread.msleep(1000)
            else:
                self.stack.setCurrentIndex(3)
                self.update_nav()
                return
        # 非续装模式：目标需要管理员权限且当前不可写时，提示以管理员重跑
        if not self.resume and need_admin_for(dst) and not is_admin():
            self.prompt_admin(dst)
            return
        opts = self.p_opt.get_opts()
        self.stack.setCurrentIndex(4)
        self.update_nav()
        self.worker = InstallWorker(get_payload_dir(), dst, opts)
        self.worker.progress.connect(self.p_prog.set_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def prompt_admin(self, dst):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("需要管理员权限")
        msg.setText("无法写入目标目录：\n" + dst)
        msg.setInformativeText(
            "该目录受 Windows 保护，需要管理员权限。\n\n"
            "点「以管理员身份重新运行」可自动完成安装；\n"
            "或点「返回修改路径」换一个用户目录（如默认位置）。")
        btn_admin = msg.addButton("以管理员身份重新运行", QMessageBox.AcceptRole)
        msg.addButton("返回修改路径", QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == btn_admin:
            if not restart_as_admin(dst, self.p_opt.get_opts()):
                QMessageBox.warning(self, "提示",
                    "无法启动管理员安装。请关闭本窗口，右键安装程序选择"
                    "“以管理员身份运行”，再重新安装。")
            else:
                self.close()
        else:
            self.stack.setCurrentIndex(1)
            self.update_nav()

    def on_finished(self, ok, msg):
        if ok:
            self.p_finish.msg.setText(msg)
        else:
            self.p_finish.msg.setText(msg)
        title = self.p_finish.findChild(QLabel, "Title")
        if title:
            title.setText("安装成功" if ok else "安装失败")
        self.stack.setCurrentIndex(5)
        self.update_nav()
        self.btn_cancel.setText("完成")
        self.btn_cancel.setVisible(True)
        # 完成页：把“完成”按钮移到导航栏右侧
        self.nav.removeWidget(self.btn_cancel)
        self.nav.addWidget(self.btn_cancel)


def main():
    resume = parse_resume()
    # 默认以管理员身份运行：非管理员时自动请求 UAC 提升并重启(普通 GUI 模式)
    if not is_admin() and "--resume" not in sys.argv and "--silent" not in sys.argv:
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, "", None, 1)
            sys.exit(0)
        except Exception:
            pass  # 用户拒绝提权则继续以普通身份运行
    # 隐藏的静默安装模式(便于自动化测试与高级用户)
    if "--silent" in sys.argv:
        from PySide6.QtCore import QCoreApplication
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--silent", action="store_true")
        ap.add_argument("--target", default=None)
        ap.add_argument("--keep-data", action="store_true",
                        dest="keep_data", default=False)
        ns = ap.parse_known_args()[0]
        target = ns.target or get_default_install_dir()
        opts = {"desktop": True, "startmenu": True, "autostart": False,
                "run": False, "keepdata": ns.keep_data}
        if need_admin_for(target) and not is_admin():
            # 目标需要管理员权限：自动提权重启本安装程序(保留 --silent 参数)
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0)
            except Exception:
                print("权限不足: 目标目录需要管理员权限 -> " + target)
                print("请以管理员身份运行本安装程序(右键 -> 以管理员身份运行)。")
                sys.exit(2)
        app = QCoreApplication(sys.argv)
        worker = InstallWorker(get_payload_dir(), target, opts)

        def on_finished(ok, msg):
            print(("OK: " if ok else "FAIL: ") + msg)
            if ok:
                # 安装成功后自动启动新版本
                new_exe = os.path.join(target, APP_NAME + ".exe")
                try:
                    subprocess.Popen([new_exe])
                except Exception:
                    pass
            app.exit(0 if ok else 1)

        worker.finished.connect(on_finished)
        worker.progress.connect(lambda p, m: print("[{}%] {}".format(p, m)))
        worker.start()
        sys.exit(app.exec())

    # Windows 任务栏图标：让任务栏把本程序当作独立应用，使用本程序图标
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    w = MainWindow(resume=resume)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
