# MCP Server Architecture

## Component Structure

```
floorplan-mcp-server/
├── src/
│   ├── index.ts              # MCP server entry point
│   ├── tools/
│   │   ├── index.ts          # Tool registration
│   │   ├── render.ts         # render_floorplan
│   │   ├── validate.ts       # validate_floorplan
│   │   ├── analyze.ts        # analyze_floorplan
│   │   └── modify.ts         # modify_floorplan
│   ├── resources/
│   │   └── schema.ts         # floorplan://schema resource
│   └── utils/
│       ├── renderer.ts       # 2D SVG/PNG rendering
│       └── renderer3d.ts     # 3D PNG rendering
└── test/                     # Integration tests
```

## Dependencies

- **@modelcontextprotocol/sdk** - MCP server framework
- **floorplan-language** - DSL parser and AST
- **floorplan-3d-core** - 3D scene construction
- **langium** - Parser framework
- **three** - 3D rendering engine
- **puppeteer** - Headless browser for 3D PNG export
- **@resvg/resvg-js** - SVG to PNG conversion

## How Rendering Works

1. **Parse**: DSL → Langium parser → AST
2. **Transform**: AST → JSON model → Scene data
3. **Render**:
   - **PNG**: SVG → resvg → PNG buffer
   - **SVG**: Direct SVG string output
   - **3D-PNG**: Three.js → Puppeteer/WebGL → PNG buffer
4. **Encode**: PNG buffer → base64 for MCP response

## Testing

### Manual Testing

```bash
# Build the server
npm run build --workspace floorplan-mcp-server

# Run tests
npm run --workspace floorplan-mcp-server test

# Start server manually (for debugging)
node floorplan-mcp-server/out/index.js
```

### Integration Testing

```typescript
import { createFloorplansServices } from "floorplan-language";
import { render3DToPng } from "floorplans-mcp-server/utils/renderer3d";

test("renders simple floorplan", async () => {
  const dsl = `floorplan
    floor f1 {
      room Office at (0,0) size (10 x 12)
    }`;

  const result = await render3DToPng(dsl, {
    projection: "isometric",
    width: 800,
    height: 600
  });

  expect(result.png).toBeDefined();
  expect(result.metadata.floorCount).toBe(1);
});
```

### Debugging Tips

1. **Enable verbose logging**: Set `NODE_ENV=development`
2. **Test DSL parsing**: Use `validate_floorplan` first
3. **Check intermediate outputs**: Save SVG before PNG conversion
4. **Inspect AST**: Use `analyze_floorplan` to see parsed structure
5. **Isolate 3D issues**: Test with simple single-room floorplan
