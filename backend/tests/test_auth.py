import pytest
import uuid
import random
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_registration_and_otp_verification(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    test_email = f"test_{uid}@example.com"
    test_mobile = f"98{random.randint(10000000, 99999999)}"

    # Step 1: Register new user
    reg_payload = {
        "full_name": "Test Engineer",
        "email": test_email,
        "mobile": test_mobile,
        "password": "SecurePassword@123",
        "confirm_password": "SecurePassword@123"
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    otp = data["data"]["dev_otp"]
    assert len(otp) == 6

    # Step 2: Duplicate email validation
    res_dup = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["error"]["message"]

    # Step 3: Verify with invalid OTP
    res_bad = await client.post("/api/v1/auth/verify-otp", json={
        "target_identifier": test_email,
        "otp_code": "000000",
        "purpose": "REGISTRATION"
    })
    assert res_bad.status_code == 400

    # Step 4: Verify with valid OTP
    res_good = await client.post("/api/v1/auth/verify-otp", json={
        "target_identifier": test_email,
        "otp_code": otp,
        "purpose": "REGISTRATION"
    })
    assert res_good.status_code == 200
    token_data = res_good.json()
    assert "access_token" in token_data
    assert token_data["user"]["email"] == test_email
    assert token_data["user"]["is_verified"] is True


@pytest.mark.asyncio
async def test_login_2fa_flow(client: AsyncClient):
    # Step 1: Login with invalid password
    res_fail = await client.post("/api/v1/auth/login", json={
        "username": "admin@stocksense.local",
        "password": "WrongPassword!"
    })
    assert res_fail.status_code == 401

    # Step 2: Login with valid credentials
    res_step1 = await client.post("/api/v1/auth/login", json={
        "username": "admin@stocksense.local",
        "password": "AdminPass@123"
    })
    assert res_step1.status_code == 200
    otp = res_step1.json()["data"]["dev_otp"]
    assert len(otp) == 6

    # Step 3: Verify OTP and receive JWT
    res_step2 = await client.post("/api/v1/auth/login/verify-otp", json={
        "target_identifier": "admin@stocksense.local",
        "otp_code": otp,
        "purpose": "LOGIN"
    })
    assert res_step2.status_code == 200
    access_token = res_step2.json()["access_token"]

    # Step 4: Verify profile access on /me
    res_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "admin@stocksense.local"
    assert "ADMIN" in res_me.json()["roles"]
