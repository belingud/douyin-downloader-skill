# 抖音无水印下载器 🎬

支持 **视频（无水印）** + **图文（原图）** 下载。自动识别链接类型，无需登录。

## 功能

- 🎬 **视频下载** — 无水印高清视频 (MP4)
- 🖼️ **图文下载** — 原图下载 (JPEG，最高分辨率)
- 🤖 **自动识别** — 自动判断链接是视频还是图文
- 📋 **批量下载** — 支持从 txt 文件批量导入
- 🚫 **无需登录** — 不需要 Cookie 或登录态

## 快速使用

```bash
# 下载单个（视频或图文均可）
python download.py "抖音分享链接"

# 指定保存目录
python download.py "抖音分享链接" /tmp/downloads

# 批量下载（每行一个链接的 txt 文件）
python download.py --batch links.txt /tmp/downloads
```

输入格式支持：
- 短链：`https://v.douyin.com/xxxx/`
- 完整分享文本：`0.28 复制打开抖音... https://v.douyin.com/xxxx/ b@a.NJ ...`
- 长链接：`https://www.douyin.com/video/xxxx` 或 `https://www.douyin.com/note/xxxx`

## 输出

- **视频**：`{标题}_{video_id}.mp4`
- **图文**：保存在 `{标题}_{note_id}/` 目录下，`图片1.jpeg`、`图片2.jpeg`...
- 终端显示实时下载进度

## 技术原理

1. 从分享链接通过 301 重定向获取真实 URL
2. 识别内容类型（video/note）
3. 请求 iesdouyin.com 分享页，解析 `window._ROUTER_DATA` JSON
4. **视频**：提取 `play_addr.uri` → 构造无水印播放地址
5. **图文**：提取 `images[].url_list` → 优选 jpeg 原图

## 依赖

- Python 3.8+
- requests（自动安装，SHA256 hash 校验）

## License

MIT
