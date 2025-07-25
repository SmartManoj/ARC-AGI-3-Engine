from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import uvicorn
import uuid
import json
from datetime import datetime
from game_data_loader import game_loader

app = FastAPI(
    title="ARC-AGI-3 REST API",
    description="Programmatic interface for running agents against ARC-AGI-3 games, opening/closing score-cards and driving game state with actions.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models matching the official API specification
class Game(BaseModel):
    game_id: str = Field(..., example="ls20-016295f7601e")
    title: str = Field(..., example="LS20")

class OpenScorecardRequest(BaseModel):
    source_url: Optional[str] = Field(None, format="uri")
    tags: Optional[List[str]] = Field(None)
    opaque: Optional[Dict[str, Any]] = Field(None)

class OpenScorecardResponse(BaseModel):
    card_id: str

class CloseScorecardRequest(BaseModel):
    card_id: str

class PerGameCard(BaseModel):
    game_id: str
    total_plays: int
    total_actions: int
    scores: Optional[List[int]] = None
    states: Optional[List[str]] = None
    actions: Optional[List[int]] = None

class ScorecardSummary(BaseModel):
    api_key: str
    card_id: str
    won: int
    played: int
    total_actions: int
    score: int
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None
    opaque: Optional[Dict[str, Any]] = None
    cards: Dict[str, PerGameCard]

class ResetCommand(BaseModel):
    game_id: str
    card_id: str
    guid: Optional[str] = None

class SimpleActionCommand(BaseModel):
    game_id: str
    guid: str
    reasoning: Optional[Dict[str, Any]] = None

class ComplexActionCommand(BaseModel):
    game_id: str
    guid: str
    x: int = Field(..., ge=0, le=63)
    y: int = Field(..., ge=0, le=63)
    reasoning: Optional[Dict[str, Any]] = None

class FrameResponse(BaseModel):
    game_id: str
    guid: str
    frame: List[List[List[int]]]  # 64x64 grid of 4-bit color indices
    state: str  # NOT_FINISHED, NOT_STARTED, WIN, GAME_OVER
    score: int = Field(..., ge=0, le=254)
    win_score: int = Field(ge=0, le=254, default=100)
    action_input: Dict[str, Any]

# In-memory storage
scorecards_db: Dict[str, Dict[str, Any]] = {}
sessions_db: Dict[str, Dict[str, Any]] = {}

# Mock API key for development
MOCK_API_KEY = "test-api-key-12345"

def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key - in production this would check against a database"""
    if x_api_key != MOCK_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Games are now loaded from real data via game_loader

def create_frame_from_game_data(game_id: str, level: str = "level_1", frame_type: str = "initial") -> List[List[List[int]]]:
    """Create frame data from real game data"""
    frame_data = game_loader.get_frame_data(game_id, level, frame_type)
    if frame_data:
        return frame_data
    else:
        # Fallback to mock frame if no real data
        frame = []
        for y in range(64):
            row = []
            for x in range(64):
                color = (x + y) % 16
                row.append(color)
            frame.append(row)
        return [frame]

@app.get("/api/games")
async def list_games(api_key: str = Depends(verify_api_key)):
    """List available games"""
    return game_loader.get_available_games()

@app.post("/api/scorecard/open")
async def open_scorecard(
    request: OpenScorecardRequest,
    api_key: str = Depends(verify_api_key)
):
    """Open a scorecard (begin tracked run)"""
    card_id = str(uuid.uuid4())
    
    scorecards_db[card_id] = {
        "card_id": card_id,
        "api_key": api_key,
        "source_url": request.source_url,
        "tags": request.tags or [],
        "opaque": request.opaque,
        "won": 0,
        "played": 0,
        "total_actions": 0,
        "score": 0,
        "cards": {},
        "created_at": datetime.now().isoformat()
    }
    
    return OpenScorecardResponse(card_id=card_id)

@app.post("/api/scorecard/close")
async def close_scorecard(
    request: CloseScorecardRequest,
    api_key: str = Depends(verify_api_key)
):
    """Close a scorecard (finish run and aggregate statistics)"""
    if request.card_id not in scorecards_db:
        raise HTTPException(status_code=404, detail="Scorecard not found")
    
    scorecard = scorecards_db[request.card_id]
    
    # Convert to ScorecardSummary format
    cards_dict = {}
    for game_id, card_data in scorecard["cards"].items():
        cards_dict[game_id] = PerGameCard(**card_data)
    
    # Calculate score based on games won vs total games played
    score = 1 if scorecard["won"] > 0 else 0
    
    summary = ScorecardSummary(
        api_key=scorecard["api_key"],
        card_id=scorecard["card_id"],
        won=scorecard["won"],
        played=scorecard["played"],
        total_actions=scorecard["total_actions"],
        score=score,
        source_url=scorecard["source_url"],
        tags=scorecard["tags"],
        opaque=scorecard["opaque"],
        cards=cards_dict
    )
    
    return summary

@app.get("/api/scorecard/{card_id}")
async def get_scorecard(
    card_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Retrieve a scorecard"""
    if card_id not in scorecards_db:
        raise HTTPException(status_code=404, detail="Scorecard not found")
    
    scorecard = scorecards_db[card_id]
    
    # Convert to ScorecardSummary format
    cards_dict = {}
    for game_id, card_data in scorecard["cards"].items():
        cards_dict[game_id] = PerGameCard(**card_data)
    
    # Calculate score based on games won vs total games played
    score = 1 if scorecard["won"] > 0 else 0
    
    summary = ScorecardSummary(
        api_key=scorecard["api_key"],
        card_id=scorecard["card_id"],
        won=scorecard["won"],
        played=scorecard["played"],
        total_actions=scorecard["total_actions"],
        score=score,
        source_url=scorecard["source_url"],
        tags=scorecard["tags"],
        opaque=scorecard["opaque"],
        cards=cards_dict
    )
    
    return summary

@app.get("/api/scorecard/{card_id}/{game_id}")
async def get_scorecard_for_game(
    card_id: str,
    game_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Retrieve a scorecard filtered to one game"""
    if card_id not in scorecards_db:
        raise HTTPException(status_code=404, detail="Scorecard not found")
    
    scorecard = scorecards_db[card_id]
    
    if game_id not in scorecard["cards"]:
        raise HTTPException(status_code=404, detail="Game not found in scorecard")
    
    # Filter to just this game
    game_card = scorecard["cards"][game_id]
    
    # Recompute totals for this game only
    won = sum(1 for state in game_card["states"] if state == "WIN") if game_card["states"] else 0
    played = game_card["total_plays"]
    total_actions = game_card["total_actions"]
    score = 1 if won > 0 else 0  # Score is 1 if any games were won, 0 otherwise
    
    cards_dict = {game_id: PerGameCard(**game_card)}
    
    summary = ScorecardSummary(
        api_key=scorecard["api_key"],
        card_id=scorecard["card_id"],
        won=won,
        played=played,
        total_actions=total_actions,
        score=score,
        source_url=scorecard["source_url"],
        tags=scorecard["tags"],
        opaque=scorecard["opaque"],
        cards=cards_dict
    )
    
    return summary

@app.post("/api/cmd/RESET")
async def reset_game(
    command: ResetCommand,
    api_key: str = Depends(verify_api_key)
):
    """Start or reset a game instance and receive the first frame"""
    print(f"DEBUG: RESET called with game_id={command.game_id}, card_id={command.card_id}, guid={command.guid}")
    
    # Check if game exists in available games
    available_games = game_loader.get_available_games()
    game_exists = any(game["game_id"] == command.game_id for game in available_games)
    if not game_exists:
        raise HTTPException(status_code=400, detail="Unknown game_id")
    
    if command.card_id not in scorecards_db:
        raise HTTPException(status_code=400, detail="Unknown card_id")
    
    # Generate new session or use existing
    if command.guid is None:
        guid = str(uuid.uuid4())
    else:
        guid = command.guid
        if guid not in sessions_db:
            raise HTTPException(status_code=400, detail="Unknown guid")
    
    # Get game state from real data
    game_state = game_loader.get_game_state(command.game_id, "level_1")
    
    # Initialize or reset session
    sessions_db[guid] = {
        "game_id": command.game_id,
        "card_id": command.card_id,
        "state": game_state["state"],
        "score": game_state["score"],
        "level": "level_1",
        "actions_taken": 0,
        "created_at": datetime.now().isoformat(),
        "current_frame": create_frame_from_game_data(command.game_id, "level_1", "initial")
    }
    print(f"DEBUG: Session created with guid={guid}")
    print(f"DEBUG: sessions_db now has {len(sessions_db)} sessions: {list(sessions_db.keys())}")
    
    # Update scorecard
    scorecard = scorecards_db[command.card_id]
    if command.game_id not in scorecard["cards"]:
        scorecard["cards"][command.game_id] = {
            "game_id": command.game_id,
            "total_plays": 0,
            "total_actions": 0,
            "scores": [],
            "states": [],
            "actions": []
        }
    
    game_card = scorecard["cards"][command.game_id]
    game_card["total_plays"] += 1
    game_card["scores"].append(game_state["score"])
    game_card["states"].append(game_state["state"])
    game_card["actions"].append(0)
    
    # Increment overall scorecard played counter
    scorecard["played"] += 1
    
    return FrameResponse(
        game_id=command.game_id,
        guid=guid,
        frame=create_frame_from_game_data(command.game_id, "level_1", "initial"),
        state=game_state["state"],
        score=game_state["score"],
        win_score=100,  # Keep for API compatibility but not used for scoring
        action_input={"id": 0, "data": {}}
    )

def execute_action(game_id: str, guid: str, action_id: int, action_data: Dict[str, Any] = None):
    """Execute an action and return the frame response"""
    print(f"DEBUG: execute_action called with game_id={game_id}, guid={guid}, action_id={action_id}")
    print(f"DEBUG: sessions_db keys: {list(sessions_db.keys())}")
    
    if guid not in sessions_db:
        print(f"DEBUG: GUID {guid} not found in sessions_db")
        raise HTTPException(status_code=400, detail=f"Unknown guid: {guid}")
    
    session = sessions_db[guid]
    print(f"DEBUG: Session found: {session}")
    
    if session["game_id"] != game_id:
        print(f"DEBUG: Game ID mismatch. Session has {session['game_id']}, request has {game_id}")
        raise HTTPException(status_code=400, detail=f"Guid does not belong to game_id. Session: {session['game_id']}, Request: {game_id}")
    
    # Check if this is a click action on a blue cell for block toggling
    if action_id == 6 and action_data and "x" in action_data and "y" in action_data:
        x, y = action_data["x"], action_data["y"]
        current_frame = session.get("current_frame", [[]])
        
        if current_frame and len(current_frame) > 0 and len(current_frame[0]) > y and len(current_frame[0][y]) > x:
            # Define multiple 12x12 blocks with 5-cell gaps using formula
            # Block size: 12x12, Gap: 5 cells
            # Formula: x1 = base_x + (col * (12 + 5)), y1 = base_y + (row * (12 + 5))
            base_x, base_y = 4, 10
            block_size = 12
            gap = 4
            
            blocks = []
            block_index = 0
            for row in range(3):  # 3 rows
                for col in range(3):  # 3 columns
                    block_index += 1
                    # Skip the 5th block (center block)
                    if block_index == 5:
                        continue
                    
                    x1 = base_x + (col * (block_size + gap))
                    y1 = base_y + (row * (block_size + gap))
                    x2 = x1 + block_size - 1
                    y2 = y1 + block_size - 1
                    blocks.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
            
            # Check if click is within any of the blocks
            clicked_in_block = False
            for block in blocks:
                if block["x1"] <= x <= block["x2"] and block["y1"] <= y <= block["y2"]:
                    clicked_in_block = True
                    # Toggle the entire 12x12 block
                    toggled = False
                    old_colors = []
                    new_colors = []
                    
                    for block_y in range(block["y1"], block["y2"] + 1):  # y1 to y2 inclusive
                        for block_x in range(block["x1"], block["x2"] + 1):  # x1 to x2 inclusive
                            if block_y < len(current_frame[0]) and block_x < len(current_frame[0][block_y]):
                                block_color = current_frame[0][block_y][block_x]
                                if block_color == 9:  # Blue
                                    current_frame[0][block_y][block_x] = 8  # Red
                                    toggled = True
                                    old_colors.append(9)
                                    new_colors.append(8)
                                elif block_color == 8:  # Red
                                    current_frame[0][block_y][block_x] = 9  # Blue
                                    toggled = True
                                    old_colors.append(8)
                                    new_colors.append(9)
                                else:
                                    # For other colors, default to blue
                                    current_frame[0][block_y][block_x] = 9
                                    toggled = True
                                    old_colors.append(block_color)
                                    new_colors.append(9)
                    
                    if toggled:
                        session["current_frame"] = current_frame
                        
                        # Update session
                        session["actions_taken"] += 1
                        
                        # Update scorecard
                        scorecard = scorecards_db[session["card_id"]]
                        game_card = scorecard["cards"][game_id]
                        game_card["total_actions"] += 1
                        game_card["actions"][-1] += 1
                        
                        scorecard["total_actions"] += 1
                        
                        # Check win condition: only 4 specific blocks should be red (color 8)
                        # Block coordinates: base_x=4, base_y=10, block_size=12, gap=4
                        # Based on final state analysis, only blocks 2,4,6,8 should be red
                        win_condition_met = True
                        
                        # Define the 4 blocks that need to be red (based on final state)
                        win_blocks = [
                            {"x1": 20, "y1": 10, "x2": 31, "y2": 21},  # Block 2 - should be red
                            {"x1": 4, "y1": 26, "x2": 15, "y2": 37},   # Block 4 - should be red
                            {"x1": 36, "y1": 26, "x2": 47, "y2": 37},  # Block 6 - should be red
                            {"x1": 20, "y1": 42, "x2": 31, "y2": 53}   # Block 8 - should be red
                        ]
                        
                        # Check if all win blocks are red (color 8)
                        for win_block in win_blocks:
                            for block_y in range(win_block["y1"], win_block["y2"] + 1):
                                for block_x in range(win_block["x1"], win_block["x2"] + 1):
                                    if block_y < len(current_frame[0]) and block_x < len(current_frame[0][block_y]):
                                        if current_frame[0][block_y][block_x] != 8:  # Not red
                                            win_condition_met = False
                                            break
                                if not win_condition_met:
                                    break
                        
                        if win_condition_met:
                            # Win condition met!
                            session["state"] = "WIN"
                            session["score"] = 1  # Set score to 1 when winning
                            game_card["scores"][-1] = session["score"]
                            game_card["states"][-1] = "WIN"
                            scorecard["won"] += 1
                            scorecard["score"] = 1  # Set overall scorecard score to 1 when winning
                            
                            return FrameResponse(
                                game_id=game_id,
                                guid=guid,
                                frame=current_frame,
                                state="WIN",
                                score=session["score"],
                                action_input={
                                    "id": action_id, 
                                    "data": action_data, 
                                    "toggled": True, 
                                    "block_toggled": True,
                                    "block_coords": block,
                                    "old_colors": old_colors,
                                    "new_colors": new_colors,
                                    "win_achieved": True,
                                    "blocks_completed": True
                                }
                            )
                        
                        return FrameResponse(
                            game_id=game_id,
                            guid=guid,
                            frame=current_frame,
                            state=session["state"],
                            score=session["score"],
                            action_input={
                                "id": action_id, 
                                "data": action_data, 
                                "toggled": True, 
                                "block_toggled": True,
                                "block_coords": block,
                                "old_colors": old_colors,
                                "new_colors": new_colors
                            }
                        )
            
            # If click was outside all blocks, return no-op (same frame)
            if not clicked_in_block:
                return FrameResponse(
                    game_id=game_id,
                    guid=guid,
                    frame=current_frame,
                    state=session["state"],
                    score=session["score"],
                    win_score=session["win_score"],
                    action_input={
                        "id": action_id, 
                        "data": action_data, 
                        "toggled": False, 
                        "block_toggled": False,
                        "no_op": True
                    }
                )
    
    # Regular action execution
    session["actions_taken"] += 1
    
    # Get current level from session
    level = session.get("level", "level_1")
    
    # Calculate meaningful score based on progress toward solution
    # For this specific game, score should be based on how many correct blocks are toggled
    current_frame = session.get("current_frame", [[]])
    final_data = game_loader.get_frame_data(game_id, level, "final")
    
    if final_data and len(final_data) > 0 and current_frame and len(current_frame) > 0:
        final_frame = final_data[0]
        correct_cells = 0
        total_cells = 0
        
        # Count how many cells match the final pattern
        for y in range(64):
            for x in range(64):
                if y < len(current_frame[0]) and x < len(current_frame[0][y]):
                    current_color = current_frame[0][y][x]
                    final_color = final_frame[y][x] if y < len(final_frame) and x < len(final_frame[y]) else 0
                    if current_color == final_color:
                        correct_cells += 1
                    total_cells += 1
        
        # Calculate score as percentage of correct cells (0-100 scale)
        if total_cells > 0:
            progress_percentage = correct_cells / total_cells
            session["score"] = int(progress_percentage * 100)
        else:
            session["score"] = session["score"] + 1
    else:
        # Fallback to simple scoring if no final data available
        session["score"] = session["score"] + 1
    
    # Update scorecard
    scorecard = scorecards_db[session["card_id"]]
    game_card = scorecard["cards"][game_id]
    game_card["total_actions"] += 1
    game_card["actions"][-1] += 1
    game_card["scores"][-1] = session["score"]
    
    # Check win condition against final pattern
    final_data = game_loader.get_frame_data(game_id, level, "final")
    if final_data and len(final_data) > 0:
        final_frame = final_data[0]
        current_frame = session.get("current_frame", [[]])
        
        # Check if current frame matches the final pattern
        matches_final = True
        if current_frame and len(current_frame) > 0:
            for check_y in range(64):
                for check_x in range(64):
                    if check_y < len(current_frame[0]) and check_x < len(current_frame[0][check_y]):
                        current_color = current_frame[0][check_y][check_x]
                        final_color = final_frame[check_y][check_x] if check_y < len(final_frame) and check_x < len(final_frame[check_y]) else 0
                        if current_color != final_color:
                            matches_final = False
                            break
                if not matches_final:
                    break
        
        if matches_final:
            session["state"] = "WIN"
            session["score"] = 1  # Set score to 1 when winning
            game_card["states"][-1] = "WIN"
            scorecard["won"] += 1
            scorecard["score"] = 1  # Set overall scorecard score to 1 when winning
        else:
            session["state"] = "NOT_FINISHED"
            game_card["states"][-1] = "NOT_FINISHED"
    else:
        # Fallback - no win condition without final data
        session["state"] = "NOT_FINISHED"
        game_card["states"][-1] = "NOT_FINISHED"
    
    scorecard["total_actions"] += 1
    
    # Get frame data based on current state
    frame_type = "final" if session["state"] == "WIN" else "initial"
    frame_data = create_frame_from_game_data(game_id, level, frame_type)
    
    # Update session with new frame data
    session["current_frame"] = frame_data
    
    return FrameResponse(
        game_id=game_id,
        guid=guid,
        frame=frame_data,
        state=session["state"],
        score=session["score"],
        win_score=100,  # Keep for API compatibility but not used for scoring
        action_input={"id": action_id, "data": action_data or {}}
    )

@app.post("/api/cmd/ACTION1")
async def action1(
    command: SimpleActionCommand,
    api_key: str = Depends(verify_api_key)
):
    """Execute simple action 1"""
    return execute_action(command.game_id, command.guid, 1, command.reasoning)

@app.post("/api/cmd/ACTION2")
async def action2(
    command: SimpleActionCommand,
    api_key: str = Depends(verify_api_key)
):
    """Execute simple action 2"""
    return execute_action(command.game_id, command.guid, 2, command.reasoning)

@app.post("/api/cmd/ACTION3")
async def action3(
    command: SimpleActionCommand,
    api_key: str = Depends(verify_api_key)
):
    """Execute simple action 3"""
    return execute_action(command.game_id, command.guid, 3, command.reasoning)

@app.post("/api/cmd/ACTION4")
async def action4(
    command: SimpleActionCommand,
    api_key: str = Depends(verify_api_key)
):
    """Execute simple action 4"""
    return execute_action(command.game_id, command.guid, 4, command.reasoning)

@app.post("/api/cmd/ACTION5")
async def action5(
    command: SimpleActionCommand,
    api_key: str = Depends(verify_api_key)
):
    """Execute simple action 5"""
    return execute_action(command.game_id, command.guid, 5, command.reasoning)

@app.post("/api/cmd/ACTION6")
async def action6(
    command: ComplexActionCommand,
    api_key: str = Depends(verify_api_key)
):
    """Execute complex action (requires x,y)"""
    print(f"DEBUG: ACTION6 received - game_id={command.game_id}, guid={command.guid}, x={command.x}, y={command.y}")
    action_data = {"x": command.x, "y": command.y}
    if command.reasoning:
        action_data.update(command.reasoning)
    
    return execute_action(command.game_id, command.guid, 6, action_data)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "ARC-AGI-3 REST API",
        "version": "1.0.0",
        "description": "Programmatic interface for running agents against ARC-AGI-3 games",
        "endpoints": {
            "/api/games": "List available games",
            "/api/scorecard/open": "Open a scorecard",
            "/api/scorecard/close": "Close a scorecard",
            "/api/scorecard/{card_id}": "Get scorecard details",
            "/api/cmd/RESET": "Reset game session",
            "/api/cmd/ACTION1-6": "Execute actions"
        },
        "note": "All requests require X-API-Key header"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "arc-agi-3-engine"}

if __name__ == "__main__":
    uvicorn.run('backend:app', host="0.0.0.0", port=3193, reload=1) 