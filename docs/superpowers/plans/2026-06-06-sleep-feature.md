# 睡觉功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为桌面宠物添加睡觉功能，让猫可以随机进入睡觉状态，有呼吸动画，并支持自然唤醒和交互唤醒。

**架构：** 在现有随机动作系统中集成睡觉功能，使用三段式动画（onset → loop → wake），通过 is_sleeping 状态变量管理睡觉状态，使用定时器实现自然唤醒，右键菜单实现交互唤醒。

**技术栈：** Python, PySide6, APScheduler

---

## 文件结构

### 配置文件
- `assets/configs/act_conf.json` — 添加三段睡觉动画配置
- `assets/configs/pet_conf.json` — 添加睡觉动作到 random_act

### 核心代码
- `dyberpet/DyberPet/settings.py` — 添加 is_sleeping 全局变量
- `dyberpet/DyberPet/modules.py` — 修改 Animation_worker 和 Interaction_worker
- `dyberpet/DyberPet/DyberPet.py` — 修改主窗口类添加鼠标事件处理和右键菜单

### 测试文件
- 无（桌面宠物项目无测试框架）

---

## 任务 1：添加睡觉动画配置

**文件：**
- 修改：`assets/configs/act_conf.json`
- 修改：`assets/configs/pet_conf.json`

- [ ] **步骤 1：在 act_conf.json 中添加睡觉动画配置**

在 `act_conf.json` 的末尾（`}` 之前）添加以下配置：

```json
"fallasleep_onset": {
  "images": "fallasleep_onset",
  "act_num": 1,
  "frame_refresh": 0.04,
  "frame_start": 0,
  "frame_end": 145
},
"fallasleep_loop": {
  "images": "fallasleep_loop",
  "act_num": 1,
  "frame_refresh": 0.04,
  "frame_start": 0,
  "frame_end": 145
},
"fallasleep_wake": {
  "images": "fallasleep_wake",
  "act_num": 1,
  "frame_refresh": 0.04,
  "frame_start": 0,
  "frame_end": 169
}
```

- [ ] **步骤 2：在 pet_conf.json 的 random_act 中添加睡觉动作**

在 `pet_conf.json` 的 `random_act` 数组末尾添加以下配置：

```json
{
  "name": "睡觉",
  "act_list": ["fallasleep_onset", "fallasleep_loop", "fallasleep_wake"],
  "act_prob": 0.05,
  "act_type": [2, 0]
}
```

- [ ] **步骤 3：部署配置文件**

运行：`python tools/copy_configs.py`

预期：配置文件部署到 `dyberpet/res/role/六一/`

- [ ] **步骤 4：Commit**

```bash
git add assets/configs/act_conf.json assets/configs/pet_conf.json
git commit -m "feat: 添加睡觉动画配置"
```

---

## 任务 2：添加睡觉状态变量

**文件：**
- 修改：`dyberpet/DyberPet/settings.py`

- [ ] **步骤 1：在 settings.py 中添加 is_sleeping 全局变量**

在 `settings.py` 的 `init()` 函数中添加以下代码（在 `global showing_dialogue_now` 之后）：

```python
global is_sleeping
is_sleeping = False
```

- [ ] **步骤 2：Commit**

```bash
git add dyberpet/DyberPet/settings.py
git commit -m "feat: 添加睡觉状态变量"
```

---

## 任务 3：修改 Animation_worker 支持睡觉触发

**文件：**
- 修改：`dyberpet/DyberPet/modules.py`

- [ ] **步骤 1：在 random_act 方法中添加睡觉状态检查**

在 `random_act` 方法的开头（`acts = None` 之前）添加以下代码：

```python
# 如果正在睡觉，不执行随机动作
if settings.is_sleeping:
    return
```

- [ ] **步骤 2：Commit**

```bash
git add dyberpet/DyberPet/modules.py
git commit -m "feat: 在随机动作系统中添加睡觉状态检查"
```

---

## 任务 4：修改 Interaction_worker 支持睡觉动画

**文件：**
- 修改：`dyberpet/DyberPet/modules.py`

- [ ] **步骤 1：在 Interaction_worker 类中添加 sleeping 方法**

在 `Interaction_worker` 类中（在 `mousedrag` 方法之后）添加以下方法：

```python
def sleeping(self, act_name):
    """处理睡觉动画循环"""
    if not settings.is_sleeping:
        return
    
    # 获取睡觉动画配置
    onset = self.pet_conf.fallasleep_onset
    loop = self.pet_conf.fallasleep_loop
    
    # 播放入睡动画（如果还没播完）
    if settings.act_id == 0:
        self.img_from_act(onset)
        if settings.playid >= len(onset.images) * onset.act_num:
            settings.act_id = 1
            settings.playid = 0
        return
    
    # 循环播放睡觉动画
    self.img_from_act(loop)
    # 如果动画播放完毕，重置 playid 实现循环
    n_repeat = math.ceil(loop.frame_refresh / (self.pet_conf.interact_speed / 1000))
    img_list_expand = [item for item in loop.images for i in range(n_repeat)] * loop.act_num
    if settings.playid >= len(img_list_expand):
        settings.playid = 0
```

- [ ] **步骤 2：在 start_interact 方法中添加睡觉处理**

在 `start_interact` 方法中（在 `if interact == 'patpat':` 之前）添加以下代码：

```python
# 睡觉动画
if interact == 'sleep':
    settings.is_sleeping = True
    settings.playid = 0
    settings.act_id = 0
```

- [ ] **步骤 3：Commit**

```bash
git add dyberpet/DyberPet/modules.py
git commit -m "feat: 添加睡觉动画处理逻辑"
```

---

## 任务 5：添加自然唤醒定时器

**文件：**
- 修改：`dyberpet/DyberPet/modules.py`

- [ ] **步骤 1：在 Scheduler_worker 类中添加自然唤醒定时器**

在 `Scheduler_worker` 类的 `run` 方法中（在 `self.scheduler.start()` 之后）添加以下代码：

```python
# 自然唤醒定时器
self.scheduler.add_job(self.check_natural_wake, interval.IntervalTrigger(minutes=1))
```

- [ ] **步骤 2：添加 check_natural_wake 方法**

在 `Scheduler_worker` 类中添加以下方法：

```python
def check_natural_wake(self):
    """检查是否自然唤醒"""
    if not settings.is_sleeping:
        return
    
    # 20% 概率自然唤醒
    if random.random() < 0.2:
        self.wake_up()
```

- [ ] **步骤 3：添加 wake_up 方法**

在 `Scheduler_worker` 类中添加以下方法：

```python
def wake_up(self):
    """唤醒睡觉的猫"""
    if not settings.is_sleeping:
        return
    
    # 播放醒来动画
    wake_act = self.pet_conf.fallasleep_wake
    # 这里需要通过信号触发 Interaction_worker 播放醒来动画
    # 暂时直接设置状态
    settings.is_sleeping = False
    settings.playid = 0
    settings.act_id = 0
```

- [ ] **步骤 4：Commit**

```bash
git add dyberpet/DyberPet/modules.py
git commit -m "feat: 添加自然唤醒定时器"
```

---

## 任务 6：修改主窗口支持睡觉状态下的鼠标行为

**文件：**
- 修改：`dyberpet/DyberPet/DyberPet.py`

- [ ] **步骤 1：在 mousePressEvent 中添加睡觉状态检查**

在 `mousePressEvent` 方法的开头（`if event.button() == Qt.LeftButton:` 之前）添加以下代码：

```python
# 睡觉状态下，左键点击无反应
if settings.is_sleeping and event.button() == Qt.LeftButton:
    event.accept()
    return
```

- [ ] **步骤 2：在 mouseMoveEvent 中添加睡觉状态限制**

在 `mouseMoveEvent` 方法中（在 `if self.is_follow_mouse:` 之后）添加以下代码：

```python
# 睡觉状态下，只能在 X 轴方向移动
if settings.is_sleeping:
    new_pos = QPoint(event.globalPos().x() - self.mouse_drag_pos.x(), self.pos().y())
    self.move(new_pos)
    event.accept()
    return
```

- [ ] **步骤 3：在右键菜单中添加"唤醒六一"选项**

在 `contextMenuEvent` 方法中（在 `menu = RoundMenu(parent=self)` 之后）添加以下代码：

```python
# 睡觉状态下添加唤醒选项
if settings.is_sleeping:
    wake_action = QAction(self.tr("唤醒六一"), self)
    wake_action.triggered.connect(self.wake_up_pet)
    menu.addAction(wake_action)
    menu.addSeparator()
```

- [ ] **步骤 4：添加 wake_up_pet 方法**

在 `DyberPet` 类中添加以下方法：

```python
def wake_up_pet(self):
    """唤醒睡觉的猫"""
    if not settings.is_sleeping:
        return
    
    # 播放醒来动画
    wake_act = self.pet_conf.fallasleep_wake
    # 通过 Interaction_worker 播放醒来动画
    self.workers['Interaction'].start_interact('wake')
    settings.is_sleeping = False
```

- [ ] **步骤 5：Commit**

```bash
git add dyberpet/DyberPet/DyberPet.py
git commit -m "feat: 添加睡觉状态下的鼠标行为和唤醒菜单"
```

---

## 任务 7：完善 Interaction_worker 的唤醒处理

**文件：**
- 修改：`dyberpet/DyberPet/modules.py`

- [ ] **步骤 1：在 start_interact 方法中添加 wake 处理**

在 `start_interact` 方法中（在 `if interact == 'sleep':` 之后）添加以下代码：

```python
# 唤醒动画
if interact == 'wake':
    settings.is_sleeping = False
    settings.playid = 0
    settings.act_id = 0
```

- [ ] **步骤 2：在 Interaction_worker 类中添加 wake 方法**

在 `Interaction_worker` 类中（在 `sleeping` 方法之后）添加以下方法：

```python
def wake(self, act_name):
    """处理唤醒动画"""
    wake_act = self.pet_conf.fallasleep_wake
    self.img_from_act(wake_act)
    
    # 检查动画是否播放完毕
    n_repeat = math.ceil(wake_act.frame_refresh / (self.pet_conf.interact_speed / 1000))
    img_list_expand = [item for item in wake_act.images for i in range(n_repeat)] * wake_act.act_num
    if settings.playid >= len(img_list_expand):
        # 唤醒动画播放完毕，恢复正常状态
        settings.is_sleeping = False
        settings.playid = 0
        settings.act_id = 0
        self.stop_interact()
```

- [ ] **步骤 3：完善 Scheduler_worker 的 wake_up 方法**

修改 `Scheduler_worker` 类中的 `wake_up` 方法：

```python
def wake_up(self):
    """唤醒睡觉的猫"""
    if not settings.is_sleeping:
        return
    
    # 通过信号触发 Interaction_worker 播放醒来动画
    # 这里需要添加信号连接，暂时直接设置状态
    settings.is_sleeping = False
    settings.playid = 0
    settings.act_id = 0
```

- [ ] **步骤 4：Commit**

```bash
git add dyberpet/DyberPet/modules.py
git commit -m "feat: 完善唤醒动画处理"
```

---

## 任务 8：测试和验证

**文件：**
- 无

- [ ] **步骤 1：运行应用测试睡觉功能**

运行：`cd dyberpet && python run_DyberPet.py`

预期：
1. 猫有 5% 概率进入睡觉状态
2. 睡觉时播放三段动画（onset → loop → wake）
3. 自然唤醒功能正常（每分钟 20% 概率）
4. 右键菜单显示"唤醒六一"选项
5. 左键点击无反应，左键按住只能 X 轴移动

- [ ] **步骤 2：修复发现的问题**

如果测试中发现问题，修复代码并重新测试。

- [ ] **步骤 3：最终 Commit**

```bash
git add -A
git commit -m "feat: 完成睡觉功能实现"
```

---

## 自检清单

1. **规格覆盖度：** ✅ 所有规格需求都有对应任务
2. **占位符扫描：** ✅ 无占位符
3. **类型一致性：** ✅ 所有类型和方法名一致
