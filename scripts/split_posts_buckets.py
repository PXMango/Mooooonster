# -*- coding: utf-8 -*-
"""将 posts/*.md 按 ID 百段拆入子目录，并重建索引链接。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\cdzn-cs\XiaomiMiMoProjects\zhiyao-archive")
POSTS = ROOT / "posts"
META = ROOT / "meta"


def parse_id(name: str) -> int | None:
    m = re.match(r"^(\d+)_", name)
    return int(m.group(1)) if m else None


def bucket_of(pid: int) -> str:
    start = (pid // 100) * 100
    end = start + 99
    return f"{start:04d}-{end:04d}"


def main():
    files = sorted(POSTS.glob("*.md"))
    print(f"flat md files: {len(files)}")

    # 移动到子目录
    mapping = {}  # filename -> relative path under repo
    for f in files:
        pid = parse_id(f.name)
        if pid is None:
            bucket = "misc"
        else:
            bucket = bucket_of(pid)
        dest_dir = POSTS / bucket
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / f.name
        shutil.move(str(f), str(dest))
        mapping[f.name] = f"posts/{bucket}/{f.name}"

    # 校验：根目录不应再有 .md
    leftover = list(POSTS.glob("*.md"))
    print(f"moved={len(mapping)} leftover={len(leftover)}")
    buckets = sorted([p.name for p in POSTS.iterdir() if p.is_dir()])
    print(f"buckets={len(buckets)} e.g. {buckets[:5]} ... {buckets[-3:]}")

    # 更新 index.json
    index_path = META / "index.json"
    items = json.loads(index_path.read_text(encoding="utf-8"))
    for it in items:
        # 根据 id 找文件名
        pid = it.get("id") or ""
        # 文件名在 mapping 里以 <id>_title.md 形式
        # 用 id 前缀匹配
        rel = None
        for fname, rpath in mapping.items():
            if fname.startswith(f"{pid}_") or fname == f"{pid}.md":
                rel = rpath
                break
        if rel is None:
            # 尝试 exact
            for fname, rpath in mapping.items():
                if parse_id(fname) == int(pid) if pid.isdigit() else False:
                    rel = rpath
                    break
        it["path"] = rel or ""
    index_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    # 重建 index.html
    rows = []
    for it in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        rel = it.get("path") or ""
        if not rel:
            continue
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
.buckets{{margin:1rem 0;font-size:.92rem}}
.buckets a{{margin-right:.6rem}}
</style></head><body>
<h1>知妖词条离线存档</h1>
<p class="meta">共 {len(rows)} 条 · 每目录约 100 条 · 来源 <a href="https://www.czhiyao.com/ct">https://www.czhiyao.com/ct</a> · 仅供个人离线阅读</p>
<div class="buckets">按编号段浏览：
{''.join(f'<a href="posts/{b}/">{b}</a>' for b in buckets if b != 'misc')}
</div>
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
    print(f"index rebuilt: {len(rows)} rows, {len(buckets)} buckets")


if __name__ == "__main__":
    main()
