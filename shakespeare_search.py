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
    
    def connect(self) -> bool:
        """Connect to local Weaviate instance"""
        try:
            self.client = weaviate.connect_to_local()
            console.print("✓ Connected to Weaviate", style="green")
            return True
        except Exception as e:
            console.print(f"❌ Failed to connect to Weaviate: {e}", style="red")
            console.print("Make sure Weaviate is running locally (docker-compose up)", style="yellow")
            return False
    
    def check_collections(self) -> bool:
        """Check if all required collections exist and test basic functionality"""
        missing_collections = []
        
        for name, collection_name in self.collections.items():
            if not self.client.collections.exists(collection_name):
                missing_collections.append(collection_name)
        
        if missing_collections:
            console.print(f"❌ Missing collections: {', '.join(missing_collections)}", style="red")
            console.print("Please run load_weaviate.py first to create and populate the collections", style="yellow")
            return False
        
        console.print("✓ All collections found", style="green")
        
        # Test basic search functionality
        try:
            test_collection = self.client.collections.get("ShakespearePlays")
            test_response = test_collection.query.fetch_objects(limit=1)
            if test_response.objects:
                console.print("✓ Collections are accessible and contain data", style="green")
            else:
                console.print("⚠️ Collections exist but appear to be empty", style="yellow")
        except Exception as e:
            console.print(f"⚠️ Collections exist but there may be connectivity issues: {e}", style="yellow")
        
        return True
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get basic statistics about each collection"""
        stats = {}
        
        for name, collection_name in self.collections.items():
            collection = self.client.collections.get(collection_name)
            
            # Count objects (with safety limit)
            count = 0
            for _ in collection.iterator():
                count += 1
                if count >= 50000:  # Safety limit
                    break
            
            stats[name] = count
        
        return stats
    
    def search_collection(self, collection_name: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search a specific collection using semantic search"""
        try:
            collection = self.client.collections.get(collection_name)
            
            # Use hybrid search for better results
            response = collection.query.hybrid(
                query=query,
                limit=limit,
                return_metadata=MetadataQuery(score=True, distance=True)
            )
            
            results = []
            for obj in response.objects:
                # Use distance instead of score if score is not available
                score = obj.metadata.score if obj.metadata and obj.metadata.score else None
                distance = obj.metadata.distance if obj.metadata and obj.metadata.distance else None
                
                # Convert distance to a relevance score (lower distance = higher relevance)
                if distance is not None and score is None:
                    score = 1.0 - distance if distance < 1.0 else 0.0
                
                result = {
                    "properties": obj.properties,
                    "score": score,
                    "distance": distance
                }
                
                # Add context for plays collection
                if collection_name == "ShakespearePlays":
                    result = self._add_play_context(result, collection)
                
                results.append(result)
            
            return results
            
        except Exception as e:
            console.print(f"Error searching {collection_name}: {e}", style="red")
            # Fallback to simple text search
            try:
                response = collection.query.near_text(
                    query=query,
                    limit=limit,
                    return_metadata=MetadataQuery(distance=True)
                )
                
                results = []
                for obj in response.objects:
                    distance = obj.metadata.distance if obj.metadata else 1.0
                    score = 1.0 - distance if distance < 1.0 else 0.0
                    
                    result = {
                        "properties": obj.properties,
                        "score": score,
                        "distance": distance
                    }
                    
                    # Add context for plays collection
                    if collection_name == "ShakespearePlays":
                        result = self._add_play_context(result, collection)
                    
                    results.append(result)
                
                return results
                
            except Exception as e2:
                console.print(f"Fallback search also failed for {collection_name}: {e2}", style="red")
                return []
    
    def _add_play_context(self, result: Dict[str, Any], collection) -> Dict[str, Any]:
        """Add surrounding context (previous 5 and following 5 chunks) to a play result"""
        try:
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
            
        except Exception as e:
            console.print(f"Warning: Could not add context to result: {e}", style="yellow")
            
        return result
    
    def _get_context_chunks(self, collection, play_name: str, start_sequence: int, end_sequence: int) -> List[Dict[str, Any]]:
        """Retrieve chunks from the same play that have sequence numbers in the specified range"""
        try:
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
            
        except Exception as e:
            console.print(f"Error retrieving context chunks: {e}", style="red")
            raise  # Re-raise the exception so you can see the full error
    
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
        """Search across all collections (fallback method)"""
        all_results = {}
        
        for name, collection_name in self.collections.items():
            results = self.search_collection(collection_name, query, limit_per_collection)
            if results:
                all_results[name] = results
        
        return all_results
    
    def test_vector_search(self) -> bool:
        """Test vector search functionality"""
        try:
            collection = self.client.collections.get("ShakespearePlays")
            
            console.print("Testing vector search...")
            vector_response = collection.query.near_text(
                query="love",
                limit=1,
                return_metadata=MetadataQuery(distance=True)
            )
            
            if vector_response.objects:
                console.print("✓ Vector search working", style="green")
                return True
            else:
                console.print("⚠️ Vector search returned no results", style="yellow")
                return False
                
        except Exception as e:
            console.print(f"❌ Vector search issues: {e}", style="red")
            console.print("Make sure Weaviate is running and embeddings are available", style="yellow")
            return False
    
    def close(self):
        """Close the Weaviate connection"""
        if self.client:
            self.client.close()