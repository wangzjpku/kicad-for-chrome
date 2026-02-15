# AGENTS.md - Agent Coding Guidelines

This file provides guidance for AI agents operating in this repository.

## Project Overview

KiCad for Chrome - Browser-based access to KiCad (open-source EDA software) with AI automation through REST APIs and WebSocket. The project consists of:

- **kicad-source/** - Official KiCad source code (C++, CMake)
- **kicad-ai-auto/** - AI automation layer
  - **agent/** - FastAPI backend (Python)
  - **web/** - React frontend (TypeScript/Vite)

## Build, Lint, and Test Commands

### Backend (Python/FastAPI)

```bash
# Navigate to agent directory
cd kicad-ai-auto/agent

# Activate virtual environment (Windows)
venv\Scripts\python main.py

# Run all tests
pytest tests/ -v

# Run single test
pytest tests/test_api.py::TestProjectAPI::test_start_kicad -v

# Run tests excluding slow ones
pytest -m "not slow"

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Frontend (TypeScript/React)

```bash
# Navigate to web directory
cd kicad-ai-auto/web

# Install dependencies
npm install

# Development server (port 3000)
npm run dev

# Production build
npm run build

# Lint check
npm run lint

# Run tests (watch mode)
npm test

# Run tests once
npm test -- --run

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- --run src/test/api.test.ts
```

### All Tests

```bash
# Run all tests (backend + frontend)
cd kicad-ai-auto
python run_all_tests.py
```

## Code Style Guidelines

### Python (Backend)

**Imports:**
- Standard library first, then third-party, then local
- Group imports by type (stdlib, third-party, local)
- Use explicit imports (`from x import y`)

```python
# Correct
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import List, Optional

from middleware import ErrorHandlingMiddleware
from kicad_controller import KiCadController
```

**Naming:**
- `snake_case` for functions, variables, methods
- `PascalCase` for classes, exceptions
- `UPPER_SNAKE_CASE` for constants

```python
# Variables and functions
def get_project_info():
    project_path = "/path/to/project"

# Classes
class KiCadController:
    pass

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024
```

**Type Hints:**
- Use type hints for function parameters and return values
- Use `Optional[X]` instead of `X | None` for Python 3.10 compatibility

```python
def process_file(path: str, timeout: Optional[int] = None) -> bool:
    ...
```

**Error Handling:**
- Use custom exceptions from `middleware.py`
- Always log errors with appropriate level

```python
from middleware import KiCadError, KiCadTimeoutError

try:
    result = kicad_controller.get_screenshot()
except KiCadTimeoutError as e:
    logger.error(f"Timeout getting screenshot: {e}")
    raise HTTPException(status_code=504, detail=str(e))
```

**Pydantic Models:**
- Use for all API request/response schemas
- Add validators for path validation and security

```python
class ProjectPath(BaseModel):
    path: str

    @validator("path")
    def validate_path(cls, v):
        if ".." in v or not v.startswith("/"):
            raise ValueError("Invalid path: path traversal not allowed")
        return v
```

**Async/Await:**
- Use async def for FastAPI endpoints
- Use asyncio for concurrent operations
- Mock async functions in tests with `AsyncMock`

### TypeScript/React (Frontend)

**Imports:**
- React imports first, then external libraries, then local
- Use path aliases (`@/*` maps to `src/*`)

```typescript
// Correct
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PCBData, ApiResponse } from '../types';
import { projectApi } from '../services/api';
```

**Naming:**
- `camelCase` for variables, functions
- `PascalCase` for components, interfaces, types
- `UPPER_SNAKE_CASE` for constants

```typescript
// Variables and functions
const fetchProject = async (id: string): Promise<Project> => {
  const projectPath = '/projects';
};

// Components and Types
interface PCBProps {
  data: PCBData;
}

const PCBViewer: React.FC<PCBProps> = ({ data }) => {
  // ...
};
```

**TypeScript:**
- Use strict mode (see tsconfig.json)
- Avoid `any` - use `unknown` if type is truly unknown
- Use interfaces for object shapes, types for unions/intersections

```typescript
// Good
interface Project {
  id: string;
  name: string;
  modified: Date;
}

// Avoid
const project: any = {};
```

**React Components:**
- Use functional components with hooks
- Prefer composition over inheritance
- Extract custom hooks for reusable logic

```typescript
// Good - custom hook
const useProject = (projectId: string) => {
  const [project, setProject] = useState<Project | null>(null);
  // ...
  return { project, loading, error };
};
```

**State Management (Zustand):**
- Create stores in `stores/` directory
- Use TypeScript interfaces for store state

```typescript
interface KiCadStore {
  isConnected: boolean;
  currentTool: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
}

export const useKiCadStore = create<KiCadStore>((set) => ({
  isConnected: false,
  currentTool: null,
  connect: async () => { /* ... */ },
  disconnect: () => set({ isConnected: false }),
}));
```

**Tailwind CSS:**
- Use utility classes for styling
- Follow component composition patterns

```tsx
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
  Click Me
</button>
```

**Testing:**
- Tests in `src/test/` directory
- Use `@testing-library/react` for component tests
- Use `describe`, `it`, `expect` (Vitest)

```typescript
describe('projectApi', () => {
  it('should fetch projects', async () => {
    const response = await projectApi.listProjects();
    expect(response.success).toBe(true);
  });
});
```

## Project Structure

```
kicad-for-chrome/
├── kicad-source/           # KiCad C++ source (do not modify)
├── kicad-ai-auto/
│   ├── agent/              # Python FastAPI backend
│   │   ├── main.py         # Entry point
│   │   ├── middleware.py   # Error handling, logging
│   │   ├── routes/         # API route handlers
│   │   └── tests/          # pytest tests
│   └── web/                # React frontend
│       ├── src/
│       │   ├── components/ # React components
│       │   ├── hooks/      # Custom hooks
│       │   ├── services/   # API clients
│       │   ├── stores/     # Zustand stores
│       │   ├── types/      # TypeScript types
│       │   └── test/       # Vitest tests
│       └── package.json
```

## Key Constraints

- **NEVER** suppress type errors with `as any`, `@ts-ignore`
- **NEVER** use empty catch blocks
- **NEVER** commit without explicit request
- **ALWAYS** run lsp_diagnostics before reporting completion
- **ALWAYS** follow existing patterns in the codebase

## Platform Notes

- Windows development uses IPC API mode (KiCad 9.0+)
- Linux development can use Docker/X11 mode
- Frontend changes: delegate to `frontend-ui-ux-engineer` for visual work
- Backend logic changes: handle directly
