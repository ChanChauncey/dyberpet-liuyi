# coding:utf-8
import sys
import os
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (NavigationItemPosition, MessageBox, setTheme, Theme, FluentWindow,
                            NavigationAvatarWidget,  SplitFluentWindow, FluentTranslator)
from qfluentwidgets import FluentIcon as FIF

from .statusUI import statusInterface
from .inventoryUI import backpackInterface
from .shopUI import shopInterface
from .taskUI import taskInterface

from sys import platform
import DyberPet.settings as settings
basedir = settings.BASEDIR
module_path = os.path.join(basedir, 'DyberPet/Dashboard/')

'''
if platform == 'win32':
    basedir = ''
    module_path = 'DyberPet/Dashboard/'
else:
    #from pathlib import Path
    basedir = os.path.dirname(__file__) #Path(os.path.dirname(__file__))
    #basedir = basedir.parent
    basedir = basedir.replace('\\','/')
    basedir = '/'.join(basedir.split('/')[:-2])

    module_path = os.path.join(basedir, 'DyberPet/Dashboard/')
'''

class DashboardMainWindow(FluentWindow):

    def __init__(self, minWidth=650, minHeight=650):
        super().__init__()

        # create sub interface
        self.statusInterface = statusInterface(sizeHintdb=(minWidth, minHeight), parent=self)
        self.backpackInterface = backpackInterface(sizeHintdb=(minWidth, minHeight), parent=self)
        self.shopInterface = shopInterface(sizeHintdb=(minWidth, minHeight), parent=self)
        self.taskInterface = taskInterface(sizeHintdb=(minWidth, minHeight), parent=self)

        self.initNavigation()
        self.setMinimumSize(minWidth, minHeight)
        self.resize(minWidth, minHeight)
        self.initWindow()
        self.__connectSignalToSlot()

    def initNavigation(self):
        # add sub interface
        self.addSubInterface(self.statusInterface,
                             QIcon(os.path.join(basedir, "res/icons/Dashboard/progress.svg")),
                             self.tr('Status'))
        self.addSubInterface(self.backpackInterface,
                             QIcon(os.path.join(basedir, "res/icons/Dashboard/backpack.svg")),
                             self.tr('Backpack'))
        self.addSubInterface(self.shopInterface,
                             QIcon(os.path.join(basedir, "res/icons/Dashboard/shop.svg")),
                             self.tr('Shop'))
        self.addSubInterface(self.taskInterface,
                             QIcon(os.path.join(basedir, "res/icons/Dashboard/task.svg")),
                             self.tr('Daily Tasks'))

        self.navigationInterface.setExpandWidth(150)

    def initWindow(self):
        #self.setMinimumSize(minWidth, minHeight)
        #self.resize(1000, 800)
        self.setWindowIcon(QIcon(os.path.join(basedir, "res/icons/dashboard.svg")))
        self.setWindowTitle(self.tr('Dashboard'))

        desktop = QApplication.primaryScreen().availableGeometry() #QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
    
    def __connectSignalToSlot(self):
        self.backpackInterface.addBuff.connect(self.statusInterface._addBuff)
        self.statusInterface.addCoins.connect(self.backpackInterface.addCoins)
        self.backpackInterface.rmBuff.connect(self.statusInterface._rmBuff)
        self.backpackInterface.coinWidget.coinUpdated.connect(self.shopInterface.coinWidget._update2data)
        self.backpackInterface.item_num_changed.connect(self.shopInterface._updateItemNum)
        # buy&sell
        self.shopInterface.buyItem.connect(self.backpackInterface.add_item)
        self.shopInterface.sellItem.connect(self.backpackInterface.add_item)
        self.shopInterface.updateCoin.connect(self.backpackInterface.addCoins)

        # Task reward
        self.taskInterface.focusPanel.addCoins.connect(self.backpackInterface.addCoins)
        self.taskInterface.progressPanel.addCoins.connect(self.backpackInterface.addCoins)
        self.taskInterface.taskPanel.addCoins.connect(self.backpackInterface.addCoins)

    def show_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.resize(650, 650)
            self.show()

    def show_and_switch(self, panel_name):
        """打开面板并切换到指定子页面"""
        panel_map = {
            'status': self.statusInterface,
            'backpack': self.backpackInterface,
            'shop': self.shopInterface,
            'task': self.taskInterface,
        }
        target = panel_map.get(panel_name)
        if target is None:
            self.show_window()
            return
        if not self.isVisible():
            self.resize(650, 650)
            self.show()
        self.switchTo(target)

    def closeEvent(self, event):
        event.ignore()  # Ignore the close event
        self.hide()





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



















