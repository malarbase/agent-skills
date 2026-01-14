# MCP Integration Examples

## Table of Contents
- [Add Room with Absolute Position](#add-room-with-absolute-position)
- [Add Room with Relative Position](#add-room-with-relative-position)
- [3D Perspective Rendering](#3d-perspective-rendering)
- [Multi-Floor Side-by-Side](#multi-floor-side-by-side)
- [Converting to Relative Positioning](#converting-to-relative-positioning)
- [Integration Patterns](#integration-patterns)

## Add Room with Absolute Position

```json
{
  "dsl": "floorplan\n  floor f1 {\n    room Office at (0,0) size (10 x 12)\n  }",
  "operations": [
    {
      "action": "add_room",
      "params": {
        "name": "Kitchen",
        "position": { "x": 12, "y": 0 },
        "size": { "width": 10, "height": 12 },
        "walls": {
          "top": "solid",
          "right": "window",
          "bottom": "solid",
          "left": "door"
        },
        "label": "main kitchen"
      }
    }
  ]
}
```

## Add Room with Relative Position

```json
{
  "dsl": "floorplan\n  floor f1 {\n    room Office at (0,0) size (10 x 12)\n  }",
  "operations": [
    {
      "action": "add_room",
      "params": {
        "name": "Kitchen",
        "size": { "width": 10, "height": 12 },
        "walls": {
          "top": "solid",
          "right": "window",
          "bottom": "solid",
          "left": "door"
        },
        "relativePosition": {
          "direction": "right-of",
          "reference": "Office",
          "gap": 2,
          "alignment": "top"
        }
      }
    }
  ]
}
```

## 3D Perspective Rendering

```json
{
  "dsl": "floorplan\n  floor Ground {\n    room Living at (0,0) size (14 x 12)\n  }\n  floor First {\n    room Bedroom at (0,0) size (12 x 10)\n  }",
  "format": "3d-png",
  "projection": "perspective",
  "cameraPosition": { "x": 30, "y": 20, "z": 30 },
  "cameraTarget": { "x": 5, "y": 5, "z": 5 },
  "fov": 60,
  "renderAllFloors": true,
  "width": 1920,
  "height": 1080
}
```

## Multi-Floor Side-by-Side

```json
{
  "dsl": "floorplan\n  floor Ground {...}\n  floor First {...}",
  "format": "png",
  "renderAllFloors": true,
  "multiFloorLayout": "sideBySide",
  "width": 1600,
  "height": 800
}
```

## Converting to Relative Positioning

```json
{
  "dsl": "floorplan\n  floor f1 {\n    room Living at (0,0) size (14 x 12)\n    room Kitchen at (14,0) size (10 x 12)\n    room Dining at (0,12) size (10 x 8)\n  }",
  "operations": [
    {
      "action": "convert_to_relative",
      "params": {
        "anchorRoom": "Living",
        "alignmentTolerance": 1
      }
    }
  ]
}
```

**Result**:
```
room Living at (0,0) size (14 x 12)
room Kitchen size (10 x 12) right-of Living align top
room Dining size (10 x 8) below Living align left
```

## Integration Patterns

### Validation Before Modification

```javascript
const validation = await validate_floorplan({ dsl });
if (!validation.valid) {
  console.error("Invalid DSL:", validation.errors);
  return;
}

const modified = await modify_floorplan({
  dsl,
  operations: [...]
});
```

### Render After Modification

```javascript
const result = await modify_floorplan({
  dsl,
  operations: [{ action: "add_room", params: {...} }]
});

const image = await render_floorplan({
  dsl: result.modifiedDsl,
  format: "png"
});
```

### Multi-Format Export Pipeline

```javascript
const validation = await validate_floorplan({ dsl });
if (!validation.valid) return;

const [png, svg, iso3d, persp3d] = await Promise.all([
  render_floorplan({ dsl, format: "png" }),
  render_floorplan({ dsl, format: "svg" }),
  render_floorplan({ dsl, format: "3d-png", projection: "isometric" }),
  render_floorplan({ dsl, format: "3d-png", projection: "perspective" })
]);
```

### Analyze-Then-Optimize

```javascript
const analysis = await analyze_floorplan({ dsl });

if (analysis.totalArea < 500) {
  // Add more rooms
} else if (analysis.roomCount > 20) {
  // Consider sub-rooms
}
```
