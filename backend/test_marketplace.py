from unittest.mock import patch, MagicMock


def _register_and_login(client, username='vendeur1', email='vendeur1@example.com'):
    client.post('/api/auth/register', json={
        'username': username,
        'email': email,
        'password': 'motdepasse123'
    })


def test_list_marketplace_empty(client):
    response = client.get('/api/marketplace')
    assert response.status_code == 200
    data = response.get_json()
    assert data['listings'] == []
    assert data['total'] == 0


def test_create_listing_requires_login(client):
    response = client.post('/api/marketplace', data={
        'titre': 'Test',
        'description': 'Une description',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    assert response.status_code in (401, 403)


def test_create_listing_externe_lien(client):
    _register_and_login(client)
    response = client.post('/api/marketplace', data={
        'titre': 'Mon app',
        'description': 'Une description',
        'prix_centimes': '2500',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['titre'] == 'Mon app'
    assert data['prix_centimes'] == 2500
    assert data['favicon_url'] is not None


def test_create_listing_missing_fields(client):
    _register_and_login(client)
    response = client.post('/api/marketplace', data={'titre': 'Incomplet'})
    assert response.status_code == 400


def test_create_listing_invalid_source_type(client):
    _register_and_login(client)
    response = client.post('/api/marketplace', data={
        'titre': 'Test',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'inconnu'
    })
    assert response.status_code == 400


def test_list_marketplace_after_create(client):
    _register_and_login(client)
    client.post('/api/marketplace', data={
        'titre': 'App visible',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    response = client.get('/api/marketplace')
    data = response.get_json()
    assert data['total'] == 1
    assert data['listings'][0]['titre'] == 'App visible'


def test_search_filter(client):
    _register_and_login(client)
    client.post('/api/marketplace', data={
        'titre': 'Application Banque',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    client.post('/api/marketplace', data={
        'titre': 'Boutique en ligne',
        'description': 'desc',
        'prix_centimes': '2000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })

    response = client.get('/api/marketplace?q=Banque')
    data = response.get_json()
    assert data['total'] == 1
    assert data['listings'][0]['titre'] == 'Application Banque'


def test_price_filter(client):
    _register_and_login(client)
    client.post('/api/marketplace', data={
        'titre': 'App pas chere',
        'description': 'desc',
        'prix_centimes': '500',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    client.post('/api/marketplace', data={
        'titre': 'App chere',
        'description': 'desc',
        'prix_centimes': '5000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })

    response = client.get('/api/marketplace?prix_max=1000')
    data = response.get_json()
    assert data['total'] == 1
    assert data['listings'][0]['titre'] == 'App pas chere'


def test_purchase_requires_login(client):
    _register_and_login(client)
    create_resp = client.post('/api/marketplace', data={
        'titre': 'App a vendre',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    listing_id = create_resp.get_json()['id']
    client.post('/api/auth/logout')

    response = client.post(f'/api/marketplace/{listing_id}/purchase')
    assert response.status_code in (401, 403)


def test_cannot_purchase_own_listing(client):
    _register_and_login(client)
    create_resp = client.post('/api/marketplace', data={
        'titre': 'Mon app',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    listing_id = create_resp.get_json()['id']

    response = client.post(f'/api/marketplace/{listing_id}/purchase')
    assert response.status_code == 400
    assert 'propre application' in response.get_json()['error']


def test_purchase_by_other_user(client):
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

    mock_response = MagicMock()
    mock_response.json.return_value = {
        'v1/transaction': {
            'id': 12345,
            'payment_url': 'https://sandbox.fedapay.com/pay/fake-token'
        }
    }

    with patch('app.routes.marketplace.requests.post', return_value=mock_response):
        response = client.post(f'/api/marketplace/{listing_id}/purchase')

    assert response.status_code == 201
    data = response.get_json()
    assert data['purchase']['commission_centimes'] == 200
    assert data['purchase']['montant_vendeur_centimes'] == 800
    assert data['payment_url'] == 'https://sandbox.fedapay.com/pay/fake-token'


def test_delete_listing_requires_ownership(client):
    _register_and_login(client, username='vendeur3', email='vendeur3@example.com')
    create_resp = client.post('/api/marketplace', data={
        'titre': 'App proprietaire',
        'description': 'desc',
        'prix_centimes': '1000',
        'source_type': 'externe_lien',
        'lien_externe': 'https://example.com'
    })
    listing_id = create_resp.get_json()['id']
    client.post('/api/auth/logout')

    _register_and_login(client, username='autre', email='autre@example.com')
    response = client.delete(f'/api/marketplace/{listing_id}')
    assert response.status_code == 403
