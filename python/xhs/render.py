"""HTML → PNG 渲染（Playwright Chromium）。

版式来自固定模板文件，不再依赖 AI 生成图片：
  封面：cover-poster / cover-magazine / cover-note
  内页：card-index / card-timeline
  节奏页：card-quote（金句）/ closing（尾页）
同一模板 + 同一配色 + 同一内容，输出完全一致。

变化不靠随机数：强调色和封面变体都由标题哈希决定，
所以「同一篇永远同一张图」和「批内不重样」可以同时成立。
"""
from __future__ import annotations

import html as htmlmod
import re
import zlib
from pathlib import Path

from .config import CANVAS_H, CANVAS_W, FONTS_DIR, SCALE, TEMPLATES_DIR
from .icons import icon_for

_TPL: dict[str, str] = {}
_FONT_CSS: str = ""
COVER_VARIANTS = ("a", "b")

# 字体包在仓库里，本地 file:// 读取：同一份字体 → 任何机器上排版一致。
# 顺序即优先级：西文/数字先命中 XHS Num，中文回落 XHS Sans。
FONT_FACES: list[tuple[str, str, int]] = [
    ("XHS Num", "archivo-600.woff2", 600),
    ("XHS Num", "archivo-800.woff2", 800),
    ("XHS Sans", "noto-400.woff2", 400),
    ("XHS Sans", "noto-700.woff2", 700),
    ("XHS Sans", "noto-900.woff2", 900),
]

# 文字溢出保护：版式全部用 rem，所以整体缩放根字号即可等比缩小文字。
# 只检查叶子文本节点，装饰性图形（大圆、色块）故意出界，不能算溢出。
AUTOFIT_JS = """
({w, h}) => {
  const root = document.documentElement;
  const base = parseFloat(getComputedStyle(root).fontSize) || 16;
  const leaves = () => [...document.querySelectorAll("body *")]
    .filter((el) => el.children.length === 0 && el.textContent.trim().length > 0);
  const spill = () => leaves().filter((el) => {
    // 绝对定位元素是刻意的出血装饰（旋转标签、大圆），不算溢出
    const position = getComputedStyle(el).position;
    if (position === "absolute" || position === "fixed") return false;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    return r.bottom > h + 0.5 || r.top < -0.5 || r.right > w + 0.5 || r.left < -0.5;
  });
  let guard = 0;
  while (spill().length && guard++ < 18) {
    const size = parseFloat(getComputedStyle(root).fontSize) - 0.35;
    if (size < base * 0.84) break;
    root.style.fontSize = size + "px";
  }
  const left = spill();
  const now = parseFloat(getComputedStyle(root).fontSize);
  const out = [];
  if (left.length) {
    const sample = left.slice(0, 3).map((el) => el.textContent.trim().slice(0, 12)).join(" / ");
    out.push(`文字溢出 ${left.length} 处：${sample}`);
  } else if (now < base - 0.01) {
    out.push(`已自动缩字至 ${Math.round((now / base) * 100)}%`);
  }
  return out;
}
"""


def font_css() -> str:
    """生成 @font-face 样式。字体缺失时静默跳过，回落系统字体。"""
    global _FONT_CSS
    if _FONT_CSS:
        return _FONT_CSS
    rules = []
    for family, filename, weight in FONT_FACES:
        path = FONTS_DIR / filename
        if not path.exists():
            continue
        rules.append(
            f'@font-face{{font-family:"{family}";src:url("{path.as_uri()}") format("woff2");'
            f"font-weight:{weight};font-style:normal;font-display:block}}"
        )
    _FONT_CSS = "<style>" + "".join(rules) + "</style>" if rules else ""
    return _FONT_CSS


def font_stack() -> str:
    """CSS font-family 值：西文数字 → 中文字体 → 系统兜底。"""
    return '"XHS Num","XHS Sans","PingFang SC","Heiti SC",-apple-system,sans-serif'



def _tpl(name: str) -> str:
    if name not in _TPL:
        _TPL[name] = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    return _TPL[name]


def esc(text: str) -> str:
    return htmlmod.escape(str(text or ""), quote=False)


def highlight(text: str) -> str:
    """**关键词** → 高亮。"""
    value = esc(text)
    return re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', value)


def note_seed(note: dict) -> int:
    """标题哈希。同一篇恒定，不同篇分散——确定性变化的唯一来源。"""
    return zlib.crc32(str(note.get("title", "")).encode("utf-8"))


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def mix(color: str, base: str, ratio: float) -> str:
    """把 color 按 ratio 混进 base。用于从强调色推导浅底色，保证同族同调。"""
    a, b = _rgb(color), _rgb(base)
    parts = [round(x * ratio + y * (1 - ratio)) for x, y in zip(a, b)]
    return "#{:02X}{:02X}{:02X}".format(*parts)


class Renderer:
    def __init__(self, palette: dict, cover_style: str = "poster", card_style: str = "index",
                 accent_range: str = "narrow"):
        self.p = palette
        self.accent_range = "wide" if accent_range == "wide" else "narrow"
        self.cover_style = cover_style if cover_style in ("poster", "magazine", "note") else "poster"
        self.card_style = card_style if card_style in ("index", "timeline") else "index"
        self._pw = None
        self._browser = None
        self.warnings: list[str] = []

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            args=["--font-render-hinting=none", "--allow-file-access-from-files"]
        )
        return self

    def __exit__(self, *exc):
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    # ---------------------------------------------------------------- internals
    def _tokens(self, note: dict | None = None) -> dict[str, str]:
        palette = self.p
        key = "accents_wide" if self.accent_range == "wide" else "accents"
        accents = palette.get(key) or palette.get("accents") or [palette["accent"]]
        # 每篇一个强调色：同族轮换，不跳色系，保证家族感
        accent = accents[note_seed(note) % len(accents)] if note else palette["accent"]
        seed = note_seed(note) if note else 0
        variant = COVER_VARIANTS[seed % len(COVER_VARIANTS)]
        card_variant = COVER_VARIANTS[(seed // 7) % len(COVER_VARIANTS)]
        return {
            "WIDTH": str(CANVAS_W), "HEIGHT": str(CANVAS_H),
            "BG": palette["bg"], "INK": palette["ink"], "MUTED": palette["muted"],
            "ACCENT": accent,
            # 浅底色由强调色推导，避免新增配色时忘记补 token
            "ACCENT_SOFT": mix(accent, palette["bg"], 0.16),
            "SURFACE": mix(palette["ink"], palette["bg"], 0.05),
            "ON_ACCENT": palette.get("on_accent", "#FFFFFF"),
            "LINE": palette["line"],
            "VARIANT": variant,
            "CARD_VARIANT": card_variant,
            "FONT_STACK": font_stack(),
        }

    def _points(self, note: dict) -> str:
        headings = [section.get("heading", "") for section in note.get("sections", []) if section.get("heading")]
        if not headings:
            return ""
        items = "".join(
            f'<div><i>{index + 1:02d}</i><span>{esc(text)}</span></div>'
            for index, text in enumerate(headings[:3])
        )
        return f'<div class="points">{items}</div>'

    def _signature(self, signature: str) -> str:
        return esc(signature) if signature else ""

    def _shoot(self, html: str, out_path: Path):
        fonts = font_css()
        if fonts:
            html = html.replace("</head>", fonts + "</head>", 1)
        page = self._browser.new_page(
            viewport={"width": CANVAS_W, "height": CANVAS_H},
            device_scale_factor=SCALE,
        )
        try:
            tmp = out_path.parent / f".render-{out_path.stem}.html"
            tmp.write_text(html, encoding="utf-8")
            page.goto(tmp.as_uri(), wait_until="load")
            page.evaluate(
                """async () => {
                    const faces = [
                        '400 16px "XHS Sans"', '700 16px "XHS Sans"', '900 16px "XHS Sans"',
                        '600 16px "XHS Num"', '800 16px "XHS Num"',
                    ];
                    await Promise.all(faces.map((f) => document.fonts.load(f).catch(() => null)));
                    await document.fonts.ready;
                }"""
            )
            for warning in page.evaluate(AUTOFIT_JS, {"w": CANVAS_W, "h": CANVAS_H}) or []:
                self.warnings.append(f"{out_path.name}: {warning}")
            page.wait_for_timeout(120)
            page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": CANVAS_W, "height": CANVAS_H})
            tmp.unlink(missing_ok=True)
        finally:
            page.close()

    @staticmethod
    def _marker(row: str) -> str:
        """命中小图标就画图标，否则退回圆点。"""
        icon = icon_for(row)
        return f'<span class="ico">{icon}</span>' if icon else '<span class="dot"></span>'

    # ---------------------------------------------------------------- pages
    def cover(self, note: dict, out_path: Path, signature: str, total_pages: int):
        tokens = self._tokens(note)
        tokens.update({
            "KICKER": esc(note["cover"]["kicker"]),
            "TITLE": esc(note["cover"]["title"]),
            "SUBTITLE": highlight(note["cover"]["subtitle"]),
            "SIGNATURE_BLOCK": self._signature(signature),
            "PAGE_LABEL": f"01 / {total_pages:02d}",
            "COVER_META": f"{len(note.get('sections', []))} 个要点 · {total_pages} 张图",
            "COVER_POINTS": self._points(note),
        })
        html = _tpl(f"cover-{self.cover_style}.html")
        for key, value in tokens.items():
            html = html.replace("{{" + key + "}}", value)
        self._shoot(html, out_path)

    def card(self, note: dict, index: int, page: int, total: int, out_path: Path, signature: str):
        card = note["cards"][index]
        rows = card["lines"] or [""]
        if self.card_style == "timeline":
            body = "\n".join(
                f'<div class="item"><span class="tx">{highlight(row)}</span></div>' for row in rows
            )
        else:
            body = "\n".join(
                f'<div class="line">{self._marker(row)}<span class="tx">{highlight(row)}</span></div>'
                for row in rows
            )
        tokens = self._tokens(note)
        tokens.update({
            "NO": f"{index + 1:02d}",
            "LABEL": "步骤" if self.card_style == "timeline" else "要点",
            "STAMP": "收藏再看",
            "TITLE": highlight(card["title"]),
            "LINES": body,
            "SIGNATURE_BLOCK": self._signature(signature),
            "PAGE": f"{page} / {total}",
        })
        html = _tpl(f"card-{self.card_style}.html")
        for key, value in tokens.items():
            html = html.replace("{{" + key + "}}", value)
        self._shoot(html, out_path)

    def quote(self, note: dict, page: int, total: int, out_path: Path, signature: str):
        """金句页：打破要点卡的重复节奏，给整组图一个呼吸点。"""
        tokens = self._tokens(note)
        tokens.update({
            "QUOTE": highlight(note.get("hook", "")),
            "FROM": esc(note["cover"]["title"]),
            "SIGNATURE_BLOCK": self._signature(signature),
            "PAGE": f"{page} / {total}",
        })
        html = _tpl("card-quote.html")
        for key, value in tokens.items():
            html = html.replace("{{" + key + "}}", value)
        self._shoot(html, out_path)

    def closing(self, note: dict, page: int, total: int, out_path: Path, signature: str):
        """尾页：把 CTA 和话题标签收在一张图上，替代之前没有落点的结尾。"""
        tags = note.get("tags", [])[:6]
        tokens = self._tokens(note)
        tokens.update({
            "TITLE": esc(note["cover"]["title"]),
            "CTA": highlight(note.get("cta", "")),
            "TAGS": "".join(f'<span class="tag">{esc(tag)}</span>' for tag in tags),
            "SIGNATURE_BLOCK": self._signature(signature),
            "PAGE": f"{page} / {total}",
        })
        html = _tpl("closing.html")
        for key, value in tokens.items():
            html = html.replace("{{" + key + "}}", value)
        self._shoot(html, out_path)


def render_note(renderer: Renderer, note: dict, out_dir: Path, signature: str = "") -> list[Path]:
    """按页面角色排版：封面 → 要点卡（中间插一张金句）→ 尾页。

    页数 = 2 + 要点数 (+ 1)，有 hook 才有金句页。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = note["cards"]
    hook = (note.get("hook") or "").strip()
    has_quote = len(hook) >= 8
    total = 2 + len(cards) + (1 if has_quote else 0)

    plan: list[tuple[str, int]] = [("cover", -1)]
    for index in range(len(cards)):
        plan.append(("card", index))
        if has_quote and index == 0:
            plan.append(("quote", -1))
    plan.append(("closing", -1))

    files: list[Path] = []
    for page, (role, index) in enumerate(plan, 1):
        path = out_dir / f"{page:02d}.png"
        if role == "cover":
            renderer.cover(note, path, signature, total)
        elif role == "card":
            renderer.card(note, index, page, total, path, signature)
        elif role == "quote":
            renderer.quote(note, page, total, path, signature)
        else:
            renderer.closing(note, page, total, path, signature)
        files.append(path)
    return files
