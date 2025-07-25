#!/usr/bin/env python3
# test_auth_minimal.py - Minimal test to isolate the auth issue

import sys

sys.path.append(".")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth_routes import router as auth_router
from database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

# Create minimal app
app = FastAPI()
app.include_router(auth_router)

# Create test client
client = TestClient(app)


def test_login():
    """Test the login endpoint directly"""
    print("Testing login endpoint...")

    response = client.post(
        "/api/auth/login",
        json={"email": "[email@example.com]", "password": "testpassword123"},
    )

    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 500:
        # Try to get more details
        try:
            error = response.json()
            print(f"Error details: {error}")
        except:
            pass


if __name__ == "__main__":
    test_login()
