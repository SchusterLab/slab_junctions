"""
Example: Asymmetric Dolan Junction

This junction has different widths on the left and right sides.
Useful for flux-tunable devices or directional coupling.

Left side: narrow (0.2 um typical)
Right side: wide (2.0 um typical)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'multimode'))

from typing import Tuple
from phidl import Device
from phidl_bridge import Chip, Structure, CPWStraight, CPWLinearTaper
import phidl_bridge


def draw_asymmetric_junction(width: float, gap: float,
                             layer_pin: int, layer_gap: int,
                             left_width: float = 0.2,
                             right_width: float = 2.0) -> Tuple[Device, Device]:
    """
    Draw an asymmetric Dolan junction with different left/right widths.

    Args:
        width: Not used (kept for compatibility)
        gap: Junction gap (um)
        layer_pin: PIN layer number (fullcut)
        layer_gap: GAP layer number (undercut)
        left_width: Left electrode width (um), default 0.2
        right_width: Right electrode width (um), default 2.0

    Returns:
        (pin_device, gap_device): Tuple of phidl Devices
    """
    orig_pin = phidl_bridge.LAYER_PIN
    orig_gap = phidl_bridge.LAYER_GAP

    # Geometry
    bar_w = 5.0
    taper_l = 2.0
    thin_l = 0.8
    uc = 0.3

    try:
        phidl_bridge.LAYER_PIN = layer_pin
        phidl_bridge.LAYER_GAP = layer_gap

        pin_chip = Chip('pin_temp', size=(20, 20), two_layer=False)
        gap_chip = Chip('gap_temp', size=(20, 20), two_layer=False)

        # PIN LAYER
        s = Structure(pin_chip, start=(0, 0), direction=0)

        # Left side (narrow)
        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)
        CPWLinearTaper(s, length=taper_l,
                      start_pinw=bar_w, stop_pinw=left_width,
                      start_gapw=0, stop_gapw=0)
        CPWStraight(s, pinw=0, gapw=left_width/2, length=thin_l)

        # Gap
        s.last = (s.last[0] + gap, s.last[1])

        # Right side (wide)
        CPWStraight(s, pinw=0, gapw=right_width/2, length=thin_l)
        CPWLinearTaper(s, length=taper_l,
                      start_pinw=right_width, stop_pinw=bar_w,
                      start_gapw=0, stop_gapw=0)
        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)

        # GAP LAYER
        phidl_bridge.LAYER_PIN = layer_gap
        s2 = Structure(gap_chip, start=(0, 0), direction=0)

        # Left edge
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Left bar
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Left taper
        CPWLinearTaper(s2, length=taper_l,
                      start_pinw=bar_w, stop_pinw=left_width,
                      start_gapw=uc/2, stop_gapw=uc/2)

        # Left electrode
        CPWStraight(s2, pinw=left_width, gapw=uc/2, length=thin_l)

        # Gap region (use max width for Dolan bridge)
        max_width = max(left_width, right_width)
        CPWStraight(s2, pinw=0, gapw=(max_width + uc)/2, length=gap)

        # Right electrode
        CPWStraight(s2, pinw=right_width, gapw=uc/2, length=thin_l)

        # Right taper
        CPWLinearTaper(s2, length=taper_l,
                      start_pinw=right_width, stop_pinw=bar_w,
                      start_gapw=uc/2, stop_gapw=uc/2)

        # Right bar
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Right edge
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Center and return
        pin_dev = pin_chip.device
        gap_dev = gap_chip.device
        pin_dev.move(origin=pin_dev.center, destination=(0, 0))
        gap_dev.move(origin=gap_dev.center, destination=(0, 0))

        return pin_dev, gap_dev

    finally:
        phidl_bridge.LAYER_PIN = orig_pin
        phidl_bridge.LAYER_GAP = orig_gap


if __name__ == '__main__':
    from phidl import quickplot as qp

    print("Testing asymmetric junction...")

    # Test different asymmetry ratios
    test_cases = [
        (0.2, 0.2, "Symmetric"),      # ratio = 1:1
        (0.2, 1.0, "Moderate"),       # ratio = 1:5
        (0.2, 2.0, "High"),           # ratio = 1:10
    ]

    for left, right, name in test_cases:
        print(f"\n--- {name} asymmetry: {left} um / {right} um ---")

        pin_dev, gap_dev = draw_asymmetric_junction(
            width=0.2,  # Not used
            gap=0.2,
            layer_pin=20,
            layer_gap=60,
            left_width=left,
            right_width=right
        )

        combined = Device(f'asymmetric_{name}')
        combined << pin_dev
        combined << gap_dev

        print(f"Total length: {combined.xsize:.2f} um")
        print(f"Left width: {left} um, Right width: {right} um")
        print(f"Asymmetry ratio: 1:{right/left:.1f}")

        qp(combined)
        combined.write_gds(f'asymmetric_{name}.gds')
