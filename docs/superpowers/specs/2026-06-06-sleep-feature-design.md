# 睡觉功能设计规格

## 概述

为桌面宠物添加睡觉功能，让猫可以随机进入睡觉状态，有呼吸动画，并支持自然唤醒和交互唤醒。

## 设计决策

### 触发机制
- **基于概率**：每次随机动作选择时，有 5% 的概率选择睡觉
- **全时段相同**：睡觉概率与时间无关，任何时间都有相同的触发概率

### 素材
现有三段睡觉素材：
- `fallasleep_onset`：入睡动画，145 帧
- `fallasleep_loop`：睡觉循环动画，145 帧
- `fallasleep_wake`：醒来动画，169 帧

### 动画播放流程
1. **触发**：随机动作系统以 5% 概率选择"睡觉"动作
2. **播放顺序**：
   - fallasleep_onset（入睡动画，播放 1 次）
   - fallasleep_loop（睡觉循环，持续播放直到被唤醒）
   - 被唤醒时播放 fallasleep_wake（醒来动画，播放 1 次）
3. **循环机制**：fallasleep_loop 需要特殊处理，类似于 drag_loop 的实现方式：
   - 在 Interaction_worker 中添加专门的睡觉处理方法
   - 手动管理 playid，当动画播放完毕后重置 playid = 0 实现循环
   - 使用 is_sleeping 状态变量控制循环退出

### 唤醒机制

#### 自然唤醒
- 每分钟 20% 概率自然醒来
- 使用定时器，每分钟检查一次
- 随机数 < 0.2 时触发唤醒

#### 交互唤醒
- 鼠标右键点击 → 显示菜单选项"唤醒六一"
- 点击"唤醒六一" → 触发唤醒流程
- 鼠标左键点击 → 无反应
- 鼠标左键按住 → 只能在 X 轴方向移动

#### 唤醒流程
1. 停止 fallasleep_loop
2. 播放 fallasleep_wake
3. 恢复正常状态

### 状态管理

#### 状态标识
在 settings.py 中添加 `is_sleeping` 全局变量：
- `True`：猫正在睡觉
- `False`：猫正常状态

#### 状态切换
- 进入睡觉：设置 `is_sleeping = True`
- 唤醒后：设置 `is_sleeping = False`

#### 状态影响
- 睡觉时禁用随机动作系统
- 睡觉时禁用鼠标左键拖拽（只能 X 轴移动）
- 睡觉时右键菜单显示"唤醒六一"选项

#### 数据存储
- 睡觉状态不需要持久化存储
- 每次启动应用时默认为非睡觉状态

## 配置文件变更

### act_conf.json
添加三段睡觉动画配置：
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

### pet_conf.json
在 random_act 中添加睡觉动作：
```json
{
  "name": "睡觉",
  "act_list": ["fallasleep_onset", "fallasleep_loop", "fallasleep_wake"],
  "act_prob": 0.05,
  "act_type": [2, 0]
}
```

## 代码变更

### settings.py
添加全局变量：
```python
is_sleeping = False
```

### modules.py
修改 Animation_worker 类：
1. 在 `random_act` 方法中添加睡觉状态检查
2. 添加睡觉动画播放逻辑

修改 Interaction_worker 类：
1. 添加 `sleeping` 方法处理睡觉动画循环
2. 添加自然唤醒定时器
3. 添加唤醒流程实现

### DyberPet.py
修改主窗口类：
1. 添加睡觉状态下的鼠标事件处理
2. 添加右键菜单"唤醒六一"选项
3. 添加唤醒流程实现

## 测试验证

### 功能测试
1. 验证睡觉动画能正常播放
2. 验证自然唤醒功能
3. 验证交互唤醒功能
4. 验证睡觉状态下的鼠标行为

### 边界测试
1. 验证睡觉时禁用随机动作
2. 验证唤醒后恢复正常状态
3. 验证右键菜单选项显示

## 风险与缓解

### 风险 1：动画播放冲突
- **风险**：睡觉动画与其他动画冲突
- **缓解**：在进入睡觉前停止所有当前动画

### 风险 2：状态管理混乱
- **风险**：睡觉状态与其他状态冲突
- **缓解**：明确状态优先级，睡觉状态优先级最高

### 风险 3：唤醒时机问题
- **风险**：唤醒时动画未播放完毕
- **缓解**：等待当前动画播放完毕后再唤醒

## 实现优先级

1. **P0**：动画配置和基础播放
2. **P1**：自然唤醒功能
3. **P2**：交互唤醒功能
4. **P3**：状态管理和鼠标行为
