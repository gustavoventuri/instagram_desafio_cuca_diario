"""Reels de curiosidades do @quebra.cuca.diario (serie das 11:43).

Cada curiosidade vem de um JSON escrito e verificado com fontes (pela tarefa semanal):
{
  "emoji": "🍯",
  "pergunta": "Mel pode durar 3.000 anos?",
  "resposta": "Sim!",
  "explicacao": ["frase 1", "frase 2", "frase 3"],
  "fonte": "Smithsonian Magazine",
  "fonte_url": "https://...",
  "legenda": "texto da legenda (sem hashtags; o rodape e adicionado aqui)"
}

Roteiro do Reel (~14s): pergunta (0-3.5s) -> resposta + explicacao linha a linha -> chamada para seguir.
Uso: python curiosidades.py <arquivo.json> <pasta_saida> <numero_inicial>
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from gerador import AMARELO, BRANCO, TINTA, cartao, fonte, fundo, gera_audio, pilula, rodape, texto_centro

W, H, FPS = 1080, 1920, 30
EMOJI_FONTE = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
TAGS = "#curiosidades #vocesabia #ciencia #fatoscuriosos #conhecimento"
ROXO_FORTE = (120, 60, 230)
CINZA = (110, 100, 150)


def desenha_emoji(img, emoji, cx, cy, tamanho):
    """Desenha um emoji colorido (Noto Color Emoji so renderiza no tamanho 109; redimensiona depois)."""
    if not emoji or not os.path.exists(EMOJI_FONTE):
        return
    f = ImageFont.truetype(EMOJI_FONTE, 109)
    tmp = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((80, 80), emoji, font=f, embedded_color=True, anchor="mm")
    tmp = tmp.crop(tmp.getbbox() or (0, 0, 160, 160)).resize((tamanho, tamanho), Image.LANCZOS)
    img.paste(tmp, (int(cx - tamanho / 2), int(cy - tamanho / 2)), tmp)


def quadro_pergunta(item, num):
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 110, "VOCÊ SABIA?", fonte("Black", 48))
    desenha_emoji(img, item.get("emoji"), 540, 560, 320)
    d = ImageDraw.Draw(img)
    f = fonte("Black", 100)
    texto_centro(d, 540, 820, item["pergunta"], f, max_w=940, entre=1.12)
    texto_centro(d, 540, 1380, "Comenta seu palpite antes da resposta!", fonte("SemiBold", 50), AMARELO, max_w=940)
    rodape(d, W, H, f"curiosidade #{num:03d}")
    return img


def quadro_resposta(item, num, linhas_visiveis):
    img = fundo(W, H)
    d = ImageDraw.Draw(img)
    pilula(d, 540, 110, "VOCÊ SABIA?", fonte("Black", 48))
    desenha_emoji(img, item.get("emoji"), 540, 330, 190)
    d = ImageDraw.Draw(img)
    f = fonte("Black", 120)
    while d.textlength(item["resposta"], font=f) > 960:
        f = fonte("Black", f.size - 4)
    d.text((540, 520), item["resposta"], font=f, fill=AMARELO, anchor="mm")
    d = cartao(img, (60, 650, 1020, 1560))
    y = 720
    for i, linha in enumerate(item["explicacao"]):
        if i >= linhas_visiveis:
            break
        y = texto_centro(d, 540, y, linha, fonte("Bold", 54), TINTA, max_w=860, entre=1.18) + 40
    d.text((540, 1500), f"Fonte: {item['fonte']}", font=fonte("SemiBold", 36), fill=CINZA, anchor="mm")
    rodape(ImageDraw.Draw(img), W, H, "Siga para 1 curiosidade por dia")
    return img


def monta(item, num, pasta):
    os.makedirs(pasta, exist_ok=True)
    frames = os.path.join(pasta, "frames")
    os.makedirs(frames, exist_ok=True)
    n_linhas = len(item["explicacao"])
    t_perg, t_linha, t_fim_extra = 3.5, 3.2, 2.5
    t_fim = t_perg + n_linhas * t_linha + t_fim_extra
    cache = {}
    for i in range(int(t_fim * FPS)):
        t = i / FPS
        chave = "p" if t < t_perg else min(n_linhas, 1 + int((t - t_perg) / t_linha))
        if chave not in cache:
            cache[chave] = quadro_pergunta(item, num) if chave == "p" else quadro_resposta(item, num, chave)
        cache[chave].save(os.path.join(frames, f"{i:04d}.jpg"), quality=90)
    wav = os.path.join(pasta, "audio.wav")
    gera_audio(wav, t_fim, t_perg)
    mp4 = os.path.join(pasta, "reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames, "%04d.jpg"),
                    "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4], check=True)
    cache["p"].save(os.path.join(pasta, "capa.jpg"), quality=93)
    subprocess.run(["rm", "-rf", frames, wav])
    legenda = (f"{item['legenda']}\n\nFonte: {item['fonte']} ({item['fonte_url']})\n\n"
               f"Siga @quebra.cuca.diario: curiosidade às 11:43 e desafio às 18:47 🧩\n\n{TAGS}")
    post = dict(num=num, tipo="reel", serie="curiosidades", arquivos=["reel.mp4"], resposta=item["resposta"],
                legenda=legenda, fonte_url=item["fonte_url"])
    with open(os.path.join(pasta, "post.json"), "w") as fh:
        json.dump(post, fh, ensure_ascii=False, indent=2)
    return post


if __name__ == "__main__":
    itens = json.load(open(sys.argv[1]))
    for k, it in enumerate(itens):
        n = int(sys.argv[3]) + k
        monta(it, n, os.path.join(sys.argv[2], f"{n:03d}"))
        print(f"curiosidade #{n:03d}: {it['pergunta']}")
