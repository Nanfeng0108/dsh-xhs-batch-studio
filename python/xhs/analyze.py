"""第一步：解析资料并提炼选题。

用法：
  python -m xhs.analyze --data <资料目录> --out <运行目录> --count 8 [--topic 方向]

输出：<out>/topics.json、<out>/_ingest/、<out>/meta.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from . import generate, ingest
from .config import DATA_DIR, OUT_DIR, load_config


def log(message: str = "") -> None:
    print(message, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser("xhs.analyze", description="解析资料并提炼选题")
    parser.add_argument("--data", default=str(DATA_DIR))
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=None, help="期望产出的选题数量")
    parser.add_argument("--topic", default=None, help="内容方向提示")
    parser.add_argument("--audience", default=None)
    parser.add_argument("--model", default=None, help="选题模型，默认 deepseek-flash")
    parser.add_argument("--chunk", type=int, default=None, help="单片段字符数上限")
    args = parser.parse_args(argv)

    cfg = load_config(
        note_count=args.count,
        topic=args.topic,
        audience=args.audience,
        outline_model=args.model,
        max_chars_per_chunk=args.chunk,
    )
    data_dir = Path(args.data).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    log(f"资料目录：{data_dir}")
    docs = ingest.ingest_all(data_dir, out_dir, log=log)
    total_chars = sum(doc.chars for doc in docs)
    if total_chars < 50:
        log("× 资料内容太少，无法提炼选题")
        return 2
    log(f"  共 {len(docs)} 个文件 / {total_chars} 字")

    log("")
    log("提炼选题")
    topics = generate.extract_topics(docs, cfg, log)
    for index, topic in enumerate(topics, 1):
        topic["id"] = topic.get("id") or f"t{index:02d}"
        log(f"  {index:02d}. {topic['title']}  ← {topic.get('source', '')}")

    (out_dir / "topics.json").write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(data_dir),
        "files": [{"name": doc.path.name, "kind": doc.kind, "chars": doc.chars, "ocr": doc.ocr_used}
                  for doc in docs],
        "chars": total_chars,
        "topics": len(topics),
        "elapsed": round(time.time() - started, 1),
        "topic_hint": cfg.get("topic", ""),
        "audience": cfg.get("audience", ""),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n完成：{len(topics)} 个选题 / {meta['elapsed']}s")
    log(json.dumps({"ok": True, "topics": len(topics), "out": str(out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
