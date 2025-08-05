#!/usr/bin/env python3
"""
Startup script for the Shakespeare RAG API server.
Handles proper initialization and configuration.
"""

import sys
import os
import uvicorn
from rich.console import Console
from rich.panel import Panel

console = Console()


def check_dependencies():
    """Check that all required dependencies are available"""
    try:
        import fastapi
        import weaviate
        import openai
        return True
    except ImportError as e:
        console.print(f"❌ Missing dependency: {e}", style="red")
        console.print("Run: pip install -e . or uv sync", style="yellow")
        return False


def check_environment():
    """Check environment variables"""
    warnings = []
    
    if not os.getenv("OPENAI_API_KEY"):
        warnings.append("OPENAI_API_KEY not set - bot will use fallback responses")
    
    # Check Weaviate configuration (defaults are usually fine)
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    console.print(f"🔗 Weaviate URL: {weaviate_url}", style="dim")
    
    if warnings:
        for warning in warnings:
            console.print(f"⚠️ {warning}", style="yellow")
    
    return True


def main():
    """Main startup function"""
    # Print banner
    banner = Panel(
        """[bold blue]🎭 Shakespeare RAG Chatbot API 🎭[/bold blue]

Starting FastAPI server with:
• RESTful endpoints for chat queries
• Session-based conversation history  
• Automatic session cleanup
• CORS enabled for frontend integration
• Interactive API docs at /docs

[dim]Press Ctrl+C to stop the server[/dim]""",
        title="Shakespeare API Server",
        border_style="blue"
    )
    console.print(banner)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Shakespeare RAG API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    
    args = parser.parse_args()
    
    console.print(f"🚀 Starting server on {args.host}:{args.port}", style="green")
    console.print(f"📖 API Documentation: http://{args.host}:{args.port}/docs", style="cyan")
    console.print(f"🔄 Auto-reload: {'enabled' if args.reload else 'disabled'}", style="dim")
    
    try:
        # Start the server
        uvicorn.run(
            "api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,  # Workers and reload don't mix
            access_log=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        console.print("\n👋 Server stopped gracefully", style="green")
    except Exception as e:
        console.print(f"❌ Server error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()