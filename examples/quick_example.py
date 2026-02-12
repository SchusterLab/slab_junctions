"""
Dose Chip Example - Full 5x5mm Chip with 6 Grids

This script generates a complete dose chip matching the current configuration.
Creates a 5×5 mm chip with:
- 2 Dolan junction grids (dose test + geometry sweep)
- 1 Manhattan junction dose test
- 1 Junction array dose test
- 1 Junction array geometry sweep
- 1 Manhattan width sweep

Run: python quick_example.py
View: klayout dose_chip_example.gds
"""

import sys
import os

# Add parent directory and dose_chip to path
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'dose_chip'))

from dose_chip_generator import (
    DoseChipGenerator,
    draw_dolan_junction,
    draw_dolan_junction_array
)

print('='*70)
print('DOSE CHIP GENERATOR')
print('='*70)

# Create chip generator (5x5 mm chip)
generator = DoseChipGenerator(chip_size=(5000, 5000))

# =========================================================================
# POSITIONING GUIDE for 5x5mm chip (5000x5000 um)
# =========================================================================
#
# Chip coordinate system:
#   - Origin (0, 0) is at chip center
#   - X range: -2500 to +2500 um (left to right)
#   - Y range: -2500 to +2500 um (bottom to top)
#
# Grid dimensions:
#   - Each 15×15 grid at 100um spacing = 1500×1500 um for junctions
#   - With labels and margins: ~1700×1700 um total per grid
#   - This is approximately 1/3 of chip size in each dimension (5000/3 ≈ 1667 um)
#
# Layout strategy: 2 columns × 3 rows
#   - Column spacing: 5000/2 = 2500 um between column centers
#   - Row spacing: 5000/3 ≈ 1667 um between row centers
#
# Column positions (2 columns):
#   - Left column:  x = -1250 - 1100 = -2350 um (shifted left by 1100)
#   - Right column: x = +1250 - 1100 = +150 um
#
# Row positions (3 rows):
#   - Top row:     y = +1667 - 650 = +1017 um  (shifted down by 650)
#   - Middle row:  y = 0 - 650 = -650 um
#   - Bottom row:  y = -1667 - 650 = -2317 um
#
# Grid positions (x, y):
#   Top-left:      (-2350, +1017)    Top-right:     (+150, +1017)
#   Middle-left:   (-2350,  -650)    Middle-right:  (+150,  -650)
#   Bottom-left:   (-2350, -2317)    Bottom-right:  (+150, -2317)
#
# =========================================================================

tests = [
    {
        'type': 'dose_test',
        'name': 'Dolan Junction Dose Test',
        'junction_func': draw_dolan_junction,
        'geometry': (0.2, 0.2),  # Fixed width, gap
        'dose_fullcut_range': (400, 3000),
        'dose_undercut_range': (150, 1200),
        'position': (-2350, 1017),  # Top-left (shifted)
        'n_rows': 15,
        'n_cols': 15,
        'spacing': 100
    },
    {
        'type': 'dose_array',
        'name': 'Geometry Sweep',
        'junction_func': draw_dolan_junction,
        'dose_fullcut': 1800,  # Fixed fullcut dose
        'dose_undercut': 400,  # Fixed undercut dose
        'width_range': (0.05, 5.0),
        'gap_range': (0.03, 1.0),
        'position': (150, 1017),  # Top-right (shifted)
        'n_rows': 15,
        'n_cols': 15,
        'spacing': 100
    },
    {
        'type': 'manhattan_dose_test',
        'name': 'Manhattan Dose Test',
        'geometry': (0.18, 0),  # width, gap ignored
        'dose_fullcut_range': (400, 3000),
        'dose_undercut_range': (150, 1200),
        'position': (-2350, -650),  # Middle-left (shifted)
        'n_rows': 15,
        'n_cols': 15,
        'spacing': 100
    },
    {
        'type': 'dose_test',
        'name': 'Junction Array Dose Test',
        'junction_func': draw_dolan_junction_array,
        'geometry': (0.2, 0.2),  # Fixed width, gap
        'dose_fullcut_range': (400, 3000),
        'dose_undercut_range': (150, 1200),
        'position': (150, -650),  # Middle-right (shifted)
        'n_rows': 15,
        'n_cols': 15,
        'spacing': 100
    },
    {
        'type': 'dose_array',
        'name': 'Junction Array Geometry Sweep',
        'junction_func': draw_dolan_junction_array,
        'dose_fullcut': 1800,  # Fixed fullcut dose
        'dose_undercut': 450,  # Fixed undercut dose
        'width_range': (0.05, 5.0),
        'gap_range': (0.03, 1.0),
        'position': (-2350, -2317),  # Bottom-left (shifted)
        'n_rows': 15,
        'n_cols': 15,
        'spacing': 100
    },
    {
        'type': 'manhattan_sweep',
        'name': 'Manhattan Width Sweep',
        'width_range': (0.05, 1.0),
        'position': (150, -2317),  # Bottom-right (shifted)
        'n_junctions': 40,
        'n_cols': 10,
        'spacing': 100,
        'dose_fullcut': 1800,
        'dose_undercut': 450
    }
]

# Generate grids
print('\nGenerating grids...')
for test in tests:
    if test['type'] == 'dose_test':
        generator.add_dose_test(
            test['name'],
            test['junction_func'],
            test['geometry'],
            test['dose_fullcut_range'],
            test['dose_undercut_range'],
            test['position'],
            test['n_rows'],
            test['n_cols'],
            test['spacing']
        )
    elif test['type'] == 'dose_array':
        generator.add_dose_array(
            test['name'],
            test['junction_func'],
            test['dose_fullcut'],
            test['dose_undercut'],
            test['width_range'],
            test['gap_range'],
            test['position'],
            test['n_rows'],
            test['n_cols'],
            test['spacing']
        )
    elif test['type'] == 'manhattan_dose_test':
        generator.add_manhattan_dose_test(
            test['name'],
            test['geometry'],
            test['dose_fullcut_range'],
            test['dose_undercut_range'],
            test['position'],
            test['n_rows'],
            test['n_cols'],
            test['spacing']
        )
    elif test['type'] == 'manhattan_sweep':
        generator.add_manhattan_sweep(
            test['name'],
            test['width_range'],
            test['position'],
            test['n_junctions'],
            test['n_cols'],
            test['spacing'],
            test['dose_fullcut'],
            test['dose_undercut']
        )

# Save
output_file = 'dose_chip_example.gds'
generator.save(output_file)

print('='*70)
print('\nSUCCESS!')
print(f'\nGenerated files:')
print(f'  - {output_file}')
print(f'  - {output_file.replace(".gds", "_dose_table.txt")}')
print(f'\nChip details:')
print(f'  - Size: 5×5 mm (5000×5000 µm)')
print(f'  - Layout: 2 columns × 3 rows')
print(f'  - Total grids: 6 (15×15 junctions each, except Manhattan sweep)')
print(f'\nTo view in KLayout:')
print(f'  klayout {output_file}')
print('='*70)
