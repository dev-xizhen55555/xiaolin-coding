# 小林coding 离线资料库

把 [xiaolincoding.com](https://www.xiaolincoding.com) 的技术内容整理成可离线浏览的静态 HTML。
页面脚本已剥离，样式本地化，正文图片保留远程 CDN 地址。用浏览器打开根目录的 `index.html`
即可通过中文目录进入全部内容。

## 收录内容

| 分区 | 页数 | 说明 |
| --- | --- | --- |
| interview | 28 | 面试八股题，含 Java、C++、Go、Python、数据库、操作系统、网络、MQ、分布式、系统设计、Linux、Git、Docker、测试开发、后端进阶 |
| network | 42 | 图解网络 |
| os | 36 | 图解操作系统 |
| mysql | 24 | 图解 MySQL |
| redis | 16 | 图解 Redis |
| backend_interview | 51 | 互联网大厂面经 |

未收录 `reader_nb`、`cs_learn`、`project`、`openai`、`salary`、`other` 等分区。这些分区里的站内链接
在离线页面中会被保留为线上绝对地址，联网时仍可正常跳转。

## 方法论

这套离线化的核心判断是：**正文一直就在服务器返回的 HTML 里，所谓"关注公众号解锁全文"只是前端折叠**。

页面接入的是第三方 readmore 插件（`qiniu.techgrow.cn/readmore/dist/readmore.js`），抓包可以看到它
向 `open.techgrow.cn` 校验 `readmore_token` 后再执行浏览上报。但该 token 只决定前端是否把正文收起，
服务端返回的 HTML 本身就是完整正文。直接剥离页面脚本后，正文会永久完整展开，因此不需要登录 cookie，
也不需要绕过任何验证码或风控。

识别出这一点后，处理流程如下。

站点基于 VuePress 1.9.7，由 nginx 直接托管静态 HTML，`robots.txt` 指向 `sitemap.xml`。因此第一步是
读取 `sitemap.xml` 枚举全部 267 个页面，再按分区筛选出需要镜像的 198 页，不需要爬虫去发现链接。

第二步是对每个页面做 DOM 改写。用 BeautifulSoup 删除所有 `<script>` 以及 `preload`/`prefetch` 的 script
引用，这一步同时去掉了 readmore 折叠、百度统计、公众号广告和 docsearch，页面变得干净且没有离线报错。

第三步是资源与链接处理。样式表被下载到 `assets/`，并递归把 CSS 内 `url()` 引用的根相对资源也本地化，
保证离线打开时排版和代码高亮正常。根相对链接（如 `/interview/java.html`）在 `file://` 下会解析到文件系统
根目录而失效，所以统一改写为相对当前页面的路径；指向被排除分区的链接则补成线上绝对地址。正文图片按
需求保持远程 CDN 地址，不做下载。

最后扫描各分区页面读取 `<title>`，按分区和子目录生成中文目录页 `index.html`。

## 目录结构

```
.
├── index.html            生成的中文目录导航
├── home.html             原站首页（离线版）
├── interview/ network/ os/ mysql/ redis/ backend_interview/
├── assets/               本地化的样式表与图标
└── tools/                抓取与生成脚本
```

## 使用

浏览：直接用浏览器打开 `index.html`。

离线化脚本需要 Python 3 与 beautifulsoup4：

```bash
pip install beautifulsoup4
```

全量或增量抓取（站点更新后重跑即可，已存在页面会被覆盖）：

```bash
python tools/run_mirror.py
```

只抓取指定页面：

```bash
python tools/mirror.py /interview/redis.html /interview/java.html
```

重新生成目录页：

```bash
python tools/gen_index.py
```

脚本会把仓库根目录作为输出目录，也可以通过环境变量 `XIAOLIN_MIRROR_ROOT` 指定其它位置。

## 注意

图片使用远程 CDN，断网时页面文字与排版正常，但图片无法显示。

本项目仅作个人学习用途，全部内容版权归 小林coding 所有。
