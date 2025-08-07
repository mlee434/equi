#!/usr/bin/env python3
"""
Minimal startup script to run the FastAPI app without CLI flags.

Usage:
  python start_api.py

Optional environment variables:
  API_HOST   (default: 0.0.0.0)
  API_PORT   (default: 8000)
  API_RELOAD (default: false)
"""

import os
import uvicorn

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run("api:app", host=host, port=port)
