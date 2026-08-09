# -*- coding: utf-8 -*-
"""六一桌宠 卸载程序 (windowed, 无控制台)

带图形界面：显示猫 LOGO、安装位置，并提供「保留用户数据」复选框。
- 勾选：先把 install_dir/data/ 中的存档备份到 AppData，再删除整个程序目录。
- 不勾选：直接删除整个安装目录（含存档）。
通过临时副本方式实现自删除。
"""
import os
import sys
import shutil
import tempfile
import subprocess
import time

APP_NAME = "六一桌宠"
CREATE_NO_WINDOW = 0x08000000

# 与安装器 SAVE_FILES 保持一致的用户存档文件
SAVE_FILES = ["settings.json", "pet_data.json", "version",
              "task_data.json", "act_data.json"]


def msg_box(text, title="卸载" + APP_NAME, flags=0x40):
    # 0x40 = ICONINFORMATION
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def get_install_dir():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME)
        val, _ = winreg.QueryValueEx(key, "InstallLocation")
        winreg.CloseKey(key)
        if val and os.path.isdir(val):
            return val
    except Exception:
        pass
    return os.path.dirname(sys.executable)


def save_backup_dir():
    return os.path.join(os.path.expanduser("~"), "AppData", "Local", APP_NAME, "user_data")


def backup_user_data(install_dir):
    """把 install_dir/data/ 中的存档复制到 AppData 备份目录，返回是否备份到内容。"""
    src = os.path.join(install_dir, "data")
    if not os.path.isdir(src):
        return False
    dst = save_backup_dir()
    try:
        os.makedirs(dst, exist_ok=True)
        copied = False
        # 先按已知存档文件名精确复制
        for name in SAVE_FILES:
            s = os.path.join(src, name)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(dst, name))
                copied = True
        # 再兜底复制 data 目录内其余所有文件（防止遗漏自定义存档）
        for root, _dirs, files in os.walk(src):
            for f in files:
                s = os.path.join(root, f)
                rel = os.path.relpath(s, src)
                d = os.path.join(dst, rel)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                if not os.path.exists(d):
                    shutil.copy2(s, d)
                    copied = True
        return copied
    except Exception:
        return False


def kill_pet():
    try:
        subprocess.run(["taskkill", "/f", "/im", APP_NAME + ".exe"],
                       creationflags=CREATE_NO_WINDOW, timeout=5)
    except Exception:
        pass


def remove_registry():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME)
    except Exception:
        pass


def remove_shortcuts():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", APP_NAME + ".lnk")
    try:
        subprocess.run(["cmd", "/c", "del", "/f", "/q", desktop],
                       creationflags=CREATE_NO_WINDOW, timeout=10)
    except Exception:
        pass
    sm_dir = os.path.join(os.environ.get("APPDATA", ""),
                          "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME)
    try:
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", sm_dir],
                       creationflags=CREATE_NO_WINDOW, timeout=10)
    except Exception:
        pass


def delete_install_dir(install_dir):
    try:
        if os.path.isdir(install_dir):
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", install_dir],
                           creationflags=CREATE_NO_WINDOW, timeout=30)
    except Exception:
        pass
    try:
        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir, ignore_errors=True)
    except Exception:
        pass


def _log(msg):
    try:
        log_path = os.path.join(tempfile.gettempdir(), "liuyi_uninst.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("[{}] {}\n".format(time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def self_delete_later(exe_path):
    try:
        subprocess.Popen(
            'cmd /c ping 127.0.0.1 -n 2 > nul & del /f /q "{}"'.format(exe_path),
            shell=True, creationflags=CREATE_NO_WINDOW)
    except Exception:
        pass


# ===== 清理模式：由临时副本调用，删除安装目录并自删 =====
def run_cleanup(install_dir):
    _log("cleanup start: install_dir={}".format(install_dir))
    time.sleep(1)
    delete_install_dir(install_dir)
    _log("delete_install_dir done")
    self_delete_later(sys.executable)
    _log("self_delete_later done")
    msg_box(APP_NAME + " 已卸载完成。", flags=0x40)
    _log("cleanup finished")


def _same_path(a, b):
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    except Exception:
        return a == b


def spawn_cleanup_and_exit(install_dir):
    """复制自身到临时目录，让它删除安装目录并自删，然后主进程强制退出。"""
    exe = sys.executable
    _log("spawn_cleanup_and_exit: exe={}, install_dir={}".format(exe, install_dir))
    if _same_path(os.path.dirname(exe), install_dir):
        tmp = os.path.join(tempfile.gettempdir(), "liuyi_uninst_tmp.exe")
        try:
            shutil.copy2(exe, tmp)
            _log("copied tmp: {}".format(tmp))
            subprocess.Popen([tmp, "--cleanup", install_dir], creationflags=CREATE_NO_WINDOW)
            _log("spawned cleanup process, force exit main")
        except Exception as e:
            _log("spawn cleanup failed: {}".format(e))
    else:
        _log("uninstaller not inside install dir, cleanup in-place")
    # 无论走哪条路，都直接清理一次兜底，并强制结束主进程
    try:
        delete_install_dir(install_dir)
    except Exception as e:
        _log("in-place delete failed: {}".format(e))
    try:
        self_delete_later(exe)
    except Exception as e:
        _log("self_delete_later failed: {}".format(e))
    os._exit(0)


# ===== 图形界面 =====
def run_ui():
    from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QCheckBox,
                                   QPushButton, QVBoxLayout, QHBoxLayout)
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    exe = sys.executable
    app.setWindowIcon(QIcon(exe))

    install_dir = get_install_dir()

    win = QWidget()
    win.setWindowTitle("卸载 " + APP_NAME)
    win.setWindowIcon(QIcon(exe))
    win.setFixedWidth(420)
    win.setStyleSheet("QWidget{font-family:'Microsoft YaHei',SimHei,sans-serif;font-size:13px;}")

    layout = QVBoxLayout(win)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)

    # 猫 LOGO（从 exe 内嵌图标取）
    logo = QLabel()
    logo.setAlignment(Qt.AlignCenter)
    pm = QIcon(exe).pixmap(96, 96)
    if pm.isNull():
        pm = QPixmap(96, 96)
        pm.fill(Qt.transparent)
    logo.setPixmap(pm)
    layout.addWidget(logo)

    title = QLabel("确定要卸载 " + APP_NAME + " 吗？")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size:15px;font-weight:bold;")
    layout.addWidget(title)

    loc = QLabel("安装位置：\n" + install_dir)
    loc.setWordWrap(True)
    loc.setStyleSheet("color:#555;font-size:12px;")
    layout.addWidget(loc)

    cb_keep = QCheckBox("保留用户数据（存档）")
    cb_keep.setChecked(True)
    cb_keep.setToolTip("勾选后，你的游戏存档（等级 / 好感度 / 背包等）会保留在：\n" + save_backup_dir())
    layout.addWidget(cb_keep)

    status = QLabel("")
    status.setStyleSheet("color:#888;font-size:12px;")
    layout.addWidget(status)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)
    btn_cancel = QPushButton("取消")
    btn_uninst = QPushButton("卸载")
    btn_uninst.setStyleSheet(
        "background-color:#e74c3c;color:white;font-weight:bold;padding:6px 18px;border-radius:4px;")
    btn_cancel.setStyleSheet("padding:6px 18px;border-radius:4px;")
    btn_row.addWidget(btn_cancel)
    btn_row.addWidget(btn_uninst)
    layout.addLayout(btn_row)

    def do_uninstall():
        _log("do_uninstall started")
        btn_uninst.setEnabled(False)
        btn_cancel.setEnabled(False)
        keep = cb_keep.isChecked()
        _log("keep user data: {}".format(keep))
        status.setText("正在结束程序进程...")
        app.processEvents()
        kill_pet()
        if keep:
            status.setText("正在备份用户存档...")
            app.processEvents()
            backup_user_data(install_dir)
            _log("backup_user_data done")
        status.setText("正在清理注册表与快捷方式...")
        app.processEvents()
        remove_registry()
        remove_shortcuts()
        _log("registry/shortcuts removed")
        status.setText("正在卸载...")
        app.processEvents()
        spawn_cleanup_and_exit(install_dir)
        # spawn_cleanup_and_exit 会 os._exit(0) 强制退出，不应继续执行
        _log("WARNING: reached after spawn_cleanup_and_exit")
        os._exit(0)

    btn_uninst.clicked.connect(do_uninstall)
    btn_cancel.clicked.connect(win.close)

    win.show()
    sys.exit(app.exec())


def main():
    args = sys.argv[1:]
    if "--cleanup" in args:
        idx = args.index("--cleanup")
        install_dir = args[idx + 1] if idx + 1 < len(args) else get_install_dir()
        run_cleanup(install_dir)
        return
    if "--silent" in args:
        # 静默模式：默认保留用户存档
        install_dir = get_install_dir()
        kill_pet()
        backup_user_data(install_dir)
        remove_registry()
        remove_shortcuts()
        spawn_cleanup_and_exit(install_dir)
        return
    run_ui()


if __name__ == "__main__":
    main()
