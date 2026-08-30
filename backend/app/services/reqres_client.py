import os
import requests

REQRES_API_KEY = os.environ.get("REQRES_API_KEY")
REQRES_BASE_URL = "https://reqres.in/api"
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"


def _headers():
    return {"x-api-key": REQRES_API_KEY}


def get_users(page=1):
    """Retourne des utilisateurs de test via ReqRes."""
    resp = requests.get(f"{REQRES_BASE_URL}/users", params={"page": page}, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_user(user_id):
    resp = requests.get(f"{REQRES_BASE_URL}/users/{user_id}", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def create_user(name, job):
    resp = requests.post(f"{REQRES_BASE_URL}/users", json={"name": name, "job": job}, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
