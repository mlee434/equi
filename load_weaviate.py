#!/usr/bin/env python3
"""
Load Shakespeare data into Weaviate with separate collections:
1. ShakespearePlays - for all dramatic works  
2. ShakespeareSonnets - specifically for the 154 sonnets
3. ShakespearePoems - for other poetry (Venus and Adonis, Rape of Lucrece, Lover's Complaint)
"""

import os
import json
import glob
from pathlib import Path
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.data import DataObject
from typing import List, Dict, Any


def connect_to_weaviate():
    """Connect to local Weaviate instance"""
    try:
        client = weaviate.connect_to_local()
        print("✓ Connected to Weaviate")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        print("Make sure Weaviate is running locally (docker-compose up)")
        return None


def create_collections(client):
    """Create the three Shakespeare collections"""
    
    # Delete existing collections if they exist
    collections_to_delete = ["ShakespearePlays", "ShakespeareSonnets", "ShakespearePoems"]
    for collection_name in collections_to_delete:
        if client.collections.exists(collection_name):
            client.collections.delete(collection_name)
            print(f"🗑️  Deleted existing collection: {collection_name}")
    
    # 1. Shakespeare Plays Collection
    client.collections.create(
        "ShakespearePlays",
        vector_config=Configure.Vectors.text2vec_ollama(
            api_endpoint="http://host.docker.internal:11434",
            model="nomic-embed-text",
        ),
        generative_config=Configure.Generative.ollama(
            api_endpoint="http://host.docker.internal:11434", 
            model="llama3.2",
        ),
        properties=[
            Property(name="chunk_id", data_type=DataType.TEXT),
            Property(name="chunk_type", data_type=DataType.TEXT),  # speech, stage_direction, scene_opening
            Property(name="play", data_type=DataType.TEXT),
            Property(name="title", data_type=DataType.TEXT),
            Property(name="genre", data_type=DataType.TEXT),
            Property(name="act", data_type=DataType.INT),
            Property(name="scene", data_type=DataType.INT),
            Property(name="speaker", data_type=DataType.TEXT),
            Property(name="location", data_type=DataType.TEXT),
            Property(name="characters_present", data_type=DataType.TEXT_ARRAY),
            Property(name="line_numbers", data_type=DataType.INT_ARRAY),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="stage_directions", data_type=DataType.TEXT),
            Property(name="sequence_no", data_type=DataType.INT),
            Property(name="total_acts", data_type=DataType.INT),
            Property(name="total_scenes", data_type=DataType.INT),
            Property(name="total_lines", data_type=DataType.INT),
        ]
    )
    print("✓ Created ShakespearePlays collection")
    
    # 2. Shakespeare Sonnets Collection  
    client.collections.create(
        "ShakespeareSonnets",
        vector_config=Configure.Vectors.text2vec_ollama(
            api_endpoint="http://host.docker.internal:11434",
            model="nomic-embed-text",
        ),
        generative_config=Configure.Generative.ollama(
            api_endpoint="http://host.docker.internal:11434",
            model="llama3.2", 
        ),
        properties=[
            Property(name="chunk_id", data_type=DataType.TEXT),
            Property(name="sonnet_number", data_type=DataType.INT),
            Property(name="roman_numeral", data_type=DataType.TEXT),
            Property(name="title", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="collection", data_type=DataType.TEXT),  # "sonnets"
            Property(name="genre", data_type=DataType.TEXT),  # "poetry"
        ]
    )
    print("✓ Created ShakespeareSonnets collection")
    
    # 3. Shakespeare Poems Collection (other poetry)
    client.collections.create(
        "ShakespearePoems",
        vector_config=Configure.Vectors.text2vec_ollama(
            api_endpoint="http://host.docker.internal:11434",
            model="nomic-embed-text",
        ),
        generative_config=Configure.Generative.ollama(
            api_endpoint="http://host.docker.internal:11434",
            model="llama3.2",
        ),
        properties=[
            Property(name="chunk_id", data_type=DataType.TEXT),
            Property(name="chunk_type", data_type=DataType.TEXT),
            Property(name="poem", data_type=DataType.TEXT),
            Property(name="title", data_type=DataType.TEXT),
            Property(name="full_title", data_type=DataType.TEXT),
            Property(name="genre", data_type=DataType.TEXT),
            Property(name="poem_type", data_type=DataType.TEXT),  # narrative, complaint, etc.
            Property(name="content", data_type=DataType.TEXT),
            Property(name="stanza_number", data_type=DataType.INT),
            Property(name="line_numbers", data_type=DataType.INT_ARRAY),
            Property(name="approximate_date", data_type=DataType.TEXT),
        ]
    )
    print("✓ Created ShakespearePoems collection")


def load_plays(client, json_dir: str):
    """Load all Shakespeare plays into the ShakespearePlays collection"""
    collection = client.collections.get("ShakespearePlays")
    
    # Files that are poetry, not plays
    poetry_files = {"sonnets.json", "venus_and_adonis.json", "rape_of_lucrece.json", "lovers_complaint.json"}
    
    play_files = [f for f in glob.glob(f"{json_dir}/*.json") if Path(f).name not in poetry_files]
    
    total_chunks = 0
    
    for file_path in play_files:
        print(f"📖 Loading play: {Path(file_path).stem}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        play_metadata = data.get("play_metadata", {})
        chunks = data.get("chunks", [])
        
        # Prepare batch data
        data_objects = []
        sequence_no = 1  # Start sequence number at 1 for each play
        for chunk in chunks:
            properties = {
                "chunk_id": chunk.get("chunk_id", ""),
                "chunk_type": chunk.get("chunk_type", ""),
                "play": chunk.get("play", ""),
                "title": play_metadata.get("title", ""),
                "genre": play_metadata.get("genre", ""),
                "content": chunk.get("content", ""),
                "sequence_no": sequence_no,
                "total_acts": play_metadata.get("total_acts"),
                "total_scenes": play_metadata.get("total_scenes"), 
                "total_lines": play_metadata.get("total_lines"),
            }
            
            # Optional fields that might not be present
            if "act" in chunk:
                properties["act"] = chunk["act"]
            if "scene" in chunk:
                properties["scene"] = chunk["scene"]
            if "speaker" in chunk:
                properties["speaker"] = chunk["speaker"]
            if "location" in chunk:
                properties["location"] = chunk["location"]
            if "characters_present" in chunk:
                properties["characters_present"] = chunk["characters_present"]
            if "line_numbers" in chunk:
                properties["line_numbers"] = chunk["line_numbers"]
            if "stage_directions" in chunk:
                properties["stage_directions"] = chunk["stage_directions"]
                
            data_objects.append(DataObject(properties=properties))
            sequence_no += 1  # Increment sequence number for next chunk
        
        # Batch insert
        with collection.batch.fixed_size(batch_size=100) as batch:
            for obj in data_objects:
                batch.add_object(properties=obj.properties)
        
        total_chunks += len(chunks)
        print(f"  ✓ Loaded {len(chunks)} chunks")
    
    print(f"✅ Loaded {len(play_files)} plays with {total_chunks} total chunks")


def load_sonnets(client, json_dir: str):
    """Load Shakespeare's sonnets into the ShakespeareSonnets collection"""
    collection = client.collections.get("ShakespeareSonnets")
    
    sonnets_file = os.path.join(json_dir, "sonnets.json")
    if not os.path.exists(sonnets_file):
        print("❌ sonnets.json not found")
        return
    
    print("📝 Loading Shakespeare's Sonnets")
    
    with open(sonnets_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    poetry_metadata = data.get("poetry_metadata", {})
    chunks = data.get("chunks", [])
    
    # Prepare batch data
    data_objects = []
    for chunk in chunks:
        if chunk.get("chunk_type") == "sonnet":
            properties = {
                "chunk_id": chunk.get("chunk_id", ""),
                "sonnet_number": chunk.get("sonnet_number"),
                "roman_numeral": chunk.get("roman_numeral", ""),
                "title": chunk.get("title", ""),
                "content": chunk.get("content", ""),
                "collection": chunk.get("collection", ""),
                "genre": poetry_metadata.get("genre", "poetry"),
            }
            data_objects.append(DataObject(properties=properties))
    
    # Batch insert
    with collection.batch.fixed_size(batch_size=50) as batch:
        for obj in data_objects:
            batch.add_object(properties=obj.properties)
    
    print(f"✅ Loaded {len(data_objects)} sonnets")


def load_poems(client, json_dir: str):
    """Load other Shakespeare poetry into the ShakespearePoems collection"""
    collection = client.collections.get("ShakespearePoems")
    
    poem_files = ["venus_and_adonis.json", "rape_of_lucrece.json", "lovers_complaint.json"]
    
    total_chunks = 0
    
    for filename in poem_files:
        file_path = os.path.join(json_dir, filename)
        if not os.path.exists(file_path):
            print(f"⚠️  {filename} not found, skipping")
            continue
            
        print(f"📜 Loading poem: {Path(filename).stem}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        poetry_metadata = data.get("poetry_metadata", {})
        chunks = data.get("chunks", [])
        
        # Prepare batch data
        data_objects = []
        for chunk in chunks:
            properties = {
                "chunk_id": chunk.get("chunk_id", ""),
                "chunk_type": chunk.get("chunk_type", ""),
                "poem": chunk.get("poem", ""),
                "title": poetry_metadata.get("title", ""),
                "full_title": poetry_metadata.get("full_title", ""),
                "genre": poetry_metadata.get("genre", "poetry"),
                "content": chunk.get("content", ""),
                "approximate_date": poetry_metadata.get("approximate_date", ""),
            }
            
            # Optional fields
            if "poem_type" in poetry_metadata:
                properties["poem_type"] = poetry_metadata["poem_type"]
            if "stanza_number" in chunk:
                properties["stanza_number"] = chunk["stanza_number"]
            if "line_numbers" in chunk:
                properties["line_numbers"] = chunk["line_numbers"]
                
            data_objects.append(DataObject(properties=properties))
        
        # Batch insert
        with collection.batch.fixed_size(batch_size=100) as batch:
            for obj in data_objects:
                batch.add_object(properties=obj.properties)
        
        total_chunks += len(chunks)
        print(f"  ✓ Loaded {len(chunks)} chunks")
    
    print(f"✅ Loaded {len(poem_files)} poems with {total_chunks} total chunks")


def verify_collections(client):
    """Verify that all collections were created and populated"""
    collections = ["ShakespearePlays", "ShakespeareSonnets", "ShakespearePoems"]
    
    print("\n📊 Collection Summary:")
    print("-" * 50)
    
    for collection_name in collections:
        if client.collections.exists(collection_name):
            collection = client.collections.get(collection_name)
            
            # Get object count using iterator
            count = 0
            for _ in collection.iterator():
                count += 1
                if count >= 10000:  # Safety limit for counting
                    break
            
            print(f"{collection_name}: {count} objects")
            
            # Show a sample object
            sample = collection.query.fetch_objects(limit=1)
            if sample.objects:
                print(f"  Sample: {sample.objects[0].properties.get('title', 'N/A')}")
        else:
            print(f"{collection_name}: ❌ Not found")
    
    print("-" * 50)


def main():
    """Main execution function"""
    json_dir = "json_output"
    
    if not os.path.exists(json_dir):
        print(f"❌ Directory {json_dir} not found")
        return
    
    # Connect to Weaviate
    client = connect_to_weaviate()
    if not client:
        return
    
    try:
        # Create collections
        print("\n🏗️  Creating collections...")
        create_collections(client)
        
        # Load data
        print("\n📚 Loading data...")
        load_plays(client, json_dir)
        load_sonnets(client, json_dir) 
        load_poems(client, json_dir)
        
        # Verify results
        verify_collections(client)
        
        print("\n🎉 Shakespeare data successfully loaded into Weaviate!")
        print("\nYou can now query the collections:")
        print("- ShakespearePlays: All dramatic works")
        print("- ShakespeareSonnets: The 154 sonnets")  
        print("- ShakespearePoems: Other poetry (Venus & Adonis, Rape of Lucrece, Lover's Complaint)")
        print("\n📋 Prerequisites:")
        print("- Ollama running with 'nomic-embed-text' and 'llama3.2' models")
        print("- Run: ollama pull nomic-embed-text && ollama pull llama3.2")
        
    except Exception as e:
        print(f"❌ Error during loading: {e}")
        
    finally:
        client.close()


if __name__ == "__main__":
    main()
