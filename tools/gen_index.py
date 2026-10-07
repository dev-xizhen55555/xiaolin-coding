# -*- coding: utf-8 -*-
"""生成离线资料库的目录导航页 index.html。

扫描仓库内各分区的 HTML 页面，读取 <title> 作为条目名称，按分区和子目录分组输出。
用法：
    python tools/gen_index.py
"""
import html
import os

from bs4 import BeautifulSoup

ROOT = os.environ.get(
    "XIAOLIN_MIRROR_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

SECTION_NAMES = [
    ("interview", "01 面试八股题"),
    ("network", "02 图解网络"),
    ("os", "03 图解操作系统"),
    ("mysql", "04 图解MySQL"),
    ("redis", "05 图解Redis"),
    ("backend_interview", "06 互联网大厂面经"),
]

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小林八股文 离线资料库</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 960px;
         margin: 0 auto; padding: 3rem 1.5rem 6rem; line-height: 1.7; color: #2c3e50; }}
  h1 {{ font-size: 1.8rem; margin-bottom: .4rem; }}
  .sub {{ color: #888; margin-top: 0; }}
  h2 {{ margin-top: 2.8rem; padding-bottom: .4rem; border-bottom: 2px solid #3eaf7c; font-size: 1.3rem; }}
  h3 {{ margin: 1.6rem 0 .4rem; font-size: 1.05rem; color: #476582; }}
  ul {{ list-style: none; padding-left: 0; margin: .4rem 0; }}
  li {{ margin: .25rem 0; }}
  a {{ color: #2c3e50; text-decoration: none; }}
  a:hover {{ color: #3eaf7c; text-decoration: underline; }}
  .home {{ display: inline-block; margin-bottom: 1rem; color: #3eaf7c; font-weight: 600; }}
  footer {{ margin-top: 4rem; color: #999; font-size: .85rem; border-top: 1px solid #eee; padding-top: 1rem; }}
</style>
</head>
<body>
<h1>小林八股文 离线资料库</h1>
<p class="sub">共 {total} 页，脚本已剥离，图片走远程 CDN，样式本地化。</p>
<a class="home" href="home.html">→ 原站首页（离线版）</a>
{body}
<footer>离线镜像仅供个人学习，内容版权归 小林coding 所有。</footer>
</body>
</html>
"""


def page_title(path):
    try:
        soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        return title.replace(" | 小林coding", "").strip()
    except Exception:
        return os.path.basename(path)


def collect(section):
    """收集某个分区下所有正文页，跳过分区自身的首页。"""
    items = []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, section)):
        for name in files:
            if not name.endswith(".html"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            if rel.endswith("/index.html"):
                continue
            items.append((rel, page_title(full)))
    items.sort()
    return items


def build_body():
    body = []
    total = 0
    for section, name in SECTION_NAMES:
        items = collect(section)
        total += len(items)
        body.append('<h2>%s <span style="font-weight:400;font-size:.85rem;color:#999;">(%d 篇)</span></h2>'
                    % (html.escape(name), len(items)))
        groups = {}
        for rel, title in items:
            parts = os.path.dirname(rel).split("/", 1)
            key = parts[1] if len(parts) > 1 else ""
            groups.setdefault(key, []).append((rel, title))
        for key in sorted(groups):
            if key:
                body.append("<h3>%s</h3>" % html.escape(key))
            body.append("<ul>")
            for rel, title in groups[key]:
                body.append('  <li><a href="%s">%s</a></li>'
                            % (html.escape(rel), html.escape(title or rel)))
            body.append("</ul>")
    return total, "\n".join(body)


def main():
    total, body = build_body()
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(PAGE_TEMPLATE.format(total=total, body=body))
    print("index.html 已生成，共收录 %d 篇" % total)


if __name__ == "__main__":
    main()
