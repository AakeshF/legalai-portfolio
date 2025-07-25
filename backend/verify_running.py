#!/usr/bin/env python3
"""Verify the backend is running"""

import subprocess
import time
import sys

# Start the server in background
print("Starting backend server...")
process = subprocess.Popen(
    [sys.executable, "start.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

# Wait a bit for server to start
print("Waiting for server to initialize...")
time.sleep(10)

# Test with curl
print("\nTesting server endpoints...")
result = subprocess.run(
    ["curl", "-s", "http://localhost:8000/"], capture_output=True, text=True
)

if result.returncode == 0:
    print("✅ Server is running!")
    print(
        "Response:",
        result.stdout[:100] + "..." if len(result.stdout) > 100 else result.stdout,
    )
else:
    print("❌ Server test failed")
    print("Error:", result.stderr)

# Test API docs
result = subprocess.run(
    [
        "curl",
        "-s",
        "-o",
        "/dev/null",
        "-w",
        "%{http_code}",
        "http://localhost:8000/docs",
    ],
    capture_output=True,
    text=True,
)
print(f"\nAPI Docs status code: {result.stdout}")

# Clean up
process.terminate()
print("\nBackend server stopped.")
