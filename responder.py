"""Responde comentarios dos posts recentes do @quebra.cuca.diario usando o Gemini.

Agenda (o workflow roda a cada 10 minutos e este script decide se age):
  - 1a hora depois do post: a cada 10 minutos
  - da 1a ate a 7a hora: 1 vez por hora (na primeira execucao de cada hora cheia)
  - depois disso: o post e ignorado

Nao guarda estado: antes de responder, confere se a conta ja respondeu aquele comentario.

Variaveis de ambiente: IG_TOKEN, IG_USER_ID, GEMINI_API_KEY, GEMINI_MODEL (opcional),
EVENTO (nome do evento do GitHub; em execucao manual ignora a agenda).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

import publicar as pub

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-flash-latest"
MAX_RESPOSTAS_POR_EXECUCAO = 25
LOG = os.path.join(pub.RAIZ, "diagnostico", "respostas.log")

PROMPT = """Você administra o perfil de Instagram @quebra.cuca.diario, que publica 1 desafio de lógica por dia.
Responda ao comentário abaixo em português do Brasil, como a conta, de forma curta (no máximo 2 frases),
simpática e animada, com no máximo 1 emoji. Nunca use hashtags nem links.

Desafio do post: {desafio}
Resposta correta (NÃO revele a resposta a quem errou): {resposta}
Onde a resposta aparece no post: {onde}

Regras:
- Se a pessoa acertou: parabenize e convide a marcar um amigo para testar.
- Se errou: incentive sem dar a resposta, sugira olhar {dica}.
- Se só comentou o tempo que levou (ex.: "achei em 3s"): reaja ao tempo dela.
- Se for elogio ou comentário geral: agradeça e convide a seguir para o desafio de amanhã.
- Se for spam, ofensa, propaganda, golpe, assunto político/sensível ou algo sem sentido: não responda.

Comentário de @{usuario}: "{texto}"

Devolva somente JSON: {{"responder": true ou false, "texto": "sua resposta"}}"""


def log(msg):
    linha = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}Z {msg}"
    print(linha)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(linha + "\n")


def idade_horas(quando):
    t = datetime.strptime(quando, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


def deve_verificar(idade, agora=None):
    """Aplica a agenda: <1h sempre; 1h-7h so na primeira janela de 10 min de cada hora."""
    agora = agora or datetime.now(timezone.utc)
    if idade < 1.0:
        return True
    if idade < 7.0:
        return agora.minute < 10
    return False


def gemini(prompt):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}},
        timeout=60)
    if r.status_code >= 400:
        pub.falha(f"Erro do Gemini ({r.status_code}): {r.text[:500]}")
    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(txt)


def contexto_do_post(num):
    with open(os.path.join(pub.MIDIA, f"{num:03d}", "post.json")) as fh:
        post = json.load(fh)
    if post["tipo"] == "reel":
        return dict(desafio=post["legenda"].split("\n")[0], resposta=post["resposta"],
                    onde="no final do vídeo, circulada", dica="o vídeo até o final")
    return dict(desafio=post["legenda"].split("\n")[0], resposta=post["resposta"],
                onde="no último slide do carrossel", dica="a dica no 2º slide")


def responder_post(p, minha_conta, restante):
    ctx = contexto_do_post(p["num"])
    dados = pub.chama("GET", f"{p['media_id']}/comments",
                      fields="id,text,username,timestamp,replies{username}", limit="50")
    feitas = 0
    for c in dados.get("data", []):
        if restante - feitas <= 0:
            break
        if c.get("username") == minha_conta:
            continue
        respostas = c.get("replies", {}).get("data", [])
        if any(r.get("username") == minha_conta for r in respostas):
            continue
        decisao = gemini(PROMPT.format(usuario=c.get("username", ""), texto=c.get("text", "")[:500], **ctx))
        if not decisao.get("responder") or not decisao.get("texto", "").strip():
            log(f"#{p['num']:03d} ignorado @{c.get('username')}: {c.get('text', '')[:60]!r}")
            continue
        texto = decisao["texto"].strip()[:300]
        pub.chama("POST", f"{c['id']}/replies", message=texto)
        log(f"#{p['num']:03d} respondeu @{c.get('username')}: {c.get('text', '')[:60]!r} -> {texto!r}")
        feitas += 1
        time.sleep(3)
    return feitas


def main():
    if not GEMINI_KEY:
        pub.falha("GEMINI_API_KEY nao definido")
    manual = os.environ.get("EVENTO") == "workflow_dispatch"
    e = pub.carrega_estado()
    recentes = [p for p in e["publicados"] if p.get("via") == "api" and p.get("media_id")]
    alvos = []
    for p in recentes:
        idade = idade_horas(p["quando"])
        if (manual and idade < 7) or deve_verificar(idade):
            alvos.append((p, idade))
    if not alvos:
        print("nada a verificar agora (fora da agenda)")
        return
    minha_conta = pub.conta()["username"]
    total = 0
    for p, idade in alvos:
        print(f"verificando #{p['num']:03d} (publicado ha {idade:.1f}h)")
        total += responder_post(p, minha_conta, MAX_RESPOSTAS_POR_EXECUCAO - total)
    print(f"{total} resposta(s) enviada(s)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as erro:
        if erro.code not in (0, None):
            log(f"ERRO: {erro.code}")
        raise
    except Exception as erro:  # registra qualquer falha no log lido pelo Claude
        log(f"ERRO: {type(erro).__name__}: {str(erro)[:500]}")
        raise
