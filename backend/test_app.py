def test_app_exists(app):
    assert app is not None


def test_404_json(client):
    response = client.get('/api/route-inexistante')
    assert response.status_code == 404
    assert response.get_json()['error'] == 'Ressource introuvable'


def test_auth_me_requires_login(client):
    response = client.get('/api/auth/me')
    assert response.status_code in (401, 403)


def test_register_and_login(client):
    response = client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'motdepasse123'
    })
    assert response.status_code in (200, 201)

    response = client.get('/api/auth/me')
    assert response.status_code == 200
    assert response.get_json()['username'] == 'testuser'


def test_create_workspace_requires_login(client):
    response = client.post('/api/workspaces', json={'nom': 'Test'})
    assert response.status_code in (401, 403)


def test_full_workspace_flow(client):
    client.post('/api/auth/register', json={
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password': 'motdepasse123'
    })

    response = client.post('/api/workspaces', json={'nom': 'Mon espace'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['nom'] == 'Mon espace'

    response = client.get('/api/workspaces')
    assert response.status_code == 200
    assert len(response.get_json()) == 1
