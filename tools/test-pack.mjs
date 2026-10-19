import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { apply } from '../dsh/index.js'

const routes = new Map()
const ctx = {
  connection: { fetch: { register: (route) => routes.set(route.path, route) } },
  effect: (fn) => fn(),
  logger: () => ({ info: (message) => console.log('[host]', message) }),
}
apply(ctx, {})

async function call(path, { method = 'GET', body } = {}) {
  const init = { method }
  if (body instanceof Uint8Array) init.body = body
  else if (body !== undefined) init.body = JSON.stringify(body)
  const response = await routes.get(path.split('?')[0]).fetch(new Request('http://127.0.0.1' + path, init))
  const type = response.headers.get('content-type') || ''
  if (type.includes('application/json')) return { status: response.status, data: await response.json() }
  const buffer = Buffer.from(await response.arrayBuffer())
  return { status: response.status, bytes: buffer.length, type }
}

async function waitJob(id) {
  let last = 0
  while (true) {
    const { data } = await call(`/api/xhs-batch/job?id=${id}`)
    const job = data.job
    for (const line of job.lines.slice(last).slice(-2)) console.log('   ', line)
    last = job.lines.length
    if (job.status !== 'running') return job
    await new Promise((resolve) => setTimeout(resolve, 800))
  }
}

const dir = '/Users/chery/Downloads/120款考勤表模板excel'
const uploads = []
for (const name of ['模板01.xlsx', '模板21.xlsx', '模板116.docx']) {
  const bytes = await readFile(join(dir, name))
  const { data } = await call(`/api/xhs-batch/upload?name=${encodeURIComponent(name)}`, { method: 'POST', body: bytes })
  uploads.push(data.id)
  console.log('upload:', name, data.ok)
}

const started = await call('/api/xhs-batch/pack/analyze', { method: 'POST', body: { uploads } })
console.log('analyze job:', started.data.jobId)
const analyzed = await waitJob(started.data.jobId)
console.log('analyze status:', analyzed.status, analyzed.error || '')
if (analyzed.status !== 'done') process.exit(1)
const plans = analyzed.result.plans
plans.forEach((plan, index) => console.log(`plan ${index + 1}:`, plan.name, '|', plan.title.replace(/\n/g, ' / ')))

const generated = await call('/api/xhs-batch/pack/generate', {
  method: 'POST',
  body: { runId: analyzed.result.runId, plan: plans[0] },
})
console.log('generate job:', generated.data.jobId)
const done = await waitJob(generated.data.jobId)
console.log('generate status:', done.status, done.error || '')
if (done.status !== 'done') process.exit(1)
console.log('images:', done.result.images.map((image) => image.name).join(', '))
const first = await call(`/api/xhs-batch/file?runId=${done.result.runId}&path=01.png`)
console.log('image route:', first.status, first.bytes, 'bytes', first.type)
console.log('caption head:', done.result.caption.slice(0, 60).replace(/\n/g, ' '))
