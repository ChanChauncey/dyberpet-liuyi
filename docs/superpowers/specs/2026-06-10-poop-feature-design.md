# 猫拉屎功能设计规格

## 概述

猫会随机在任务栏上拉屎，屎从猫身体位置以抛物线飞出，随机落在任务栏上。用户点击屎可消除，获得亲密度奖励。

## 功能规格

### 触发机制

- **方式**：Scheduler_worker 中新增 APScheduler 定时任务
- **频率**：每 `POOP_CHECK_INTERVAL`（10）分钟检查一次，`POOP_PROBABILITY`（30%）概率触发
- **前置条件**：`settings.poop_enabled == True` 且猫在地面（`onfloor==1`）且不在睡觉且不在启动且不在弹跳
- **隐身模式**：屎正常生成，可独立点击消除（PoopWidget 是独立窗口，不受猫的 WS_EX_TRANSPARENT 影响）
- **估算频率**：平均约每 33 分钟拉一坨屎

### 视觉表现

- **素材**：`poop.png`（透明背景 PNG，~48×48）
- **素材路径**：`res/items/Default/poop.png`（固定路径，所有角色共用）

### 物理动画（抛物线）

复用金币掉落的物理模型：

- **初始位置**：猫身体中心（`settings.widget_pos` + 猫尺寸偏移）
- **初始速度**：
  - `v_x = random.uniform(-3, 3)`（随机水平方向，决定落点远近）
  - `v_y = random.uniform(-8, -4)`（向上抛出）
- **重力**：`gravity = 0.5`（每帧叠加到 v_y）
- **动画驱动**：QTimer 20ms 间隔
- **落地条件**：`y >= floor_y - poop_height`
- **落地后**：停止动画，屎静止在任务栏上，永久留存直到被点击

### 定位

- **Y 坐标**：落地后固定在 `floor_y - poop_height`（任务栏顶部）
- **X 坐标**：由抛物线物理决定，落点在任务栏上随机分布
- **多屏幕**：使用 `settings.current_screen` 确定屏幕边界，落地后调用 `limit_in_screen()` 约束

### 用户交互

- **鼠标悬停**：图标放大 1.2x + cursor 变为手型（提示可点击）
- **鼠标离开**：恢复原始大小
- **左键点击**：
  1. 播放淡出动画（200ms，`QPropertyAnimation` 控制 `windowOpacity`）
  2. 发射 `poop_clicked(str)` 信号（poop_id 使用 `id(self)` 即对象内存地址，保证唯一）
  3. `close()` 关闭窗口
- **点击后奖励**：`PetWidget._change_status('fv', POOP_FV_REWARD, 'poop', True)` → 进度条更新 + 右下角通知 + 持久化
- **通知文案**：`f"{settings.petname}拉屎啦！点击清理获得亲密度"`

### PoopWidget 窗口属性

- `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.NoDropShadowWindowHint`
- `Qt.WA_TranslucentBackground`
- `Qt.WA_DeleteOnClose`（关闭后自动释放）

## 配置项

```python
# settings.py 新增
poop_enabled = True           # 全局开关
POOP_CHECK_INTERVAL = 10      # 检查间隔（分钟）
POOP_PROBABILITY = 0.3        # 每次检查的触发概率
POOP_FV_REWARD = 3            # 点击消除获得的亲密度
```

## 系统设置 UI

- `BasicSettingUI.py` 新增 FluentSwitch
- 标签："允许拉屎"
- 切换时写入 `settings.poop_enabled` 并持久化到 `settings.json`

## 信号流

```
Scheduler_worker                    PetWidget
  │                                   │
  │ check_poop() 每10分钟             │
  │ random() < 0.3 → 触发            │
  │                                   │
  │──sig_poop_trigger()──────────────→│ _on_poop_trigger()
  │                                   │   ├─ 检查 settings.poop_enabled
  │                                   │   ├─ 检查 onfloor/sleeping/startup/bouncing
  │                                   │   ├─ 创建 PoopWidget(cat_x, cat_y)
  │                                   │   │     │
  │                                   │   │     │ 抛物线动画 → 落地静止
  │                                   │   │     │
  │                                   │   │     │ 用户点击
  │                                   │   │     │──poop_clicked(id)──────────→│
  │                                   │   │                                  │
  │                                   │   │   _on_poop_clicked(id)           │
  │                                   │   │     ├─ _change_status('fv', +3)  │
  │                                   │   │     ├─ setup_notification()      │
  │                                   │   │     └─ 从 poop_list 移除         │
```

## 生命周期管理

- `PetWidget.poop_list: List[PoopWidget]` 存储所有存活的屎实例
- 创建时加入列表，点击消除时移除
- 应用退出时遍历 `poop_list` 逐个 `close()`

## 文件变更清单

| 文件 | 变更类型 | 内容 |
|------|---------|------|
| `dyberpet/DyberPet/Poop.py` | 新增 | PoopWidget 类（~150 行） |
| `dyberpet/DyberPet/modules.py` | 修改 | Scheduler_worker 新增 `check_poop()` 定时任务 + `sig_poop_trigger` 信号 |
| `dyberpet/DyberPet/DyberPet.py` | 修改 | 新增信号连接 + `_on_poop_trigger()` + `_on_poop_clicked()` + `poop_list` |
| `dyberpet/DyberPet/settings.py` | 修改 | 新增 `poop_enabled` 变量 + 配置常量 |
| `dyberpet/DyberPet/DyberSettings/BasicSettingUI.py` | 修改 | 新增"允许拉屎"开关 |
| `assets/poop.png` | 新增 | 屎的 PNG 素材（需提供） |
