// Dispara as publicacoes diarias no GitHub Actions a partir do celular (o agendamento do GitHub nao e confiavel).
// Chamado pelo laco a cada 10 min. Cada serie dispara uma vez por dia, a partir do seu horario (Brasilia):
//   HORARIOS=11:43=curiosidades,17:13=youtube,18:47=desafios   (padrao)
// O workflow so publica se nao houve post da mesma serie nas ultimas 18h, entao disparo repetido nao duplica post.
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
const HORARIOS = (cfg('HORARIOS') || '11:43=curiosidades,17:13=youtube,18:47=desafios')
  .split(',').map(x => x.trim().split('=')).filter(x => x.length === 2)
const marca = serie => path.join(DIR, `.ultimo_disparo_${serie}`)

function agoraBrasilia () {
  const d = new Date(Date.now() - 3 * 3600e3) // Brasilia = UTC-3 (sem horario de verao)
  return { dia: d.toISOString().slice(0, 10), hm: d.toISOString().slice(11, 16) }
}

async function dispara (serie) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/publicar.yml/dispatches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${GH_TOKEN}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
    body: JSON.stringify({ ref: 'main', inputs: { forcar: 'false', serie } })
  })
  const linha = `${new Date().toISOString().slice(0, 16)}Z disparo ${serie}: HTTP ${r.status}${r.ok ? '' : ' ' + (await r.text()).slice(0, 200)}`
  console.log(linha)
  fs.appendFileSync(path.join(DIR, 'respostas.log'), linha + '\n')
  return r.ok
}

async function main () {
  if (!GH_TOKEN) { console.log('GH_TOKEN nao definido - disparo pelo celular desligado'); return }
  const { dia, hm } = agoraBrasilia()
  for (const [hora, serie] of HORARIOS) {
    if (!fs.existsSync(marca(serie))) {
      // primeira execucao desta versao: se o horario de hoje ja passou, comeca a disparar a partir de amanha
      if (hm >= hora) { fs.writeFileSync(marca(serie), dia); continue }
    }
    const ultimo = fs.existsSync(marca(serie)) ? fs.readFileSync(marca(serie), 'utf8').trim() : ''
    if (hm < hora || ultimo === dia) continue
    if (await dispara(serie)) fs.writeFileSync(marca(serie), dia)
    await new Promise(r => setTimeout(r, 2000))
  }
}
main().catch(e => console.log('erro no disparo:', e.message))
