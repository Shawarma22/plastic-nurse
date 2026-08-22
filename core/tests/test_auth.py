from fastapi.testclient import TestClient

def test_login_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["username"] == "admin"

def test_login_invalid_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_read_current_user(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"

def test_register_user_as_admin(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "nurse1", "password": "securepassword", "role": "operator"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "nurse1"
    assert data["role"] == "operator"

def test_register_user_forbidden_for_operator(client: TestClient, operator_token: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "nurse2", "password": "securepassword", "role": "operator"},
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 403
