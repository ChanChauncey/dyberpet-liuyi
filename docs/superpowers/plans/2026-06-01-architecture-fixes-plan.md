# 架构修复 实现计划

> **面向 AI 代理的工作者：** 推荐使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复架构审查发现的 14 项问题中的 8 项关键问题——抠图增强、AI 桥接通路、配置修正、fallback 引擎、性格持久化

**架构：** 增强色键管线（替代简单色键）→ AI 轮询桥接（queue + QTimer）→ 配置参数校正 + 脚本化 fallback

**技术栈：** Python 3.12、OpenCV + NumPy（抠图）、PySide6 QTimer + queue.Queue（桥接）、SQLite（性格持久化）

---

## 任务 1：抠图增强——despill + 羽化 + alpha 精细化

**文件：**
- 修改：`tools/sam2_mask.py`

- [ ] **步骤 1：新增 despill 函数**

在 `apply_mask` 函数之后插入：

```python
def despill(frame: np.ndarray, mask: np.ndarray, bg_rgb: tuple) -> np.ndarray:
    """对半透明边缘区域做绿色溢出抑制。

    只处理 alpha 在 0.1~0.9 之间的边缘像素，
    将绿色通道压到 max(R, B)，消除绿幕残留的 green spill。
    """
    bg_b, bg_g, bg_r = bg_rgb
    alpha = mask.astype(float)

    # 只处理边缘区域（半透明像素）
    edge = (alpha > 0.1) & (alpha < 0.9)
    if not edge.any():
        return frame

    result = frame.copy().astype(float)
    r, g, b = result[:, :, 2], result[:, :, 1], result[:, :, 0]

    # 绿色溢出抑制：G = min(G, max(R, B))
    max_rb = np.maximum(r, b)
    g_edge = g[edge]
    suppressed = np.minimum(g_edge, max_rb[edge])
    g[edge] = suppressed

    return np.clip(result, 0, 255).astype(np.uint8)


def feather_mask(mask: np.ndarray, radius: float = 2.5) -> np.ndarray:
    """对二值 mask 做高斯羽化，产生 0~1 连续 alpha 过渡。"""
    return cv2.GaussianBlur(mask.astype(float), (0, 0), sigmaX=radius)


def refine_alpha(mask: np.ndarray) -> np.ndarray:
    """腐蚀+膨胀去边缘噪点，再跟羽化 mask 取 max 保留软边缘。"""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    eroded = cv2.erode(mask, kernel, iterations=1)
    dilated = cv2.dilate(eroded, kernel, iterations=1)
    return np.maximum(mask, dilated)
```

- [ ] **步骤 2：修改 `process_frames` 管线顺序**

将现有的：
```python
mask = simple_green_screen_mask(frame, bg_rgb, tolerance)
rgba = apply_mask(frame, mask)
```

替换为新的 5 步管线：
```python
# 1. 色键二值化
mask_binary = simple_green_screen_mask(frame, bg_rgb, tolerance)

# 2. 边缘羽化
mask_feathered = feather_mask(mask_binary)

# 3. Alpha 精细化
mask_refined = refine_alpha(mask_feathered)

# 4. 绿色溢出抑制
frame_despilled = despill(frame, mask_refined, bg_rgb)

# 5. 合成 RGBA
rgba = apply_mask(frame_despilled, mask_refined)
```

- [ ] **步骤 3：验证——用现有帧测试管线**

```bash
cd "D:\Claude专用\桌面宠物"
mkdir -p /tmp/test_frames
# 用 Kitty 精灵模拟（非绿幕但能跑通管线）
cp dyberpet/res/role/Kitty/action/stand_0.png /tmp/test_frames/frame_0000.png
D:\Python\python.exe tools/sam2_mask.py /tmp/test_frames /tmp/test_rgba
ls /tmp/test_rgba/
```

预期：输出 RGBA PNG，无报错。

- [ ] **步骤 4：Commit**

```bash
cd "D:\Claude专用\桌面宠物"
git add tools/sam2_mask.py
git commit -m "feat: 抠图管线增强——despill + 羽化 + alpha 精细化"
```

---

## 任务 2：act_conf 参数修正（frame_move + land）

**文件：**
- 修改：`assets/configs/act_conf.json`
- 修改：`dyberpet/res/role/六一/act_conf.json`

- [ ] **步骤 1：修正 `assets/configs/act_conf.json`**

两处改动：

1. `left_walk.frame_move` 和 `right_walk.frame_move`：`0.5` → `10`
2. `land.images`：`"fallasleep"` → `"land"`

```json
{
  "default": {
    "images": "stand",
    "act_num": 1,
    "frame_refresh": 0.25
  },
  "up": {
    "images": "stand",
    "act_num": 1,
    "frame_refresh": 0.25
  },
  "down": {
    "images": "stand",
    "act_num": 1,
    "frame_refresh": 0.25
  },
  "left": {
    "images": "stand",
    "act_num": 1,
    "frame_refresh": 0.25
  },
  "right": {
    "images": "stand",
    "act_num": 1,
    "frame_refresh": 0.25
  },
  "drag": {
    "images": "drag",
    "act_num": 1,
    "frame_refresh": 0.15
  },
  "fall": {
    "images": "fall",
    "act_num": 1,
    "frame_refresh": 0.15
  },
  "stand": {
    "images": "stand",
    "act_num": 1,
    "frame_refresh": 0.25
  },
  "left_walk": {
    "images": "leftwalk",
    "act_num": 5,
    "need_move": true,
    "direction": "left",
    "frame_move": 10,
    "frame_refresh": 0.2
  },
  "right_walk": {
    "images": "rightwalk",
    "act_num": 5,
    "need_move": true,
    "direction": "right",
    "frame_move": 10,
    "frame_refresh": 0.2
  },
  "drag_start": {
    "images": "drag",
    "act_num": 1,
    "need_move": false,
    "frame_refresh": 0.15
  },
  "prefall": {
    "images": "drag",
    "act_num": 1,
    "need_move": false,
    "frame_refresh": 0.15
  },
  "fall_loop": {
    "images": "fall",
    "act_num": 3,
    "need_move": false,
    "frame_refresh": 0.15
  },
  "land": {
    "images": "land",
    "act_num": 1,
    "need_move": false,
    "frame_refresh": 0.1
  }
}
```

- [ ] **步骤 2：同步到 `dyberpet/res/role/六一/act_conf.json`**

内容同上，完整覆盖。

- [ ] **步骤 3：验证 JSON 格式合法**

```bash
cd "D:\Claude专用\桌面宠物"
D:\Python\python.exe -c "
import json
for p in ['assets/configs/act_conf.json', 'dyberpet/res/role/六一/act_conf.json']:
    with open(p) as f:
        d = json.load(f)
    assert d['left_walk']['frame_move'] == 10
    assert d['right_walk']['frame_move'] == 10
    assert d['land']['images'] == 'land'
    print(f'{p}: OK')
"
```

- [ ] **步骤 4：Commit**

```bash
cd "D:\Claude专用\桌面宠物"
git add assets/configs/act_conf.json dyberpet/res/role/六一/act_conf.json
git commit -m "fix: 修正 act_conf——frame_move 10、land 指向 land 动作"
```

---

## 任务 3：性格参数随机初始化 + 持久化

**文件：**
- 修改：`ai_engine/state/cat_state.py`
- 修改：`ai_engine/data/database.py`
- 修改：`ai_engine/bridge.py`

- [ ] **步骤 1：修改 `CatState`——personality 改为可选参数**

`ai_engine/state/cat_state.py`：

```python
"""猫的状态快照，作为 AI 行为决策的输入。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import random


@dataclass
class CatState:
    """当前时刻猫的完整状态。"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    hunger: int = 100
    vitality: int = 100
    favorability: int = 50
    cleanliness: int = 100

    screen_x: int = 0
    screen_y: int = 0
    screen_width: int = 1920
    screen_height: int = 1080

    last_action: str = ""
    last_interaction: str = ""
    time_since_interact_min: int = 60

    personality: Optional[dict] = None

    def __post_init__(self):
        if self.personality is None:
            self.personality = {
                "activity": round(random.uniform(0.2, 0.9), 2),
                "clingy": round(random.uniform(0.2, 0.9), 2),
                "foodie": round(random.uniform(0.2, 0.9), 2),
                "curiosity": round(random.uniform(0.2, 0.9), 2),
            }
```

- [ ] **步骤 2：database.py 新增 personality 存取函数**

在 `ai_engine/data/database.py` 末尾追加：

```python
import json


def ensure_personality_column():
    """确保 state_snapshots 表有 personality_json 列。"""
    conn = get_connection()
    cursor = conn.execute("PRAGMA table_info(state_snapshots)")
    columns = [row[1] for row in cursor.fetchall()]
    if "personality_json" not in columns:
        conn.execute("ALTER TABLE state_snapshots ADD COLUMN personality_json TEXT")
        conn.commit()
    conn.close()


def save_personality(personality: dict):
    """持久化性格参数到最近一条 state_snapshot。"""
    conn = get_connection()
    conn.execute(
        """UPDATE state_snapshots SET personality_json = ?
           WHERE id = (SELECT MAX(id) FROM state_snapshots)""",
        (json.dumps(personality),),
    )
    conn.commit()
    conn.close()


def load_latest_personality() -> dict | None:
    """从数据库读取最近一次的性格参数。"""
    conn = get_connection()
    row = conn.execute(
        "SELECT personality_json FROM state_snapshots "
        "WHERE personality_json IS NOT NULL "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return None
```

- [ ] **步骤 3：修改 `AIBridge`——启动时加载或生成性格**

`ai_engine/bridge.py`：

```python
"""桥接模块：连接 AI 行为引擎和 DyberPet 壳。"""

import queue
import threading
import time
from ai_engine.state.cat_state import CatState
from ai_engine.behavior.decision import decide_action
from ai_engine.data.database import (
    init_db, save_state, save_decision,
    ensure_personality_column, load_latest_personality, save_personality,
)

# AI → DyberPet 动作名映射
ACTION_MAP = {
    "stand": "stand",
    "walk_right": "right_walk",
    "walk_left": "left_walk",
    "sleep_cycle": "stand",  # 降级，睡眠动画后期才有
}


class AIBridge:
    """AI 引擎桥接器。在独立线程中运行行为决策循环。"""

    def __init__(self, decision_interval_sec: int = 120):
        # 性格参数：优先从 DB 恢复，否则随机生成
        init_db()
        ensure_personality_column()
        saved_personality = load_latest_personality()
        self.state = CatState(personality=saved_personality)
        if saved_personality is None:
            save_personality(self.state.personality)
            print(f"[AI Bridge] 首次启动，随机生成性格: {self.state.personality}")
        else:
            print(f"[AI Bridge] 从数据库恢复性格: {self.state.personality}")

        self.interval = decision_interval_sec
        self.running = False
        self.thread = None
        self.action_queue = queue.Queue()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print(f"[AI Bridge] 行为引擎已启动，决策间隔 {self.interval}s")

    def stop(self):
        self.running = False

    def update_state(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

    def get_pending_action(self) -> dict | None:
        """非阻塞获取队列中的下一个动作决策。"""
        try:
            return self.action_queue.get_nowait()
        except queue.Empty:
            return None

    def _loop(self):
        while self.running:
            try:
                decision = decide_action(self.state)
                save_decision(decision)

                # 动作名映射
                raw_action = decision.get("action", "stand")
                mapped_action = ACTION_MAP.get(raw_action, "stand")
                decision["action"] = mapped_action

                save_state(vars(self.state))
                self.action_queue.put(decision)
                print(f"[AI] {raw_action} → {mapped_action} "
                      f"(优先级 {decision['priority']}, {decision['duration_min']}min)")
            except Exception as e:
                print(f"[AI] 决策失败: {e}")
            time.sleep(self.interval)
```

- [ ] **步骤 4：验证性格持久化**

```bash
cd "D:\Claude专用\桌面宠物"
D:\Python\python.exe -c "
import sys; sys.path.insert(0, '.')
from ai_engine.bridge import AIBridge
b = AIBridge(decision_interval_sec=999)
print('Personality:', b.state.personality)
assert 0.2 <= b.state.personality['activity'] <= 0.9
assert 0.2 <= b.state.personality['clingy'] <= 0.9
print('OK')

# 第二次启动：应从 DB 恢复相同值
b2 = AIBridge(decision_interval_sec=999)
assert b2.state.personality == b.state.personality
print('DB 恢复 OK')
"
```

- [ ] **步骤 5：Commit**

```bash
cd "D:\Claude专用\桌面宠物"
git add ai_engine/state/cat_state.py ai_engine/data/database.py ai_engine/bridge.py
git commit -m "feat: 性格参数随机初始化 + SQLite 持久化"
```

---

## 任务 4：脚本化 fallback 行为引擎

**文件：**
- 修改：`ai_engine/behavior/decision.py`

- [ ] **步骤 1：新增 `scripted_fallback` 函数**

在 `ai_engine/behavior/decision.py` 的 `build_prompt` 之后、`decide_action` 之前插入：

```python
def scripted_fallback(state: CatState) -> dict:
    """无 Ollama 时的纯规则降级行为。

    规则优先级：
    1. 夜晚（22:00-06:00）→ 安静休息
    2. 饥饿 < 30 → 原地待机等喂食
    3. 白天活力 > 50 + 在屏幕边缘 → 向中心走
    4. 默认 → 待机
    """
    import datetime
    now = datetime.datetime.now()
    hour = now.hour

    # 规则 1：夜晚休息
    if hour >= 22 or hour < 6:
        return {"action": "stand", "target_x": 0, "duration_min": 30, "priority": 3}

    # 规则 2：饥饿等食
    if state.hunger < 30:
        return {"action": "stand", "target_x": 0, "duration_min": 5, "priority": 1}

    # 规则 3：白天活跃 + 在边缘 → 向中间走
    screen_center = state.screen_width // 2
    margin = state.screen_width // 5
    if state.vitality > 50:
        if state.screen_x < margin:
            return {"action": "walk_right", "target_x": screen_center,
                    "duration_min": 3, "priority": 2}
        elif state.screen_x > state.screen_width - margin:
            return {"action": "walk_left", "target_x": screen_center,
                    "duration_min": 3, "priority": 2}

    # 规则 4：默认待机
    return {"action": "stand", "target_x": 0, "duration_min": 5, "priority": 3}
```

- [ ] **步骤 2：修改 `decide_action`——失败时使用 fallback**

将 `decide_action` 函数中现有的 `except` 分支：
```python
    except json.JSONDecodeError:
        decision = {
            "action": "stand",
            "target_x": 0,
            "duration_min": 5,
            "priority": 3,
        }
```

替换为：
```python
    except Exception:
        # Ollama 不可用或 JSON 解析失败 → 脚本化降级
        return scripted_fallback(state)
```

同时把 `json.JSONDecodeError` 改为更宽的 `Exception`（覆盖 `ollama` 模块的连接错误、超时等）。

- [ ] **步骤 3：验证 fallback 逻辑**

```bash
cd "D:\Claude专用\桌面宠物"
D:\Python\python.exe -c "
import sys; sys.path.insert(0, '.')
from ai_engine.state.cat_state import CatState
from ai_engine.behavior.decision import scripted_fallback

# 测试夜晚逻辑
state = CatState()
from datetime import datetime
# 模拟夜晚
import unittest.mock as mock
with mock.patch('datetime.datetime') as mock_dt:
    mock_dt.now.return_value = datetime(2026, 6, 2, 2, 30)
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    # 这里简单测返回值结构
    result = scripted_fallback(state)
    assert 'action' in result
    assert result['action'] == 'stand'
    assert result['duration_min'] == 30
    print('夜晚 fallback OK')

# 测试饥饿
state.hunger = 20
result = scripted_fallback(state)
assert result['priority'] == 1
print('饥饿 fallback OK')

# 测试活跃+边缘
state.hunger = 100
state.vitality = 80
state.screen_x = 50  # 左边缘
result = scripted_fallback(state)
assert result['action'] == 'walk_right'
print('活跃边缘 fallback OK')

print('全部验证通过')
"
```

- [ ] **步骤 4：Commit**

```bash
cd "D:\Claude专用\桌面宠物"
git add ai_engine/behavior/decision.py
git commit -m "feat: 添加脚本化 fallback 行为引擎（无 Ollama 时降级）"
```

---

## 任务 5：AI→DyberPet 桥接通路——PetWidget 消费端

**文件：**
- 修改：`dyberpet/DyberPet/DyberPet.py`
- 修改：`dyberpet/run_DyberPet.py`

- [ ] **步骤 1：PetWidget 新增 bridge 消费逻辑**

在 `dyberpet/DyberPet/DyberPet.py` 的 `PetWidget.__init__` 末尾（`self._setup_compensate()` 之前）添加 AI 决策消费定时器：

```python
        # AI 行为引擎桥接（可选）
        self.ai_bridge = None
        self.ai_decision_timer = QTimer()
        self.ai_decision_timer.timeout.connect(self._consume_ai_decision)
        self.ai_decision_timer.start(2000)  # 每 2 秒轮询
```

在 `PetWidget` 类中添加两个方法。放在 `_setup_compensate` 之后：

```python
    def set_bridge(self, bridge):
        """注入 AI 行为引擎桥接器。"""
        self.ai_bridge = bridge

    def _consume_ai_decision(self):
        """消费 AI 行为引擎的决策指令。"""
        if self.ai_bridge is None:
            return
        decision = self.ai_bridge.get_pending_action()
        if decision is None:
            return
        action_name = decision.get("action", "stand")
        if action_name in self.pet_conf.act_dict:
            self._show_act(action_name)
```

- [ ] **步骤 2：修改 `run_DyberPet.py`——启动 bridge**

在 `run_DyberPet.py` 的 `DyberPetApp.__init__` 中，`self.p = PetWidget(...)` 之后添加：

```python
        # 启动 AI 行为引擎
        from ai_engine.bridge import AIBridge
        self.bridge = AIBridge(decision_interval_sec=120)
        self.bridge.start()
        self.p.set_bridge(self.bridge)
```

注意：`ai_engine` 需要能在 Python path 中找到。在文件顶部已有 `sys.path.insert(0, os.path.dirname(__file__))`，但 `ai_engine` 在上级目录。需要在 import 之前加：

```python
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

完整修改后的 `run_DyberPet.py` 头部：

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # ai_engine 在上级目录
from sys import platform
import ctypes
from tendo import singleton
import os
from DyberPet.utils import read_json
from DyberPet.DyberPet import PetWidget
from DyberPet.Notification import DPNote
from DyberPet.Accessory import DPAccessory
# ... 其余保持不变
```

- [ ] **步骤 3：验证导入路径**

```bash
cd "D:\Claude专用\桌面宠物\dyberpet"
D:\Python\python.exe -c "
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ai_engine.bridge import AIBridge
print('AI bridge 导入 OK')
"
```

- [ ] **步骤 4：Commit**

```bash
cd "D:\Claude专用\桌面宠物"
git add dyberpet/DyberPet/DyberPet.py dyberpet/run_DyberPet.py
git commit -m "feat: AI 桥接通路——PetWidget 轮询消费 AI 决策"
```

---

## 任务 6：CLAUDE.md 配置同步约定

**文件：**
- 修改：`CLAUDE.md`

- [ ] **步骤 1：在 CLAUDE.md 的命名约定板块添加配置同步规则**

在 `## 命名约定` 部分末尾追加：

```markdown
- **配置同步**：`assets/configs/` 是精灵图/角色配置的**唯一编辑源**。修改后运行 `python tools/copy_configs.py` 部署到 `dyberpet/res/role/六一/`。不要直接改 dyberpet 下的配置。
```

- [ ] **步骤 2：Commit**

```bash
cd "D:\Claude专用\桌面宠物"
git add CLAUDE.md
git commit -m "docs: 添加配置同步约定——assets/configs/ 为唯一编辑源"
```

---

## 任务 7：端到端验证

- [ ] **步骤 1：确认所有模块可导入**

```bash
cd "D:\Claude专用\桌面宠物"
D:\Python\python.exe -c "
import sys; sys.path.insert(0, '.')
from ai_engine.state.cat_state import CatState
from ai_engine.behavior.decision import decide_action, scripted_fallback
from ai_engine.data.database import init_db, ensure_personality_column, load_latest_personality, save_personality
from ai_engine.bridge import AIBridge
print('所有 AI 模块导入 OK')
"
```

- [ ] **步骤 2：确认 DyberPet 配置合法**

```bash
cd "D:\Claude专用\桌面宠物"
D:\Python\python.exe -c "
import sys, os
sys.path.insert(0, 'dyberpet')
os.chdir('dyberpet')
from DyberPet.conf import CheckCharFiles
status, info = CheckCharFiles('res/role/六一')
assert status == 0, f'配置检查失败: {status} {info}'
print('六一 配置检查 PASS')
"
```

- [ ] **步骤 3：启动完整系统**

```bash
cd "D:\Claude专用\桌面宠物\dyberpet"
D:\Python\python.exe run_DyberPet.py
```

手动验证清单：
- [ ] 猫在桌面上正确显示
- [ ] 控制台输出 `[AI Bridge] 行为引擎已启动`
- [ ] 控制台输出 `[AI]` 决策日志（如果有 Ollama）或 fallback 日志
- [ ] 猫可以正常拖拽、右键菜单
- [ ] 关闭程序不崩溃

- [ ] **步骤 4：验证抠图管线可运行**

```bash
cd "D:\Claude专用\桌面宠物"
# 用 Kitty 精灵模拟管线
mkdir -p /tmp/test_pipeline
cp dyberpet/res/role/Kitty/action/stand_0.png /tmp/test_pipeline/frame_0000.png
D:\Python\python.exe tools/sam2_mask.py /tmp/test_pipeline /tmp/test_pipeline_rgba
ls /tmp/test_pipeline_rgba/
```

预期：输出 RGBA PNG，无报错。

---

## 附录：修改文件总览

| 文件 | 改动类型 | 任务 |
|------|---------|------|
| `tools/sam2_mask.py` | 新增 3 个函数 + 修改管线 | 任务 1 |
| `assets/configs/act_conf.json` | frame_move 0.5→10，land images 修正 | 任务 2 |
| `dyberpet/res/role/六一/act_conf.json` | 同上 | 任务 2 |
| `ai_engine/state/cat_state.py` | personality → Optional，随机初始化 | 任务 3 |
| `ai_engine/data/database.py` | 新增 3 个函数（personality 存取） | 任务 3 |
| `ai_engine/bridge.py` | action_queue + ACTION_MAP + 性格加载 | 任务 3 |
| `ai_engine/behavior/decision.py` | 新增 scripted_fallback + 修改 except | 任务 4 |
| `dyberpet/DyberPet/DyberPet.py` | 新增 bridge 消费 QTimer | 任务 5 |
| `dyberpet/run_DyberPet.py` | 启动 bridge + path 修正 | 任务 5 |
| `CLAUDE.md` | 配置同步约定 | 任务 6 |
