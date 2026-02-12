"""
Junction Array Template

Template for creating junctions with multiple gaps in series.
Useful for high-impedance devices or multi-junction SQUIDs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'multimode'))

from typing import Tuple
from phidl import Device
from phidl_bridge import Chip, Structure, CPWStraight, CPWLinearTaper
import phidl_bridge


def draw_my_junction_array(width: float, gap: float,
                           layer_pin: int, layer_gap: int,
                           right_width: float = 2.0,
                           num_juncs: int = 10) -> Tuple[Device, Device]:
    """
    Draw junction array with multiple junctions in series.

    Structure: Bar | Taper | Thin | Gap | [Thin | Gap]×N | Thin | Taper | Bar

    Args:
        width: Thin section width (um)
        gap: Junction gap (um)
        layer_pin: PIN layer number (fullcut)
        layer_gap: GAP layer number (undercut)
        right_width: Right thin section width (um), default 2.0
        num_juncs: Number of junctions in series

    Returns:
        (pin_device, gap_device): Tuple of phidl Devices
    """
    # Save original layer settings
    orig_pin = phidl_bridge.LAYER_PIN
    orig_gap = phidl_bridge.LAYER_GAP

    # Geometry parameters
    bar_w = 5.0      # Bar width
    taper_l = 2.0    # Taper length
    thin_l = 0.8     # Thin section length
    uc = 0.3         # Undercut border width

    try:
        phidl_bridge.LAYER_PIN = layer_pin
        phidl_bridge.LAYER_GAP = layer_gap

        pin_chip = Chip('pin_temp', size=(50, 20), two_layer=False)
        gap_chip = Chip('gap_temp', size=(50, 20), two_layer=False)

        # =====================================================================
        # PIN LAYER - Draw fullcut geometry (junction electrodes)
        # Structure: Bar | Taper | Thin | Gap | [Thin | Gap]×N | Thin | Taper | Bar
        # =====================================================================
        s = Structure(pin_chip, start=(0, 0), direction=0)

        # Left contact pad
        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)

        # Taper down from bar to junction width
        CPWLinearTaper(s, length=taper_l,
                      start_pinw=bar_w, stop_pinw=width,
                      start_gapw=0, stop_gapw=0)

        # First electrode (thin section before first gap)
        CPWStraight(s, pinw=0, gapw=width/2, length=thin_l)

        # Skip first gap (Josephson junction #1)
        s.last = (s.last[0] + gap, s.last[1])

        # Middle electrodes and gaps (junctions #2 through #num_juncs)
        for i in range(num_juncs - 1):
            # Middle electrode
            CPWStraight(s, pinw=0, gapw=width/2, length=thin_l)
            # Skip gap (Josephson junction)
            s.last = (s.last[0] + gap, s.last[1])

        # Last electrode (thin section after last gap)
        CPWStraight(s, pinw=0, gapw=right_width/2, length=thin_l)

        # Taper up from junction width to bar
        CPWLinearTaper(s, length=taper_l,
                      start_pinw=right_width, stop_pinw=bar_w,
                      start_gapw=0, stop_gapw=0)

        # Right contact pad
        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)

        # =====================================================================
        # GAP LAYER - Draw undercut borders
        # =====================================================================
        phidl_bridge.LAYER_PIN = layer_gap
        s2 = Structure(gap_chip, start=(0, 0), direction=0)

        # Left edge border
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Left bar borders
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Left taper borders
        CPWLinearTaper(s2, length=taper_l,
                      start_pinw=bar_w, stop_pinw=width,
                      start_gapw=uc/2, stop_gapw=uc/2)

        # First thin section borders
        CPWStraight(s2, pinw=width, gapw=uc/2, length=thin_l)

        # First gap region border
        max_width = max(width, right_width)
        CPWStraight(s2, pinw=0, gapw=(max_width + uc)/2, length=gap)

        # Middle thin sections and gaps
        for i in range(num_juncs - 1):
            # Thin section borders (match PIN layer: length=thin_l)
            CPWStraight(s2, pinw=width, gapw=uc/2, length=thin_l)
            # Gap region border
            CPWStraight(s2, pinw=0, gapw=(max_width + uc)/2, length=gap)

        # Last thin section borders
        CPWStraight(s2, pinw=right_width, gapw=uc/2, length=thin_l)

        # Right taper borders
        CPWLinearTaper(s2, length=taper_l,
                      start_pinw=right_width, stop_pinw=bar_w,
                      start_gapw=uc/2, stop_gapw=uc/2)

        # Right bar borders
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Right edge border
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Extract and center devices
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

    print("Testing junction array...")

    # Test with different array sizes
    for n in [1, 3, 10]:
        print(f"\n--- Array with {n} junctions ---")
        pin_dev, gap_dev = draw_my_junction_array(
            width=0.2, gap=0.2,
            layer_pin=20, layer_gap=60,
            right_width=2.0,
            num_juncs=n
        )

        print(f"Total length: {pin_dev.xsize:.2f} um")
        print(f"PIN polygons: {len(pin_dev.polygons)}")
        print(f"GAP polygons: {len(gap_dev.polygons)}")

        # Visualize
        combined = Device(f'array_{n}')
        combined << pin_dev
        combined << gap_dev
        qp(combined)

        # Save
        combined.write_gds(f'test_array_{n}.gds')
