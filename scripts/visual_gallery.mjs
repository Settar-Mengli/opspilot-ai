#!/usr/bin/env node
/**
 * Visual gallery / determinism helper for UI Baselines workflow.
 *
 * Modes:
 *   index <playwright-json> <out-md> [--new-states=a,b]
 *   render-gate <playwright-json> [--new-states=a,b]
 *   compare-trees <dirA> <dirB>
 */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const NEW_DEFAULT = ['dashboard-error', 'evening-error']

function parseArgs(argv) {
  const args = { positional: [], flags: {} }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a.startsWith('--')) {
      const [k, v] = a.slice(2).split('=')
      args.flags[k] = v ?? true
    } else {
      args.positional.push(a)
    }
  }
  return args
}

function newStates(flags) {
  if (typeof flags['new-states'] === 'string') {
    return flags['new-states'].split(',').map((s) => s.trim()).filter(Boolean)
  }
  return NEW_DEFAULT
}

function sha256File(filePath) {
  const h = crypto.createHash('sha256')
  h.update(fs.readFileSync(filePath))
  return h.digest('hex')
}

function walkPngs(root) {
  const out = new Map()
  if (!fs.existsSync(root)) return out
  const stack = [root]
  while (stack.length) {
    const dir = stack.pop()
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name)
      const st = fs.statSync(full)
      if (st.isDirectory()) stack.push(full)
      else if (name.endsWith('.png')) {
        const rel = path.relative(root, full).replace(/\\/g, '/')
        out.set(rel, full)
      }
    }
  }
  return out
}

function parseStateViewport(title, projectName) {
  // title like "visual baselines › dashboard" or "dashboard"
  const m = String(title).match(/›\s*([^\s]+)\s*$/) || String(title).match(/^([a-z0-9-]+)$/i)
  const state = m ? m[1] : String(title)
  const vp = String(projectName || '').replace(/^chromium-/, '') || 'unknown'
  return { state, viewport: vp }
}

function loadReport(jsonPath) {
  const raw = fs.readFileSync(jsonPath, 'utf-8')
  return JSON.parse(raw)
}

function collectSpecs(report) {
  const rows = []
  const suites = report.suites || []
  const walk = (suite, projectHint) => {
    const project = suite.projectName || projectHint
    for (const spec of suite.specs || []) {
      for (const t of spec.tests || []) {
        const result = (t.results || [])[(t.results || []).length - 1] || {}
        const status = result.status || t.status || 'unknown'
        const errors = result.errors || []
        const attachments = result.attachments || []
        const { state, viewport } = parseStateViewport(spec.title, t.projectName || project)
        let diffPixels = null
        const errText = errors.map((e) => e.message || e.value || '').join('\n')
        const pix = errText.match(/(\d+)\s+pixels?\s+\(ratio/i)
        if (pix) diffPixels = Number(pix[1])
        const isRender =
          status === 'timedOut' ||
          /Timeout|locator|toBeVisible|strict mode|not found|Error:/i.test(errText)
        const isPixel =
          /toHaveScreenshot|pixels \(ratio|Screenshot comparison/i.test(errText) ||
          status === 'unexpected'
        rows.push({
          state,
          viewport,
          status,
          diffPixels,
          isRender: Boolean(isRender && status !== 'passed'),
          isPixelDiff: Boolean(isPixel && status !== 'passed'),
          error: errText.slice(0, 500),
          attachments: attachments.map((a) => ({
            name: a.name,
            path: a.path,
            contentType: a.contentType,
          })),
        })
      }
    }
    for (const child of suite.suites || []) walk(child, project)
  }
  for (const s of suites) walk(s, s.projectName)
  return rows
}

function cmdIndex(jsonPath, outMd, flags) {
  const report = loadReport(jsonPath)
  const rows = collectSpecs(report)
  const news = new Set(newStates(flags))
  const lines = [
    '# Visual gallery index',
    '',
    '| State | Viewport | Result | Diff px | Notes | Images |',
    '|-------|----------|--------|---------|-------|--------|',
  ]
  for (const r of rows.sort((a, b) => a.state.localeCompare(b.state) || a.viewport.localeCompare(b.viewport))) {
    let result = 'pass'
    let notes = ''
    if (r.status === 'passed') result = 'pass'
    else if (news.has(r.state) && r.isRender) {
      result = 'new-state'
      notes = 'new state, no before'
    } else if (r.isPixelDiff) {
      result = 'diff'
      notes = (r.error || '').split('\n')[0].slice(0, 120)
    } else if (r.isRender) {
      result = 'render-fail'
      notes = (r.error || '').split('\n')[0].slice(0, 120)
    } else {
      result = r.status
      notes = (r.error || '').split('\n')[0].slice(0, 120)
    }
    const imgs = r.attachments
      .filter((a) => (a.contentType || '').startsWith('image/') || (a.path || '').endsWith('.png'))
      .map((a) => a.path || a.name)
      .join('<br>')
    lines.push(
      `| ${r.state} | ${r.viewport} | ${result} | ${r.diffPixels ?? '—'} | ${notes.replace(/\|/g, '/')} | ${imgs || '—'} |`,
    )
  }
  fs.writeFileSync(outMd, lines.join('\n') + '\n', 'utf-8')
  console.log(`Wrote ${outMd} (${rows.length} rows)`)
}

function cmdRenderGate(jsonPath, flags) {
  const report = loadReport(jsonPath)
  const rows = collectSpecs(report)
  const news = new Set(newStates(flags))
  const blockers = rows.filter((r) => r.isRender && !news.has(r.state) && r.status !== 'passed')
  if (blockers.length) {
    console.error('RENDER GATE FAILED (non-new states):')
    for (const b of blockers) {
      console.error(`- ${b.state}@${b.viewport}: ${b.error.split('\n')[0]}`)
    }
    process.exit(1)
  }
  const skippedNew = rows.filter((r) => news.has(r.state) && r.status !== 'passed')
  if (skippedNew.length) {
    console.log('New-state render issues (allowed for before-run):')
    for (const s of skippedNew) console.log(`- ${s.state}@${s.viewport}`)
  }
  console.log('Render gate OK')
}

function cmdCompareTrees(dirA, dirB) {
  const a = walkPngs(dirA)
  const b = walkPngs(dirB)
  const keys = new Set([...a.keys(), ...b.keys()])
  const mismatches = []
  for (const k of [...keys].sort()) {
    if (!a.has(k)) {
      mismatches.push(`only in B: ${k}`)
      continue
    }
    if (!b.has(k)) {
      mismatches.push(`only in A: ${k}`)
      continue
    }
    const ha = sha256File(a.get(k))
    const hb = sha256File(b.get(k))
    if (ha !== hb) mismatches.push(`diff: ${k}`)
  }
  if (mismatches.length) {
    console.error(`DETERMINISM FAIL: ${mismatches.length} mismatch(es)`)
    for (const m of mismatches.slice(0, 50)) console.error(`  ${m}`)
    if (mismatches.length > 50) console.error(`  ... +${mismatches.length - 50} more`)
    process.exit(1)
  }
  console.log(`DETERMINISM OK: ${a.size} PNGs byte-identical`)
}

function main() {
  const { positional, flags } = parseArgs(process.argv.slice(2))
  const [mode, ...rest] = positional
  if (mode === 'index') {
    cmdIndex(rest[0], rest[1], flags)
  } else if (mode === 'render-gate') {
    cmdRenderGate(rest[0], flags)
  } else if (mode === 'compare-trees') {
    cmdCompareTrees(rest[0], rest[1])
  } else {
    console.error('Usage: visual_gallery.mjs index|render-gate|compare-trees ...')
    process.exit(2)
  }
}

main()
