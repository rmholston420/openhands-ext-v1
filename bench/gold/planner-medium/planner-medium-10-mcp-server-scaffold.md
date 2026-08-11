# planner-medium-10-mcp-server-scaffold

## Task summary
Plan the creation of a new MCP (Model Context Protocol) server exposing three tools: `search_notes(query: str)`, `create_note(title: str, body: str)`, and `get_note(id: str)`, backed by a SQLite database, following OpenHands-Ext's MCP conventions (ADR-0019).

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Author mcp-servers/notes/server.py using the MCP SDK: define the MCP server object, name it 'notes', bind to an unused port in the MCP port range (per ADR-0019).", "deps": []},
    {"id": "s2", "desc": "Define the SQLite schema (notes table with id UUID PK, title, body, created_at) and initialize the database file at server startup if not present.", "deps": []},
    {"id": "s3", "desc": "Implement the three MCP tool handlers: search_notes returns matching titles/ids via LIKE query, create_note inserts and returns the new id, get_note returns full row by id or None.", "deps": ["s1", "s2"]},
    {"id": "s4", "desc": "Register the tools with proper input/output schemas so MCP clients can discover them; include description strings for each parameter.", "deps": ["s3"]},
    {"id": "s5", "desc": "Add the server to the OpenHands-Ext MCP registry configuration so it's launched under the mode wrapper (per ADR-0019).", "deps": ["s4"]},
    {"id": "s6", "desc": "Add pytest coverage: happy-path for each tool, invalid inputs (empty query, invalid id) return appropriate MCP errors, database persistence across server restarts.", "deps": ["s5"]}
  ]
}
```

## Scoring rubric (0-100)

| Card | Criteria |
|---|---|
| 90-100 | 5-7 steps: MCP server scaffold with port-range compliance → schema + init → tool handlers → tool schemas → registry integration → tests. References ADR-0019 conventions. |
| 70-89 | Server + tools present but tool schemas missing (MCP clients can't introspect) OR registry integration missing (server won't be launched). |
| 40-69 | Server + tools present but doesn't respect the MCP port range from ADR-0019 (hardcodes a port). |
| 10-39 | Tool handlers described but no SQLite schema OR no registry integration. |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's ability to use project-specific conventions (ADR-0019 MCP port range + mode wrapper). Key discriminator: does the plan surface the ADR-0019 constraints explicitly, or does it produce a generic MCP-server plan that ignores project context?
