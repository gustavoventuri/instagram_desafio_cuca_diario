"""Robo do @quebra.cuca.diario.

Comandos:
  python publicar.py preparar        -> garante que o proximo post existe em docs/media/NNN (gera se faltar)
  python publicar.py publicar        -> publica o proximo post pela API do Instagram e atualiza estado.json
  python publicar.py renovar_token   -> renova o token de longa duracao (imprime o novo em $GITHUB_OUTPUT)
  python publicar.py testar          -> confere token e conta, sem publicar nada

Variaveis de ambiente:
  IG_TOKEN        token de acesso
  IG_USER_ID      ID da conta do Instagram. Se definido, usa graph.facebook.com (token de usuario
                  do sistema do login unificado, que nao expira). Sem ele, usa graph.instagram.com.
  MEDIA_BASE_URL  URL publica onde a pasta docs/ fica acessivel (ex.: GitHub Pages)
"""
import json
import os
import sys
import time

import requests

def falha(msg):
    """Mostra o erro como anotacao no resumo do GitHub Actions, grava em diagnostico/ e encerra."""
    print(f"::error::{msg}")
    try:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnostico")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "ultimo_erro.txt"), "w") as fh:
            fh.write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + str(msg) + "\n")
    except OSError:
        pass
    sys.exit(msg)


RAIZ = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(RAIZ, "estado.json")
SERIE = os.environ.get("SERIE", "").strip() or "desafios"   # desafios (18:47) ou curiosidades (11:43)
SUBPASTA = {"desafios": "media", "curiosidades": "curiosidades", "youtube": "shorts"}[SERIE]
MIDIA = os.path.join(RAIZ, "docs", SUBPASTA)
CHAVE_PROXIMO = {"desafios": "proximo", "curiosidades": "proximo_curiosidades", "youtube": "proximo_shorts"}[SERIE]
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()
API = "https://graph.facebook.com/v25.0" if IG_USER_ID else "https://graph.instagram.com"


def carrega_estado():
    with open(ESTADO) as fh:
        return json.load(fh)


def salva_estado(e):
    with open(ESTADO, "w") as fh:
        json.dump(e, fh, ensure_ascii=False, indent=2)


def token():
    t = os.environ.get("IG_TOKEN", "").strip()
    if not t:
        falha("IG_TOKEN nao definido")
    return t


def chama(metodo, caminho, **params):
    params["access_token"] = token()
    r = requests.request(metodo, f"{API}/{caminho}", params=params if metodo == "GET" else None,
                         data=params if metodo != "GET" else None, timeout=120)
    if r.status_code >= 400:
        # nunca imprime o token
        falha(f"Erro da API ({r.status_code}) em {caminho}: {r.text[:800]}")
    return r.json()


def conta():
    if IG_USER_ID:
        c = chama("GET", IG_USER_ID, fields="id,username")
        return {"user_id": c["id"], "username": c.get("username")}
    return chama("GET", "me", fields="user_id,username")


# ---------------------------------------------------------------- preparar
def preparar():
    e = carrega_estado()
    num = e.get(CHAVE_PROXIMO, 1)
    pasta = os.path.join(MIDIA, f"{num:03d}")
    if os.path.exists(os.path.join(pasta, "post.json")):
        print(f"{SERIE} #{num:03d} ja existe na fila")
        return
    if SERIE == "curiosidades":
        prepara_curiosidade(num, pasta)
        return
    sys.path.insert(0, RAIZ)
    import gerador
    item = gerador.gera_um(num, MIDIA)
    # remove sobras que nao vao para o Instagram
    for f in os.listdir(pasta):
        if f == "capa.jpg":
            os.remove(os.path.join(pasta, f))
    print(f"gerado #{num:03d}: {item['tipo']} | resposta: {item['resposta']}")


def itens_curiosidades():
    """Todas as curiosidades escritas pela tarefa semanal, em ordem: o item k (a partir de 1) e a curiosidade #k.
    Arquivos conteudo/curiosidades-AAAA-MM-DD.json, lidos em ordem de nome."""
    import glob
    itens = []
    for f in sorted(glob.glob(os.path.join(RAIZ, "conteudo", "curiosidades-*.json"))):
        with open(f, encoding="utf-8") as fh:
            itens += json.load(fh)
    return itens


def prepara_curiosidade(num, pasta):
    """Renderiza a curiosidade #num a partir do conteudo/ (o workflow ja tem ffmpeg e Pillow)."""
    itens = itens_curiosidades()
    if num > len(itens):
        falha(f"fila de curiosidades vazia: so ha {len(itens)} no conteudo/ e falta a #{num:03d}; a tarefa semanal precisa escrever novas")
    sys.path.insert(0, RAIZ)
    import curiosidades
    if not os.path.exists(curiosidades.EMOJI_FONTE):
        import subprocess
        subprocess.run("sudo apt-get install -y -qq fonts-noto-color-emoji", shell=True, check=False)
    post = curiosidades.monta(itens[num - 1], num, pasta)
    capa = os.path.join(pasta, "capa.jpg")
    if os.path.exists(capa):
        os.remove(capa)
    print(f"gerada curiosidade #{num:03d}: resposta: {post['resposta']}")


# ---------------------------------------------------------------- publicar
def espera_url(url, limite=900):
    ini = time.time()
    while time.time() - ini < limite:
        try:
            r = requests.head(url, timeout=30, allow_redirects=True)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        print(f"aguardando arquivo ficar publico: {url}")
        time.sleep(20)
    falha(f"arquivo nao ficou acessivel a tempo: {url}")


def espera_container(cid, limite=600):
    ini = time.time()
    while time.time() - ini < limite:
        st = chama("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            falha(f"container {cid} falhou: {st}")
        time.sleep(15)
    falha(f"container {cid} nao terminou de processar a tempo")


def ja_publicou_recentemente(e, horas=18):
    """Evita post duplicado da mesma serie (desafios ou curiosidades) em menos de `horas`."""
    from datetime import datetime, timezone
    for p in reversed(e["publicados"]):
        if p.get("via") == "api" and p.get("serie", "desafios") == SERIE:
            quando = datetime.strptime(p["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - quando).total_seconds() < horas * 3600
    return False


def publicar():
    if os.environ.get("FORCAR", "").lower() != "true" and ja_publicou_recentemente(carrega_estado()):
        print("ja houve publicacao nas ultimas 18h - nao publica de novo (use forcar=true para publicar assim mesmo)")
        return
    base = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
    if not base:
        falha("MEDIA_BASE_URL nao definido")
    e = carrega_estado()
    num = e.get(CHAVE_PROXIMO, 1)
    pasta = os.path.join(MIDIA, f"{num:03d}")
    with open(os.path.join(pasta, "post.json")) as fh:
        post = json.load(fh)
    urls = [f"{base}/{SUBPASTA}/{num:03d}/{a}" for a in post["arquivos"]]
    for u in urls:
        espera_url(u)
    ig = conta()["user_id"]

    if post["tipo"] == "reel":
        c = chama("POST", f"{ig}/media", media_type="REELS", video_url=urls[0], caption=post["legenda"],
                  share_to_feed="true", thumb_offset="500")["id"]
        espera_container(c)
    else:
        filhos = []
        for u in urls:
            fid = chama("POST", f"{ig}/media", image_url=u, is_carousel_item="true")["id"]
            espera_container(fid)
            filhos.append(fid)
        c = chama("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(filhos),
                  caption=post["legenda"])["id"]
        espera_container(c)

    mid = chama("POST", f"{ig}/media_publish", creation_id=c)["id"]
    link = chama("GET", mid, fields="permalink").get("permalink", "")
    e["publicados"].append(dict(num=num, serie=SERIE, tipo=post["tipo"], desafio=post.get("desafio", SERIE),
                                media_id=mid, link=link,
                                quando=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), via="api"))
    e[CHAVE_PROXIMO] = num + 1
    salva_estado(e)
    print(f"publicado {SERIE} #{num:03d}: {link}")
    limpa_antigos(num)


def limpa_antigos(publicado, manter=3):
    """Apaga as midias de posts ja publicados ha mais de `manter` posts (repositorio leve para o jsDelivr)."""
    import shutil
    for nome in os.listdir(MIDIA):
        if nome.isdigit() and int(nome) <= publicado - manter:
            shutil.rmtree(os.path.join(MIDIA, nome), ignore_errors=True)


# ---------------------------------------------------------------- token
def renovar_token():
    if IG_USER_ID:
        print("token de usuario do sistema nao expira - nada a renovar")
        return
    r = requests.get(f"{API}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token()}, timeout=60)
    if r.status_code >= 400:
        falha(f"falha ao renovar token ({r.status_code}): {r.text[:500]}")
    novo = r.json()["access_token"]
    dias = r.json().get("expires_in", 0) // 86400
    saida = os.environ.get("GITHUB_OUTPUT")
    if saida:
        print(f"::add-mask::{novo}")
        with open(saida, "a") as fh:
            fh.write(f"novo_token={novo}\n")
    print(f"token renovado; vale por ~{dias} dias")


def testar():
    c = conta()
    print(f"token ok - conta @{c.get('username')} (id {c.get('user_id')})")
    e = carrega_estado()
    print(f"proximo desafio: #{e['proximo']:03d} | proxima curiosidade: #{e.get('proximo_curiosidades', 1):03d}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"preparar": preparar, "publicar": publicar, "renovar_token": renovar_token, "testar": testar}.get(
        cmd, lambda: sys.exit(__doc__))()
