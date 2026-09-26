import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db
from app.core.seed import seed_demo_data


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    await init_db()
    await seed_demo_data()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_auth_token(client: AsyncClient):
    """Authenticate demo admin and return JWT access token."""
    res = await client.post("/api/v1/auth/login", json={
        "username": "admin@stocksense.local",
        "password": "AdminPass@123"
    })
    assert res.status_code == 200
    otp = res.json()["data"]["dev_otp"]

    res_verify = await client.post("/api/v1/auth/login/verify-otp", json={
        "target_identifier": "admin@stocksense.local",
        "otp_code": otp,
        "purpose": "LOGIN"
    })
    assert res_verify.status_code == 200
    token = res_verify.json()["access_token"]
    return token
