---
name: mcp-integration
description: How to use the Floorplan MCP server for AI-powered floorplan manipulation.
  Use when working with MCP tools, AI integrations, or programmatic floorplan modifications.
metadata:
  tags:
  - mcp
  - ai
  - integration
  - project-specific
  author: malar
  repo: github.com/malar/mermaid-floorplan
---

# MCP Server Integration

The **floorplan-mcp-server** provides AI assistants with tools to render, validate, analyze, and modify floorplan DSL code.

## Available Tools

### render_floorplan

Parse and render floorplan DSL to visual formats.

**Formats**: `png`, `svg`, `3d-png`

```json
{
  "dsl": "floorplan\n  floor f1 {\n    room Office at (0,0) size (10 x 12)\n  }",
  "format": "png",
  "width": 800,
  "height": 600
}
```

**Parameters**:
- `floorIndex` - Which floor to render (0-based)
- `renderAllFloors` - Render all floors in one image
- `multiFloorLayout` - "stacked" or "sideBySide" (for 2D)
- `projection` - "isometric" or "perspective" (for 3D)
- `cameraPosition` - {x, y, z} for 3D perspective
- `cameraTarget` - {x, y, z} look-at point
- `fov` - Field of view in degrees (10-120)

### validate_floorplan

Fast syntax validation without rendering.

```json
{
  "dsl": "floorplan\n  floor f1 {\n    room Office at (0,0) size (10 x 12)\n  }"
}
```

**Output**: `{ "valid": true, "errors": [] }`

### analyze_floorplan

Extract structured information: floor count, room inventory, total area, connections.

```json
{
  "dsl": "floorplan\n  floor f1 {\n    room Office at (0,0) size (10 x 12)\n  }"
}
```

### modify_floorplan

Programmatically modify floorplan DSL.

**Actions**: `add_room`, `remove_room`, `resize_room`, `move_room`, `rename_room`, `update_walls`, `add_label`, `convert_to_relative`

```json
{
  "dsl": "...",
  "operations": [
    { "action": "add_room", "params": { "name": "Kitchen", ... } }
  ]
}
```

## Common Workflows

### Design Iteration

```
validate_floorplan → check syntax
modify_floorplan → add_room operations
render_floorplan → visualize result
analyze_floorplan → get metrics
```

### Multi-Format Export

```
render_floorplan → format: "png"   (quick preview)
render_floorplan → format: "svg"   (web/print)
render_floorplan → format: "3d-png", projection: "isometric"
render_floorplan → format: "3d-png", projection: "perspective"
```

### Batch Validation (CI/CD)

```
For each .floorplan file:
1. validate_floorplan → check syntax
2. analyze_floorplan → extract metrics
3. render_floorplan → generate preview
```

## Best Practices

**Do**:
- Always validate before rendering or modifying
- Use relative positions when possible (more maintainable)
- Batch operations in single modify_floorplan call
- Start with 2D for iteration, then 3D for presentation

**Don't**:
- Skip validation - it catches errors early
- Make sequential modify calls - batch them
- Render at 4K unless necessary - slower
- Assume room names - use analyze to list them

## Quick Reference

| Tool | Use | Speed |
|------|-----|-------|
| `validate_floorplan` | Syntax checking | ⚡ Fast |
| `analyze_floorplan` | Extract data | ⚡ Fast |
| `render_floorplan` (png/svg) | 2D visualization | 🔄 Medium |
| `render_floorplan` (3d-png) | 3D visualization | 🐌 Slow |
| `modify_floorplan` | Code modification | 🔄 Medium |

## Reference Documentation

- **[Setup & Configuration](references/setup.md)** - Installation, MCP config for Cursor/Claude Desktop
- **[Examples](references/examples.md)** - Full code examples for all operations
- **[Architecture](references/architecture.md)** - Component structure, dependencies, rendering pipeline
- **[Troubleshooting](references/troubleshooting.md)** - Common issues and performance tips
