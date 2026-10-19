/**
 * 不启动 DSH 的本地自测：用假的 ctx 挂载服务端，逐个调用 /api/xhs-batch/* 路由。
 * 用法：node tools/test-host.mjs [run|prepare|all]
 */
import { readFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { apply } from '../dsh/index.js'

const root = process.env.DSH_HOME
  ? join(process.env.DSH_HOME, 'xhs-batch-studio')
  : resolve('.xhs-batch-studio-test')

const routes = new Map()
const ctx = {
  connection: { fetch: { register(route) { routes.set(route.path, route) } } },
  effect(fn) { const dispose = fn(); return () => dispose?.() },
  logger: () => ({ info: (message) => console.log('[host]', message) }),
}

apply(ctx, { root })
console.log('routes:', [...routes.keys()].join(', '))

async function call(path, { method = 'GET', body } = {}) {
  const url = `http://127.0.0.1${path}`
  const init = { method }
  if (body instanceof Uint8Array) init.body = body
  else if (body !== undefined) init.body = JSON.stringify(body)
  const response = await routes.get(path.split('?')[0]).fetch(new Request(url, init))
  const type = response.headers.get('content-type') || ''
  if (type.includes('application/json')) return { status: response.status, data: await response.json() }
  const buffer = Buffer.from(await response.arrayBuffer())
  return { status: response.status, bytes: buffer.length, type }
}

async function waitJob(id, { quiet = false } = {}) {
  let last = 0
  while (true) {
    const { data } = await call(`/api/xhs-batch/job?id=${id}`)
    const job = data.job
    if (!quiet && job.lines.length !== last) {
      const fresh = job.lines.slice(last)
      last = job.lines.length
      for (const line of fresh.slice(-3)) console.log(`   ${line}`)
    }
    if (job.status !== 'running') return job
    await new Promise((resolveWait) => setTimeout(resolveWait, 700))
  }
}

const mode = process.argv[2] || 'all'

if (mode === 'env' || mode === 'all') {
  const env = await call('/api/xhs-batch/env')
  console.log('env:', env.data)
}

if (mode === 'prepare' || mode === 'all') {
  const started = await call('/api/xhs-batch/prepare', { method: 'POST' })
  console.log('prepare job:', started.data.jobId)
  const job = await waitJob(started.data.jobId)
  console.log('prepare status:', job.status, job.error || '')
  if (job.status !== 'done') process.exit(1)
}

if (mode === 'analyze' || mode === 'all') {
  const samples = resolve('../samples')
  const uploads = []
  for (const name of ['冬季护肤手册.xlsx', '小户型收纳手册.pdf']) {
    const bytes = await readFile(join(samples, name))
    const { data } = await call(`/api/xhs-batch/upload?name=${encodeURIComponent(name)}`, { method: 'POST', body: bytes })
    console.log('upload:', data.name, data.size, data.id ? 'ok' : data)
    uploads.push(data.id)
  }
  const started = await call('/api/xhs-batch/analyze', {
    method: 'POST',
    body: { uploads, config: { count: 4, topic: '' } },
  })
  console.log('analyze job:', started.data.jobId)
  const job = await waitJob(started.data.jobId)
  console.log('analyze status:', job.status, job.error || '')
  if (job.status !== 'done') process.exit(1)
  const runId = job.result.runId
  console.log('topics:', job.result.topics.map((topic) => `- ${topic.title}`).join('\n         '))

  const gen = await call('/api/xhs-batch/generate', {
    method: 'POST',
    body: {
      runId,
      topics: job.result.topics.slice(0, 2).map((topic) => ({ ...topic, selected: true })),
      config: { count: 2, writing: 'listicle', cover: 'poster', card: 'index', cards: 3, palette: 'warm' },
    },
  })
  console.log('generate job:', gen.data.jobId)
  const done = await waitJob(gen.data.jobId)
  console.log('generate status:', done.status, done.error || '')
  if (done.status !== 'done') process.exit(1)
  const result = done.result
  console.log('notes:', result.notes.map((note) => `${note.dir} (${note.images.length} 图)`).join('\n       '))
  const first = result.notes[0]
  const image = await call(`/api/xhs-batch/file?runId=${result.runId}&path=${encodeURIComponent(first.images[0].url.includes('path=') ? decodeURIComponent(first.images[0].url.split('path=')[1]) : '')}`)
  console.log('image route:', image.status, image.bytes, 'bytes', image.type)
  const zip = await call(`/api/xhs-batch/zip?runId=${result.runId}`)
  console.log('zip route:', zip.status, zip.bytes, 'bytes')
  const xlsx = await call(`/api/xhs-batch/file?runId=${result.runId}&path=index.xlsx`)
  console.log('index route:', xlsx.status, xlsx.bytes, 'bytes')
}
