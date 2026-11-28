"""Reels de logica do @quebra.cuca.diario: formas, triangulos numericos e sequencias.

Todo Reel segue o mesmo roteiro (1080x1920, 30 fps):
  - desafio na tela com cronometro (barra + segundos) e tique-taque
  - dica aparece em ~55% do tempo (segura quem esta travado)
  - revelacao da resposta com "ding" e explicacao
"""
import math
import os
import subprocess

from PIL import ImageDraw

from gerador import (AMARELO, BRANCO, ROSA, TINTA, VERDE, avalia, cartao, desenha_forma, fonte, fundo,
                     gera_audio, linha_equacao, pilula, rodape, texto_centro)

W, H, FPS = 1080, 1920, 30
ROXO_FORTE = (120, 60, 230)
CINZA = (110, 100, 150)
CARD = (60, 430, 1020, 1540)
ROTULO_FIXO = None  # ex.: "BÔNUS" nos Shorts, no lugar de "DESAFIO #NNN"


# ---------------------------------------------------------------- base comum
def cabecalho(img, num, titulo, subtitulo):
    d = ImageDraw.Draw(img)
    pilula(d, 540, 100, ROTULO_FIXO or f"DESAFIO #{num:03d}", fonte("Black", 44))
    f = fonte("Black", 96)
    while d.textlength(titulo, font=f) > 980:
        f = fonte("Black", f.size - 4)
    texto_centro(d, 540, 195, titulo, f)
    texto_centro(d, 540, 325, subtitulo, fonte("SemiBold", 48), (230, 222, 255), max_w=960)
    return d


def monta_reel(desafio, resposta, segundos, dica, pasta):
    """desafio/resposta: imagens 1080x1920 completas. Gera reel.mp4 e capa.jpg em `pasta`."""
    t_ini, t_rev = 1.0, 1.0 + segundos
    t_fim = t_rev + 4.5
    t_dica = t_ini + segundos * 0.55
    frames = os.path.join(pasta, "frames")
    os.makedirs(frames, exist_ok=True)
    f_seg = fonte("Black", 56)
    f_dica = fonte("Bold", 42)
    txt_dica = f"Dica: {dica}"
    while ImageDraw.Draw(desafio).textlength(txt_dica, font=f_dica) > 980 and f_dica.size > 28:
        f_dica = fonte("Bold", f_dica.size - 2)
    for i in range(int(t_fim * FPS)):
        t = i / FPS
        if t < t_rev:
            img = desafio.copy()
            d = ImageDraw.Draw(img)
            frac = 1 - max(0, t - t_ini) / segundos
            d.rounded_rectangle((90, 1590, 990, 1630), 20, fill=(70, 40, 170))
            if frac > 0:
                d.rounded_rectangle((90, 1590, 90 + 900 * frac, 1630), 20, fill=AMARELO if frac > .3 else ROSA)
            restante = math.ceil(max(0, t_rev - t)) if t >= t_ini else segundos
            d.text((540, 1650), f"{restante}s", font=f_seg, fill=BRANCO, anchor="ma")
            if t >= t_dica:
                d.text((540, 1735), txt_dica, font=f_dica, fill=AMARELO, anchor="ma")
        else:
            img = resposta
        img.save(os.path.join(frames, f"{i:04d}.jpg"), quality=90)
    wav = os.path.join(pasta, "audio.wav")
    gera_audio(wav, t_fim, t_rev)
    mp4 = os.path.join(pasta, "reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames, "%04d.jpg"),
                    "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4], check=True)
    desafio.save(os.path.join(pasta, "capa.jpg"), quality=93)
    subprocess.run(["rm", "-rf", frames, wav])
    return mp4


def faixa_resposta(img, linha1, linha2):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((90, 1580, 990, 1790), 40, fill=AMARELO)
    d.text((540, 1610), linha1, font=fonte("Black", 54), fill=TINTA, anchor="ma")
    d.text((540, 1690), linha2, font=fonte("SemiBold", 40), fill=TINTA, anchor="ma")


# ---------------------------------------------------------------- formas (4 incognitas)
def reel_formas(dados, num, pasta, segundos=15):
    a, b, c, dd = dados["a"], dados["b"], dados["c"], dados["d"]
    # desafio
    img = fundo(W, H)
    cabecalho(img, num, "Só 2% acertam.", "Quanto vale a última linha?")
    d = cartao(img, CARD)
    y = 545
    for termos, res in dados["eqs"]:
        linha_equacao(d, y, termos, res, s=100, f=fonte("Black", 80))
        y += 195
    d.line((130, y - 80, 950, y - 80), fill=(225, 220, 245), width=5)
    linha_equacao(d, y + 10, dados["pergunta"], "?", s=92, f=fonte("Black", 74))
    rodape(d, W, H)
    desafio = img
    # resposta
    img = fundo(W, H)
    cabecalho(img, num, f"Resposta: {dados['resposta']}", "× vem antes de + e −")
    d = cartao(img, CARD)
    pos = [(330, 560), (750, 560), (330, 730), (750, 730)]
    for (nome, v), (x, yy) in zip([("circulo", a), ("quadrado", b), ("triangulo", c), ("estrela", dd)], pos):
        desenha_forma(d, nome, x - 75, yy, 100)
        d.text((x, yy), f"= {v}", font=fonte("Black", 80), fill=TINTA, anchor="lm")
    texto_centro(d, 540, 900, f"{dd} + {b} × {c} − {a}", fonte("Black", 84), TINTA)
    texto_centro(d, 540, 1020, f"= {dd} + {b * c} − {a}", fonte("Black", 84), TINTA)
    texto_centro(d, 540, 1140, f"= {dados['resposta']}", fonte("Black", 110), ROXO_FORTE)
    texto_centro(d, 540, 1320, f"Deu {dados['errado']}? Você fez da esquerda para a direita!",
                 fonte("SemiBold", 44), CINZA, max_w=860)
    faixa_resposta(img, "Acertou? Comenta o que deu!", "Manda pra quem jura que é bom de conta")
    rodape(ImageDraw.Draw(img), W, H)
    return monta_reel(desafio, img, segundos, "descubra uma forma por linha, de cima para baixo", pasta)


# ---------------------------------------------------------------- triangulos numericos
REGRAS_TRI = [
    (lambda a, b, c: (b + c) * a, "(esquerda + direita) × topo", "o topo multiplica"),
    (lambda a, b, c: a * b - c, "topo × esquerda − direita", "multiplique dois e subtraia o terceiro"),
    (lambda a, b, c: a * c + b, "topo × direita + esquerda", "multiplique dois e some o terceiro"),
    (lambda a, b, c: (a - b) * c, "(topo − esquerda) × direita", "comece por uma subtração"),
    (lambda a, b, c: a * a - b * c, "topo² − esquerda × direita", "um dos números aparece ao quadrado"),
    (lambda a, b, c: (a + b) * c - a, "(topo + esquerda) × direita − topo", "o topo é usado duas vezes"),
]


def gera_triangulos(rng, idx_regra):
    regra, texto, dica = REGRAS_TRI[idx_regra % len(REGRAS_TRI)]
    for _ in range(500):
        tri = []
        while len(tri) < 4:
            a, b, c = rng.randint(2, 9), rng.randint(1, 9), rng.randint(1, 9)
            v = regra(a, b, c)
            if 1 <= v <= 120 and (a, b, c) not in [t[:3] for t in tri]:
                tri.append((a, b, c, v))
        # a regra precisa ser a unica da lista que explica os 3 exemplos
        outras = [r for j, r in enumerate(REGRAS_TRI) if j != idx_regra % len(REGRAS_TRI)]
        if not any(all(o[0](a, b, c) == v for a, b, c, v in tri[:3]) for o in outras):
            return dict(tri=tri, regra=texto, dica=dica, resposta=tri[3][3])
    raise RuntimeError("nao consegui gerar triangulos com regra unica")


def desenha_triangulo(d, cx, cy, a, b, c, centro, cor_centro=TINTA):
    s = 290
    top, esq, dir_ = (cx, cy - s * 0.55), (cx - s * 0.62, cy + s * 0.45), (cx + s * 0.62, cy + s * 0.45)
    d.polygon([top, esq, dir_], outline=ROXO_FORTE, width=10, fill=(244, 240, 255))
    f = fonte("Black", 58)
    for (x, y), n in zip([top, esq, dir_], [a, b, c]):
        d.ellipse((x - 42, y - 42, x + 42, y + 42), fill=AMARELO, outline=ROXO_FORTE, width=6)
        d.text((x, y + 2), str(n), font=f, fill=TINTA, anchor="mm")
    d.text((cx, cy + 40), str(centro), font=fonte("Black", 86), fill=cor_centro, anchor="mm")


def reel_triangulos(dados, num, pasta, segundos=15):
    centros = [(295, 720), (785, 720), (295, 1240), (785, 1240)]

    def quadro(revela):
        img = fundo(W, H)
        if revela:
            cabecalho(img, num, f"Resposta: {dados['resposta']}", f"Regra: {dados['regra']}")
        else:
            cabecalho(img, num, "Qual número falta?", "Só gênios acham em 15 segundos")
        d = cartao(img, CARD)
        for k, ((a, b, c, v), (x, y)) in enumerate(zip(dados["tri"], centros)):
            if k == 3:
                desenha_triangulo(d, x, y, a, b, c, v if revela else "?", VERDE if revela else ROSA)
            else:
                desenha_triangulo(d, x, y, a, b, c, v)
        if revela:
            faixa_resposta(img, "Acertou de primeira?", "Comenta e marca quem não ia conseguir")
        rodape(ImageDraw.Draw(img), W, H)
        return img

    return monta_reel(quadro(False), quadro(True), segundos, dados["dica"], pasta)


# ---------------------------------------------------------------- sequencias
def reel_sequencia(seq, dica, regra, num, pasta, segundos=15):
    pos = [(195, 760), (425, 760), (655, 760), (885, 760), (310, 1020), (540, 1020), (770, 1020)]

    def quadro(revela):
        img = fundo(W, H)
        if revela:
            cabecalho(img, num, f"Resposta: {seq[6]}", "Acertou? Comenta aí!")
        else:
            cabecalho(img, num, "Qual é o próximo?", "Só 3% acertam sem a dica")
        d = cartao(img, CARD)
        for k, (n, (x, y)) in enumerate(zip(seq, pos)):
            ultimo = k == 6
            cor = (VERDE if revela else ROSA) if ultimo else ROXO_FORTE
            d.ellipse((x - 100, y - 100, x + 100, y + 100), fill=(244, 240, 255), outline=cor, width=10)
            txt = str(n) if (not ultimo or revela) else "?"
            f = fonte("Black", 84)
            while d.textlength(txt, font=f) > 160:
                f = fonte("Black", f.size - 4)
            d.text((x, y + 4), txt, font=f, fill=cor if ultimo else TINTA, anchor="mm")
            if k < 6:
                # setinha para o proximo
                nx, ny = pos[k + 1]
                if ny == y:
                    d.text(((x + nx) / 2, y), "›", font=fonte("Black", 70), fill=CINZA, anchor="mm")
        if revela:
            texto_centro(d, 540, 1200, regra, fonte("Bold", 50), TINTA, max_w=860)
            faixa_resposta(img, "Você acertou?", "Manda pra aquele amigo que adora matemática")
        rodape(ImageDraw.Draw(img), W, H)
        return img

    return monta_reel(quadro(False), quadro(True), segundos, dica, pasta)
