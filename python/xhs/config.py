"""集中配置：路径、模型、配色、画布规格。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "out"
TEMPLATES_DIR = PKG_DIR / "templates"
FONTS_DIR = PKG_DIR / "fonts"
BIN_DIR = PKG_DIR / "bin"

# 小红书竖版 3:4，导出 1080x1440（CSS 540x720 @2x）
CANVAS_W = 540
CANVAS_H = 720
SCALE = 2

DEFAULT_MODEL = "deepseek-flash"
OUTLINE_MODEL = "deepseek-flash"

# 配色是版式模板的参数，不是“风格抽卡”：同一模板 + 同一配色 = 完全一致的版式
# accents：同一配色族内的强调色轮换池。每篇按标题哈希取一个，批内不重样、单篇可复现。
# on_accent：压在强调色上的文字色（以前硬编码 #fff，深色配色下对比度不足）
PALETTES: dict[str, dict] = {
    "warm": {
        "bg": "#FBF7F0", "ink": "#1B1B1B", "muted": "#6B6257",
        "accent": "#E8543F", "accent_soft": "#FBE3DD", "line": "#E4DACB",
        "cover_bg": "#FBF7F0", "cover_ink": "#1B1B1B",
        "on_accent": "#FFFFFF",
        "accents": ["#E8543F", "#D3692F", "#C0422E", "#A65B3A"],
        "accents_wide": ["#E8543F", "#C0422E", "#3E6E8C", "#5C6B3C", "#A65B3A", "#8A5A7A"],
    },
    "ink": {
        "bg": "#101418", "ink": "#F4F0E8", "muted": "#9AA3A8",
        "accent": "#C9A227", "accent_soft": "#2A2415", "line": "#2A3036",
        "cover_bg": "#101418", "cover_ink": "#F4F0E8",
        "on_accent": "#16130A",
        "accents": ["#C9A227", "#D9B65E", "#A88B4A", "#B8892E"],
        "accents_wide": ["#C9A227", "#D9B65E", "#7FA6B8", "#9DB07A", "#B8892E", "#C77F86"],
    },
    "mint": {
        "bg": "#F2F8F4", "ink": "#17251F", "muted": "#5F756B",
        "accent": "#1F7A5C", "accent_soft": "#D9EFE4", "line": "#D3E5DA",
        "cover_bg": "#F2F8F4", "cover_ink": "#17251F",
        "on_accent": "#FFFFFF",
        "accents": ["#1F7A5C", "#2C6E63", "#3F7A4A", "#1E6E7A"],
        "accents_wide": ["#1F7A5C", "#1E6E7A", "#4A5D8C", "#B06A3C", "#3F7A4A", "#7A4E6E"],
    },
    "paper": {
        "bg": "#FFFDF8", "ink": "#2A2320", "muted": "#7A6E66",
        "accent": "#D9482F", "accent_soft": "#FBE7D8", "line": "#EADFD3",
        "cover_bg": "#FFFDF8", "cover_ink": "#2A2320",
        "on_accent": "#FFFFFF",
        "accents": ["#D9482F", "#C2703B", "#A8452F", "#8F5B36"],
        "accents_wide": ["#D9482F", "#A8452F", "#3F5E7A", "#6B7A45", "#8F5B36", "#8A5A6E"],
    },
}

DEFAULTS: dict[str, Any] = {
    "model": DEFAULT_MODEL,
    "outline_model": OUTLINE_MODEL,
    "note_count": 8,
    "cards": 4,
    "signature": "",          # 图片上的署名，可留空
    "topic": "",              # 内容方向提示，可为空
    "audience": "25-35 岁女性",
    "concurrency": 4,
    "fix": True,              # 命中违禁词时用模型做最小改写
    "max_chars_per_chunk": 18000,
}


def load_config(**overrides: Any) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    local = ROOT / "xhs.config.json"
    if local.exists():
        cfg.update(json.loads(local.read_text(encoding="utf-8")))
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    return cfg
