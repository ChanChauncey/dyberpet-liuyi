# 🐱 六一桌宠 - 数字猫桌面宠物

将家里的猫变成"数字生命"——一只运行在 Windows 桌面上的模拟养成桌面宠物。

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green)
![License](https://img.shields.io/badge/License-GPL--3.0-green)

## ✨ 功能特色

### 🎮 核心玩法
- **模拟养成**：喂食、玩耍、铲屎，照顾你的数字猫
- **状态系统**：饥饿值（HP）、好感度（FV）、金币系统
- **物品系统**：商店购买食物和玩具，收集各种物品

### 🎬 动画系统
- **18种动画**：站立、行走、跳跃、打滚、睡觉等
- **自娱自乐**：猫会随机播放动画（打喷嚏、舔毛、抓苍蝇等）
- **点击触发**：25%概率触发动画，增加互动趣味
- **变速移动**：行走动画支持分阶段变速（静止→加速→匀速→减速）

### 💤 睡觉系统
- **自然作息**：猫会随机打瞌睡
- **唤醒互动**：右键菜单唤醒或等待自然醒来
- **启动动画**：每次启动播放醒来动画
- **鼠标限制**：睡觉时只能X轴拖动，防止打扰美梦

### 💩 便便系统
- **自动产生**：猫会在桌面上产生便便
- **交互清理**：鼠标悬停放大（80px→96px），点击消除（200ms淡出）
- **物理模拟**：便便会从猫屁股掉落，碰到边界反弹，最终落地
- **好感度惩罚**：不清理便便会降低好感度

### 👻 隐身模式
- **鼠标穿透**：开启后鼠标移到猫位置时猫自动隐藏，可穿透点击桌面
- **像素级检测**：只在猫轮廓区域触发隐藏（alpha > 30）
- **一键恢复**：隐藏后显示恢复按钮（48×26圆角按钮）

### 🔔 通知系统
- **气泡提示**：猫头顶显示状态提示（饥饿、心情等）
- **智能推荐**：根据饥饿等级推荐合适的食物
- **淡入淡出**：鼠标靠近自动隐藏（200ms），离开恢复
- **鼠标穿透**：气泡隐藏时允许点击穿透到下层

### 🖥️ 多屏幕支持
- **拖拽跨屏**：释放时检测重叠面积，超过50%自动切换屏幕
- **自适应地面**：每个屏幕独立计算任务栏高度
- **边界限制**：窗口始终限制在当前屏幕可用区域内

## 📥 下载安装

### 方式一：下载安装包（推荐）

前往 [Releases](https://github.com/ChanChauncey/dyberpet-liuyi/releases) 页面下载最新版本的 **六一桌宠** 安装包（`liuyi_Setup.exe`），双击运行即可。

### 方式二：源码运行

1. 安装 Python 3.12+
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行：
   ```bash
   cd dyberpet
   python run_DyberPet.py
   ```

### 方式三：自行打包

1. 安装 PyInstaller：
   ```bash
   pip install pyinstaller
   ```

2. 打包：
   ```bash
   cd dyberpet
   pyinstaller liuyi.spec
   ```

3. 安装程序生成在 `安装包/` 目录

## 🎮 操作说明

### 基础操作
| 操作 | 说明 |
|------|------|
| 左键点击 | 触发动画、物品掉落 |
| 左键拖拽 | 移动猫的位置、扔猫 |
| 右键菜单 | 打开功能菜单 |

### 右键菜单
- **打开仪表盘**：查看状态、背包、商店、任务
- **隐身模式**：开启鼠标穿透
- **唤醒六一**：唤醒睡觉中的猫

### 鼠标交互
- **点击猫**：掉落金币 + 爱心图标，概率触发动画
- **拖拽猫**：松手后会坠落弹跳，支持抛体物理
- **靠近气泡**：提示自动隐藏
- **点击便便**：清理便便，获得好感度

## 📁 项目结构

```
桌面宠物-GitHub/
├── CLAUDE.md              # 项目规范文档
├── README.md              # 本文件
├── requirements.txt       # Python 依赖
├── .gitignore             # Git 忽略规则
├── assets/                # 素材配置（唯一编辑源）
│   └── configs/           # pet_conf.json + act_conf.json
├── dyberpet/              # 核心代码
│   ├── run_DyberPet.py    # 启动入口 + 信号总线
│   └── DyberPet/          # 主逻辑
│       ├── DyberPet.py    # 主窗口 + 鼠标交互
│       ├── modules.py     # 三线程 Worker（Animation/Interaction/Scheduler）
│       ├── settings.py    # 全局状态 + 配置持久化
│       ├── conf.py        # 配置加载（PetConfig/ActData/PetData/ItemData）
│       ├── utils.py       # 工具函数 + SubPet_Manager
│       ├── Accessory.py   # 饰品/掉落物系统
│       ├── Poop.py        # 便便交互（悬停放大 + 点击消除）
│       ├── Notification.py # 通知（Toaster）+ 气泡（BubbleText）
│       ├── bubbleManager.py # 气泡行为逻辑层
│       ├── extra_windows.py # 额外窗口（教程等）
│       ├── Dashboard/     # 仪表盘（状态/背包/商店/任务）
│       └── DyberSettings/ # 设置面板（基本设置/存档/角色卡）
├── tools/                 # 素材处理工具
│   ├── frame_extractor.py # 视频帧提取
│   ├── deploy_sprites.py  # 精灵图部署（色度键抠图 + resize）
│   ├── copy_configs.py    # 配置文件批量部署
│   ├── adjust_floor.py    # 地面位置可视化调节器
│   └── sam2_mask.py       # SAM2 逐帧抠图
├── docs/                  # 设计文档
│   ├── design.md          # 完整设计规格
│   ├── decisions/         # 架构决策记录
│   └── superpowers/       # AI 工作产物（specs/plans）
└── res/                   # 资源文件（角色、物品、图标）
```

## 🛠️ 开发说明

### 技术栈
- **语言**：Python 3.12
- **GUI 框架**：PySide6 (Qt6)
- **UI 组件**：PySide6-Fluent-Widgets
- **打包工具**：PyInstaller + Inno Setup

### 架构设计
- **三线程架构**：Animation / Interaction / Scheduler 并行运行
- **信号驱动**：Qt 信号通信，状态协调
- **懒加载**：精灵图按需加载，启动快速

### 动画系统
- **帧动画**：PNG 序列帧播放
- **概率系统**：根据状态解锁动画
- **变速移动**：行走支持分阶段变速

## 🎨 素材制作

### 工具脚本
```bash
# 视频帧提取
python tools/frame_extractor.py video.mp4 frames/

# 精灵图部署（色度键抠图 + 部署）
python tools/deploy_sprites.py

# 地面位置调节
python tools/adjust_floor.py
```

### 素材规范
- **格式**：PNG 透明背景
- **分辨率**：640×360（16:9）
- **帧率**：24fps
- **风格**：Disney/皮克斯风格，偏真实感

## 📝 配置说明

### 角色配置
- `assets/configs/pet_conf.json` - 角色属性、动画配置
- `assets/configs/act_conf.json` - 动画帧范围、概率

### 物品配置
- `res/items/Default/items_config.json` - 物品属性、效果

### 部署配置
```bash
# 修改配置后，运行部署脚本
python tools/copy_configs.py
```

## 🐛 已知问题

- **Python 3.12 兼容性**：需要最新版 PySide6-Fluent-Widgets + pyside6（不锁版本）
- **act_conf.json 必需键**：stand/default/up/down/left/right/drag/drag_start/drag_loop/fall/fall_loop/on_floor/land_bounce/land_stay/fallasleep_onset/fallasleep_loop/fallasleep_wake
- **SubPet 功能已禁用**：DPAccessory.setup_accessory() 中 pet/subpet 直接 return
- **PyInstaller 打包**：需要排除大型库（torch/cv2/scipy等）减少体积

## 📄 许可证

本项目基于 [DyberPet](https://github.com/ChaozhongLiu/DyberPet) 二次开发，采用 [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html) 协议。使用本项目时请遵守原作者 Chaozhong Liu 的版权声明。

## 🙏 致谢

### 原项目

[DyberPet](https://github.com/ChaozhongLiu/DyberPet) 是本项目的底层框架，特别感谢 [DyberPet](https://github.com/ChaozhongLiu/DyberPet) 提供的框架和设计灵感，让我家的小猫"六一"实现了"数字永生"——从一只真实的猫，变成了永远陪伴在桌面上的数字生命。

### 素材制作流程

1. **风格生成**：使用 GPT image2 根据猫照片生成皮克斯/迪士尼风格的绿幕图片，保留猫毛等细节特征
2. **动作视频**：使用 seedance 2.0 根据绿幕照片生成各类动作视频
3. **视频切帧**：让 Claude Code 编写视频切分脚本，逐帧提取为 PNG 序列
4. **逐帧抠图**：让 Claude Code 编写抠图脚本，对每一帧进行精细抠图处理
5. **部署调试**：将素材部署到项目中，与 Claude Code 反复对话调试，逐组调校动画的播放逻辑

### 在原项目基础上的新增功能

- **隐身模式**：开启后鼠标移动到猫的位置时猫会自动隐藏、鼠标可穿透点击桌面，移开后猫自动恢复显示，解决了猫猫挡住桌面信息的问题
- **便便系统**：猫猫会在桌面上产生便便，支持悬停放大和点击清理，有物理模拟（掉落、反弹、落地）
- **睡眠系统**：完整的入睡、睡觉循环、自然唤醒/交互唤醒动画，睡觉时限制鼠标交互
- **多屏幕支持**：拖拽跨屏自动切换，每个屏幕独立计算地面位置
- **气泡行为系统**：根据饥饿等级智能调度气泡提示，鼠标靠近自动隐藏
- **物品系统**：21个物品，按亲密度解锁，支持喂食动画和Buff效果
- **金币系统**：点击掉落、物品掉落、任务奖励，商店购买/出售（75%折旧）
- **番茄钟/专注计时**：任务系统支持番茄钟和专注计时，完成获得金币奖励

### 致谢

- [PySide6](https://pypi.org/project/PySide6/) - Qt6 Python 绑定
- [PySide6-Fluent-Widgets](https://github.com/zhiyiYo/PySide6-Fluent-Widgets) - Fluent Design 风格组件

如有问题或建议，欢迎提交 Issue。

---

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**
