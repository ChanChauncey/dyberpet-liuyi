"""测试食物气泡文案 — 直接在屏幕上显示气泡效果"""
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dyberpet'))

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath

# 加载气泡配置
conf_path = os.path.join(os.path.dirname(__file__), '..', 'dyberpet', 'res', 'icons', 'bubble_conf.json')
with open(conf_path, 'r', encoding='utf-8') as f:
    bubble_conf = json.load(f)

# 模拟 petname
petname = '六一'

# 构造消息
msg = bubble_conf['feed_required']['message']
msg = msg.replace('PETNAME', petname).replace('USERTAG', '').replace('ITEMNAME', '[薯条]').strip()
print(f"气泡文案: {msg}")

app = QApplication(sys.argv)

# 创建一个半透明的气泡窗口
bubble = QWidget()
bubble.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
bubble.setAttribute(Qt.WA_TranslucentBackground)
bubble.setAttribute(Qt.WA_ShowWithoutActivating)

label = QLabel(msg, bubble)
label.setFont(QFont("Microsoft YaHei", 14))
label.setStyleSheet("""
    QLabel {
        color: #333;
        background-color: rgba(255, 255, 255, 230);
        border: 1px solid #ccc;
        border-radius: 12px;
        padding: 12px 18px;
    }
""")
label.adjustSize()

# 气泡宽度限制
label.setFixedWidth(min(label.width() + 20, 400))
label.setWordWrap(True)
label.adjustSize()

# 窗口大小跟随 label
bubble.setFixedSize(label.size())

# 屏幕居中显示
screen = app.primaryScreen().geometry()
x = (screen.width() - bubble.width()) // 2
y = (screen.height() - bubble.height()) // 2
bubble.move(x, y)
bubble.show()

# 5 秒后自动关闭
QTimer.singleShot(5000, app.quit)

print("气泡显示中，5 秒后自动关闭...")
sys.exit(app.exec())
