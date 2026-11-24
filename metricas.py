"""Puxa as estatisticas de cada post publicado e grava em diagnostico/metricas.csv.

Precisa da permissao instagram_manage_insights no token. Sem ela, grava o aviso e sai sem erro.
"""
import csv
import os

import requests

import publicar as pub

METRICAS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
            "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
SAIDA = os.path.join(pub.RAIZ, "diagnostico", "metricas.csv")


def valor(media_id, metrica):
    r = requests.get(f"{pub.API}/{media_id}/insights",
                     params={"metric": metrica, "access_token": pub.token()}, timeout=60)
    if r.status_code >= 400:
        return None, r.json().get("error", {}).get("message", r.text)[:200]
    dados = r.json().get("data", [])
    if not dados:
        return None, ""
    v = dados[0].get("values", [{}])[0].get("value")
    if metrica == "ig_reels_avg_watch_time" and v is not None:
        v = round(v / 1000, 1)  # ms -> s
    return v, ""


def main():
    e = pub.carrega_estado()
    linhas, avisos = [], set()
    for p in e["publicados"]:
        if not p.get("media_id"):
            continue
        linha = {"num": p["num"], "quando": p["quando"], "link": p.get("link", "")}
        for m in METRICAS:
            v, erro = valor(p["media_id"], m)
            linha[m] = "" if v is None else v
            if erro:
                avisos.add(erro)
        linhas.append(linha)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["num", "quando", "link"] + METRICAS)
        w.writeheader()
        w.writerows(linhas)
    if avisos:
        with open(os.path.join(pub.RAIZ, "diagnostico", "metricas_avisos.txt"), "w") as fh:
            fh.write("\n".join(sorted(avisos)) + "\n")
    print(f"metricas de {len(linhas)} post(s) gravadas; avisos: {len(avisos)}")


if __name__ == "__main__":
    main()
