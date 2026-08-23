with open('test_marketplace.py', 'r') as f:
    content = f.read()

changes = 0

old_start = "def _register_and_login(client, username='vendeur1', email='vendeur1@example.com'):"
new_start = """from unittest.mock import patch, MagicMock


def _register_and_login(client, username='vendeur1', email='vendeur1@example.com'):"""

if old_start in content:
    content = content.replace(old_start, new_start)
    changes += 1
    print("1/2 OK: import mock ajoute")
else:
    print("1/2 ERREUR: debut de fichier non trouve")

old = """def test_purchase_by_other_user(client):
    _register_and_login(client, username='vendeur2', email='vendeur2@example.com')
    create_resp = client.post('/api/marketplace', data={
        'titre': 'App a acheter',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    listing_id = create_resp.get_json()['id']
    client.post('/api/auth/logout')

    _register_and_login(client, username='acheteur1', email='acheteur1@example.com')
    response = client.post(f'/api/marketplace/{listing_id}/purchase')
    assert response.status_code == 201
    data = response.get_json()
    assert data['commission_centimes'] == 200
    assert data['montant_vendeur_centimes'] == 800"""

new = """def test_purchase_by_other_user(client):
    _register_and_login(client, username='vendeur2', email='vendeur2@example.com')
    create_resp = client.post('/api/marketplace', data={
        'titre': 'App a acheter',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    listing_id = create_resp.get_json()['id']
    client.post('/api/auth/logout')

    _register_and_login(client, username='acheteur1', email='acheteur1@example.com')

    mock_transaction = MagicMock()
    mock_transaction.id = 12345
    mock_token = MagicMock()
    mock_token.url = 'https://sandbox.fedapay.com/pay/fake-token'
    mock_transaction.generate_token.return_value = mock_token

    with patch('app.routes.marketplace.fedapay.Transaction.create', return_value=mock_transaction):
        response = client.post(f'/api/marketplace/{listing_id}/purchase')

    assert response.status_code == 201
    data = response.get_json()
    assert data['purchase']['commission_centimes'] == 200
    assert data['purchase']['montant_vendeur_centimes'] == 800
    assert data['payment_url'] == 'https://sandbox.fedapay.com/pay/fake-token'"""

if old in content:
    content = content.replace(old, new)
    changes += 1
    print("2/2 OK: test corrige avec mock FedaPay")
else:
    print("2/2 ERREUR: test original non trouve")

with open('test_marketplace.py', 'w') as f:
    f.write(content)

print(f"Total: {changes}/2")
