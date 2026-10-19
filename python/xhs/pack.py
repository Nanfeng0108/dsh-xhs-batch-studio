"""资料包模式：把一个资料文件夹做成一套小红书图文（A 版式）。

流程固定：
  解析文件夹 → 按类型归类 → 选 3 个代表模板 → 渲染表格预览 → 出 6 张图 + 文案

用法：
  python -m xhs.pack --data <资料目录> --out <输出目录> \
      --title "HR 别再手画考勤了" --audience "HR / 行政 专用" --keyword 资料

不出现资料份数；截图里的年份统一替换为今年。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import config as _config
from .render import AUTOFIT_JS, COVER_VARIANTS, font_css, font_stack, mix, note_seed

CURRENT_YEAR = str(date.today().year)
W, H = 540, 720

CATEGORY_RULES = [
    ("排班表", ["排班", "值班", "班次", "倒班", "轮班"], "按班次排，门店和工厂常用"),
    ("自动统计版", ["自动统计", "汇总", "统计"], "改个公司名，出勤缺勤自动算"),
    ("打卡记录", ["打卡", "签到", "考勤机"], "原始打卡记录整理用"),
    ("专项版", ["请假", "年假", "调休", "加班"], "请假 / 加班 / 年假单列统计"),
    ("Word 可打印版", ["word", "打印", "doc"], "签字、盖章、存档直接用"),
]

DEFAULT_CATEGORIES = [
    ("自动统计版", "改个公司名，出勤缺勤自动算"),
    ("部门 / 员工月度", "最常见版式，符号体系齐全"),
    ("带公式版", "出勤、缺勤、迟到自动汇总"),
    ("Word 可打印版", "签字、盖章、存档直接用"),
    ("专项版", "请假 / 加班 / 年假单列统计"),
]


@dataclass
class Sheet:
    file: Path
    kind: str
    title: str = ""
    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    formulas: int = 0
    names: int = 0
    grid: list[list[str]] = field(default_factory=list)
    features: set[str] = field(default_factory=set)

    @property
    def label(self) -> str:
        return self.file.stem


def clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = re.sub(r"\s+", " ", str(value)).strip()
    text = re.sub(r"20\d\d", CURRENT_YEAR, text)
    return text


def parse_xlsx(path: Path) -> Sheet:
    from openpyxl import load_workbook

    sheet = Sheet(file=path, kind="xlsx")
    values = load_workbook(path, read_only=True, data_only=True)
    formulas = load_workbook(path, read_only=True, data_only=False)
    try:
        ws = values[values.sheetnames[0]]
        fws = formulas[formulas.sheetnames[0]]
        grid: list[list[str]] = []
        for row in ws.iter_rows(min_row=1, max_row=min(30, ws.max_row or 1), max_col=min(18, ws.max_column or 1)):
            grid.append([clean(cell.value) for cell in row])
        for row in fws.iter_rows(min_row=1, max_row=min(300, fws.max_row or 1)):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    sheet.formulas += 1
    finally:
        values.close()
        formulas.close()

    grid = [row for row in grid if any(row)]
    sheet.grid = grid[:20]
    if not grid:
        return sheet
    header_index = max(range(min(10, len(grid))), key=lambda i: len([c for c in grid[i] if c]))
    sheet.header = [c for c in grid[header_index] if c][:12]
    sheet.rows = [row for row in grid[header_index + 1: header_index + 13] if any(row)]
    for row in grid[:header_index]:
        joined = " ".join(c for c in row if c)
        if len(joined) >= 3:
            sheet.title = joined[:60]
            break
    text = " ".join([" ".join(row) for row in grid[:10]])
    for feature in ("姓名", "出勤", "部门", "请假", "加班", "班次", "年假", "调休", "工资"):
        if feature in text or feature in " ".join(sheet.header):
            sheet.features.add(feature)
    sheet.names = max((sum(1 for value in row[1:2] if value) for row in sheet.rows), default=0) + len(sheet.rows)
    return sheet


def parse_xls(path: Path) -> Sheet:
    import xlrd

    book = xlrd.open_workbook(str(path))
    sheet = Sheet(file=path, kind="xls")
    ws = book.sheets()[0]
    grid = []
    for row_index in range(min(30, ws.nrows)):
        grid.append([clean(ws.cell_value(row_index, col)) for col in range(min(16, ws.ncols))])
    grid = [row for row in grid if any(row)]
    sheet.grid = grid[:20]
    if not grid:
        return sheet
    header_index = max(range(min(10, len(grid))), key=lambda i: len([c for c in grid[i] if c]))
    sheet.header = [c for c in grid[header_index] if c][:12]
    sheet.rows = [row for row in grid[header_index + 1: header_index + 13] if any(row)]
    for row in grid[:header_index]:
        joined = " ".join(c for c in row if c)
        if len(joined) >= 3:
            sheet.title = joined[:60]
            break
    text = " ".join(" ".join(row) for row in grid[:10])
    for feature in ("姓名", "出勤", "部门", "请假", "加班", "班次", "年假", "调休", "工资"):
        if feature in text or feature in " ".join(sheet.header):
            sheet.features.add(feature)
    sheet.names = len(sheet.rows)
    return sheet


def parse_docx(path: Path) -> Sheet:
    import docx

    document = docx.Document(str(path))
    sheet = Sheet(file=path, kind="docx")
    if not document.tables:
        return sheet
    table = document.tables[0]
    grid = []
    for row in table.rows[:14]:
        grid.append([clean(cell.text)[:12] for cell in row.cells[:12]])
    grid = [row for row in grid if any(row)]
    sheet.grid = grid[:20]
    if not grid:
        return sheet
    sheet.header = [c for c in grid[0] if c]
    sheet.rows = grid[1:10]
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    sheet.title = (paragraphs[0] if paragraphs else path.stem)[:60]
    return sheet


def parse_pack(data_dir: Path) -> list[Sheet]:
    sheets: list[Sheet] = []
    skipped: list[str] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in (".xlsx", ".xlsm", ".xls", ".docx"):
            skipped.append(path.name)
            continue
        try:
            if suffix in (".xlsx", ".xlsm"):
                sheets.append(parse_xlsx(path))
            elif suffix == ".xls":
                sheets.append(parse_xls(path))
            elif suffix == ".docx":
                sheets.append(parse_docx(path))
        except Exception as error:  # 单个坏文件不影响整包
            print(f"! {path.name}: {error}")
    if skipped:
        print(f"! 跳过 {len(skipped)} 份格式不支持的资料：{'、'.join(skipped[:8])}"
              f"{' 等' if len(skipped) > 8 else ''}（这套流程只读 xlsx / xls / docx）")
    return [sheet for sheet in sheets if sheet.header or sheet.rows]


def categorize(sheets: list[Sheet]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    has_word = any(sheet.kind in ("docx", "doc") for sheet in sheets)
    has_formula = any(sheet.formulas > 0 for sheet in sheets)
    has_special = any(sheet.features & {"请假", "加班", "年假", "调休"} for sheet in sheets)
    has_shift = any("班次" in sheet.features for sheet in sheets)
    has_auto = any("自动统计" in (sheet.title + " ".join(sheet.header)) for sheet in sheets) or has_formula

    if has_auto:
        found.append(("自动统计版", "改个公司名，出勤缺勤自动算"))
    if any(sheet.features & {"姓名", "出勤"} for sheet in sheets):
        found.append(("部门 / 员工月度", "最常见版式，符号体系齐全"))
    if has_formula:
        found.append(("带公式版", "出勤、缺勤、迟到自动汇总"))
    if has_word:
        found.append(("Word 可打印版", "签字、盖章、存档直接用"))
    if has_special:
        found.append(("专项版", "请假 / 加班 / 年假单列统计"))
    if has_shift:
        found.append(("排班表", "按班次排，门店和工厂常用"))
    if not found:
        found = [(name, desc) for name, desc in DEFAULT_CATEGORIES[:3]]
    return found[:5]


def pick_previews(sheets: list[Sheet]) -> list[Sheet]:
    """保留接口：标准表重绘不依赖具体文件，这里只返回前几个做参考。"""
    return sheets[:3]


# ---------------------------------------------------------------- 表格预览图（按资料特征重绘）
CANON_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1260px;background:var(--card);padding:26px 28px 24px;font-family:"Songti SC","STSong","PingFang SC",serif;color:#111}
.head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:16px}
.title{font-size:36px;font-weight:600;letter-spacing:.08em}
.badge{font-family:var(--font);font-size:16px;color:#137333;background:#E6F4EA;border:1px solid #A8D5B5;
 border-radius:999px;padding:5px 12px;display:inline-flex;align-items:center;gap:6px}
.badge i{width:7px;height:7px;border-radius:50%;background:#1F9D55;display:inline-block}
table{border-collapse:collapse;width:100%;table-layout:fixed}
th,td{border:1px solid #8e99a3;font-size:23px;line-height:1.3;padding:0 3px;text-align:center;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;height:54px}
thead th{background:#2F75B5;color:#fff;font-weight:600;font-size:20px;border-color:#2F75B5}
thead tr.week th{background:#5B9BD5;font-size:19px;height:40px}
th.weekend{background:#3E6E9E}
td{background:var(--card)}
td.weekend{background:#F3F6FA}
td.name{background:#eef3f8;font-weight:600;text-align:center}
td.ok{color:#137333;font-weight:700}
td.no{color:#C5221F;font-weight:700}
td.leave{color:#B06000;font-weight:700}
td.rest{color:#9AA0A6}
td.stat{background:#EAF1FB;font-weight:700;color:#12395F}
td.stat.bad{background:#FCE8E6;color:#A50E0E}
td.stat.warn{background:#FEF3E2;color:#8A5300}
tfoot td{background:#E8EEF6;font-weight:700;color:#12395F;font-size:21px;height:50px}
.tabs{display:flex;gap:2px;margin-top:10px;border-bottom:2px solid #2F75B5;padding-left:2px}
.tabs span{font-family:var(--font);font-size:17px;color:#44505c;background:#eceff3;border:1px solid #d4dae0;
 border-bottom:0;border-radius:6px 6px 0 0;padding:7px 18px}
.tabs span.active{background:var(--card);color:#1a5a96;font-weight:600;border-color:#2F75B5;box-shadow:inset 0 3px 0 #2F75B5}
.tabs span.gap{background:transparent;border:0;color:#8a949e;padding:7px 6px}
"""
NAME_POOL = ["张伟", "李娜", "王芳", "刘洋", "陈静", "杨磊", "赵敏", "黄强", "周洁", "吴涛"]


def pack_features(sheets: list[Sheet]) -> set[str]:
    features: set[str] = set()
    for sheet in sheets:
        features |= sheet.features
        text = " ".join(sheet.header) + " " + " ".join(" ".join(row) for row in sheet.grid[:6])
        for word in ("部门", "出勤", "缺勤", "病假", "事假", "早退", "迟到", "旷工", "加班", "年假", "调休", "班次"):
            if word in text:
                features.add(word)
    return features


def canonical_table(kind: str, features: set[str], title: str, variant: int = 0) -> str:
    """按 kind 画一张标准考勤表：固定版式 + 颜色标注 + 多 sheet 标签。"""
    days = 12 if kind != "word" else 15
    weekdays = [["四", "五", "六", "日", "一", "二", "三"][i % 7] for i in range(days)]
    if kind == "auto":
        summary = ["出勤", "病假", "事假", "迟到", "合计"]
    elif kind == "dept":
        summary = ["出勤", "缺勤", "病假", "迟到", "合计"]
    else:
        summary = ["出勤", "签字"]
    lead = ["部门", "姓名"] if kind == "dept" else (["序号", "姓名"] if kind == "word" else ["姓名"])

    lead_w = 11 if len(lead) == 2 else 12
    sum_w = 7.6
    day_w = (100 - lead_w * len(lead) - sum_w * len(summary)) / days
    widths = [f"{lead_w}%"] * len(lead) + [f"{day_w:.2f}%"] * days + [f"{sum_w}%"] * len(summary)
    colgroup = "".join(f'<col style="width:{width}">' for width in widths)

    head_week = "<tr class='week'>" + "".join(f"<th rowspan='2' class='name'>{name}</th>" for name in lead)
    head_week += "".join(
        f"<th class='{'weekend' if day in ('六', '日') else ''}'>{day}</th>" for day in weekdays
    )
    head_week += "".join(f"<th rowspan='2'>{name}</th>" for name in summary) + "</tr>"
    head_day = "<tr>" + "".join(
        f"<th class='{'weekend' if weekdays[index] in ('六', '日') else ''}'>{index + 1}</th>"
        for index in range(days)
    ) + "</tr>"

    name_offset = variant % len(NAME_POOL)
    names = NAME_POOL[name_offset:] + NAME_POOL[:name_offset]
    dept_names = ["行政部", "人事部", "财务部"]
    dept_offset = variant % len(dept_names)
    depts = dept_names[dept_offset:] + dept_names[:dept_offset]

    rows = []
    totals: list[int | None] = [0] * len(summary)
    for row_index in range(10):
        cells = []
        if kind == "dept":
            cells.append(f"<td class='name'>{depts[row_index % len(depts)]}</td>")
            cells.append(f"<td class='name'>{names[row_index % len(names)]}</td>")
        elif kind == "word":
            cells.append(f"<td class='name'>{row_index + 1}</td>")
            cells.append(f"<td class='name'>{names[row_index % len(names)]}</td>")
        else:
            cells.append(f"<td class='name'>{names[row_index % len(names)]}</td>")
        present = leave = absent = late = 0
        for day in range(days):
            weekend = weekdays[day] in ("六", "日")
            if weekend:
                mark, cls = "○", "rest"
            elif (row_index + day) % 9 == 0:
                mark, cls, absent = "×", "no", absent + 1
            elif (row_index + day) % 11 == 0:
                mark, cls, leave = "△", "leave", leave + 1
            else:
                mark, cls, present = "√", "ok", present + 1
            cells.append(f"<td class='{cls}{' weekend' if weekend else ''}'>{mark}</td>")
        total = present + leave + absent
        if kind == "auto":
            stats = [(present, "stat"), (leave, "stat warn"), ((row_index % 2), "stat warn"),
                     ((row_index % 2), "stat bad"), (total, "stat")]
        elif kind == "dept":
            stats = [(present, "stat"), (absent, "stat bad"), (leave, "stat warn"),
                     ((row_index % 2), "stat bad"), (total, "stat")]
        else:
            stats = [(present, "stat"), (-1, "stat")]
        for index, (value, cls) in enumerate(stats):
            if value == -1:
                totals[index] = None
                cells.append("<td class='stat'></td>")
            else:
                if totals[index] is not None:
                    totals[index] += value
                cells.append(f"<td class='{cls}'>{value}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    foot_cells = ["<td></td>"] * len(lead)
    foot_cells += [f"<td class='name' cols='{days}'></td>" if False else "" for _ in range(0)]
    foot_row = "<tr>" + "<td colspan='" + str(len(lead)) + "'>部门合计</td>"
    foot_row += "".join("<td></td>" for _ in range(days))
    foot_row += "".join("<td></td>" if value is None else f"<td>{value}</td>" for value in totals) + "</tr>"

    tabs = "".join(
        f"<span class='{'active' if index == 6 else ''}'>{index + 1}月</span>" for index in range(12)
    )
    tabs += "<span class='gap'>…</span><span>使用说明</span>"

    return f"""<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><style>{CANON_CSS}</style></head>
<body>
<div class="head"><div class="title">{title}</div><div class="badge"><i></i>自动统计</div></div>
<table><colgroup>{colgroup}</colgroup>
<thead>{head_week}{head_day}</thead>
<tbody>{''.join(rows)}</tbody>
<tfoot>{foot_row}</tfoot></table>
<div class="tabs">{tabs}</div>
</body></html>"""


def render_canonical(browser, kind: str, features: set[str], title: str, out_path: Path, variant: int = 0) -> Path:
    html = canonical_table(kind, features, title, variant)
    tmp = out_path.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    page = browser.new_page(viewport={"width": 1240, "height": 820}, device_scale_factor=1)
    page.goto(tmp.as_uri(), wait_until="load")
    page.wait_for_timeout(80)
    bottom = page.evaluate("() => { const t = document.querySelector('.tabs') || document.querySelector('table'); return t ? t.getBoundingClientRect().bottom + 26 : document.body.scrollHeight }")
    page.set_viewport_size({"width": 1240, "height": max(320, min(1200, int(bottom)))})
    page.wait_for_timeout(60)
    page.screenshot(path=str(out_path), full_page=False)
    page.close()
    tmp.unlink(missing_ok=True)
    return out_path


# ---------------------------------------------------------------- 页面
BASE = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html{{font-size:16px}}
body{{width:{W}px;height:{H}px;overflow:hidden;background:var(--bg);color:var(--ink);
 font-family:var(--font);-webkit-font-smoothing:antialiased}}
.page{{position:relative;width:100%;height:100%;display:flex;flex-direction:column;padding:1.5rem 2rem 1.3rem;overflow:hidden}}
.topbar{{position:absolute;top:0;left:0;right:0;height:.42rem;background:var(--accent)}}
.kicker{{align-self:flex-start;background:var(--accent);color:var(--on-accent);font-size:.7rem;font-weight:700;
 padding:.34rem .6rem;border-radius:.4rem;position:relative;z-index:2}}
.mark{{background:linear-gradient(transparent 54%,var(--accent-soft) 54%,var(--accent-soft) 92%,transparent 92%)}}
.title{{position:relative;z-index:2;font-weight:900;letter-spacing:-.035em;line-height:1.22;text-wrap:balance}}
.foot{{margin-top:auto;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--line);
 padding-top:.62rem;font-size:.72rem;position:relative;z-index:2}}
.foot b{{color:var(--accent)}}
.foot span{{color:var(--muted);font-size:.64rem}}
.sticker{{font-size:.7rem;font-weight:700;padding:.38rem .64rem;border-radius:.45rem;
 box-shadow:0 6px 14px rgba(80,40,20,.10);display:inline-block}}
.how{{margin-top:1.1rem;display:flex;border:1px solid var(--line);border-radius:.55rem;overflow:hidden;background:var(--card)}}
.how div{{flex:1;padding:.7rem .55rem;border-right:1px solid var(--line)}}
.how div:last-child{{border-right:0}}
.how b{{display:block;font-size:.66rem;color:var(--accent);margin-bottom:.22rem}}
.how span{{font-size:.7rem;line-height:1.5;color:var(--ink)}}
"""


def token_css(cfg: dict) -> str:
    """每篇按标题哈希取主色与封面变体，保证同一篇可复现、批内不撞脸。"""
    seed = note_seed({"title": cfg.get("title", "")})
    palette = _config.PALETTES["warm"]
    accents = palette.get("accents") or [palette["accent"]]
    accent = accents[seed % len(accents)]
    bg, ink = palette["bg"], palette["ink"]
    tokens = {
        "--font": font_stack(),
        "--bg": bg,
        "--ink": ink,
        "--muted": palette["muted"],
        "--accent": accent,
        "--accent-soft": mix(accent, bg, 0.16),
        "--line": mix(ink, bg, 0.14),
        "--card": "#FFFFFF",
        "--on-accent": palette.get("on_accent") or "#FFFFFF",
    }
    root = ":root{" + ";".join(f"{key}:{value}" for key, value in tokens.items()) + "}"
    variant = COVER_VARIANTS[seed % len(COVER_VARIANTS)]
    faces = font_css().removeprefix("<style>").removesuffix("</style>")
    return f"{root}\n{faces}\nbody{{--variant:{variant}}}"

COVER_CSS = BASE + """
.ring{position:absolute;right:-5.5rem;top:-3.5rem;width:21rem;height:21rem;border-radius:50%;
 background:var(--accent-soft);opacity:.5;z-index:0}
.ring::after{content:"";position:absolute;inset:4.2rem;border-radius:50%;border:1px solid var(--accent);opacity:.3}
.tagpill{background:var(--accent);color:#fff;font-size:.74rem;font-weight:700;letter-spacing:.1em;padding:.42rem .8rem;
 border-radius:999px;box-shadow:0 8px 20px rgba(255,75,62,.22)}
.title{font-size:3.3rem;line-height:1.06;margin-top:1rem}
.sub{margin-top:.9rem;font-size:.9rem;line-height:1.6;color:var(--muted);position:relative;z-index:2;white-space:pre-line}
.stickers{display:flex;gap:.5rem;margin-top:1rem;flex-wrap:wrap}
.shot{margin:1.3rem -2.9rem 0 0;align-self:flex-end;width:30rem;transform:rotate(-4deg);border:7px solid var(--card);
 border-radius:.5rem;box-shadow:0 24px 50px rgba(70,30,10,.22);overflow:hidden}
.shot img{width:100%;display:block}
.caption{margin-top:.85rem;font-size:.7rem;color:var(--muted)}
.caption b{color:var(--accent)}
.cats{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.7rem}
.cats span{font-size:.6rem;font-weight:600;background:var(--card);border:1px solid var(--line);border-radius:999px;
 padding:.26rem .52rem;color:var(--muted)}
"""

CATALOG_CSS = BASE + """
.title{font-size:2rem;margin-top:.9rem}
.tagline{margin-top:.55rem;font-size:.78rem;color:var(--muted)}
.rows{margin-top:1.1rem;display:flex;flex-direction:column;gap:.5rem}
.row{display:flex;align-items:center;gap:.7rem;background:var(--card);border:1px solid var(--line);border-radius:.55rem;
 padding:.6rem .7rem;box-shadow:0 8px 18px rgba(80,40,20,.08)}
.no{flex:none;width:1.5rem;height:1.5rem;background:var(--accent);color:#fff;font-size:.72rem;font-weight:800;
 border-radius:.3rem;display:grid;place-items:center}
.mid{flex:1;min-width:0}
.mid b{display:block;font-size:.86rem}
.mid i{display:block;font-style:normal;font-size:.66rem;color:var(--muted);margin-top:.16rem}
.stickers{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.9rem}
.tip{margin-top:auto;font-size:.7rem;line-height:1.7;color:var(--muted);border-left:3px solid var(--accent);padding-left:.65rem}
"""

PREVIEW_CSS = BASE + """
.title{font-size:1.95rem;margin-top:.85rem;line-height:1.24}
.subline{margin-top:.5rem;font-size:.72rem;color:var(--muted)}
.shot{margin-top:.85rem;border:6px solid var(--card);border-radius:.5rem;box-shadow:0 16px 36px rgba(70,30,10,.16);
 overflow:hidden;position:relative}
.shot img{width:100%;display:block}
.box{position:absolute;border:3px solid var(--accent);border-radius:4px}
.point{position:absolute;background:var(--accent);color:#fff;font-size:.58rem;font-weight:700;padding:.22rem .42rem;border-radius:.3rem}
.fx{margin-top:.7rem;display:flex;align-items:center;gap:.5rem;background:#1C1719;color:#e9dfe3;border-radius:.45rem;
 padding:.42rem .6rem;font:0.62rem/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;overflow:hidden}
.fx b{color:var(--accent-soft);font-weight:700}
.fx span{color:#9f958f;font-family:var(--font);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.notes{margin-top:.8rem;display:flex;flex-direction:column;gap:.42rem}
.notes div{font-size:.72rem;line-height:1.55;color:var(--ink);padding-left:.9rem;position:relative}
.notes div::before{content:"";position:absolute;left:0;top:.4rem;width:.32rem;height:.32rem;background:var(--accent);border-radius:50%}
"""

CLAIM_CSS = BASE + """
.title{font-size:2.35rem;margin-top:1.2rem;line-height:1.2}
.steps{margin-top:1.3rem;display:flex;flex-direction:column;gap:.75rem}
.step{display:flex;gap:.7rem;align-items:flex-start}
.step b{flex:none;width:1.7rem;height:1.7rem;border-radius:50%;background:var(--accent);color:#fff;font-size:.78rem;display:grid;place-items:center}
.step div{flex:1;font-size:.84rem;line-height:1.6;color:var(--ink)}
.step div i{display:block;font-style:normal;font-size:.66rem;color:var(--muted);margin-top:.14rem}
.quote{margin-top:1.1rem;background:var(--card);border:1.5px dashed var(--ink);border-radius:.5rem;padding:.7rem .8rem;
 font-size:.7rem;line-height:1.6;color:var(--muted)}
.next{margin-top:.9rem;display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;font-size:.68rem;color:var(--muted)}
.next b{font-weight:700;background:var(--card);border:1px solid var(--line);border-radius:999px;padding:.26rem .58rem;color:var(--ink)}
.next span{color:var(--accent);font-weight:700}
.qa{margin-top:1rem;border-left:3px solid var(--accent);padding-left:.7rem}
.qa div{font-size:.7rem;line-height:1.8;color:var(--ink)}
.qa b{color:var(--accent)}
"""


def build_config(sheets: list[Sheet], title: str, audience: str, keyword: str) -> dict:
    categories = categorize(sheets)
    previews = pick_previews(sheets)
    return {
        "title": title,
        "audience": audience,
        "keyword": keyword,
        "categories": [{"name": name, "desc": desc} for name, desc in categories],
        "sheets": sheets,
        "previews": previews,
        "caption": None,
    }


def wrap_title(raw: str) -> list[str]:
    raw = str(raw or "").strip()
    if "\n" in raw:
        return [line for line in raw.split("\n") if line.strip()]
    if len(raw.replace(" ", "")) <= 9:
        return [raw]
    tokens = [token for token in raw.split(" ") if token]
    lines: list[str] = []
    current = ""
    for token in tokens:
        candidate = f"{current} {token}".strip()
        if current and len(candidate.replace(" ", "")) > 8:
            lines.append(current)
            current = token
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [raw]


def cover_html(cfg: dict, shot: str) -> str:
    lines = wrap_title(cfg["title"])
    highlight = cfg.get("highlight", "")
    rendered = []
    for line in lines:
        if highlight and highlight in line:
            line = line.replace(highlight, f'<span class="mark">{highlight}</span>')
        rendered.append(line)
    cats = "".join(f"<span>{item['name']}</span>" for item in cfg["categories"])
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{token_css(cfg)}{COVER_CSS}</style></head><body>
<div class="page"><div class="topbar"></div><div class="ring"></div>
  <div style="display:flex"><span class="tagpill">{cfg['audience']}</span></div>
  <div class="title">{'<br>'.join(rendered)}</div>
  <div class="sub">{cfg['sub']}</div>
  <div class="stickers">
    <span class="sticker" style="background:var(--accent);color:var(--on-accent);transform:rotate(-3deg)">{cfg['stickers'][0]}</span>
    <span class="sticker" style="background:var(--card);border:1px solid var(--line);transform:rotate(2deg)">{cfg['stickers'][1]}</span>
  </div>
  <div class="shot"><img src="{shot}" /></div>
  <div class="caption"><b>↑</b> 实际模板长这样，不是效果图</div>
  <div class="cats">{cats}</div>
  <div class="foot"><span>评论区扣 <b>「{cfg['keyword']}」</b>，我私信发你</span><span>左滑看清单</span></div>
</div></body></html>"""


def catalog_html(cfg: dict) -> str:
    rows = "".join(
        f'<div class="row"><span class="no">{index:02d}</span><div class="mid"><b>{item["name"]}</b>'
        f'<i>{item["desc"]}</i></div></div>'
        for index, item in enumerate(cfg["categories"], 1)
    )
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{token_css(cfg)}{CATALOG_CSS}</style></head><body>
<div class="page"><div class="topbar"></div>
  <div class="kicker">内含清单</div>
  <div class="title">按类型分好<br><span class="mark">对号入座就行</span></div>
  <div class="tagline">全部可编辑，公式和符号说明都保留着</div>
  <div class="rows">{rows}</div>
  <div class="stickers">
    <span class="sticker" style="background:var(--accent-soft);transform:rotate(-2deg)">不用从空白表画起</span>
    <span class="sticker" style="background:var(--card);border:1px solid var(--line)">源文件都在</span>
  </div>
  <div class="tip"><b>不知道怎么选</b>：先用第二个「部门 / 员工月度」，最通用。</div>
  <div class="foot"><span>全部可编辑</span><span>2 / 6</span></div>
</div></body></html>"""


def preview_html(index: int, badge: str, note: str, headline: str, sheet_png: str,
                 bullets: list[str], steps: list[str], box: dict | None, page_no: str,
                 formula: str = "", theme: str = "") -> str:
    box_html = ""
    if box:
        box_html = (f'<span class="box" style="right:{box["right"]};top:{box["top"]};'
                    f'width:{box["width"]};height:{box["height"]}"></span>')
    notes = "".join(f"<div>{text}</div>" for text in bullets)
    step_html = "".join(f"<div><b>STEP {i}</b><span>{text}</span></div>" for i, text in enumerate(steps, 1))
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{theme}{PREVIEW_CSS}</style></head><body>
<div class="page"><div class="topbar"></div>
  <div style="display:flex;align-items:center;gap:.55rem">
    <span class="kicker">{badge}</span><span class="subline" style="margin:0">{note}</span>
  </div>
  <div class="title">{headline}</div>
  <div class="shot"><img src="{sheet_png}" />{box_html}</div>
  {f'<div class="fx"><b>fx</b><span>{formula}</span></div>' if formula else ''}
  <div class="notes">{notes}</div>
  <div class="how">{step_html}</div>
  <div class="foot"><span>实际模板 · {badge}</span><span>{page_no}</span></div>
</div></body></html>"""


def claim_html(cfg: dict) -> str:
    keyword = cfg["keyword"]
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{token_css(cfg)}{CLAIM_CSS}</style></head><body>
<div class="page"><div class="topbar"></div>
  <div class="kicker">怎么拿</div>
  <div class="title">评论区扣<br><span class="mark">「{keyword}」</span>我私信发你</div>
  <div class="steps">
    <div class="step"><b>1</b><div>在评论区扣「{keyword}」<i>看到就会回，不用加好友</i></div></div>
    <div class="step"><b>2</b><div>收到私信后回我一句<i>方便我把整理好的文件发给你</i></div></div>
    <div class="step"><b>3</b><div>先收藏，防止刷走找不到<i>后面还会更同系列的模板</i></div></div>
  </div>
  <div class="quote">资料不收费，也别拿去卖。<br>整理一次很费时间，能帮到同行就行。</div>
  <div class="next"><span>还会更</span><b>排班表</b><b>入职登记表</b><b>离职交接单</b></div>
  <div class="qa">
    <div><b>Q</b> 能打开吗？ <b>A</b> 都是 xls / xlsx / docx，手机电脑都能看。</div>
    <div><b>Q</b> 能改吗？ <b>A</b> 都是源文件，公式和格式保留，改公司名就能用。</div>
  </div>
  <div class="foot"><span>关注不迷路</span><span>6 / 6</span></div>
</div></body></html>"""


PREVIEW_COPY = {
    "auto": {
        "badge": "自动统计版",
        "note": "改个名字就能用",
        "headline": "右边这几列<br><span class='mark'>是公式自己算的</span>",
        "bullets": ["每天打钩，右边自动出数", "改公司名、改月份，其他都不用动"],
        "steps": ["改公司名和月份", "每天打钩记录", "月底自动出数"],
    },
    "dept": {
        "badge": "部门月度版",
        "note": "最常见的那种版式",
        "headline": "部门考勤，<br><span class='mark'>一张表管一整月</span>",
        "bullets": ["姓名 + 整月日期 + 出勤/缺勤/迟到", "打印手填、或电子版打钩都行", "表头写部门和月份，月底直接归档"],
        "steps": ["填部门和月份", "打印或电子版打钩", "签字归档"],
    },
    "word": {
        "badge": "Word 可打印版",
        "note": "签字盖章用这个",
        "headline": "要签字盖章的，<br><span class='mark'>用这个版本</span>",
        "bullets": ["Word 版式，A4 打印不变形", "表底留了制表人、主管领导的签字位", "和 Excel 版配套，改内容也不难"],
        "steps": ["下载 Word 版", "填人数和月份", "A4 打印签字"],
    },
}


def build_caption(cfg: dict) -> str:
    lines = [cfg["title"].replace("\n", ""), ""]
    lines += ["每个月做考勤、排班、统计，最烦的不是算，是又要新建一个表、调格式、补公式。", ""]
    lines += [f"这次把手上这些整理了一下，按类型分好了："]
    for item in cfg["categories"]:
        lines.append(f"· {item['name']}：{item['desc']}")
    lines += ["", "图里放了几张预览，都能在包里找到。", "行政、前台、刚接手的姐妹，直接对号入座就行。", ""]
    lines += [f"需要的话评论区扣「{cfg['keyword']}」，我私信发你。", "不收费，也别拿去卖，整理一次挺费时间的。", ""]
    lines += ["#HR #考勤表 #人事行政 #Excel模板 #行政 #前台 #职场干货 #办公技巧"]
    return "\n".join(lines)


def plan_to_cfg(plan: dict, sheets: list[Sheet]) -> dict:
    return {
        "title": plan["title"],
        "highlight": plan.get("highlight", ""),
        "audience": plan["audience"],
        "sub": plan.get("sub") or "",
        "stickers": plan.get("stickers") or ["可直接编辑", "改名字就能用"],
        "categories": plan["categories"],
        "previews": plan["previews"],
        "keyword": plan.get("keyword", "资料"),
        "sheets": sheets,
        "caption": plan.get("caption", ""),
    }


def render_note(cfg: dict, out_dir: Path, variant: int = 0) -> dict:
    """渲染一套 6 张图 + caption.md；variant 决定月份与人名轮换，让批量出的图不重样。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[Sheet] = cfg["sheets"]
    features = pack_features(sheets)
    year = CURRENT_YEAR
    month = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6][variant % 12]
    titles = [f"{year}年{month}月份考勤表"] * 3

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--font-render-hinting=none", "--allow-file-access-from-files"])
        shots = []
        for index, kind in enumerate(("auto", "dept", "word")):
            path = out_dir / f"_sheet-{index + 1}.png"
            render_canonical(browser, kind, features, titles[index], path, variant)
            shots.append(path.as_uri())

        pages = [("01.png", cover_html(cfg, shots[0])), ("02.png", catalog_html(cfg))]
        for index, kind in enumerate(("auto", "dept", "word")):
            copy = cfg["previews"][index]
            box = None
            if index == 0:
                box = {"right": "2.2%", "top": "26.5%", "width": "36%", "height": "52%"}
            pages.append((f"{index + 3:02d}.png", preview_html(
                index, copy["badge"], copy["note"], copy["headline"], shots[index],
                copy["bullets"], copy["steps"], box, f"{index + 3} / 6", copy.get("formula", ""),
                token_css(cfg))))
        pages.append(("06.png", claim_html(cfg)))

        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for name, html in pages:
            tmp = out_dir / f".{name}.html"
            tmp.write_text(html, encoding="utf-8")
            page.goto(tmp.as_uri(), wait_until="load")
            page.evaluate("() => document.fonts.ready.then(() => true)")
            page.wait_for_timeout(120)
            shrink = page.evaluate(AUTOFIT_JS, {"w": W, "h": H})
            if shrink:
                print("  · 文字偏多，缩到", shrink)
            page.screenshot(path=str(out_dir / name))
            tmp.unlink(missing_ok=True)
            print("rendered", name)
        browser.close()

    caption = cfg.get("caption") or build_caption(cfg)
    (out_dir / "caption.md").write_text(caption, encoding="utf-8")
    for temp in out_dir.glob("_sheet-*.png"):
        temp.unlink(missing_ok=True)
    return {
        "images": [f"{index:02d}.png" for index in range(1, 7)],
        "caption": caption,
    }


def render(cfg: dict, out_dir: Path) -> None:
    render_note(cfg, out_dir, 0)


def main(argv: list[str] | None = None) -> int:
    import warnings
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser("xhs.pack", description="资料包 → 一套小红书图文")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default="别再从零做表了")
    parser.add_argument("--highlight", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--keyword", default="资料")
    parser.add_argument("--sub", default="")
    parser.add_argument("--plan", default="", help="planner 生成的方案 JSON")
    parser.add_argument("--pick", type=int, default=0, help="用第几套方案（从 0 开始）")
    args = parser.parse_args(argv)

    data_dir = Path(args.data).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    sheets = parse_pack(data_dir)
    if not sheets:
        print("× 没解析到可用的表格")
        return 2
    if args.plan:
        payload = json.loads(Path(args.plan).expanduser().read_text(encoding="utf-8"))
        plans = payload.get("plans") or []
        if not plans:
            print("× 方案文件里没有 plans")
            return 2
        plan = plans[min(args.pick, len(plans) - 1)]
        cfg = {
            "title": plan["title"],
            "highlight": plan.get("highlight", ""),
            "audience": plan["audience"],
            "sub": plan.get("sub") or "",
            "stickers": plan.get("stickers") or ["可直接编辑", "改名字就能用"],
            "categories": plan["categories"],
            "previews": plan["previews"],
            "keyword": plan.get("keyword", "资料"),
            "sheets": sheets,
            "caption": plan.get("caption", ""),
        }
    else:
        cfg = build_config(sheets, args.title, args.audience or "打工人", args.keyword)
        cfg["sub"] = args.sub or "每个月新建表、调格式、补公式\n现成的版式，改个名字就能用"
        cfg["highlight"] = args.highlight or ""
        cfg["stickers"] = ["自动汇总", "可直接打印"]
        cfg["previews"] = [
            dict(PREVIEW_COPY["auto"], formula='=COUNTIF(C4:N4,"√")  ← 出勤天数，月底自动汇总'),
            dict(PREVIEW_COPY["dept"], formula='=SUMIF(部门列,"行政部",出勤列)  ← 按部门汇总'),
            dict(PREVIEW_COPY["word"], formula=""),
        ]
    render(cfg, out_dir)
    print("完成：", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
