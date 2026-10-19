"""合规检查：平台高风险词、广告法极限词。只做提示与低风险替换，不擅自改写语义。"""
from __future__ import annotations

import re

# 广告法/平台常见绝对化用语（命中即提示）
ABS_WORDS = [
    "最好", "最佳", "最优", "最强", "最有效", "最快", "最便宜", "最高级", "最低价", "最先进",
    "No.1", "NO.1", "TOP1", "顶级", "顶尖", "极致", "国家级", "世界级", "全球首创",
    "绝对", "100%", "百分百", "永久", "根治", "彻底解决", "包治", "零风险", "无副作用",
    "万能", "唯一", "史上", "全网最低", "销量第一", "秒杀", "立即见效", "立竿见影",
]

# 医疗/金融/功效类高危词（命中标红，需人工确认）
HIGH_RISK = [
    "治疗", "治愈", "疗效", "药效", "抗癌", "降血压", "降血糖", "消炎", "杀菌",
    "稳赚", "保本", "暴利", "躺赚", "年化", "返利", "内幕消息",
    "医美级", "药妆", "处方", "替代药物",
]

# 只做安全替换的少数词
SAFE_REPLACE = {
    "最好": "很推荐", "最佳": "很合适", "最强": "很强", "最有效": "比较有效",
    "第一": "靠前", "NO.1": "头部", "No.1": "头部", "TOP1": "头部",
    "绝对": "真的", "100%": "基本都", "百分百": "基本都",
    "永久": "长久", "根治": "缓解", "万能": "通用", "唯一": "少见",
}


# "第一步/第一次" 是顺序表达，不构成绝对化用语；只拦真正的排名/优劣用法
FIRST_PATTERNS = [
    (re.compile(r"第一(?!步|次|时间|天|口|眼|反应|感觉|印象|份|层|遍|晚|早)"), "第一"),
    (re.compile(r"销量第一|排名第一|全国第一|全网第一|行业第一"), "排名类用语"),
]


def scan(text: str) -> list[dict]:
    hits: list[dict] = []
    abs_hit = any(w in text for w in ABS_WORDS)
    for pat, word in FIRST_PATTERNS:
        if not pat.search(text):
            continue
        if word == "第一" and any("第一" in w for w in ABS_WORDS if w in text):
            continue
        if word == "排名类用语" and abs_hit:
            continue
        hits.append({"level": "warn", "word": word, "kind": "极限词"})
    for w in ABS_WORDS:
        if w in text:
            hits.append({"level": "warn", "word": w, "kind": "极限词"})
    for w in HIGH_RISK:
        if w in text:
            hits.append({"level": "high", "word": w, "kind": "高危词"})
    # 手机号/微信号
    if re.search(r"1[3-9]\d{9}", text) or re.search(r"(微信|VX|vx|wx)[:：]?\s*[A-Za-z0-9_-]{5,}", text):
        hits.append({"level": "high", "word": "联系方式", "kind": "导流风险"})
    return hits


def autofix(text: str) -> tuple[str, list[str]]:
    used = []
    for k, v in SAFE_REPLACE.items():
        if k in text:
            text = text.replace(k, v)
            used.append(f"{k}→{v}")
    return text, used


def note_fields(note: dict) -> str:
    parts = [note.get("title", ""), note.get("hook", ""), note.get("cta", "")]
    for s in note.get("sections", []):
        parts.append(s.get("heading", ""))
        parts.extend(s.get("lines", []))
    for c in note.get("cards", []):
        parts.append(c.get("title", ""))
        parts.extend(c.get("lines", []))
    for t in note.get("tags", []):
        parts.append(t)
    cover = note.get("cover", {})
    parts.extend([cover.get("title", ""), cover.get("subtitle", ""), cover.get("kicker", "")])
    return "\n".join(p for p in parts if p)
