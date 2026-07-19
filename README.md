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
3. 请求 iesdouyin.com 页面 → 解析 `window._ROUTER_DATA` JSON
4. 视频：提取 play_addr → 构造无水印下载地址
5. 图文：提取 images[] → 原图下载
6. ⚡ **限速降级**：iesdouyin WAF 限速时，自动切换到 `www.douyin.com/aweme/v1/web/aweme/detail/` API

## 注意事项

- iesdouyin.com 存在间歇性 WAF 限速（ByteDance Acrawler），遇到时等待一段时间重试即可
- 脚本已内置限速降级逻辑，大部分情况下无需手动干预
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
