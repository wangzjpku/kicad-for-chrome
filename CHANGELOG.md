# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-02-26

### Security

#### Path Traversal Prevention
- Added comprehensive path validation in `ProjectPath.validate_path()` with URL decoding and traversal pattern detection
- Implemented `_validate_output_path()` in `export_manager.py`, `generate_circuit_files.py`, `kicad_exporter.py`
- Fixed `ALLOWED_OUTPUT_BASE` configuration to use application root directory instead of current working directory
- Added output directory whitelist validation in `kicad_ipc_manager.py`

#### Thread Safety
- Implemented double-checked locking with exception handling in `get_kicad_manager()` singleton
- Added `asyncio.Lock` to `WebSocketManager` for thread-safe connection management
- Implemented `threading.Lock` in `ProjectCache` with LRU eviction mechanism
- Fixed race conditions in `get_chip_checker()` singleton pattern

#### Input Validation
- Added WebSocket message validation (JSON format, type field, command field)
- Implemented `project_id` format validation with regex pattern
- Added file path validation with character whitelist in `validators/__init__.py`
- Implemented CLI path validation with file type and executable permission checks

#### Command Injection Prevention
- Fixed subprocess calls to use list arguments instead of shell=True
- Added character whitelist validation for file paths
- Implemented path traversal checks before CLI execution

#### Sensitive Information Protection
- Fixed error responses to return generic messages instead of exposing internal details
- Implemented log injection prevention using `repr()` for user inputs
- Added sensitive header filtering in middleware

#### Resource Management
- Fixed temporary file cleanup using try/finally blocks
- Implemented operation success tracking for proper resource cleanup
- Added LRU cache to prevent memory leaks in project storage

### Changed
- `main.py`: Enhanced WebSocket handling with message validation and error responses
- `kicad_ipc_routes.py`: Removed user-controlled `output_path` parameter from screenshot endpoint
- `project_routes.py`: Added output directory security validation in `export_bom()`
- `kicad_controller.py`: Updated export methods with path validation

### Fixed
- Variable initialization bug in `export_bom()` function
- WebSocket race condition in `ConnectionManager`
- Memory leak in project cache storage
- Hardcoded paths replaced with environment variable configuration
- Debug print statements replaced with proper logging

## [0.8.7] - 2026-02-26

### Fixed
- AI circuit generation voltage detection and chip identification
- Import issues in V2 generator

## [0.8.6] - 2026-02-25

### Added
- Enhanced PCB footprint design functionality
- AI circuit generation improvements

### Fixed
- PCB coordinate scaling (0.254 → 0.025)
- DIP-8 pin layout alignment
- Electrical connection verification

## [0.8.0] - 2026-02-24

### Added
- Initial MVP release
- Browser-based KiCad access
- AI automation layer with REST APIs and WebSocket
- Multiple operation modes:
  - IPC API Mode (KiCad 9.0+)
  - PyAutoGUI Mode (Legacy)
  - Docker/X11 Mode (Linux)
- Project management CRUD operations
- Real-time control via WebSocket
- File export (Gerber, BOM, STEP, etc.)
- Design Rule Checking (DRC)

### Technical Stack
- Backend: FastAPI (Python 3.11+)
- Frontend: React + TypeScript + Vite
- KiCad Integration: kicad-python (kipy)
- Automation: PyAutoGUI + python-xlib

---

## Security Audit Summary (v0.9.0)

### Files Modified (15 iterations)
| File | Modifications |
|------|---------------|
| main.py | 6 |
| kicad_ipc_manager.py | 5 |
| project_routes.py | 5 |
| kicad_ipc_routes.py | 4 |
| chip_data_checker.py | 3 |
| kicad_controller.py | 3 |
| generate_circuit_files.py | 2 |
| validators/__init__.py | 2 |
| kicad_exporter.py | 2 |
| export_manager.py | 1 |
| middleware.py | 1 |

### Issues Fixed by Category
| Category | Count |
|----------|-------|
| Path Traversal | 8 |
| Thread Safety | 4 |
| Resource Leak | 4 |
| Input Validation | 6 |
| Command Injection | 3 |
| Sensitive Info Leak | 3 |
| Logic Bugs | 5 |
| Configuration | 3 |
| **Total** | **36** |

---

## Upgrade Guide

### From v0.8.x to v0.9.0

1. **Environment Variables**: Ensure the following are configured:
   ```bash
   OUTPUT_DIR=/path/to/output
   KICAD_CLI_PATH=/path/to/kicad-cli
   ```

2. **Output Directory**: The output directory now requires explicit configuration. Files will only be written to the configured `OUTPUT_DIR` or the default `./output` directory.

3. **WebSocket API**: WebSocket messages now require:
   - `type` field (required)
   - `command` field for command-type messages
   - Proper JSON format

4. **Breaking Changes**:
   - Screenshot endpoint no longer accepts user-provided `output_path`
   - Project IDs must match pattern `^[a-zA-Z0-9_-]+$`

---

## Contributors

- Claude Code (Anthropic)
- Development Team

---

## License

See [LICENSE](LICENSE) file for details.
