"""
Core query processing functionality for Shakespeare RAG chatbot.
Orchestrates the entire pipeline from query to response.
"""

from typing import List, Dict, Any, Tuple, Optional
from rich.console import Console
from shakespeare_ai import ShakespeareAIClient
from shakespeare_search import ShakespeareSearchClient  
from shakespeare_semantic import ShakespeareSemanticProcessor

console = Console()


class ShakespeareCoreProcessor:
    """Main processor that orchestrates the Shakespeare RAG pipeline"""
    
    def __init__(self):
        self.ai_client = ShakespeareAIClient()
        self.search_client = ShakespeareSearchClient()
        self.semantic_processor = ShakespeareSemanticProcessor()
        self._connected = False
    
    def initialize(self) -> bool:
        """Initialize all components and connections"""
        console.print("🎭 Initializing Shakespeare RAG system...", style="blue")
        
        # Connect to Weaviate
        if not self.search_client.connect():
            return False
        
        # Check collections
        if not self.search_client.check_collections():
            return False
        
        # Check OpenAI (optional)
        if not self.ai_client.is_available():
            console.print("⚠️ OpenAI API key not configured - responses will use fallback mode", style="yellow")
            console.print("For better responses, set: export OPENAI_API_KEY='your-key'", style="yellow")
        
        self._connected = True
        console.print("✅ Shakespeare RAG system initialized successfully!", style="green")
        return True
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get collection statistics"""
        if not self._connected:
            return {}
        return self.search_client.get_collection_stats()
    
    def test_system(self) -> bool:
        """Test all system components"""
        if not self._connected:
            console.print("❌ System not initialized", style="red")
            return False
        
        console.print("🔍 Testing system components...", style="blue")
        
        # Test vector search
        search_ok = self.search_client.test_vector_search()
        
        # Test OpenAI
        ai_ok = self.ai_client.test_connection()
        
        # Test collection selection
        if ai_ok:
            self.ai_client.test_collection_selection()
        
        return search_ok and ai_ok
    
    def process_query(self, query: str, conversation_history: List[Dict] = None, 
                     use_smart_selection: bool = True) -> str:
        """
        Process a query and return a response using the Shakespeare RAG pipeline.
        
        Args:
            query: The user's question
            conversation_history: Previous conversation for context
            use_smart_selection: Whether to use AI-powered collection selection
            
        Returns:
            The generated response
        """
        if not self._connected:
            return "❌ Shakespeare RAG system not initialized. Please check connections."
        
        console.print(f"🔍 Processing query: {query}", style="blue")
        
        try:
            # Step 1: Determine which collections to search
            if use_smart_selection and self.ai_client.is_available():
                relevant_collections = self.ai_client.determine_relevant_collections(query)
                search_results = self.search_client.search_relevant_collections(
                    query, relevant_collections, limit_per_collection=5
                )
            else:
                console.print("🔍 Searching all collections...", style="dim blue")
                search_results = self.search_client.search_all_collections(query, limit_per_collection=3)
            
            # Step 2: Analyze search quality
            quality_analysis = self.semantic_processor.analyze_search_quality(search_results)
            console.print(f"📊 Search quality: {quality_analysis['quality']} "
                         f"({quality_analysis['total_results']} results, "
                         f"max relevance: {quality_analysis['max_score']:.3f})", style="dim")
            
            # Step 3: Build context from results
            context_parts, citation_parts = self.semantic_processor.build_context_from_results(
                query, search_results
            )
            
            if not context_parts:
                return "I couldn't find sufficiently relevant passages to answer your question. Try rephrasing or asking about a more specific topic."
            
            # Step 4: Generate response
            if self.ai_client.is_available() and quality_analysis['max_score'] > 0.1:
                console.print("🤖 Generating AI response...", style="dim blue")
                response = self.ai_client.generate_response(
                    query, context_parts, citation_parts, conversation_history
                )
            else:
                console.print("📝 Using structured response...", style="dim blue") 
                response = self.ai_client._create_fallback_response(
                    query, context_parts, citation_parts
                )
            
            return response
            
        except Exception as e:
            console.print(f"❌ Error processing query: {e}", style="red")
            return f"An error occurred while processing your query: {str(e)}"
    
    def process_query_all_collections(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Process query searching all collections (bypass smart selection)"""
        if not self._connected:
            return "❌ Shakespeare RAG system not initialized. Please check connections."
        
        console.print(f"🔍 Searching ALL collections for: {query}", style="blue")
        
        try:
            # Search all collections
            search_results = self.search_client.search_all_collections(query, limit_per_collection=3)
            
            # Analyze search quality
            quality_analysis = self.semantic_processor.analyze_search_quality(search_results)
            console.print(f"📊 Search quality: {quality_analysis['quality']} "
                         f"({quality_analysis['total_results']} results)", style="dim")
            
            # Build context from results
            context_parts, citation_parts = self.semantic_processor.build_context_from_results(
                query, search_results
            )
            
            if not context_parts:
                return "I couldn't find sufficiently relevant passages to answer your question."
            
            # Generate response
            if self.ai_client.is_available():
                response = self.ai_client.generate_response(
                    query, context_parts, citation_parts, conversation_history
                )
            else:
                response = self.ai_client._create_fallback_response(
                    query, context_parts, citation_parts
                )
            
            return response
            
        except Exception as e:
            console.print(f"❌ Error processing query: {e}", style="red")
            return f"An error occurred while processing your query: {str(e)}"
    
    def close(self):
        """Clean up connections"""
        if self.search_client:
            self.search_client.close()
        self._connected = False