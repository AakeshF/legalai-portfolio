#!/usr/bin/env python3
"""Test frontend authentication compatibility"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_frontend_registration():
    """Test registration with frontend format"""
    print("\n1. Testing Frontend Registration...")
    
    # Frontend format
    frontend_data = {
        "email": "[email@example.com]",
        "password": "SecurePassword123!",
        "full_name": "Test User",
        "organization_name": "Test Law Firm"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json=frontend_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Registration successful!")
        print(f"Access Token: {data.get('access_token', 'Not found')[:50]}...")
        print(f"User data included: {'user' in data}")
        return data.get('access_token'), data.get('refresh_token')
    else:
        print(f"❌ Registration failed: {response.text}")
        return None, None

def test_frontend_login():
    """Test login with frontend expectations"""
    print("\n2. Testing Frontend Login...")
    
    login_data = {
        "email": "[email@example.com]",
        "password": "SecurePassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Login successful!")
        print(f"Access Token: {data.get('access_token', 'Not found')[:50]}...")
        print(f"User data included: {'user' in data}")
        if 'user' in data:
            print(f"User email: {data['user'].get('email')}")
        return data.get('access_token'), data.get('refresh_token')
    else:
        print(f"❌ Login failed: {response.text}")
        return None, None

def test_get_current_user(access_token):
    """Test /me endpoint"""
    print("\n3. Testing Get Current User...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Get user successful!")
        print(f"User email: {data.get('email')}")
        print(f"Organization ID: {data.get('organization_id')}")
    else:
        print(f"❌ Get user failed: {response.text}")

def test_refresh_token(refresh_token):
    """Test refresh with frontend format"""
    print("\n4. Testing Token Refresh...")
    
    # Frontend sends refresh token in JSON body
    refresh_data = {
        "refresh_token": refresh_token
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/refresh", json=refresh_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Refresh successful!")
        print(f"New Access Token: {data.get('access_token', 'Not found')[:50]}...")
    else:
        print(f"❌ Refresh failed: {response.text}")

def main():
    print("Testing Frontend Auth Compatibility")
    print("===================================")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not running! Start it with: python start.py")
            sys.exit(1)
    except requests.ConnectionError:
        print("❌ Cannot connect to server! Start it with: python start.py")
        sys.exit(1)
    
    # Test registration
    access_token, refresh_token = test_frontend_registration()
    
    if not access_token:
        # Try login if registration failed (user might already exist)
        print("\nRegistration failed, trying login...")
        access_token, refresh_token = test_frontend_login()
    
    if access_token:
        # Test authenticated endpoints
        test_get_current_user(access_token)
        
        if refresh_token:
            test_refresh_token(refresh_token)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()