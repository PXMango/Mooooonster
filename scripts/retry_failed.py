# -*- coding: utf-8 -*-
"""补抓超时失败的词条，并重建索引。"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\cdzn-cs\XiaomiMiMoProjects\.mimo-sessions\2026\10\15\new-chat-2")
from archive_zhiyao import DELAY, build_index, get_text, parse_article, safe_name, to_markdown

ROOT = Path(r"C:\Users\cdzn-cs\XiaomiMiMoProjects\.mimo-sessions\2026\10\15\new-chat-2\zhiyao_archive")
POSTS, META = ROOT / "posts", ROOT / "meta"

prog = json.loads((META / "progress.json").read_text(encoding="utf-8"))
items = json.loads((META / "index.json").read_text(encoding="utf-8"))
failed = list(prog.get("failed") or [])
still = []
for f in failed:
    url = f["url"]
    try:
        raw = get_text(url)
        item = parse_article(url, raw)
        md = to_markdown(item)
        fname = safe_name(item["title"], item["id"])
        (POSTS / fname).write_text(md, encoding="utf-8")
        items = [x for x in items if x.get("id") != item["id"]]
        items.append(item)
        prog["done"].append(url)
        print("OK", item["title"])
    except Exception as e:
        still.append({"url": url, "error": str(e)[:200]})
        print("FAIL", url, e)
    time.sleep(DELAY)

prog["failed"] = still
(META / "progress.json").write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")
(META / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
build_index(items)
print("retry_done remaining_fail", len(still), "items", len(items))
