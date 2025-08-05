"""
Semantic context building and result formatting for Shakespeare RAG chatbot.
Handles context preparation and result formatting for different collection types.
"""

from typing import List, Dict, Any, Tuple
from rich.console import Console

console = Console()


class ShakespeareSemanticProcessor:
    """Handles semantic processing and context building for Shakespeare search results"""
    
    def __init__(self):
        pass
    
    def format_play_result(self, result: Dict[str, Any]) -> str:
        """Format a play search result for display"""
        props = result["properties"]
        score = result.get("score", 0)
        
        parts = []
        
        # Title and location info
        title = props.get("title", "Unknown Play")
        act = props.get("act")
        scene = props.get("scene")
        speaker = props.get("speaker")
        
        header = f"**{title}**"
        if act and scene:
            header += f" (Act {act}, Scene {scene})"
        if speaker:
            header += f" - {speaker}"
        
        parts.append(header)
        
        # Content
        content = props.get("content", "").strip()
        if content:
            # Truncate if too long
            if len(content) > 300:
                content = content[:300] + "..."
            parts.append(f"  {content}")
        
        # Metadata
        chunk_type = props.get("chunk_type", "")
        if chunk_type:
            parts.append(f"  *Type: {chunk_type}*")
        
        parts.append(f"  *Relevance: {score:.3f}*")
        
        return "\n".join(parts)
    
    def format_sonnet_result(self, result: Dict[str, Any]) -> str:
        """Format a sonnet search result for display"""
        props = result["properties"]
        score = result.get("score", 0)
        
        parts = []
        
        # Title
        sonnet_num = props.get("sonnet_number")
        title = f"**Sonnet {sonnet_num}**" if sonnet_num else "**Sonnet**"
        parts.append(title)
        
        # Content
        content = props.get("content", "").strip()
        if content:
            # For sonnets, show more content as they're shorter
            if len(content) > 500:
                content = content[:500] + "..."
            parts.append(f"  {content}")
        
        parts.append(f"  *Relevance: {score:.3f}*")
        
        return "\n".join(parts)
    
    def format_poem_result(self, result: Dict[str, Any]) -> str:
        """Format a poem search result for display"""
        props = result["properties"]
        score = result.get("score", 0)
        
        parts = []
        
        # Title
        title = props.get("title", "Unknown Poem")
        stanza = props.get("stanza_number")
        
        header = f"**{title}**"
        if stanza:
            header += f" (Stanza {stanza})"
        
        parts.append(header)
        
        # Content
        content = props.get("content", "").strip()
        if content:
            if len(content) > 300:
                content = content[:300] + "..."
            parts.append(f"  {content}")
        
        # Metadata
        poem_type = props.get("poem_type", "")
        if poem_type:
            parts.append(f"  *Type: {poem_type}*")
        
        parts.append(f"  *Relevance: {score:.3f}*")
        
        return "\n".join(parts)
    
    def format_search_results(self, results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format all search results for display"""
        if not results:
            return "No relevant passages found."
        
        formatted_parts = []
        
        for collection_type, collection_results in results.items():
            if not collection_results:
                continue
                
            # Section header
            if collection_type == "plays":
                section_header = "🎭 **From Shakespeare's Plays:**"
            elif collection_type == "sonnets":
                section_header = "📜 **From Shakespeare's Sonnets:**"
            elif collection_type == "poems":
                section_header = "🖋️ **From Shakespeare's Poems:**"
            else:
                section_header = f"**From {collection_type}:**"
            
            formatted_parts.append(section_header)
            formatted_parts.append("")
            
            # Format each result
            for i, result in enumerate(collection_results, 1):
                if collection_type == "plays":
                    formatted_result = self.format_play_result(result)
                elif collection_type == "sonnets":
                    formatted_result = self.format_sonnet_result(result)
                elif collection_type == "poems":
                    formatted_result = self.format_poem_result(result)
                else:
                    formatted_result = str(result)
                
                formatted_parts.append(f"{i}. {formatted_result}")
                formatted_parts.append("")
        
        return "\n".join(formatted_parts)
    
    def build_context_from_results(self, query: str, search_results: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[str], List[str]]:
        """Build context and citations from search results for LLM processing"""
        if not search_results:
            return [], []
        
        # Filter results by relevance score
        filtered_results = {}
        total_good_results = 0
        
        for collection_type, results in search_results.items():
            good_results = []
            for result in results:
                score = result.get("score", 0)
                # Only include results with decent relevance
                if score > 0.1:  # Adjust threshold as needed
                    good_results.append(result)
                    total_good_results += 1
            if good_results:
                filtered_results[collection_type] = good_results
        
        # If no good results, lower the threshold
        if total_good_results == 0:
            for collection_type, results in search_results.items():
                if results:  # Take the best results even if low score
                    filtered_results[collection_type] = results[:2]
        
        # Prepare context from search results
        context_parts = []
        citation_parts = []
        
        for collection_type, results in filtered_results.items():
            for i, result in enumerate(results[:3]):  # Limit to top 3 per collection
                props = result["properties"]
                content = props.get("content", "").strip()
                score = result.get("score", 0)
                
                if content:
                    # Add metadata for context
                    if collection_type == "plays":
                        title = props.get("title", "Unknown Play")
                        act = props.get("act")
                        scene = props.get("scene")
                        speaker = props.get("speaker", "")
                        
                        citation = f"{title}"
                        if act and scene:
                            citation += f" (Act {act}, Scene {scene})"
                        if speaker:
                            citation += f" - {speaker}"
                        
                        # Build enhanced context with surrounding chunks
                        enhanced_content = self._build_enhanced_content(content, result.get("context", {}))
                        context = f"From {citation}: {enhanced_content}"
                        
                    elif collection_type == "sonnets":
                        sonnet_num = props.get("sonnet_number")
                        citation = f"Sonnet {sonnet_num}" if sonnet_num else "a sonnet"
                        context = f"From {citation}: {content}"
                        
                    elif collection_type == "poems":
                        title = props.get("title", "Unknown Poem")
                        stanza = props.get("stanza_number")
                        citation = f"{title}"
                        if stanza:
                            citation += f" (Stanza {stanza})"
                        context = f"From {citation}: {content}"
                    
                    context_parts.append(context)
                    citation_parts.append(citation)
        
        return context_parts, citation_parts
    
    def _build_enhanced_content(self, main_content: str, context_data: Dict[str, Any]) -> str:
        """Build enhanced content using surrounding chunks for better context"""
        if not context_data:
            return main_content
        
        preceding_chunks = context_data.get("preceding_chunks", [])
        following_chunks = context_data.get("following_chunks", [])
        
        # Select most relevant preceding context (all available chunks)
        preceding_context = []
        if preceding_chunks:
            # Take all preceding chunks for complete context
            for chunk in preceding_chunks:
                chunk_content = chunk.get("content", "").strip()
                chunk_speaker = chunk.get("speaker", "")
                if chunk_content and chunk_speaker:
                    preceding_context.append(f"{chunk_speaker}: {chunk_content}")
                elif chunk_content:
                    preceding_context.append(chunk_content)
        
        # Select most relevant following context (all available chunks)
        following_context = []
        if following_chunks:
            # Take all following chunks for complete context
            for chunk in following_chunks:
                chunk_content = chunk.get("content", "").strip()
                chunk_speaker = chunk.get("speaker", "")
                if chunk_content and chunk_speaker:
                    following_context.append(f"{chunk_speaker}: {chunk_content}")
                elif chunk_content:
                    following_context.append(chunk_content)
        
        # Build the enhanced content
        enhanced_parts = []
        
        if preceding_context:
            enhanced_parts.append("[Previous context: " + " | ".join(preceding_context) + "]")
        
        enhanced_parts.append(main_content)
        
        if following_context:
            enhanced_parts.append("[Following context: " + " | ".join(following_context) + "]")
        
        return " ".join(enhanced_parts)
    
    def analyze_search_quality(self, search_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze the quality of search results"""
        if not search_results:
            return {
                "total_results": 0,
                "avg_score": 0.0,
                "max_score": 0.0,
                "collections_searched": 0,
                "quality": "poor"
            }
        
        all_scores = []
        total_results = 0
        
        for collection_type, results in search_results.items():
            for result in results:
                score = result.get("score", 0)
                all_scores.append(score)
                total_results += 1
        
        if not all_scores:
            return {
                "total_results": 0,
                "avg_score": 0.0,
                "max_score": 0.0,
                "collections_searched": len(search_results),
                "quality": "poor"
            }
        
        avg_score = sum(all_scores) / len(all_scores)
        max_score = max(all_scores)
        
        # Determine quality
        if max_score > 0.5:
            quality = "excellent"
        elif max_score > 0.3:
            quality = "good"
        elif max_score > 0.1:
            quality = "fair"
        else:
            quality = "poor"
        
        return {
            "total_results": total_results,
            "avg_score": avg_score,
            "max_score": max_score,
            "collections_searched": len(search_results),
            "quality": quality
        }