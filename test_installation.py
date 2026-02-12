"""
Test script to verify all components work correctly in a fresh environment.
Run this after installing dependencies: pip install -r requirements.txt
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 70)
    print("TESTING IMPORTS")
    print("=" * 70)

    try:
        import phidl
        print("[OK] phidl imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import phidl: {e}")
        return False

    try:
        import numpy as np
        print("[OK] numpy imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import numpy: {e}")
        return False

    try:
        import shapely
        print("[OK] shapely imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import shapely: {e}")
        return False

    try:
        import phidl_bridge
        print("[OK] phidl_bridge imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import phidl_bridge: {e}")
        return False

    try:
        import phidl_native
        print("[OK] phidl_native imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import phidl_native: {e}")
        return False

    try:
        sys.path.insert(0, 'dose_chip')
        import dose_chip_generator
        print("[OK] dose_chip_generator imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import dose_chip_generator: {e}")
        return False

    return True


def test_phidl_bridge():
    """Test basic phidl_bridge functionality."""
    print("\n" + "=" * 70)
    print("TESTING PHIDL_BRIDGE")
    print("=" * 70)

    try:
        from phidl_bridge import Chip, Structure, CPWStraight

        # Create a simple chip and draw a straight CPW
        chip = Chip('test', size=(100, 100), two_layer=False)
        s = Structure(chip, start=(0, 0), direction=0)
        CPWStraight(s, pinw=10, gapw=5, length=50)

        device = chip.device
        print(f"[OK] Created chip with {len(device.polygons)} polygons")

        return True
    except Exception as e:
        print(f"[FAIL] phidl_bridge test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dose_chip_generator():
    """Test dose chip generator functionality."""
    print("\n" + "=" * 70)
    print("TESTING DOSE CHIP GENERATOR")
    print("=" * 70)

    try:
        sys.path.insert(0, 'dose_chip')
        from dose_chip_generator import DoseChipGenerator, draw_dolan_junction

        # Create a small test chip
        generator = DoseChipGenerator(chip_size=(1000, 1000))

        # Add a small dose test
        generator.add_dose_test(
            name='Test Dose Grid',
            junction_func=draw_dolan_junction,
            geometry=(0.2, 0.2),
            dose_fullcut_range=(400, 800),
            dose_undercut_range=(100, 200),
            position=(0, 0),
            n_rows=3,
            n_cols=3,
            spacing=100
        )

        # Save to test file
        test_file = 'test_output.gds'
        generator.save(test_file)

        # Check if files were created
        if os.path.exists(test_file):
            os.remove(test_file)  # Clean up
            print("[OK] GDS file created successfully")
        else:
            print("[FAIL] GDS file not created")
            return False

        dose_table_file = test_file.replace('.gds', '_dose_table.txt')
        if os.path.exists(dose_table_file):
            os.remove(dose_table_file)  # Clean up
            print("[OK] Dose table created successfully")
        else:
            print("[FAIL] Dose table not created")
            return False

        print("[OK] Dose chip generator test passed")
        return True

    except Exception as e:
        print(f"[FAIL] Dose chip generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_junction_functions():
    """Test junction drawing functions."""
    print("\n" + "=" * 70)
    print("TESTING JUNCTION FUNCTIONS")
    print("=" * 70)

    try:
        sys.path.insert(0, 'dose_chip')
        from dose_chip_generator import (
            draw_dolan_junction,
            draw_dolan_junction_array,
            draw_manhattan_junction
        )

        # Test Dolan junction
        pin_dev, gap_dev = draw_dolan_junction(0.2, 0.2, 20, 60)
        print(f"[OK] Dolan junction: PIN={len(pin_dev.polygons)} polys, GAP={len(gap_dev.polygons)} polys")

        # Test junction array
        pin_dev, gap_dev = draw_dolan_junction_array(0.2, 0.2, 20, 60)
        print(f"[OK] Junction array: PIN={len(pin_dev.polygons)} polys, GAP={len(gap_dev.polygons)} polys")

        # Test Manhattan junction
        pin_dev, gap_dev = draw_manhattan_junction(0.18, 20, 60)
        print(f"[OK] Manhattan junction: PIN={len(pin_dev.polygons)} polys, GAP={len(gap_dev.polygons)} polys")

        return True

    except Exception as e:
        print(f"[FAIL] Junction function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SLAB JUNCTIONS - INSTALLATION TEST")
    print("=" * 70)
    print()

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("phidl_bridge", test_phidl_bridge()))
    results.append(("Dose Chip Generator", test_dose_chip_generator()))
    results.append(("Junction Functions", test_junction_functions()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        symbol = "[OK]" if passed else "[FAIL]"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n[OK] ALL TESTS PASSED!")
        print("The slab_junctions package is working correctly.")
        return 0
    else:
        print("\n[FAIL] SOME TESTS FAILED")
        print("Please check the error messages above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
