# -*- coding: utf-8 -*-
"""xiaolincoding.com 静态离线镜像核心模块。

站点是 nginx 托管的 VuePress 静态站，正文在 SSR 阶段就已写进 HTML。所谓的
"关注公众号解锁全文"由第三方 readmore.js 在浏览器里完成，它只负责把 DOM 折叠起来，
服务器返回的 HTML 本身包含完整正文。因此只要剥离页面脚本，全文就会永久展开，
既不需要登录 cookie，也不需要绕过任何验证。

由于离线阅读依赖 file:// 直接打开页面，根相对链接（如 /assets/css/xxx.css）会解析到
文件系统根目录而失效。本模块把所有站内链接改写为相对路径，同时把样式表下载到本地，
图片则按要求保持远程 CDN 地址。
"""
import os
import re
import sys
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

BASE = "https://www.xiaolincoding.com"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")

# 仓库根目录默认为 tools/ 的上一级，可通过环境变量覆盖以便在别处运行
ROOT = os.environ.get(
    "XIAOLIN_MIRROR_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

# 本次镜像的顶层分区。其它分区的站内链接保留为线上绝对地址，避免离线打开时指向本地缺失文件
MIRRORED_SECTIONS = {"", "interview", "network", "os", "mysql", "redis", "backend_interview"}

# 记录已处理过的本地资源，避免重复下载
_downloaded = set()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def local_html_path(root_relative_url):
    """把站内根路径映射到本地文件路径，如 /interview/ -> interview/index.html。"""
    if root_relative_url in ("", "/"):
        return "home.html"
    path = root_relative_url.split("?", 1)[0].split("#", 1)[0].lstrip("/")
    if path.endswith("/"):
        path += "index.html"
    return path


def rewrite_internal_href(href, page_local_path):
    """把站内链接改写为相对当前页面的本地路径；被排除的分区保留为线上地址。"""
    if not href:
        return href
    lowered = href.lower()
    if lowered.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return href
    if href.startswith("http://") or href.startswith("https://") or href.startswith("//"):
        return href

    split = urllib.parse.urlsplit(href)
    base, fragment = split.path, ("#" + split.fragment if split.fragment else "")
    if not base.startswith("/"):
        return href  # 已是相对链接，保持不动

    section = base.strip("/").split("/")[0]
    if base == "/" or section in MIRRORED_SECTIONS:
        target = local_html_path(base)
        page_dir = os.path.dirname(page_local_path)
        rel = os.path.relpath(target, page_dir) if page_dir else target
        return rel + fragment
    return BASE + base + fragment


def rewrite_img_src(src):
    """图片保持远程；仅把根相对路径补成绝对 URL，避免离线打开时指向文件系统根。"""
    if src and src.startswith("/") and not src.startswith("//"):
        return BASE + src
    return src


def _rewrite_css_urls(css_text, css_local_rel):
    """把样式表里的根相对 url() 一并本地化，保证离线打开时样式完整。"""

    def repl(match):
        raw = match.group(1).strip().strip('"').strip("'")
        if raw.startswith("data:") or raw.startswith("http") or raw.startswith("//"):
            return match.group(0)
        if raw.startswith("/"):
            asset_local = localize_asset(raw)
            new_rel = os.path.relpath(
                os.path.join(ROOT, asset_local),
                os.path.join(ROOT, os.path.dirname(css_local_rel)),
            )
            return "url(%s)" % new_rel.replace(os.sep, "/")
        return match.group(0)

    return re.sub(r"url\(([^)]+)\)", repl, css_text)


def localize_asset(root_relative_path):
    """下载站内根路径资源到仓库对应位置，返回相对仓库根的本地路径。"""
    local_rel = root_relative_path.lstrip("/")
    if local_rel in _downloaded:
        return local_rel
    dest = os.path.join(ROOT, local_rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = fetch(BASE + root_relative_path)
    if root_relative_path.endswith(".css"):
        css_text = _rewrite_css_urls(data.decode("utf-8", "replace"), local_rel)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(css_text)
    else:
        with open(dest, "wb") as fh:
            fh.write(data)
    _downloaded.add(local_rel)
    return local_rel


def _link_to_local(href, page_local_path):
    """把根相对的样式表 href 改写为相对当前页面的本地路径。"""
    local_rel = localize_asset(href)
    page_dir = os.path.dirname(page_local_path)
    rel = os.path.relpath(os.path.join(ROOT, local_rel), os.path.join(ROOT, page_dir)) \
        if page_dir else local_rel
    return rel.replace(os.sep, "/")


def process_page(url_path):
    """抓取并改写单个页面，返回写出的本地路径。"""
    html = fetch(BASE + url_path).decode("utf-8", "replace")
    soup = BeautifulSoup(html, "html.parser")
    page_local = local_html_path(url_path)

    # 剥离所有脚本：readmore 折叠、百度统计、docsearch 都随脚本一起消失
    for tag in soup.find_all("script"):
        tag.decompose()

    for link in list(soup.find_all("link")):
        rel = link.get("rel") or []
        href = link.get("href", "")
        as_attr = (link.get("as") or "").lower()
        if as_attr == "script" or href.endswith(".js"):
            link.decompose()
        elif "stylesheet" in rel or href.endswith(".css"):
            if href.startswith("/"):
                link["href"] = _link_to_local(href, page_local)
        elif href.startswith("/"):
            link["href"] = BASE + href

    for anchor in soup.find_all("a"):
        if anchor.has_attr("href"):
            anchor["href"] = rewrite_internal_href(anchor["href"], page_local)

    for img in soup.find_all("img"):
        if img.has_attr("src"):
            img["src"] = rewrite_img_src(img["src"])

    dest = os.path.join(ROOT, page_local)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(str(soup))
    return page_local


if __name__ == "__main__":
    for path in sys.argv[1:]:
        print("已保存:", process_page(path))
