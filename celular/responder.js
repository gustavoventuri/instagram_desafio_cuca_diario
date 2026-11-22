// Robo de respostas do @quebra.cuca.diario - roda no celular (Termux) usando o Fly (Llama 3.2 1B local).
//
// Agenda (o laco chama este script a cada 10 minutos):
//   1a hora depois do post: a cada 10 min | da 1a a 7a hora: 1x por hora | depois: ignora
// Respostas neutras: agradece, incentiva e convida a seguir, sem dizer se a pessoa acertou.
// Sem estado: antes de responder, confere se a conta ja respondeu aquele comentario.
//
// Uso: node responder.js            (respeita a agenda)
//      node responder.js --agora    (ignora a agenda; verifica posts das ultimas 7h)
'use strict'
const fs = require('fs')
const path = require('path')
const { spawn, execSync } = require('child_process')

const DIR = __dirname
const ENV = Object.fromEntries(
  (fs.existsSync(path.join(DIR, '.env')) ? fs.readFileSync(path.join(DIR, '.env'), 'utf8') : '')
    .split('\n').filter(l => /^\s*[A-Z_]+\s*=/.test(l))
    .map(l => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim().replace(/^["']|["']$/g, '')] }))
const cfg = k => process.env[k] || ENV[k] || ''

const IG_TOKEN = cfg('IG_TOKEN')
const IG_USER_ID = cfg('IG_USER_ID')
const REPO_RAW = cfg('REPO_RAW') || 'https://raw.githubusercontent.com/gustavoventuri/instagram_desafio_cuca_diario/main'
const PORTA = Number(cfg('FLY_PORTA') || 8095)
const API = 'https://graph.facebook.com/v25.0'
const MAX_POR_EXECUCAO = 25
const LOG = path.join(DIR, 'respostas.log')
const AGORA = process.argv.includes('--agora')

function log (msg) {
  const linha = `${new Date().toISOString().slice(0, 16).replace('T', ' ')}Z ${msg}`
  console.log(linha)
  fs.appendFileSync(LOG, linha + '\n')
}
const sleep = ms => new Promise(r => setTimeout(r, ms))

// ---------------------------------------------------------------- Instagram
async function ig (metodo, caminho, params = {}) {
  const p = new URLSearchParams({ ...params, access_token: IG_TOKEN })
  const url = metodo === 'GET' ? `${API}/${caminho}?${p}` : `${API}/${caminho}`
  const r = await fetch(url, metodo === 'GET' ? {} : { method: 'POST', body: p })
  const j = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(`Instagram ${r.status} em ${caminho}: ${JSON.stringify(j).slice(0, 400)}`)
  return j
}

// ---------------------------------------------------------------- Fly (llama-server sob demanda)
function acha (nomes, raizes) {
  for (const n of nomes) {
    try { const p = execSync(`command -v ${n}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); if (p) return p } catch {}
  }
  for (const r of raizes) {
    try {
      const p = execSync(`find ${r} -maxdepth 6 -name "${nomes[0]}" -type f 2>/dev/null | head -1`).toString().trim()
      if (p) return p
    } catch {}
  }
  return ''
}

let servidor = null
async function ligaFly () {
  if (await flyOnline()) return
  const home = process.env.HOME
  const bin = cfg('LLAMA_SERVER') || acha(['llama-server'], [home])
  const modelo = cfg('FLY_MODELO') || acha(['Llama-3.2-1B-Instruct-Q4_K_M.gguf'], [home])
  if (!bin) throw new Error('llama-server nao encontrado (defina LLAMA_SERVER no .env)')
  if (!modelo) throw new Error('modelo do Fly nao encontrado (defina FLY_MODELO no .env)')
  servidor = spawn(bin, ['-m', modelo, '--port', String(PORTA), '--host', '127.0.0.1', '-c', '2048', '-t', '4'],
    { stdio: 'ignore' })
  for (let i = 0; i < 60; i++) { await sleep(1000); if (await flyOnline()) return }
  throw new Error('o Fly nao subiu em 60s')
}
async function flyOnline () {
  try { return (await fetch(`http://127.0.0.1:${PORTA}/health`)).ok } catch { return false }
}
function desligaFly () { if (servidor) { servidor.kill(); servidor = null } }

const RESERVAS = [
  'Valeu por participar! 🧩 Amanhã tem desafio novo, fica de olho!',
  'Obrigado pelo comentário! 🙌 Marca aquele amigo que se acha bom nisso.',
  'Adoramos ver você por aqui! 🧠 Segue o perfil pra não perder o próximo desafio.',
  'Boa! 😄 Desafia um amigo e vê quem é mais rápido.'
]
const PROIBIDO = /(acert|errou|errad|corret|incorret|a resposta é|resposta certa|resposta correta|linha \d|coluna \d|#|https?:|www\.)/i

function limpa (txt) {
  let t = String(txt || '').replace(/^["'\s]+|["'\s]+$/g, '').replace(/\s+/g, ' ')
  const frases = t.match(/[^.!?]+[.!?]*/g) || []
  t = frases.slice(0, 2).join(' ').trim().slice(0, 200)
  return t
}

async function fly (usuario, comentario) {
  const r = await fetch(`http://127.0.0.1:${PORTA}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      temperature: 0.6,
      max_tokens: 70,
      messages: [
        { role: 'system', content: 'Você é o perfil de Instagram @quebra.cuca.diario, que posta 1 desafio de lógica por dia. Responda comentários em português do Brasil com UMA frase curta, simpática e animada, com no máximo 1 emoji. Apenas agradeça, incentive ou convide a seguir o perfil ou marcar um amigo. Nunca diga se a pessoa acertou ou errou, nunca revele respostas, nunca use hashtags nem links.' },
        { role: 'user', content: 'Comentário de @ana: "achei em 3 segundos!"' },
        { role: 'assistant', content: 'Que rapidez, Ana! ⚡ Marca um amigo pra ver se ele bate seu tempo.' },
        { role: 'user', content: 'Comentário de @joao: "muito difícil esse"' },
        { role: 'assistant', content: 'Esse era dos bons mesmo! 💪 Amanhã tem outro, não desiste.' },
        { role: 'user', content: `Comentário de @${usuario}: "${comentario.slice(0, 300)}"` }
      ]
    })
  })
  if (!r.ok) throw new Error(`Fly respondeu ${r.status}`)
  const j = await r.json()
  return limpa(j.choices?.[0]?.message?.content)
}

// ---------------------------------------------------------------- filtros e agenda
function ignorar (texto) {
  const t = texto.toLowerCase()
  if (!t.trim()) return 'vazio'
  if (/https?:|www\.|\.com\b/.test(t)) return 'link'
  if (/\b(pix|ganhe|ganhar dinheiro|renda extra|seguidores grátis|promo|cupom|dm me|me chama|chama no direct|onlyfans|bet|aposta)\b/.test(t)) return 'spam'
  if (/\b(porra|caralho|merda|bosta|idiota|burr[oa]|lixo|fdp|puta|vagabund\w*)\b/.test(t)) return 'ofensa'
  if (/\b(lula|bolsonaro|eleição|eleições|partido|pt|pl)\b/.test(t)) return 'politica'
  return ''
}

function deveVerificar (idadeH, agora = new Date()) {
  if (idadeH < 1) return true
  if (idadeH < 7) return agora.getUTCMinutes() < 10
  return false
}

// ---------------------------------------------------------------- principal
async function principal () {
  if (!IG_TOKEN || !IG_USER_ID) throw new Error('defina IG_TOKEN e IG_USER_ID no .env')
  const estado = await (await fetch(`${REPO_RAW}/estado.json?t=${Date.now()}`)).json()
  const alvos = estado.publicados
    .filter(p => p.via === 'api' && p.media_id)
    .map(p => ({ ...p, idade: (Date.now() - Date.parse(p.quando)) / 3600e3 }))
    .filter(p => (AGORA ? p.idade < 7 : deveVerificar(p.idade)))
  if (!alvos.length) { console.log('nada a verificar agora (fora da agenda)'); return }

  const conta = (await ig('GET', IG_USER_ID, { fields: 'username' })).username
  let feitas = 0
  for (const p of alvos) {
    console.log(`verificando #${String(p.num).padStart(3, '0')} (publicado há ${p.idade.toFixed(1)}h)`)
    const dados = await ig('GET', `${p.media_id}/comments`, { fields: 'id,text,username,replies{username}', limit: '50' })
    for (const c of dados.data || []) {
      if (feitas >= MAX_POR_EXECUCAO) break
      if (c.username === conta) continue
      if ((c.replies?.data || []).some(r => r.username === conta)) continue
      const motivo = ignorar(c.text || '')
      if (motivo) { log(`#${p.num} ignorado (${motivo}) @${c.username}: ${JSON.stringify((c.text || '').slice(0, 60))}`); continue }
      await ligaFly()
      let resp = ''
      try { resp = await fly(c.username, c.text || '') } catch (e) { log(`Fly falhou: ${e.message}`) }
      if (!resp || resp.length < 8 || PROIBIDO.test(resp)) resp = RESERVAS[Math.floor(Math.random() * RESERVAS.length)]
      await ig('POST', `${c.id}/replies`, { message: resp })
      log(`#${p.num} respondeu @${c.username}: ${JSON.stringify((c.text || '').slice(0, 60))} -> ${JSON.stringify(resp)}`)
      feitas++
      await sleep(3000)
    }
  }
  console.log(`${feitas} resposta(s) enviada(s)`)
}

principal()
  .catch(e => { log(`ERRO: ${e.message}`); process.exitCode = 1 })
  .finally(desligaFly)
