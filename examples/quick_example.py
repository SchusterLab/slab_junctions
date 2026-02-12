"""
Quick Example: Generate a small dose chip

This script creates a minimal dose chip that you can open in KLayout
to verify the installation works.
"""

import sys
import os

# Add parent directory and dose_chip to path
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'dose_chip'))

from dose_chip_generator import DoseChipGenerator, draw_dolan_junction

print("=" * 70)
print("QUICK EXAMPLE: Generating a small dose chip")
print("=" * 70)
print()

# Create a small 2x2 mm chip for quick testing
generator = DoseChipGenerator(chip_size=(2000, 2000))

# Add a small dose test (3x3 grid)
print("Adding dose test grid (3x3)...")
generator.add_dose_test(
    name='Test Dose Grid',
    junction_func=draw_dolan_junction,
    geometry=(0.2, 0.2),  # 200nm width, 200nm gap
    dose_fullcut_range=(400, 800),  # Fullcut doses
    dose_undercut_range=(100, 200),  # Undercut doses
    position=(-400, 400),  # Top-left
    n_rows=3,
    n_cols=3,
    spacing=200  # 200 um spacing
)

# Add a small geometry sweep (2x2 grid)
print("Adding geometry sweep grid (2x2)...")
generator.add_dose_array(
    name='Geometry Sweep',
    junction_func=draw_dolan_junction,
    dose_fullcut=1450,  # Fixed fullcut dose
    dose_undercut=350,  # Fixed undercut dose
    width_range=(0.15, 0.25),  # Vary width
    gap_range=(0.15, 0.25),  # Vary gap
    position=(200, 400),  # Top-right
    n_rows=2,
    n_cols=2,
    spacing=200
)

# Save the chip
output_file = 'quick_example.gds'
print(f"\nSaving to {output_file}...")
generator.save(output_file)

print("\n" + "=" * 70)
print("SUCCESS!")
print("=" * 70)
print(f"\nGenerated files:")
print(f"  - {output_file} (GDS layout)")
print(f"  - {output_file.replace('.gds', '_dose_table.txt')} (dose table)")
print(f"\nTo view the GDS file:")
print(f"  1. Install KLayout: https://www.klayout.de/")
print(f"  2. Open: klayout {output_file}")
print(f"\nYou should see:")
print(f"  - Layer 1: Labels and boxes")
print(f"  - Layer 2: Clearing dose text (3000 uC/cm^2)")
print(f"  - Layers 200-202: Fullcut doses for dose test")
print(f"  - Layers 600-602: Undercut doses for dose test")
print(f"  - Layer 20: Fullcut for geometry sweep (1450 uC/cm^2)")
print(f"  - Layer 60: Undercut for geometry sweep (1400 uC/cm^2)")
print("=" * 70)
