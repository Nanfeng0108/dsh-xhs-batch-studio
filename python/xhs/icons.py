"""要点行的小图标：按关键词匹配，匹配不到就不画。

不追求图标齐全——宁可少画，也不要给「多喝水」配一个毫无关系的图形。
命中就替换掉原来的圆点，没命中保持圆点：视觉上仍然是同一套语言。
"""
from __future__ import annotations

_SVG = '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{}</svg>'

# 关键词 → 图形。顺序有意义：越具体的越靠前
_SHAPES: list[tuple[tuple[str, ...], str]] = [
    (("防晒", "太阳", "紫外线", "晒", "出门"), '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>'),
    (("水温", "温度", "℃", "热水", "冷水"), '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/>'),
    (("洁面", "洗脸", "水", "拍打", "湿敷", "精华", "点涂", "爽肤"), '<path d="M12 3c3.1 4 5.8 7 5.8 10.2a5.8 5.8 0 0 1-11.6 0C6.2 10 8.9 7 12 3z"/>'),
    (("分钟", "小时", "时间", "早上", "晚上", "提前", "频率", "次"), '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>'),
    (("预算", "价格", "元", "块", "钱", "成本", "花费"), '<circle cx="12" cy="12" r="8.5"/><path d="M9 9h6M9 12h6M12 9v6"/><path d="M9.2 15.5 12 12l2.8 3.5"/>'),
    (("kg", "克", "重量", "负重", "背"), '<path d="M4.5 8h15l-1.8 12H6.3L4.5 8z"/><path d="M12 4v4M9 4h6"/>'),
    (("尺寸", "厘米", "cm", "米", "㎡", "面积", "厘米", "宽", "高", "长"), '<rect x="3" y="9" width="18" height="6" rx="1"/><path d="M7 9v2M11 9v2M15 9v2M19 9v2"/>'),
    (("收纳", "盒子", "柜", "抽屉", "装箱", "空间", "隔板"), '<path d="M3 8l9-4 9 4v8l-9 4-9-4V8z"/><path d="M3 8l9 4 9-4M12 12v8"/>'),
    (("顺序", "首先", "然后", "最后", "步骤"), '<path d="M4 7h10M4 12h14M4 17h8"/><path d="M17 5l3 2-3 2"/>'),
]


def icon_for(text: str) -> str:
    """返回内联 SVG，未命中返回空串。"""
    value = str(text or "")
    for keywords, shape in _SHAPES:
        if any(keyword in value for keyword in keywords):
            return _SVG.format(shape)
    return ""
