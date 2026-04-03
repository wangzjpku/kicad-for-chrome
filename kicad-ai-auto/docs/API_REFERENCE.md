# KiCad AI Auto - API Reference

Complete API documentation for the KiCad AI Automation system.

**Base URL**: `http://localhost:8000`

**Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Project Management](#project-management)
3. [AI Design](#ai-design)
4. [Schematic Editor](#schematic-editor)
5. [PCB Editor](#pcb-editor)
6. [Design Rule Check (DRC)](#design-rule-check-drc)
7. [Manufacturing Export](#manufacturing-export)
8. [Spatial Operations](#spatial-operations)
9. [Collaboration](#collaboration)
10. [Ecosystem](#ecosystem)

---

## Authentication

### Register User
```
POST /api/v1/auth/register
```

**Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

### Login
```
POST /api/v1/auth/login
```

**Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer"
}
```

### Refresh Token
```
POST /api/v1/auth/refresh
```

**Headers:** `Authorization: Bearer <refresh_token>`

### Get Current User
```
GET /api/v1/auth/me
```

**Headers:** `Authorization: Bearer <access_token>`

---

## Project Management

### List Projects
```
GET /api/v1/projects
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)

### Create Project
```
POST /api/v1/projects
```

**Body:**
```json
{
  "name": "My Project",
  "description": "Project description",
  "template": "arduino_shield"
}
```

### Get Project
```
GET /api/v1/projects/{project_id}
```

### Update Project
```
PUT /api/v1/projects/{project_id}
```

### Delete Project
```
DELETE /api/v1/projects/{project_id}
```

### Share Project
```
POST /api/v1/projects/{project_id}/share
```

**Body:**
```json
{
  "user_id": "string",
  "role": "editor"
}
```

### Create Share Link
```
POST /api/v1/share-links
```

**Body:**
```json
{
  "project_id": "string",
  "expires_in_hours": 24,
  "max_uses": 10
}
```

---

## AI Design

### Analyze Circuit Requirements
```
POST /api/v1/ai/analyze
```

**Body:**
```json
{
  "description": "设计一个 ESP32 智能控制器，带有温湿度传感器和 WiFi 连接",
  "constraints": {
    "board_size": "50x50mm",
    "layers": 2
  }
}
```

**Response:**
```json
{
  "components": [...],
  "nets": [...],
  "suggestions": [...],
  "questions": [...]
}
```

### Enhance Circuit
```
POST /api/v1/ai/enhance
```

**Body:**
```json
{
  "schematic": {...},
  "requirements": ["add ESD protection", "optimize power"]
}
```

---

## Schematic Editor

### Search Symbols
```
POST /api/v1/symbols/search
```

**Body:**
```json
{
  "query": "resistor",
  "category": "passive",
  "limit": 20
}
```

### Get Symbol Categories
```
GET /api/v1/symbols/categories
```

### Bulk Place Components
```
POST /api/v1/symbols/bulk-place
```

**Body:**
```json
{
  "components": [
    {"name": "R10K", "reference": "R1", "value": "10K"},
    {"name": "C100N", "reference": "C1", "value": "100nF"}
  ],
  "layout": "grid",
  "grid_spacing": 2.54
}
```

---

## PCB Editor

### Fanout Pins
```
POST /api/v1/pcb/fanout
```

**Body:**
```json
{
  "footprint_id": "U1",
  "pads": ["1", "2", "3"],
  "via_size": 0.6,
  "via_drill": 0.3
}
```

### Get Pin Spacing
```
GET /api/v1/pcb/fanout/pin-spacing/{package_type}
```

**Path Parameters:**
- `package_type`: `QFP`, `QFN`, `BGA`, `SOP`, etc.

---

## Design Rule Check (DRC)

### Run Basic DRC
```
POST /drc/check
```

**Body:**
```json
{
  "pcb_data": {...},
  "rules": {
    "min_clearance": 0.15,
    "min_track_width": 0.2,
    "min_via_drill": 0.3
  }
}
```

**Response:**
```json
{
  "passed": false,
  "error_count": 3,
  "warning_count": 5,
  "violations": [
    {
      "code": "CLEARANCE",
      "message": "Clearance violation between GND and VCC",
      "severity": "error",
      "x": 10.5,
      "y": 20.3
    }
  ]
}
```

### Run Advanced DRC
```
POST /drc/advanced
```

**Body:**
```json
{
  "pcb_data": {...},
  "manufacturer": "jlcpcb",
  "tier": "standard"
}
```

### Signal Integrity Analysis
```
POST /drc/si/analyze
```

**Body:**
```json
{
  "pcb_data": {...},
  "nets": ["CLK", "DATA"],
  "frequency_mhz": 100
}
```

**Response:**
```json
{
  "impedance": {
    "CLK": {"value": 52.3, "target": 50, "status": "warning"}
  },
  "crosstalk": [...],
  "loss": [...]
}
```

### EMI Analysis
```
POST /drc/emi/analyze
```

**Body:**
```json
{
  "pcb_data": {...},
  "severity": "medium"
}
```

### EMI Visualization
```
GET /drc/emi/visualization
```

---

## Manufacturing Export

### Export Gerber
```
POST /export/gerber
```

**Body:**
```json
{
  "project_id": "string",
  "layers": ["F.Cu", "B.Cu", "F.SilkS", "F.Mask"],
  "format": "rs274x"
}
```

### Export BOM
```
POST /export/bom
```

**Body:**
```json
{
  "project_id": "string",
  "format": "csv",
  "include_lcsc": true
}
```

### Export ODB++
```
POST /export/odb
```

**Body:**
```json
{
  "project_id": "string",
  "include_3d": true
}
```

### Manufacturing Check
```
POST /export/manufacturing-check
```

**Body:**
```json
{
  "pcb_data": {...},
  "manufacturer": "jlcpcb"
}
```

### Cost Estimate
```
POST /export/cost-estimate
```

**Body:**
```json
{
  "board_size": {"width": 50, "height": 50},
  "layers": 2,
  "quantity": 5,
  "thickness": 1.6,
  "surface_finish": "HASL"
}
```

---

## Spatial Operations

### Query Components in Region
```
POST /api/v1/spatial/components
```

**Body:**
```json
{
  "x1": 0, "y1": 0,
  "x2": 100, "y2": 100
}
```

### Check Collisions
```
GET /api/v1/spatial/collisions
```

**Query Parameters:**
- `tolerance` (float): Collision tolerance in mm

### Clearance Check
```
POST /api/v1/spatial/clearance-check
```

**Body:**
```json
{
  "item1_id": "R1",
  "item2_id": "C1",
  "required_clearance": 0.2
}
```

### Net Adjacency
```
GET /api/v1/spatial/net/{net_name}/adjacency
```

### Batch Spatial Query
```
POST /api/v1/spatial/batch
```

---

## Collaboration

### WebSocket Connection
```
WS /api/v1/collab/{project_id}
```

**Message Types:**
- `cursor_move`: `{"type": "cursor_move", "x": 10, "y": 20}`
- `selection_change`: `{"type": "selection_change", "ids": ["R1", "C1"]}`
- `component_update`: `{"type": "component_update", "id": "R1", "changes": {...}}`

### Get Room Info
```
GET /api/v1/collab/{project_id}/info
```

### Version History

#### Create Snapshot
```
POST /api/v1/projects/{project_id}/snapshot
```

**Body:**
```json
{
  "message": "Before major refactoring"
}
```

#### List Revisions
```
GET /api/v1/projects/{project_id}/revisions
```

#### Compare Revisions
```
GET /api/v1/projects/{project_id}/diff?from={rev1}&to={rev2}
```

#### Rollback
```
POST /api/v1/projects/{project_id}/rollback
```

**Body:**
```json
{
  "revision_id": "string"
}
```

#### Tag Revision
```
POST /api/v1/projects/{project_id}/tag
```

**Body:**
```json
{
  "revision_id": "string",
  "tag": "v1.0"
}
```

---

## Ecosystem

### Marketplace

#### List Templates
```
GET /api/v1/ecosystem/templates
```

**Query Parameters:**
- `category` (string): Filter by category
- `search` (string): Search query
- `sort` (string): `popular`, `recent`, `rating`

#### Submit Template
```
POST /api/v1/ecosystem/templates
```

#### Rate Template
```
POST /api/v1/ecosystem/templates/{id}/rate
```

**Body:**
```json
{
  "rating": 5,
  "review": "Excellent template"
}
```

### Custom DRC

#### List Custom Rules
```
GET /api/v1/ecosystem/drc/rules
```

#### Create Custom Rule
```
POST /api/v1/ecosystem/drc/rules
```

**Body:**
```json
{
  "name": "My Custom Rule",
  "description": "Check minimum clearance",
  "condition": "clearance(item1, item2) >= 0.2",
  "severity": "error"
}
```

#### Run Custom DRC
```
POST /api/v1/ecosystem/drc/run
```

### SDK Generation

#### Generate Python SDK
```
GET /api/v1/ecosystem/sdk/python
```

**Response:** Python source file

#### Generate TypeScript SDK
```
GET /api/v1/ecosystem/sdk/typescript
```

**Response:** TypeScript source file

#### Get OpenAPI Spec
```
GET /api/v1/ecosystem/sdk/openapi
```

### Internationalization

#### Get Translations
```
GET /api/v1/ecosystem/i18n/translations/{language}
```

**Path Parameters:**
- `language`: `en-US`, `zh-CN`, `ja-JP`

#### List Supported Languages
```
GET /api/v1/ecosystem/i18n/languages
```

---

## Cache Management

### Get Cache Stats
```
GET /api/v1/cache/stats
```

**Response:**
```json
{
  "total_keys": 150,
  "memory_usage_mb": 12.5,
  "hit_rate": 0.85,
  "namespaces": {
    "bom": 50,
    "drc": 30,
    "api": 70
  }
}
```

### Get Cached Value
```
GET /api/v1/cache/{namespace}/{key}
```

### Set Cached Value
```
POST /api/v1/cache/set
```

**Body:**
```json
{
  "namespace": "api",
  "key": "projects_list",
  "value": {...},
  "ttl_seconds": 3600
}
```

### Delete Cached Value
```
DELETE /api/v1/cache/{namespace}/{key}
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "board_size",
      "reason": "must be positive"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate name) |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limits

| Endpoint Type | Limit |
|--------------|-------|
| General API | 200 req/min |
| AI Analysis | 20 req/min |
| Export | 10 req/min |
| WebSocket | 1 connection/user |

---

## Versioning

API version is included in the URL path: `/api/v1/...`

Breaking changes will result in a new version (v2, v3, etc.).
