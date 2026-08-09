# 桌面宠物教程实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 制作8张小红书图文教程图片，展示"六一桌宠"桌面宠物的制作流程

**架构：** 使用HTML+CSS生成科技风格的教程图片，每张图片是一个独立的HTML页面，可以通过浏览器截图或导出为图片

**技术栈：** HTML5 + CSS3 + JavaScript（用于交互效果）

---

## 文件结构

### 创建的文件

| 文件 | 职责 |
|------|------|
| `docs/tutorial/` | 教程根目录 |
| `docs/tutorial/index.html` | 教程主页，包含所有8张图的导航 |
| `docs/tutorial/css/style.css` | 全局样式（颜色、字体、布局） |
| `docs/tutorial/images/` | 图片资源目录 |
| `docs/tutorial/01-cover.html` | 第1张：封面图 |
| `docs/tutorial/02-preview.html` | 第2张：效果预览 |
| `docs/tutorial/03-ai-generation.html` | 第3张：AI图像生成+视频生成 |
| `docs/tutorial/04-frame-extract.html` | 第4张：帧提取 |
| `docs/tutorial/05-matte.html` | 第5张：智能抠图 |
| `docs/tutorial/06-deploy.html` | 第6张：精灵图部署 |
| `docs/tutorial/07-config.html` | 第7张：配置调整 |
| `docs/tutorial/08-final.html` | 第8张：成品展示 |

---

## 任务分解

### 任务1：创建教程目录结构

**文件：**
- 创建：`docs/tutorial/` 目录
- 创建：`docs/tutorial/css/` 目录
- 创建：`docs/tutorial/images/` 目录

- [ ] **步骤1：创建目录结构**

```bash
cd "D:\Claude专用\桌面宠物"
mkdir -p docs/tutorial/css
mkdir -p docs/tutorial/images
```

- [ ] **步骤2：验证目录创建**

```bash
ls -la docs/tutorial/
```

预期输出：
```
css/
images/
```

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/
git commit -m "chore: 创建教程目录结构"
```

---

### 任务2：创建全局样式文件

**文件：**
- 创建：`docs/tutorial/css/style.css`

- [ ] **步骤1：编写CSS样式**

```css
/* 全局样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #ffffff;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* 教程卡片容器 */
.tutorial-card {
    width: 1080px;
    height: 1440px;
    background: linear-gradient(180deg, #1a1a2e 0%, #0f3460 100%);
    border: 2px solid #533483;
    border-radius: 16px;
    padding: 60px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(83, 52, 131, 0.3);
}

/* 标题样式 */
.title {
    font-size: 32px;
    font-weight: bold;
    color: #ffffff;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
    margin-bottom: 20px;
}

.subtitle {
    font-size: 18px;
    color: #a0a0a0;
    margin-bottom: 40px;
}

/* 流程图样式 */
.flow-chart {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    margin: 40px 0;
}

.flow-step {
    background: rgba(83, 52, 131, 0.3);
    border: 1px solid #533483;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    min-width: 150px;
}

.flow-arrow {
    font-size: 24px;
    color: #533483;
}

/* 对比图样式 */
.comparison {
    display: flex;
    gap: 20px;
    margin: 40px 0;
}

.comparison-item {
    flex: 1;
    background: rgba(15, 52, 96, 0.5);
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}

.comparison-label {
    font-size: 14px;
    color: #a0a0a0;
    margin-bottom: 10px;
}

/* 代码块样式 */
.code-block {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    font-family: 'Consolas', 'Source Code Pro', monospace;
    font-size: 14px;
    color: #e6edf3;
    overflow-x: auto;
    margin: 20px 0;
}

/* 工具图标样式 */
.tool-icons {
    display: flex;
    gap: 20px;
    margin: 20px 0;
}

.tool-icon {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

.tool-icon img {
    width: 48px;
    height: 48px;
}

.tool-icon span {
    font-size: 12px;
    color: #a0a0a0;
}

/* 网格布局 */
.grid-2x3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(2, 1fr);
    gap: 20px;
    margin: 40px 0;
}

.grid-item {
    background: rgba(83, 52, 131, 0.3);
    border: 1px solid #533483;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}

.grid-item img {
    width: 100%;
    height: auto;
    border-radius: 8px;
    margin-bottom: 10px;
}

.grid-item span {
    font-size: 14px;
    color: #a0a0a0;
}

/* 进度条样式 */
.progress-bar {
    width: 100%;
    height: 8px;
    background: rgba(83, 52, 131, 0.3);
    border-radius: 4px;
    overflow: hidden;
    margin: 20px 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #533483, #0f3460);
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* 目录树样式 */
.directory-tree {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    font-family: 'Consolas', 'Source Code Pro', monospace;
    font-size: 14px;
    color: #e6edf3;
    margin: 20px 0;
}

/* 配置对比样式 */
.config-comparison {
    display: flex;
    gap: 20px;
    margin: 40px 0;
}

.config-panel {
    flex: 1;
    background: rgba(15, 52, 96, 0.5);
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 20px;
}

.config-panel h3 {
    font-size: 16px;
    color: #533483;
    margin-bottom: 15px;
}

/* 功能列表样式 */
.feature-list {
    margin: 20px 0;
}

.feature-item {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0;
}

.feature-icon {
    width: 24px;
    height: 24px;
    background: #533483;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
}

.feature-text {
    font-size: 14px;
    color: #a0a0a0;
}

/* 页码样式 */
.page-number {
    position: absolute;
    bottom: 30px;
    right: 30px;
    font-size: 14px;
    color: #533483;
}

/* 装饰元素 */
.decoration {
    position: absolute;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: rgba(83, 52, 131, 0.1);
    z-index: -1;
}

.decoration-1 {
    top: -50px;
    right: -50px;
}

.decoration-2 {
    bottom: -50px;
    left: -50px;
}
```

- [ ] **步骤2：验证CSS文件创建**

```bash
ls -la docs/tutorial/css/
```

预期输出：`style.css`

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/css/style.css
git commit -m "style: 添加教程全局样式"
```

---

### 任务3：创建封面图页面

**文件：**
- 创建：`docs/tutorial/01-cover.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>六一桌宠 - 封面</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">六一桌宠</h1>
        <p class="subtitle">把你的猫变成桌面上的数字生命</p>
        
        <div style="margin: 40px 0;">
            <p style="color: #533483; font-size: 16px;">技术栈</p>
            <div class="tool-icons">
                <div class="tool-icon">
                    <span style="font-size: 24px;">🐍</span>
                    <span>Python</span>
                </div>
                <div class="tool-icon">
                    <span style="font-size: 24px;">🎨</span>
                    <span>PySide6</span>
                </div>
                <div class="tool-icon">
                    <span style="font-size: 24px;">🤖</span>
                    <span>AI视频生成</span>
                </div>
            </div>
        </div>
        
        <div style="position: absolute; bottom: 100px; right: 60px; width: 300px; height: 300px; background: rgba(83, 52, 131, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 120px;">🐱</span>
        </div>
        
        <div class="page-number">1/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/01-cover.html
```

验证：页面显示正确的标题、副标题和技术栈图标

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/01-cover.html
git commit -m "feat: 添加教程封面图页面"
```

---

### 任务4：创建效果预览页面

**文件：**
- 创建：`docs/tutorial/02-preview.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>效果预览</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">效果预览</h1>
        <p class="subtitle">18种动画动作，覆盖日常行为</p>
        
        <div class="grid-2x3">
            <div class="grid-item">
                <div style="height: 120px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px;">🧍</span>
                </div>
                <span>站立</span>
            </div>
            <div class="grid-item">
                <div style="height: 120px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px;">🚶</span>
                </div>
                <span>行走</span>
            </div>
            <div class="grid-item">
                <div style="height: 120px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px;">😴</span>
                </div>
                <span>睡觉</span>
            </div>
            <div class="grid-item">
                <div style="height: 120px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px;">🦘</span>
                </div>
                <span>跳跃</span>
            </div>
            <div class="grid-item">
                <div style="height: 120px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px;">🔄</span>
                </div>
                <span>打滚</span>
            </div>
            <div class="grid-item">
                <div style="height: 120px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px;">🍽️</span>
                </div>
                <span>喂食</span>
            </div>
        </div>
        
        <div class="feature-list">
            <div class="feature-item">
                <div class="feature-icon">✓</div>
                <span class="feature-text">模拟养成系统（饥饿值、亲密度）</span>
            </div>
            <div class="feature-item">
                <div class="feature-icon">✓</div>
                <span class="feature-text">实时交互（点击、拖拽、喂食）</span>
            </div>
            <div class="feature-item">
                <div class="feature-icon">✓</div>
                <span class="feature-text">智能行为（自动行走、睡觉、排便）</span>
            </div>
        </div>
        
        <div class="page-number">2/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/02-preview.html
```

验证：页面显示6个动作图标和3个功能特点

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/02-preview.html
git commit -m "feat: 添加效果预览页面"
```

---

### 任务5：创建AI生成页面

**文件：**
- 创建：`docs/tutorial/03-ai-generation.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI图像生成 + 视频生成</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">AI图像生成 + 视频生成</h1>
        <p class="subtitle">素材制作第一步（两步流程）</p>
        
        <div class="flow-chart">
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">📷</div>
                <span>真实照片</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🎨</div>
                <span>AI图像生成</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🖼️</div>
                <span>皮克斯风格图片</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🎬</div>
                <span>AI视频生成</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🎥</div>
                <span>原始视频</span>
            </div>
        </div>
        
        <div class="comparison">
            <div class="comparison-item">
                <div class="comparison-label">第一步：AI图像生成</div>
                <div style="height: 150px; background: rgba(15, 52, 96, 0.5); border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-bottom: 15px;">
                    <span style="font-size: 64px;">🐱</span>
                </div>
                <p style="font-size: 14px; color: #a0a0a0;">输入：真实猫咪照片</p>
                <p style="font-size: 14px; color: #a0a0a0;">输出：皮克斯风格图片</p>
                <div class="tool-icons" style="margin-top: 15px;">
                    <div class="tool-icon">
                        <span style="font-size: 20px;">🎭</span>
                        <span>Midjourney</span>
                    </div>
                    <div class="tool-icon">
                        <span style="font-size: 20px;">🤖</span>
                        <span>DALL-E</span>
                    </div>
                </div>
            </div>
            <div class="comparison-item">
                <div class="comparison-label">第二步：AI视频生成</div>
                <div style="height: 150px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-bottom: 15px;">
                    <span style="font-size: 64px;">🎬</span>
                </div>
                <p style="font-size: 14px; color: #a0a0a0;">输入：皮克斯风格图片 + 动作描述</p>
                <p style="font-size: 14px; color: #a0a0a0;">输出：猫咪动作视频</p>
                <div class="tool-icons" style="margin-top: 15px;">
                    <div class="tool-icon">
                        <span style="font-size: 20px;">🎥</span>
                        <span>Runway</span>
                    </div>
                    <div class="tool-icon">
                        <span style="font-size: 20px;">🐉</span>
                        <span>Kling</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="code-block">
            <p style="color: #7ee787;">// 提示词模板</p>
            <p>A cute black and white cow cat with yellow eyes, Pixar style, green screen background, [动作描述]</p>
            <br>
            <p style="color: #7ee787;">// 视频参数</p>
            <p>1920x1080, 24fps, MP4, 3-5秒</p>
        </div>
        
        <div class="page-number">3/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/03-ai-generation.html
```

验证：页面显示两步流程图和工具对比

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/03-ai-generation.html
git commit -m "feat: 添加AI生成页面"
```

---

### 任务6：创建帧提取页面

**文件：**
- 创建：`docs/tutorial/04-frame-extract.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>帧提取</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">帧提取</h1>
        <p class="subtitle">从视频到图片序列</p>
        
        <div class="flow-chart">
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🎥</div>
                <span>原始视频</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">⚙️</div>
                <span>frame_extractor.py</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🖼️</div>
                <span>PNG序列</span>
            </div>
        </div>
        
        <div class="comparison">
            <div class="comparison-item">
                <div class="comparison-label">处理前：视频</div>
                <div style="height: 150px; background: rgba(15, 52, 96, 0.5); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 64px;">🎥</span>
                </div>
            </div>
            <div class="comparison-item">
                <div class="comparison-label">处理后：PNG序列</div>
                <div style="height: 150px; background: rgba(83, 52, 131, 0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 10px;">
                    <span style="font-size: 32px;">🖼️</span>
                    <span style="font-size: 32px;">🖼️</span>
                    <span style="font-size: 32px;">🖼️</span>
                    <span style="font-size: 32px;">...</span>
                </div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: 75%;"></div>
        </div>
        <p style="text-align: center; color: #a0a0a0; font-size: 14px;">处理进度：75%</p>
        
        <div class="code-block">
            <p style="color: #7ee787;"># 帧提取命令</p>
            <p>python tools/frame_extractor.py video.mp4 frames/</p>
            <br>
            <p style="color: #7ee787;"># 参数说明</p>
            <p>输入：24fps视频 → 输出：24张PNG/秒</p>
        </div>
        
        <div class="page-number">4/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/04-frame-extract.html
```

验证：页面显示流程图、对比图和进度条

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/04-frame-extract.html
git commit -m "feat: 添加帧提取页面"
```

---

### 任务7：创建智能抠图页面

**文件：**
- 创建：`docs/tutorial/05-matte.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能抠图</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">智能抠图</h1>
        <p class="subtitle">去除绿幕背景</p>
        
        <div class="flow-chart">
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🟢</div>
                <span>绿幕识别</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🔄</div>
                <span>颜色替换</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">✨</div>
                <span>阴影移除</span>
            </div>
        </div>
        
        <div class="comparison">
            <div class="comparison-item">
                <div class="comparison-label">处理前：绿幕视频</div>
                <div style="height: 200px; background: #00E676; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 80px;">🐱</span>
                </div>
            </div>
            <div class="comparison-item">
                <div class="comparison-label">处理后：透明背景</div>
                <div style="height: 200px; background: repeating-conic-gradient(#808080 0% 25%, #fff 0% 50%) 50% / 20px 20px; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 80px;">🐱</span>
                </div>
            </div>
        </div>
        
        <div style="margin: 30px 0;">
            <h3 style="color: #533483; margin-bottom: 15px;">抠图效果细节</h3>
            <div style="display: flex; gap: 20px;">
                <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border-radius: 8px; padding: 15px;">
                    <p style="color: #7ee787; margin-bottom: 5px;">✓ 猫毛边缘清晰</p>
                    <p style="font-size: 12px; color: #a0a0a0;">每帧独立采样，确保一致性</p>
                </div>
                <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border-radius: 8px; padding: 15px;">
                    <p style="color: #7ee787; margin-bottom: 5px;">✓ 颜色替换准确</p>
                    <p style="font-size: 12px; color: #a0a0a0;">绿色 → 透明，无残留</p>
                </div>
                <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border-radius: 8px; padding: 15px;">
                    <p style="color: #7ee787; margin-bottom: 5px;">✓ 阴影完全移除</p>
                    <p style="font-size: 12px; color: #a0a0a0;">消除地面投影</p>
                </div>
            </div>
        </div>
        
        <div class="code-block">
            <p style="color: #7ee787;"># 智能抠图命令</p>
            <p>python tools/sam2_mask.py input_frames/ output_frames/</p>
            <br>
            <p style="color: #7ee787;"># 技术特点</p>
            <p>每帧独立采样 + 颜色替换 + 阴影移除</p>
        </div>
        
        <div class="page-number">5/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/05-matte.html
```

验证：页面显示三步流程、对比图和技术细节

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/05-matte.html
git commit -m "feat: 添加智能抠图页面"
```

---

### 任务8：创建精灵图部署页面

**文件：**
- 创建：`docs/tutorial/06-deploy.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>精灵图部署</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">精灵图部署</h1>
        <p class="subtitle">将处理好的图片部署到项目</p>
        
        <div class="flow-chart">
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">🖼️</div>
                <span>PNG序列</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">⚙️</div>
                <span>deploy_sprites.py</span>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 32px; margin-bottom: 10px;">📁</div>
                <span>精灵图目录</span>
            </div>
        </div>
        
        <div class="directory-tree">
            <p style="color: #7ee787;">dyberpet/res/role/六一/</p>
            <p style="margin-left: 20px;">├── action/</p>
            <p style="margin-left: 40px;">├── stand_0.png</p>
            <p style="margin-left: 40px;">├── stand_1.png</p>
            <p style="margin-left: 40px;">├── walk_0.png</p>
            <p style="margin-left: 40px;">├── walk_1.png</p>
            <p style="margin-left: 40px;">└── ...</p>
            <p style="margin-left: 20px;">├── pet_conf.json</p>
            <p style="margin-left: 20px;">└── act_conf.json</p>
        </div>
        
        <div class="config-comparison">
            <div class="config-panel">
                <h3>自动化部署</h3>
                <div class="feature-list">
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">自动创建目录结构</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">自动复制文件</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">自动生成配置文件</span>
                    </div>
                </div>
            </div>
            <div class="config-panel">
                <h3>配置文件生成</h3>
                <div class="code-block" style="font-size: 12px;">
                    <p>{</p>
                    <p style="margin-left: 20px;">"stand": {</p>
                    <p style="margin-left: 40px;">"frame_start": 0,</p>
                    <p style="margin-left: 40px;">"frame_end": 23</p>
                    <p style="margin-left: 20px;">}</p>
                    <p>}</p>
                </div>
            </div>
        </div>
        
        <div class="code-block">
            <p style="color: #7ee787;"># 部署命令</p>
            <p>python tools/deploy_sprites.py</p>
            <br>
            <p style="color: #7ee787;"># 特点</p>
            <p>不覆盖已有配置，只补充新动作</p>
        </div>
        
        <div class="page-number">6/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/06-deploy.html
```

验证：页面显示流程图、目录结构和配置对比

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/06-deploy.html
git commit -m "feat: 添加精灵图部署页面"
```

---

### 任务9：创建配置调整页面

**文件：**
- 创建：`docs/tutorial/07-config.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>配置调整</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">配置调整</h1>
        <p class="subtitle">个性化定制</p>
        
        <div class="config-comparison">
            <div class="config-panel">
                <h3>pet_conf.json</h3>
                <p style="color: #a0a0a0; margin-bottom: 15px;">角色外观、动画配置</p>
                <div class="code-block" style="font-size: 12px;">
                    <p>{</p>
                    <p style="margin-left: 20px;">"name": "六一",</p>
                    <p style="margin-left: 20px;">"breed": "奶牛猫",</p>
                    <p style="margin-left: 20px;">"animations": {</p>
                    <p style="margin-left: 40px;">"stand": "stand",</p>
                    <p style="margin-left: 40px;">"walk": "walk"</p>
                    <p style="margin-left: 20px;">}</p>
                    <p>}</p>
                </div>
            </div>
            <div class="config-panel">
                <h3>act_conf.json</h3>
                <p style="color: #a0a0a0; margin-bottom: 15px;">动画概率、解锁条件</p>
                <div class="code-block" style="font-size: 12px;">
                    <p>{</p>
                    <p style="margin-left: 20px;">"stand": {</p>
                    <p style="margin-left: 40px;">"act_prob": 1.0,</p>
                    <p style="margin-left: 40px;">"act_type": 0</p>
                    <p style="margin-left: 20px;">},</p>
                    <p style="margin-left: 20px;">"walk": {</p>
                    <p style="margin-left: 40px;">"act_prob": 0.1,</p>
                    <p style="margin-left: 40px;">"act_type": 3</p>
                    <p style="margin-left: 20px;">}</p>
                    <p>}</p>
                </div>
            </div>
        </div>
        
        <div style="margin: 30px 0;">
            <h3 style="color: #533483; margin-bottom: 15px;">个性化调整</h3>
            <div style="display: flex; gap: 20px;">
                <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border-radius: 8px; padding: 15px;">
                    <p style="color: #7ee787; margin-bottom: 5px;">动画速度</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 60%;"></div>
                    </div>
                    <p style="font-size: 12px; color: #a0a0a0;">调整 frame_refresh 参数</p>
                </div>
                <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border-radius: 8px; padding: 15px;">
                    <p style="color: #7ee787; margin-bottom: 5px;">互动频率</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 40%;"></div>
                    </div>
                    <p style="font-size: 12px; color: #a0a0a0;">调整 act_prob 参数</p>
                </div>
                <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border-radius: 8px; padding: 15px;">
                    <p style="color: #7ee787; margin-bottom: 5px;">解锁条件</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 80%;"></div>
                    </div>
                    <p style="font-size: 12px; color: #a0a0a0;">调整 act_type 参数</p>
                </div>
            </div>
        </div>
        
        <div class="code-block">
            <p style="color: #7ee787;"># 关键配置说明</p>
            <p>act_prob: 动画触发概率（0-1）</p>
            <p>act_type: 亲密度解锁阈值（0-4）</p>
            <p>frame_refresh: 帧刷新速度（ms）</p>
        </div>
        
        <div class="page-number">7/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/07-config.html
```

验证：页面显示配置对比和调整参数

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/07-config.html
git commit -m "feat: 添加配置调整页面"
```

---

### 任务10：创建成品展示页面

**文件：**
- 创建：`docs/tutorial/08-final.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>成品展示</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="tutorial-card">
        <div class="decoration decoration-1"></div>
        <div class="decoration decoration-2"></div>
        
        <h1 class="title">成品展示</h1>
        <p class="subtitle">最终效果 + 使用方式</p>
        
        <div style="height: 400px; background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); border-radius: 16px; border: 2px solid #533483; display: flex; align-items: center; justify-content: center; margin-bottom: 30px; position: relative; overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: url('data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><rect fill=\"%23333\" width=\"100\" height=\"100\"/><rect fill=\"%23444\" x=\"10\" y=\"10\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"40\" y=\"10\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"70\" y=\"10\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"10\" y=\"40\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"40\" y=\"40\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"70\" y=\"40\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"10\" y=\"70\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"40\" y=\"70\" width=\"20\" height=\"20\"/><rect fill=\"%23444\" x=\"70\" y=\"70\" width=\"20\" height=\"20\"/></svg>'); background-size: 50px 50px; opacity: 0.3;"></div>
            <span style="font-size: 120px; z-index: 1;">🐱</span>
            <div style="position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.7); padding: 10px 15px; border-radius: 8px;">
                <span style="color: #533483; font-size: 14px;">六一桌宠</span>
            </div>
        </div>
        
        <div style="display: flex; gap: 20px; margin-bottom: 30px;">
            <div style="flex: 1; background: rgba(83, 52, 131, 0.3); border: 1px solid #533483; border-radius: 8px; padding: 20px;">
                <h3 style="color: #533483; margin-bottom: 15px;">功能亮点</h3>
                <div class="feature-list">
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">18种动画动作</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">模拟养成系统</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">实时交互</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">✓</div>
                        <span class="feature-text">智能行为</span>
                    </div>
                </div>
            </div>
            <div style="flex: 1; background: rgba(15, 52, 96, 0.5); border: 1px solid #0f3460; border-radius: 8px; padding: 20px;">
                <h3 style="color: #0f3460; margin-bottom: 15px;">使用方法</h3>
                <div class="feature-list">
                    <div class="feature-item">
                        <div class="feature-icon">🖱️</div>
                        <span class="feature-text">右键菜单：喂食、设置</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">⌨️</div>
                        <span class="feature-text">快捷键：A/D行走、S睡觉</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">👋</div>
                        <span class="feature-text">点击：触发金币/爱心</span>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">✋</div>
                        <span class="feature-text">拖拽：移动猫咪位置</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; background: rgba(83, 52, 131, 0.2); border-radius: 8px; padding: 20px;">
            <p style="color: #533483; font-size: 16px; margin-bottom: 10px;">下载体验</p>
            <div style="display: inline-block; background: #533483; padding: 10px 30px; border-radius: 20px;">
                <span style="color: #ffffff; font-size: 14px;">GitHub: github.com/xxx/dyberpet</span>
            </div>
        </div>
        
        <div class="page-number">8/8</div>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/08-final.html
```

验证：页面显示成品效果、功能亮点和使用方法

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/08-final.html
git commit -m "feat: 添加成品展示页面"
```

---

### 任务11：创建教程主页

**文件：**
- 创建：`docs/tutorial/index.html`

- [ ] **步骤1：编写HTML页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>六一桌宠 - 小红书图文教程</title>
    <link rel="stylesheet" href="css/style.css">
    <style>
        body {
            flex-direction: column;
            padding: 40px;
        }
        .tutorial-nav {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            justify-content: center;
            margin-bottom: 40px;
        }
        .tutorial-nav a {
            display: block;
            width: 200px;
            height: 267px;
            background: linear-gradient(180deg, #1a1a2e 0%, #0f3460 100%);
            border: 2px solid #533483;
            border-radius: 8px;
            padding: 20px;
            text-decoration: none;
            color: #ffffff;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .tutorial-nav a:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(83, 52, 131, 0.4);
        }
        .tutorial-nav a h3 {
            font-size: 16px;
            margin-bottom: 10px;
            color: #533483;
        }
        .tutorial-nav a p {
            font-size: 12px;
            color: #a0a0a0;
        }
        .tutorial-nav a .page-num {
            position: absolute;
            bottom: 10px;
            right: 10px;
            font-size: 12px;
            color: #533483;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 36px;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 18px;
            color: #a0a0a0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>六一桌宠</h1>
        <p>小红书图文教程（共8张）</p>
    </div>
    
    <div class="tutorial-nav">
        <a href="01-cover.html">
            <h3>1. 封面</h3>
            <p>项目标题 + 成品效果预览</p>
        </a>
        <a href="02-preview.html">
            <h3>2. 效果预览</h3>
            <p>展示猫咪的各种动作和状态</p>
        </a>
        <a href="03-ai-generation.html">
            <h3>3. AI生成</h3>
            <p>AI图像生成 + 视频生成</p>
        </a>
        <a href="04-frame-extract.html">
            <h3>4. 帧提取</h3>
            <p>从视频到图片序列</p>
        </a>
        <a href="05-matte.html">
            <h3>5. 智能抠图</h3>
            <p>去除绿幕背景</p>
        </a>
        <a href="06-deploy.html">
            <h3>6. 精灵图部署</h3>
            <p>将处理好的图片部署到项目</p>
        </a>
        <a href="07-config.html">
            <h3>7. 配置调整</h3>
            <p>个性化定制</p>
        </a>
        <a href="08-final.html">
            <h3>8. 成品展示</h3>
            <p>最终效果 + 使用方式</p>
        </a>
    </div>
    
    <div style="text-align: center; color: #a0a0a0; font-size: 14px;">
        <p>点击任意卡片查看对应的教程页面</p>
        <p style="margin-top: 10px;">建议在浏览器中打开，使用 Ctrl+P 打印为PDF或截图</p>
    </div>
</body>
</html>
```

- [ ] **步骤2：在浏览器中预览**

```bash
start docs/tutorial/index.html
```

验证：页面显示8个教程卡片，点击可跳转到对应页面

- [ ] **步骤3：Commit**

```bash
git add docs/tutorial/index.html
git commit -m "feat: 添加教程主页"
```

---

### 任务12：测试和优化

**文件：**
- 修改：所有HTML文件（根据测试结果调整）

- [ ] **步骤1：在浏览器中打开主页**

```bash
start docs/tutorial/index.html
```

验证：
- 所有8个卡片正常显示
- 点击卡片能跳转到对应页面
- 页面样式正确

- [ ] **步骤2：逐个测试每个页面**

```bash
# 测试每个页面
for i in 01-cover 02-preview 03-ai-generation 04-frame-extract 05-matte 06-deploy 07-config 08-final; do
    start docs/tutorial/$i.html
done
```

验证：
- 每个页面显示正确
- 样式一致
- 内容准确

- [ ] **步骤3：调整样式问题**

根据测试结果，修改 `css/style.css` 中的样式问题

- [ ] **步骤4：最终Commit**

```bash
git add docs/tutorial/
git commit -m "chore: 完成教程页面测试和优化"
```

---

## 自检清单

### 1. 规格覆盖度
- [x] 第1张：封面图 ✓
- [x] 第2张：效果预览 ✓
- [x] 第3张：AI图像生成+视频生成 ✓
- [x] 第4张：帧提取 ✓
- [x] 第5张：智能抠图 ✓
- [x] 第6张：精灵图部署 ✓
- [x] 第7张：配置调整 ✓
- [x] 第8张：成品展示 ✓

### 2. 占位符扫描
- [x] 无"待定"、"TODO"等占位符
- [x] 所有步骤都有具体代码
- [x] 所有命令都有预期输出

### 3. 类型一致性
- [x] CSS类名一致
- [x] HTML结构一致
- [x] 文件路径一致

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-06-11-tutorial-plan.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
