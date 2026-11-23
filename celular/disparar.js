// Dispara a publicacao diaria no GitHub Actions a partir do celular (o agendamento do GitHub nao e confiavel).
// Chamado pelo laco a cada 10 min: dispara uma vez por dia, a partir do horario definido (padrao 18:47, horario de Brasilia).
// O workflow so publica se nao houve post nas ultimas 18h, entao disparo repetido nao duplica post.
'use strict'
const fs = require('fs')
const path = require('path')
const DIR = __dirname
const ENV = Object.fromEntries(
  (fs.existsSync(path.join(DIR, '.env')) ? fs.readFileSync(path.join(DIR, '.env'), 'utf8') : '')
    .split('\n').filter(l => /^\s*[A-Z_]+\s*=/.test(l))
    .map(l => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim().replace(/^["']|["']$/g, '')] }))
const cfg = k => process.env[k] || ENV[k] || ''

const GH_TOKEN = cfg('GH_TOKEN')
const REPO = cfg('GH_REPO') || 'gustavoventuri/instagram_desafio_cuca_diario'
const HORA = cfg('HORA_POST') || '18:47'
const MARCA = path.join(DIR, '.ultimo_disparo')

function agoraBrasilia () {
  const d = new Date(Date.now() - 3 * 3600e3) // Brasilia = UTC-3 (sem horario de verao)
  return { dia: d.toISOString().slice(0, 10), hm: d.toISOString().slice(11, 16) }
}

async function main () {
  if (!GH_TOKEN) { console.log('GH_TOKEN nao definido - disparo pelo celular desligado'); return }
  const { dia, hm } = agoraBrasilia()
  const ultimo = fs.existsSync(MARCA) ? fs.readFileSync(MARCA, 'utf8').trim() : ''
  if (hm < HORA || ultimo === dia) return
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/publicar.yml/dispatches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${GH_TOKEN}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
    body: JSON.stringify({ ref: 'main', inputs: { forcar: 'false' } })
  })
  const linha = `${new Date().toISOString().slice(0, 16)}Z disparo da publicacao: HTTP ${r.status}${r.ok ? '' : ' ' + (await r.text()).slice(0, 200)}`
  console.log(linha)
  fs.appendFileSync(path.join(DIR, 'respostas.log'), linha + '\n')
  if (r.ok) fs.writeFileSync(MARCA, dia)
}
main().catch(e => console.log('erro no disparo:', e.message))
