"""自动编排：读资料事实 → 模型给 3 套方案（人群/角度不同）。

模型只负责“写文案层”，所有事实来自解析器；方案落盘后由 pack.py 严格渲染。
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from pathlib import Path

from . import llm
from .pack import Sheet, parse_pack

from .prompts import VOICE

PLAN_SYSTEM = """你是小红书内容策划，擅长把一份资料包变成一套能引流的小红书图文。
你只输出 JSON，不解释。"""

PLAN_PROMPT = """下面是对一份资料包的解析结果（事实清单）。不要凭空添加清单里没有的功能。

{facts}

请给出 {count} 套不同的「编排方案」，每套面向不同人群/场景，但都基于同一份资料。
人群必须来自「主流场景」，禁止把「边缘模板」的行业写成人群或标题（例如资料以办公考勤为主，就不能出现工地记工、记工员、工种登记这类主题）：
- 第 1 套：主推人群（最可能收藏的人）
- 之后每套换一个角度：换人群（岗位/身份不同）或换场景（时间节点/使用场合不同），不要和前面重复
- 套数多时也要保证标题和人群各不相同，不要换汤不换药

每套方案输出这些字段：
- name：方案名（≤10 字，如“HR 主推”）
- audience：封面左上角的人群标签（≤14 字，如“HR / 行政 专用”）
- title：封面主标题（≤14 字，可用 \\n 分两行；要像小红书标题，有痛点或身份）
- highlight：必须出现在 title 里的高亮词（≤6 字，用于荧光笔标注）
- sub：封面副标题（≤30 字，两行，用 \\n 分隔；不要出现空括号、占位符，如“年( )月”要写成“每月”）
- stickers：两个具体卖点贴纸（各 ≤8 字，如“出勤自动算”“A4 直接打”），不要写“够用”这类空话
- categories：5 个分类，每个 name ≤10 字、desc ≤20 字；分类必须来自事实清单里的类型
- previews：3 张预览页，每张 badge（≤8 字）、note（≤10 字）、headline（≤18 字，可含 \\n）、
  bullets（2 条，每条 ≤24 字）、steps（3 条，每条 ≤10 字）、formula（可选，一条 Excel 公式说明，≤30 字，没有就给空）
- keyword：评论区关键词（2-4 字，如“资料”“考勤”）
- caption：小红书正文（300-500 字，开头抓人，中间列 5 类，结尾引导评论；不要出现“网盘、链接、微信、免费领取”）。正文必须满足下面这套语感规范，emoji 数量、位置、分工都要照做：

{voice}

只输出 JSON：
{{"plans":[{{
  "name":"","audience":"","title":"","highlight":"","sub":"","stickers":["",""],
  "categories":[{{"name":"","desc":""}}],
  "previews":[{{"badge":"","note":"","headline":"","bullets":["",""],"steps":["","",""],"formula":""}}],
  "keyword":"","caption":""
}}]}}，plans 里恰好 {count} 套。"""


FRINGE_WORDS = ("记工", "工地", "工种", "进场", "计件", "产线", "车间", "门店", "学校", "医院", "酒店", "餐饮")


def scene_mix(sheets: list[Sheet]) -> tuple[list[str], list[str]]:
    """区分主流场景和边缘模板：只出现在少数文件里的行业词，不能拿来做方案主题。"""
    total = max(1, len(sheets))
    hits: dict[str, int] = {word: 0 for word in FRINGE_WORDS}
    for sheet in sheets:
        text = sheet.title + " " + " ".join(sheet.header) + " " + " ".join(" ".join(row) for row in sheet.grid[:6])
        for word in FRINGE_WORDS:
            if word in text:
                hits[word] += 1
    mainstream = [word for word, count in hits.items() if count >= total * 0.4]
    fringe = [word for word, count in hits.items() if 0 < count < total * 0.2]
    return mainstream, fringe


def facts_text(sheets: list[Sheet], data_dir: Path) -> str:
    kinds: dict[str, int] = {}
    for sheet in sheets:
        kinds[sheet.kind] = kinds.get(sheet.kind, 0) + 1
    features = sorted(pack_features(sheets))
    titles = []
    headers = []
    for sheet in sheets[:40]:
        if sheet.title and sheet.title not in titles:
            titles.append(sheet.title[:40])
        for cell in sheet.header[:10]:
            if cell and cell not in headers:
                headers.append(cell)
    formulas = sum(1 for sheet in sheets if sheet.formulas > 0)
    mainstream, fringe = scene_mix(sheets)
    lines = [
        f"- 文件夹：{data_dir.name}",
        "- 文件类型：" + "、".join(f"{kind} {count} 个" for kind, count in kinds.items()),
        f"- 带公式的文件：{'有' if formulas else '没有'}",
        "- 出现过的表头词：" + "、".join(headers[:30]),
        "- 识别到的业务特征：" + "、".join(features),
        "- 资料里的标题样例：" + "；".join(titles[:8]),
        "- 主流场景：" + ("、".join(mainstream) or "办公通用"),
        "- 边缘模板（只出现在少数文件里，不能作为方案主题）：" + ("、".join(fringe) or "无"),
    ]
    return "\n".join(lines)


COUNT_PATTERN = re.compile(r"\d+\s*(?:款|份|套|个模板|种模板|个文件|个表)")
COUNT_LINE = re.compile(r"(\d+\s*(?:款|份|套)|一共|总共|整理\s*了\s*\d+)")
CN_YEAR = re.compile(r"二[〇○零一二三四五六七八九]{3}年")
CURRENT_YEAR = str(__import__("datetime").date.today().year)


def strip_years(text: str) -> str:
    """不出现旧年份：所有 20xx 统一成今年，中文年份改成“今年”。"""
    text = CN_YEAR.sub("今年", str(text or ""))
    return re.sub(r"20\d\d", CURRENT_YEAR, text)


def strip_counts(text: str) -> str:
    """用户要求：不出现资料份数。统一清掉“120款/80份/…”。"""
    text = strip_years(text)
    text = re.sub(r"年\s*[（(]\s*[)）]\s*月", "每月", text)
    text = re.sub(r"[（(]\s*[)）]", "", text)
    text = COUNT_PATTERN.sub("", str(text or ""))
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^[ \t]*[，、,]+", "", text)
    return text.strip()


def _clip(text: str, limit: int) -> str:
    text = strip_counts(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def has_fringe(text: str, fringe: list[str]) -> bool:
    return any(word in str(text or "") for word in fringe)


def validate(plan: dict, facts: str, fringe: list[str] | None = None) -> dict:
    plan["name"] = _clip(plan.get("name") or "方案", 12)
    plan["audience"] = _clip(plan.get("audience") or "打工人", 16)
    plan["title"] = _clip(plan.get("title") or "别再手画表了", 30)
    plan["highlight"] = _clip(plan.get("highlight") or "", 8)
    if plan["highlight"] and plan["highlight"] not in plan["title"]:
        plan["highlight"] = ""
    plan["sub"] = _clip(plan.get("sub") or "", 40)
    stickers = [str(item) for item in (plan.get("stickers") or []) if item][:2]
    while len(stickers) < 2:
        stickers.append("可直接编辑" if not stickers else "改名字就能用")
    plan["stickers"] = [_clip(item, 10) for item in stickers]

    categories = []
    for item in (plan.get("categories") or [])[:5]:
        name = _clip(item.get("name") or "", 12)
        desc = _clip(item.get("desc") or "", 22)
        if name:
            categories.append({"name": name, "desc": desc})
    while len(categories) < 3:
        categories.append({"name": "常用版式", "desc": "直接套用"})
    plan["categories"] = categories

    previews = []
    for item in (plan.get("previews") or [])[:3]:
        bullets = [_clip(text, 26) for text in (item.get("bullets") or []) if text][:2]
        steps = [_clip(text, 12) for text in (item.get("steps") or []) if text][:3]
        while len(steps) < 3:
            steps.append("直接套用")
        previews.append({
            "badge": _clip(item.get("badge") or "版式预览", 10),
            "note": _clip(item.get("note") or "", 12),
            "headline": _clip(item.get("headline") or "这张表，改个名字就能用", 24),
            "bullets": bullets or ["每天打钩，右边自动出数", "改公司名、改月份就能用"],
            "steps": steps,
            "formula": _clip(item.get("formula") or "", 40),
        })
    while len(previews) < 3:
        previews.append({
            "badge": "版式预览", "note": "", "headline": "这张表，改个名字就能用",
            "bullets": ["每天打钩，右边自动出数", "改公司名、改月份就能用"],
            "steps": ["改名字和月份", "每天记录", "月底出数"], "formula": "",
        })
    plan["previews"] = previews
    plan["keyword"] = _clip(plan.get("keyword") or "资料", 6)
    caption_lines = []
    for line in str(plan.get("caption") or "").splitlines():
        if COUNT_LINE.search(line) and ("份" in line or "款" in line or "套" in line):
            continue
        caption_lines.append(strip_counts(line))
    plan["caption"] = "\n".join(caption_lines).strip()[:1200]

    # 边缘模板不能进人群/标题
    if fringe and (has_fringe(plan["audience"], fringe) or has_fringe(plan["title"], fringe)):
        plan["_drop"] = True

    # 事实校验：没有公式就不能声称“自动统计/公式”
    if "自动" not in facts and "公式" not in facts:
        for preview in plan["previews"]:
            preview["formula"] = ""
            if any(word in preview["badge"] for word in ("自动", "公式")):
                preview["badge"] = "版式预览"
    return plan


def _data_plans(sheets: list[Sheet]) -> list[dict]:
    """非考勤资料的兜底：只描述资料里真实存在的表和列，不编业务。"""
    from .pack import data_previews

    categories = [
        {
            "name": (sheet.title or sheet.label)[:12],
            "desc": f"{len(sheet.rows)} 行 · {len(sheet.header)} 列",
        }
        for sheet in sheets[:5]
    ]
    first = sheets[0]
    label = (first.title or first.label).strip() or "这份表"
    cols = [cell.strip() for cell in first.header if cell.strip()][:4]
    cleaned = re.sub(r"(表|清单|模板|记录|统计)$", "", label).strip()
    keyword = cleaned if 2 <= len(cleaned) <= 4 else "表格"
    col_line = f"表头是 {' / '.join(cols)}。" if cols else ""

    seeds = [
        ("整理好了", "自己用 / 发给朋友", f"{label[:9]}\n我整理好了"),
        ("照着改", "第一次用的人", f"{label[:9]}\n照着改就行"),
        ("一份就够", "想省时间的人", "这份表\n一份就够"),
    ]
    plans = []
    for name, audience, title in seeds:
        lines = [title.replace("\n", ""), ""]
        lines.append(f"这份{label}整理了一阵，直接拿去用就行。")
        lines.append("")
        lines.append(f"里面有 {len(sheets)} 个表：")
        for item in categories:
            lines.append(f"· {item['name']}：{item['desc']}")
        lines += ["", col_line, "", "图里放的就是原表，不是效果图。", "",
                  f"需要的话评论区扣「{keyword}」，我私信发你。",
                  "不收费，也别拿去卖，整理一次挺费时间的。", "",
                  f"#{keyword} #表格模板 #效率工具"]
        validated = validate({
            "name": name,
            "audience": audience,
            "title": title,
            "highlight": "",
            "sub": "表头和数据都在\n改成自己的就能用",
            "stickers": ["可直接编辑", "源文件都在"],
            "categories": categories,
            "previews": data_previews(sheets),
            "keyword": keyword,
            "caption": "\n".join(line for line in lines if line is not None),
        }, "", [])
        # 校验会补足到 3 个分类，这里只保留资料里真实存在的表
        validated["categories"] = categories
        plans.append(validated)
    return plans


def fallback_plans(sheets: list[Sheet]) -> list[dict]:
    """模型不可用时的兜底：用规则分类 + 固定文案，保证界面永远有 3 套可选。"""
    from .pack import PREVIEW_COPY, categorize, is_attendance

    if not is_attendance(sheets):
        return _data_plans(sheets)

    from .pack import PREVIEW_COPY, categorize

    categories = [{"name": name, "desc": desc} for name, desc in categorize(sheets)]
    seeds = [
        ("HR 主推", "HR / 行政 专用", "考勤表别再\n手画了", "手画", "HR / 行政"),
        ("主管自管", "部门主管 / 组长", "带小团队\n考勤别乱", "考勤别乱", "部门主管 / 组长"),
        ("月末结算", "行政 / 财务 月末用", "月底考勤\n一次算清", "一次算清", "行政 / 财务"),
    ]
    previews = [
        dict(PREVIEW_COPY["auto"], formula='=COUNTIF(C4:N4,"√")  ← 出勤天数，月底自动汇总'),
        dict(PREVIEW_COPY["dept"], formula='=SUMIF(部门列,"行政部",出勤列)  ← 按部门汇总'),
        dict(PREVIEW_COPY["word"], formula=""),
    ]
    plans = []
    for index, (name, audience, title, highlight, target) in enumerate(seeds):
        lines = [title.replace("\\n", ""), ""]
        lines.append(f"每个月做考勤，最烦的不是算，是又要新建表、调格式、补公式。")
        lines.append("")
        lines.append(f"给{target}整理了一套现成的考勤表，按类型分好了：")
        for item in categories:
            lines.append(f"· {item['name']}：{item['desc']}")
        lines += ["", "图里放了几张预览，都能在包里找到。", "", "需要的话评论区扣「考勤」，我私信发你。",
                  "不收费，也别拿去卖，整理一次挺费时间的。", "",
                  "#HR #考勤表 #人事行政 #Excel模板 #行政 #职场干货"]
        plans.append(validate({
            "name": name,
            "audience": audience,
            "title": title,
            "highlight": highlight,
            "sub": "每个月新建表、调格式、补公式\n现成的版式，改个名字就能用",
            "stickers": ["出勤自动算", "A4 直接打"],
            "categories": categories,
            "previews": [dict(item) for item in previews],
            "keyword": "考勤",
            "caption": "\n".join(lines),
        }, "自动 公式", []))
    return plans


def make_plans(sheets: list[Sheet], data_dir: Path, count: int = 3) -> dict:
    facts = facts_text(sheets, data_dir)
    mainstream, fringe = scene_mix(sheets)
    message = PLAN_PROMPT.format(facts=facts, count=count, voice=VOICE)
    plans: list[dict] = []
    fallback_used = False
    for attempt in range(2):
        try:
            raw = llm.chat(
                [{"role": "system", "content": PLAN_SYSTEM}, {"role": "user", "content": message}],
                temperature=0.9, max_tokens=min(8000, 2400 + count * 1600),
            )
            data = llm.parse_json(raw)
        except Exception as error:  # 网络/限流/格式问题都不能让整条流程挂掉
            print(f"! 第 {attempt + 1} 次编排失败：{error}", flush=True)
            continue
        batch = [validate(plan, facts, fringe) for plan in (data.get("plans") or [])]
        plans = [plan for plan in batch if not plan.pop("_drop", False)]
        if len(plans) >= count:
            break
        message = PLAN_PROMPT.format(facts=facts, count=count, voice=VOICE) + (
            "\n上一轮出现了边缘模板主题，这次必须全部落在主流场景："
            + "、".join(mainstream)
            + "；禁止出现：" + "、".join(fringe or ["无"])
        )
    if not plans:
        print("! 模型多次失败，改用兜底方案", flush=True)
        plans = fallback_plans(sheets)
        fallback_used = True
    if len(plans) < count:
        fallback_used = True
        plans.extend(fallback_batch(sheets, count - len(plans), start=len(plans)))
    return {"facts": facts, "plans": plans[:count], "fallback": fallback_used}



BATCH_ANGLES = [
    "月末赶表", "月初接手", "新人入职", "多部门汇总", "迟到早退", "请假年假",
    "加班记录", "考勤符号", "公式统计", "A4 打印", "Word 签字", "小团队自管",
    "前台代管", "试用期", "跨月核对", "工资核算", "表格美化", "统计口径",
    "考勤规范", "员工自助", "主管审核", "模板替换", "出勤汇总", "排班衔接",
]

BATCH_PROMPT = """下面是对一份资料包的解析结果（事实清单）。不要凭空添加清单里没有的功能。

{facts}

现在要一次性产出 {count} 套「小红书图文方案」，用于批量发笔记：
- 每套挑一个不同的角度（从下面角度里选，尽量不重复）：
{angles}
- 已经用过的标题（不能重复，也不要换汤不换药）：{used}
- 人群可以轮换（HR / 行政 / 前台 / 部门主管 / 财务 / 小团队负责人），但不要出现边缘模板的行业
- 语气统一：直接、具体、像同行分享，不吹牛

每套输出字段：
- name：方案名（≤10 字，用角度概括，如“月末赶表”）
- audience：封面人群标签（≤14 字）
- title：封面主标题（≤14 字，可含 \\n 分两行，要有痛点或身份）
- highlight：必须出现在 title 里的高亮词（≤6 字）
- sub：封面副标题（≤30 字，可含 \\n；不要空括号占位符）
- stickers：两个具体卖点贴纸（各 ≤8 字）
- categories：5 个分类（name ≤10 字、desc ≤20 字，来自事实清单）
- previews：3 张预览页，每张 badge（≤8 字）、note（≤10 字）、headline（≤18 字）、
  bullets（2 条 ≤24 字）、steps（3 条 ≤10 字）、formula（可选 ≤30 字）
- keyword：评论区关键词（2-4 字）
- caption：小红书正文（300-500 字，开头抓人、中间列分类、结尾引导评论；不要出现“网盘、链接、微信、免费领取”）

只输出 JSON：{{"plans":[...]}}，plans 里恰好 {count} 套。
"""


def _title_key(plan: dict) -> str:
    return re.sub(r"\s+", "", plan.get("title", ""))


def fallback_batch(sheets: list[Sheet], count: int, start: int = 0) -> list[dict]:
    from .pack import PREVIEW_COPY, categorize

    categories = [{"name": name, "desc": desc} for name, desc in categorize(sheets)]
    audiences = ["HR / 行政 专用", "行政 / 前台代管", "部门主管 / 组长", "财务 / 工资核算", "小团队负责人"]
    previews = [
        dict(PREVIEW_COPY["auto"], formula='=COUNTIF(C4:N4,"√")  ← 出勤天数'),
        dict(PREVIEW_COPY["dept"], formula='=SUMIF(部门列,"行政部",出勤列)  ← 按部门汇总'),
        dict(PREVIEW_COPY["word"], formula=""),
    ]
    plans = []
    for index in range(count):
        angle = BATCH_ANGLES[(start + index) % len(BATCH_ANGLES)]
        audience = audiences[(start + index) % len(audiences)]
        title = f"{angle}\n一张表搞定"
        lines = [f"{angle}，别再从零画表格了。", "",
                 "每个月做考勤，最烦的不是算，是又要新建表、调格式、补公式。", "",
                 "整理了一套现成的考勤表，按类型分好了："]
        lines += [f"· {item['name']}：{item['desc']}" for item in categories]
        lines += ["", "图里放了几张预览，都能在包里找到。", "",
                  "需要的话评论区扣「考勤」，我私信发你。", "不收费，也别拿去卖，整理一次挺费时间的。", "",
                  "#HR #考勤表 #人事行政 #Excel模板 #行政 #职场干货"]
        plans.append(validate({
            "name": angle[:10],
            "audience": audience,
            "title": title,
            "highlight": "一张表搞定",
            "sub": "每个月新建表、调格式、补公式\n现成的版式，改个名字就能用",
            "stickers": ["出勤自动算", "A4 直接打"],
            "categories": categories,
            "previews": [dict(item) for item in previews],
            "keyword": "考勤",
            "caption": "\n".join(lines),
        }, "自动 公式", []))
    return plans


def _batch_call(facts: str, count: int, angles: list[str], used: list[str]) -> list[dict]:
    message = BATCH_PROMPT.format(
        facts=facts, count=count,
        angles="、".join(angles[:10]),
        used=" / ".join(used[-12:]) or "无",
    )
    raw = llm.chat(
        [{"role": "system", "content": PLAN_SYSTEM}, {"role": "user", "content": message}],
        temperature=0.95, max_tokens=700 + count * 1500,
    )
    return llm.parse_json(raw).get("plans") or []


def make_batch(sheets: list[Sheet], data_dir: Path, count: int = 12) -> dict:
    count = max(1, min(int(count), 30))
    facts = facts_text(sheets, data_dir)
    mainstream, fringe = scene_mix(sheets)

    # 每 2 套一组并发请求：单次输出更短，JSON 不会被 max_tokens 截断
    groups: list[dict] = []
    cursor = 0
    while cursor < count:
        need = min(2, count - cursor)
        offset = (len(groups) * 2) % len(BATCH_ANGLES)
        angles = (BATCH_ANGLES[offset:] + BATCH_ANGLES[:offset])[:need]
        used = [f"第{index + 1}组：{'、'.join(group['angles'])}" for index, group in enumerate(groups)]
        groups.append({"need": need, "angles": angles, "used": used})
        cursor += need

    results: dict[int, list[dict]] = {}
    results_lock = threading.Lock()

    def run(index: int, group: dict) -> tuple[int, list[dict], str]:
        last = ""
        for attempt in range(2):
            try:
                need = group["need"] if attempt == 0 else 1
                return index, _batch_call(facts, need, group["angles"][:need], group["used"]), ""
            except Exception as error:  # noqa: BLE001
                last = str(error)
                print(f"! 第 {index + 1} 组请求失败：{error}", flush=True)
        return index, [], last

    with ThreadPoolExecutor(max_workers=min(3, len(groups))) as pool:
        futures = [pool.submit(run, index, group) for index, group in enumerate(groups)]
        for future in as_completed(futures):
            index, plans, _ = future.result()
            with results_lock:
                results[index] = plans
            done = min(sum(len(value) for value in results.values()), count)
            print(f"编排进度 {done}/{count}", flush=True)

    plans: list[dict] = []
    seen_titles: set[str] = set()
    for index in range(len(groups)):
        for plan in results.get(index, []):
            plan = validate(plan, facts, fringe)
            if plan.pop("_drop", False):
                continue
            key = _title_key(plan)
            if key in seen_titles:
                continue
            seen_titles.add(key)
            plans.append(plan)
            if len(plans) >= count:
                break
        if len(plans) >= count:
            break

    fallback_used = len(plans) < count
    if fallback_used:
        print(f"! 模型只给出 {len(plans)} 套，其余用兜底补齐", flush=True)
        plans.extend(fallback_batch(sheets, count - len(plans), start=len(plans)))
    return {"facts": facts, "plans": plans[:count], "fallback": fallback_used}


def main(argv: list[str] | None = None) -> int:
    import warnings
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser("xhs.planner", description="资料包 → 模型编排方案")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=3, help="生成几套方案（1-6）")
    args = parser.parse_args(argv)

    data_dir = Path(args.data).expanduser().resolve()
    sheets = parse_pack(data_dir)
    if not sheets:
        print("× 没解析到资料")
        return 2
    result = make_plans(sheets, data_dir, max(1, min(int(args.count), 6)))
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("方案已生成：", out_path)
    for index, plan in enumerate(result["plans"], 1):
        print(f"  {index}. {plan['name']}｜{plan['audience']}｜{plan['title'].replace(chr(10), ' / ')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
