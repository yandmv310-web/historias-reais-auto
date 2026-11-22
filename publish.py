"""
Automação de publicação do @historiasreais00.

Fluxo:
  1. pega o primeiro post do posts.json que ainda NÃO está em published.json
  2. renderiza o card (1080x1080 JPEG)
  3. commita a imagem no repositório (para ela ter uma URL pública)
  4. manda para o Buffer via API (plano Free), que publica no Instagram
  5. só se o Buffer aceitar, marca o post como publicado em published.json

Variáveis de ambiente:
  BUFFER_API_KEY     - chave da API do Buffer (obrigatória)
  BUFFER_CHANNEL_ID  - id do canal do Instagram no Buffer (obrigatória)
  GITHUB_REPOSITORY  - preenchida automaticamente pelo GitHub Actions
  GIT_BRANCH         - branch (padrão: main)
  PUBLIC_BASE_URL    - opcional: se você servir as imagens por outro lugar
  DRY_RUN            - "1" para só gerar a imagem, sem publicar
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

from render_card import render, HANDLE

ROOT = Path(__file__).resolve().parent
POSTS_FILE = ROOT / "posts.json"
PUBLISHED_FILE = ROOT / "published.json"
IMAGES_DIR = ROOT / "images"
LOG_FILE = ROOT / "log.jsonl"

BUFFER_ENDPOINT = "https://api.buffer.com"

MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post { id dueAt }
    }
    ... on MutationError { message }
  }
}
"""


def load_posts():
    data = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    return data["posts"]


def load_published():
    if PUBLISHED_FILE.exists():
        try:
            return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_published(ids):
    PUBLISHED_FILE.write_text(
        json.dumps(sorted(set(ids)), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def pick_next(posts, published):
    for post in posts:
        if post["id"] not in published:
            return post
    return None


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check,
                          capture_output=True, text=True)


def in_git(path: Path):
    r = git("ls-files", "--error-unmatch", str(path.relative_to(ROOT)), check=False)
    return r.returncode == 0


def commit_and_push(paths, message):
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return False
    git("config", "user.name", "historias-reais-bot")
    git("config", "user.email", "bot@users.noreply.github.com")
    for p in paths:
        git("add", str(p.relative_to(ROOT)), check=False)
    r = git("commit", "-m", message, check=False)
    if r.returncode != 0:
        print(f"  (git commit sem mudancas: {message})")
        return True
    p = git("push", check=False)
    if p.returncode != 0:
        print(f"  (git push falhou: {p.stderr.strip()[:300]})")
        return False
    return True


def public_url(path: Path):
    base = os.environ.get("PUBLIC_BASE_URL")
    rel = path.relative_to(ROOT).as_posix()
    if base:
        return f"{base.rstrip('/')}/{rel}"
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GIT_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{rel}"


def create_buffer_post(channel_id: str, text: str, image_url: str):
    variables = {
        "input": {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [{"image": {"url": image_url}}],
            # Instagram exige o tipo do post explicito
            "metadata": {
                "instagram": {
                    "type": "post",
                    "shouldShareToFeed": True,
                }
            },
        }
    }
    r = requests.post(
        BUFFER_ENDPOINT,
        json={"query": MUTATION, "variables": variables},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def main():
    posts = load_posts()
    published = load_published()
    post = pick_next(posts, published)
    if post is None:
        print("Banco de posts esgotado. Adicione novos itens em posts.json.")
        return 0

    print(f"Post escolhido: {post['id']}")

    out = IMAGES_DIR / f"{post['id']}.jpg"
    if out.exists():
        print(f"[1/4] imagem ja existia: {out.name}")
    else:
        render(post["headline"], post["subtext"], str(out))
        print(f"[1/4] imagem gerada: {out.name}")

    text = f"{post['caption']}\n\n{post['hashtags']}"

    if os.environ.get("DRY_RUN") == "1":
        print("[dry-run] nao vou publicar. Legenda:")
        print(text)
        return 0

    if in_git(out):
        print("[2/4] imagem ja estava no repositorio")
    else:
        ok = commit_and_push([out], f"post: {post['id']}")
        print(f"[2/4] imagem publicada no repositorio: {ok}")
        if not ok and not os.environ.get("PUBLIC_BASE_URL"):
            print("ERRO: a imagem precisa estar commitada para ter URL publica.")
            return 1

    url = public_url(out)
    print(f"[3/4] URL publica: {url}")

    data = create_buffer_post(os.environ["BUFFER_CHANNEL_ID"], text, url)
    print("[4/4] resposta do Buffer:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    body = data.get("data", {}).get("createPost", {}) or {}
    erros = data.get("errors") or body.get("message")
    if erros:
        print("ERRO do Buffer: o post NAO foi agendado e vai ser tentado de novo amanha.")
        return 1

    published.append(post["id"])
    save_published(published)
    commit_and_push([PUBLISHED_FILE], f"published: {post['id']}")

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"post": post["id"], "url": url,
                            "buffer": data}, ensure_ascii=False) + "\n")
    print(f"OK: {post['id']} agendado no Buffer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
