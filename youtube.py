"""Publica o proximo Short (docs/shorts/NNN/short.mp4) no YouTube pela YouTube Data API.

Variaveis de ambiente (segredos do GitHub): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Sem elas, nao faz nada (sai sem erro).

Atencao: projetos do Google Cloud nao auditados so conseguem enviar videos como PRIVADOS.
Por isso o padrao e YT_PRIVACIDADE=private ate a auditoria ser aprovada; depois, defina a variavel
YT_PRIVACIDADE=public no GitHub.
"""
import json
import os
import time

import requests

import publicar as pub

PASTA = os.path.join(pub.RAIZ, "docs", "shorts")


def access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=60)
    if r.status_code >= 400:
        pub.falha(f"YouTube: falha ao renovar o acesso ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


def main():
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("::notice::YouTube ainda nao configurado (YT_CLIENT_ID/YT_CLIENT_SECRET/YT_REFRESH_TOKEN)")
        return
    e = pub.carrega_estado()
    if os.environ.get("FORCAR", "").lower() != "true" and pub.ja_publicou_recentemente(e):
        print("ja houve Short nas ultimas 18h - nao publica de novo")
        return
    num = e.get("proximo_shorts", 1)
    pasta = os.path.join(PASTA, f"{num:03d}")
    if not os.path.exists(os.path.join(pasta, "post.json")):
        pub.falha(f"fila de Shorts vazia (falta docs/shorts/{num:03d}); aprove a semana no GitHub")
    post = json.load(open(os.path.join(pasta, "post.json")))
    video = os.path.join(pasta, post["arquivos"][0])
    tok = access_token()
    meta = {
        "snippet": {"title": post["titulo"], "description": post["descricao"], "categoryId": "27",
                    "tags": ["desafio", "lógica", "curiosidades", "quebra-cabeça", "shorts"], "defaultLanguage": "pt-BR"},
        "status": {"privacyStatus": os.environ.get("YT_PRIVACIDADE", "").strip() or "private",
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False},
    }
    ini = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                                 "X-Upload-Content-Type": "video/mp4",
                                 "X-Upload-Content-Length": str(os.path.getsize(video))},
                        data=json.dumps(meta), timeout=60)
    if ini.status_code >= 400:
        pub.falha(f"YouTube: falha ao iniciar o envio ({ini.status_code}): {ini.text[:400]}")
    with open(video, "rb") as fh:
        up = requests.put(ini.headers["Location"], headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"},
                          data=fh, timeout=600)
    if up.status_code >= 400:
        pub.falha(f"YouTube: falha no envio ({up.status_code}): {up.text[:400]}")
    vid = up.json()["id"]
    link = f"https://youtube.com/shorts/{vid}"
    e["publicados"].append(dict(num=num, serie="youtube", tipo="short", video_id=vid, link=link,
                                quando=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), via="api"))
    e["proximo_shorts"] = num + 1
    pub.salva_estado(e)
    print(f"Short #{num:03d} enviado: {link} ({meta['status']['privacyStatus']})")


if __name__ == "__main__":
    main()
