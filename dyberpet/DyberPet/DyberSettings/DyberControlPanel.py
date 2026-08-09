# coding:utf-8
import sys
import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (NavigationItemPosition, MessageBox, setTheme, Theme, FluentWindow,
                            NavigationAvatarWidget,  SplitFluentWindow, FluentTranslator)
from qfluentwidgets import FluentIcon as FIF

from .BasicSettingUI import SettingInterface
from .GameSaveUI import SaveInterface
from .CharCardUI import CharInterface
from .ItemCardUI import ItemInterface
from sys import platform
import DyberPet.settings as settings
basedir = settings.BASEDIR

module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')


class ControlMainWindow(FluentWindow):

    def __init__(self, minWidth=800, minHeight=800):
        super().__init__()

        # create sub interface
        self.settingInterface = SettingInterface(self)
        self.gamesaveInterface = SaveInterface(sizeHintDyber=(minWidth, minHeight), parent=self)
        self.charCardInterface = CharInterface(sizeHintDyber=(minWidth, minHeight), parent=self)
        self.itemCardInterface = ItemInterface(sizeHintDyber=(minWidth, minHeight), parent=self)

        self.initNavigation()
        self.setMinimumSize(minWidth, minHeight)
        self.initWindow()

    def initNavigation(self):
        # add sub interface
        self.addSubInterface(self.settingInterface, FIF.SETTING, self.tr('Settings'))
        self.addSubInterface(self.gamesaveInterface,
                             FIF.SAVE, #QIcon(os.path.join(module_path, 'resource/saveIcon.svg')),
                             self.tr('Game Save'))
        self.addSubInterface(self.charCardInterface,
                             QIcon(os.path.join(basedir, "res/icons/system/character.svg")),
                             self.tr('Characters'))
        self.addSubInterface(self.itemCardInterface,
                             QIcon(os.path.join(basedir, "res/icons/system/itemMod.svg")),
                             self.tr('Item MOD'))

        # 署名
        self.addSubInterface(
            self._create_credit_page(),
            FIF.INFO,
            '鸣谢',
            position=NavigationItemPosition.BOTTOM
        )

        self.navigationInterface.setExpandWidth(200)

    def _create_credit_page(self):
        """创建鸣谢页面"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
        from PySide6.QtCore import Qt

        scroll = QScrollArea()
        scroll.setObjectName('creditPage')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 36, 50, 40)
        layout.setSpacing(0)

        # ---- 样式常量 ----
        title_style = 'font-size: 22px; font-weight: bold; color: #1a1a2e;'
        section_style = 'font-size: 14px; font-weight: bold; color: #1a1a2e; padding-top: 4px;'
        body_style = 'font-size: 13px; color: #444; line-height: 1.7; padding: 2px 0;'
        step_style = 'font-size: 13px; color: #444; padding: 2px 0 2px 16px;'

        def add_section(text):
            """添加分节标题"""
            layout.addSpacing(20)
            lbl = QLabel(text)
            lbl.setStyleSheet(section_style)
            layout.addWidget(lbl)
            # 标题下划线
            line = QLabel()
            line.setFixedHeight(1)
            line.setStyleSheet('background-color: #e0e0e0; margin-top: 2px;')
            layout.addWidget(line)
            layout.addSpacing(6)

        # ---- 标题 ----
        title = QLabel('鸣谢')
        title.setStyleSheet(title_style)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(8)

        # 分隔线
        top_line = QLabel()
        top_line.setFixedHeight(1)
        top_line.setStyleSheet('background-color: #ccc;')
        layout.addWidget(top_line)
        layout.addSpacing(16)

        # ---- 项目介绍 ----
        p1 = QLabel(
            '[我叫六一] 是我基于 GitHub 开源项目 [DyberPet]'
            '(https://github.com/ChaozhongLiu/DyberPet) 进行的二次开发。'
            '特别感谢 [DyberPet] 提供的框架和设计灵感，让我家的六一'
            '实现了"数字永生"，让它可以在桌面上永远陪伴我。'
        )
        p1.setWordWrap(True)
        p1.setStyleSheet(body_style)
        layout.addWidget(p1)

        # ---- 素材制作流程 ----
        add_section('素材制作流程')

        flow_steps = [
            ('1. 风格生成', '使用 GPT image2 根据猫照片生成皮克斯/迪士尼风格的绿幕图片，保留猫毛等细节特征'),
            ('2. 动作视频', '使用 seedance 2.0 根据绿幕照片生成各类动作视频'),
            ('3. 视频切帧', '让 Claude Code 编写视频切分脚本，逐帧提取为 PNG 序列'),
            ('4. 逐帧抠图', '让 Claude Code 编写抠图脚本，对每一帧进行精细抠图处理'),
            ('5. 部署调试', '将素材部署到项目中，与 Claude Code 反复对话调试，逐组调校动画的播放逻辑'),
        ]
        for title_text, desc in flow_steps:
            step = QLabel(f'<b>{title_text}：</b>{desc}')
            step.setWordWrap(True)
            step.setStyleSheet(step_style)
            layout.addWidget(step)

        # ---- 新增功能 ----
        add_section('在原项目基础上的新增功能')

        features = [
            ('隐身模式', '个人最喜欢的功能。开启后，鼠标移动到猫的位置时猫会自动隐藏、'
                         '鼠标可穿透点击桌面，移开后猫自动恢复显示，解决了猫猫挡住桌面信息的问题'),
            ('铲屎功能', '猫猫会在桌面上产生便便，需要定时清理'),
            ('睡眠系统', '完整的入睡、自然唤醒/交互唤醒动画'),
        ]
        for title_text, desc in features:
            feat = QLabel(f'<b>• {title_text}：</b>{desc}')
            feat.setWordWrap(True)
            feat.setStyleSheet(step_style)
            layout.addWidget(feat)

        # ---- 署名区域 ----
        layout.addSpacing(32)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background-color: #ccc;')
        layout.addWidget(sep)

        layout.addSpacing(16)

        credit_style = 'font-size: 13px; color: #555;'
        credit1 = QLabel('二次开发：@余歌')
        credit1.setAlignment(Qt.AlignCenter)
        credit1.setStyleSheet(credit_style)
        layout.addWidget(credit1)

        layout.addSpacing(4)

        credit2 = QLabel('特别鸣谢：@松鼠')
        credit2.setAlignment(Qt.AlignCenter)
        credit2.setStyleSheet(credit_style)
        layout.addWidget(credit2)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def initWindow(self):
        #self.setMinimumSize(minWidth, minHeight)
        #self.resize(1000, 800)
        self.setWindowIcon(QIcon(os.path.join(basedir, "res/icons/SystemPanel.png")))
        self.setWindowTitle(self.tr('System'))

        desktop = QApplication.primaryScreen().availableGeometry() #QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def show_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def closeEvent(self, event):
        event.ignore()  # Ignore the close event
        self.hide()

    #def _onCharChange(self, char):
    #    self.hide()


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # setTheme(Theme.DARK)

    app = QApplication(sys.argv)

    # install translator
    translator = FluentTranslator()
    app.installTranslator(translator)

    w = ControlMainWindow()
    w.show()
    app.exec_()



















