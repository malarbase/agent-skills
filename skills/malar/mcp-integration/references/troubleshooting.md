# MCP Server Troubleshooting

## Server Not Connecting

**Symptoms**: MCP server not available in AI assistant

**Solution**:
1. Check server is built: `npm run build --workspace floorplan-mcp-server`
2. Verify path in config is absolute
3. Check Node.js version >= 20.10.0
4. Restart the AI assistant application

## 3D Rendering Fails

**Symptoms**: Error when using `format: "3d-png"`

**Causes**:
- Puppeteer not installed
- Chromium not downloaded

**Solution**:
```bash
npm run --workspace floorplan-mcp-server clean
npm install
npm run build --workspace floorplan-mcp-server
```

## Validation Returns Errors

**Symptoms**: `validate_floorplan` reports syntax errors

**Solution**:
1. Check DSL syntax matches grammar
2. Verify room names are unique
3. Ensure all rooms have required properties
4. Review wall types are valid: solid, door, window, open
5. Use `floorplan://schema` resource for reference

## Modify Operations Not Applied

**Symptoms**: `modify_floorplan` returns unchanged DSL

**Causes**:
- Room name doesn't exist (for modify/remove)
- Invalid relative position reference
- Conflicting operations

**Solution**:
1. Use `analyze_floorplan` to list all room names
2. Verify reference rooms exist
3. Apply operations one at a time to isolate issues

## Large Images Take Long to Generate

**Symptoms**: `render_floorplan` times out or is slow

**Solution**:
1. Reduce image dimensions: `width: 800, height: 600`
2. Render individual floors instead of all: `renderAllFloors: false`
3. Use PNG instead of 3D: `format: "png"`
4. For 3D, use isometric instead of perspective

## Performance Tips

| Tip | Rationale |
|-----|-----------|
| Validate before rendering | `validate_floorplan` is much faster |
| Cache analysis results | `analyze_floorplan` is computationally cheap |
| Batch modifications | Combine operations in one `modify_floorplan` call |
| Use appropriate resolutions | Preview: 800x600, Web: 1200x900, Print: 2400x1800 |
| Prefer 2D for iterations | 3D rendering is slower due to WebGL setup |
