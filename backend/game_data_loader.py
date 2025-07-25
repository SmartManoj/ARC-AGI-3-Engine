#!/usr/bin/env python3
"""
Game data loader for ARC-AGI-3 Engine
Loads real ARC game data from game_data/game_id/level_x/ folder structure
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class GameDataLoader:
    """Loads and manages ARC game data from file system"""
    
    def __init__(self, data_dir: str = "game_data"):
        self.data_dir = Path(data_dir)
        self.games_cache = {}
        
    def get_available_games(self) -> List[Dict[str, str]]:
        """Get list of available games"""
        games = []
        if not self.data_dir.exists():
            return games
            
        for game_dir in self.data_dir.iterdir():
            if game_dir.is_dir():
                game_id = game_dir.name
                # Try to find a title from the first level
                title = self._get_game_title(game_id)
                games.append({
                    "game_id": game_id,
                    "title": title or game_id.replace('-', ' ').title()
                })
        return games
    
    def _get_game_title(self, game_id: str) -> Optional[str]:
        """Extract game title from metadata or first level"""
        game_dir = self.data_dir / game_id
        if not game_dir.exists():
            return None
            
        # Look for metadata file
        metadata_file = game_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get("title", metadata.get("name"))
            except:
                pass
                
        # Try to get title from first level
        levels = self._get_levels(game_id)
        if levels:
            level_data = self.load_level(game_id, levels[0])
            if level_data and "title" in level_data:
                return level_data["title"]
        return None
    
    def _get_levels(self, game_id: str) -> List[str]:
        """Get list of available levels for a game"""
        game_dir = self.data_dir / game_id
        if not game_dir.exists():
            return []
            
        levels = []
        for item in game_dir.iterdir():
            if item.is_dir() and item.name.startswith("level_"):
                levels.append(item.name)
        return sorted(levels)
    
    def load_level(self, game_id: str, level: str) -> Optional[Dict]:
        """Load a specific level's data"""
        level_dir = self.data_dir / game_id / level
        if not level_dir.exists():
            return None
            
        initial_file = level_dir / "initial.json"
        final_file = level_dir / "final.json"
        
        if not initial_file.exists():
            return None
            
        try:
            with open(initial_file, 'r') as f:
                initial_data = json.load(f)
                
            final_data = None
            if final_file.exists():
                with open(final_file, 'r') as f:
                    final_data = json.load(f)
                    
            return {
                "game_id": game_id,
                "level": level,
                "initial": initial_data,
                "final": final_data,
                "title": initial_data.get("title", f"{game_id} - {level}")
            }
        except Exception as e:
            print(f"Error loading level {level} for game {game_id}: {e}")
            return None
    
    def get_frame_data(self, game_id: str, level: str, frame_type: str = "initial") -> Optional[List[List[List[int]]]]:
        """Get frame data for a specific level and frame type"""
        level_data = self.load_level(game_id, level)
        if not level_data:
            return None
            
        frame_data = level_data.get(frame_type, {})
        if not frame_data:
            return None
            
        # Convert grid data to frame format
        grid = frame_data.get("grid", [])
        if not grid:
            return None
            
        # Ensure 64x64 grid
        frame = []
        for y in range(64):
            row = []
            for x in range(64):
                if y < len(grid) and x < len(grid[y]):
                    color_index = grid[y][x]
                else:
                    color_index = 0  # Default to black
                row.append(color_index)
            frame.append(row)
            
        return [frame]
    
    def get_game_state(self, game_id: str, level: str) -> Dict:
        """Get game state information"""
        level_data = self.load_level(game_id, level)
        if not level_data:
                    return {
            "state": "NOT_STARTED",
            "score": 0
        }
            
        # Extract state from level data
        initial = level_data.get("initial", {})
        final = level_data.get("final", {})
        
        return {
            "state": "NOT_FINISHED",
            "score": 0,
            "title": level_data.get("title", f"{game_id} - {level}"),
            "description": initial.get("description", ""),
            "rules": initial.get("rules", [])
        }

# Global loader instance
game_loader = GameDataLoader() 