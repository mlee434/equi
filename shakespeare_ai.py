"""
AI/LLM client functionality for Shakespeare RAG chatbot.
Handles OpenAI interactions, collection selection, and response generation.
"""

import os
from typing import List, Dict, Any
from openai import OpenAI
from rich.console import Console

console = Console()


class ShakespeareAIClient:
    """Handles all AI/LLM interactions for the Shakespeare chatbot"""
    
    def __init__(self):
        self.client = None
        self._init_openai()
    
    def _init_openai(self) -> bool:
        """Initialize OpenAI client"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return False
            
            self.client = OpenAI(api_key=api_key)
            return True
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if OpenAI client is available"""
        return self.client is not None
    
    def test_connection(self) -> bool:
        """Test OpenAI connectivity"""
        if not self.client:
            console.print("❌ OpenAI client not initialized", style="red")
            return False
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'OpenAI connection test successful' if you can read this."}
                ],
                max_tokens=50
            )
            
            if response.choices and response.choices[0].message.content:
                console.print("✓ OpenAI generation working", style="green")
                console.print(f"Response: {response.choices[0].message.content.strip()}", style="dim")
                return True
            else:
                console.print("⚠️ OpenAI returned empty response", style="yellow")
                return False
                
        except Exception as e:
            console.print(f"❌ OpenAI connectivity issues: {e}", style="red")
            return False
    
    def determine_relevant_collections(self, query: str) -> List[str]:
        """Use OpenAI to determine which collection(s) are most relevant for the query"""
        if not self.client:
            # Fallback: search all collections if OpenAI not available
            return ["plays", "sonnets", "poems"]
        
        try:
            system_prompt = """You are a Shakespeare expert. Given a user's question about Shakespeare's works, determine which collection(s) would be most relevant to search.

Collections available:
- "plays": All 37 dramatic works (tragedies, comedies, histories) with characters, dialogue, scenes
- "sonnets": The 154 sonnets - love poetry, philosophical reflections, personal themes  
- "poems": Other poetry (Venus and Adonis, Rape of Lucrece, Lover's Complaint) - narrative poems

Rules:
1. Return ONLY the collection name(s) that would contain the answer
2. If asking about specific plays, characters, scenes, dialogue, or dramatic elements → "plays"
3. If asking about sonnets specifically, love poetry, or sonnet themes → "sonnets"  
4. If asking about narrative poems like Venus & Adonis → "poems"
5. For general themes that could span multiple types, choose the most likely primary source
6. Return comma-separated list if multiple collections needed
7. Be conservative - prefer fewer, more focused searches

Examples:
- "What does Hamlet say about death?" → "plays"
- "Show me sonnets about love" → "sonnets" 
- "Tell me about Venus and Adonis" → "poems"
- "Shakespeare's view on love" → "sonnets"
- "Who is Iago?" → "plays"
- "Compare themes across all works" → "plays,sonnets,poems"

Respond with ONLY the collection name(s), nothing else."""

            user_prompt = f"Query: {query}"

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=50,
                temperature=0.1  # Low temperature for consistency
            )
            
            if response.choices and response.choices[0].message.content:
                collections_str = response.choices[0].message.content.strip().lower()
                # Parse comma-separated collections
                collections = [c.strip() for c in collections_str.split(",")]
                # Validate and filter
                valid_collections = [c for c in collections if c in ["plays", "sonnets", "poems"]]
                
                if valid_collections:
                    console.print(f"🎯 Targeting collections: {', '.join(valid_collections)}", style="dim blue")
                    return valid_collections
                    
        except Exception as e:
            console.print(f"Collection selection failed: {e}", style="dim yellow")
        
        # Fallback to all collections
        return ["plays", "sonnets", "poems"]
    
    def generate_response(self, query: str, context_parts: List[str], citation_parts: List[str], 
                         conversation_history: List[Dict] = None) -> str:
        """Generate a response using OpenAI with the retrieved context"""
        if not self.client:
            return self._create_fallback_response(query, context_parts, citation_parts)
        
        try:
            # Create context text
            context_text = "\n\n".join(context_parts[:5])  # Limit context to top 5
            
            # DEBUG: Print the entire context being sent to OpenAI
            print("=" * 80)
            print("🐛 DEBUG: ENTIRE CONTEXT BEING SENT TO OPENAI")
            print("=" * 80)
            print(f"Query: {query}")
            print(f"Number of context parts: {len(context_parts)}")
            print("-" * 40)
            print("Context text:")
            print(context_text)
            print("=" * 80)
            
            system_prompt = """You are a knowledgeable Shakespeare scholar and literary expert. Your task is to answer questions about Shakespeare's works using only the provided passages as evidence.

Guidelines:
- Base your answer strictly on the provided passages
- Be specific about which works, acts, scenes, or sonnets you're referencing
- If the passages don't fully answer the question, acknowledge what they do and don't reveal
- Maintain an engaging, scholarly tone
- Include relevant quotes when they strengthen your answer"""

            user_prompt = f"""Question: {query}

Relevant passages from Shakespeare's works:
{context_text}

Please provide a comprehensive answer based on these passages."""

            # Build messages list with conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                # Only include recent conversation to avoid token limits
                recent_history = conversation_history[-6:]  # Last 3 exchanges
                messages.extend(recent_history)
            
            # Add current user prompt
            messages.append({"role": "user", "content": user_prompt})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )
            
            if response.choices and response.choices[0].message.content:
                generated_response = response.choices[0].message.content.strip()
                if len(generated_response) > 10:
                    return generated_response
                    
        except Exception as e:
            console.print(f"OpenAI generation failed, using fallback response: {e}", style="yellow")
        
        # Fallback to structured response
        return self._create_fallback_response(query, context_parts, citation_parts)
    
    def _create_fallback_response(self, query: str, context_parts: List[str], citation_parts: List[str]) -> str:
        """Create a structured response when AI generation fails"""
        query_lower = query.lower()
        
        response_parts = []
        
        if "who is" in query_lower or "who was" in query_lower:
            response_parts.append("Based on the passages I found, here's what Shakespeare's works tell us:")
        elif "what" in query_lower and ("say" in query_lower or "says" in query_lower):
            response_parts.append("Here are the relevant passages where characters speak about this topic:")
        elif "sonnet" in query_lower:
            response_parts.append("I found these relevant sonnets:")
        else:
            response_parts.append("Here are the most relevant passages from Shakespeare's works:")
        
        response_parts.append("")
        
        # Add the best contexts with better formatting
        for i, (context, citation) in enumerate(zip(context_parts[:5], citation_parts[:5]), 1):
            # Extract just the content part
            if ": " in context:
                content = context.split(": ", 1)[1]
            else:
                content = context
            
            response_parts.append(f"**{i}. {citation}:**")
            response_parts.append(f"{content}")
            response_parts.append("")
        
        # Add a concluding statement
        if len(context_parts) > 1:
            response_parts.append("These passages show different perspectives on your query from Shakespeare's works.")
        else:
            response_parts.append("This passage addresses your query from Shakespeare's works.")
        
        return "\n".join(response_parts)
    
    def test_collection_selection(self) -> None:
        """Test collection selection with sample queries"""
        if not self.client:
            console.print("❌ OpenAI client not available for collection selection test", style="red")
            return
        
        try:
            console.print("Testing smart collection selection...")
            test_queries = [
                "What does Hamlet say about death?",
                "Show me sonnets about love",
                "Tell me about Venus and Adonis"
            ]
            
            for test_query in test_queries:
                selected = self.determine_relevant_collections(test_query)
                console.print(f"  '{test_query}' → {selected}", style="dim")
                
        except Exception as e:
            console.print(f"Collection selection test failed: {e}", style="yellow")