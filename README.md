# Slab Junctions

Tools for designing and fabricating superconducting Josephson junctions using e-beam lithography.

## Overview

This repository provides Python tools for:
- **Dose chip generation**: Create comprehensive test chips with dose and geometry sweeps
- **Junction design**: Multiple junction types (Dolan, Manhattan cross, arrays)
- **phidl integration**: Modern GDS layout generation using the phidl library

## Features

### Dose Chip Generator
- Create 5×5 mm or 7×7 mm dose test chips
- Dose tests: Vary e-beam doses with fixed geometry
- Geometry sweeps: Vary junction dimensions with fixed doses
- Manhattan junction support
- Automatic dose tables for BEAMER e-beam system
- Configurable grid layouts

### Junction Types
- **Dolan junctions**: Standard bridge junctions with undercut
- **Manhattan cross junctions**: Perpendicular crossing leads with paddle undercuts
- **Junction arrays**: Multiple junctions in series
- **Asymmetric junctions**: Different widths on left/right sides

### phidl Bridge
- Compatibility layer between old mask_maker API and modern phidl
- Stateful CPW drawing (CPWStraight, CPWLinearTaper, CPWBend)
- Two-layer support (PIN/GAP for optical/e-beam lithography)

## Installation

### Requirements
- Python 3.8+
- phidl
- numpy
- shapely (for polygon operations)

### Setup
```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Generate a Dose Chip

```python
from dose_chip.dose_chip_generator import DoseChipGenerator, draw_dolan_junction

# Create 5×5 mm chip
generator = DoseChipGenerator(chip_size=(5000, 5000))

# Add dose test grid (vary doses)
generator.add_dose_test(
    name='Dose Test',
    junction_func=draw_dolan_junction,
    geometry=(0.2, 0.2),  # Fixed width, gap
    dose_fullcut_range=(400, 3600),
    dose_undercut_range=(100, 1200),
    position=(-2350, 1017),
    n_rows=15,
    n_cols=15,
    spacing=100
)

# Save GDS and dose table
generator.save('my_chip.gds')
```

### 2. Design Custom Junctions

See `junction_experiments/` for interactive notebooks and examples:
- `test_manhattan_junction.ipynb`: Manhattan cross junction designer
- `examples/asymmetric_junction.py`: Asymmetric junction example
- `templates/template_array.py`: Junction array template

## Repository Structure

```
slab_junctions/
├── README.md
├── requirements.txt
├── .gitignore
├── phidl_bridge.py          # phidl compatibility layer
├── phidl_native.py           # Native phidl components
├── dose_chip/
│   ├── dose_chip_generator.py  # Main dose chip library
│   └── my_chip_config.py       # Example configuration
├── junction_experiments/
│   ├── test_manhattan_junction.ipynb  # Interactive junction designer
│   ├── examples/
│   │   └── asymmetric_junction.py
│   └── templates/
│       └── template_array.py
└── examples/
    └── run_files.ipynb          # Full workflow example
```

## Usage Examples

### Dose Test (Vary Doses)
```python
generator.add_dose_test(
    name='My Dose Test',
    junction_func=draw_dolan_junction,
    geometry=(0.2, 0.2),
    dose_fullcut_range=(500, 2000),
    dose_undercut_range=(100, 600),
    position=(0, 0),
    n_rows=10,
    n_cols=10,
    spacing=100
)
```

### Geometry Sweep (Vary Dimensions)
```python
generator.add_dose_array(
    name='Geometry Sweep',
    junction_func=draw_dolan_junction,
    dose_fullcut=1450,
    dose_undercut=350,
    width_range=(0.1, 0.4),
    gap_range=(0.1, 0.4),
    position=(0, 0),
    n_rows=10,
    n_cols=10,
    spacing=100
)
```

### Manhattan Junction
```python
generator.add_manhattan_dose_test(
    name='Manhattan Test',
    geometry=(0.18, 0),
    dose_fullcut_range=(400, 3600),
    dose_undercut_range=(100, 1200),
    position=(0, 0),
    n_rows=15,
    n_cols=15,
    spacing=100
)
```

## Layer Convention

- **Layer 1**: Optical lithography labels and markers
- **Layer 2**: Clearing dose text (3000 µC/cm²)
- **Layer 20**: E-beam fullcut (PIN layer - junction metal)
- **Layer 60**: E-beam undercut (GAP layer - junction bridge)
- **Layers 200-214**: Dose test fullcut layers (varying doses)
- **Layers 600-614**: Dose test undercut layers (varying doses)

## Fabrication Notes

### E-beam Doses
- Fullcut doses typically range from 400-3600 µC/cm²
- Undercut doses are multiplied by 4× for BEAMER compatibility
- Clearing dose for text labels: 3000 µC/cm²

### Geometry
- Minimum junction width: ~0.05 µm (50 nm)
- Typical undercut border: 0.15-0.3 µm (150-300 nm)
- Grid spacing: 50-500 µm depending on chip size

## Contributing

This is a research tool developed at the Schuster Lab. For questions or contributions, please contact the maintainers.

## License

[Add license information]

## Citation

If you use this code in your research, please cite:
[Add citation information]
