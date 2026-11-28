"""YouTube Shorts de ~1 minuto do Quebra-Cuca Diario.

Cada Short junta: abertura (3s) + curiosidade do dia + desafio do dia + desafio bonus + encerramento (4s).
Os pedacos sao os Reels ja renderizados; o bonus e gerado na hora com outra semente (numero + 1000).

Uso: python shorts.py <numero_short> <num_curiosidade> <num_desafio> <pasta_saida>
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import ImageDraw

import gerador
from gerador import AMARELO, BRANCO, fonte, fundo, pilula, rodape, texto_centro

RAIZ = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30


def cartela(texto1, texto2, segundos, destino, selo):
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 640, selo, fonte("Black", 50))
    texto_centro(d, 540, 780, texto1, fonte("Black", 100), BRANCO, max_w=960)
    texto_centro(d, 540, 1080, texto2, fonte("SemiBold", 54), AMARELO, max_w=920)
    rodape(d, W, H)
    png = destino + ".png"
    img.save(png)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=mono", "-t", str(segundos), "-r", str(FPS), "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-ac", "1", "-shortest", destino], check=True)
    os.remove(png)


def normaliza(src, destino):
    """Reencoda para os mesmos parametros (necessario para concatenar sem falhas)."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-r", str(FPS), "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-ac", "1", destino], check=True)


def duracao(arq):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                                capture_output=True, text=True).stdout.strip())


def monta(num, num_cur, num_des, pasta):
    os.makedirs(pasta, exist_ok=True)
    tmp = tempfile.mkdtemp()
    cur = os.path.join(RAIZ, "docs", "curiosidades", f"{num_cur:03d}")
    des = os.path.join(RAIZ, "docs", "media", f"{num_des:03d}")
    bonus_dir = os.path.join(tmp, "bonus")
    partes = []
    cartela("Você acerta todos?", "Curiosidade + desafios em 1 minuto", 3, os.path.join(tmp, "0.mp4"), f"QUEBRA-CUCA #{num:03d}")
    partes.append(os.path.join(tmp, "0.mp4"))
    for k, src in enumerate([os.path.join(cur, "reel.mp4"), os.path.join(des, "reel.mp4")], 1):
        dst = os.path.join(tmp, f"{k}.mp4")
        normaliza(src, dst)
        partes.append(dst)
    # bonus: desafios de outro tipo (de preferencia os mais longos) ate o Short passar de ~55s
    tipos_usados = {json.load(open(os.path.join(des, "post.json"))).get("desafio")}
    total = sum(duracao(p) for p in partes) + 4
    bonus, n_bonus = [], 1000 + num * 10
    while total < 55 and len(bonus) < 3:
        tipo = gerador.PLANO_SEMANAL[n_bonus % len(gerador.PLANO_SEMANAL)]
        if tipo in tipos_usados or tipo == "ache":
            n_bonus += 1
            continue
        import reels
        reels.ROTULO_FIXO = "BÔNUS"
        b = gerador.gera_um(n_bonus, bonus_dir)
        reels.ROTULO_FIXO = None
        dst = os.path.join(tmp, f"b{len(bonus)}.mp4")
        normaliza(os.path.join(bonus_dir, f"{n_bonus:03d}", "reel.mp4"), dst)
        partes.append(dst)
        total += duracao(dst)
        bonus.append(b["resposta"])
        tipos_usados.add(tipo)
        n_bonus += 1
    cartela("Quantos você acertou?", "Comenta aí e se inscreve: 1 desafio novo todo dia!", 4,
            os.path.join(tmp, "9.mp4"), "FIM")
    partes.append(os.path.join(tmp, "9.mp4"))
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in partes)
    saida = os.path.join(pasta, "short.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy",
                    "-movflags", "+faststart", saida], check=True)
    cur_post = json.load(open(os.path.join(cur, "post.json")))
    titulo = f"Você acerta os 3? Curiosidade + 2 desafios de lógica #{num:03d} #shorts"
    descricao = (f"Quebra-Cuca Diário #{num:03d}: 1 curiosidade e 2 desafios de lógica em 1 minuto.\n"
                 f"Respostas: curiosidade - {cur_post['resposta']} | desafio - {json.load(open(os.path.join(des, 'post.json')))['resposta']}"
                 f" | bônus - {' / '.join(bonus)}\n"
                 f"Fonte da curiosidade: {cur_post.get('fonte_url', '')}\n\n"
                 "Inscreva-se para 1 desafio novo todo dia! 🧩\n#desafio #logica #curiosidades #quebracabeca #shorts")
    post = dict(num=num, serie="youtube", arquivos=["short.mp4"], titulo=titulo[:100], descricao=descricao,
                curiosidade=num_cur, desafio=num_des, bonus=bonus, duracao=round(duracao(saida), 1))
    json.dump(post, open(os.path.join(pasta, "post.json"), "w"), ensure_ascii=False, indent=2)
    subprocess.run(["rm", "-rf", tmp])
    return post


if __name__ == "__main__":
    n, nc, nd = map(int, sys.argv[1:4])
    print(monta(n, nc, nd, os.path.join(sys.argv[4], f"{n:03d}")))
