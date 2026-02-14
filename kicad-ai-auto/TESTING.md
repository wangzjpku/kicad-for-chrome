# KiCad AI Auto - Testing Guide

## Overview

This document describes the testing strategy and how to run tests for the KiCad AI Auto project.

## Test Structure

```
kicad-ai-auto/
├── agent/
│   ├── tests/                    # Backend (Python) tests
│   │   ├── __init__.py
│   │   ├── conftest.py           # Pytest fixtures
│   │   ├── test_middleware.py    # Middleware tests
│   │   ├── test_export_manager.py # Export manager tests
│   │   └── test_api.py           # API endpoint tests
│   ├── pytest.ini                # Pytest configuration
│   └── run_tests.py              # Test runner script
├── web/
│   └── src/
│       └── test/                 # Frontend (TypeScript) tests
│           ├── setup.ts          # Test setup and mocks
│           ├── App.test.tsx      # App component tests
│           ├── MenuBar.test.tsx  # MenuBar component tests
│           ├── kicadStore.test.ts # Zustand store tests
│           ├── api.test.ts       # API service tests
│           └── useWebSocket.test.ts # WebSocket hook tests
└── playwright-tests/
    └── test_kicad_automation.py  # E2E automation tests
```

## Running Tests

### All Tests

From the `kicad-ai-auto` directory:

```bash
python run_all_tests.py
```

### Backend Tests Only

```bash
# Using the test runner
cd agent
python run_tests.py

# Or using pytest directly
cd agent
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Frontend Tests Only

```bash
cd web

# Run tests once
npm run test -- --run

# Run tests in watch mode
npm run test

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```

### Playwright E2E Tests

> Note: Playwright tests require the full Docker stack to be running.

```bash
# Start services first
docker-compose up -d

# Run Playwright tests
cd playwright-tests
pytest test_kicad_automation.py -v
```

## Test Categories

### Unit Tests

Test individual functions and classes in isolation.

**Backend:**
- `test_middleware.py` - Custom exception classes, logging setup, middleware behavior
- `test_export_manager.py` - Export logic for various file formats

**Frontend:**
- `kicadStore.test.ts` - State management actions and initial state
- `api.test.ts` - API service methods with mocked axios

### Component Tests

Test React components rendering and interactions.

- `App.test.tsx` - Main application structure and connection status
- `MenuBar.test.tsx` - Menu rendering, dropdown behavior, action handlers

### Hook Tests

Test custom React hooks.

- `useWebSocket.test.ts` - WebSocket connection, message sending

### Integration Tests

Test API endpoints with mocked dependencies.

- `test_api.py` - All REST API endpoints using FastAPI TestClient

### E2E Tests

Test complete user workflows.

- `test_kicad_automation.py` - Full design workflow from schematic to PCB export

## Test Fixtures

### Backend Fixtures (`conftest.py`)

- `mock_kicad_controller` - Mock KiCad controller with all methods
- `mock_state_monitor` - Mock state monitor
- `temp_output_dir` - Temporary directory for output files
- `temp_project_dir` - Temporary directory with test project

### Frontend Mocks (`setup.ts`)

- `localStorage` - Mock browser localStorage
- `WebSocket` - Mock WebSocket class
- `import.meta.env` - Mock environment variables

## Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Backend API | 80% |
| Frontend Components | 75% |
| Utilities | 90% |

## Writing New Tests

### Backend Test Template

```python
import pytest
from unittest.mock import Mock

class TestNewFeature:
    """Tests for new feature"""

    @pytest.fixture
    def fixture_name(self):
        """Description of fixture"""
        return Mock()

    def test_something(self, fixture_name):
        """Test description"""
        # Arrange
        # Act
        # Assert
        assert True
```

### Frontend Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('Component or feature name', () => {
  beforeEach(() => {
    // Setup
  })

  it('should do something', () => {
    // Arrange
    // Act
    // Assert
    expect(true).toBe(true)
  })
})
```

## CI Integration

Tests are configured to run in CI environments:

```yaml
# Example GitLab CI
test:
  script:
    - cd kicad-ai-auto
    - python run_all_tests.py --coverage
  coverage: '/TOTAL\s+\d+\s+\d+\s+(\d+%)/'
```

## Troubleshooting

### Common Issues

1. **Import errors in backend tests**
   - Ensure `sys.path` includes the agent directory
   - Check `conftest.py` path setup

2. **WebSocket mock issues in frontend**
   - Check `setup.ts` mock configuration
   - Ensure cleanup in `afterEach`

3. **Playwright connection refused**
   - Start Docker services: `docker-compose up -d`
   - Check port availability: 6080, 8000, 3000

### Debug Mode

```bash
# Backend with detailed output
pytest tests/ -v -s --tb=long

# Frontend with UI
npm run test:ui
```
