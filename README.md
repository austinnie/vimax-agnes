# ViMax-Agnes（Fork）

> **本仓库 fork 自 [austinnie/vimax-agnes](https://github.com/austinnie/vimax-agnes)**，
> 原项目源自 [lcy362/vimax-agnes](https://github.com/lcy362/vimax-agnes)，
> 而 lcy362 的项目又基于 [HKUDS/ViMax](https://github.com/HKUDS/ViMax)。
>
> **本 fork 的改动：**
> - 为 Chat / Image / Video / 下载全链路加入 **429 / 5xx / 网络错误**的指数退避重试
> - 视频提交加入**主动节流**，避免触发服务端限流
> - Chat 调用之间加入**最小间隔控制**，减少 429
> - 修复了原版一处 DNS 抖动即崩溃的问题
> - 移除 `start.sh`，统一使用 `python run_creative.py`（跨平台）

**免费 AI 视频生成 —— 用 Agnes AI 免费模型，把任意文字创意变成多场景、角色一致的完整视频。**

> 使用 Agnes AI 免费模型（`agnes-video-v2.0`、`agnes-image-2.1-flash`、`agnes-2.0-flash`）从文本生成视频 —— 无需 GPU、无需信用卡，只需一个 API Key。

---

## 它是什么

ViMax-Agnes 是一个开源的 **Agentic 视频生成框架**，调用 [Agnes AI](https://platform.agnes-ai.com) API，将文字创意自动转化为完整视频。三个 Agnes 免费模型协同工作：

- **agnes-2.0-flash**（Chat）—— 从你的创意出发，写故事、脚本、视觉 prompt
- **agnes-image-2.1-flash**（Image）—— 通过 text-to-image 生成角色参考图、关键帧
- **agnes-video-v2.0**（Video）—— 通过 text-to-video（t2v）、image-to-video（ti2vid）、keyframes 模式生成场景视频

无需注册费、无需信用卡，[免费获取 Agnes API Key](https://platform.agnes-ai.com) 即可开始生成。

## 核心功能

**一条命令，创意变视频**
写一个 YAML 文件描述你的创意，运行 `python run_creative.py creatives/<name>.yaml`，等待出片。故事、图片、视频、拼接 —— 全流程自动执行。

**跨场景角色一致性**
两阶段方案锁定视觉身份：先生成（或由你提供）一张角色参考图，然后每个场景视频都以它为起始帧通过 `ti2vid` 模式生成，保持外貌、服装和风格统一。

**三种场景串联模式**
- `none` —— 每个场景独立生成，共用同一张参考图。速度最快。
- `keyframes` —— 顺序生成，AI 计算首帧 + 尾帧关键帧，场景过渡最平滑。**（推荐）**
- `ti2vid` —— 顺序生成，通过 img2img 生成场景间的过渡帧。

**智能缓存与断点续跑**
每个中间结果（故事、脚本、参考图、场景视频）都会持久化到磁盘。重新运行时只生成缺失部分 —— 天然支持崩溃恢复。

**多模态图片分析**
提供自己的参考图或自定义尾帧图片，系统会通过多模态 LLM 分析图片内容，将视觉信息融入故事和生成 prompt。

**实时进度反馈**
中文进度提示 + emoji 标记，支持文件日志，适合后台运行。

**健壮的网络层（本 fork 新增）**
- Chat / Image / Video 全部走带重试的 POST 封装
- 429 和 5xx 自动指数退避（15s → 30s → 60s → …，上限 180s）
- DNS 抖动、连接重置等 `ConnectionError` 也会自动重试
- 视频提交之间有主动节流，从源头减少 429

## 快速开始

### 环境要求

- Python 3.10+
- 一个 Agnes AI API Key —— [免费注册](https://platform.agnes-ai.com)
- **ffmpeg**（必须，用于抽取尾帧和拼接视频），确保 `ffmpeg -version` 能正常运行

### 安装

```bash
git clone https://github.com/austinnie/vimax-agnes.git
cd vimax-agnes
```

Linux / macOS：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Windows：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 设置 API Key

**推荐方式**：设置环境变量。

Linux / macOS：

```bash
export AGNES_API_KEY="your-agnes-api-key"
```

Windows CMD（临时）：

```cmd
set AGNES_API_KEY=your-agnes-api-key
```

Windows CMD（永久）：

```cmd
setx AGNES_API_KEY "your-agnes-api-key"
```

Windows PowerShell：

```powershell
$env:AGNES_API_KEY="your-agnes-api-key"
```

其他可选方式：
- 编辑 `configs/idea2video.yaml` 中的 `api_key` 字段
- 命令行传入 `-k` 参数

> 优先级：命令行 `-k` > 环境变量 `AGNES_API_KEY` > 配置文件 `configs/idea2video.yaml`

> ⚠️ 注意：本项目 **不读取 `.api_key` 文件**（原 README 中提到的该方式在当前代码中无效）。

### 运行

```bash
# 查看可用创意列表
python run_creative.py --list

# 运行指定创意
python run_creative.py creatives/frog.yaml

# 指定 API Key（覆盖环境变量）
python run_creative.py creatives/frog.yaml -k "your-api-key"
```

### 查看结果

- 最终视频：`.working_dir/<创意名称>/final_video.mp4`
- 运行日志：`.working_dir/logs/`

## 创意配置

在 `creatives/` 目录下用 YAML 定义你的视频创意：

```yaml
name: "my_video"

idea: |
  一个机器人在洒满阳光的工作室里学画画，
  逐渐创作出一幅融合科技与艺术的杰作。

user_requirement: |
  3个场景，每个场景10秒，电影质感

style: "电影质感写实风格"

chaining_mode: keyframes     # none | keyframes | ti2vid
video_width: 768             # 竖屏 768x1152
video_height: 1152
reference_image: ""          # 可选：本地路径或 URL
# end_frame_images:          # 可选：自定义每场景尾帧
#   - /path/to/end_0.png
```

然后运行：`python run_creative.py creatives/my_video.yaml`

> ⚠️ **尺寸映射提示**：Agnes 的视频接口只接受固定预设尺寸。如果你写 `768x1152`，服务端可能自动映射为最接近的预设（如 `832x1088`，3:4 比例），最终视频比例会与请求值略有差异。

## 系统架构

```
creatives/*.yaml          ← 你的创意
        │
        ▼
┌─────────────────┐
│  run_creative.py │  ← 统一入口
└────────┬────────┘
         │
┌────────▼────────┐
│   编剧模块       │  Agnes Chat (agnes-2.0-flash)
│   故事 + 脚本    │  → 故事、场景、尾帧 prompt
└────────┬────────┘
         │
┌────────▼────────┐
│   图片生成器     │  Agnes Image (agnes-image-2.1-flash)
│   角色参考图     │  → 参考图、尾帧图片
└────────┬────────┘
         │
┌────────▼────────┐
│   视频生成器     │  Agnes Video (agnes-video-v2.0)
│   逐场景视频     │  → t2v / ti2vid / keyframes
└────────┬────────┘
         │
┌────────▼────────┐
│   视频拼接       │  moviepy
│   final_video    │
└─────────────────┘
```

## 角色一致性原理

1. **阶段一（t2i）** —— 从故事的角色描述中生成一张角色参考图，也可以由你直接提供。
2. **阶段二（ti2vid）** —— 每个场景视频以该参考图作为起始帧生成。视频模型从同一视觉锚点出发进行动画化，保留角色设计、配色和构图。

> **提示**：卡通 / 风格化画风一致性效果最好。写实风格建议直接提供 `reference_image`。

## 使用的 Agnes AI 模型

本项目通过 OpenAI 兼容 API（`https://apihub.agnes-ai.com/v1`）使用三个 Agnes 免费模型：

| 用途 | Agnes 模型 | API 接口 | 模式 |
|------|-----------|---------|------|
| 故事和脚本编写 | `agnes-2.0-flash` | `POST /chat/completions` | 对话 |
| 角色参考图和关键帧 | `agnes-image-2.1-flash` | `POST /images/generations` | text-to-image (t2i) |
| 图片编辑和过渡帧 | `agnes-image-2.0-flash` | `POST /images/generations` | image-to-image (i2i) |
| 场景视频生成 | `agnes-video-v2.0` | `POST /videos` | t2v / ti2vid / keyframes |
| 视频任务轮询 | — | `GET /videos/{task_id}` | 异步轮询 |

所有模型均**免费使用**，只需 Agnes API Key —— 无需信用卡、无需 GPU。

## 配置

编辑 `configs/idea2video.yaml` 调整每场景视频时长：

```yaml
video_generator:
  init_args:
    default_duration: 10  # 每场景秒数（5, 10, 15, 18, 20）
```

| 时长 | 帧数 | 帧率 |
|------|------|------|
| 5秒 | 121 | 24 |
| 10秒 | 241 | 24 |
| 15秒 | 361 | 24 |
| 18秒 | 441 | 24 |
| 20秒 | 441 | 22 |

## 项目结构

```
vimax-agnes/
├── run_creative.py                   # 统一入口（跨平台）
├── main_idea2video.py                # 编程式入口
├── creatives/                        # 创意 YAML 配置
│   ├── child.yaml
│   ├── example.yaml
│   ├── frog.yaml
│   ├── girldunk.yaml
│   ├── hot_spring_robot.yaml
│   └── singing_dancing.yaml
├── configs/idea2video.yaml           # 系统配置
├── agents/screenwriter.py            # LLM 编剧 Agent
├── tools/
│   ├── image_generator_agnes_api.py  # 图片生成（t2i + i2i）
│   └── video_generator_agnes_api.py  # 视频生成（t2v/ti2vid/keyframes）
├── interfaces/                       # Pydantic 数据模型
├── pipelines/idea2video_pipeline.py  # 核心编排流水线
├── utils/                            # 下载工具（带重试）
├── requirements.txt
└── LICENSE
```

## 常见问题

**Q：为什么一直 429？**
Agnes 免费模型对调用频率有限流。本 fork 已加入指数退避重试和提交节流，遇到 429 会自动等待并重试，不需要你手动干预。

**Q：视频生成很慢？**
单个 10 秒场景通常需要 2–3 分钟。整条流水线跑 5 个场景大约 15–25 分钟。免费模型就是这个速度。

**Q：生成的尺寸和 YAML 里写的不一样？**
Agnes 视频接口只接受固定预设尺寸，会自动映射到最接近的预设（如 768x1152 → 832x1088）。这是服务端行为，客户端无法改变。

**Q：中断了怎么办？**
直接重跑同一条命令。缓存机制会跳过已完成部分，只生成缺失的。已提交的视频任务会从 `task.json` 恢复。

**Q：Windows 上提示 `ffmpeg 不是内部或外部命令`？**
需要手动安装 ffmpeg 并把它加入系统 PATH。验证：命令行运行 `ffmpeg -version` 能输出版本信息。

## 致谢

- [ViMax](https://github.com/HKUDS/ViMax) —— 原始 Agentic 视频生成框架
- [lcy362/vimax-agnes](https://github.com/lcy362/vimax-agnes) —— 本 fork 的直接上游
- [austinnie/vimax-agnes](https://github.com/austinnie/vimax-agnes) —— 本 fork 的来源
- [Agnes AI](https://platform.agnes-ai.com) —— AI 生成 API

## 许可证

MIT