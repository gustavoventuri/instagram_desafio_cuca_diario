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

RAIZ = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(RAIZ, "estado.json")
MIDIA = os.path.join(RAIZ, "docs", "media")
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
        sys.exit("IG_TOKEN nao definido")
    return t


def chama(metodo, caminho, **params):
    params["access_token"] = token()
    r = requests.request(metodo, f"{API}/{caminho}", params=params if metodo == "GET" else None,
                         data=params if metodo != "GET" else None, timeout=120)
    if r.status_code >= 400:
        # nunca imprime o token
        sys.exit(f"Erro da API ({r.status_code}) em {caminho}: {r.text[:800]}")
    return r.json()


def conta():
    if IG_USER_ID:
        c = chama("GET", IG_USER_ID, fields="id,username")
        return {"user_id": c["id"], "username": c.get("username")}
    return chama("GET", "me", fields="user_id,username")


# ---------------------------------------------------------------- preparar
def preparar():
    e = carrega_estado()
    num = e["proximo"]
    pasta = os.path.join(MIDIA, f"{num:03d}")
    if os.path.exists(os.path.join(pasta, "post.json")):
        print(f"post #{num:03d} ja existe na fila")
        return
    sys.path.insert(0, RAIZ)
    import gerador
    item = gerador.gera_um(num, MIDIA)
    # remove sobras que nao vao para o Instagram
    for f in os.listdir(pasta):
        if f == "capa.jpg":
            os.remove(os.path.join(pasta, f))
    print(f"gerado #{num:03d}: {item['tipo']} | resposta: {item['resposta']}")


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
    sys.exit(f"arquivo nao ficou acessivel a tempo: {url}")


def espera_container(cid, limite=600):
    ini = time.time()
    while time.time() - ini < limite:
        st = chama("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"container {cid} falhou: {st}")
        time.sleep(15)
    sys.exit(f"container {cid} nao terminou de processar a tempo")


def publicar():
    base = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
    if not base:
        sys.exit("MEDIA_BASE_URL nao definido")
    e = carrega_estado()
    num = e["proximo"]
    pasta = os.path.join(MIDIA, f"{num:03d}")
    with open(os.path.join(pasta, "post.json")) as fh:
        post = json.load(fh)
    urls = [f"{base}/media/{num:03d}/{a}" for a in post["arquivos"]]
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
    e["publicados"].append(dict(num=num, tipo=post["tipo"], media_id=mid, link=link,
                                quando=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), via="api"))
    e["proximo"] = num + 1
    salva_estado(e)
    print(f"publicado #{num:03d}: {link}")


# ---------------------------------------------------------------- token
def renovar_token():
    if IG_USER_ID:
        print("token de usuario do sistema nao expira - nada a renovar")
        return
    r = requests.get(f"{API}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token()}, timeout=60)
    if r.status_code >= 400:
        sys.exit(f"falha ao renovar token ({r.status_code}): {r.text[:500]}")
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
    print(f"proximo post: #{carrega_estado()['proximo']:03d}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"preparar": preparar, "publicar": publicar, "renovar_token": renovar_token, "testar": testar}.get(
        cmd, lambda: sys.exit(__doc__))()
