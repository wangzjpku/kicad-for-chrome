"""
OpenAPI SDK Generator Service

Provides:
- OpenAPI 3.0 specification generation from FastAPI routes
- Python SDK generation
- TypeScript SDK generation
- API documentation export
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---- OpenAPI Spec Builder ----

OPENAPI_TEMPLATE = {
    "openapi": "3.0.3",
    "info": {
        "title": "KiCad AI Auto API",
        "description": "AI-driven PCB design automation API",
        "version": "1.0.0",
        "contact": {
            "name": "KiCad AI Auto",
        },
    },
    "servers": [
        {"url": "http://localhost:8000", "description": "Local development"},
    ],
    "paths": {},
    "components": {
        "schemas": {},
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
        },
    },
}


class SDKGenerator:
    """Generates OpenAPI specs and SDK code."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._spec = json.loads(json.dumps(OPENAPI_TEMPLATE))
        self._spec["servers"][0]["url"] = base_url

    def build_spec_from_routes(self, app) -> Dict[str, Any]:
        """Build OpenAPI spec from FastAPI app routes."""
        # FastAPI already has OpenAPI generation built-in
        if hasattr(app, "openapi"):
            try:
                return app.openapi()
            except Exception as e:
                logger.warning(f"FastAPI OpenAPI generation failed: {e}")

        # Manual spec building as fallback
        return self._spec

    # ---- Python SDK ----

    def generate_python_sdk(self, spec: Dict[str, Any]) -> str:
        """Generate a Python SDK client."""
        endpoints = self._extract_endpoints(spec)
        models = self._extract_models(spec)

        code = '''\
"""
KiCad AI Auto - Python SDK
Auto-generated client for the KiCad AI Auto API.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


class KiCadAIError(Exception):
    """API error response."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class KiCadAIClient:
    """Client for the KiCad AI Auto API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._token = ""

    def set_token(self, token: str):
        """Set JWT bearer token."""
        self._token = token

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Any:
        """Make HTTP request."""
        url = f"{self.base_url}{path}"

        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                url += f"?{query}"

        body = json.dumps(data).encode() if data else None
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                error_json = json.loads(error_body)
                msg = error_json.get("detail", error_body)
            except json.JSONDecodeError:
                msg = error_body
            raise KiCadAIError(e.code, msg)

'''
        # Generate endpoint methods
        for ep in endpoints:
            method_name = self._to_python_method(ep["path"], ep["method"])
            doc = f'"""{ep.get("summary", ep["path"])}."""'
            args = ["self"]
            if "{project_id}" in ep["path"]:
                args.append("project_id: str")
            if ep["method"] in ("POST", "PUT"):
                args.append("data: Dict[str, Any] = None")
            if ep["method"] == "GET":
                args.append("**params")

            args_str = ", ".join(args)
            path = ep["path"]
            if "{project_id}" in path:
                path = path.replace("{project_id}", "' + project_id + '")
                path = f"f\"{ep['path'].replace('{project_id}', '{project_id}')}\""
            else:
                path = f'"{ep["path"]}"'

            code += f"\n    def {method_name}({args_str}):\n"
            code += f"        {doc}\n"
            code += f'        return self._request("{ep["method"]}", {path}'
            if ep["method"] in ("POST", "PUT"):
                code += ", data=data"
            if ep["method"] == "GET":
                code += ", params=params"
            code += ")\n"

        return code

    # ---- TypeScript SDK ----

    def generate_typescript_sdk(self, spec: Dict[str, Any]) -> str:
        """Generate a TypeScript SDK client."""
        endpoints = self._extract_endpoints(spec)

        code = '''\
/**
 * KiCad AI Auto - TypeScript SDK
 * Auto-generated client for the KiCad AI Auto API.
 */

interface RequestOptions {
  method: string;
  path: string;
  data?: unknown;
  params?: Record<string, string | number | undefined>;
}

export class KiCadAIError extends Error {
  statusCode: number;
  constructor(statusCode: number, message: string) {
    super(`HTTP ${statusCode}: ${message}`);
    this.statusCode = statusCode;
  }
}

export class KiCadAIClient {
  private baseUrl: string;
  private apiKey: string;
  private token: string;

  constructor(baseUrl = 'http://localhost:8000', apiKey = '') {
    this.baseUrl = baseUrl.replace(/\\/+$/, '');
    this.apiKey = apiKey;
    this.token = '';
  }

  setToken(token: string): void {
    this.token = token;
  }

  private async request<T>(options: RequestOptions): Promise<T> {
    let url = `${this.baseUrl}${options.path}`;

    if (options.params) {
      const qs = Object.entries(options.params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => `${k}=${v}`)
        .join('&');
      if (qs) url += `?${qs}`;
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    if (this.apiKey) headers['X-API-Key'] = this.apiKey;

    const resp = await fetch(url, {
      method: options.method,
      headers,
      body: options.data ? JSON.stringify(options.data) : undefined,
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new KiCadAIError(resp.status, text);
    }
    return resp.json();
  }

'''
        # Generate endpoint methods
        for ep in endpoints:
            method_name = self._to_ts_method(ep["path"], ep["method"])
            doc = f"   * {ep.get('summary', ep['path'])}"
            args = []
            if "{project_id}" in ep["path"]:
                args.append("projectId: string")
            if ep["method"] in ("POST", "PUT"):
                args.append("data?: Record<string, unknown>")
            if ep["method"] == "GET":
                args.append("params?: Record<string, string | number | undefined>")

            args_str = ", ".join(args)
            path = ep["path"]
            if "{project_id}" in path:
                path_expr = f"`{path.replace('{project_id}', '${projectId}')}`"
            else:
                path_expr = f"'{path}'"

            ret_type = "Promise<unknown>"

            code += f"  /**\n{doc}\n   */\n"
            code += f"  async {method_name}({args_str}): {ret_type} {{\n"
            code += f"    return this.request({{ method: '{ep['method']}', path: {path_expr}"
            if ep["method"] in ("POST", "PUT"):
                code += ", data"
            if ep["method"] == "GET":
                code += ", params"
            code += " });\n  }\n\n"

        code += "}\n"
        return code

    # ---- Helpers ----

    def _extract_endpoints(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        endpoints = []
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "operation_id": details.get("operationId", ""),
                    })
        return endpoints

    def _extract_models(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": name, "schema": schema}
            for name, schema in spec.get("components", {}).get("schemas", {}).items()
        ]

    @staticmethod
    def _to_python_method(path: str, method: str) -> str:
        name = path.replace("/api/", "").replace("/api/v1/", "")
        name = re.sub(r"[/{]", "_", name).replace("}", "").replace("-", "_")
        prefix = method.lower()
        return f"{prefix}_{name}".rstrip("_")

    @staticmethod
    def _to_ts_method(path: str, method: str) -> str:
        name = path.replace("/api/", "").replace("/api/v1/", "")
        name = re.sub(r"[/{]", "_", name).replace("}", "").replace("-", "_")
        prefix = method.lower()
        parts = prefix.split("_") + name.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:] if p)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_sdk_generator: Optional[SDKGenerator] = None


def get_sdk_generator() -> SDKGenerator:
    global _sdk_generator
    if _sdk_generator is None:
        _sdk_generator = SDKGenerator()
    return _sdk_generator
