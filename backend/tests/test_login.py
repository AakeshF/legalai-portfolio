#!/usr/bin/env python3
import requests
import json

# Test login endpoint
url = "http://localhost:8000/api/auth/login"
data = {"email": "[email@example.com]", "password": "testpassword123"}

headers = {"Content-Type": "application/json", "Origin": "http://localhost:3000"}

print("Testing login endpoint...")
try:
    response = requests.post(url, json=data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        print("✅ Login successful!")
        data = response.json()
        print(f"Access Token: {data.get('access_token', '')[:50]}...")
    else:
        print("❌ Login failed")

except Exception as e:
    print(f"❌ Error: {e}")
