"""选题提炼 + 单篇笔记生成 + 去重。"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from typing import Any, Callable

from . import llm, prompts
from .ingest import Doc

Log = Callable[[str], None]


# ------------------------------------------------------------ chunking

def chunk_docs(docs: list[Doc], max_chars: int) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for d in docs:
        head = f"【文件】{d.path.name}"
        if size + len(head) > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(head)
        size += len(head)
        for b in d.blocks:
            piece = f"[{b.loc}] {b.text}"
            if size + len(piece) > max_chars and buf:
                chunks.append("\n\n".join(buf))
                buf, size = [], 0
            # 单块超长时硬切
            while len(piece) > max_chars:
                chunks.append(piece[:max_chars])
                piece = f"[{b.loc}·续] " + piece[max_chars:]
            buf.append(piece)
            size += len(piece)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


# ------------------------------------------------------------ outline

def _norm(s: str) -> str:
    return re.sub(r"[\s\W_]+", "", s or "")


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def extract_topics(docs: list[Doc], cfg: dict, log: Log) -> list[dict]:
    chunks = chunk_docs(docs, int(cfg["max_chars_per_chunk"]))
    log(f"  资料切分为 {len(chunks)} 个片段，开始提炼选题")

    def one(chunk: str) -> list[dict]:
        msg = prompts.outline_user(
            chunk, count=cfg["note_count"],
            topic=cfg.get("topic", ""), audience=cfg["audience"],
        )
        try:
            data = llm.parse_json(llm.chat(
                [{"role": "system", "content": prompts.OUTLINE_SYSTEM},
                 {"role": "user", "content": msg}],
                model=cfg["outline_model"], temperature=0.8, max_tokens=6000,
            ))
            return data.get("topics", [])
        except Exception as e:
            log(f"  ! 片段选题失败: {e}")
            return []

    topics: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(4, len(chunks) or 1)) as pool:
        for got in pool.map(one, chunks):
            for t in got:
                if not t.get("title"):
                    continue
                # 与已有选题去重
                if any(_sim(t["title"], x["title"]) > 0.72 for x in topics):
                    continue
                t.setdefault("key_facts", [])
                topics.append(t)

    topics.sort(key=lambda t: -len(t.get("key_facts", [])))
    need = int(cfg["note_count"])
    if len(topics) < need:
        log(f"  ! 只提炼出 {len(topics)} 个选题（目标 {need}），可增加资料或调小 --count")
    return topics[:need]


# ------------------------------------------------------------ note

def _fit(note: dict, cards: int, topic: dict) -> dict:
    """补齐/裁剪字段，避免渲染时缺字段。"""
    title = (note.get("title") or topic.get("title") or "未命名").strip()
    note["title"] = title[:28]
    note["hook"] = (note.get("hook") or "").strip()
    secs = []
    for s in note.get("sections") or []:
        lines = [str(x).strip() for x in (s.get("lines") or []) if str(x).strip()]
        if s.get("heading") or lines:
            secs.append({"heading": str(s.get("heading") or "").strip(), "lines": lines})
    if not secs and note["hook"]:
        secs = [{"heading": "", "lines": [note["hook"]]}]
    note["sections"] = secs[:6]
    tags = []
    for t in note.get("tags") or []:
        t = str(t).strip().lstrip("#").replace(" ", "")
        if t and t not in tags:
            tags.append(t)
    if len(tags) < 3:
        tags += [x for x in ["成长", "干货分享", "生活记录"] if x not in tags]
    note["tags"] = tags[:8]
    cards_list = []
    for c in note.get("cards") or []:
        lines = [str(x).strip() for x in (c.get("lines") or []) if str(x).strip()]
        if c.get("title") or lines:
            cards_list.append({"title": str(c.get("title") or "").strip(), "lines": lines})
    while len(cards_list) < cards:
        cards_list.append({"title": note["title"][:12], "lines": []})
    note["cards"] = cards_list[:cards]
    cover = note.get("cover") or {}
    note["cover"] = {
        "kicker": str(cover.get("kicker") or "干货合集").strip()[:10],
        "title": str(cover.get("title") or title).strip()[:24],
        "subtitle": str(cover.get("subtitle") or topic.get("angle") or "").strip()[:30],
        "image_prompt": str(cover.get("image_prompt") or "").strip(),
    }
    note["topic"] = topic
    return note


def write_note(topic: dict, cfg: dict, template: dict, log: Log) -> dict | None:
    msg = prompts.note_user(
        topic, template=template, cards=int(cfg["cards"]),
        audience=cfg["audience"], signature=cfg.get("signature", ""),
    )
    last_err = ""
    for attempt in range(3):
        try:
            raw = llm.chat(
                [{"role": "system", "content": prompts.NOTE_SYSTEM},
                 {"role": "user", "content": msg if attempt == 0 else
                  msg + "\n\n注意：只输出 JSON，不要 markdown 代码块。"}],
                model=cfg["model"], temperature=0.9 if attempt == 0 else 0.75,
                max_tokens=6000,
            )
            data = llm.parse_json(raw)
            if not data.get("title"):
                raise ValueError("缺少 title")
            return _fit(data, int(cfg["cards"]), topic)
        except Exception as e:
            last_err = str(e)[:200]
            log(f"  ! 重试选题《{topic.get('title','')[:12]}》: {last_err}")
    log(f"  × 放弃选题《{topic.get('title','')[:12]}》: {last_err}")
    return None


def write_notes(topics: list[dict], cfg: dict, template: dict, log: Log) -> list[dict]:
    with ThreadPoolExecutor(max_workers=int(cfg["concurrency"])) as pool:
        results = list(pool.map(lambda item: write_note(item, cfg, template, log), topics))
    return [note for note in results if note]


# ------------------------------------------------------------ dedupe

def note_text(note: dict) -> str:
    parts = [note.get("hook", "")]
    for s in note["sections"]:
        parts.append(s["heading"])
        parts.extend(s["lines"])
    return "\n".join(parts)


def find_duplicates(notes: list[dict], thresh: float = 0.6) -> list[tuple[int, int, float]]:
    hits = []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            s_body = SequenceMatcher(None, _norm(note_text(notes[i])), _norm(note_text(notes[j]))).ratio()
            s_title = SequenceMatcher(None, _norm(notes[i]["title"]), _norm(notes[j]["title"])).ratio()
            score = max(s_body, s_title)
            if score >= thresh:
                hits.append((i, j, round(score, 2)))
    return hits


def fix_note(note: dict, issues: list[dict], cfg: dict, log: Log) -> dict | None:
    """让模型做最小改写，去掉违禁/极限表达；失败返回 None。"""
    words = sorted({i["word"] for i in issues if i.get("word")})
    if not words:
        return None
    try:
        raw = llm.chat(
            [{"role": "system", "content": prompts.FIX_SYSTEM},
             {"role": "user", "content": prompts.fix_user(note, words)}],
            model=cfg["model"], temperature=0.3, max_tokens=5000,
        )
        data = llm.parse_json(raw)
        if not data.get("title"):
            return None
        data.setdefault("topic", note.get("topic"))
        return _fit(data, len(note["cards"]), note.get("topic") or {})
    except Exception as e:
        log(f"  ! 违禁表达改写失败：{str(e)[:100]}")
        return None
