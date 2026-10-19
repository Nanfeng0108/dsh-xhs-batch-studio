// 生成离线预览页：真实客户端代码 + 假后端 + 真实出图产物，供截图核对完整流程。
import { readFile, writeFile, readdir } from 'node:fs/promises'
import { join, resolve } from 'node:path'

const runDir = process.argv[2]
const outHtml = resolve(process.argv[3] || 'tools/preview.html')
if (!runDir) throw new Error('usage: node tools/make-preview.mjs <runDir> [out.html]')

const entries = await readdir(runDir, { withFileTypes: true })
const dirs = entries.filter((e) => e.isDirectory() && /^\d{3}-/.test(e.name)).map((e) => e.name).sort()
const notes = []
for (const dir of dirs) {
  const caption = await readFile(join(runDir, dir, 'caption.txt'), 'utf8').catch(() => '')
  const files = (await readdir(join(runDir, dir)).catch(() => [])).filter((f) => /\.png$/i.test(f)).sort()
  notes.push({
    dir,
    title: caption.split('\n')[0].trim(),
    caption,
    images: files.map((f) => ({ name: f, url: `file://${join(runDir, dir, f)}` })),
  })
}

const catalog = {
  writing: {
    listicle: { id: 'listicle', name: '干货清单', desc: 'N 条要点，每条先给结论再给依据', builtin: true, sections: [3, 5], lines: [2, 4], line_max: 22, tags: [6, 8] },
    tutorial: { id: 'tutorial', name: '教程步骤', desc: '按顺序讲清怎么做，每步一个动作', builtin: true, sections: [3, 6], lines: [2, 4], line_max: 22, tags: [6, 8] },
    pitfall: { id: 'pitfall', name: '避坑指南', desc: '先列错误做法，再给正确做法', builtin: true, sections: [3, 5], lines: [2, 4], line_max: 22, tags: [6, 8] },
    'my-style': { id: 'my-style', name: '我的爆款结构', desc: '自建模板：先结论后故事', builtin: false, sections: [4, 5], lines: [2, 3], line_max: 20, tags: [6, 8] },
  },
  covers: { poster: '大字报（色块 + 超大标题）', magazine: '杂志留白（细线 + 大留白）', note: '便签手账（米色纸 + 标记笔）' },
  cards: { index: '编号卡片（圆点 + 要点列表）', timeline: '时间轴（竖线 + 步骤编号）' },
}

const topics = [
  { id: 't01', title: '冬天脸越洗越干？5 步顺序自查', angle: '按顺序讲清每步用量', audience: '干皮上班族', key_facts: ['水温 32-35℃', '一元硬币大小', '面霜黄豆大小×2'], source: '护肤步骤!行2-行6', selected: true },
  { id: 't02', title: '干皮 5 个误区，第 3 个我天天在犯', angle: '反常识纠错', audience: '干皮/敏感肌', key_facts: ['面膜一周 2-3 次', '干皮 2-3 周去一次角质', '喷雾后 30 秒内涂霜'], source: '干皮误区!行2-行6', selected: true },
  { id: 't03', title: '神经酰胺、玻尿酸、A醇，谁该用', angle: '成分对号入座', audience: '成分党', key_facts: ['烟酰胺 5% 起可能刺激', 'A醇夜间用', '玻尿酸需封闭'], source: '成分速查!行2-行6', selected: true },
  { id: 't04', title: '小户型别急着买收纳盒，先做 3 件事', angle: '先减法再收纳', audience: '租房/小户型', key_facts: ['闲置约占 31%', '储物量提升 40%', '台面只留 5 件'], source: '第1页', selected: true },
  { id: 't05', title: '60㎡ 两居，收纳顺序反了越收越乱', angle: '动线优先', audience: '小户型家庭', key_facts: ['按动线不按品类', '柜内隔板可调', '顶部放换季'], source: '第2页', selected: false },
]

const mock = {
  env: { ok: true, ready: true, python: '/tmp/venv/bin/python', root: '~/xhs-batch-studio', runs: [{ runId: '20261018081659', topics: 5, notes: 2 }], catalog },
  topicsResult: { ok: true, job: { id: 'a1', kind: 'analyze', status: 'done', stage: '选题已生成', progress: 100, lines: ['[1/1] 解析资料', '  共 3 个文件 / 1511 字', '提炼选题', '  01. ' + topics[0].title, '  02. ' + topics[1].title], elapsed: 4.2, result: { runId: '20261018081659', topics } } },
  genResult: { ok: true, job: { id: 'g1', kind: 'generate', status: 'done', stage: '完成', progress: 100, lines: ['[1/4] 写文案', '[2/4] 合规检查与查重', '[3/4] 按模板渲染图片', '[4/4] 写文件与索引表'], elapsed: 13.6, result: { runId: '20261018081659', notes, indexUrl: '#', zipUrl: '#', report: { elapsed_sec: 13.6, notes: notes.length, template: { writing: '干货清单', cover: 'poster', card: 'index' } } } } },
}

const client = await readFile(new URL('../lib/client.js', import.meta.url), 'utf8')
const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;background:#f4eef0}#root{height:100vh}</style>
<script src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
</head><body><div id="root"></div>
<script>window.__ModuleLoader__={load:(m)=>{window.__mod=m}}</script>
<script>${client}</script>
<script>
  const MOCK = ${JSON.stringify(mock)}
  const realFetch = window.fetch
  window.fetch = async (url, init) => {
    const u = String(url)
    const respond = (data) => new Response(JSON.stringify(data), {status:200, headers:{'content-type':'application/json'}})
    if (u.includes('/env')) return respond(MOCK.env)
    if (u.includes('/upload')) {
      const name = decodeURIComponent((u.split('name=')[1] || 'file').split('&')[0])
      return respond({ok:true, id:'u-' + name, name, size: 231477})
    }
    if (u.includes('/analyze')) return respond({ok:true, jobId:'a1'})
    if (u.includes('/generate')) return respond({ok:true, jobId:'g1'})
    if (u.includes('/job')) return respond(u.includes('a1') ? MOCK.topicsResult : MOCK.genResult)
    if (u.includes('/reveal')) return respond({ok:true})
    if (u.includes('/templates')) return respond({ok:true, catalog: MOCK.env.catalog})
    return realFetch(url, init)
  }
  const mod = window.__mod.factory((name) => { if (name === 'react') return React; throw new Error(name) })
  const ctx = { effect: (fn) => fn(), desktopWorkbenches: { register: (d, C) => { window.__Panel = C; return () => {} } } }
  mod.apply(ctx)
  const fakeConversation = React.createElement('div', {
    style: { padding: '16px', fontSize: '13px', color: '#4a3d44', lineHeight: 1.8, flex: 1, minHeight: 0, overflow: 'auto' },
  },
    React.createElement('div', { style: { background: '#f7f1f3', borderRadius: '10px', padding: '10px 12px', marginBottom: '10px' } }, '这是宿主注入的原生对话区（真实环境里就是你和 AI 的会话）。'),
    React.createElement('div', { style: { background: '#f2fbf5', borderRadius: '10px', padding: '10px 12px' } }, '左边的工作台照常操作，需要改文案时在这里说一声，不用切出去。'))
  const fakeService = { currentSession: () => 's1', ownsSession: () => { throw new Error('Workbench registration requires a client package entry name.') }, defaultWorkspace: () => ({ workspaceId: 'w1' }), newSession: async () => {} }
  ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(window.__Panel, { service: fakeService, entry: {}, active: true, conversation: fakeConversation }))
</script></body></html>`
await writeFile(outHtml, html)
console.log('preview written:', outHtml, 'notes:', notes.length)
