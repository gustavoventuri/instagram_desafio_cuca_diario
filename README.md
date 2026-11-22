# Robô do @quebra.cuca.diario

Gera e publica 1 desafio por dia no Instagram (18:47, horário de Brasília) usando a API oficial.

- `gerador.py`: cria os desafios. São Reels "ache o diferente" (com cronômetro, som e revelação) e carrosséis de formas e de sequências. O próprio código confere as respostas.
- `publicar.py`: publica o próximo post da fila e atualiza o `estado.json`.
- `docs/media/NNN/`: é a fila. O que já estiver lá é publicado na ordem. Quando a fila acaba, o robô gera o próximo sozinho.
- `.github/workflows/`: `publicar.yml` roda todo dia, `renovar_token.yml` roda toda segunda e `testar.yml` é acionado manualmente.

## Configuração (uma vez só)

1. **O repositório precisa ser público** para usar o GitHub Pages grátis, porque o Instagram baixa as mídias de uma URL pública. Não há segredos no código.
   *Settings → General → Change visibility → Public*
2. **GitHub Pages**: *Settings → Pages → Source: **GitHub Actions***.
3. **Token (usuário do sistema, não expira)**: em business.facebook.com → *Configurações* → *Usuários do sistema*:
   - Crie o usuário `quebra-cuca-bot` como Admin.
   - Em *Atribuir ativos*, dê a ele o **app** e o perfil do Instagram **@quebra.cuca.diario**, com controle total.
   - Clique em *Gerar token*, escolha o app, defina a expiração como **Nunca** e marque as permissões `instagram_basic` e `instagram_content_publish`.
4. **No GitHub** (*Settings → Secrets and variables → Actions*):
   - Na aba *Secrets*, crie `IG_TOKEN` com o token do passo 3.
   - Na aba *Variables*, crie `IG_USER_ID` com o ID do @quebra.cuca.diario. O ID aparece em business.facebook.com → *Configurações* → *Contas do Instagram*.
5. Em *Actions*, rode **Testar conexão com o Instagram**. Se aparecer "token ok - conta @quebra.cuca.diario", está tudo pronto.

## Uso no dia a dia

- Para publicar agora: *Actions → Publicar desafio do dia → Run workflow*.
- Para pausar: *Actions → Publicar desafio do dia → ⋯ → Disable workflow*.
- Para mudar o horário: edite o `cron` em `publicar.yml`. O horário é em UTC (Brasília = UTC−3).

## Respostas automáticas aos comentários (no celular, com o Fly)

Ficam na pasta `celular/` e rodam no Termux do celular servidor, usando o Fly (Llama 3.2 1B local):

- **Agenda:** a cada 10 minutos na 1ª hora depois do post, e 1 vez por hora até a 7ª hora.
- **Respostas neutras:** agradecem, incentivam e convidam a seguir. Nunca dizem se a pessoa acertou.
- **Filtros:** spam, links, ofensas e política são ignorados. Se o Fly gerar algo estranho, o robô usa uma frase pronta.

Instalação no Termux:
```
curl -fsSL https://raw.githubusercontent.com/gustavoventuri/instagram_desafio_cuca_diario/main/celular/instalar.sh | bash
nano ~/quebracuca/.env            # IG_TOKEN (precisa da permissão instagram_manage_comments)
cd ~/quebracuca && node responder.js --agora   # teste
tmux new-session -d -s quebracuca ~/quebracuca/laco.sh
```
O log fica em `~/quebracuca/respostas.log`.
