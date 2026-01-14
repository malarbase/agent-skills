# MCP Server Setup

## Building the Server

```bash
# From workspace root
npm install
npm run build --workspace floorplan-mcp-server
```

## Configuration for Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "floorplans": {
      "command": "node",
      "args": ["/absolute/path/to/mermaid-floorplan/floorplan-mcp-server/out/index.js"]
    }
  }
}
```

## Configuration for Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "floorplans": {
      "command": "node",
      "args": ["/absolute/path/to/mermaid-floorplan/floorplan-mcp-server/out/index.js"]
    }
  }
}
```

## Testing the Server

```bash
# Run the server directly
node floorplan-mcp-server/out/index.js

# Or use the make command
make mcp-server
```

## Resources

The MCP server provides documentation via resources:

### floorplan://schema

Returns comprehensive DSL documentation including:
- Syntax reference
- Wall types
- Positioning modes
- Complete examples

**Access**:
```json
{
  "resource": "floorplan://schema"
}
```
