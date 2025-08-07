"""
FastAPI application for Shakespeare RAG Chatbot.
Simplified demo API with just a chat endpoint.
"""

from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from shakespeare_core import ShakespeareCoreProcessor
from rich.console import Console

console = Console()

# Global variables
core_processor = None


class QueryRequest(BaseModel):
    """Request model for chat queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="The user's question about Shakespeare")


class ChatResponse(BaseModel):
    """Response model for chat queries"""
    response: str = Field(..., description="The bot's response")
    timestamp: datetime = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime


async def initialize_shakespeare_bot():
    """Initialize the Shakespeare bot core processor"""
    global core_processor
    
    console.print("🎭 Initializing Shakespeare RAG API...", style="blue")
    core_processor = ShakespeareCoreProcessor()
    core_processor.initialize()
    console.print("✅ Shakespeare RAG API initialized successfully!", style="green")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await initialize_shakespeare_bot()
    yield
    # Shutdown
    if core_processor:
        core_processor.close()
    console.print("👋 Shakespeare RAG API shutdown complete", style="blue")


# Create FastAPI application
app = FastAPI(
    title="Shakespeare RAG Chatbot API",
    description="Demo API for the Shakespeare RAG Chatbot with semantic search and AI-powered responses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now()
    )


@app.delete("/conversation")
async def clear_conversation():
    """Clear the conversation history"""
    core_processor.clear_conversation_history()
    
    return {"message": "Conversation history cleared", "timestamp": datetime.now()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: QueryRequest):
    """
    Process a chat query and return a response.
    
    Conversation history is managed by the core processor.
    """
    response = core_processor.process_query(
        request.query,
        use_smart_selection=True
    )
    
    return ChatResponse(
        response=response,
        timestamp=datetime.now()
    )

