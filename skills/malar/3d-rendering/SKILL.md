---
name: 3d-rendering
description: How to generate 3D visualizations from floorplan DSL files. Use when working with 3D exports, isometric views, or perspective rendering.
metadata:
  author: malar
  repo: github.com/malar/mermaid-floorplan
  tags: [3d, rendering, visualization, project-specific]
---

# 3D Rendering

## Overview

The project includes a powerful 3D rendering system built on Three.js that can generate:
- Isometric 3D views
- Perspective 3D views with custom camera positioning
- Multi-floor stacked visualizations
- High-resolution PNG exports

## Quick Commands

### Using Makefile

```bash
# Generate 3D isometric view
make export-3d

# Generate 3D perspective view
make export-3d-perspective

# Custom camera position
make export-3d-perspective CAMERA_POS=50,30,50 CAMERA_TARGET=0,0,0

# Custom resolution
make export-3d WIDTH_3D=1920 HEIGHT_3D=1080

# All images (includes 3D)
make export-images
```

### Using Script Directly

```bash
# Basic 3D export (isometric)
npx tsx scripts/generate-3d-images.ts trial/TriplexVilla.floorplan trial --all

# Perspective mode
npx tsx scripts/generate-3d-images.ts trial/TriplexVilla.floorplan trial --all \
  --projection perspective

# Custom camera and resolution
npx tsx scripts/generate-3d-images.ts trial/TriplexVilla.floorplan trial --all \
  --projection perspective \
  --camera-pos 50,30,50 \
  --camera-target 0,0,0 \
  --fov 60 \
  --width 1920 \
  --height 1080
```

## Projection Modes

### Isometric Projection (Default)

- **Best for**: Technical diagrams, architectural overviews
- **Characteristics**: Parallel lines remain parallel, no depth distortion
- **Use case**: When you need accurate spatial relationships
- **Default settings**: Camera positioned at 45° angle

```bash
make export-3d
# or
npx tsx scripts/generate-3d-images.ts input.floorplan output --all --projection isometric
```

### Perspective Projection

- **Best for**: Realistic visualizations, presentations
- **Characteristics**: Objects farther away appear smaller (like human vision)
- **Use case**: Marketing materials, client presentations
- **Customizable**: Camera position, target, field of view

```bash
make export-3d-perspective
# or
npx tsx scripts/generate-3d-images.ts input.floorplan output --all --projection perspective
```

## Camera Configuration

### Camera Position (`--camera-pos X,Y,Z`)

Controls where the camera is located in 3D space.

**Coordinate System**:
- X: Left (-) to Right (+)
- Y: Down (-) to Up (+)
- Z: Back (-) to Front (+)

**Common Positions**:
```bash
# High overhead view
--camera-pos 0,100,50

# Side elevation view
--camera-pos 80,30,0

# Corner perspective (default for perspective)
--camera-pos 50,30,50

# Low angle (dramatic)
--camera-pos 40,10,40
```

### Camera Target (`--camera-target X,Y,Z`)

Controls what point the camera is looking at.

**Defaults**:
- Usually set to building center: `0,0,0`

**Examples**:
```bash
# Focus on specific room (adjust based on your floor plan)
--camera-target 10,0,10

# Look at upper floors
--camera-target 0,15,0

# Offset view
--camera-target 5,5,5
```

### Field of View (`--fov DEGREES`)

Controls the camera's viewing angle (only for perspective mode).

**Values**:
- **30-40°**: Telephoto effect (less distortion, flatter)
- **50°**: Default (natural looking)
- **60-75°**: Wide angle (more dramatic, slight distortion)
- **>75°**: Fish-eye effect (significant distortion)

```bash
# Natural view
--fov 50

# Dramatic wide angle
--fov 70

# Flatter telephoto
--fov 35
```

## Output Configuration

### Resolution (`--width N --height N`)

Control output image dimensions in pixels.

**Presets**:
```bash
# HD (default)
--width 1200 --height 900

# Full HD
--width 1920 --height 1080

# 4K
--width 3840 --height 2160

# Square (social media)
--width 1080 --height 1080

# Portrait
--width 1080 --height 1920
```

### Scale Factor (`--scale N`)

Affects annotation text size and detail level.

- **10-12**: Small annotations
- **15**: Default (balanced)
- **20-25**: Larger, more readable annotations
- **>30**: Very large (for high-DPI displays)

## Makefile Variables

The Makefile provides convenient shortcuts for 3D rendering:

```bash
# Basic variables
FLOORPLAN_FILE=trial/TriplexVilla.floorplan  # Input file
OUTPUT_DIR=trial                              # Output directory
PROJECTION=isometric                          # isometric or perspective

# Camera settings
CAMERA_POS=50,30,50                          # X,Y,Z position
CAMERA_TARGET=0,0,0                          # X,Y,Z look-at point
FOV=50                                       # Field of view (degrees)

# Output settings
WIDTH_3D=1200                                # Width in pixels
HEIGHT_3D=900                                # Height in pixels
```

**Example usage**:
```bash
# High-res perspective render
make export-3d-perspective \
  FLOORPLAN_FILE=trial/MyHouse.floorplan \
  WIDTH_3D=3840 \
  HEIGHT_3D=2160 \
  CAMERA_POS=60,40,60 \
  FOV=55
```

## Common Use Cases

### 1. Standard Isometric Export

**Goal**: Technical documentation

```bash
make export-3d FLOORPLAN_FILE=trial/TriplexVilla.floorplan
```

Output: `trial/TriplexVilla-3d-isometric.png`

### 2. Marketing Render

**Goal**: Eye-catching perspective view

```bash
make export-3d-perspective \
  FLOORPLAN_FILE=trial/TriplexVilla.floorplan \
  CAMERA_POS=70,35,70 \
  FOV=65 \
  WIDTH_3D=1920 \
  HEIGHT_3D=1080
```

### 3. Multiple Views

**Goal**: Show building from different angles

```bash
# Front view
npx tsx scripts/generate-3d-images.ts input.floorplan output/front \
  --all --projection perspective --camera-pos 0,25,80

# Back view
npx tsx scripts/generate-3d-images.ts input.floorplan output/back \
  --all --projection perspective --camera-pos 0,25,-80

# Side view
npx tsx scripts/generate-3d-images.ts input.floorplan output/side \
  --all --projection perspective --camera-pos 80,25,0
```

### 4. Animation Frames

**Goal**: Create frames for a rotating animation

```bash
# Create frames at 30° intervals
for angle in 0 30 60 90 120 150 180 210 240 270 300 330; do
  rad=$(echo "scale=4; $angle * 3.14159 / 180" | bc)
  x=$(echo "scale=2; 50 * c($rad)" | bc -l)
  z=$(echo "scale=2; 50 * s($rad)" | bc -l)
  npx tsx scripts/generate-3d-images.ts input.floorplan output/frame_$angle \
    --all --projection perspective --camera-pos $x,30,$z
done
```

## Integration with Other Tools

### Combined Export (2D + 3D)

Generate all visualizations at once:

```bash
make export-images  # Creates SVG, PNG, and 3D views
```

This generates:
- `[name]-floor-[N].svg` - Vector 2D floor plans
- `[name]-floor-[N].png` - Raster 2D floor plans
- `[name]-3d-isometric.png` - Isometric 3D view
- `[name]-3d-perspective.png` - Perspective 3D view

### MCP Server Integration

The 3D renderer is also available via the MCP server:

```typescript
// From AI tool context
{
  "tool": "render_floorplan",
  "render3d": true,
  "projection": "perspective",
  "cameraPosition": [50, 30, 50]
}
```

## Technical Details

### Architecture

```
scripts/generate-3d-images.ts
  ↓ imports
floorplan-mcp-server/utils/renderer3d.ts
  ↓ uses
floorplan-3d-core/
  ├── scene-builder.ts    # Constructs 3D scene
  ├── camera.ts           # Camera setup
  └── materials.ts        # Materials and lighting
```

### Dependencies

- **Three.js**: 3D rendering engine
- **Puppeteer**: Headless browser for PNG export
- **floorplan-language**: DSL parsing
- **floorplan-3d-core**: 3D scene construction

### Output Files

**Naming Convention**:
- Isometric: `{basename}-3d-isometric.png`
- Perspective: `{basename}-3d-perspective.png`

**Location**: Same directory as input file or specified `OUTPUT_DIR`

## Troubleshooting

### Issue: Blank or Black Image

**Causes**:
- Camera too far from scene
- Camera inside a wall
- Incorrect camera target

**Solution**:
```bash
# Reset to defaults
make export-3d FLOORPLAN_FILE=yourfile.floorplan

# Try standard perspective
make export-3d-perspective CAMERA_POS=50,30,50 CAMERA_TARGET=0,0,0
```

### Issue: Image Too Dark

**Causes**:
- Default lighting may be insufficient for some scenes

**Solution**:
- Adjust camera angle for better light exposure
- Scene lighting is built into the 3D core renderer

### Issue: Distorted View

**Causes**:
- FOV too high
- Camera too close

**Solution**:
```bash
# Use moderate FOV
--fov 50

# Move camera farther back
--camera-pos 70,35,70
```

### Issue: Building Appears Cut Off

**Causes**:
- Camera too close
- Resolution aspect ratio doesn't match scene

**Solution**:
```bash
# Increase camera distance
CAMERA_POS=80,40,80

# Try 16:9 aspect ratio
WIDTH_3D=1920 HEIGHT_3D=1080
```

### Issue: Puppeteer/Browser Errors

**Causes**:
- Missing Chrome/Chromium installation
- Puppeteer dependencies not installed

**Solution**:
```bash
# Reinstall mcp-server dependencies
npm run --workspace floorplan-mcp-server clean
npm install
npm run build
```

## Quick Reference

| Task | Command |
|------|---------|
| Isometric 3D | `make export-3d` |
| Perspective 3D | `make export-3d-perspective` |
| Custom camera | `make export-3d-perspective CAMERA_POS=X,Y,Z` |
| High resolution | `make export-3d WIDTH_3D=3840 HEIGHT_3D=2160` |
| Wide FOV | `make export-3d-perspective FOV=70` |
| All images | `make export-images` |
| Custom file | `make export-3d FLOORPLAN_FILE=path/to/file.floorplan` |

## Best Practices

1. **Start with defaults**: Use `make export-3d` first to see the basic output
2. **Iterate on perspective**: Adjust camera position incrementally
3. **Test multiple angles**: Try 4-8 different camera positions for best view
4. **Use appropriate resolution**: Match your intended output medium
5. **Keep FOV reasonable**: 45-65° for most architectural visualizations
6. **Document custom settings**: Save successful camera configurations for reuse

