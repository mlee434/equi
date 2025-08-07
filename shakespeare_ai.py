"""
AI/LLM client functionality for Shakespeare RAG chatbot.
Handles OpenAI interactions, collection selection, and response generation.
"""

import os
from typing import List, Dict
from openai import OpenAI
from rich.console import Console

console = Console()

MODEL = "gpt-4o-mini"


class ShakespeareAIClient:
    """Handles all AI/LLM interactions for the Shakespeare chatbot"""
    
    def __init__(self):
        self.client = None
        self._init_openai()
    

    def _init_openai(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)


    def determine_relevant_collections(self, query: str) -> List[str]:
        """Use OpenAI to determine which collection(s) are most relevant for the query"""
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
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        collections_str = response.choices[0].message.content.strip().lower()
        collections = [c.strip() for c in collections_str.split(",")]
        valid_collections = [c for c in collections if c in ["plays", "sonnets", "poems"]]
        
        console.print(f"🎯 Targeting collections: {', '.join(valid_collections)}", style="dim blue")
        return valid_collections
    

    def generate_response(self, query: str, context_parts: List[str], citation_parts: List[str], 
                         conversation_history: List[Dict] = None) -> str:
        """Generate a response using OpenAI with the retrieved context"""
        context_text = "\n\n".join(context_parts[:5])
        
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

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            recent_history = conversation_history[-6:]
            messages.extend(recent_history)
        
        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
