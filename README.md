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
3. **App na Meta** (developers.facebook.com):
   - Crie um app do tipo **Empresa/Business** e adicione o produto **Instagram**. Escolha *API setup with Instagram business login*.
   - Em *Generate access tokens*, adicione a conta **quebra.cuca.diario** e gere o token. Ele precisa das permissões `instagram_business_basic` e `instagram_business_content_publish`.
4. **Segredos do repositório** (*Settings → Secrets and variables → Actions → New repository secret*):
   - `IG_TOKEN`: o token gerado no passo 3.
   - `GH_PAT` (opcional, recomendado): um *fine-grained token* do GitHub com acesso só a este repositório e permissão **Secrets: Read and write**. Com ele, o token do Instagram é renovado sozinho toda semana. Sem ele, o token expira em 60 dias.
5. Em *Actions*, rode **Testar conexão com o Instagram**. Se aparecer "token ok - conta @quebra.cuca.diario", está tudo pronto.

## Uso no dia a dia

- Para publicar agora: *Actions → Publicar desafio do dia → Run workflow*.
- Para pausar: *Actions → Publicar desafio do dia → ⋯ → Disable workflow*.
- Para mudar o horário: edite o `cron` em `publicar.yml`. O horário é em UTC (Brasília = UTC−3).
