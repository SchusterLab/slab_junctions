# phidl_bridge User Guide

Complete guide to using the phidl_bridge compatibility layer for CPW (Coplanar Waveguide) layout design.

## Table of Contents
1. [Overview](#overview)
2. [Basic Concepts](#basic-concepts)
3. [Common Functions](#common-functions)
4. [Examples](#examples)
5. [Layer Management](#layer-management)

---

## Overview

`phidl_bridge` provides a stateful API for drawing CPW structures, bridging the old mask_maker interface with modern phidl. It maintains position and direction tracking while drawing, making it easy to create complex geometries.

### Key Features
- **Stateful drawing**: Tracks current position and direction
- **Two-layer support**: Automatic PIN/GAP layer management
- **CPW primitives**: Straight, taper, and bend segments
- **Port-based**: Compatible with phidl Device workflow

---

## Basic Concepts

### 1. Chip and Structure

Every layout starts with a **Chip** (container) and **Structure** (drawing context):

```python
from phidl_bridge import Chip, Structure

# Create a chip (container for geometry)
chip = Chip('my_chip', size=(1000, 1000), two_layer=False)

# Create a structure (drawing context with position/direction)
s = Structure(chip, start=(0, 0), direction=0)
```

**Parameters:**
- `start`: Starting position (x, y) in microns
- `direction`: Angle in degrees (0=right, 90=up, 180=left, 270=down)

### 2. CPW Geometry Convention

CPW (Coplanar Waveguide) has a center conductor and side gaps:

```
    |<-- gapw -->|<-- pinw -->|<-- gapw -->|
    +------------+------------+------------+
    |   GAP      | CONDUCTOR  |   GAP      |
    +------------+------------+------------+
```

**Two drawing modes:**

#### Standard CPW (pinw > 0):
```python
CPWStraight(s, pinw=10, gapw=5, length=100)
```
Draws: 10µm conductor + 5µm gaps on each side = 20µm total width

#### Solid Rectangle (pinw = 0):
```python
CPWStraight(s, pinw=0, gapw=5, length=100)
```
Draws: Solid 10µm wide rectangle (gapw × 2)

---

## Common Functions

### 1. CPWStraight
Draw a straight CPW segment.

```python
from phidl_bridge import CPWStraight

CPWStraight(
    structure,     # Structure object
    pinw=10,       # Center conductor width (µm), 0 for solid
    gapw=5,        # Gap width on each side (µm)
    length=100     # Segment length (µm)
)
```

**Examples:**
```python
# Standard CPW: 10µm conductor, 5µm gaps
CPWStraight(s, pinw=10, gapw=5, length=100)

# Solid rectangle: 10µm wide (2 × 5µm)
CPWStraight(s, pinw=0, gapw=5, length=100)

# Narrow line: 0.2µm wide
CPWStraight(s, pinw=0, gapw=0.1, length=50)
```

### 2. CPWLinearTaper
Taper between different widths.

```python
from phidl_bridge import CPWLinearTaper

CPWLinearTaper(
    structure,
    length=50,          # Taper length (µm)
    start_pinw=20,      # Starting conductor width
    stop_pinw=10,       # Ending conductor width
    start_gapw=0,       # Starting gap width
    stop_gapw=5         # Ending gap width
)
```

**Examples:**
```python
# Taper from wide bar to thin CPW
CPWLinearTaper(s, length=50,
               start_pinw=0, stop_pinw=10,
               start_gapw=10, stop_gapw=5)

# Taper from wide to narrow solid rectangle
CPWLinearTaper(s, length=30,
               start_pinw=0, stop_pinw=0,
               start_gapw=2.5, stop_gapw=0.1)
```

### 3. CPWBend / curve_corner
Draw curved bends (90° or custom angles).

```python
from phidl_bridge import CPWBend

CPWBend(
    structure,
    angle=90,        # Bend angle in degrees (+ = CCW, - = CW)
    pinw=10,         # Conductor width
    gapw=5,          # Gap width
    radius=50,       # Bend radius (µm)
    segments=10      # Number of segments (smoothness)
)
```

**Examples:**
```python
# 90° left turn
CPWBend(s, angle=90, pinw=10, gapw=5, radius=50)

# 90° right turn
CPWBend(s, angle=-90, pinw=10, gapw=5, radius=50)

# 45° bend
CPWBend(s, angle=45, pinw=10, gapw=5, radius=30)

# Smooth curve (more segments)
CPWBend(s, angle=90, pinw=10, gapw=5, radius=50, segments=20)
```

---

## Examples

### Example 1: Simple Straight Line

```python
from phidl_bridge import Chip, Structure, CPWStraight

# Setup
chip = Chip('example1', size=(200, 200), two_layer=False)
s = Structure(chip, start=(0, 0), direction=0)

# Draw 100µm horizontal line
CPWStraight(s, pinw=10, gapw=5, length=100)

# Get result
device = chip.device
device.write_gds('example1.gds')
```

### Example 2: L-Shape with Bend

```python
from phidl_bridge import Chip, Structure, CPWStraight, CPWBend

chip = Chip('example2', size=(300, 300), two_layer=False)
s = Structure(chip, start=(0, 0), direction=0)

# Horizontal segment
CPWStraight(s, pinw=10, gapw=5, length=100)

# 90° turn
CPWBend(s, angle=90, pinw=10, gapw=5, radius=50)

# Vertical segment
CPWStraight(s, pinw=10, gapw=5, length=100)

device = chip.device
device.write_gds('example2.gds')
```

### Example 3: Tapered Junction

```python
from phidl_bridge import Chip, Structure, CPWStraight, CPWLinearTaper

chip = Chip('junction', size=(50, 50), two_layer=True)
s = Structure(chip, start=(0, 0), direction=0)

# Wide bar
CPWStraight(s, pinw=0, gapw=2.5, length=10)

# Taper down
CPWLinearTaper(s, length=5,
               start_pinw=0, stop_pinw=0,
               start_gapw=2.5, stop_gapw=0.1)

# Narrow section (junction)
CPWStraight(s, pinw=0, gapw=0.1, length=2)

# Gap (skip over junction)
s.last = (s.last[0] + 0.2, s.last[1])

# Narrow section
CPWStraight(s, pinw=0, gapw=0.1, length=2)

# Taper up
CPWLinearTaper(s, length=5,
               start_pinw=0, stop_pinw=0,
               start_gapw=0.1, stop_gapw=2.5)

# Wide bar
CPWStraight(s, pinw=0, gapw=2.5, length=10)

device = chip.device
device.write_gds('junction.gds')
```

### Example 4: Manhattan Grid

```python
from phidl_bridge import Chip, Structure, CPWStraight, CPWBend

chip = Chip('grid', size=(500, 500), two_layer=False)

# Draw a 3×3 grid of horizontal lines
for i in range(3):
    y_pos = i * 100
    s = Structure(chip, start=(0, y_pos), direction=0)

    for j in range(2):
        CPWStraight(s, pinw=10, gapw=5, length=80)
        if j < 1:  # Not last segment
            s.last = (s.last[0] + 20, s.last[1])  # Gap

device = chip.device
device.write_gds('grid.gds')
```

---

## Layer Management

### Single Layer Mode

For simple layouts (optical lithography):

```python
chip = Chip('optical', size=(1000, 1000), two_layer=False)
```

All geometry goes on the default PIN layer.

### Two-Layer Mode

For e-beam lithography with undercut:

```python
import phidl_bridge
from phidl_bridge import Chip, Structure, CPWStraight

# Save original layers
orig_pin = phidl_bridge.LAYER_PIN
orig_gap = phidl_bridge.LAYER_GAP

# Set custom layers
phidl_bridge.LAYER_PIN = 20  # Fullcut layer
phidl_bridge.LAYER_GAP = 60  # Undercut layer

chip = Chip('ebeam', size=(100, 100), two_layer=True)
s = Structure(chip, start=(0, 0), direction=0)

# Draw with both layers
CPWStraight(s, pinw=0.2, gapw=0.15, length=10)

# Restore layers
phidl_bridge.LAYER_PIN = orig_pin
phidl_bridge.LAYER_GAP = orig_gap
```

**Layer convention:**
- **PIN layer**: Metal features (conductor + gaps in standard CPW)
- **GAP layer**: Undercut borders (for suspended bridges)

### Drawing on Specific Layer

To draw only on GAP layer (e.g., for paddles):

```python
# Switch to GAP layer
phidl_bridge.LAYER_PIN = phidl_bridge.LAYER_GAP

# Draw paddles (will appear on GAP layer)
CPWStraight(s, pinw=0, gapw=0.5, length=1.5)

# Restore to PIN layer
phidl_bridge.LAYER_PIN = orig_pin
```

---

## Advanced: Position and Direction

### Manual Position Control

```python
# Get current position
current_pos = s.last  # Returns (x, y) tuple

# Set new position (teleport)
s.last = (100, 50)

# Relative movement
s.last = (s.last[0] + 10, s.last[1] + 5)
```

### Direction Control

```python
# Get current direction
current_dir = s.last_direction  # Returns angle in degrees

# Change direction
s.last_direction = 90  # Now pointing up

# Draw in new direction
CPWStraight(s, pinw=10, gapw=5, length=50)
```

---

## Tips and Best Practices

### 1. Use pinw=0 for Solid Shapes
```python
# Good: Solid rectangle
CPWStraight(s, pinw=0, gapw=5, length=100)

# Bad: Don't use large pinw for solid shapes
# CPWStraight(s, pinw=100, gapw=0, length=100)  # Wrong!
```

### 2. Layer Switching Pattern
```python
# Always save and restore layers
orig = phidl_bridge.LAYER_PIN
try:
    phidl_bridge.LAYER_PIN = custom_layer
    # Draw stuff
finally:
    phidl_bridge.LAYER_PIN = orig
```

### 3. Check Position After Complex Paths
```python
CPWStraight(s, pinw=10, gapw=5, length=100)
CPWBend(s, angle=90, pinw=10, gapw=5, radius=50)
print(f"Current position: {s.last}")
print(f"Current direction: {s.last_direction}°")
```

### 4. Combine Multiple Structures
```python
# Draw on same chip with different starting points
chip = Chip('multi', size=(1000, 1000), two_layer=False)

s1 = Structure(chip, start=(0, 0), direction=0)
CPWStraight(s1, pinw=10, gapw=5, length=100)

s2 = Structure(chip, start=(0, 200), direction=0)
CPWStraight(s2, pinw=10, gapw=5, length=100)

device = chip.device  # Contains both structures
```

---

## Common Patterns

### Junction with Tapers
```python
def draw_simple_junction(chip, width, gap):
    s = Structure(chip, start=(0, 0), direction=0)

    # Left bar
    CPWStraight(s, pinw=0, gapw=2.5, length=5)

    # Taper down
    CPWLinearTaper(s, length=2,
                   start_pinw=0, stop_pinw=0,
                   start_gapw=2.5, stop_gapw=width/2)

    # Thin section
    CPWStraight(s, pinw=0, gapw=width/2, length=1)

    # Gap
    s.last = (s.last[0] + gap, s.last[1])

    # Thin section
    CPWStraight(s, pinw=0, gapw=width/2, length=1)

    # Taper up
    CPWLinearTaper(s, length=2,
                   start_pinw=0, stop_pinw=0,
                   start_gapw=width/2, stop_gapw=2.5)

    # Right bar
    CPWStraight(s, pinw=0, gapw=2.5, length=5)
```

### Meander (Serpentine)
```python
def draw_meander(chip, n_turns=5):
    s = Structure(chip, start=(0, 0), direction=0)

    for i in range(n_turns):
        CPWStraight(s, pinw=10, gapw=5, length=100)
        CPWBend(s, angle=90, pinw=10, gapw=5, radius=30)
        CPWStraight(s, pinw=10, gapw=5, length=50)
        CPWBend(s, angle=90, pinw=10, gapw=5, radius=30)
```

---

## Troubleshooting

### Problem: Geometry not appearing
**Solution:** Make sure you're getting the device and writing GDS:
```python
device = chip.device
device.write_gds('output.gds')
```

### Problem: Gaps in geometry
**Solution:** Check if you're manually updating `s.last` and forgetting to draw:
```python
# Wrong:
s.last = (100, 0)  # Position changed but nothing drawn

# Right:
CPWStraight(s, pinw=10, gapw=5, length=100)  # Draws AND updates position
```

### Problem: Layer confusion
**Solution:** Use two separate Chip objects for PIN and GAP:
```python
pin_chip = Chip('pin', size=(100, 100), two_layer=False)
gap_chip = Chip('gap', size=(100, 100), two_layer=False)
```

---

## See Also

- `phidl_native.py` - Native phidl Device-based components
- `dose_chip_generator.py` - Complete dose chip examples
- `junction_experiments/` - Interactive junction design notebooks
