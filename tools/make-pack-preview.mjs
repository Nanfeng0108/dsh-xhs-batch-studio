// 资料包模式预览：真实客户端 + 假后端 + 真实出图产物
import { readFile, readdir } from 'node:fs/promises'
import { join, resolve } from 'node:path'

const runDir = resolve(process.argv[2] || '../out/编排-方案1')
const plansFile = resolve(process.argv[3] || '../out/plans.json')
const outHtml = resolve(process.argv[4] || 'tools/pack-preview.html')
const batchDir = resolve(process.argv[5] || '../out/batch-test')

const plans = JSON.parse(await readFile(plansFile, 'utf8')).plans
const files = (await readdir(runDir)).filter((f) => /^0\d\.png$/.test(f)).sort()
const caption = await readFile(join(runDir, 'caption.md'), 'utf8').catch(() => '')
const images = files.map((f) => ({ name: f, url: `file://${join(runDir, f)}` }))

let batch = null
try {
  const manifest = JSON.parse(await readFile(join(batchDir, 'manifest.json'), 'utf8'))
  batch = {
    runId: '20261018190001',
    count: manifest.notes.length,
    zipUrl: '#',
    notes: manifest.notes.map((note) => ({
      ...note,
      images: note.images.map((rel) => ({ name: rel.split('/').pop(), url: `file://${join(batchDir, rel)}` })),
    })),
  }
} catch { batch = null }

const batchCover = batch?.notes?.[0]?.images?.[0]?.url || images[0].url
const historyRuns = [
  { runId: '20261018190001', kind: 'batch', title: batch?.notes?.[0]?.title || '批量笔记', count: batch?.notes?.length || 6, when: '2026-10-18 19:00', thumb: batchCover },
  { runId: '20261018185600', kind: 'pack', title: plans[0]?.title?.replace(/\n/g, ' ') || '资料包笔记', count: images.length, when: '2026-10-18 18:56', thumb: images[0].url },
  { runId: '20261018170000', kind: 'notes', title: '考勤表怎么做才不加班', count: 0, notes: 6, topics: 8, when: '2026-10-18 17:00', thumb: '' },
]

const env = {
  ok: true, ready: true, python: '/tmp/venv/bin/python', root: '~/xhs-batch-studio',
  runs: historyRuns,
  catalog: { writing: { listicle: { id: 'listicle', name: '干货清单' } }, covers: { poster: '大字报' }, cards: { index: '编号卡片' } },
}

const mock = {
  env,
  analyze: { ok: true, job: { id: 'pa1', kind: 'pack-analyze', status: 'done', stage: '方案已生成', progress: 100, lines: ['资料：模板01.xlsx', '解析完成', '生成 3 套方案'], elapsed: 12.4, result: { runId: '20261018190001', plans } } },
  batch: batch ? { ok: true, job: { id: 'pb1', kind: 'pack-batch', status: 'done', stage: '完成', progress: 100, lines: ['编排 6 套方案', '[6/6] 迟到早退'], elapsed: 80.2, result: batch } } : null,
  generate: { ok: true, job: { id: 'pg1', kind: 'pack-generate', status: 'done', stage: '完成', progress: 100, lines: ['按方案出图', 'rendered 06.png', '完成'], elapsed: 9.2, result: { runId: '20261018190001', mode: 'pack', images, caption, zipUrl: '#' } } },
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
  window.fetch = async (url) => {
    const u = String(url)
    const respond = (data) => new Response(JSON.stringify(data), {status:200, headers:{'content-type':'application/json'}})
    if (u.includes('/env')) return respond(MOCK.env)
    if (u.includes('/upload')) {
      const name = decodeURIComponent((u.split('name=')[1] || 'file').split('&')[0])
      return respond({ok:true, id:'u-' + name, name, size: 231477})
    }
    if (u.includes('pack/analyze')) return respond({ok:true, jobId:'pa1'})
    if (u.includes('pack/generate')) return respond({ok:true, jobId:'pg1'})
    if (u.includes('pack/batch')) return respond(MOCK.batch ? {ok:true, jobId:'pb1'} : {ok:false, error:'no batch fixture'})
    if (u.includes('/job')) {
      if (u.includes('pa1')) return respond(MOCK.analyze)
      if (u.includes('pb1')) return respond(MOCK.batch)
      return respond(MOCK.generate)
    }
    if (u.includes('/runs')) return respond({ok:true, runs: MOCK.env.runs})
    if (u.includes('history/open')) {
      const runId = (u.split('runId=')[1] || '').split('&')[0]
      if (runId.startsWith('20261018185600')) return respond({ok:true, kind:'pack', result: MOCK.generate.job.result})
      if (runId.startsWith('20261018170000')) return respond({ok:true, kind:'notes', topics: [{id:'t1', title:'考勤表怎么做才不加班', angle:'职场效率'}]})
      return respond({ok:true, kind:'batch', result: MOCK.batch?.job.result})
    }
    if (u.includes('/reveal')) return respond({ok:true})
    return respond({ok:true})
  }
  const mod = window.__mod.factory((name) => { if (name === 'react') return React; throw new Error(name) })
  const ctx = { effect: (fn) => fn(), desktopWorkbenches: { register: (d, C) => { window.__Panel = C; return () => {} } } }
  mod.apply(ctx)
  const fakeService = { currentSession: () => ({ id: 's1' }), ownsSession: () => false, defaultWorkspace: () => ({ workspaceId: 'w1' }) }
  ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(window.__Panel, { service: fakeService, entry: {}, active: true, conversation: null }))
</script></body></html>`
await (await import('node:fs/promises')).writeFile(outHtml, html, 'utf8')
console.log('preview written:', outHtml)
