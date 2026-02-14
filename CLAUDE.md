# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project provides browser-based access to KiCad (open-source EDA software) with AI automation capabilities. It consists of the KiCad source code plus an AI automation layer that enables programmatic control through REST APIs and WebSocket.

**Key Design Constraint**: The system supports multiple operation modes:
1. **IPC API Mode** (Recommended): Uses KiCad 9.0+ official IPC API via `kicad-python` library for precise programmatic control
2. **PyAutoGUI Mode**: Legacy automation using mouse/keyboard simulation with virtual display (X11 on Linux, fallback on Windows)
3. **Docker/X11 Mode**: Full containerized environment with virtual display (Linux only)

**Windows Local Development**: Now fully supported through IPC API mode. Screenshot functionality in PyAutoGUI mode is limited on Windows (captures entire screen). Use IPC API mode for production Windows usage.

## Repository Structure

```
kicad-for-chrome/
├── kicad-source/          # Official KiCad source code (C++, CMake)
├── kicad-ai-auto/         # AI automation layer
│   ├── agent/             # FastAPI backend (Python)
│   ├── web/               # React frontend (TypeScript/Vite)
│   ├── docker/            # Docker configuration for KiCad runtime
│   ├── playwright-tests/  # Playwright automation interface
│   └── nginx/             # Reverse proxy configuration
├── kicad-symbols/         # Schematic symbol libraries
├── kicad-footprints/      # PCB footprint libraries
├── kicad-packages3D/      # 3D component models
└── kicad-templates/       # Project templates
```

## Development Commands

### KiCad Source (C++)

```bash
# Build KiCad from source (Linux/macOS)
cd kicad-source
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Build with specific options
cmake .. -DKICAD_SCRIPTING_WXPYTHON=ON -DKICAD_BUILD_QA_TESTS=ON

# Run QA tests
cd build
ctest --output-on-failure
```

### AI Automation Layer

```bash
# Start all services with Docker Compose (recommended for Linux)
cd kicad-ai-auto
docker-compose up -d

# View logs
docker-compose logs -f control-agent

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Windows Local Development (IPC API Mode)

```bash
# One-click startup (recommended)
一键启动.bat                    # Full automated startup
start-all-auto.bat              # Interactive startup with progress display
诊断工具.bat                    # Diagnostic tool to check environment

# Manual startup (step by step)
cd kicad-ai-auto/agent
venv\Scripts\python main.py    # Start backend (port 8000)

# In KiCad GUI: Tools → External Plugin → Start Server (required once)

cd kicad-ai-auto/web
npm run dev                    # Start frontend (port 3000)
```

**Prerequisites for Windows IPC API**:
- KiCad 9.0+ installed (default: `E:\Program Files\KiCad\9.0`)
- Python dependencies: `pip install kicad-python pywin32`
- `.env` file configured with `KICAD_CLI_PATH` and `USE_VIRTUAL_DISPLAY=false`

### Backend Development (without Docker)

```bash
cd kicad-ai-auto/agent
pip install -r ../docker/requirements.txt

# Run the server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Development

```bash
cd kicad-ai-auto/web
npm install
npm run dev          # Development server on port 3000
npm run build        # Production build
npm run lint         # ESLint check
npm run test         # Run tests with Vitest
```

### Testing

**Backend Tests:**
```bash
cd kicad-ai-auto/agent

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run a single test
pytest tests/test_api.py::TestProjectAPI::test_start_kicad -v
```

**Frontend Tests:**
```bash
cd kicad-ai-auto/web

# Run tests once
npm run test -- --run

# Run tests in watch mode
npm run test

# Run with coverage
npm run test:coverage

# Run a specific test file
npm run test -- --run src/test/api.test.ts
```

**All Tests:**
```bash
cd kicad-ai-auto
python run_all_tests.py
```

**Playwright E2E Tests:**
```bash
# Requires Docker services running
docker-compose up -d
cd playwright-tests
pytest test_kicad_automation.py -v
```

## Architecture

### System Components

The AI automation layer supports multiple operation modes:

**1. IPC API Mode** (Recommended for KiCad 9.0+):
```
Browser (React) ←→ FastAPI Agent ←→ kipy (IPC Client) ←→ KiCad PCB Editor (GUI)
    ↑                    ↑                    ↑                      ↑
 WebSocket          REST API        Windows Named Pipe /    Tools → External Plugin
                     /api/*         Unix Socket           → Start Server (required)
```

**2. PyAutoGUI Mode** (Legacy, cross-version):
```
Browser (React) ←→ FastAPI Agent ←→ KiCad (X11 Virtual Display)
                  ↓                  ↓                   ↑
              WebSocket          PyAutoGUI         python-xlib
            (screenshot)      (input)           (display)
```

**3. Docker/X11 Mode** (Linux containerized):
```
Browser ←→ nginx ←→ FastAPI Agent ←→ KiCad in Docker (Xvfb + noVNC)
                                 ↓
                            python-xlib + PyAutoGUI
```

**Key Flows:**
- **IPC API Routes** (`/api/kicad-ipc/*`): Direct KiCad 9.0+ IPC API access (Windows/Linux/macOS)
- **Legacy REST API** (`/api/*`): Project management, tool activation, file export, DRC (PyAutoGUI mode)
- **WebSocket** (`/ws/control` and `/api/kicad-ipc/ws`): Real-time control and status updates
- **kicad-python (kipy)**: Official KiCad IPC API client library
- **PyAutoGUI**: Simulates user input on virtual/physical display (fallback mode)
- **python-xlib**: Captures screenshots from X11 virtual display (Linux Docker only)

### KiCad Source Components

- **eeschema/** - Schematic editor
- **pcbnew/** - PCB layout editor
- **3d-viewer/** - 3D visualization
- **cvpcb/** - Component footprint selector
- **gerbview/** - Gerber file viewer
- **common/** - Shared utilities
- **libs/** - Core libraries (geometry, etc.)
- **scripting/** - Python scripting interface
- **qa/** - Unit tests and QA framework

### AI Control Agent (FastAPI)

The agent (`kicad-ai-auto/agent/main.py`) provides multiple API sets depending on operation mode:

**IPC API Routes** (KiCad 9.0+ with `kicad-python` installed):
- `/api/kicad-ipc/start` - Start KiCad and establish IPC connection
- `/api/kicad-ipc/stop` - Close KiCad connection
- `/api/kicad-ipc/status` - Get connection status and board info
- `/api/kicad-ipc/action` - Execute KiCad action
- `/api/kicad-ipc/footprint` - Create footprint (component)
- `/api/kicad-ipc/items` - Get PCB item list
- `/api/kicad-ipc/selection` - Get current selection
- `/api/kicad-ipc/screenshot` - Export screenshot (SVG)
- WebSocket: `/api/kicad-ipc/ws` - Real-time status updates

**Legacy PyAutoGUI API Routes** (cross-version, requires X11/display):
- `/api/project/start`, `/api/project/open`, `/api/project/save` - Project management
- `/api/menu/click` - Menu interactions
- `/api/tool/activate` - Tool activation
- `/api/input/mouse`, `/api/input/keyboard` - Input simulation
- `/api/export` - File export (Gerber, BOM, STEP, etc.)
- `/api/drc/run`, `/api/drc/report` - Design rule checking
- `/api/state/screenshot`, `/api/state/full` - State queries
- WebSocket: `/ws/control` (port 8001) - Mouse/keyboard events, screenshot commands

**Common Routes**:
- `/api/health` - Health check endpoint
- `/docs` - Swagger UI documentation (Auto-generated)

### Control Layer

**PyAutoGUI Mode** (`kicad_controller.py`):
- PyAutoGUI for mouse/keyboard input
- python-xlib for X11 window management and screenshots (Linux Docker only)
- Relative coordinates for multi-resolution support (1920x1080 baseline)
- Menu coordinates stored as relative positions adapted to actual screen resolution

**IPC API Mode** (`kicad_ipc_manager.py`):
- `kicad-python` (kipy) library for official KiCad IPC API
- Windows Named Pipe or Unix Socket communication
- Direct programmatic control (no UI simulation)
- Requires KiCad GUI running with `Tools → External Plugin → Start Server`
- Automatic fallback to PyAutoGUI mode if IPC unavailable

### Web Frontend

React + TypeScript stack:
- Vite for bundling (dev server proxies `/api` and `/ws` to backend)
- Zustand for state management (`kicadStore`)
- Tailwind CSS for styling
- WebSocket connection to backend for real-time updates
- Axios for REST API calls

## Docker Services

The `docker-compose.yml` defines:

| Service | Port | Purpose |
|---------|------|---------|
| kicad-runtime | 6080 (noVNC), 5900 (VNC) | KiCad with virtual display |
| control-agent | 8000 (REST), 8001 (WS) | FastAPI backend |
| web-ui | 3000 | React frontend |
| redis | 6379 | Caching/state |
| nginx | 80, 443 | Reverse proxy |

## Environment Variables

Key environment variables for the agent:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `ALLOWED_ORIGINS` | http://localhost:3000,http://localhost:3001,http://localhost:5173 | CORS origins |
| `API_KEY` | (empty) | Optional API authentication |
| `PROJECTS_DIR` | /projects | Project files directory |
| `OUTPUT_DIR` | /output | Export output directory |
| `DISPLAY` | :99 | X11 display ID (PyAutoGUI mode only) |
| `REDIS_URL` | redis://redis:6379 | Redis connection |
| `KICAD_CLI_PATH` | (empty) | Path to `kicad-cli.exe` (Windows: `E:\Program Files\KiCad\9.0\bin\kicad-cli.exe`) |
| `USE_VIRTUAL_DISPLAY` | false | Whether to use virtual display (set to `false` for Windows local) |

## Important Files

**KiCad Source**:
- `kicad-source/CMakeLists.txt` - Main build configuration

**AI Automation Layer**:
- `kicad-ai-auto/docker-compose.yml` - Service orchestration (Docker/X11 mode)
- `kicad-ai-auto/agent/main.py` - FastAPI application entry point
- `kicad-ai-auto/agent/kicad_controller.py` - Core PyAutoGUI automation logic
- `kicad-ai-auto/agent/kicad_ipc_manager.py` - IPC API manager for KiCad 9.0+
- `kicad-ai-auto/agent/routes/kicad_ipc_routes.py` - IPC API route definitions
- `kicad-ai-auto/agent/auto_starter.py` - Automatic startup script for Windows
- `kicad-ai-auto/agent/middleware.py` - Error handling, logging, custom exceptions
- `kicad-ai-auto/web/package.json` - Frontend dependencies
- `kicad-ai-auto/web/vite.config.ts` - Vite configuration with proxy settings

**Configuration and Scripts**:
- `.env` - Environment variables configuration
- `一键启动.bat`, `start-all-auto.bat`, `诊断工具.bat` - Windows startup scripts
- `README_AUTO_START.md`, `QUICK_START.md` - Startup guides
- `KICAD_IPC_INTEGRATION.md` - IPC API technical documentation
- `WHY_WINDOWS_LIMITED.md` - Platform limitations explanation

## KiCad Build Options

Key CMake options (see `kicad-source/CMakeLists.txt`):
- `KICAD_SCRIPTING_WXPYTHON` - Python scripting support
- `KICAD_BUILD_QA_TESTS` - Build unit tests
- `KICAD_BUILD_I18N` - Translation support
- `KICAD_USE_SENTRY` - Error reporting

## Security Notes

The agent implements:
- API key authentication (`X-API-Key` header)
- CORS origin restrictions
- Rate limiting (slowapi): 200/minute default, specific limits for endpoints
- Path traversal prevention for file uploads
- File size limits (50MB max)
- Allowed file extension validation for uploads

## Platform Limitations

**Operation Modes by Platform**:

| Platform | Recommended Mode | Limitations |
|----------|-----------------|-------------|
| **Windows** | IPC API Mode (KiCad 9.0+) | - Requires KiCad GUI running<br>- `Tools → External Plugin → Start Server` required once<br>- PyAutoGUI mode screenshots capture entire screen (not production suitable) |
| **Linux/macOS** | IPC API Mode or Docker/X11 Mode | - IPC API requires KiCad GUI<br>- Docker/X11 mode provides full isolation |
| **All Platforms** | PyAutoGUI Mode (legacy) | - Cross-version support<br>- Requires X11 virtual display on Linux<br>- Limited screenshot capability on Windows |

**Key Considerations**:
1. **IPC API Mode**: Requires KiCad 9.0+ with `kicad-python` library installed
2. **Docker/X11 Mode**: Only works on Linux with X11 support
3. **Windows Production**: Use IPC API mode for reliable operation
4. **KiCad Version**: IPC API only available in KiCad 9.0+

See `WHY_WINDOWS_LIMITED.md` for detailed technical explanation of PyAutoGUI limitations.
