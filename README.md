# 小红书批量工作台（DSH Desktop 插件）

资料进 → **选题清单** → 勾选 → 按模板出图文。版式固定，同一模板同一配色，输出稳定不抽卡。

## 安装

```sh
dsh plugin --profile web add dsh-xhs-batch-studio   # 已发 npm 时
dsh plugin --profile web add Nanfeng0108/dsh-xhs-batch-studio   # 或直接用 GitHub 仓库
```

DSH Desktop 里也可以走 **插件 → 添加插件**，填包名 / GitHub 地址 / 本地目录。

装完重启一次，左侧出现「小红书批量工作台」。**第一次用要点「准备环境」**：
建独立 venv、装 Python 依赖、下载 Chromium（约 150 MB），一两分钟，之后不再需要。

需要 Python 3.10+；文案要一个模型 key（DSH 里配好 DeepSeek，或设 `XHS_USE_DSH_MODEL=1` 借用当前 provider）。

## 工作流

```
① 导入资料（Excel / PDF / Word / CSV）
        ↓  解析 + OCR + 提炼
② 选题清单（可编辑标题/角度，勾选要写的）
        ↓  写作模板 + 版式模板
③ 成品（文案 + 封面 + 内页图 + 总清单）
```

**第一步只提炼选题，不写文案**——你可以先看选题对不对，改标题、改角度、只留想写的几个，再进第二步。换一批不会动资料。

## 模板（技能）

顶部「模板 / 技能」里可以：

- 选内置写作模板：干货清单 / 教程步骤 / 避坑指南 / 测评对比 / 观点共鸣 / 好物合集
- 新建自己的写作模板：节数范围、每节行数、每行字数、标题规则、开头钩子、结尾引导、语气、**补充要求**（可直接粘贴你自己的写作 skill / 规则）
- 编辑、另存、删除自定义模板（内置的只能另存）
- 查看版式模板：封面 3 种（各 2 个构图变体）、内页 2 种、金句页、尾页

写作模板存在 `$DSH_HOME/xhs-batch-studio/templates/writing/*.json`，可以直接改文件，也可以带进版本管理。

## 出图为什么稳定

- 封面 3 种固定版式（大字报 / 杂志留白 / 便签），每种各有 a/b 两个构图变体，全部是 HTML 模板渲染，**不调用任何图片生成模型**
- 内页 2 种固定版式（编号卡片 / 时间轴），每种各有 a/b 构图变体；要点行按关键词配线性图标，没命中退回圆点；字号按内容长度自适应，不会溢出
- 同一模板 + 同一配色 + 同一文案 = 完全一致的图；改文案只会改变文字，不会改变版式
- 篇与篇之间的差异（强调色、封面构图）由标题哈希决定，不是随机数：同一篇永远同一张图，整批又不会撞脸
- 页面分角色：封面 → 要点卡 → 金句页 → 尾页（CTA + 标签），避免整组图一个模子
- 尺寸固定 1080×1440（小红书 3:4 竖版），导出 2 倍清晰度

## 关于账号

**不需要登录任何账号。** 生成用的是本机 DSH 已配置的 DeepSeek 密钥，出图不联网。设置里唯一的「图上署名」只是印在图片角落的文字，可留空。

## 参数

| 参数 | 说明 |
|---|---|
| 内容方向 | 可选，用来收敛选题，如「小户型收纳」 |
| 选题数量 | 一次提炼多少个选题（最终生成几篇由你勾选决定） |
| 写作模板 | 决定文案结构与语气 |
| 封面 / 内页版式 | 决定图片排版 |
| 配色 | 米白朱红 / 暖纸棕 / 浅绿 / 深色金 |
| 色相范围 | `narrow` 同族轮换（默认）/ `wide` 跨色相 |
| 内页张数 | 每篇要点卡 2-6 张，另加封面、金句页、尾页 |
| 图上署名 | 可留空 |

## 首次使用

第一次点「提炼选题」时，插件会在后台准备 Python 环境与浏览器渲染器（约 1-2 分钟，有实时进度），之后不再需要。前置条件：本机 `python3` 可用（3.10+）。

## 数据位置

```
$DSH_HOME/xhs-batch-studio/
├── runs/<运行编号>/         资料、topics.json、notes.json、成品目录、index.xlsx
├── uploads/                 上传的原始资料
├── templates/writing/       自定义写作模板
└── venv/                    插件自用 Python 环境
```

本机 `$DSH_HOME` = `~/Library/Application Support/dsh-desktop/harness`。卸载插件不删除这些数据。

## 打开方式

重启 DSH Desktop 后，展开左侧栏 → 点左上角「工作台」右侧的当前工作台名称 → 选「小红书批量工作台」。

## 目录结构

```
package.json           插件声明（dsh.bundle / dsh.client）
cordis.patch.yml       服务端入口插入插件树
dsh/index.js           服务端：/api/xhs-batch/*（上传、分析、生成、模板、产物）
lib/client.js          客户端：三步式工作台面板
python/xhs/analyze.py  第一阶段：资料 → 选题
python/xhs/build.py    第二阶段：选题 → 文案 → 出图
python/xhs/writing.py  写作模板定义与读写
python/xhs/templates/  封面 / 内页版式模板
python/zip_run.py      打包下载
tools/                 本地自测与预览截图脚本（不打进包）
```

## 本地自测

```bash
node tools/test-host.mjs env       # 路由 + 环境 + 模板目录
node tools/test-host.mjs prepare   # 准备 Python 环境
node tools/test-host.mjs all       # 上传样例 → 提炼选题 → 生成两篇 → 校验图片/zip/xlsx
```

## 许可

MIT
