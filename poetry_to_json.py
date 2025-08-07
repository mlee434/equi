import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup


def roman_to_int(roman):
    """Convert Roman numeral to integer."""
    roman_numerals = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000
    }
    
    result = 0
    prev_value = 0
    
    for char in reversed(roman):
        value = roman_numerals[char]
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value
    
    return result


def parse_sonnet_html(file_path):
    """Parse a sonnet HTML file and extract the content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract title
    title_tag = soup.find('title')
    title = title_tag.text if title_tag else ""
    
    # Extract h1 for sonnet number
    h1_tag = soup.find('h1')
    h1_text = h1_tag.text if h1_tag else ""
    
    # Extract the sonnet text from blockquote
    blockquote = soup.find('blockquote')
    if not blockquote:
        return None
    
    # Get all text, replace <BR> tags with newlines
    sonnet_text = ""
    for element in blockquote.contents:
        if hasattr(element, 'name'):
            if element.name == 'br':
                sonnet_text += '\n'
            else:
                sonnet_text += element.get_text()
        else:
            sonnet_text += str(element)
    
    # Clean up the text
    sonnet_text = sonnet_text.strip()
    # Remove extra whitespace but preserve line breaks
    lines = [line.strip() for line in sonnet_text.split('\n') if line.strip()]
    sonnet_text = '\n'.join(lines)
    
    return {
        'title': title,
        'h1_text': h1_text,
        'content': sonnet_text
    }


def sonnets_to_json():
    """Convert all sonnets to JSON format matching the chunks structure."""
    
    # Path to the Poetry directory
    poetry_dir = Path(__file__).parent / "shakespeare" / "Poetry"
    
    # Find all sonnet files
    sonnet_files = list(poetry_dir.glob("sonnet.*.html"))
    
    if not sonnet_files:
        print("No sonnet files found!")
        return
    
    # Sort files by Roman numeral
    def get_sonnet_number(file_path):
        # Extract Roman numeral from filename
        match = re.search(r'sonnet\.([IVXLCDM]+)\.html', file_path.name)
        if match:
            return roman_to_int(match.group(1))
        return 0
    
    sonnet_files.sort(key=get_sonnet_number)
    
    # Create the JSON structure
    sonnets_data = {
        "poetry_metadata": {
            "id": "sonnets",
            "title": "Shakespeare's Sonnets",
            "full_title": "The Complete Sonnets of William Shakespeare",
            "genre": "poetry",
            "type": "sonnet_collection",
            "total_sonnets": len(sonnet_files),
            "approximate_date": "1590s-1609"
        },
        "chunks": []
    }
    
    # Process each sonnet
    for file_path in sonnet_files:
        # Extract Roman numeral from filename
        match = re.search(r'sonnet\.([IVXLCDM]+)\.html', file_path.name)
        if not match:
            continue
            
        roman_numeral = match.group(1)
        sonnet_number = roman_to_int(roman_numeral)
        
        # Parse the HTML
        parsed = parse_sonnet_html(file_path)
        if not parsed:
            print(f"Failed to parse {file_path}")
            continue
        
        # Create chunk for this sonnet
        chunk = {
            "chunk_id": f"sonnet_{sonnet_number}",
            "chunk_type": "sonnet",
            "collection": "sonnets",
            "sonnet_number": sonnet_number,
            "roman_numeral": roman_numeral,
            "title": parsed['title'],
            "content": parsed['content']
        }
        
        sonnets_data["chunks"].append(chunk)
    
    # Create output directory if it doesn't exist
    output_dir = Path(__file__).parent / "json_output"
    output_dir.mkdir(exist_ok=True)
    
    # Write to JSON file
    output_file = output_dir / "sonnets.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sonnets_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully converted {len(sonnets_data['chunks'])} sonnets to {output_file}")
    print(f"Sonnets range from {min(chunk['sonnet_number'] for chunk in sonnets_data['chunks'])} to {max(chunk['sonnet_number'] for chunk in sonnets_data['chunks'])}")


def long_poems_to_json():
    """Convert the three long poems to JSON format with stanza-based chunks."""
    
    poetry_dir = Path(__file__).parent / "shakespeare" / "Poetry"
    output_dir = Path(__file__).parent / "json_output"
    output_dir.mkdir(exist_ok=True)
    
    # Configuration for each poem
    poems_config = {
        "loverscomplaint": {
            "file": "loverscomplaint",
            "title": "A Lover's Complaint",
            "start_line": 5,
            "stanza_lines": 7,
            "id": "lovers_complaint"
        },
        "rapeoflucrece": {
            "file": "rapeoflucrece", 
            "title": "The Rape of Lucrece",
            "start_line": 73,
            "stanza_lines": 7,
            "id": "rape_of_lucrece"
        },
        "venusandadonis": {
            "file": "venusandadonis",
            "title": "Venus and Adonis", 
            "start_line": 31,
            "stanza_lines": 6,
            "id": "venus_and_adonis"
        }
    }
    
    for poem_key, config in poems_config.items():
        file_path = poetry_dir / config["file"]
        
        if not file_path.exists():
            print(f"File not found: {file_path}")
            continue
            
        # Read the entire file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Extract poem content starting from the specified line
        poem_lines = lines[config["start_line"] - 1:]  # Convert to 0-based index
        
        # Remove trailing whitespace from each line but keep the line breaks
        poem_lines = [line.rstrip() for line in poem_lines]
        
        # Group lines into stanzas
        stanzas = []
        current_stanza = []
        line_count = 0
        
        for line in poem_lines:
            if line.strip():  # Non-empty line
                current_stanza.append(line)
                line_count += 1
                
                # Check if we've completed a stanza
                if line_count == config["stanza_lines"]:
                    stanzas.append(current_stanza)
                    current_stanza = []
                    line_count = 0
            else:
                # Empty line - if we have content in current_stanza, it should be completed
                if current_stanza and line_count == config["stanza_lines"]:
                    stanzas.append(current_stanza)
                    current_stanza = []
                    line_count = 0
        
        # Add any remaining lines as a final stanza
        if current_stanza:
            stanzas.append(current_stanza)
        
        # Create JSON structure
        poem_data = {
            "poetry_metadata": {
                "id": config["id"],
                "title": config["title"],
                "full_title": config["title"],
                "genre": "narrative_poetry",
                "type": "long_poem",
                "total_stanzas": len(stanzas),
                "stanza_pattern": f"{config['stanza_lines']}-line stanzas",
                "approximate_date": "1590s"
            },
            "chunks": []
        }
        
        # Create chunks for each stanza
        for i, stanza in enumerate(stanzas, 1):
            stanza_content = '\n'.join(stanza)
            
            chunk = {
                "chunk_id": f"{config['id']}_stanza_{i}",
                "chunk_type": "stanza", 
                "collection": config["id"],
                "poem_title": config["title"],
                "stanza_number": i,
                "stanza_lines": len(stanza),
                "content": stanza_content
            }
            
            poem_data["chunks"].append(chunk)
        
        # Write to JSON file
        output_file = output_dir / f"{config['id']}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(poem_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted {config['title']} to {output_file}")
        print(f"  - {len(stanzas)} stanzas ({config['stanza_lines']}-line stanzas)")
        print(f"  - Total lines: {sum(len(stanza) for stanza in stanzas)}")


if __name__ == "__main__":
    sonnets_to_json()
    long_poems_to_json()
