# start.py - Application startup script
import uvicorn
import os
from config import settings

def start_server():
    """Start the FastAPI server with proper configuration"""
    
    # Ensure upload directory exists
    os.makedirs(settings.upload_directory, exist_ok=True)
    
    # Start server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )

if __name__ == "__main__":
    start_server()