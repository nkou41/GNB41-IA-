import os
import requests
import json

def load_env():
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k, v)

load_env()
api_key = os.environ.get('MISTRAL_API_KEY', '').strip()
if not api_key:
    print("ERREUR: MISTRAL_API_KEY non trouvee dans .env")
    exit(1)

response = requests.post(
    'https://api.mistral.ai/v1/chat/completions',
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
    json={
        'model': 'mistral-medium-latest',
        'messages': [{'role': 'user', 'content': 'Compte de 1 a 5, un chiffre par ligne.'}],
        'stream': True
    },
    stream=True,
    timeout=30
)

print(f"Code HTTP: {response.status_code}")
chunk_count = 0
for line in response.iter_lines(decode_unicode=True):
    if not line or not line.startswith('data: '):
        continue
    payload = line[len('data: '):]
    if payload.strip() == '[DONE]':
        print("--- FIN DU STREAM ---")
        break
    try:
        data = json.loads(payload)
        delta = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
        if delta:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {repr(delta)}")
    except json.JSONDecodeError:
        print(f"Ligne non-JSON ignoree: {payload[:50]}")

print(f"Total chunks recus: {chunk_count}")
