"""
Native phidl implementation for superconducting qubit design.

This module provides Device-based CPW (coplanar waveguide) components
without the stateful compatibility layer.

Phase 3 & 4: Gradual migration from phidl_bridge to pure phidl.
"""

from phidl import Device, Path
import phidl.geometry as pg
import numpy as np
from typing import Tuple, Optional

# GDS Layer definitions
LAYER_PIN = (1, 0)  # Metal conductor layer (optical lithography)
LAYER_GAP = (2, 0)  # Undercut/ground layer (e-beam lithography)


def create_cpw_straight(length: float, pinw: float, gapw: float,
                       layer: int = LAYER_PIN[0]) -> Device:
    """
    Create a straight CPW segment as a Device.

    Args:
        length: Segment length in µm
        pinw: Pin (center conductor) width in µm
        gapw: Gap width on each side in µm
        layer: GDS layer number

    Returns:
        Device with CPW straight segment, ports 'input' and 'output'
    """
    D = Device('cpw_straight')

    if pinw == 0:
        # Solid bar mode (single rectangle)
        total_width = 2 * gapw
        rect = pg.rectangle(size=(length, total_width), layer=layer)
        D << rect
    else:
        # Standard CPW mode (center conductor + gaps)
        total_width = pinw + 2 * gapw

        # Create the full CPW cross-section
        outer_rect = pg.rectangle(size=(length, total_width), layer=layer)

        # For PIN layer: solid conductor
        # For GAP layer: would need to subtract center (future enhancement)
        D << outer_rect

    # Add ports for connectivity
    D.add_port(name='input', midpoint=(0, 0), width=pinw if pinw > 0 else 2*gapw,
               orientation=180)
    D.add_port(name='output', midpoint=(length, 0), width=pinw if pinw > 0 else 2*gapw,
               orientation=0)

    return D


def create_cpw_taper(length: float, width_start: float, width_end: float,
                    layer: int = LAYER_PIN[0]) -> Device:
    """
    Create a linear taper segment as a Device.

    Args:
        length: Taper length in µm
        width_start: Starting width in µm
        width_end: Ending width in µm
        layer: GDS layer number

    Returns:
        Device with taper geometry, ports 'input' and 'output'
    """
    D = Device('cpw_taper')

    # Create taper polygon
    points = [
        (0, -width_start/2),
        (length, -width_end/2),
        (length, width_end/2),
        (0, width_start/2)
    ]

    D.add_polygon(points, layer=layer)

    # Add ports
    D.add_port(name='input', midpoint=(0, 0), width=width_start, orientation=180)
    D.add_port(name='output', midpoint=(length, 0), width=width_end, orientation=0)

    return D


def create_cpw_bend(angle: float, radius: float, width: float,
                   layer: int = LAYER_PIN[0]) -> Device:
    """
    Create a curved CPW bend as a Device.

    Args:
        angle: Bend angle in degrees (positive = CCW, negative = CW)
        radius: Bend radius in µm
        width: CPW width in µm
        layer: GDS layer number

    Returns:
        Device with bend geometry, ports 'input' and 'output'
    """
    D = Device('cpw_bend')

    # Use phidl Path for smooth curves
    P = Path()
    P.append(pg.arc(radius=radius, angle=angle, num_pts=32))

    # Extrude the path to create the CPW
    cpw = P.extrude(width=width, layer=layer)
    D << cpw

    # Add ports
    D.add_port(name='input', midpoint=(0, 0), width=width, orientation=180)

    # Calculate output position and orientation
    angle_rad = np.deg2rad(angle)
    if angle > 0:  # CCW
        end_x = radius * np.sin(angle_rad)
        end_y = radius * (1 - np.cos(angle_rad))
    else:  # CW
        end_x = radius * np.sin(angle_rad)
        end_y = radius * (1 - np.cos(angle_rad))

    D.add_port(name='output', midpoint=(end_x, end_y), width=width,
               orientation=angle)

    return D


def create_two_layer_device(pin_device: Device, gap_expansion: float = 0) -> Tuple[Device, Device]:
    """
    Create two-layer version (PIN and GAP) from a single-layer Device.

    Args:
        pin_device: Device on PIN layer
        gap_expansion: How much to expand for GAP layer (µm)

    Returns:
        Tuple of (pin_device, gap_device)
    """
    gap_device = Device('gap_layer')

    # Copy PIN geometry to GAP layer with optional expansion
    pin_polys = pin_device.get_polygons(by_spec=False)

    for poly in pin_polys:
        # For now, just copy the polygon to GAP layer
        # Future: implement proper boolean expansion
        gap_device.add_polygon(poly, layer=LAYER_GAP)

    return pin_device, gap_device


def create_junction_dolan(bar_width: float, bar_length1: float, bar_length2: float,
                         taper_length: float, jj_width: float, jj_gap: float,
                         jj_length: float, layer_pin: int = 20, layer_gap: int = 60) -> Tuple[Device, Device]:
    """
    Create Dolan bridge junction geometry for e-beam lithography.

    Properly centered at origin for accurate placement.

    Args:
        bar_width: Width of junction bars (µm)
        bar_length1: Left bar length (µm)
        bar_length2: Right bar length (µm)
        taper_length: Taper section length (µm)
        jj_width: Junction width (µm)
        jj_gap: Junction gap (µm)
        jj_length: Junction length (µm)
        layer_pin: PIN layer number (default: 20)
        layer_gap: GAP layer number (default: 60)

    Returns:
        Tuple of (pin_device, gap_device) with junction geometry
    """
    # Calculate total length and center at origin
    total_length = bar_length1 + 2*taper_length + 2*jj_length + jj_gap + bar_length2
    x_offset = -total_length / 2

    # Create PIN device
    pin_dev = Device('junction_pin')

    x = x_offset
    # Left bar
    rect = pg.rectangle(size=(bar_length1, bar_width), layer=layer_pin)
    ref = pin_dev << rect
    ref.move(destination=(x, -bar_width/2))
    x += bar_length1

    # Left taper
    taper = pg.taper(length=taper_length, width1=bar_width, width2=jj_width, layer=layer_pin)
    ref = pin_dev << taper
    ref.move(destination=(x, 0))
    x += taper_length

    # Left thin section
    rect = pg.rectangle(size=(jj_length, jj_width), layer=layer_pin)
    ref = pin_dev << rect
    ref.move(destination=(x, -jj_width/2))
    x += jj_length

    # Gap (no drawing)
    x += jj_gap

    # Right thin section
    rect = pg.rectangle(size=(jj_length, jj_width), layer=layer_pin)
    ref = pin_dev << rect
    ref.move(destination=(x, -jj_width/2))
    x += jj_length

    # Right taper
    taper = pg.taper(length=taper_length, width1=jj_width, width2=bar_width, layer=layer_pin)
    ref = pin_dev << taper
    ref.move(destination=(x, 0))
    x += taper_length

    # Right bar
    rect = pg.rectangle(size=(bar_length2, bar_width), layer=layer_pin)
    ref = pin_dev << rect
    ref.move(destination=(x, -bar_width/2))

    # Create GAP device (undercut) - only around junction area, not thick bars
    gap_dev = Device('junction_gap')
    undercut_width = bar_width + 0.4

    # Undercut should only cover: tapers + thin sections + gap
    # NOT the thick bars on either end
    undercut_length = 2*taper_length + 2*jj_length + jj_gap
    undercut_x_offset = -undercut_length / 2

    undercut_rect = pg.rectangle(size=(undercut_length, undercut_width), layer=layer_gap)
    ref = gap_dev << undercut_rect
    ref.move(destination=(undercut_x_offset, -undercut_width/2))

    return pin_dev, gap_dev


def create_short_junction(bar_width: float, total_length: float,
                         layer_pin: int = 20, layer_gap: int = 60) -> Tuple[Device, Device]:
    """
    Create a short junction (solid metal bar connecting both sides).

    Properly centered at origin for accurate placement.

    Args:
        bar_width: Width of the bar (µm)
        total_length: Total horizontal length (µm)
        layer_pin: PIN layer number (default: 20)
        layer_gap: GAP layer number (default: 60)

    Returns:
        Tuple of (pin_device, gap_device) with short junction geometry
    """
    pin_dev = Device('short_pin')

    # Solid bar centered at origin
    rect = pg.rectangle(size=(total_length, bar_width), layer=layer_pin)
    ref = pin_dev << rect
    ref.move(destination=(-total_length/2, -bar_width/2))

    # GAP device
    gap_dev = Device('short_gap')
    undercut_width = bar_width + 0.4
    undercut_rect = pg.rectangle(size=(total_length, undercut_width), layer=layer_gap)
    ref = gap_dev << undercut_rect
    ref.move(destination=(-total_length/2, -undercut_width/2))

    return pin_dev, gap_dev


def create_open_junction(bar_width: float, total_length: float,
                        layer_pin: int = 20, layer_gap: int = 60) -> Tuple[Device, Device]:
    """
    Create an open junction (complete gap, no metal connection).

    Properly centered at origin for accurate placement.

    Args:
        bar_width: Width of the gap area (µm)
        total_length: Total horizontal length of open region (µm)
        layer_pin: PIN layer number (default: 20)
        layer_gap: GAP layer number (default: 60)

    Returns:
        Tuple of (pin_device, gap_device) with open junction geometry
    """
    pin_dev = Device('open_pin')  # Empty

    # GAP only
    gap_dev = Device('open_gap')
    undercut_width = bar_width
    undercut_rect = pg.rectangle(size=(total_length - 0.4, undercut_width), layer=layer_gap)
    ref = gap_dev << undercut_rect
    ref.move(destination=(-(total_length - 0.4)/2, -undercut_width/2))

    return pin_dev, gap_dev


class NativeCPWRouter:
    """
    Helper class for routing CPW paths using native phidl Devices.

    Provides a cleaner API for building complex CPW structures without
    the stateful compatibility layer.
    """

    def __init__(self, layer: int = LAYER_PIN[0]):
        """
        Initialize router.

        Args:
            layer: GDS layer for drawing
        """
        self.layer = layer
        self.components = []
        self.current_port = None

    def add_straight(self, length: float, width: float) -> 'NativeCPWRouter':
        """Add a straight segment."""
        segment = create_cpw_straight(length, pinw=0, gapw=width/2, layer=self.layer)
        self.components.append(segment)
        return self

    def add_bend(self, angle: float, radius: float, width: float) -> 'NativeCPWRouter':
        """Add a curved bend."""
        bend = create_cpw_bend(angle, radius, width, layer=self.layer)
        self.components.append(bend)
        return self

    def build(self, name: str = 'cpw_route') -> Device:
        """Build the complete routed CPW as a single Device."""
        D = Device(name)

        # Connect components in sequence
        current_pos = (0, 0)
        current_angle = 0

        for comp in self.components:
            ref = D << comp
            ref.move(destination=current_pos)
            ref.rotate(current_angle, center=current_pos)

            # Update position for next component
            if 'output' in comp.ports:
                out_port = ref.ports['output']
                current_pos = out_port.midpoint
                current_angle = out_port.orientation

        return D


# Convenience functions matching old API but returning Devices

def CPWStraight_native(length: float, pinw: float, gapw: float) -> Device:
    """Native version of CPWStraight - returns Device instead of modifying state."""
    return create_cpw_straight(length, pinw, gapw)


def CPWLinearTaper_native(length: float, start_pinw: float, end_pinw: float,
                          start_gapw: float, end_gapw: float) -> Device:
    """Native version of CPWLinearTaper - returns Device instead of modifying state."""
    start_width = start_pinw + 2 * start_gapw
    end_width = end_pinw + 2 * end_gapw
    return create_cpw_taper(length, start_width, end_width)


def CPWBend_native(angle: float, radius: float, pinw: float, gapw: float) -> Device:
    """Native version of CPWBend - returns Device instead of modifying state."""
    width = pinw + 2 * gapw
    return create_cpw_bend(angle, radius, width)
