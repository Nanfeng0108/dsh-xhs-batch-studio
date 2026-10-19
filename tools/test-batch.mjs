import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { apply } from '../dsh/index.js'

const routes = new Map()
const ctx = {
  connection: { fetch: { register: (route) => routes.set(route.path, route) } },
  effect: (fn) => fn(),
  logger: () => ({ info: () => {} }),
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
  while (true) {
    const { data } = await call(`/api/xhs-batch/job?id=${id}`)
    const job = data.job
    if (job.status !== 'running') return job
    await new Promise((resolve) => setTimeout(resolve, 900))
  }
}

const dir = '/Users/chery/Downloads/120款考勤表模板excel'
const uploads = []
for (const name of ['模板01.xlsx', '模板21.xlsx']) {
  const bytes = await readFile(join(dir, name))
  const { data } = await call(`/api/xhs-batch/upload?name=${encodeURIComponent(name)}`, { method: 'POST', body: bytes })
  uploads.push(data.id)
}
const analyzed = await waitJob((await call('/api/xhs-batch/pack/analyze', { method: 'POST', body: { uploads } })).data.jobId)
if (analyzed.status !== 'done') { console.log('analyze failed', analyzed.error); process.exit(1) }
const runId = analyzed.result.runId

const started = await call('/api/xhs-batch/pack/batch', { method: 'POST', body: { runId, count: 3 } })
const done = await waitJob(started.data.jobId)
console.log('batch status:', done.status, done.error || '')
if (done.status !== 'done') process.exit(1)

const notes = done.result.notes
console.log('notes:', notes.length)
let bad = 0
for (const note of notes) {
  const image = note.images[0]
  const fetched = await call(image.url.replace('http://127.0.0.1', ''))
  const mark = fetched.status === 200 && fetched.bytes > 10000 ? 'ok' : 'BAD'
  if (mark === 'BAD') bad++
  console.log(`${note.id} ${note.title.replace(/\n/g, '/')} -> ${image.name} ${fetched.status} ${fetched.bytes}B ${mark}`)
}
const zip = await call(done.result.zipUrl.replace('http://127.0.0.1', ''))
console.log('zip:', zip.status, zip.bytes, 'B')
if (bad) process.exit(1)
console.log('batch urls OK')
