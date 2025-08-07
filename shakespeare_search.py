"""
Shakespeare search functionality using Weaviate collections.
Handles collection querying and context building from Shakespeare's works.
"""

import weaviate
from typing import List, Dict, Any
from weaviate.classes.query import MetadataQuery, Filter
from rich.console import Console

console = Console()


class ShakespeareSearchClient:
    """Handles all Weaviate interactions for searching Shakespeare's works"""
    
    def __init__(self):
        self.client = None
        self.collections = {
            "plays": "ShakespearePlays",
            "sonnets": "ShakespeareSonnets", 
            "poems": "ShakespearePoems"
        }
    
    
    def connect(self):
        """Connect to local Weaviate instance"""
        self.client = weaviate.connect_to_local()
        console.print("✓ Connected to Weaviate", style="green")

   
    def search_collection(self, collection_name: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search a specific collection using semantic search"""
        collection = self.client.collections.get(collection_name)
        
        response = collection.query.hybrid(
            query=query,
            limit=limit,
            return_metadata=MetadataQuery(score=True, distance=True)
        )
        
        results = []
        for obj in response.objects:
            score = obj.metadata.score if obj.metadata and obj.metadata.score else None
            distance = obj.metadata.distance if obj.metadata and obj.metadata.distance else None
            
            if distance is not None and score is None:
                score = 1.0 - distance if distance < 1.0 else 0.0
            
            result = {
                "properties": obj.properties,
                "score": score,
                "distance": distance
            }
            
            if collection_name == "ShakespearePlays":
                result = self._add_play_context(result, collection)
            
            results.append(result)
        
        return results
    

    def _add_play_context(self, result: Dict[str, Any], collection) -> Dict[str, Any]:
        """Add surrounding context (previous 5 and following 5 chunks) to a play result"""
        properties = result["properties"]
        sequence_no = properties.get("sequence_no")
        play_name = properties.get("play", "")
        
        if sequence_no is None or not play_name:
            return result
        
        # Define context range (5 chunks before and after)
        context_start = max(1, sequence_no - 5)
        context_end = sequence_no + 5
        
        # Query for chunks in this sequence range
        context_chunks = self._get_context_chunks(collection, play_name, context_start, context_end)
        
        # Add context to the result
        result["context"] = {
            "preceding_chunks": [],
            "following_chunks": [],
            "current_sequence_no": sequence_no
        }
        
        for chunk in context_chunks:
            chunk_sequence_no = chunk.get("sequence_no")
            if chunk_sequence_no is not None:
                # Classify chunks as preceding or following
                if chunk_sequence_no < sequence_no:
                    result["context"]["preceding_chunks"].append({
                        "content": chunk.get("content", ""),
                        "speaker": chunk.get("speaker", ""),
                        "chunk_type": chunk.get("chunk_type", ""),
                        "sequence_no": chunk_sequence_no,
                        "line_numbers": chunk.get("line_numbers", [])
                    })
                elif chunk_sequence_no > sequence_no:
                    result["context"]["following_chunks"].append({
                        "content": chunk.get("content", ""),
                        "speaker": chunk.get("speaker", ""),
                        "chunk_type": chunk.get("chunk_type", ""),
                        "sequence_no": chunk_sequence_no,
                        "line_numbers": chunk.get("line_numbers", [])
                    })
        
        # Sort context chunks by sequence number
        result["context"]["preceding_chunks"].sort(key=lambda x: x["sequence_no"])
        result["context"]["following_chunks"].sort(key=lambda x: x["sequence_no"])
        
        return result
    

    def _get_context_chunks(self, collection, play_name: str, start_sequence: int, end_sequence: int) -> List[Dict[str, Any]]:
        """Retrieve chunks from the same play that have sequence numbers in the specified range"""
        # Use Weaviate filters to query for chunks from the same play within sequence range
        filters = Filter.by_property("play").equal(play_name) & \
                 Filter.by_property("sequence_no").greater_or_equal(start_sequence) & \
                 Filter.by_property("sequence_no").less_or_equal(end_sequence)
        
        query_response = collection.query.fetch_objects(
            filters=filters,
            limit=20  # Maximum of 11 chunks (5 before + current + 5 after), with some buffer
        )
        
        context_chunks = []
        for obj in query_response.objects:
            context_chunks.append(obj.properties)
        
        return context_chunks

    
    def search_relevant_collections(self, query: str, collection_types: List[str], 
                                   limit_per_collection: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Search only the specified collections"""
        all_results = {}
        
        for collection_type in collection_types:
            if collection_type in self.collections:
                collection_name = self.collections[collection_type]
                results = self.search_collection(collection_name, query, limit_per_collection)
                if results:
                    all_results[collection_type] = results
        
        return all_results
    

    def search_all_collections(self, query: str, limit_per_collection: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all collections"""
        all_results = {}
        
        for name, collection_name in self.collections.items():
            results = self.search_collection(collection_name, query, limit_per_collection)
            if results:
                all_results[name] = results
        
        return all_results
    

    def close(self):
        """Close the Weaviate connection"""
        if self.client:
            self.client.close()