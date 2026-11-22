# Histórias Reais — automação de posts no Instagram

Publica sozinho, de graça. Sem IA em tempo de execução: a arte é um template e as legendas já estão prontas no `posts.json`.

## Como funciona (fluxo)

```
GitHub Actions (cron dia sim, dia não)
   └─ publish.py
        1. pega o próximo post do posts.json (o primeiro cuja imagem ainda não existe)
        2. render_card.py desenha o card 1080x1080 em JPEG
        3. faz commit da imagem no repo -> ela ganha uma URL pública
        4. chama a API do Buffer -> o Buffer publica no Instagram
```

Nada de servidor pago, nada de mensalidade. O GitHub Actions é gratuito para repositórios públicos (e dá 2.000 min/mês em privado — este robô usa ~2 min por execução, ou seja ~30 min/mês).

## Custo

| Item | Custo |
|---|---|
| GitHub Actions | R$ 0 |
| Buffer (plano Free) | R$ 0 |
| API do Buffer (Free: 1 chave, 1.000 req/canal/mês) | R$ 0 |
| Geração de imagem (Pillow local) | R$ 0 |

## Passo a passo (montagem, uma vez só)

### 1. Buffer
1. Crie a conta gratuita em `buffer.com`.
2. Conecte o Instagram `@historiasreais00` (conta profissional — a sua de Criador serve).
3. Em **Settings → API**, gere uma **API key** (no Free é 1 chave).
4. Descubra o **channel id** do Instagram: abra o canal e copie da URL
   `https://publish.buffer.com/channel/<ESTE_E_O_ID>`.
   *(Alternativa: rode `BUFFER_API_KEY=... python3 setup_check.py`.)*
5. Em **Settings → Posting schedule**, defina o horário que o Buffer deve usar
   (ex.: 19:00 todos os dias). O script usa `addToQueue`, então ele respeita esse horário.

### 2. GitHub
1. Crie um repositório **privado** chamado, por exemplo, `historias-reais-auto`.
2. Envie todos os arquivos desta pasta para o repositório (branch `main`).
3. Em **Settings → Secrets and variables → Actions**, crie dois secrets:
   - `BUFFER_API_KEY` → a chave do passo 1.3
   - `BUFFER_CHANNEL_ID` → o id do passo 1.4
4. Em **Settings → Actions → General → Workflow permissions**, marque
   **Read and write permissions** (o robô precisa commitar a imagem).
5. Vá em **Actions → Publicar post do dia → Run workflow** com `dry_run = 1`
   para testar a geração da imagem sem publicar.
6. Depois rode de novo com `dry_run = 0` para o primeiro post de verdade.

Pronto. A partir daí ele publica dia sim, dia não, às 19h de Brasília, sem você fazer nada.

## Manutenção

- **Adicionar posts:** copie um bloco em `posts.json`, troque o `id` (sem espaços/acentos), a manchete, o apoio, a legenda e as hashtags. O script usa o primeiro `id` que ainda não tem imagem em `images/`.
- **Trocar a frequência:** edite o `cron` em `.github/workflows/postar.yml`.
  - Dia sim, dia não: `0 22 */2 * *` (~15/mês) ← padrão
  - Seg/Qua/Sex/Dom: `0 22 * * 0,1,3,5` (~17/mês)
  - Todo dia: `0 22 * * *` (~30/mês)
- **Trocar o visual:** `render_card.py` — cores, tamanhos de fonte e o desenho das pirâmides estão no topo, fáceis de ajustar.
- **Histórico:** cada execução grava uma linha em `log.jsonl` com a resposta do Buffer.

## Limites que você precisa saber

- **Buffer Free:** até 3 canais e **10 posts agendados por canal na fila**. Como o robô adiciona 1 por execução e 1 é publicado, a fila nunca enche. Se você mudar para "todo dia" e a fila crescer, o Buffer devolve erro — aí é só reduzir a frequência.
- **Instagram:** a API só aceita **JPEG** no feed — o script já gera JPEG (não troque para PNG).
- **Imagem por URL:** o Buffer recebe a imagem por link público. Por isso o commit no repositório é obrigatório; se o repositório for privado, o link `raw.githubusercontent.com` pode não abrir. **Se der erro de imagem, torne o repositório público** (as imagens já são públicas no feed de qualquer forma).
- **Workflows agendados em repositório público** são desativados após 60 dias sem atividade — mas o próprio robô commita a cada execução, então isso se resolve sozinho.
- **Repositório privado:** se preferir privado, use `PUBLIC_BASE_URL` apontando para onde as imagens estiverem públicas (Cloudflare R2, GitHub Pages, etc.).

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `publish.py` | o robô: escolhe o post, gera, commita e envia ao Buffer |
| `render_card.py` | desenha o card 1080x1080 com Pillow |
| `posts.json` | banco de posts (manchete, apoio, legenda, hashtags) |
| `setup_check.py` | ajuda a descobrir o `BUFFER_CHANNEL_ID` |
| `.github/workflows/postar.yml` | o agendamento (cron) |
| `images/` | cards já gerados (também serve de controle do que já saiu) |
