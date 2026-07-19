# -*- coding: utf-8 -*-
"""
抖音无水印下载器 - 核心脚本
支持：视频（无水印） + 图文（原图）
下载原理：
  1. 提取分享链接 -> 跟随301重定向 -> 获取真实URL
  2. 解析 video_id，识别类型（video/note）
  3. 请求 https://www.iesdouyin.com/share/video/{id}/ 或 /share/note/{id}/
  4. 从 window._ROUTER_DATA JSON 中提取内容
  5. 视频：构造无水印下载地址下载 .mp4
  6. 图文：提取所有图片原图下载 .jpeg
  7. 降级方案（视频专用）：当 iesdouyin 页面被 WAF 限速时，
     自动降级到 www.douyin.com/aweme/v1/web/aweme/detail/ API
"""
import sys
import os

# 自动安装依赖（仅通过 requirements.txt + --require-hashes，防止供应链投毒）
try:
    import requests
except ImportError:
    import subprocess
    _req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements.txt")
    if os.path.exists(_req_file):
        print("[*] 检测到缺少 requests 库，正在通过 requirements.txt 安装（SHA256 hash 校验）...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", _req_file, "--require-hashes", "-q"],
            check=True,
        )
    else:
        print("[!] 错误：未找到 requirements.txt，无法安全安装依赖。")
        print("    请手动执行：pip install -r requirements.txt --require-hashes")
        sys.exit(1)
    import requests

import re
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/116.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "https://www.douyin.com/?is_from_mobile_home=1&recommend=1",
}


def extract_url(text: str) -> str | None:
    """从分享文本中提取抖音链接（短链或长链）"""
    m = re.search(r"https?://v\.douyin\.com/[a-zA-Z0-9\-_.]+", text)
    if m:
        url = m.group(0)
        return url if url.endswith("/") else url + "/"
    m = re.search(r"https?://(?:www\.)?douyin\.com/(?:video|note)/[0-9]+", text)
    if m:
        return m.group(0)
    return None


def get_real_url(share_url: str) -> str | None:
    """跟随重定向，获取真实URL"""
    if "douyin.com/video/" in share_url or "douyin.com/note/" in share_url:
        return share_url
    try:
        r = requests.get(share_url, headers=HEADERS, allow_redirects=True, timeout=10)
        return r.url
    except Exception as e:
        print(f"[!] 获取真实链接失败: {e}")
        return None


def get_content_id(real_url: str) -> tuple[str | None, str | None]:
    """从真实 URL 中提取内容 ID 和类型（video/note），返回 (content_id, content_type)"""
    # 先尝试从 URL 路径判断类型
    if "/note/" in real_url or "share/note/" in real_url:
        content_type = "note"
        m = re.search(r"/note/([0-9]+)", real_url)
        if m:
            return m.group(1), content_type
    elif "/video/" in real_url or "share/video/" in real_url:
        content_type = "video"
        m = re.search(r"/video/([0-9]+)", real_url)
        if m:
            return m.group(1), content_type

    # 从 URL 参数提取
    for param in ["modal_id", "note_id", "item_id", "video_id"]:
        m = re.search(rf"{param}=([0-9]+)", real_url)
        if m:
            return m.group(1), "video"  # 默认按视频处理，后续自动检测

    # 兜底：提取 15 位以上数字作为 ID
    m = re.search(r"/([0-9]{15,})", real_url)
    if m:
        return m.group(1), "video"

    return None, None


def get_router_data(content_id: str, content_type: str) -> dict | None:
    """请求详情页并解析 _ROUTER_DATA JSON（自动尝试 video/note 两种路径）"""
    urls_to_try = [
        f"https://www.iesdouyin.com/share/{content_type}/{content_id}/",
        f"https://www.iesdouyin.com/share/{'note' if content_type == 'video' else 'video'}/{content_id}/",
    ]

    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            m = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", r.text, re.DOTALL)
            if m:
                data = json.loads(m.group(1).strip())
                if _has_item_list(data):
                    return data
        except Exception:
            continue

    print("[!] 页面中未找到有效 _ROUTER_DATA")
    return None


def get_detail_api(content_id: str) -> dict | None:
    """降级方案：从 douyin.com 的 detail JSON API 获取视频信息。
    
    dyfetch 项目（HuanNan520/dyfetch）验证此 API 在 iesdouyin WAF 限速时仍可工作。
    仅支持视频，不支持图文。
    """
    api_url = (
        "https://www.douyin.com/aweme/v1/web/aweme/detail/"
        f"?aweme_id={content_id}"
        "&device_platform=webapp&aid=6383&channel=channel_pc_web"
    )
    detail_headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Mobile/15E148 Safari/604.1"
        ),
        "Referer": "https://www.douyin.com/",
    }
    try:
        r = requests.get(api_url, headers=detail_headers, timeout=15)
        if r.status_code != 200 or not r.text.strip():
            print("[~] detail API 返回为空（可能也被限速）")
            return None
        data = r.json()
        ad = data.get("aweme_detail")
        if not ad:
            print(f"[~] detail API 无 aweme_detail（status_code={data.get('status_code')}）")
            return None
        return data
    except Exception as e:
        print(f"[~] detail API 请求失败: {e}")
        return None


def parse_detail_api(data: dict) -> dict | None:
    """从 detail JSON API 响应中提取视频信息。"""
    try:
        ad = data["aweme_detail"]
        desc = ad.get("desc", "无标题")
        nickname = ad.get("author", {}).get("nickname", "未知作者")
        video_info = ad.get("video", {})
        play_addr = video_info.get("play_addr", {})
        url_list = play_addr.get("url_list", [])

        if not url_list:
            print("[!] detail API 中未找到视频地址")
            return None

        # 优先选 douyinvod.com 直链（已是无水印），否则取第一个
        best_url = next(
            (u for u in url_list if "douyinvod.com" in u),
            url_list[0]
        )

        return {
            "type": "video",
            "desc": desc,
            "nickname": nickname,
            "media": [{
                "url": best_url,
                "filename": f"{_safe_name(desc)}_{ad.get('aweme_id', '')}.mp4",
            }],
        }
    except Exception as e:
        print(f"[!] 解析 detail API 内容出错: {e}")
        return None


def _has_item_list(data: dict) -> bool:
    """检查 _ROUTER_DATA 中是否包含有效的 item_list"""
    try:
        loader = data.get("loaderData", {})
        for k, v in loader.items():
            if not isinstance(v, dict):
                continue
            for k2, v2 in v.items():
                if isinstance(v2, dict) and "item_list" in v2 and v2["item_list"]:
                    return True
        return False
    except Exception:
        return False


def _find_item(data: dict) -> dict | None:
    """从 _ROUTER_DATA 中挖出第一个 item"""
    loader = data.get("loaderData", {})
    for k, v in loader.items():
        if not isinstance(v, dict):
            continue
        for k2, v2 in v.items():
            if isinstance(v2, dict) and "item_list" in v2:
                items = v2["item_list"]
                if items:
                    return items[0]
    return None


def parse_content(data: dict) -> dict | None:
    """
    从 JSON 数据中提取内容信息，自动判断视频还是图文。
    返回格式：
    {
        "type": "video" | "image",
        "desc": str,
        "nickname": str,
        "media": [
            {"url": "...", "filename": "..."},
            ...
        ]
    }
    """
    try:
        item = _find_item(data)
        if not item:
            print("[!] 未找到 item")
            return None

        desc = item.get("desc", "无标题")
        nickname = item.get("author", {}).get("nickname", "未知作者")

        # 判断类型：有 images 就是图文，否则是视频
        images = item.get("images", [])
        if images:
            # ---- 图文 ----
            media_list = []
            for i, img in enumerate(images):
                # 优先选 jpeg/jpg 后缀（清晰度最高），其次第一个
                best_url = None
                for u in img.get("url_list", []):
                    if ".jpeg?" in u or ".jpg?" in u:
                        best_url = u
                        break
                if not best_url:
                    best_url = img["url_list"][0]

                ext = "jpeg" if (".jpeg?" in best_url or ".jpg?" in best_url) else "webp"
                name_part = _safe_name(nickname, 12)
                desc_part = _safe_name(desc, 18)
                filename = f"{name_part}_{desc_part}_{i + 1}.{ext}"
                media_list.append({"url": best_url, "filename": filename})

            return {
                "type": "image",
                "desc": desc,
                "nickname": nickname,
                "media": media_list,
            }
        else:
            # ---- 视频 ----
            uri = item.get("video", {}).get("play_addr", {}).get("uri")
            if not uri:
                print("[!] 未找到视频 URI")
                return None

            download_url = f"https://www.douyin.com/aweme/v1/play/?video_id={uri}"
            return {
                "type": "video",
                "desc": desc,
                "nickname": nickname,
                "media": [{"url": download_url, "filename": f"{_safe_name(desc)}_{item.get('aweme_id', '')}.mp4"}],
            }

    except Exception as e:
        print(f"[!] 解析内容出错: {e}")
        return None


def _safe_name(text: str, max_len: int = 30) -> str:
    """去除非法字符、多余符号、截断"""
    # 先去掉 emoji 和特殊符号
    text = re.sub(r'[#@&]', '', text)
    # 去掉文件名非法字符
    text = re.sub(r'[\\/*?:"<>|\r\n\t]', '', text)
    # 合并多余空格并 trim
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_len]


def download_file(url: str, filepath: str, is_image: bool = False) -> bool:
    """下载单个文件（视频流式+进度条，图片直接下载）"""
    try:
        print(f"[+] 正在下载: {os.path.basename(filepath)}")
        if is_image:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(r.content)
            size_kb = len(r.content) / 1024
            print(f"[OK] 下载完成！保存至: {os.path.abspath(filepath)} ({size_kb:.0f} KB)")
        else:
            r = requests.get(url, headers=HEADERS, stream=True, timeout=30)
            if r.status_code == 403:
                print("[~] 403，去掉Referer重试...")
                h2 = HEADERS.copy()
                h2.pop("Referer", None)
                r = requests.get(url, headers=h2, stream=True, timeout=30)
            r.raise_for_status()

            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = downloaded / total * 100
                            bar = "#" * int(pct / 2)
                            print(f"\r  [{bar:<50}] {pct:.1f}%", end="", flush=True)
            print()
            print(f"[OK] 下载完成！保存至: {os.path.abspath(filepath)}")
        return True
    except Exception as e:
        print(f"[!] 下载失败: {e}")
        return False


def run(raw_input: str, output_dir: str = None) -> bool:
    """主流程：输入分享链接/文本，自动下载视频或图文"""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)

    share_url = extract_url(raw_input)
    if not share_url:
        print(f"[!] 未在输入中找到有效链接: {raw_input}")
        return False

    print(f"[+] 正在解析链接: {share_url}")
    real_url = get_real_url(share_url)
    if not real_url:
        return False

    content_id, content_type = get_content_id(real_url)
    if not content_id:
        print("[!] 无法提取内容ID")
        return False

    print(f"[+] 内容ID: {content_id} (类型: {content_type})")

    # ---- 第1层：iesdouyin 页面解析 ----
    data = get_router_data(content_id, content_type)
    info = None

    if data:
        info = parse_content(data)

    # ---- 第2层（降级）：detail JSON API（仅视频） ----
    if not info and content_type == "video":
        print("[~] iesdouyin 页面解析失败，尝试降级到 detail JSON API...")
        data2 = get_detail_api(content_id)
        if data2:
            info = parse_detail_api(data2)
            if info:
                print("[~] detail API 降级成功 ✅")

    # 都失败了
    if not info:
        print()
        print("=" * 50)
        print("⚠️  下载失败：抖音 iesdouyin 触发了 WAF 限速防护。")
        print("   这是抖音服务端的间歇性限速，非脚本故障。")
        print("   建议稍等几分钟到几小时后再重试即可恢复。")
        print("=" * 50)
        return False

    content_type_cn = "图文" if info["type"] == "image" else "视频"
    print(f"[+] {content_type_cn}: {info['desc']} | 作者: {info['nickname']}")
    print(f"[+] 共 {len(info['media'])} 个文件待下载")

    # 图文专用子目录
    if info["type"] == "image":
        safe_prefix = _safe_name(info["desc"])
        output_dir = os.path.join(output_dir, f"{safe_prefix}_{content_id}")
        os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    for media in info["media"]:
        filepath = os.path.join(output_dir, media["filename"])
        is_image = info["type"] == "image"
        if download_file(media["url"], filepath, is_image=is_image):
            success_count += 1

    print(f"\n[OK] 全部完成！成功 {success_count}/{len(info['media'])}，保存至: {os.path.abspath(output_dir)}")
    return success_count > 0


def run_batch(txt_file: str, output_dir: str = None) -> None:
    """批量下载：从txt文件逐行读取链接"""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(txt_file):
        print(f"[!] 找不到文件: {txt_file}")
        return

    urls = []
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            with open(txt_file, "r", encoding=enc) as f:
                urls = [l.strip() for l in f if l.strip()]
            break
        except Exception:
            continue

    if not urls:
        print("[!] 文件中未找到有效链接")
        return

    total = len(urls)
    print(f"[+] 共 {total} 个链接，开始批量下载...")
    for i, url in enumerate(urls, 1):
        print(f"\n--- 第 {i}/{total} 个 ---")
        run(url, output_dir)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) < 2:
        print("用法:")
        print("  单个下载:  python download.py <分享链接或文本>")
        print("  批量下载:  python download.py --batch <txt文件路径> [保存目录]")
        print("  指定目录:  python download.py <链接> <保存目录>")
        print(f"  默认保存至: {script_dir}")
        sys.exit(0)

    if sys.argv[1] == "--batch":
        txt = sys.argv[2] if len(sys.argv) > 2 else "links.txt"
        out = sys.argv[3] if len(sys.argv) > 3 else script_dir
        run_batch(txt, out)
    else:
        link = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else script_dir
        run(link, out)
