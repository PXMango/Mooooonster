# -*- coding: utf-8 -*-
"""知妖网词条离线存档：批量抓取公开文章正文，存为 Markdown + 本地索引。

礼貌抓取：固定间隔，默认 0.6s；支持断点续传（progress.json）。
仅供个人离线阅读，请保留原文出处信息。
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from lxml import html as LH

ROOT = Path(__file__).resolve().parent / "zhiyao_archive"
POSTS = ROOT / "posts"
META = ROOT / "meta"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ZhiYaoPersonalArchive/1.0 (offline reading; polite crawl)"
DELAY = 0.6
TIMEOUT = 25

SITEMAP_YEARS = [
    "sitemap-post-2016.xml",
    "sitemap-post-2017.xml",
    "sitemap-post-2018.xml",
    "sitemap-post-2019.xml",
    "sitemap-post-2020.xml",
    "sitemap-post-2021.xml",
    "sitemap-post-2022.xml",
    "sitemap-post-2023.xml",
    "sitemap-post-2024.xml",
    "sitemap-post-2025.xml",
]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def get_text(url: str) -> str:
    return get(url).decode("utf-8", errors="replace")


def ensure_dirs():
    POSTS.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)


def collect_urls() -> list[str]:
    urls: list[str] = []
    for name in SITEMAP_YEARS:
        sm_url = f"https://www.czhiyao.com/{name}"
        try:
            raw = get_text(sm_url)
        except Exception as e:
            print(f"[warn] sitemap {name}: {e}", flush=True)
            continue
        found = re.findall(r"<loc>\s*(https?://www\.czhiyao\.com/\d+\.html)\s*</loc>", raw)
        urls.extend(found)
        print(f"[sitemap] {name}: +{len(found)}", flush=True)
        time.sleep(DELAY)
    # 去重保序
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    (META / "urls.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[urls] total unique posts: {len(out)}", flush=True)
    return out


def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ").replace("​", "")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_article(url: str, raw_html: str) -> dict:
    doc = LH.fromstring(raw_html)
    title = ""
    h1 = doc.xpath("//h1")
    if h1:
        title = clean_text(h1[0].text_content())

    date = ""
    # 常见日期：/YYYY/MM/DD/ 或页面上的 2024年1月4日
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if not date:
        t = doc.xpath("//time/@datetime")
        if t:
            date = t[0][:10]

    # 来源分类：知妖词条页里的 breadcrumb / ct 链接
    source = ""
    crumbs = doc.xpath('//a[contains(@href,"/ct/")]/text()')
    crumbs = [clean_text(c) for c in crumbs if clean_text(c) and clean_text(c) != "知妖词条"]
    if crumbs:
        source = crumbs[0]

    # 正文：优先 article / entry-content
    body_nodes = doc.xpath("//article") or doc.xpath('//div[contains(@class,"entry-content")]')
    body_html = body_nodes[0] if body_nodes else doc
    # 去掉评论、侧栏噪声
    for bad in body_nodes[0].xpath(".//script|.//style|.//nav|.//form|.//*[contains(@class,'comment')]") if body_nodes else []:
        parent = bad.getparent()
        if parent is not None:
            parent.remove(bad)

    # 标签
    tags = [clean_text(x) for x in doc.xpath('//a[contains(@href,"/tag/")]/text()')]
    tags = [t for t in tags if t and t not in ("标签",)]

    # 提取正文段落
    paragraphs = []
    for el in body_nodes[0].iter() if body_nodes else []:
        if el.tag in ("p", "h2", "h3", "h4", "li", "blockquote"):
            txt = clean_text(el.text_content())
            if txt:
                paragraphs.append(txt)
    # 去掉重复（嵌套）
    dedup = []
    for p in paragraphs:
        if not dedup or dedup[-1] != p:
            if p not in dedup[-3:] if dedup else True:
                dedup.append(p)
    body = "\n\n".join(dedup)

    # 摘要：列表页风格，正文首段
    summary = dedup[0] if dedup else ""

    return {
        "url": url,
        "id": re.search(r"/(\d+)\.html", url).group(1) if re.search(r"/(\d+)\.html", url) else "",
        "title": title,
        "date": date,
        "source": source,
        "tags": tags[:12],
        "summary": summary[:200],
        "body": body,
    }


def to_markdown(item: dict) -> str:
    lines = [
        f"# {item['title']}",
        "",
        f"- **日期**: {item['date'] or '未知'}",
        f"- **来源**: {item['source'] or '知妖词条'}",
        f"- **标签**: {', '.join(item['tags']) if item['tags'] else '—'}",
        f"- **原文**: <{item['url']}>",
        "",
        "---",
        "",
        item["body"],
        "",
        "---",
        "",
        f"*存档自知妖网 {item['url']}，仅供个人离线阅读。*",
        "",
    ]
    return "\n".join(lines)


def load_progress() -> dict:
    p = META / "progress.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"done": [], "failed": []}


def save_progress(prog: dict):
    (META / "progress.json").write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")


def build_index(items: list[dict]):
    (META / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    # 可读 HTML 索引
    rows = []
    for it in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        rel = f"posts/{it['id']}_{re.sub(r'[^0-9A-Za-z一-鿿]+','_',it['title'])[:40]}.md"
        rows.append(
            f"<tr><td>{it.get('date','')}</td>"
            f"<td><a href=\"{rel}\" target=\"_blank\">{it['title']}</a></td>"
            f"<td>{it.get('source','')}</td>"
            f"<td>{', '.join(it.get('tags') or [])}</td></tr>"
        )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>知妖词条离线存档</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;margin:2rem;background:#faf8f5;color:#2e2a26}}
h1{{color:#1f3a5f}}
table{{border-collapse:collapse;width:100%;background:#fff}}
th,td{{border:1px solid #ddd;padding:.55rem .7rem;text-align:left;vertical-align:top}}
th{{background:#1f3a5f;color:#fff;position:sticky;top:0}}
tr:nth-child(even){{background:#f7f4ef}}
a{{color:#1f3a5f;text-decoration:none}}
a:hover{{text-decoration:underline}}
.meta{{color:#666;margin-bottom:1rem}}
input{{padding:.5rem .8rem;width:min(420px,90%);margin-bottom:1rem;border:1px solid #ccc;border-radius:4px}}
</style></head><body>
<h1>知妖词条离线存档</h1>
<p class="meta">共 {len(items)} 条 · 来源 <a href="https://www.czhiyao.com/ct">https://www.czhiyao.com/ct</a> · 仅供个人离线阅读</p>
<input id="q" placeholder="搜索标题 / 来源 / 标签…" oninput="filter()">
<table id="t"><thead><tr><th>日期</th><th>标题</th><th>来源</th><th>标签</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table>
<script>
function filter(){{
  const q=document.getElementById('q').value.toLowerCase();
  const rows=document.querySelectorAll('#t tbody tr');
  rows.forEach(r=>{{ r.style.display=r.innerText.toLowerCase().includes(q)?'':'none'; }});
}}
</script></body></html>"""
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"[index] {len(items)} items -> {ROOT / 'index.html'}", flush=True)


def safe_name(title: str, pid: str) -> str:
    t = re.sub(r"[\\/:*?\"<>|\s]+", "_", title).strip("_")[:40]
    return f"{pid}_{t}.md" if t else f"{pid}.md"


def main():
    ensure_dirs()
    urls_file = META / "urls.json"
    if urls_file.exists():
        urls = json.loads(urls_file.read_text(encoding="utf-8"))
        print(f"[urls] loaded cached {len(urls)}", flush=True)
    else:
        urls = collect_urls()

    prog = load_progress()
    done = set(prog["done"])
    items_path = META / "index.json"
    items = json.loads(items_path.read_text(encoding="utf-8")) if items_path.exists() else []
    have_ids = {it["id"] for it in items}

    pending = [u for u in urls if u not in done]
    print(f"[plan] total={len(urls)} done={len(done)} pending={len(pending)}", flush=True)

    for i, url in enumerate(pending, 1):
        pid = re.search(r"/(\d+)\.html", url)
        pid = pid.group(1) if pid else str(i)
        if pid in have_ids and url in done:
            continue
        try:
            raw = get_text(url)
            item = parse_article(url, raw)
            md = to_markdown(item)
            fname = safe_name(item["title"], item["id"] or pid)
            (POSTS / fname).write_text(md, encoding="utf-8")
            # 更新 items
            items = [x for x in items if x.get("id") != item["id"]]
            items.append(item)
            have_ids.add(item["id"])
            prog["done"].append(url)
            if i % 20 == 0 or i <= 5:
                save_progress(prog)
                items_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[{i}/{len(pending)}] {item['title'][:30]}", flush=True)
        except Exception as e:
            prog["failed"].append({"url": url, "error": str(e)[:200]})
            print(f"[fail] {url}: {e}", flush=True)
        time.sleep(DELAY)

    save_progress(prog)
    items_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    build_index(items)
    print(f"[done] saved={len(items)} failed={len(prog['failed'])}", flush=True)


if __name__ == "__main__":
    main()
