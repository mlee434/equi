#!/usr/bin/env python3
"""
Convert Shakespeare plays from HTML to JSON format for vector database ingestion.
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional


def extract_play_metadata(soup: BeautifulSoup, play_id: str) -> Dict[str, Any]:
    """Extract metadata from the play HTML."""
    # Get title from the page title first, then table
    title_element = soup.find('title')
    if title_element:
        full_title = title_element.get_text().replace(': Entire Play', '').strip()
    else:
        title_element = soup.find('td', class_='play')
        full_title = title_element.get_text().strip() if title_element else play_id
    
    # Extract short title (remove "The" and subtitle)
    title = full_title
    if title.startswith('The '):
        title = title[4:]
    if ',' in title:
        title = title.split(',')[0]
    
    # Determine genre based on play name patterns
    genre = "unknown"
    play_lower = full_title.lower()
    if any(word in play_lower for word in ['tragedy', 'hamlet', 'othello', 'lear', 'macbeth', 'romeo', 'julius', 'titus', 'timon', 'coriolanus', 'cleopatra']):
        genre = "tragedy"
    elif any(word in play_lower for word in ['comedy', 'midsummer', 'merchant', 'much ado', 'as you like', 'twelfth', 'merry wives', 'all\'s well', 'measure', 'tempest', 'winter\'s tale', 'errors']):
        genre = "comedy"
    elif any(word in play_lower for word in ['henry', 'richard', 'john', 'king']):
        genre = "history"
    
    return {
        "id": play_id,
        "title": title,
        "full_title": full_title,
        "genre": genre,
        "approximate_date": "unknown",  # Could be enhanced with a lookup table
        "setting": "unknown",  # Could be enhanced with parsing
        "total_acts": 0,  # Will be calculated
        "total_scenes": 0,  # Will be calculated
        "total_lines": 0  # Will be calculated
    }


def extract_line_number(line_anchor: str) -> Optional[int]:
    """Extract line number from anchor name like '1.1.30' -> 30"""
    if not line_anchor:
        return None
    # Check if it matches the pattern x.x.x
    parts = line_anchor.split('.')
    if len(parts) == 3:
        try:
            # Validate all parts are numbers and return the line number (third part)
            int(parts[0])
            int(parts[1]) 
            return int(parts[2])
        except ValueError:
            return None
    return None


def parse_speech(speech_element, play_id: str, act_num: int, scene_num: int, speech_counter: int) -> Optional[Dict[str, Any]]:
    """Parse a single speech element."""
    # Find speaker name
    speaker_element = speech_element.find('b')
    if not speaker_element:
        return None
    
    speaker = speaker_element.get_text().strip()
    
    # Find all lines in this speech - blockquote is usually the next sibling
    blockquote = speech_element.find_next_sibling('blockquote')
    if not blockquote:
        return None
    
    lines = []
    line_numbers = []
    
    # Find all anchor elements with line numbers
    line_anchors = blockquote.find_all('a', attrs={'name': True})
    
    for anchor in line_anchors:
        line_num = extract_line_number(anchor.get('name'))
        if line_num is not None:
            # Get the text content of this anchor (the line text)
            line_text = anchor.get_text().strip()
            
            if line_text:
                lines.append(line_text)
                line_numbers.append(line_num)
    
    # If no lines found with anchors, get all text from blockquote
    if not lines:
        text = blockquote.get_text().strip()
        if text:
            lines = [text]
            line_numbers = [speech_counter]  # Use speech counter as fallback
    
    if not lines:
        return None
    
    content = "\n".join(lines)
    
    return {
        "chunk_id": f"{play_id}_{act_num}_{scene_num}_speech_{speech_counter}",
        "chunk_type": "speech",
        "play": play_id,
        "act": act_num,
        "scene": scene_num,
        "speaker": speaker,
        "line_numbers": line_numbers,
        "content": content
    }


def parse_stage_direction(stage_dir_element, play_id: str, act_num: int, scene_num: int, stage_counter: int) -> Dict[str, Any]:
    """Parse a stage direction element."""
    content = stage_dir_element.get_text().strip()
    
    return {
        "chunk_id": f"{play_id}_{act_num}_{scene_num}_stage_{stage_counter}",
        "chunk_type": "stage_direction",
        "play": play_id,
        "act": act_num,
        "scene": scene_num,
        "content": content
    }


def parse_scene_opening(scene_header, play_id: str, act_num: int, scene_num: int) -> Optional[Dict[str, Any]]:
    """Parse scene opening with location and initial stage directions."""
    if not scene_header:
        return None
    
    scene_text = scene_header.get_text().strip()
    
    # Extract location from scene header like "SCENE I. Elsinore. A platform before the castle."
    location = ""
    if '. ' in scene_text:
        parts = scene_text.split('. ', 1)
        if len(parts) > 1:
            location = parts[1].rstrip('.')
    
    # Find initial stage directions
    stage_directions = ""
    characters_present = []
    
    # Look for stage directions in italic after the scene header
    next_element = scene_header.find_next_sibling()
    while next_element:
        if next_element.name == 'blockquote':
            italic = next_element.find('i')
            if italic:
                stage_directions = italic.get_text().strip()
                # Extract character names from stage directions
                if 'Enter' in stage_directions:
                    # Simple extraction - could be enhanced
                    enter_text = stage_directions.split('Enter')[-1]
                    # Remove common words and extract likely character names
                    words = re.findall(r'[A-Z][A-Z\s]+', enter_text)
                    characters_present = [w.strip() for w in words if len(w.strip()) > 1]
            break
        elif next_element.name in ['h3', 'H3']:
            break
        next_element = next_element.find_next_sibling()
    
    content = f"Scene {scene_num} opens"
    if location:
        content += f" at {location}"
    if stage_directions:
        content += f". {stage_directions}"
    
    return {
        "chunk_id": f"{play_id}_{act_num}_{scene_num}_opening",
        "chunk_type": "scene_opening",
        "play": play_id,
        "act": act_num,
        "scene": scene_num,
        "location": location,
        "characters_present": characters_present,
        "stage_directions": stage_directions,
        "content": content
    }


def parse_play_html(html_content: str, play_id: str) -> Dict[str, Any]:
    """Parse a complete play HTML file."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract metadata
    metadata = extract_play_metadata(soup, play_id)
    
    chunks = []
    
    # Find all act headers
    act_headers = soup.find_all(['h3', 'H3'], string=re.compile(r'ACT [IVX]+'))
    
    # Find all scene headers  
    scene_headers = soup.find_all(['h3', 'h3'], string=re.compile(r'SCENE [IVX]+'))
    
    total_acts = len(act_headers)
    total_scenes = len(scene_headers)
    total_lines = 0
    
    # Map each scene to its act
    scene_to_act = {}
    for scene_idx, scene_header in enumerate(scene_headers):
        current_act = 1
        # Find which act this scene belongs to by checking which act header comes before it
        for act_idx, act_header in enumerate(act_headers):
            # Check if act header comes before this scene in document order
            try:
                if scene_header.parent and act_header.parent:
                    scene_pos = list(soup.descendants).index(scene_header)
                    act_pos = list(soup.descendants).index(act_header)
                    if act_pos < scene_pos:
                        current_act = act_idx + 1
            except (ValueError, AttributeError):
                pass
        scene_to_act[scene_idx] = current_act
    
    # Get all elements in the document for range-based processing
    all_elements = list(soup.find_all())
    
    # Process each scene
    for scene_idx, scene_header in enumerate(scene_headers):
        current_act = scene_to_act[scene_idx]
        scene_num = scene_idx + 1
        
        # Add scene opening
        scene_opening = parse_scene_opening(scene_header, play_id, current_act, scene_num)
        if scene_opening:
            chunks.append(scene_opening)
        
        # Find the range of elements for this scene
        scene_start_idx = all_elements.index(scene_header)
        
        # Find end boundary - next scene header or end of document
        scene_end_idx = len(all_elements)
        if scene_idx + 1 < len(scene_headers):
            next_scene_header = scene_headers[scene_idx + 1]
            scene_end_idx = all_elements.index(next_scene_header)
        
        # Get elements in this scene
        scene_elements = all_elements[scene_start_idx + 1:scene_end_idx]
        
        # Process speeches and stage directions in this scene
        speech_counter = 0
        stage_counter = 0
        
        for element in scene_elements:
            # Check for speech elements
            if element.name == 'a' and element.get('name', '').startswith('speech'):
                speech_counter += 1
                speech = parse_speech(element, play_id, current_act, scene_num, speech_counter)
                if speech:
                    chunks.append(speech)
                    total_lines += len(speech['line_numbers'])
            
            # Check for stage directions
            elif element.name in ['p', 'blockquote']:
                italic = element.find('i')
                if italic and ('Enter' in italic.get_text() or 'Exit' in italic.get_text() or 'Exeunt' in italic.get_text()):
                    stage_counter += 1
                    stage_dir = parse_stage_direction(italic, play_id, current_act, scene_num, stage_counter)
                    chunks.append(stage_dir)
    
    # Update metadata with calculated values
    metadata["total_acts"] = total_acts
    metadata["total_scenes"] = total_scenes
    metadata["total_lines"] = total_lines
    
    return {
        "play_metadata": metadata,
        "chunks": chunks
    }


def convert_play(play_dir: Path) -> Dict[str, Any]:
    """Convert a single play directory to JSON."""
    full_html_path = play_dir / "full.html"
    
    with open(full_html_path, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()
    
    play_id = play_dir.name
    result = parse_play_html(html_content, play_id)
    
    print(f"Converted {play_id}: {result['play_metadata']['total_acts']} acts, "
          f"{result['play_metadata']['total_scenes']} scenes, "
          f"{len(result['chunks'])} chunks")
    
    return result


def main():
    """Convert all Shakespeare plays to JSON."""
    shakespeare_dir = Path("shakespeare")
    output_dir = Path("json_output")
    output_dir.mkdir(exist_ok=True)
    
    # Process each play directory
    for play_dir in shakespeare_dir.iterdir():
        if not play_dir.is_dir() or play_dir.name == "Poetry":
            continue
        
        print(f"Processing {play_dir.name}...")
        
        result = convert_play(play_dir)
        # Save individual play JSON
        output_file = output_dir / f"{play_dir.name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {output_file}")
    
    print("Conversion complete!")


if __name__ == "__main__":
    main()
