# 猫拉屎功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现猫随机拉屎功能——屎从猫身体以抛物线飞出落在任务栏上，用户点击消除获得亲密度。

**架构：** Scheduler_worker 每 10 分钟定时检查，30% 概率触发拉屎。PetWidget 接收信号后创建独立的 PoopWidget 窗口，屎以抛物线物理动画落在任务栏上，永久留存直到被点击消除。

**技术栈：** Python 3.12 + PySide6 + APScheduler

---

## 文件结构

| 文件 | 变更 | 职责 |
|------|------|------|
| `dyberpet/DyberPet/settings.py` | 修改 | 新增 `poop_enabled` 开关 + 3 个配置常量 |
| `dyberpet/DyberPet/Poop.py` | **新增** | PoopWidget 类（抛物线动画 + 点击消除） |
| `dyberpet/DyberPet/modules.py` | 修改 | Scheduler_worker 新增 `sig_poop_trigger` 信号 + `check_poop()` 定时任务 |
| `dyberpet/DyberPet/DyberPet.py` | 修改 | 新增 `poop_list` + 信号连接 + `_on_poop_trigger()` + `_on_poop_clicked()` |
| `dyberpet/DyberPet/DyberSettings/BasicSettingUI.py` | 修改 | 新增"允许拉屎"开关 |
| `dyberpet/res/items/Default/poop.png` | **新增** | 屎的 PNG 素材（占位） |

---

### 任务 1：settings.py 新增配置

**文件：** `dyberpet/DyberPet/settings.py`

- [ ] **步骤 1：在模块级常量区域（第 98 行 `AUTOFEED_THRESHOLD` 之后）新增拉屎配置常量**

```python
AUTOFEED_THRESHOLD = 60

# Poop feature
POOP_CHECK_INTERVAL = 10      # 检查间隔（分钟）
POOP_PROBABILITY = 0.3        # 每次检查的触发概率
POOP_FV_REWARD = 3            # 点击消除获得的亲密度
```

- [ ] **步骤 2：在 `init()` 函数中（第 239 行 `focus_timer_on` 附近）新增 global 声明和默认值**

找到：
```python
global focus_timer_on
focus_timer_on = False
```

在其后新增：
```python
global focus_timer_on
focus_timer_on = False

global poop_enabled
poop_enabled = True
```

- [ ] **步骤 3：在 `init_settings()` 的 global 声明（第 277-279 行）末尾加 `poop_enabled`**

找到：
```python
global gravity, fixdragspeedx, fixdragspeedy, tunable_scale, scale_dict, volume, \
       language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
       toaster_on, usertag_dict, auto_lock, bubble_on
```

改为：
```python
global gravity, fixdragspeedx, fixdragspeedy, tunable_scale, scale_dict, volume, \
       language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
       toaster_on, usertag_dict, auto_lock, bubble_on, poop_enabled
```

- [ ] **步骤 4：在 `init_settings()` 中读取 `poop_enabled`（第 367 行 `bubble_on` 之后）**

找到：
```python
# v0.6.7 Bubble can be turned off
bubble_on = data_params.get('bubble_on', True)
#=====================================================
```

在其后新增：
```python
# v0.6.7 Bubble can be turned off
bubble_on = data_params.get('bubble_on', True)
#=====================================================

# Poop feature toggle
poop_enabled = data_params.get('poop_enabled', True)
#=====================================================
```

- [ ] **步骤 5：在 `init_settings()` 的 else 默认值分支（第 388 行 `auto_lock = False` 之后）新增**

找到：
```python
    auto_lock = False
```

改为：
```python
    auto_lock = False
    poop_enabled = True
```

- [ ] **步骤 6：在 `save_settings()` 的 global 声明（第 393-395 行）末尾加 `poop_enabled`**

找到：
```python
global file_path, set_fall, gravity, fixdragspeedx, fixdragspeedy, scale_dict, volume, \
       language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
       toaster_on, usertag_dict, auto_lock, bubble_on
```

改为：
```python
global file_path, set_fall, gravity, fixdragspeedx, fixdragspeedy, scale_dict, volume, \
       language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
       toaster_on, usertag_dict, auto_lock, bubble_on, poop_enabled
```

- [ ] **步骤 7：在 `save_settings()` 的 `data_js` 字典（第 413 行 `auto_lock:auto_lock` 之后）新增**

找到：
```python
           'auto_lock':auto_lock
           }
```

改为：
```python
           'auto_lock':auto_lock,
           'poop_enabled':poop_enabled
           }
```

- [ ] **步骤 8：Commit**

```bash
git add dyberpet/DyberPet/settings.py
git commit -m "feat: settings.py 新增 poop_enabled 开关和拉屎配置常量"
```

---

### 任务 2：创建 PoopWidget 类

**文件：** 创建 `dyberpet/DyberPet/Poop.py`

- [ ] **步骤 1：创建 Poop.py 文件**

```python
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

    def __init__(self, parent=None):
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

        # 加载屎的图片
        self._load_image()

        # 初始化位置：猫身体中心
        self._init_position()

        # 抛物线物理参数
        self.finished = False
        self.v_x = random.uniform(-3, 3)
        self.v_y = random.uniform(-8, -4)
        self.gravity = 0.5

        # 屏幕和地面信息
        screen_geo = settings.current_screen.availableGeometry()
        self.current_screen = settings.current_screen.geometry()
        self.screen_width = screen_geo.width()
        work_height = screen_geo.height()
        settings.compute_floor_offset(settings.current_screen)
        self.floor_pos = (
            self.current_screen.topLeft().y()
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
        """加载屎的 PNG 图片"""
        img_path = os.path.join(
            settings.basedir, 'res', 'items', 'Default', 'poop.png'
        )
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            # 占位：用 48x48 的棕色圆形
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.transparent)
        self.label = QLabel(self)
        self.label.setPixmap(pixmap)
        self.label.setScaledContents(True)
        self.label.resize(pixmap.size())
        self.resize(pixmap.size())

    def _init_position(self):
        """初始位置：猫身体中心"""
        pet_x = settings.widget_pos[0]
        pet_y = settings.widget_pos[1]
        pet_w = self.label.width()
        pet_h = self.label.height()
        start_x = pet_x + pet_w // 2 - self.width() // 2
        start_y = pet_y + pet_h // 3
        self.move(start_x, start_y)

    def _physics_tick(self):
        """每 20ms 执行一次物理计算"""
        if self.finished:
            return

        plus_x = self.v_x
        plus_y = self.v_y
        self.v_y += self.gravity

        new_x = self.x() + plus_x
        new_y = self.y() + plus_y

        # 屏幕边界和落地检测
        new_x, new_y = self._limit_in_screen(new_x, new_y)

        self.move(int(new_x), int(new_y))

    def _limit_in_screen(self, new_x, new_y):
        """屏幕边界检测，落地时停止动画"""
        # 左边界
        if new_x + self.width() // 2 < self.current_screen.topLeft().x():
            new_x = self.current_screen.topLeft().x() - self.width() // 2
        # 右边界
        elif new_x + self.width() // 2 > (
            self.current_screen.topLeft().x() + self.screen_width
        ):
            new_x = (
                self.current_screen.topLeft().x()
                + self.screen_width
                - self.width() // 2
            )
        # 上边界
        if new_y < self.current_screen.topLeft().y():
            new_y = self.current_screen.topLeft().y()
        # 落地（任务栏顶部）
        elif new_y >= self.floor_pos:
            self.finished = True
            new_y = self.floor_pos
            self.timer.stop()

        return new_x, new_y

    def enterEvent(self, event):
        """鼠标悬停：放大 + 手型光标"""
        self.label.setPixmap(
            self.label.pixmap().scaled(
                int(self.label.width() * 1.2),
                int(self.label.height() * 1.2),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def leaveEvent(self, event):
        """鼠标离开：恢复原始大小"""
        self._load_image()
        self.setCursor(QCursor(Qt.ArrowCursor))

    def mousePressEvent(self, event):
        """左键点击：淡出 + 发射信号"""
        if event.button() == Qt.LeftButton and self.finished:
            # 淡出动画
            self._fade_animation()

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
```

- [ ] **步骤 2：验证文件语法**

```bash
cd "D:\Claude专用\桌面宠物\dyberpet"
D:\Python\python.exe -c "from DyberPet.Poop import PoopWidget; print('PoopWidget imported OK')"
```

预期：`PoopWidget imported OK`

- [ ] **步骤 3：Commit**

```bash
git add dyberpet/DyberPet/Poop.py
git commit -m "feat: 新增 PoopWidget 类（抛物线物理 + 点击消除）"
```

---

### 任务 3：Scheduler_worker 新增拉屎定时任务

**文件：** `dyberpet/DyberPet/modules.py`

- [ ] **步骤 1：在 Scheduler_worker 信号定义（第 1114 行 `sig_wake_sche` 之后）新增信号**

找到：
```python
    sig_wake_sche = Signal(name='sig_wake_sche')
```

在其后新增：
```python
    sig_wake_sche = Signal(name='sig_wake_sche')
    sig_poop_trigger = Signal(name='sig_poop_trigger')
```

- [ ] **步骤 2：在 APScheduler 任务注册（第 1173 行 `check_natural_wake` 之后、`self.scheduler.start()` 之前）新增定时任务**

找到：
```python
self.scheduler.add_job(self.check_natural_wake, interval.IntervalTrigger(minutes=1))
self.scheduler.start()
```

改为：
```python
self.scheduler.add_job(self.check_natural_wake, interval.IntervalTrigger(minutes=1))
# 拉屎检查（每 N 分钟检查一次，随机概率触发）
self.scheduler.add_job(
    self.check_poop,
    interval.IntervalTrigger(minutes=settings.POOP_CHECK_INTERVAL),
)
self.scheduler.start()
```

- [ ] **步骤 3：在 Scheduler_worker 类中新增 `check_poop()` 方法（在 `check_natural_wake()` 方法之后）**

找到 `wake_up()` 方法的结束位置，在其后新增：

```python
def check_poop(self):
    """定时检查是否触发拉屎"""
    if not settings.poop_enabled:
        return

    # 30% 概率触发
    if random.random() >= settings.POOP_PROBABILITY:
        return

    # 状态检查：必须在地面、不在睡觉、不在启动、不在弹跳
    if settings.onfloor != 1:
        return
    if settings.is_sleeping:
        return
    if settings.is_starting_up:
        return
    if settings.bouncing:
        return

    self.sig_poop_trigger.emit()
```

- [ ] **步骤 4：Commit**

```bash
git add dyberpet/DyberPet/modules.py
git commit -m "feat: Scheduler_worker 新增 check_poop 定时任务和 sig_poop_trigger 信号"
```

---

### 任务 4：PetWidget 集成拉屎功能

**文件：** `dyberpet/DyberPet/DyberPet.py`

- [ ] **步骤 1：在文件顶部 imports 区域新增 PoopWidget 导入**

在现有的 `from DyberPet.Accessory import DPAccessory` 附近新增：

```python
from DyberPet.Poop import PoopWidget
```

- [ ] **步骤 2：在 `__init__` 中（第 534 行 `self.runScheduler()` 之后）初始化 `poop_list`**

找到：
```python
self.runScheduler()
```

在其后新增：
```python
self.runScheduler()

# 拉屎功能：存活的屎实例列表
self.poop_list = []
```

- [ ] **步骤 3：在 `runScheduler()` 方法中（第 2645 行 `sig_wake_sche` 连接之后）新增信号连接**

找到：
```python
self.workers['Scheduler'].sig_wake_sche.connect(self._wake_pet)
```

在其后新增：
```python
self.workers['Scheduler'].sig_wake_sche.connect(self._wake_pet)
self.workers['Scheduler'].sig_poop_trigger.connect(self._on_poop_trigger)
```

- [ ] **步骤 4：在 PetWidget 类中新增 `_on_poop_trigger()` 和 `_on_poop_clicked()` 方法**

在 `_change_status()` 方法之后新增：

```python
def _on_poop_trigger(self):
    """Scheduler 触发拉屎，创建 PoopWidget"""
    poop = PoopWidget()
    poop.poop_clicked.connect(self._on_poop_clicked)
    self.poop_list.append(poop)

def _on_poop_clicked(self, poop_id):
    """用户点击消除屎，增加亲密度"""
    self._change_status('fv', settings.POOP_FV_REWARD, 'inventory', True)
    # 从列表移除
    self.poop_list = [p for p in self.poop_list if p.poop_id != poop_id]
```

- [ ] **步骤 5：Commit**

```bash
git add dyberpet/DyberPet/DyberPet.py
git commit -m "feat: PetWidget 集成拉屎功能（信号连接 + 触发/消除处理）"
```

---

### 任务 5：设置界面新增"允许拉屎"开关

**文件：** `dyberpet/DyberPet/DyberSettings/BasicSettingUI.py`

- [ ] **步骤 1：在现有开关卡片创建之后（第 155 行 `AllowBubbleCard` 之后）新增 poop 开关**

找到：
```python
self.AllowBubbleCard.switchButton.checkedChanged.connect(self._AllowBubbleChanged)
```

在其后新增：
```python
self.AllowBubbleCard.switchButton.checkedChanged.connect(self._AllowBubbleChanged)

# 允许拉屎开关
self.AllowPoopCard = SwitchSettingCard(
    QIcon(os.path.join(basedir, 'res/icons/system/poop.svg')),
    self.tr("Allow Poop"),
    self.tr("When turned on, the pet will randomly poop on the taskbar"),
    parent=self.VolumnGroup
)
if settings.poop_enabled:
    self.AllowPoopCard.setChecked(True)
else:
    self.AllowPoopCard.setChecked(False)
self.AllowPoopCard.switchButton.checkedChanged.connect(self._AllowPoopChanged)
```

- [ ] **步骤 2：在 `__initLayout()` 中（第 232 行 `VolumnGroup.addSettingCard` 之后）注册到布局**

找到：
```python
self.VolumnGroup.addSettingCard(self.AllowBubbleCard)
```

在其后新增：
```python
self.VolumnGroup.addSettingCard(self.AllowBubbleCard)
self.VolumnGroup.addSettingCard(self.AllowPoopCard)
```

- [ ] **步骤 3：在回调方法区域（第 353 行 `_AllowBubbleChanged` 之后）新增回调**

找到：
```python
def _AllowBubbleChanged(self, isChecked):
    if isChecked:
        settings.bubble_on = True
    else:
        settings.bubble_on = False
    settings.save_settings()
```

在其后新增：
```python
def _AllowPoopChanged(self, isChecked):
    if isChecked:
        settings.poop_enabled = True
    else:
        settings.poop_enabled = False
    settings.save_settings()
```

- [ ] **步骤 4：Commit**

```bash
git add dyberpet/DyberPet/DyberSettings/BasicSettingUI.py
git commit -m "feat: 设置界面新增允许拉屎开关"
```

---

### 任务 6：准备屎的占位素材

**文件：** 创建 `dyberpet/res/items/Default/poop.png`

- [ ] **步骤 1：用 Python 生成一个 48x48 的棕色占位圆形 PNG**

```bash
cd "D:\Claude专用\桌面宠物"
D:\Python\python.exe -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
# 棕色圆形
draw.ellipse([8, 8, 40, 40], fill=(139, 90, 43, 255))
img.save('dyberpet/res/items/Default/poop.png')
print('poop.png created')
"
```

如果 PIL 不可用，用 PySide6 生成：

```bash
D:\Python\python.exe -c "
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
pixmap = QPixmap(48, 48)
pixmap.fill(Qt.transparent)
painter = QPainter(pixmap)
painter.setRenderHint(QPainter.Antialiasing)
painter.setBrush(QBrush(QColor(139, 90, 43)))
painter.setPen(Qt.NoPen)
painter.drawEllipse(8, 8, 32, 32)
painter.end()
pixmap.save('dyberpet/res/items/Default/poop.png')
print('poop.png created')
"
```

- [ ] **步骤 2：验证图片存在**

```bash
ls -la "D:\Claude专用\桌面宠物\dyberpet\res\items\Default\poop.png"
```

预期：文件存在，大小 > 0

- [ ] **步骤 3：Commit**

```bash
git add dyberpet/res/items/Default/poop.png
git commit -m "feat: 添加屎的占位 PNG 素材"
```

---

### 任务 7：集成测试

- [ ] **步骤 1：启动应用验证**

```bash
cd "D:\Claude专用\桌面宠物\dyberpet"
D:\Python\python.exe run_DyberPet.py
```

验证清单：
- [ ] 应用正常启动，猫正常显示
- [ ] 设置面板中出现"允许拉屎"开关
- [ ] 手动测试：临时将 `POOP_CHECK_INTERVAL` 改为 1 分钟，`POOP_PROBABILITY` 改为 1.0，等待 1 分钟观察屎是否生成
- [ ] 屎是否以抛物线飞出并落在任务栏上
- [ ] 鼠标悬停屎是否放大 + 变手型
- [ ] 点击屎是否淡出消失 + 右下角通知显示亲密度增加
- [ ] 关闭"允许拉屎"开关后，屎不再生成
- [ ] 猫在睡觉时屎不生成
- [ ] 隐身模式下屎正常生成且可点击消除

- [ ] **步骤 2：最终 Commit（如果有修复）**

```bash
git add -A
git commit -m "feat: 猫拉屎功能完成（抛物线动画 + 点击消除 + 亲密度奖励 + 设置开关）"
```
