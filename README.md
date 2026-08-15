# 抖音无水印下载器 (Douyin Downloader Skill)

一键下载抖音视频（无水印 MP4）和图文（原图 JPEG），纯 Python 实现，无需外部工具。

## 功能

- 🎬 **视频下载**：无水印高清视频（.mp4）
- 🖼️ **图文下载**：原图下载（.jpeg，最高分辨率）
- 🤖 **自动识别**：自动判断链接是视频还是图文
- 📋 **批量下载**：支持从 txt 文件批量导入
- 🔄 **自动降级**：遇到 iesdouyin WAF 限速时，自动切换到 detail JSON API 获取视频

## 使用方法

```bash
# 下载单个（从分享链接或分享文本）
python3 scripts/download.py "https://v.douyin.com/xxxx/" [保存目录]

# 批量下载
python3 scripts/download.py --batch links.txt [保存目录]
```

支持以下输入格式：
- 抖音短链：`https://v.douyin.com/xxxx/`
- 完整分享文本：`0.28 复制打开抖音... https://v.douyin.com/xxxx/ b@a.NJ ...`
- 长链接：`https://www.douyin.com/video/xxxx`

## 输出

- **视频**：`{标题}_{video_id}.mp4`
- **图文**：保存在 `{标题}_{note_id}/` 目录，图片命名为 `{作者}_{描述}_{序号}.jpeg`

## 技术说明

1. 提取分享链接 → 301 重定向 → 获取真实 URL
2. 识别 content_type（video/note）
3. 第1层：请求 iesdouyin.com 分享页 → 解析 `window._ROUTER_DATA` JSON
4. 第2层（降级）：自动切换 `www.douyin.com/aweme/v1/web/aweme/detail/` API，缺 ttwid cookie 时自动注册后重试
5. 视频：提取 play_addr → 无水印直链下载
6. 图文：提取 images[] → 原图下载

## 注意事项（坑点）

- **2026-08-12 起 iesdouyin SSR 接口变更**：分享页不再返回 `_ROUTER_DATA` 数据（只给壳），脚本自动走第 2 层 detail API
- **detail API 首次返回空**：原因是缺 **ttwid cookie**（不是限速），脚本已内置自动注册——POST `ttwid.bytedance.com/ttwid/union/register/` 拿 ticket → 走 ixigua callback 拿 ttwid → 带 `Cookie: ttwid=...` 重试
- 视频+图文均支持第 2 层降级；仅当 ttwid 注册后 detail API 仍为空，才是 iesdouyin 间歇性 WAF 限速（ByteDance Acrawler），等一段时间重试即可
- 依赖仅需 `requests` 库，通过 `requirements.txt` + SHA256 hash 校验安装

## 文件结构

```
douyin-downloader-skill/
├── README.md
├── SKILL.md
├── requirements.txt
└── scripts/
    └── download.py       # 核心下载脚本
```

## 许可

MIT
