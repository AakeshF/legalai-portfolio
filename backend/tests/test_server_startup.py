#!/usr/bin/env python3
# test_server_startup.py - Test if the server can start without errors
import subprocess
import time
import requests
import os
import signal
import sys


def test_server_startup():
    """Start the server and test if it's responding"""
    print("Starting FastAPI server...")

    # Start the server as a subprocess
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"  # Ensure output is not buffered

    proc = subprocess.Popen(
        [sys.executable, "start.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    # Give the server time to start
    print("Waiting for server to start...")
    time.sleep(5)

    # Check if process is still running
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print("Server failed to start!")
        print(f"STDOUT:\n{stdout}")
        print(f"STDERR:\n{stderr}")
        return False

    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✓ Server is running and responding to health check")

            # Now test the login endpoint
            print("\nTesting login endpoint...")
            login_data = {"email": "[email@example.com]", "password": "testpassword123"}

            login_response = requests.post(
                "http://localhost:8000/api/auth/login", json=login_data
            )

            print(f"Login response status: {login_response.status_code}")
            print(f"Login response: {login_response.text}")

            if login_response.status_code == 200:
                print("✓ Login successful!")
            else:
                print("✗ Login failed")

        else:
            print(f"✗ Health check failed: {response.status_code}")

    except Exception as e:
        print(f"✗ Error testing server: {e}")

        # Get server output
        stdout, stderr = proc.communicate(timeout=1)
        if stdout:
            print(f"\nServer STDOUT:\n{stdout}")
        if stderr:
            print(f"\nServer STDERR:\n{stderr}")

    finally:
        # Stop the server
        print("\nStopping server...")
        os.kill(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
        print("Server stopped")


if __name__ == "__main__":
    test_server_startup()
