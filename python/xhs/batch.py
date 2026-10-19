"""批量出图：一份资料包 → N 套笔记（每套 6 张图 + 文案），并打包。"""
from __future__ import annotations

import argparse
import warnings
import json
import sys
import zipfile
from pathlib import Path

from . import pack, planner


def run(data_dir: Path, out_dir: Path, count: int) -> dict:
    sheets = pack.parse_pack(data_dir)
    if not sheets:
        raise SystemExit("没解析到可用的表格")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "notes").mkdir(exist_ok=True)

    print(f"编排 {count} 套方案…", flush=True)
    payload = planner.make_batch(sheets, data_dir, count)
    plans = payload["plans"]
    (out_dir / "plans-batch.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    notes: list[dict] = []
    for index, plan in enumerate(plans):
        title = str(plan.get("title", "")).replace("\n", " / ")
        print(f"[{index + 1}/{len(plans)}] {plan.get('name', '')}｜{title}", flush=True)
        note_dir = out_dir / "notes" / f"{index + 1:02d}"
        cfg = pack.plan_to_cfg(plan, sheets)
        info = pack.render_note(cfg, note_dir, variant=index)
        notes.append({
            "id": f"{index + 1:02d}",
            "name": plan.get("name", ""),
            "title": plan.get("title", ""),
            "audience": plan.get("audience", ""),
            "keyword": plan.get("keyword", ""),
            "caption": info["caption"],
            "images": [f"notes/{index + 1:02d}/{name}" for name in info["images"]],
        })

    manifest = {
        "count": len(notes),
        "fallback": payload.get("fallback", False),
        "notes": notes,
        "zip": "batch.zip",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    with zipfile.ZipFile(out_dir / "batch.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file() and path.name != "batch.zip" and not path.name.startswith("."):
                bundle.write(path, path.relative_to(out_dir))
    print(f"完成：{len(notes)} 条，{out_dir / 'batch.zip'}", flush=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser("xhs.batch", description="资料包 → 批量笔记")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args(argv)
    try:
        run(Path(args.data).expanduser().resolve(), Path(args.out).expanduser().resolve(), args.count)
    except SystemExit as error:
        print(f"× {error}", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
