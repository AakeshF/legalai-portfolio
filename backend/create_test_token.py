#!/usr/bin/env python3
"""Create a test JWT token for API testing"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_utils import create_access_token
from datetime import timedelta

# Create a test token
test_data = {
    "sub": "test-user-id",
    "email": "[email@example.com]",
    "organization_id": "test-org-id"
}

token = create_access_token(
    data=test_data,
    expires_delta=timedelta(hours=1)
)

print(f"Test token created:")
print(f"\nToken: {token}")
print(f"\nUse in API calls with:")
print(f'curl -H "Authorization: Bearer {token}" ...')
print(f"\nOr in test script:")
print(f'AUTH_TOKEN = "{token}"')