"""
Automação de publicação do @historiasreais00.

Fluxo:
  1. pega o primeiro post do posts.json cuja imagem ainda não existe em images/
  2. renderiza o card (1080x1080 JPEG)
  3. commita a imagem no repositório (para ela ter uma URL pública)
  4. manda para o Buffer via API (plano Free), que publica no Instagram

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
IMAGES_DIR = ROOT / "images"
LOG_FILE = ROOT / "log.jsonl"

BUFFER_ENDPOINT = "https://api.buffer.com"


def load_posts():
    data = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    return data.get("handle", HANDLE), data["posts"]


def pick_next(posts):
    IMAGES_DIR.mkdir(exist_ok=True)
    existing = {p.stem for p in IMAGES_DIR.glob("*.jpg")}
    for post in posts:
        if post["id"] not in existing:
            return post
    return None


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check,
                          capture_output=True, text=True)


def commit_image(path: Path, post_id: str):
    """Commita a imagem para ela ficar acessível por URL pública."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return False
    git("config", "user.name", "historias-reais-bot")
    git("config", "user.email", "bot@users.noreply.github.com")
    git("add", str(path.relative_to(ROOT)))
    r = git("commit", "-m", f"post: {post_id}", check=False)
    if r.returncode != 0:
        return False
    git("push", check=False)
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
    query = """
    mutation CreatePost($input: PostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id dueAt status }
        }
        ... on MutationError { message }
      }
    }
    """
    variables = {
        "input": {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [{"image": {"url": image_url}}],
        }
    }
    r = requests.post(
        BUFFER_ENDPOINT,
        json={"query": query, "variables": variables},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def main():
    handle, posts = load_posts()
    post = pick_next(posts)
    if post is None:
        print("Banco de posts esgotado. Adicione novos itens em posts.json.")
        return 0

    out = IMAGES_DIR / f"{post['id']}.jpg"
    render(post["headline"], post["subtext"], str(out))
    print(f"[1/4] imagem gerada: {out.name}")

    text = f"{post['caption']}\n\n{post['hashtags']}"
    if os.environ.get("DRY_RUN") == "1":
        print("[dry-run] legenda:")
        print(text)
        return 0

    pushed = commit_image(out, post["id"])
    print(f"[2/4] imagem publicada no repositório: {pushed}")
    if not pushed and not os.environ.get("PUBLIC_BASE_URL"):
        print("ERRO: não consegui commitar a imagem, então ela não tem URL pública.")
        return 1

    url = public_url(out)
    print(f"[3/4] URL pública: {url}")

    data = create_buffer_post(os.environ["BUFFER_CHANNEL_ID"], text, url)
    print("[4/4] resposta do Buffer:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"post": post["id"], "url": url,
                            "buffer": data}, ensure_ascii=False) + "\n")

    if data.get("errors"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
