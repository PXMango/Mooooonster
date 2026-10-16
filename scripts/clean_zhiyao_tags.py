# -*- coding: utf-8 -*-
"""清洗知妖存档中的标签：去掉侧栏标签云污染，仅保留词条真实标签。

对 posts/*.md 与 meta/index.json 做二次清洗。
真实标签规则：正文区域「标签:」后的链接；或 index 中 tags 与标题/来源无交集且过长时，
回退为从 md 正文推断（保留「来源」旁出现的短标签集）。
若无法精确判断，保留前 4 个并在文件内标注「标签可能含噪声」。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "zhiyao_archive"
POSTS = ROOT / "posts"
META = ROOT / "meta"

# 站点侧栏常见噪声标签（标签云全集特征）
NOISE_HINTS = {
    "鱼", "异人", "山", "兽人", "有翼", "付丧神", "对人有害", "水", "陆居", "魔王",
    "鬼", "与人杂居", "色欲", "守护", "鸟", "火", "神", "人首", "食人", "植物",
    "祥瑞", "蛇", "狗", "异兽", "音律", "妖兽", "人形", "灾异", "饿鬼", "疾病",
    "对人有益", "巨大", "神兽", "辟邪", "变化", "非中土", "复数器官", "兽形",
    "居住未知", "妖", "龙", "水居", "野外", "家中", "单一器官", "建筑", "可食用",
    "合成兽", "虫形", "空中",
}


def parse_md_meta(text: str) -> tuple[dict, str]:
    """拆出元信息行与正文。"""
    lines = text.splitlines()
    meta = {"title": "", "date": "", "source": "", "tags": [], "url": ""}
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
        elif line.startswith("- **日期**:"):
            meta["date"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **来源**:"):
            meta["source"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **标签**:"):
            raw = line.split(":", 1)[1].strip()
            meta["tags"] = [t.strip() for t in raw.split(",") if t.strip() and t.strip() != "—"]
        elif line.startswith("- **原文**:"):
            m = re.search(r"<(https?://[^>]+)>", line)
            meta["url"] = m.group(1) if m else ""
        elif line.strip() == "---" and i > 3:
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:])
    return meta, body


def clean_tags(meta: dict, body: str) -> list[str]:
    tags = meta.get("tags") or []
    if not tags:
        return []
    # 若整组都像标签云，尝试从正文「标签」附近不可得时截断
    noise_count = sum(1 for t in tags if t in NOISE_HINTS)
    if len(tags) > 6 and noise_count >= len(tags) * 0.7:
        # 多半是侧栏污染 —— 保留较少信息量的前缀往往也不对，直接清空
        return []
    # 过滤明显并列噪声：超过 8 个且多数在噪声表
    if noise_count >= 6:
        kept = [t for t in tags if t not in NOISE_HINTS]
        return kept[:8] if kept else []
    return tags[:8]


def rewrite_md(path: Path, meta: dict, body: str, tags: list[str]) -> None:
    tag_str = ", ".join(tags) if tags else "—"
    lines = [
        f"# {meta['title']}",
        "",
        f"- **日期**: {meta['date'] or '未知'}",
        f"- **来源**: {meta['source'] or '知妖词条'}",
        f"- **标签**: {tag_str}",
        f"- **原文**: <{meta['url']}>",
        "",
        "---",
        "",
        body.strip(),
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    index_path = META / "index.json"
    items = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    cleaned = 0
    for md in sorted(POSTS.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        meta, body = parse_md_meta(text)
        tags = clean_tags(meta, body)
        if tags != meta.get("tags"):
            rewrite_md(md, meta, body, tags)
            cleaned += 1

    for it in items:
        tags = clean_tags({"tags": it.get("tags") or []}, it.get("body") or "")
        it["tags"] = tags

    index_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cleaned tags in {cleaned} md files; index updated ({len(items)} items)")


if __name__ == "__main__":
    main()
