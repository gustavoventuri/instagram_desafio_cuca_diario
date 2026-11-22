"""Gerador de desafios do @quebra.cuca.diario.

Tipos:
  - ache_diferente  -> Reel 1080x1920 (grade com 1 item diferente, cronometro, revelacao)
  - formas          -> Carrossel 1080x1350 (equacoes com formas, pegadinha de ordem das operacoes)
  - sequencia       -> Carrossel 1080x1350 (qual e o proximo numero?)

Uso: python gerador.py <saida> <numero_inicial> <semente>
"""
import json
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- marca
ROXO1 = (91, 43, 224)
ROXO2 = (42, 27, 143)
AMARELO = (255, 210, 63)
BRANCO = (255, 255, 255)
TINTA = (40, 24, 120)
VERDE = (46, 204, 113)
ROSA = (255, 79, 129)
AZUL = (56, 189, 248)
HANDLE = "@quebra.cuca.diario"

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + os.sep


def fonte(peso, tam):
    return ImageFont.truetype(FD + f"InterDisplay-{peso}.otf", tam)


def fundo(w, h):
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    t = np.clip((x * 0.35 + y * 0.65), 0, 1)[..., None]
    arr = (np.array(ROXO1) * (1 - t) + np.array(ROXO2) * t).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def texto_centro(d, cx, y, txt, f, cor=BRANCO, max_w=None, entre=1.15):
    """Desenha texto centralizado, quebrando linhas se max_w. Retorna y final."""
    linhas = [txt]
    if max_w:
        linhas, atual = [], ""
        for p in txt.split():
            teste = (atual + " " + p).strip()
            if d.textlength(teste, font=f) <= max_w:
                atual = teste
            else:
                linhas.append(atual)
                atual = p
        linhas.append(atual)
    alt = f.size * entre
    for i, l in enumerate(linhas):
        d.text((cx, y + i * alt), l, font=f, fill=cor, anchor="ma")
    return y + len(linhas) * alt


def pilula(d, cx, y, txt, f, bg=AMARELO, fg=TINTA, pad=(28, 14)):
    w = d.textlength(txt, font=f)
    x0, x1 = cx - w / 2 - pad[0], cx + w / 2 + pad[0]
    y1 = y + f.size + pad[1] * 2
    d.rounded_rectangle((x0, y, x1, y1), radius=(y1 - y) / 2, fill=bg)
    d.text((cx, y + pad[1]), txt, font=f, fill=fg, anchor="ma")
    return y1


def peca(d, cx, cy, s, cor=AMARELO):
    """Mini peca de quebra-cabeca (logo)."""
    h = s / 2
    d.rectangle((cx - h, cy - h, cx + h, cy + h), fill=cor)
    r = s * 0.18
    d.ellipse((cx - r, cy - h - r * 1.5, cx + r, cy - h + r * 0.5), fill=cor)
    d.ellipse((cx + h - r * 0.5, cy - r, cx + h + r * 1.5, cy + r), fill=cor)


def rodape(d, w, h, extra=None):
    f = fonte("SemiBold", 34)
    tw = d.textlength(HANDLE, font=f)
    x = w / 2 - (tw + 50) / 2
    peca(d, x + 16, h - 72, 30)
    d.text((x + 50, h - 90), HANDLE, font=f, fill=BRANCO)
    if extra:
        d.text((w / 2, h - 150), extra, font=fonte("Medium", 34), fill=(220, 210, 255), anchor="ma")


def cartao(img, box, raio=48):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((x0, y0 + 14, x1, y1 + 14), raio, fill=(15, 8, 60, 110))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sombra).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, raio, fill=BRANCO)
    return d


# ---------------------------------------------------------------- formas
def desenha_forma(d, nome, cx, cy, s):
    h = s / 2
    if nome == "circulo":
        d.ellipse((cx - h, cy - h, cx + h, cy + h), fill=ROSA)
    elif nome == "quadrado":
        d.rounded_rectangle((cx - h * 0.9, cy - h * 0.9, cx + h * 0.9, cy + h * 0.9), s * 0.12, fill=AZUL)
    elif nome == "triangulo":
        d.polygon([(cx, cy - h), (cx + h, cy + h * 0.8), (cx - h, cy + h * 0.8)], fill=VERDE)
    elif nome == "estrela":
        pts = []
        for i in range(10):
            r = h if i % 2 == 0 else h * 0.45
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=AMARELO, outline=(230, 170, 0), width=3)


def linha_equacao(d, y, termos, resultado, s=110, f=None):
    """termos: lista de nomes de formas e operadores ('+','×','−')."""
    f = f or fonte("Black", 84)
    itens = termos + ["=", resultado]
    larg = []
    for it in itens:
        larg.append(s if it in ("circulo", "quadrado", "triangulo", "estrela") else d.textlength(str(it), font=f))
    gap = 26
    total = sum(larg) + gap * (len(itens) - 1)
    x = 540 - total / 2
    for it, w in zip(itens, larg):
        if it in ("circulo", "quadrado", "triangulo", "estrela"):
            desenha_forma(d, it, x + w / 2, y, s)
        else:
            d.text((x + w / 2, y), str(it), font=f, fill=TINTA, anchor="mm")
        x += w + gap


def gera_formas(rng):
    while True:
        a, b, c = rng.sample(range(2, 13), 3)  # circulo, quadrado, triangulo
        # pergunta: C + Q × T  (ordem das operacoes)
        resp = a + b * c
        errado = (a + b) * c
        if resp != errado:
            break
    eqs = [
        (["circulo", "+", "circulo", "+", "circulo"], 3 * a),
        (["circulo", "+", "quadrado", "+", "quadrado"], a + 2 * b),
        (["quadrado", "+", "triangulo", "+", "triangulo"], b + 2 * c),
    ]
    pergunta = ["circulo", "+", "quadrado", "×", "triangulo"]
    return dict(a=a, b=b, c=c, eqs=eqs, pergunta=pergunta, resposta=resp, errado=errado)


def carrossel_formas(dados, num, pasta):
    W, H = 1080, 1350
    fotos = []
    # slide 1
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 70, f"DESAFIO #{num:03d}", fonte("Black", 40))
    texto_centro(d, 540, 175, "95% erra esse.", fonte("Black", 92))
    texto_centro(d, 540, 290, "Quanto vale a última linha?", fonte("SemiBold", 48), (230, 222, 255))
    d = cartao(img, (70, 400, 1010, 1130))
    y = 500
    for termos, res in dados["eqs"]:
        linha_equacao(d, y, termos, res)
        y += 160
    d.line((140, y - 60, 940, y - 60), fill=(225, 220, 245), width=4)
    linha_equacao(d, y + 20, dados["pergunta"], "?")
    rodape(d, W, H, "arraste para a dica →")
    fotos.append(img)
    # slide 2 - dica
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 70, "DICA", fonte("Black", 40))
    texto_centro(d, 540, 230, "Uma forma de cada vez:", fonte("Black", 70), max_w=960)
    y = 470
    for i, (nome, txt) in enumerate([("circulo", "1ª linha"), ("quadrado", "2ª linha"), ("triangulo", "3ª linha")]):
        desenha_forma(d, nome, 330, y + 50, 100)
        d.text((420, y + 50), f"→ use a {txt}", font=fonte("Bold", 56), fill=BRANCO, anchor="lm")
        y += 170
    texto_centro(d, 540, 1000, "E lembre: multiplicação vem antes da soma 😉".replace(" 😉", ""), fonte("SemiBold", 48), AMARELO, max_w=880)
    rodape(d, W, H, "comente seu palpite antes de arrastar →")
    fotos.append(img)
    # slide 3 - resposta
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 70, "RESPOSTA", fonte("Black", 40))
    d = cartao(img, (70, 190, 1010, 1060))
    y = 280
    for nome, v in [("circulo", dados["a"]), ("quadrado", dados["b"]), ("triangulo", dados["c"])]:
        desenha_forma(d, nome, 380, y, 100)
        d.text((460, y), f"= {v}", font=fonte("Black", 80), fill=TINTA, anchor="lm")
        y += 140
    a, b, c = dados["a"], dados["b"], dados["c"]
    texto_centro(d, 540, 700, f"{a} + {b} × {c}", fonte("Black", 76), TINTA)
    texto_centro(d, 540, 800, f"= {a} + {b*c} = {dados['resposta']}", fonte("Black", 76), (120, 60, 230))
    texto_centro(d, 540, 925, f"Quem respondeu {dados['errado']} somou antes de multiplicar!", fonte("SemiBold", 42), (110, 100, 150), max_w=820)
    rodape(d, W, H, "Siga para 1 desafio novo por dia")
    fotos.append(img)
    nomes = []
    for i, im in enumerate(fotos, 1):
        p = os.path.join(pasta, f"slide{i}.jpg")
        im.save(p, quality=93)
        nomes.append(p)
    return nomes


# ---------------------------------------------------------------- sequencias
def gera_sequencia(rng):
    tipos = []
    s = rng.randint(2, 9); r = rng.randint(3, 9)
    tipos.append(([s + r * i for i in range(6)], f"Some {r} a cada passo.", "soma constante"))
    s = rng.randint(1, 4)
    tipos.append(([s * 2 ** i for i in range(6)], "Cada número é o dobro do anterior.", "dobro"))
    s = rng.randint(1, 5); inc = rng.randint(1, 3)
    seq = [s]
    for i in range(5):
        seq.append(seq[-1] + inc * (i + 1))
    tipos.append((seq, f"A diferença aumenta: +{inc}, +{2*inc}, +{3*inc}, +{4*inc}...", "diferença crescente"))
    k = rng.randint(1, 4)
    tipos.append(([(i + k) ** 2 for i in range(6)], f"São quadrados: {k}², {k+1}², {k+2}²...", "quadrados"))
    a, b = rng.randint(1, 3), rng.randint(2, 4)
    seq = [a, b]
    while len(seq) < 6:
        seq.append(seq[-1] + seq[-2])
    tipos.append((seq, "Cada número é a soma dos dois anteriores.", "fibonacci"))
    x, y_ = rng.randint(3, 7), rng.randint(1, 3)
    s = rng.randint(2, 6)
    seq = [s]
    for i in range(5):
        seq.append(seq[-1] + x if i % 2 == 0 else seq[-1] - y_)
    tipos.append((seq, f"Alterna: +{x}, −{y_}, +{x}, −{y_}...", "alternada"))
    s = rng.randint(1, 3)
    seq = [s]
    for i in range(5):
        seq.append(seq[-1] * 2 + 1)
    tipos.append((seq, "Dobre e some 1.", "dobro mais um"))
    return tipos


def carrossel_sequencia(seq, regra, num, pasta):
    W, H = 1080, 1350
    mostrados, resp = seq[:5], seq[5]
    fotos = []
    # slide 1
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 70, f"DESAFIO #{num:03d}", fonte("Black", 40))
    texto_centro(d, 540, 175, "Qual é o próximo número?", fonte("Black", 84), max_w=940)
    d = cartao(img, (70, 430, 1010, 930))
    txt = "  ".join(str(n) for n in mostrados) + "  ?"
    tam = 110
    while d.textlength(txt, font=fonte("Black", tam)) > 860:
        tam -= 4
    d.text((540, 680), txt, font=fonte("Black", tam), fill=TINTA, anchor="mm")
    texto_centro(d, 540, 990, "Você tem 10 segundos ⏱".replace(" ⏱", ""), fonte("SemiBold", 52), AMARELO)
    rodape(d, W, H, "comente sua resposta, depois arraste →")
    fotos.append(img)
    # slide 2 - resposta
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 70, "RESPOSTA", fonte("Black", 40))
    d = cartao(img, (70, 200, 1010, 1060))
    d.text((540, 430), str(resp), font=fonte("Black", 260), fill=(120, 60, 230), anchor="mm")
    texto_centro(d, 540, 640, regra, fonte("Bold", 52), TINTA, max_w=820)
    txt = "  ".join(str(n) for n in seq)
    tam = 70
    while d.textlength(txt, font=fonte("Bold", tam)) > 820:
        tam -= 4
    d.text((540, 920), txt, font=fonte("Bold", tam), fill=(110, 100, 150), anchor="mm")
    rodape(d, W, H, "Acertou? Siga para 1 desafio novo por dia")
    fotos.append(img)
    nomes = []
    for i, im in enumerate(fotos, 1):
        p = os.path.join(pasta, f"slide{i}.jpg")
        im.save(p, quality=93)
        nomes.append(p)
    return nomes


# ---------------------------------------------------------------- ache o diferente (Reel)
PARES = [("69", "96"), ("O", "Q"), ("E", "F"), ("8", "B"), ("M", "N"), ("b", "d"), ("Z", "2"), ("5", "S"), ("U", "V"), ("C", "G"),
         ("P", "R"), ("W", "VV"), ("q", "p"), ("38", "83"), ("H", "N"), ("6", "9"), ("T", "I"), ("rn", "m"), ("ã", "á"), ("81", "18")]


def gera_audio(caminho, dur, t_revela, fps=30):
    sr = 44100
    n = int(sr * dur)
    a = np.zeros(n)
    # tique a cada segundo durante o desafio
    for s in np.arange(1.5, t_revela, 1.0):
        i = int(s * sr)
        L = int(0.05 * sr)
        t = np.arange(L) / sr
        a[i:i + L] += 0.35 * np.sin(2 * np.pi * 1600 * t) * np.exp(-t * 60)
    # "ding" na revelacao
    i = int(t_revela * sr)
    L = int(1.2 * sr)
    t = np.arange(L) / sr
    ding = (np.sin(2 * np.pi * 880 * t) + 0.6 * np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 3.5) * 0.4
    a[i:i + L] += ding[: max(0, min(L, n - i))]
    a = np.clip(a, -1, 1)
    with wave.open(caminho, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


def reel_ache(par, rng, num, pasta, segundos=7):
    W, H, FPS = 1080, 1920, 30
    base, alvo = par
    cols, rows = 8, 11
    tr, tc = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
    gx0, gy0, gx1, gy1 = 70, 470, 1010, 1550
    cw, ch = (gx1 - gx0) / cols, (gy1 - gy0) / rows
    f = fonte("Bold", int(min(cw, ch) * (0.62 if len(base) == 1 else 0.5)))

    def quadro_base():
        img = fundo(W, H)
        d = ImageDraw.Draw(img)
        pilula(d, 540, 120, f"DESAFIO #{num:03d}", fonte("Black", 44))
        texto_centro(d, 540, 235, f"Ache o {alvo}", fonte("Black", 110))
        texto_centro(d, 540, 375, f"no meio dos {base}", fonte("SemiBold", 54), (230, 222, 255))
        d = cartao(img, (gx0 - 30, gy0 - 30, gx1 + 30, gy1 + 30), 44)
        for r in range(rows):
            for c in range(cols):
                ch_ = alvo if (r, c) == (tr, tc) else base
                d.text((gx0 + cw * (c + .5), gy0 + ch * (r + .5)), ch_, font=f, fill=TINTA, anchor="mm")
        rodape(d, W, H)
        return img

    base_img = quadro_base()
    t_ini, t_rev, t_fim = 1.0, 1.0 + segundos, 1.0 + segundos + 3.5
    frames_dir = os.path.join(pasta, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    nfr = int(t_fim * FPS)
    cx, cy = gx0 + cw * (tc + .5), gy0 + ch * (tr + .5)
    for i in range(nfr):
        t = i / FPS
        img = base_img.copy()
        d = ImageDraw.Draw(img)
        if t < t_rev:
            frac = 1 - max(0, t - t_ini) / segundos
            restante = math.ceil(max(0, t_rev - t)) if t >= t_ini else segundos
            # barra do cronometro
            d.rounded_rectangle((90, 1640, 990, 1680), 20, fill=(70, 40, 170))
            if frac > 0:
                d.rounded_rectangle((90, 1640, 90 + 900 * frac, 1680), 20, fill=AMARELO if frac > .3 else ROSA)
            d.text((540, 1700), f"{restante}s", font=fonte("Black", 70), fill=BRANCO, anchor="ma")
        else:
            k = min(1, (t - t_rev) / 0.4)
            r = 30 + 50 * k
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ROSA, width=12)
            d.rounded_rectangle((90, 1620, 990, 1790), 40, fill=AMARELO)
            d.text((540, 1650), "Achou? Comente seu tempo!", font=fonte("Black", 56), fill=TINTA, anchor="ma")
            d.text((540, 1722), "Manda pra quem não acharia 😂".replace(" 😂", ""), font=fonte("SemiBold", 42), fill=TINTA, anchor="ma")
        img.save(os.path.join(frames_dir, f"{i:04d}.jpg"), quality=90)
    wav = os.path.join(pasta, "audio.wav")
    gera_audio(wav, t_fim, t_rev)
    mp4 = os.path.join(pasta, "reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "%04d.jpg"),
                    "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4], check=True)
    # capa (frame do desafio)
    capa = os.path.join(pasta, "capa.jpg")
    base_img.save(capa, quality=93)
    subprocess.run(["rm", "-rf", frames_dir, wav])
    return mp4, capa, (tr + 1, tc + 1)


# ---------------------------------------------------------------- legendas
TAGS = "#desafio #enigma #quebracabeca #testedelogica #raciociniologico"


def legenda_ache(base, alvo, linha, coluna):
    return (f"Ache o {alvo} no meio dos {base} 👀 Você tem 7 segundos!\n\n"
            f"Comente em quantos segundos achou ⏱ e mande para alguém que se acha bom de olho.\n\n"
            f"Siga @quebra.cuca.diario para 1 desafio novo por dia 🧩\n\n{TAGS}")


def legenda_formas(d):
    return ("95% erra esse 🤯 Quanto vale a última linha?\n\n"
            "Comente seu palpite ANTES de arrastar para a resposta 👇\n"
            "Salve para testar a família depois.\n\n"
            "Siga @quebra.cuca.diario para 1 desafio novo por dia 🧩\n\n" + TAGS)


def legenda_seq():
    return ("Qual é o próximo número? 🔢 Você tem 10 segundos!\n\n"
            "Comente sua resposta e depois arraste para conferir 👉\n"
            "Mande para aquele amigo que adora matemática.\n\n"
            "Siga @quebra.cuca.diario para 1 desafio novo por dia 🧩\n\n" + TAGS)


# ---------------------------------------------------------------- lote
def gera_lote(saida, inicio, semente):
    rng = random.Random(semente)
    os.makedirs(saida, exist_ok=True)
    plano = ["ache", "formas", "ache", "seq", "ache", "formas", "ache", "seq", "ache"]
    pares = rng.sample(PARES, 5)
    seqs = gera_sequencia(rng)
    rng.shuffle(seqs)
    manifesto = []
    for k, tipo in enumerate(plano):
        num = inicio + k
        pasta = os.path.join(saida, f"{num:03d}_{tipo}")
        os.makedirs(pasta, exist_ok=True)
        if tipo == "ache":
            par = pares.pop()
            mp4, capa, (l, c) = reel_ache(par, rng, num, pasta)
            item = dict(num=num, tipo="reel", arquivos=[mp4], capa=capa,
                        resposta=f"'{par[1]}' na linha {l}, coluna {c}", legenda=legenda_ache(par[0], par[1], l, c))
        elif tipo == "formas":
            dd = gera_formas(rng)
            fotos = carrossel_formas(dd, num, pasta)
            item = dict(num=num, tipo="carrossel", arquivos=fotos,
                        resposta=f"circulo={dd['a']} quadrado={dd['b']} triangulo={dd['c']} -> {dd['resposta']}",
                        legenda=legenda_formas(dd), dados={k_: v for k_, v in dd.items() if k_ != 'eqs'} | {"eqs": dd["eqs"]})
        else:
            seq, regra, nome = seqs.pop()
            fotos = carrossel_sequencia(seq, regra, num, pasta)
            item = dict(num=num, tipo="carrossel", arquivos=fotos, resposta=f"{seq} ({nome})",
                        legenda=legenda_seq(), dados=dict(seq=seq, regra=regra))
        with open(os.path.join(pasta, "legenda.txt"), "w") as fh:
            fh.write(item["legenda"])
        manifesto.append(item)
        print(f"#{num:03d} {item['tipo']}: {item['resposta']}")
    with open(os.path.join(saida, "manifesto.json"), "w") as fh:
        json.dump(manifesto, fh, ensure_ascii=False, indent=2)
    return manifesto


if __name__ == "__main__":
    gera_lote(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))


# ---------------------------------------------------------------- 1 post por vez (usado pelo robo)
PLANO_SEMANAL = ["ache", "formas", "ache", "seq", "ache", "ache", "seq"]


def gera_um(num, pasta_base):
    """Gera o post de numero `num` (semente = num) e devolve o item do manifesto."""
    rng = random.Random(num * 7919)
    tipo = PLANO_SEMANAL[num % len(PLANO_SEMANAL)]
    pasta = os.path.join(pasta_base, f"{num:03d}")
    os.makedirs(pasta, exist_ok=True)
    if tipo == "ache":
        par = rng.choice(PARES)
        mp4, capa, (l, c) = reel_ache(par, rng, num, pasta)
        item = dict(num=num, tipo="reel", arquivos=["reel.mp4"], resposta=f"'{par[1]}' linha {l}, coluna {c}",
                    legenda=legenda_ache(par[0], par[1], l, c))
    elif tipo == "formas":
        dd = gera_formas(rng)
        carrossel_formas(dd, num, pasta)
        item = dict(num=num, tipo="carrossel", arquivos=["slide1.jpg", "slide2.jpg", "slide3.jpg"],
                    resposta=f"circulo={dd['a']} quadrado={dd['b']} triangulo={dd['c']} -> {dd['resposta']}",
                    legenda=legenda_formas(dd))
        # conferencia automatica
        v = {"circulo": dd["a"], "quadrado": dd["b"], "triangulo": dd["c"]}
        for termos, res in dd["eqs"]:
            assert eval("".join(str(v.get(t, t)) for t in termos)) == res
        assert dd["a"] + dd["b"] * dd["c"] == dd["resposta"]
    else:
        seq, regra, nome = rng.choice(gera_sequencia(rng))
        carrossel_sequencia(seq, regra, num, pasta)
        item = dict(num=num, tipo="carrossel", arquivos=["slide1.jpg", "slide2.jpg"], resposta=f"{seq} ({nome})",
                    legenda=legenda_seq())
    with open(os.path.join(pasta, "post.json"), "w") as fh:
        json.dump(item, fh, ensure_ascii=False, indent=2)
    return item
