#!/usr/bin/env python3
# test_auth_with_middleware.py - Test auth with middleware

import sys

sys.path.append(".")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from auth_routes import router as auth_router
from auth_middleware import AuthenticationMiddleware
from database import engine, Base
from logger import setup_logging

# Setup logging
setup_logging(log_level="DEBUG", log_format="simple")

# Create tables
Base.metadata.create_all(bind=engine)

# Create app with middleware
app = FastAPI()

# Add authentication middleware
app.add_middleware(AuthenticationMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)

# Create test client
client = TestClient(app)


def test_login():
    """Test the login endpoint with middleware"""
    print("Testing login endpoint with middleware...")

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "[email@example.com]", "password": "testpassword123"},
        )

        print(f"Status code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text[:500]}...")  # First 500 chars

        if response.status_code == 500:
            # Try to get more details
            try:
                error = response.json()
                print(f"Error details: {error}")
            except:
                pass

    except Exception as e:
        print(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_login()
