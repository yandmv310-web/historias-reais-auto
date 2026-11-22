"""
Descobre o BUFFER_CHANNEL_ID do Instagram.

Uso:
  BUFFER_API_KEY=xxxx python3 setup_check.py

Se a consulta não funcionar, pegue o id na barra de endereço do Buffer:
  https://publish.buffer.com/channel/<ESTE_E_O_ID>
"""
import json
import os
import sys

import requests

ENDPOINT = "https://api.buffer.com"


def gql(query, variables=None):
    r = requests.post(
        ENDPOINT,
        json={"query": query, "variables": variables or {}},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def main():
    if not os.environ.get("BUFFER_API_KEY"):
        print("Defina a variável BUFFER_API_KEY primeiro.")
        return 1

    print("1) Buscando organizações...")
    data = gql("{ account { id email organizations { id name } } }")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    orgs = ((data.get("data") or {}).get("account") or {}).get("organizations") or []
    if not orgs:
        print("Nenhuma organização encontrada.")
        return 1

    for org in orgs:
        print(f"\n2) Canais da organização {org['name']} ({org['id']}):")
        q = """
        query Channels($input: ChannelsInput!) {
          channels(input: $input) { id name service descriptor }
        }
        """
        try:
            ch = gql(q, {"input": {"organizationId": org["id"]}})
            print(json.dumps(ch, ensure_ascii=False, indent=2))
            print("\n>> Use como BUFFER_CHANNEL_ID o 'id' do canal com service=instagram")
        except Exception as e:  # noqa: BLE001
            print(f"Falhou: {e}")
            print("Pegue o id na URL: https://publish.buffer.com/channel/<ID>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
