# -*- coding: utf-8 -*-
"""全量镜像入口：按 sitemap 枚举目标分区并逐页离线化。

用法：
    python tools/run_mirror.py

抓取哪些分区由 mirror.MIRRORED_SECTIONS 决定。站点更新后重跑本脚本即可增量刷新，
已存在页面会被覆盖，未变化页面重复抓取的开销也很低（不下载图片）。
"""
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror

MIRRORED = ("interview", "network", "os", "mysql", "redis", "backend_interview")


def build_url_list():
    """从 sitemap 中筛出需要镜像的站内路径。"""
    req = urllib.request.Request(mirror.BASE + "/sitemap.xml",
                                headers={"User-Agent": mirror.USER_AGENT})
    xml = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    urls = []
    for loc in re.findall(r"<loc>(.*?)</loc>", xml):
        path = loc.replace("https://www.xiaolincoding.com", "")
        if path in ("", "/"):
            urls.append("/")
            continue
        if path.strip("/").split("/")[0] in MIRRORED:
            urls.append(path)
    return urls


def main():
    urls = build_url_list()
    print("共抓取 %d 页" % len(urls))
    ok, fail = 0, []
    for index, path in enumerate(urls, 1):
        for attempt in range(3):
            try:
                mirror.process_page(path)
                ok += 1
                print("[%d/%d] %s" % (index, len(urls), path))
                break
            except Exception as exc:  # 网络抖动时重试，三次仍失败则记录
                if attempt == 2:
                    fail.append((path, str(exc)))
                    print("  失败:", path, exc)
                else:
                    time.sleep(1.5)
        time.sleep(0.15)  # 轻微限速，避免被源站判定为异常流量
    print("成功 %d 页, 失败 %d 页" % (ok, len(fail)))
    if fail:
        with open("mirror_fail.txt", "w", encoding="utf-8") as fh:
            for path, err in fail:
                fh.write("%s\t%s\n" % (path, err))


if __name__ == "__main__":
    main()
