#!/usr/bin/env python3
import os
import sys

# Set the environment variable BEFORE importing config
os.environ["DISABLE_AUTH"] = "True"
os.environ["DEBUG"] = "True"  # Enable debug mode to see config loading

# Now import the config
from config import settings

print(f"Auth disabled setting: {settings.disable_auth}")
print(f"DISABLE_AUTH env var: {os.getenv('DISABLE_AUTH')}")
print(f"Settings dict: {settings.dict()}")

# Test that it's working
if settings.disable_auth:
    print("✅ Authentication is DISABLED - API endpoints should work without auth")
else:
    print("❌ Authentication is ENABLED - API endpoints will require auth")

# Start the server if requested
if len(sys.argv) > 1 and sys.argv[1] == "start":
    import uvicorn

    print("\nStarting server with auth disabled...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
