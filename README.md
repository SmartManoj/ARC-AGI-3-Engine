# ARC-AGI-3 Engine API

A local FastAPI implementation of the official ARC-AGI-3 REST API for testing and development purposes, featuring both backend API and frontend web interface.

## Features

- **Backend API**: Full REST API implementation with FastAPI
- **Frontend Web Interface**: Interactive web player for testing games
- **Game Management**: List available games and manage game sessions
- **Scorecard System**: Open, track, and close scorecards for aggregated results
- **Action Commands**: Execute simple (ACTION1-5) and complex (ACTION6) actions
- **Frame Responses**: Receive visual frames and game state updates
- **API Key Authentication**: Secure endpoints with X-API-Key header
- **CORS Support**: Cross-origin requests enabled
- **Health Monitoring**: Built-in health check endpoint

## Project Structure

```
ARC-AGI-3-Engine/
├── backend/
│   ├── backend.py           # FastAPI application
│   ├── game_data_loader.py  # Game data loading utilities
│   ├── game_data/           # Game data files
│   ├── document.yaml        # Official API specification
│   ├── pyproject.toml       # Backend dependencies
│   └── requirements.txt     # Backend dependencies
├── frontend/
│   ├── index.html           # Main web interface
│   ├── play.html            # Game player interface
│   └── serve_static.py      # Static file server
├── README.md               # This file
└── .gitattributes         # Git configuration
```

## Installation

1. Navigate to the ARC-AGI-3-Engine directory:
```bash
cd ARC-AGI-3-Engine
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

## Running the Application

### Backend API Only

Navigate to the backend directory and run:
```bash
cd backend
python backend.py
```

The API will be available at `http://localhost:3193`

### Frontend Web Interface

The frontend provides an interactive web interface for testing games. To serve the frontend:

```bash
cd frontend
python serve_static.py
```

The web interface will be available at `http://localhost:3194`


## API Endpoints

### Authentication
All requests require an `X-API-Key` header. For development, use: `test-api-key-12345`

### Games
- `GET /api/games` - List available games

### Scorecards
- `POST /api/scorecard/open` - Open a scorecard (begin tracked run)
- `POST /api/scorecard/close` - Close a scorecard (finish run and aggregate statistics)
- `GET /api/scorecard/{card_id}` - Retrieve a scorecard
- `GET /api/scorecard/{card_id}/{game_id}` - Retrieve a scorecard filtered to one game

### Commands
- `POST /api/cmd/RESET` - Start or reset a game instance
- `POST /api/cmd/ACTION1` - Execute simple action 1
- `POST /api/cmd/ACTION2` - Execute simple action 2
- `POST /api/cmd/ACTION3` - Execute simple action 3
- `POST /api/cmd/ACTION4` - Execute simple action 4
- `POST /api/cmd/ACTION5` - Execute simple action 5
- `POST /api/cmd/ACTION6` - Execute complex action (requires x,y coordinates)

### Utility
- `GET /` - API information
- `GET /health` - Health check

## API Documentation

Once the backend server is running, visit:
- **Interactive API docs**: `http://localhost:3193/docs`
- **ReDoc documentation**: `http://localhost:3193/redoc`



## Development

### Backend Development

The backend is built with FastAPI and provides the core API functionality:

- **FastAPI Application**: Located in `backend/backend.py`
- **Game Data Loading**: Utilities in `backend/game_data_loader.py`
- **API Specification**: Official spec in `backend/document.yaml`

### Frontend Development

The frontend provides a web interface for testing:

- **Main Interface**: `frontend/index.html` - Game selection and management
- **Game Player**: `frontend/play.html` - Interactive game player
- **Static Server**: `frontend/serve_static.py` - Serves static files

### Adding New Features

1. Follow the official API specification in `backend/document.yaml`
2. Add new endpoints with proper authentication in `backend/backend.py`
3. Update frontend interfaces as needed
4. Ensure compatibility with the official ARC-AGI-3 API

