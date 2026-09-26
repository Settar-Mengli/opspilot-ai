/**
 * OpenAPI-lite types — regenerate with:
 *   uv run python scripts/export_openapi.py
 *   npx openapi-typescript frontend/openapi.json -o frontend/src/api/generated.ts
 *
 * Checked into git; CI fails if this file drifts from the live schema.
 */
export type paths = {
  '/api/v1/health': {
    get: {
      responses: {
        200: { content: { 'text/plain': string } }
      }
    }
  }
  '/api/v1/runs': {
    get: {
      responses: {
        200: { content: { 'application/json': unknown[] } }
      }
    }
    post: {
      requestBody: {
        content: {
          'application/json': { input_file?: string; date: string }
        }
      }
      responses: {
        200: {
          content: {
            'application/json': {
              status: string
              stdout: string
              run_id: string
            }
          }
        }
      }
    }
  }
  '/api/v1/triage': {
    get: {
      responses: {
        200: { content: { 'application/json': unknown[] } }
      }
    }
  }
  '/api/v1/settings': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': {
              provider: string
              model: string
              api_key_set: boolean
              api_key_preview: string | null
            }
          }
        }
      }
    }
  }
}

export type components = Record<string, never>
