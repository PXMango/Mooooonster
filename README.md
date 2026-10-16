# 知妖词条离线存档

个人离线阅读库：抓取自 [知妖网](https://www.czhiyao.com/) 公开词条，便于本地检索与扩展。

> **仅供个人学习、离线阅读。**  
> 内容版权归原站与原作者所有；请勿公开传播或用于商业用途。转载请注明出处。

## 目录结构

```
zhiyao-archive/
├── index.html          # 本地检索页（浏览器直接打开）
├── posts/              # 词条 Markdown（约 2475 篇）
├── meta/
│   ├── index.json      # 机读总索引
│   ├── urls.json
│   └── progress.json
└── scripts/            # 抓取与清洗脚本（见会话内 archive_zhiyao.py 等）
```

## 本地使用

- 双击 `index.html`，或
- 任意静态服务：`python -m http.server 8765 --directory .`

## 扩展

1. 把新词条按 `posts/<id>_<标题>.md` 写入（格式见已有文件）
2. 更新 `meta/index.json`
3. 如需批量抓取新文章，参考 `scripts/` 中脚本（礼貌抓取、断点续传）

## 同步

本仓库为**私有**。换电脑：

```bash
git clone <你的私有仓库地址>
```

日常更新：

```bash
git add .
git commit -m "更新词条"
git push
```
