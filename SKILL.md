---
name: douyin-downloader
description: |
  抖音无水印下载器。支持视频（无水印）+ 图文（原图）下载。
  自动识别链接类型，单个/批量下载。
  原生Python实现，无需额外配置。
  GitHub: https://github.com/belingud/douyin-downloader-skill
version: "1.0.5"
author: belingud
source_repo: "https://github.com/belingud/douyin-downloader-skill"
base_dir: douyin-downloader-skill
---

# 抖音无水印下载器 Skill

## 功能

- 🎬 **视频下载**：无水印高清视频
- 🖼️ **图文下载**：原图下载（JPEG，最高分辨率）
- 🤖 **自动识别**：自动判断链接是视频还是图文
- 📋 **批量下载**：支持从 txt 文件批量导入
- 🚫 **无需登录**：不需要 Cookie 或登录态

## 工作原理

```
用户输入（分享链接/文本）
  → 正则提取短链
  → GET请求跟随301重定向 → 获取真实URL
  → 识别类型（video/note）
  → GET iesdouyin.com/share/{type}/{id}/
  → 解析 window._ROUTER_DATA JSON
  → 视频：提取 play_addr.uri → 构造无水印播放地址
  → 图文：提取 images[].url_list → 优选 jpeg 原图
  → 流式下载到本地
```

## 目录结构

```
douyin-downloader-skill/
  ├── SKILL.md          ← 本文件（Skill说明 + SOP）
  ├── requirements.txt  ← 依赖锁定（SHA256 hash）
  └── scripts/
      └── download.py   ← 核心下载脚本（支持视频+图文）
```

## 使用方法

### 单个下载

```python
import subprocess, sys, os

script = os.path.join(os.path.dirname(__file__), "scripts", "download.py")
link = '用户提供的抖音链接或分享文本'
subprocess.run([sys.executable, script, link])
```

### 指定下载目录

```python
subprocess.run([sys.executable, script, link, '/path/to/output'])
```

### 批量下载

```python
subprocess.run([sys.executable, script, '--batch', 'links.txt', '/path/to/output'])
```

### 命令行直接使用

```bash
# 下载视频或图文
python download.py "抖音分享链接"

# 指定保存目录
python download.py "抖音分享链接" /tmp/downloads

# 批量下载
python download.py --batch links.txt /tmp/downloads
```

## 输出

- **视频**：`{标题}_{video_id}.mp4`
- **图文**：保存在 `{标题}_{note_id}/` 目录下，文件名为 `图片1.jpeg`, `图片2.jpeg` ...
- 终端显示实时下载进度

## 操作规范（SOP）

1. **获取链接**：用户粘贴抖音分享链接或完整分享文本（脚本自动提取链接）
2. **确认保存目录**：默认保存到脚本所在目录
3. **执行下载**：自动识别视频/图文类型，下载无水印内容
4. **验证结果**：检查下载目录中新增的文件
5. **批量任务**：多个链接先写入 txt 文件，用 `--batch` 模式

## 注意事项

- 需要 Python 3.8+
- 依赖会自动安装（requests 库）
- 不需要登录 Cookie
- 抖音 API 可能变化，若解析失败可检查数据结构
