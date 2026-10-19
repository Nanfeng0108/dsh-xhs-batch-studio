"""第二步：用选中的选题 + 写作模板生成文案，并按版式模板出图。

用法：
  python -m xhs.build --run <运行目录> [--topics 选中的选题.json] \
      --writing listicle --cover poster --card index --cards 4

运行目录里需要有：topics.json、data/（资料）、可选 meta.json。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from . import compliance, generate, render, writing
from .config import PALETTES, load_config


def log(message: str = "") -> None:
    print(message, flush=True)


def slug(title: str, index: int) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "", title)[:20].rstrip("，。、｜|·-") or "note"
    return f"{index:03d}-{cleaned}"


def caption_text(note: dict) -> str:
    parts = [note["title"], "", note["hook"]]
    for index, section in enumerate(note["sections"]):
        parts.append("")
        if section["heading"]:
            parts.append(section["heading"])
        parts.extend(section["lines"])
    if note.get("cta"):
        parts += ["", note["cta"]]
    if note.get("tags"):
        parts += ["", " ".join(f"#{tag}" for tag in note["tags"])]
    return "\n".join(parts).strip()


def page_count(note: dict) -> int:
    """封面 + 要点卡 + 金句页(有 hook 才有) + 尾页。"""
    quote = 1 if len((note.get("hook") or "").strip()) >= 8 else 0
    return 2 + len(note["cards"]) + quote


def note_md(note: dict, meta: dict) -> str:
    parts = [f"# {note['title']}", "", f"> 题材：{meta.get('topic_title', '')}　来源：{meta.get('source', '')}", ""]
    parts.append(caption_text(note))
    parts += ["", "---", "## 封面",
              f"- 标签：{note['cover']['kicker']}",
              f"- 主标题：{note['cover']['title'].replace(chr(10), ' / ')}",
              f"- 副标题：{note['cover']['subtitle']}", "", "## 内页"]
    for index, card in enumerate(note["cards"], 1):
        parts.append(f"{index}. **{card['title']}**")
        parts += [f"   - {line}" for line in card["lines"]]
    if len((note.get("hook") or "").strip()) >= 8:
        parts += ["", "## 金句页", f"> {note['hook']}"]
    if note.get("cta"):
        parts += ["", "## 尾页", f"- 行动引导：{note['cta']}",
                  f"- 话题标签：{' '.join('#' + tag for tag in note.get('tags', [])[:6])}"]
    if meta.get("issues"):
        parts += ["", "## 合规提示"] + [f"- [{item['level']}] {item['kind']}：{item['word']}" for item in meta["issues"]]
    if meta.get("fixed"):
        parts += ["", "> 已对违禁表达做过最小改写，发布前建议复核。"]
    if meta.get("layout"):
        parts += ["", "## 排版提示"] + [f"- {item}" for item in meta["layout"]]
    return "\n".join(parts)


def write_index(notes: list[dict], metas: list[dict], out_dir: Path, template_name: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "笔记清单"
    headers = ["序号", "标题", "目录", "图片数", "话题标签", "来源", "正文字数", "模板", "合规", "状态"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="E8543F")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for index, (note, meta) in enumerate(zip(notes, metas), 1):
        sheet.append([
            index, note["title"], meta["dir"], page_count(note),
            " ".join("#" + tag for tag in note["tags"]), meta.get("source", ""),
            meta.get("chars", 0), template_name,
            "有告警" if meta.get("issues") else "通过",
            "文字溢出" if meta.get("layout") else "已生成",
        ])
    for index, width in enumerate([6, 40, 30, 8, 44, 18, 10, 12, 10, 10], 1):
        sheet.column_dimensions[chr(64 + index)].width = width
    sheet.freeze_panes = "A2"
    workbook.save(out_dir / "index.xlsx")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser("xhs.build", description="选题 → 文案 → 模板化配图")
    parser.add_argument("--run", required=True, help="运行目录（analyze 的输出）")
    parser.add_argument("--topics", default="", help="选中的选题 JSON，缺省用运行目录的 topics.json")
    parser.add_argument("--count", type=int, default=0, help="最多生成几篇，0 = 全部")
    parser.add_argument("--writing", default=writing.DEFAULT_ID, help="写作模板 id")
    parser.add_argument("--cover", default="poster", choices=list(writing.LAYOUT_COVERS))
    parser.add_argument("--card", default="index", choices=list(writing.LAYOUT_CARDS))
    parser.add_argument("--cards", type=int, default=4, help="内页图数量")
    parser.add_argument("--signature", default="", help="图片上的署名，可留空")
    parser.add_argument("--palette", default="warm", choices=list(PALETTES))
    parser.add_argument("--accent-range", default="narrow", choices=("narrow", "wide"),
                        help="强调色轮换范围：narrow 同族（默认）/ wide 跨色相")
    parser.add_argument("--templates-dir", default="")
    parser.add_argument("--no-fix", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args(argv)

    run_dir = Path(args.run).expanduser().resolve()
    if not run_dir.exists():
        log(f"× 运行目录不存在：{run_dir}")
        return 2
    topics_file = Path(args.topics).expanduser() if args.topics else run_dir / "topics.json"
    if not topics_file.exists():
        log(f"× 找不到选题文件：{topics_file}")
        return 2
    topics = json.loads(topics_file.read_text(encoding="utf-8"))
    if args.count > 0:
        topics = topics[: args.count]
    if not topics:
        log("× 没有选中的选题")
        return 2

    templates_dir = Path(args.templates_dir).expanduser() if args.templates_dir else None
    template = writing.get(args.writing, templates_dir)

    cfg = load_config(model=args.model, concurrency=args.concurrency,
                      cards=args.cards, signature=args.signature)
    started = time.time()

    log(f"选题：{len(topics)} 个　写作模板：{template['name']}")
    accent_note = "同族轮换" if args.accent_range == "narrow" else "跨色相轮换"
    log(f"版式：封面 {args.cover}(含 2 变体) / 内页 {args.card} × {args.cards} + 金句 + 尾页　配色 {args.palette}（强调色 {accent_note}）\n")

    log("[1/4] 写文案")
    write_cfg = dict(cfg)
    write_cfg["cards"] = args.cards
    notes = generate.write_notes(topics, write_cfg, template, log)
    if not notes:
        log("× 文案全部生成失败")
        return 3
    log(f"  完成 {len(notes)} 篇")

    log("\n[2/4] 合规检查与查重")
    metas = []
    for note in notes:
        issues = compliance.scan(compliance.note_fields(note))
        fixed = False
        if issues and not args.no_fix:
            better = generate.fix_note(note, issues, write_cfg, log)
            if better:
                remaining = compliance.scan(compliance.note_fields(better))
                if len(remaining) < len(issues):
                    note = better
                    issues = remaining
                    fixed = True
        caption = caption_text(note)
        if len(caption) > 1000:
            issues.append({"level": "warn", "word": f"{len(caption)}字", "kind": "正文超1000字"})
        if len(note["title"]) > 20:
            issues.append({"level": "warn", "word": f"{len(note['title'])}字", "kind": "标题超20字"})
        metas.append({"issues": issues, "fixed": fixed, "chars": len(caption)})
        if issues:
            log(f"  · 《{note['title'][:14]}》{len(issues)} 条提示：" +
                "，".join(f"{item['word']}({item['kind']})" for item in issues[:4]))
        elif fixed:
            log(f"  · 《{note['title'][:14]}》已自动改写违禁表达")

    duplicates = generate.find_duplicates(notes)
    for left, right, score in duplicates:
        metas[left]["dup"] = f"与#{right + 1}相似{score}"
        metas[right]["dup"] = f"与#{left + 1}相似{score}"
        log(f"  ! 第{left + 1}篇与第{right + 1}篇相似度 {score}")
    if not duplicates:
        log("  未发现明显重复")

    (run_dir / "notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")

    log("\n[3/4] 按模板渲染图片")
    palette = PALETTES[args.palette]
    signature = args.signature.strip()
    # 重跑时清掉上一轮生成的笔记目录，避免同名残留
    for stale in run_dir.iterdir():
        if stale.is_dir() and re.match(r"^\d{3}-", stale.name):
            import shutil
            shutil.rmtree(stale, ignore_errors=True)
    rendered = 0
    with render.Renderer(palette, cover_style=args.cover, card_style=args.card,
                     accent_range=args.accent_range) as renderer:
        for index, note in enumerate(notes):
            folder = run_dir / slug(note["title"], index + 1)
            folder.mkdir(parents=True, exist_ok=True)
            before = len(renderer.warnings)
            try:
                files = render.render_note(renderer, note, folder, signature)
                rendered += 1
                log(f"  · {folder.name}: {len(files)} 张")
            except Exception as error:  # 单篇失败不阻断整批
                log(f"  ! {folder.name} 渲染失败：{error}")
            metas[index]["layout"] = renderer.warnings[before:]
            for warning in metas[index]["layout"]:
                log(f"    ! 排版：{warning}")

    log("\n[4/4] 写文件与索引表")
    layout_warnings: list[str] = []
    for index, note in enumerate(notes):
        folder = run_dir / slug(note["title"], index + 1)
        folder.mkdir(parents=True, exist_ok=True)
        meta = {
            "topic_title": (note.get("topic") or {}).get("title", ""),
            "source": (note.get("topic") or {}).get("source", ""),
            "issues": metas[index]["issues"],
            "fixed": metas[index]["fixed"],
            "chars": metas[index]["chars"],
            "layout": metas[index].get("layout", []),
        }
        layout_warnings.extend(meta["layout"])
        (folder / "note.md").write_text(note_md(note, meta), encoding="utf-8")
        (folder / "caption.txt").write_text(caption_text(note), encoding="utf-8")
        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        metas[index]["dir"] = folder.name
        metas[index]["source"] = meta["source"]

    write_index(notes, metas, run_dir, template["name"])
    if layout_warnings:
        (run_dir / "layout-warnings.json").write_text(
            json.dumps(layout_warnings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": len(notes),
        "images": rendered,
        "issues": sum(1 for meta in metas if meta["issues"]),
        "dups": len(duplicates),
        "layout_warnings": len(layout_warnings),
        "template": {"writing": template["name"], "cover": args.cover, "card": args.card, "palette": args.palette,
                     "pages": ["cover", "card", "quote", "closing"],
                     "accent_range": args.accent_range},
        "elapsed_sec": round(time.time() - started, 1),
    }
    (run_dir / "run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n完成：{len(notes)} 篇 / {report['elapsed_sec']}s")
    log(json.dumps({"ok": True, "notes": len(notes), "out": str(run_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
