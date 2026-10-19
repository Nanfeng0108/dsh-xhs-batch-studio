# 内置字体

渲染不依赖系统字体：同一份字体文件 → 任何机器上排版一致。

| 文件 | 字族 | 用途 | 来源 |
|---|---|---|---|
| `noto-400.woff2` | Noto Sans SC | 正文 | Google Fonts |
| `noto-700.woff2` | Noto Sans SC | 标签、小标题 | Google Fonts |
| `noto-900.woff2` | Noto Sans SC | 大标题、强调 | Google Fonts |
| `archivo-600.woff2` | Archivo | 西文、数字 | Google Fonts |
| `archivo-800.woff2` | Archivo | 编号水印 | Google Fonts |

下载自 jsDelivr 上的 Fontsource 分发包（`@fontsource/noto-sans-sc@5.0.0`、`@fontsource/archivo@5.0.0`），
Noto 取的是 `chinese-simplified` 子集（7898 字形，覆盖 GB2312 一级汉字 3751/3755）。

补字办法：缺字时浏览器回落到 `PingFang SC`（模板 font stack 的第三顺位），不会出现方块。

## 为什么不用系统字体

苹方（PingFang SC）最粗只到 Semibold（600）。改版前模板写的是 `font-weight:900`，
实测 900 与 600 渲染结果逐像素相同——**大标题一直是 Semibold**，这是封面看着“软”的根因。
Noto Sans SC 有真正的 Black（900），标题才立得住。

## 许可

两者均为 SIL Open Font License 1.1，可商用、可随包分发。全文见 `OFL.txt`。
