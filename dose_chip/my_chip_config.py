"""
Generate a comprehensive dose chip with three 15x15 grids
"""
import sys
import os

# Add multimode to path
sys.path.insert(0, os.path.join(os.path.dirname(os.getcwd()), 'multimode'))

from dose_chip_generator import DoseChipGenerator, draw_dolan_junction

print('='*70)
print('GENERATING COMPREHENSIVE DOSE CHIP')
print('='*70)

# Create generator
generator = DoseChipGenerator(chip_size=(7000, 7000))

# Chip boundary: -3500 to +3500 in both X and Y
# Grid dimensions: 15x15 at 50µm = 700µm, with labels ~800µm total
# Position on left edge with margin

# Grid 1: Dose Test (15x15) - Vary doses, fixed geometry
print('\n1. DOSE TEST GRID (15x15)')
generator.add_dose_test(
    name='Dose Test',
    junction_func=draw_dolan_junction,
    geometry=(0.2, 0.2),  # Fixed width, gap
    dose_fullcut_range=(500, 2000),
    dose_undercut_range=(200, 800),
    position=(-3400, 2600),  # Top - left aligned
    n_rows=15,
    n_cols=15,
    spacing=50
)

# Grid 2: Dose Array (15x15) - Vary width/gap, fixed doses
print('\n2. DOSE ARRAY GRID (15x15)')
generator.add_dose_array(
    name='Dose Array',
    junction_func=draw_dolan_junction,
    dose_fullcut=1450,  # Fixed fullcut dose for PIN layer (layer 20)
    dose_undercut=350,  # Fixed undercut dose for GAP layer (layer 60)
    width_range=(0.1, 0.4),
    gap_range=(0.1, 0.4),
    position=(-3400, 1300),  # Middle - left aligned
    n_rows=15,
    n_cols=15,
    spacing=50
)

# Grid 3: Undercut Test (15x15) - Vary width/undercut, fixed dose & gap
print('\n3. UNDERCUT TEST GRID (15x15)')
generator.add_undercut_test(
    name='Undercut Test',
    width_range=(0.1, 0.4),
    uc_range=(0.2, 0.5),
    gap=0.2,  # Fixed gap
    position=(-3400, 0),  # Bottom - left aligned
    n_rows=15,
    n_cols=15,
    spacing=50
)

# Save
output_file = 'comprehensive_dose_chip.gds'
generator.save(output_file)

print(f"\n>> Generated: {output_file}")
print(f"   Chip size: {generator.chip.xsize:.1f} x {generator.chip.ysize:.1f} um")
print(f"   Total dose table entries: {len(generator.dose_table)}")
print(f"\n>> Dose table: comprehensive_dose_chip_dose_table.txt")
print(f">> Open with: klayout {output_file}")
print('='*70)
