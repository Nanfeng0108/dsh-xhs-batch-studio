"""写作模板（可理解为“文案技能”）。

内置模板是固定的结构与语气约束；自定义模板放在数据目录 templates/writing/*.json，
字段与内置模板一致，同 id 时覆盖内置。
"""
from __future__ import annotations

import json
from pathlib import Path

BUILTIN: dict[str, dict] = {
    "listicle": {
        "id": "listicle",
        "name": "干货清单",
        "desc": "N 条要点，每条先给结论再给依据，适合知识点密集的资料",
        "builtin": True,
        "title_rule": "≤20 字，带具体数字或人群词，如「5 步」「干皮」「新手」",
        "sections": [3, 5],
        "lines": [2, 4],
        "line_max": 22,
        "heading_max": 10,
        "tags": [6, 8],
        "hook": "一句反常识结论或扎心反问，不要客套开场",
        "cta": "收藏/照着做/自测型，一句话",
        "tone": "像在群里吐槽完顺手分享解决办法：口语、短句、有情绪但有用",
        "emoji": "全文 8-15 个：✅ 正确做法 ❌ 错误做法 ⚠️ 注意 💡 技巧 📌 重点 ✨ 收尾，各司其职",
        "extra": "",
    },
    "tutorial": {
        "id": "tutorial",
        "name": "教程步骤",
        "desc": "按顺序讲清怎么做，每步一个动作 + 一个注意点",
        "builtin": True,
        "title_rule": "≤20 字，突出「几步 / 顺序 / 照着做」",
        "sections": [3, 6],
        "lines": [2, 4],
        "line_max": 22,
        "heading_max": 12,
        "tags": [6, 8],
        "hook": "先说做错的代价，再说正确顺序",
        "cta": "让读者按步骤执行并回来反馈",
        "tone": "像手把手带同事走一遍：动词开头、每步点一个坑、口语",
        "emoji": "每步前 1 个序号符号（1️⃣ 或 ✅），⚠️ 标注意点，全文 8-14 个",
        "extra": "每一节对应一个动作步骤，标题用「第 N 步 · 动作」。",
    },
    "pitfall": {
        "id": "pitfall",
        "name": "避坑指南",
        "desc": "先列常见错误做法，再给正确做法，反差感强",
        "builtin": True,
        "title_rule": "≤20 字，用「越…越…」「别…」制造反差",
        "sections": [3, 5],
        "lines": [2, 4],
        "line_max": 22,
        "heading_max": 12,
        "tags": [6, 8],
        "hook": "直接点出大家都在犯的那个错",
        "cta": "让读者对照自查，评论区报情况",
        "tone": "犀利但不指责：先替读者骂两句那个坑，再给做法",
        "emoji": "❌ 标错误做法，✅ 标正确做法，⚠️ 标代价，全文 8-15 个",
        "extra": "每节标题写成「误区N · 错误做法」，正文第一行给正确做法。",
    },
    "review": {
        "id": "review",
        "name": "测评对比",
        "desc": "同一维度横向对比几个选项，给出选择建议",
        "builtin": True,
        "title_rule": "≤20 字，点明对比对象和结论",
        "sections": [3, 5],
        "lines": [2, 4],
        "line_max": 24,
        "heading_max": 12,
        "tags": [6, 8],
        "hook": "先给结论，再说凭什么这么选",
        "cta": "按人群给建议，让读者对号入座",
        "tone": "客观、给依据、敢下结论",
        "emoji": "✅ 标优点 ⚠️ 标缺点 📌 标结论，全文 6-12 个，克制但不为 0",
        "extra": "对比维度要统一，每节讲一个维度。",
    },
    "opinion": {
        "id": "opinion",
        "name": "观点共鸣",
        "desc": "一个有立场的观点 + 三段论据，适合有情绪价值的资料",
        "builtin": True,
        "title_rule": "≤20 字，一句话立场，可用「我不建议…」",
        "sections": [3, 5],
        "lines": [2, 4],
        "line_max": 22,
        "heading_max": 12,
        "tags": [5, 8],
        "hook": "第一句就把立场亮出来",
        "cta": "邀请不同意见，制造讨论",
        "tone": "有态度但讲道理，不极端",
        "emoji": "🔥 标观点 📌 标重点，全文 6-12 个",
        "extra": "论据必须来自资料，不要编个人故事。",
    },
    "collection": {
        "id": "collection",
        "name": "好物合集",
        "desc": "按场景/需求分组推荐，每组给选择理由",
        "builtin": True,
        "title_rule": "≤20 字，带场景和数量",
        "sections": [3, 5],
        "lines": [2, 4],
        "line_max": 22,
        "heading_max": 12,
        "tags": [6, 8],
        "hook": "先说明什么情况下需要这份清单",
        "cta": "让读者按预算/场景挑一个",
        "tone": "像朋友安利，说清适用和不适用",
        "emoji": "🛒 标单品 ✅ 标推荐理由 ⚠️ 标踩雷，全文 8-15 个",
        "extra": "不要编造价格和销量，资料里没有就不写。",
    },
}

DEFAULT_ID = "listicle"
LAYOUT_COVERS = {
    "poster": "大字报（色块 + 超大标题）",
    "magazine": "杂志留白（细线 + 大留白）",
    "note": "便签手账（米色纸 + 标记笔）",
}
LAYOUT_CARDS = {
    "index": "编号卡片（圆点 + 要点列表）",
    "timeline": "时间轴（竖线 + 步骤编号）",
}


def _normalize(raw: dict) -> dict:
    base = dict(BUILTIN[DEFAULT_ID])
    base.update({k: v for k, v in raw.items() if v is not None})
    base["builtin"] = bool(raw.get("builtin", False))
    base["id"] = str(base.get("id") or "custom")
    base["name"] = str(base.get("name") or base["id"])
    base["desc"] = str(base.get("desc") or "")
    for key in ("sections", "lines", "tags"):
        value = base.get(key)
        if not (isinstance(value, (list, tuple)) and len(value) == 2):
            base[key] = BUILTIN[DEFAULT_ID][key]
        else:
            base[key] = [int(value[0]), int(value[1])]
    for key in ("line_max", "heading_max"):
        base[key] = int(base.get(key) or BUILTIN[DEFAULT_ID][key])
    for key in ("title_rule", "hook", "cta", "tone", "emoji", "extra"):
        base[key] = str(base.get(key) or BUILTIN[DEFAULT_ID][key])
    return base


def load_all(templates_dir: Path | None = None) -> dict[str, dict]:
    """内置 + 自定义。自定义同 id 覆盖内置。"""
    merged = {key: dict(value) for key, value in BUILTIN.items()}
    if templates_dir:
        folder = Path(templates_dir) / "writing"
        if folder.exists():
            for file in sorted(folder.glob("*.json")):
                try:
                    raw = json.loads(file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(raw, dict):
                    continue
                template = _normalize(raw)
                merged[template["id"]] = template
    return merged


def get(template_id: str, templates_dir: Path | None = None) -> dict:
    all_templates = load_all(templates_dir)
    return all_templates.get(template_id) or all_templates[DEFAULT_ID]


def save(template: dict, templates_dir: Path) -> dict:
    folder = Path(templates_dir) / "writing"
    folder.mkdir(parents=True, exist_ok=True)
    normalized = _normalize(template)
    normalized["builtin"] = False
    if normalized["id"] in BUILTIN:
        raise ValueError("自定义模板不能用内置模板的 id，请换一个名字")
    (folder / f"{normalized['id']}.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return normalized


def delete(template_id: str, templates_dir: Path) -> bool:
    if template_id in BUILTIN:
        raise ValueError("内置模板不能删除")
    file = Path(templates_dir) / "writing" / f"{template_id}.json"
    if file.exists():
        file.unlink()
        return True
    return False
