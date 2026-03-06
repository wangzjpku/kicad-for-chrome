# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KiCad AI Automation is an AI-driven PCB design automation solution. Users describe circuit requirements in natural language, and AI automatically generates schematics and PCB layouts with support for exporting manufacturing files.

## Architecture

### Multi-Mode Operation

The system supports three operation modes:
1. **IPC API Mode** (Recommended): Uses KiCad 9.0+ official IPC API via `kicad-python` (kipy) library
2. **Docker/X11 Mode**: Linux containerized with virtual display
3. **PyAutoGUI Mode**: Legacy automation using mouse/keyboard simulation

### System Flow

```
Browser (React) ←→ FastAPI Agent ←→ KiCad (via kipy IPC / PyAutoGUI / Docker X11)
       ↑                    ↑                      ↑
   WebSocket            REST API             KiCad GUI
   Real-time           /api/*              pcbnew/eeschema
```

### Key Components

- **agent/** - Python FastAPI backend
  - `main.py` - Entry point with all route registrations
  - `routes/` - API endpoints (ai_routes.py, project_routes.py, kicad_ipc_routes.py)
  - `kicad_ipc_manager.py` - KiCad 9.0+ IPC API client
  - `kicad_controller.py` - PyAutoGUI automation (legacy)
  - `footprint_parser.py` - KiCad footprint library parser
  - `symbol_lib_parser.py` - KiCad symbol library parser

- **web/** - React TypeScript frontend
  - `src/editors/` - PCBEditor.tsx, SchematicEditor.tsx (Konva.js canvas)
  - `src/stores/` - Zustand state management (kicadStore)
  - `src/services/` - API calls to backend

## Development Commands

### Backend (Windows)

```bash
# Start backend
cd kicad-ai-auto/agent
./venv/Scripts/python.exe main.py

# Run Python tests
pytest tests/ -v
pytest tests/test_api.py::TestProjectAPI::test_start_kicad -v
```

### Frontend

```bash
cd kicad-ai-auto/web
npm run dev          # Development server (port 3000)
npm run build       # Production build
npm run test        # Run tests with Vitest
npm run test -- --run  # Run tests once
npm run lint        # ESLint check
```

### Docker (Linux)

```bash
cd kicad-ai-auto
docker-compose up -d
```

## Key Files

- **API Routes**: `agent/routes/project_routes.py` - Project CRUD, PCB/schematic data
- **AI Generation**: `agent/routes/ai_routes.py` - Circuit analysis and generation
- **IPC Control**: `agent/kicad_ipc_manager.py` - KiCad 9.0+ programmatic control
- **Frontend State**: `web/src/stores/kicadStore.ts` - Zustand store for project/schematic/PCB state
- **PCB Rendering**: `web/src/editors/PCBEditor.tsx` - Konva.js canvas rendering
- **Schematic Rendering**: `web/src/editors/SchematicEditor.tsx` - Konva.js canvas rendering

## Environment Variables

Key variables in `agent/.env`:
- `KICAD_CLI_PATH` - Path to kicad-cli.exe (Windows: `E:\Program Files\KiCad\9.0\bin\kicad-cli.exe`)
- `USE_VIRTUAL_DISPLAY` - Set to `false` for Windows local IPC mode

## Important Notes

- IPC API mode requires KiCad GUI running with "Tools → External Plugin → Start Server"
- kipy works through IPC, not direct Python imports - requires KiCad GUI
- Frontend proxies `/api` and `/ws` to backend via Vite config
- PCB/schematic data uses KiCad's native footprint/symbol libraries for component definitions
