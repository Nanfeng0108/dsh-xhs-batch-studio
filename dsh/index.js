/**
 * 小红书批量工作台 · 服务端
 *
 * 两个阶段：
 *  1. analyze  资料 → 选题清单（可编辑）
 *  2. generate 选中选题 + 写作模板 + 版式模板 → 文案 + 图片
 *
 * 另外提供模板（“技能”）的读写接口，以及产物文件服务。
 * 只依赖 Node 内置模块。
 */
import { spawn } from 'node:child_process'
import { createReadStream, existsSync } from 'node:fs'
import { copyFile, mkdir, readdir, readFile, rm, stat, writeFile } from 'node:fs/promises'
import { basename, extname, join, resolve, sep } from 'node:path'
import { homedir } from 'node:os'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'

export const name = 'xhs-batch-studio'
export const inject = ['connection']

const PREFIX = '/api/xhs-batch'
const PY_MODULES = 'pypdf,pypdfium2,openpyxl,yaml,docx,PIL,playwright'
const ALLOWED_EXT = new Set(['.xlsx', '.xlsm', '.xls', '.csv', '.pdf', '.docx', '.doc', '.md', '.txt'])
const MAX_UPLOAD_BYTES = 120 * 1024 * 1024
const MAX_LINES = 500

const fileUrl = (value) => fileURLToPath(value)

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  })
}

const fail = (message, status = 400) => json({ ok: false, error: message }, status)

function spawnProcess(command, args, options = {}) {
  const safe = { ...options }
  if (safe.cwd && !existsSync(safe.cwd)) safe.cwd = homedir()
  const child = spawn(command, args, {
    cwd: safe.cwd,
    env: safe.env || process.env,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  child.stdout.setEncoding('utf8')
  child.stderr.setEncoding('utf8')
  return child
}

function clampInt(value, min, max, fallback) {
  const number = Number.parseInt(String(value ?? ''), 10)
  if (!Number.isFinite(number)) return fallback
  return Math.min(max, Math.max(min, number))
}

export function apply(ctx, config) {
  const home = process.env.DSH_HOME || join(homedir(), '.dsh')
  const root = resolve(config?.root || join(home, 'xhs-batch-studio'))
  const pkgRoot = resolve(fileUrl(new URL('..', import.meta.url)))
  // 插件可能被软链或复制到别处加载，import.meta.url 推出的目录不一定存在；
  // 逐个探测，找到真正带 xhs/__init__.py 的 python 目录。
  const pythonDir = (() => {
    const here = resolve(fileUrl(import.meta.url), '..')
    const candidates = [
      join(pkgRoot, 'python'),
      resolve(here, '..', 'python'),
      resolve(here, '..', '..', 'python'),
      join(home, 'profiles', 'web', 'node_modules', 'dsh-xhs-batch-studio', 'python'),
    ]
    for (const candidate of candidates) {
      if (existsSync(join(candidate, 'xhs', '__init__.py'))) return candidate
    }
    return candidates[0]
  })()
  const runsDir = join(root, 'runs')
  const uploadsDir = join(root, 'uploads')
  const templatesDir = join(root, 'templates')
  const venvDir = join(root, 'venv')
  const venvPython = process.platform === 'win32'
    ? join(venvDir, 'Scripts', 'python.exe')
    : join(venvDir, 'bin', 'python')

  const jobs = new Map()
  let activeJobId = null
  let envReady = null
  let envPython = ''
  let templateCache = null

  const logger = ctx.logger?.('xhs-batch')
  const log = (message) => logger?.info?.(message)

  // ------------------------------------------------------------ job plumbing
  function newJob(kind, stage) {
    const job = {
      id: randomUUID(), kind, status: 'running', stage, progress: 0,
      lines: [], startedAt: Date.now(), runId: '', result: null, error: '', child: null,
    }
    jobs.set(job.id, job)
    const cutoff = Date.now() - 3 * 3600 * 1000
    for (const [id, item] of jobs) {
      if (item.status !== 'running' && item.startedAt < cutoff) jobs.delete(id)
    }
    return job
  }

  function pushLine(job, line) {
    const text = String(line).replace(/\s+$/, '')
    if (!text) return
    job.lines.push(text)
    if (job.lines.length > MAX_LINES) job.lines.splice(0, job.lines.length - MAX_LINES)
    const match = /^\[(\d)\/(\d)\]\s*(.*)$/.exec(text)
    if (match) {
      job.stage = match[3] || job.stage
      job.progress = Math.round((Number(match[1]) / Number(match[2])) * 100)
    }
  }

  const publicJob = (job) => ({
    id: job.id, kind: job.kind, status: job.status, stage: job.stage, progress: job.progress,
    lines: job.lines.slice(-140), runId: job.runId, result: job.result, error: job.error,
    elapsed: Math.round((Date.now() - job.startedAt) / 1000),
  })

  async function runChild(job, command, args, options = {}) {
    const child = spawnProcess(command, args, options)
    job.child = child
    child.stdout.on('data', (chunk) => {
      for (const line of String(chunk).split('\n')) {
        pushLine(job, line)
        if (typeof options.onLine === 'function' && line.trim()) options.onLine(line.trim())
      }
    })
    child.stderr.on('data', (chunk) => {
      for (const line of String(chunk).split('\n')) if (line.trim()) pushLine(job, line)
    })
    const exit = await new Promise((resolveExit) => {
      child.on('close', (code) => resolveExit({ code }))
      child.on('error', (error) => {
        const cwd = options.cwd
        pushLine(job, `进程启动失败：${error.message}`)
        pushLine(job, `诊断：syscall=${error.syscall || '-'} path=${error.path || '-'} 工作目录存在=${cwd ? existsSync(cwd) : '未指定'} 命令存在=${existsSync(command)}`)
        resolveExit({ code: -1 })
      })
    })
    job.child = null
    return exit
  }

  // ------------------------------------------------------------ environment
  async function ensureDirs() {
    await mkdir(runsDir, { recursive: true })
    await mkdir(uploadsDir, { recursive: true })
    await mkdir(join(templatesDir, 'writing'), { recursive: true })
  }

  const basePython = () => process.env.XHS_PYTHON || config?.python || 'python3'

  function probePython(candidate) {
    return new Promise((resolveProbe) => {
      let child
      try {
        child = spawnProcess(candidate, ['-c', 'import sys;print(sys.version.split()[0])'])
      } catch {
        resolveProbe(null)
        return
      }
      let out = ''
      child.stdout.on('data', (chunk) => { out += chunk })
      child.on('error', () => resolveProbe(null))
      child.on('close', (code) => resolveProbe(code === 0 ? out.trim().split('\n').pop() : null))
    })
  }

  function probeModules(python) {
    return new Promise((resolveProbe) => {
      let child
      try {
        child = spawnProcess(python, ['-c', `import ${PY_MODULES};print('ok')`])
      } catch {
        resolveProbe(false)
        return
      }
      child.on('error', () => resolveProbe(false))
      child.on('close', (code) => resolveProbe(code === 0))
    })
  }

  async function currentPython() {
    if (envPython) return envPython
    for (const candidate of [config?.python, process.env.XHS_PYTHON, venvPython, 'python3'].filter(Boolean)) {
      if (await probePython(candidate)) {
        envPython = candidate
        return candidate
      }
    }
    return ''
  }

  async function envState(refresh = false) {
    if (envReady !== null && !refresh) return { ready: envReady, python: envPython }
    const python = await currentPython()
    envReady = python ? await probeModules(python) : false
    return { ready: envReady, python: envPython }
  }

  async function prepare(job) {
    await ensureDirs()
    pushLine(job, '检查 Python 解释器…')
    const base = basePython()
    const version = await probePython(base)
    if (!version) throw new Error(`找不到可用的 Python（尝试了 ${base}）。安装 Python 3.10+ 后重试。`)
    pushLine(job, `Python ${version} 可用`)

    const exists = await stat(venvDir).then(() => true).catch(() => false)
    if (!exists) {
      pushLine(job, '创建独立虚拟环境…')
      const exit = await runChild(job, base, ['-m', 'venv', venvDir])
      if (exit.code !== 0) throw new Error('创建虚拟环境失败')
    }
    const pip = process.platform === 'win32' ? join(venvDir, 'Scripts', 'pip.exe') : join(venvDir, 'bin', 'pip')
    pushLine(job, '安装解析与渲染依赖（首次约 1 分钟）…')
    const pipExit = await runChild(job, pip, ['install', '--disable-pip-version-check', '-q', '-r', join(pythonDir, 'requirements.txt')])
    if (pipExit.code !== 0) throw new Error('依赖安装失败，请检查网络')

    pushLine(job, '准备浏览器渲染器…')
    await runChild(job, venvPython, ['-m', 'playwright', 'install', 'chromium'])
    envPython = venvPython
    envReady = await probeModules(venvPython)
    if (!envReady) throw new Error('环境准备完成但依赖校验失败')
    pushLine(job, '环境就绪')
  }

  // ------------------------------------------------------------ templates
  async function templateCatalog(force = false) {
    if (templateCache && !force) return templateCache
    const python = await currentPython()
    if (!python) return { writing: {}, covers: {}, cards: {} }
    const script = [
      'import json,sys',
      'from xhs import writing',
      "data={'writing':writing.load_all(sys.argv[1] if len(sys.argv)>1 else None),",
      "      'covers':writing.LAYOUT_COVERS,'cards':writing.LAYOUT_CARDS}",
      'print(json.dumps(data, ensure_ascii=False))',
    ].join('\n')
    const output = await new Promise((resolveOut) => {
      let buffer = ''
      const child = spawnProcess(python, ['-c', script, templatesDir], {
        cwd: pythonDir,
        env: { ...process.env, PYTHONPATH: pythonDir },
      })
      child.stdout.on('data', (chunk) => { buffer += chunk })
      child.on('close', () => resolveOut(buffer))
      child.on('error', () => resolveOut(''))
    })
    try {
      templateCache = JSON.parse(output.trim().split('\n').pop())
    } catch {
      templateCache = { writing: {}, covers: {}, cards: {} }
    }
    return templateCache
  }

  async function saveTemplate(input) {
    await ensureDirs()
    const id = String(input?.id || '').trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-')
    if (!id) throw new Error('模板需要一个英文 id')
    const payload = {
      id,
      name: String(input?.name || id).slice(0, 40),
      desc: String(input?.desc || '').slice(0, 200),
      title_rule: String(input?.title_rule || '').slice(0, 200),
      hook: String(input?.hook || '').slice(0, 200),
      cta: String(input?.cta || '').slice(0, 200),
      tone: String(input?.tone || '').slice(0, 200),
      emoji: String(input?.emoji || '').slice(0, 100),
      extra: String(input?.extra || '').slice(0, 800),
      sections: Array.isArray(input?.sections) ? input.sections : [3, 5],
      lines: Array.isArray(input?.lines) ? input.lines : [2, 4],
      tags: Array.isArray(input?.tags) ? input.tags : [6, 8],
      line_max: Number(input?.line_max) || 22,
      heading_max: Number(input?.heading_max) || 12,
      builtin: false,
    }
    const file = join(templatesDir, 'writing', `${id}.json`)
    await writeFile(file, JSON.stringify(payload, null, 2), 'utf8')
    templateCache = null
    return payload
  }

  async function deleteTemplate(id) {
    const safe = String(id || '').replace(/[^a-z0-9_-]+/gi, '')
    if (!safe) throw new Error('模板 id 无效')
    await rm(join(templatesDir, 'writing', `${safe}.json`), { force: true })
    templateCache = null
  }

  // ------------------------------------------------------------ runs
  const runIdPattern = /^[0-9]{8,20}$/

  async function stageUploads(uploadIds, dataDir) {
    await mkdir(dataDir, { recursive: true })
    const names = []
    for (const id of uploadIds) {
      const folder = join(uploadsDir, id)
      for (const file of await readdir(folder).catch(() => [])) {
        const safe = basename(file)
        if (!ALLOWED_EXT.has(extname(safe).toLowerCase())) continue
        await copyFile(join(folder, safe), join(dataDir, safe))
        names.push(safe)
      }
    }
    if (!names.length) throw new Error('上传文件已失效，请重新添加资料')
    return names
  }

  async function readTopics(runId) {
    return readFile(join(runsDir, runId, 'topics.json'), 'utf8').then(JSON.parse).catch(() => [])
  }

  async function readResult(runId) {
    const runDir = join(runsDir, runId)
    const entries = await readdir(runDir, { withFileTypes: true })
    const noteDirs = entries.filter((entry) => entry.isDirectory() && /^\d{3}-/.test(entry.name)).map((entry) => entry.name).sort()
    const notes = []
    for (const dir of noteDirs) {
      const folder = join(runDir, dir)
      const caption = await readFile(join(folder, 'caption.txt'), 'utf8').catch(() => '')
      const files = await readdir(folder).catch(() => [])
      const images = files.filter((file) => /\.(png|jpe?g|webp)$/i.test(file)).sort()
      notes.push({
        dir,
        title: (caption.split('\n')[0] || dir).trim(),
        caption,
        images: images.map((image) => ({
          name: image,
          url: `${PREFIX}/file?runId=${encodeURIComponent(runId)}&path=${encodeURIComponent(`${dir}/${image}`)}`,
        })),
      })
    }
    const report = await readFile(join(runDir, 'run.json'), 'utf8').then(JSON.parse).catch(() => null)
    return {
      runId, notes, report,
      indexUrl: `${PREFIX}/file?runId=${encodeURIComponent(runId)}&path=index.xlsx`,
      zipUrl: `${PREFIX}/zip?runId=${encodeURIComponent(runId)}`,
    }
  }

  async function readPackResult(runId) {
    const runDir = join(runsDir, runId)
    const files = await readdir(runDir).catch(() => [])
    const images = files
      .filter((file) => /^0\d\.png$/.test(file))
      .sort()
      .map((name) => ({
        name,
        url: `${PREFIX}/file?runId=${encodeURIComponent(runId)}&path=${encodeURIComponent(name)}`,
      }))
    const caption = await readFile(join(runDir, 'caption.md'), 'utf8').catch(() => '')
    const staged = await readdir(join(runDir, 'data')).catch(() => [])
    return {
      runId,
      mode: 'pack',
      images,
      caption,
      files: staged.sort(),
      zipUrl: `${PREFIX}/zip?runId=${encodeURIComponent(runId)}`,
    }
  }

  async function readBatchResult(runId) {
    const base = join(runsDir, runId, 'batch')
    const manifest = JSON.parse(await readFile(join(base, 'manifest.json'), 'utf8'))
    const url = (relative) => `${PREFIX}/file?runId=${encodeURIComponent(runId)}&path=${encodeURIComponent(`batch/${relative}`)}`
    const notes = (manifest.notes || []).map((note) => ({
      id: note.id,
      name: note.name || '',
      title: note.title || '',
      audience: note.audience || '',
      keyword: note.keyword || '',
      caption: note.caption || '',
      images: (note.images || []).map((relative) => ({ name: relative.split('/').pop(), url: url(relative) })),
    }))
    return {
      runId,
      mode: 'pack',
      count: notes.length,
      notes,
      zipUrl: url('batch.zip'),
    }
  }

  function fileUrl(runId, relative) {
    return `${PREFIX}/file?runId=${encodeURIComponent(runId)}&path=${encodeURIComponent(relative)}`
  }

  function runTime(runId) {
    const raw = String(runId || '').slice(0, 14)
    if (raw.length < 12) return ''
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)} ${raw.slice(8, 10)}:${raw.slice(10, 12)}`
  }

  async function readRunSummary(runId) {
    const runDir = join(runsDir, runId)
    const files = await readdir(runDir).catch(() => [])
    const summary = { runId, when: runTime(runId), kind: 'other', title: '', count: 0, thumb: '', topics: 0, notes: 0 }

    if (files.includes('batch')) {
      const manifest = await readFile(join(runDir, 'batch', 'manifest.json'), 'utf8').then(JSON.parse).catch(() => null)
      const notes = manifest?.notes || []
      if (notes.length) {
        const cover = notes[0]?.images?.[0]
        return {
          ...summary, kind: 'batch', count: notes.length,
          title: String(notes[0]?.title || '批量笔记').replace(/\n/g, ' ').trim(),
          thumb: cover ? fileUrl(runId, `batch/${cover}`) : '',
        }
      }
    }

    const images = files.filter((file) => /^0\d\.png$/.test(file)).sort()
    if (images.length) {
      const caption = await readFile(join(runDir, 'caption.md'), 'utf8').catch(() => '')
      const plan = await readFile(join(runDir, 'plans.json'), 'utf8').then(JSON.parse).catch(() => null)
      const title = plan?.plans?.[0]?.title || caption.split('\n').find((line) => line.trim()) || '资料包笔记'
      return { ...summary, kind: 'pack', count: images.length, title: String(title).replace(/\n/g, ' ').trim(), thumb: fileUrl(runId, images[0]) }
    }

    const topics = await readTopics(runId)
    const report = await readFile(join(runDir, 'run.json'), 'utf8').then(JSON.parse).catch(() => null)
    const notes = await readFile(join(runDir, 'notes.json'), 'utf8').then(JSON.parse).catch(() => [])
    let thumb = ''
    const entries = await readdir(runDir, { withFileTypes: true }).catch(() => [])
    const noteDir = entries
      .filter((item) => item.isDirectory() && /^\d{3}-/.test(item.name))
      .map((item) => item.name)
      .sort()[0]
    if (noteDir) {
      const inner = await readdir(join(runDir, noteDir)).catch(() => [])
      const image = inner.filter((file) => /^0\d\.png$/.test(file)).sort()[0]
      if (image) thumb = fileUrl(runId, `${noteDir}/${image}`)
    }
    const noteCount = Array.isArray(notes) ? notes.length : Number(report?.notes || 0)
    return {
      ...summary, kind: 'notes', count: noteCount, topics: topics.length, notes: noteCount, thumb,
      title: String(notes?.[0]?.title || topics[0]?.title || '知识笔记').replace(/\n/g, ' ').trim(),
    }
  }

  async function listRuns() {
    const entries = await readdir(runsDir, { withFileTypes: true }).catch(() => [])
    const dirs = entries.filter((item) => item.isDirectory()).sort((a, b) => b.name.localeCompare(a.name)).slice(0, 24)
    const items = []
    for (const entry of dirs) {
      try {
        const summary = await readRunSummary(entry.name)
        if (summary.kind === 'other') continue
        if (summary.kind === 'notes' && !summary.count && !summary.topics) continue
        items.push(summary)
      } catch {
        // 单条失败不影响列表
      }
    }
    return items
  }

  // ------------------------------------------------------------ stages
  async function analyzeJob(job, body) {
    const uploads = Array.isArray(body?.uploads) ? body.uploads.slice(0, 40) : []
    if (!uploads.length) throw new Error('请先添加资料')
    const runId = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14) + String(Date.now() % 1000).padStart(3, '0')
    const runDir = join(runsDir, runId)
    await mkdir(runDir, { recursive: true })
    const names = await stageUploads(uploads, join(runDir, 'data'))
    job.runId = runId
    pushLine(job, `资料：${names.join('、')}`)

    const python = envPython || (await currentPython())
    const args = [
      '-m', 'xhs.analyze',
      '--data', join(runDir, 'data'),
      '--out', runDir,
      '--count', String(clampInt(body?.config?.count, 1, 30, 8)),
    ]
    if (body?.config?.topic) args.push('--topic', String(body.config.topic).slice(0, 60))
    if (body?.config?.audience) args.push('--audience', String(body.config.audience).slice(0, 40))
    const exit = await runChild(job, python, args, {
      cwd: pythonDir, env: { ...process.env, PYTHONPATH: pythonDir, PYTHONUNBUFFERED: '1' },
    })
    if (job.status === 'cancelled') return
    if (exit.code !== 0) throw new Error(`分析失败（退出码 ${exit.code}），请查看日志`)
    const topics = await readTopics(runId)
    if (!topics.length) throw new Error('没有提炼出选题，换一份资料或调整内容方向试试')
    job.result = { runId, topics, meta: await readFile(join(runDir, 'meta.json'), 'utf8').then(JSON.parse).catch(() => null) }
    job.stage = '选题已生成'
    job.progress = 100
  }

  async function generateJob(job, body) {
    const runId = String(body?.runId || '')
    if (!runIdPattern.test(runId)) throw new Error('运行编号无效')
    const runDir = join(runsDir, runId)
    const exists = await stat(runDir).then(() => true).catch(() => false)
    if (!exists) throw new Error('找不到这次运行的资料，请重新分析')
    const topics = Array.isArray(body?.topics) ? body.topics.filter((topic) => topic && topic.title) : []
    if (!topics.length) throw new Error('请至少选择一个选题')
    job.runId = runId
    const topicsFile = join(runDir, 'selected-topics.json')
    await writeFile(topicsFile, JSON.stringify(topics, null, 2), 'utf8')

    const configInput = body?.config || {}
    const python = envPython || (await currentPython())
    const args = [
      '-m', 'xhs.build',
      '--run', runDir,
      '--topics', topicsFile,
      '--count', String(clampInt(configInput.count, 1, 30, topics.length)),
      '--writing', String(configInput.writing || 'listicle'),
      '--cover', ['poster', 'magazine', 'note'].includes(configInput.cover) ? configInput.cover : 'poster',
      '--card', ['index', 'timeline'].includes(configInput.card) ? configInput.card : 'index',
      '--cards', String(clampInt(configInput.cards, 2, 6, 4)),
      '--palette', ['warm', 'ink', 'mint', 'paper'].includes(configInput.palette) ? configInput.palette : 'warm',
      '--templates-dir', templatesDir,
    ]
    if (configInput.signature) args.push('--signature', String(configInput.signature).slice(0, 24))
    if (configInput.noFix) args.push('--no-fix')
    const exit = await runChild(job, python, args, {
      cwd: pythonDir, env: { ...process.env, PYTHONPATH: pythonDir, PYTHONUNBUFFERED: '1' },
    })
    if (job.status === 'cancelled') return
    if (exit.code !== 0) throw new Error(`生成失败（退出码 ${exit.code}），请查看日志`)
    job.result = await readResult(runId)
    if (!job.result.notes.length) throw new Error('没有生成任何笔记')
    job.stage = '完成'
    job.progress = 100
  }

  async function packAnalyzeJob(job, body) {
    const uploads = Array.isArray(body?.uploads) ? body.uploads.slice(0, 40) : []
    if (!uploads.length) throw new Error('请先添加资料')
    const runId = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14) + String(Date.now() % 1000).padStart(3, '0')
    const runDir = join(runsDir, runId)
    await mkdir(runDir, { recursive: true })
    const names = await stageUploads(uploads, join(runDir, 'data'))
    job.runId = runId
    pushLine(job, `资料：${names.join('、')}`)

    const python = envPython || (await currentPython())
    const planCount = clampInt(body?.count, 1, 6, 3)
    const args = ['-m', 'xhs.planner', '--data', join(runDir, 'data'), '--out', join(runDir, 'plans.json'),
      '--count', String(planCount)]
    const exit = await runChild(job, python, args, {
      cwd: pythonDir, env: { ...process.env, PYTHONPATH: pythonDir, PYTHONUNBUFFERED: '1' },
    })
    if (job.status === 'cancelled') return
    if (exit.code !== 0) throw new Error(`解析或编排失败（退出码 ${exit.code}），请查看日志`)
    const payload = await readFile(join(runDir, 'plans.json'), 'utf8').then(JSON.parse)
    if (!payload?.plans?.length) throw new Error('没有生成可用方案')
    job.result = { runId, plans: payload.plans, facts: payload.facts || '', files: names }
    job.stage = '方案已生成'
    job.progress = 100
  }

  async function packGenerateJob(job, body) {
    const runId = String(body?.runId || '')
    if (!runIdPattern.test(runId)) throw new Error('运行编号无效')
    const plan = body?.plan
    if (!plan || !plan.title) throw new Error('没有选中的方案')
    const runDir = join(runsDir, runId)
    const exists = await stat(runDir).then(() => true).catch(() => false)
    if (!exists) throw new Error('找不到这次运行的资料，请重新解析')
    job.runId = runId
    const planFile = join(runDir, 'plan.json')
    await writeFile(planFile, JSON.stringify({ plans: [plan] }, null, 2), 'utf8')

    const python = envPython || (await currentPython())
    const args = [
      '-m', 'xhs.pack',
      '--data', join(runDir, 'data'),
      '--out', runDir,
      '--plan', planFile,
      '--pick', '0',
    ]
    const exit = await runChild(job, python, args, {
      cwd: pythonDir, env: { ...process.env, PYTHONPATH: pythonDir, PYTHONUNBUFFERED: '1' },
    })
    if (job.status === 'cancelled') return
    if (exit.code !== 0) throw new Error(`出图失败（退出码 ${exit.code}），请查看日志`)
    job.result = await readPackResult(runId)
    if (!job.result.images.length) throw new Error('没有生成图片')
    job.stage = '完成'
    job.progress = 100
  }

  async function packBatchJob(job, body) {
    const runId = String(body?.runId || '')
    if (!runIdPattern.test(runId)) throw new Error('运行编号无效')
    const runDir = join(runsDir, runId)
    const exists = await stat(runDir).then(() => true).catch(() => false)
    if (!exists) throw new Error('找不到这次运行的资料，请重新解析')
    job.runId = runId
    const count = clampInt(body?.count, 1, 30, 12)

    const python = envPython || (await currentPython())
    const args = [
      '-m', 'xhs.batch',
      '--data', join(runDir, 'data'),
      '--out', join(runDir, 'batch'),
      '--count', String(count),
    ]
    const exit = await runChild(job, python, args, {
      cwd: pythonDir, env: { ...process.env, PYTHONPATH: pythonDir, PYTHONUNBUFFERED: '1' },
      onLine(line) {
        const match = /^\[(\d+)\/(\d+)\]\s*(.*)$/.exec(line)
        if (!match) {
          if (line.startsWith('编排')) { job.stage = '编排方案中'; job.progress = 3 }
          return
        }
        const done = Number(match[1])
        const total = Number(match[2]) || count
        job.stage = `出图 ${done}/${total}`
        job.progress = Math.max(3, Math.min(99, Math.round((done / total) * 100)))
      },
    })
    if (job.status === 'cancelled') return
    if (exit.code !== 0) throw new Error(`批量出图失败（退出码 ${exit.code}），请查看日志`)
    job.result = await readBatchResult(runId)
    if (!job.result.notes.length) throw new Error('没有生成任何笔记')
    job.stage = '完成'
    job.progress = 100
  }

  function startJob(kind, stage, runner, body) {
    if (activeJobId) return fail('已有任务在进行中，请等待或取消', 409)
    const job = newJob(kind, stage)
    activeJobId = job.id
    runner(job, body)
      .then(() => { job.status = 'done'; job.progress = job.progress || 100 })
      .catch((error) => {
        job.status = 'failed'
        job.error = error instanceof Error ? error.message : String(error)
      })
      .finally(() => { activeJobId = null })
    return json({ ok: true, jobId: job.id })
  }

  // ------------------------------------------------------------ routes
  const routes = [
    {
      path: `${PREFIX}/env`, methods: ['GET'], requestBody: 'buffered',
      async fetch() {
        await ensureDirs()
        const state = await envState(true)
        const [catalog, runs] = await Promise.all([templateCatalog(), listRuns().catch(() => [])])
        return json({ ok: true, ...state, root, pythonDir, pythonDirExists: existsSync(pythonDir), runs, catalog, platform: process.platform })
      },
    },
    {
      path: `${PREFIX}/prepare`, methods: ['POST'], requestBody: 'buffered',
      async fetch() {
        return startJob('prepare', '准备运行环境', (job) => prepare(job))
      },
    },
    {
      path: `${PREFIX}/upload`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const url = new URL(request.url)
        const rawName = url.searchParams.get('name') || 'file'
        const safe = basename(rawName).replace(/[\\/:*?"<>|]+/g, '_')
        const ext = extname(safe).toLowerCase()
        if (!ALLOWED_EXT.has(ext)) return fail(`不支持的格式：${ext || '未知'}`)
        const buffer = Buffer.from(await request.arrayBuffer())
        if (!buffer.length) return fail('文件为空')
        if (buffer.length > MAX_UPLOAD_BYTES) return fail('单个文件超过 120MB')
        const id = randomUUID()
        const folder = join(uploadsDir, id)
        await mkdir(folder, { recursive: true })
        await writeFile(join(folder, safe), buffer)
        return json({ ok: true, id, name: safe, size: buffer.length })
      },
    },
    {
      path: `${PREFIX}/analyze`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const state = await envState()
        if (!state.ready) return fail('运行环境尚未就绪，请先点「准备环境」', 428)
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        return startJob('analyze', '解析资料并提炼选题', analyzeJob, body)
      },
    },
    {
      path: `${PREFIX}/generate`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const state = await envState()
        if (!state.ready) return fail('运行环境尚未就绪，请先点「准备环境」', 428)
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        return startJob('generate', '按模板生成文案与图片', generateJob, body)
      },
    },
    {
      path: `${PREFIX}/pack/analyze`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const state = await envState()
        if (!state.ready) return fail('运行环境尚未就绪，请先点「准备环境」', 428)
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        return startJob('pack-analyze', '解析资料并生成方案', packAnalyzeJob, body)
      },
    },
    {
      path: `${PREFIX}/pack/generate`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const state = await envState()
        if (!state.ready) return fail('运行环境尚未就绪，请先点「准备环境」', 428)
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        return startJob('pack-generate', '按方案出图', packGenerateJob, body)
      },
    },
    {
      path: `${PREFIX}/pack/batch`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const state = await envState()
        if (!state.ready) return fail('运行环境尚未就绪，请先点「准备环境」', 428)
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        return startJob('pack-batch', '批量出图中', packBatchJob, body)
      },
    },
    {
      path: `${PREFIX}/job`, methods: ['GET'], requestBody: 'buffered',
      async fetch(request) {
        const job = jobs.get(new URL(request.url).searchParams.get('id') || '')
        if (!job) return fail('任务不存在或已过期', 404)
        return json({ ok: true, job: publicJob(job) })
      },
    },
    {
      path: `${PREFIX}/cancel`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const job = jobs.get(new URL(request.url).searchParams.get('id') || '')
        if (!job) return fail('任务不存在', 404)
        if (job.child) {
          job.status = 'cancelled'
          job.stage = '已取消'
          try { job.child.kill('SIGTERM') } catch { /* ignore */ }
        }
        return json({ ok: true })
      },
    },
    {
      path: `${PREFIX}/topics`, methods: ['GET'], requestBody: 'buffered',
      async fetch(request) {
        const runId = new URL(request.url).searchParams.get('runId') || ''
        if (!runIdPattern.test(runId)) return fail('运行编号无效')
        return json({ ok: true, runId, topics: await readTopics(runId) })
      },
    },
    {
      path: `${PREFIX}/result`, methods: ['GET'], requestBody: 'buffered',
      async fetch(request) {
        const runId = new URL(request.url).searchParams.get('runId') || ''
        if (!runIdPattern.test(runId)) return fail('运行编号无效')
        const exists = await stat(join(runsDir, runId)).then(() => true).catch(() => false)
        if (!exists) return fail('找不到这次运行', 404)
        return json({ ok: true, result: await readResult(runId) })
      },
    },
    {
      path: `${PREFIX}/templates`, methods: ['GET', 'POST'], requestBody: 'buffered',
      async fetch(request) {
        if (request.method === 'GET') {
          return json({ ok: true, catalog: await templateCatalog(true) })
        }
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        try {
          const saved = await saveTemplate(body?.template || {})
          return json({ ok: true, template: saved, catalog: await templateCatalog(true) })
        } catch (error) {
          return fail(error instanceof Error ? error.message : '保存失败')
        }
      },
    },
    {
      path: `${PREFIX}/templates/delete`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        let body
        try { body = JSON.parse(await request.text()) } catch { return fail('请求格式错误') }
        await deleteTemplate(body?.id)
        return json({ ok: true, catalog: await templateCatalog(true) })
      },
    },
    {
      path: `${PREFIX}/runs`, methods: ['GET'], requestBody: 'buffered',
      async fetch() {
        return json({ ok: true, runs: await listRuns() })
      },
    },
    {
      path: `${PREFIX}/history/open`, methods: ['GET'], requestBody: 'buffered',
      async fetch(request) {
        const runId = new URL(request.url).searchParams.get('runId') || ''
        if (!runIdPattern.test(runId)) return fail('运行编号无效')
        const summary = await readRunSummary(runId)
        if (summary.kind === 'batch') return json({ ok: true, kind: 'batch', summary, result: await readBatchResult(runId) })
        if (summary.kind === 'pack') return json({ ok: true, kind: 'pack', summary, result: await readPackResult(runId) })
        return json({ ok: true, kind: 'notes', summary, topics: await readTopics(runId) })
      },
    },
    {
      path: `${PREFIX}/file`, methods: ['GET'], requestBody: 'buffered',
      async fetch(request) {
        const url = new URL(request.url)
        const runId = url.searchParams.get('runId') || ''
        const relative = url.searchParams.get('path') || ''
        if (!runIdPattern.test(runId)) return fail('运行编号无效')
        const runDir = join(runsDir, runId)
        const target = resolve(runDir, relative)
        if (!target.startsWith(runDir + sep)) return fail('路径不合法', 403)
        const info = await stat(target).catch(() => null)
        if (!info?.isFile()) return fail('文件不存在', 404)
        const types = {
          '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
          '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          '.zip': 'application/zip', '.txt': 'text/plain; charset=utf-8',
          '.md': 'text/plain; charset=utf-8', '.json': 'application/json; charset=utf-8',
        }
        return new Response(createReadStream(target), {
          headers: {
            'content-type': types[extname(target).toLowerCase()] || 'application/octet-stream',
            'content-length': String(info.size), 'cache-control': 'no-store',
          },
        })
      },
    },
    {
      path: `${PREFIX}/zip`, methods: ['GET'], requestBody: 'buffered',
      async fetch(request) {
        const runId = new URL(request.url).searchParams.get('runId') || ''
        if (!runIdPattern.test(runId)) return fail('运行编号无效')
        const runDir = join(runsDir, runId)
        const exists = await stat(runDir).then(() => true).catch(() => false)
        if (!exists) return fail('找不到这次运行', 404)
        const zipPath = join(runsDir, `${runId}.zip`)
        const python = envPython || (await currentPython())
        const exit = await new Promise((resolveZip) => {
          const child = spawnProcess(python, [join(pythonDir, 'zip_run.py'), runDir, zipPath])
          child.on('close', (code) => resolveZip(code))
        })
        if (exit !== 0) return fail('打包失败', 500)
        const buffer = await readFile(zipPath)
        return new Response(buffer, {
          headers: {
            'content-type': 'application/zip',
            'content-disposition': `attachment; filename="xhs-${runId}.zip"`,
            'content-length': String(buffer.length), 'cache-control': 'no-store',
          },
        })
      },
    },
    {
      path: `${PREFIX}/reveal`, methods: ['POST'], requestBody: 'buffered',
      async fetch(request) {
        const runId = new URL(request.url).searchParams.get('runId') || ''
        const target = runId && runIdPattern.test(runId) ? join(runsDir, runId) : runsDir
        const info = await stat(target).catch(() => null)
        if (!info) return fail('目录不存在', 404)
        const command = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'explorer' : 'xdg-open'
        try { spawnProcess(command, [target]).unref() } catch { return fail('无法打开文件夹') }
        return json({ ok: true, dir: target })
      },
    },
  ]

  for (const route of routes) ctx.connection.fetch.register(route)

  ctx.effect(() => {
    ensureDirs().catch((error) => log(`初始化目录失败：${error}`))
    return () => {
      for (const job of jobs.values()) {
        if (job.child) {
          try { job.child.kill('SIGTERM') } catch { /* ignore */ }
        }
      }
    }
  })

  log(`小红书批量工作台已就绪，数据目录 ${root}`)
}
