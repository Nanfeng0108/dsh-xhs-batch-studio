# 上架 DSH 插件社区（dsh-market）

市场里的条目来自精选列表 [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin)，
不是直接扫 npm。条目合入后，插件会同时出现在：

- [dshmarket.com](https://dshmarket.com)
- 目录站 [awesome-dsh-plugin.com](https://awesome-dsh-plugin.com)
- DSH 客户端的「插件 → 发现」

## 硬性门槛（缺一条投了也会被打回）

| 要求 | 本仓库状态 |
| --- | --- |
| `package.json` 声明 `dsh.bundle` | ✅ 已有 `dsh.bundle.patch` |
| 仓库创建满 1 天 | ⏳ push 后等一天 |
| 仓库加 `dsh-plugin` topic | ⏳ 建仓库后在 About 里加 |
| 一个条目一个 yml 文件 | ✅ 模板见 `dist/awesome-dsh-plugin-submission/` |

## 五步

1. **建仓库并推上去**

   ```sh
   cd xhs-plugin
   git init -b main
   git add -A
   git commit -m "feat: 小红书批量工作台 3.6.6"
   gh repo create dsh-xhs-batch-studio --public --source=. --push
   gh repo edit --add-topic dsh-plugin
   ```

   仓库要公开，否则市场拉不到源码核对。

2. **把 OWNER 换成你的 GitHub 用户名**

   ```sh
   tools/set-repo.sh yourname
   ```

   会改写 `package.json` 的 repository / bugs / homepage、README 里的链接、以及投稿 yml 的 url。

3. **（可选，强烈建议）发 npm**

   ```sh
   npm login
   npm publish
   ```

   发了之后市场能显示版本号、做版本更新检测，用户也能直接
   `dsh plugin --profile web add dsh-xhs-batch-studio`。
   不发也能上架，只是更新检测退化成对比 git HEAD。

4. **提 PR**

   把 `dist/awesome-dsh-plugin-submission/data/plugins/OWNER__dsh-xhs-batch-studio.yml`
   改名成 `<你的用户名>__dsh-xhs-batch-studio.yml`，放进
   awesome-dsh-plugin 仓库的 `data/plugins/`，开 PR。

5. **等一天**，站点与市场会自动收录；之后 push 新 commit 不用重新投稿。

## 投稿时会被问到、提前想清楚的三件事

- **体积**：包 4.9 MB，其中 4.8 MB 是中文字体（Noto Sans SC 三个字重）。审核会看是否必要——理由是「不依赖用户机器上装了什么字体，出图才稳定」。
- **首跑成本**：第一次用要点「准备环境」，会建 venv、`pip install`、下 Chromium（约 150 MB）。README 必须写这一条，否则差评。
- **宿主依赖**：界面依赖 DSH Desktop 自带的工作台容器 `dsh-desktop-workbenches`。没装这个的宿主里，插件能装上但看不到界面——描述里要写明「DSH Desktop 工作台插件」。

## 描述写法参考（市场卡片只显示一两行）

> 把一批 Excel / PDF / Word 资料变成小红书图文：先提炼选题让你勾选，再按模板出封面和内页，
> 最后给一份索引表。版式固定、同一份输入每次出图完全一样。

不要写「AI 驱动」「颠覆」这类词，审核对照源码核对功能，夸大描述会被打回。
