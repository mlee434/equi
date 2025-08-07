"""
Core query processing functionality for Shakespeare RAG chatbot.
Orchestrates the entire pipeline from query to response.
"""

from typing import List, Dict
from rich.console import Console
from shakespeare_ai import ShakespeareAIClient
from shakespeare_search import ShakespeareSearchClient  
import format_context

console = Console()


class ShakespeareCoreProcessor:
    """Main processor that orchestrates the Shakespeare RAG pipeline"""
    
    def __init__(self):
        self.ai_client = ShakespeareAIClient()
        self.search_client = ShakespeareSearchClient()
        self.conversation_history: List[Dict] = []
        self._connected = False
    

    def initialize(self):
        """Initialize all components and connections"""
        console.print("🎭 Initializing Shakespeare RAG system...", style="blue")
        
        self.search_client.connect()
        
        self._connected = True
        console.print("✅ Shakespeare RAG system initialized successfully!", style="green")


    def process_query(self, query: str, use_smart_selection: bool = True) -> str:
        """
        Process a query and return a response using the Shakespeare RAG pipeline.
        
        Args:
            query: The user's question
            use_smart_selection: Whether to use AI-powered collection selection
            
        Returns:
            The generated response
        """
        console.print(f"🔍 Processing query: {query}", style="blue")
        
        if use_smart_selection:
            relevant_collections = self.ai_client.determine_relevant_collections(query)
            search_results = self.search_client.search_relevant_collections(
                query, relevant_collections, limit_per_collection=5
            )
        else:
            console.print("🔍 Searching all collections...", style="dim blue")
            search_results = self.search_client.search_all_collections(query, limit_per_collection=3)
        
        quality_analysis = format_context.analyze_search_quality(search_results)
        console.print(f"📊 Search quality: {quality_analysis['quality']} "
                     f"({quality_analysis['total_results']} results, "
                     f"max relevance: {quality_analysis['max_score']:.3f})", style="dim")
        
        context_parts, citation_parts = format_context.build_context_from_results(
            query, search_results
        )
        
        console.print("🤖 Generating AI response...", style="dim blue")
        response = self.ai_client.generate_response(
            query, context_parts, citation_parts, self.conversation_history
        )
        
        # Add this exchange to conversation history
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Keep only the last 10 exchanges (20 messages) to prevent context from getting too long
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        console.print(f"💬 Conversation history now has {len(self.conversation_history)} messages", style="dim")
        
        return response
    
    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
        console.print("🗑️ Conversation history cleared", style="dim blue")
    

    def close(self):
        """Clean up connections"""
        if self.search_client:
            self.search_client.close()
        self._connected = False