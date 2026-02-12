"""
Dose Chip Generator - Comprehensive junction testing
Creates 7x7mm chips with dose tests and dose arrays

Based on maskLib fluxonium example patterns
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'multimode'))

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Callable

from phidl import Device
import phidl.geometry as pg
from phidl_bridge import Chip, Structure, CPWStraight, CPWLinearTaper
import phidl_bridge

# ============================================================================
# JUNCTION DRAWING FUNCTIONS
# ============================================================================

def draw_dolan_junction_variable_uc(width: float, gap: float, layer_pin: int, layer_gap: int,
                                    uc: float = 0.3, right_width: float = 2.0) -> Tuple[Device, Device]:
    """
    Draw a Dolan bridge junction with variable undercut border width.

    Args:
        width: Left thin section width (um)
        gap: Junction gap (um)
        layer_pin: PIN layer number (fullcut)
        layer_gap: GAP layer number (undercut)
        uc: Undercut border width (um), default 0.3
        right_width: Right thin section width (um), default 2.0

    Returns:
        (pin_device, gap_device) tuple
    """
    # Save original layer settings
    orig_pin = phidl_bridge.LAYER_PIN
    orig_gap = phidl_bridge.LAYER_GAP

    # Geometry parameters
    bar_w = 5.0      # Bar width
    taper_l = 2.0    # Taper length
    thin_l = 0.8     # Thin section length
    right_width = max(width, right_width)  # Ensure right width is at least as large as left width

    try:
        # Set layers for this junction
        phidl_bridge.LAYER_PIN = layer_pin
        phidl_bridge.LAYER_GAP = layer_gap

        # Create temporary chips for drawing
        pin_chip = Chip('pin_temp', size=(20, 20), two_layer=False)
        gap_chip = Chip('gap_temp', size=(20, 20), two_layer=False)

        # =====================================================================
        # PIN LAYER - Draw fullcut geometry
        # =====================================================================
        s = Structure(pin_chip, start=(0, 0), direction=0)

        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)                        # Left bar (rectangle: width=5µm)
        CPWLinearTaper(s, length=taper_l, start_pinw=bar_w, stop_pinw=width, start_gapw=0, stop_gapw=0)       # Taper down to left width
        CPWStraight(s, pinw=0, gapw=width/2, length=thin_l)                     # Left thin section
        s.last = (s.last[0] + gap, s.last[1])                # Skip gap
        CPWStraight(s, pinw=0, gapw=right_width/2, length=thin_l)               # Right thin section
        CPWLinearTaper(s, length=taper_l, start_pinw=right_width, stop_pinw=bar_w, start_gapw=0, stop_gapw=0) # Taper up from right width
        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)                        # Right bar (rectangle: width=5µm)

        # =====================================================================
        # GAP LAYER - Draw undercut borders sequentially
        # =====================================================================
        # IMPORTANT: In optical mode (two_layer=False), geometry always draws on LAYER_PIN
        # So to draw on GAP layer, we set LAYER_PIN = layer_gap temporarily
        phidl_bridge.LAYER_PIN = layer_gap
        s2 = Structure(gap_chip, start=(0, 0), direction=0)

        # Save position and draw left edge border
        left_pos = s2.last
        s2.last_direction = 0
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Return to horizontal, draw left bar borders
        s2.last_direction = 0
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Left taper borders
        CPWLinearTaper(s2, length=taper_l, start_pinw=bar_w, stop_pinw=width, start_gapw=uc/2, stop_gapw=uc/2)

        # Left thin section borders
        CPWStraight(s2, pinw=width, gapw=uc/2, length=thin_l)

        # Gap region (full rectangle for bridge) - use max of left/right widths
        max_width = max(width, right_width)
        CPWStraight(s2, pinw=0, gapw=(max_width+uc)/2, length=gap)

        # Right thin section borders
        CPWStraight(s2, pinw=right_width, gapw=uc/2, length=thin_l)

        # Right taper borders
        CPWLinearTaper(s2, length=taper_l, start_pinw=right_width, stop_pinw=bar_w, start_gapw=uc/2, stop_gapw=uc/2)

        # Right bar borders
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Right edge border
        right_pos = s2.last
        s2.last_direction = 0
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Extract and center devices
        pin_dev = pin_chip.device
        gap_dev = gap_chip.device
        pin_dev.move(origin=pin_dev.center, destination=(0, 0))
        gap_dev.move(origin=gap_dev.center, destination=(0, 0))

        return pin_dev, gap_dev

    finally:
        # Restore original layers
        phidl_bridge.LAYER_PIN = orig_pin
        phidl_bridge.LAYER_GAP = orig_gap


def draw_dolan_junction(width: float, gap: float, layer_pin: int, layer_gap: int, right_width: float = 2.0) -> Tuple[Device, Device]:
    """
    Draw a Dolan bridge junction using phidl_bridge stateful API.

    Args:
        width: Left thin section width (um)
        gap: Junction gap (um)
        layer_pin: PIN layer number (fullcut)
        layer_gap: GAP layer number (undercut)
        right_width: Right thin section width (um), default 2.0

    Returns:
        (pin_device, gap_device) tuple
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
        # Set layers for this junction
        phidl_bridge.LAYER_PIN = layer_pin
        phidl_bridge.LAYER_GAP = layer_gap

        # Create temporary chips for drawing
        pin_chip = Chip('pin_temp', size=(20, 20), two_layer=False)
        gap_chip = Chip('gap_temp', size=(20, 20), two_layer=False)

        # =====================================================================
        # PIN LAYER - Draw fullcut geometry
        # =====================================================================
        s = Structure(pin_chip, start=(0, 0), direction=0)

        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)                        # Left bar (rectangle: width=5µm)
        CPWLinearTaper(s, length=taper_l, start_pinw=bar_w, stop_pinw=width, start_gapw=0, stop_gapw=0)       # Taper down to left width
        CPWStraight(s, pinw=0, gapw=width/2, length=thin_l)                     # Left thin section
        s.last = (s.last[0] + gap, s.last[1])                # Skip gap
        CPWStraight(s, pinw=0, gapw=right_width/2, length=thin_l)               # Right thin section
        CPWLinearTaper(s, length=taper_l, start_pinw=right_width, stop_pinw=bar_w, start_gapw=0, stop_gapw=0) # Taper up from right width
        CPWStraight(s, pinw=0, gapw=bar_w/2, length=1.0)                        # Right bar (rectangle: width=5µm)

        # =====================================================================
        # GAP LAYER - Draw undercut borders sequentially
        # =====================================================================
        # IMPORTANT: In optical mode (two_layer=False), geometry always draws on LAYER_PIN
        # So to draw on GAP layer, we set LAYER_PIN = layer_gap temporarily
        phidl_bridge.LAYER_PIN = layer_gap
        s2 = Structure(gap_chip, start=(0, 0), direction=0)

        # Save position and draw left edge border
        left_pos = s2.last
        s2.last_direction = 0
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Return to horizontal, draw left bar borders
        # s2.last = left_pos
        s2.last_direction = 0
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Left taper borders
        CPWLinearTaper(s2, length=taper_l, start_pinw=bar_w, stop_pinw=width, start_gapw=uc/2, stop_gapw=uc/2)

        # Left thin section borders
        CPWStraight(s2, pinw=width, gapw=uc/2, length=thin_l)

        # Gap region (full rectangle for bridge) - use max of left/right widths
        max_width = max(width, right_width)
        CPWStraight(s2, pinw=0, gapw=(max_width+uc)/2, length=gap)

        # Right thin section borders
        CPWStraight(s2, pinw=right_width, gapw=uc/2, length=thin_l)

        # Right taper borders
        CPWLinearTaper(s2, length=taper_l, start_pinw=right_width, stop_pinw=bar_w, start_gapw=uc/2, stop_gapw=uc/2)

        # Right bar borders
        CPWStraight(s2, pinw=bar_w, gapw=uc/2, length=1.0)

        # Right edge border
        right_pos = s2.last
        s2.last_direction = 0
        CPWStraight(s2, pinw=0, gapw=(bar_w + uc)/2, length=uc)

        # Extract and center devices
        pin_dev = pin_chip.device
        gap_dev = gap_chip.device
        pin_dev.move(origin=pin_dev.center, destination=(0, 0))
        gap_dev.move(origin=gap_dev.center, destination=(0, 0))

        return pin_dev, gap_dev

    finally:
        # Restore original layers
        phidl_bridge.LAYER_PIN = orig_pin
        phidl_bridge.LAYER_GAP = orig_gap


def draw_dolan_junction_array(width: float, gap: float,
                              layer_pin: int, layer_gap: int,
                              right_width: float = 2.0,
                              num_juncs: int = 10) -> Tuple[Device, Device]:
    """
    Draw a Dolan bridge junction array.
    
    Structure: Bar | Taper | Thin | Gap | [Thin | Gap]×N | Thin | Taper | Bar
    
    Args:
        width: Thin section width (um)
        gap: Junction gap (um)
        layer_pin: PIN layer number (fullcut)
        layer_gap: GAP layer number (undercut)
        right_width: Right thin section width (um)
        num_juncs: Number of junctions in series
    
    Returns:
        (pin_device, gap_device): Tuple of phidl Devices
    """
    # Save original layer settings
    orig_pin = phidl_bridge.LAYER_PIN
    orig_gap = phidl_bridge.LAYER_GAP
    
    # =========================================================================
    # GEOMETRY PARAMETERS - Edit these to customize!
    # =========================================================================
    bar_w = 5.0      # Contact pad width (um)
    taper_l = 2.0    # Taper length (um)
    thin_l = 0.8     # Thin section length (um)
    uc = 0.3         # Undercut border width (um)
    right_width = max(width, right_width)  # Ensure right width is at least as large as left width
    
    try:
        # Set layers
        phidl_bridge.LAYER_PIN = layer_pin
        phidl_bridge.LAYER_GAP = layer_gap
        
        # Create temporary chips
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
            CPWStraight(s, pinw=0, gapw=width/2, length=gap)
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
        # WORKAROUND: Set LAYER_PIN = layer_gap to draw on GAP layer
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
        
        
        # Middle thin sections and gaps (for junction array)
        for i in range(num_juncs - 1):
            # Bridge 
            CPWStraight(s2, pinw=0, gapw=(width + uc)/2, length=gap)
            # Thin section borders (match PIN layer: length=gap)
            CPWStraight(s2, pinw=width, gapw=uc/2, length=gap)
            
        # Gap region border
        CPWStraight(s2, pinw=0, gapw=( max_width+uc)/2, length=gap)
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
        # Restore original layers
        phidl_bridge.LAYER_PIN = orig_pin
        phidl_bridge.LAYER_GAP = orig_gap


def draw_rectangle_cpw(pin_chip, gap_chip, center_pos: Tuple[float, float],
                       width: float, length: float,
                       direction: float,
                       paddle_width: float = 1.0,
                       paddle_length: float = 1.5,
                       uc: float = 0.3) -> None:
    """
    Draw a solid rectangle with paddles at ends and side undercut borders.

    Args:
        pin_chip: Chip object for main rectangle (PIN layer)
        gap_chip: Chip object for paddles and side undercut (GAP/undercut layer)
        center_pos: (x, y) center position of rectangle
        width: Rectangle width (perpendicular to direction)
        length: Rectangle length (along direction)
        direction: Angle in degrees (0=horizontal, 90=vertical, 45/−45=diagonal)
        paddle_width: Paddle width (default 1.0 µm)
        paddle_length: Paddle length (default 1.5 µm)
        uc: Undercut border width (default 0.15 µm = 150 nm)

    Draws:
        - Main rectangle on pin_chip (fullcut metal)
        - Paddles at both ends on gap_chip (undercut)
        - Side undercut borders (150 nm width) along rectangle edges (between paddles)
    """
    # Save original layer setting
    orig_layer_pin = phidl_bridge.LAYER_PIN

    theta_rad = np.radians(direction)

    # Draw main rectangle on PIN chip (centered at center_pos)
    half_dx = (length / 2) * np.cos(theta_rad)
    half_dy = (length / 2) * np.sin(theta_rad)
    start_pos = (center_pos[0] - half_dx, center_pos[1] - half_dy)

    s_main = Structure(pin_chip, start=start_pos, direction=direction)
    CPWStraight(s_main, pinw=0, gapw=width/2, length=length)

    # Switch to GAP layer for undercut features
    phidl_bridge.LAYER_PIN = phidl_bridge.LAYER_GAP

    # Calculate positions for undercut features
    paddle_half_dx = (paddle_length / 2) * np.cos(theta_rad)
    paddle_half_dy = (paddle_length / 2) * np.sin(theta_rad)

    # Left paddle (at start end)
    left_center = (center_pos[0] - half_dx, center_pos[1] - half_dy)
    left_start = (left_center[0] - paddle_half_dx, left_center[1] - paddle_half_dy)
    s_left = Structure(gap_chip, start=left_start, direction=direction)
    CPWStraight(s_left, pinw=0, gapw=paddle_width/2, length=paddle_length)

    # Side undercut borders (between paddles, along rectangle edges)
    # Start just after left paddle, end just before right paddle
    side_start_x = center_pos[0] - half_dx + (paddle_length/2) * np.cos(theta_rad)
    side_start_y = center_pos[1] - half_dy + (paddle_length/2) * np.sin(theta_rad)
    side_length = length - paddle_length

    s_side = Structure(gap_chip, start=(side_start_x, side_start_y), direction=direction)
    CPWStraight(s_side, pinw=width, gapw=uc/2, length=side_length)

    # Right paddle (at end end)
    right_center = (center_pos[0] + half_dx, center_pos[1] + half_dy)
    right_start = (right_center[0] - paddle_half_dx, right_center[1] - paddle_half_dy)
    s_right = Structure(gap_chip, start=right_start, direction=direction)
    CPWStraight(s_right, pinw=0, gapw=paddle_width/2, length=paddle_length)

    # Restore original layer
    phidl_bridge.LAYER_PIN = orig_layer_pin



def draw_manhattan_junction(width: float,
                            layer_pin: int, layer_gap: int) -> Tuple[Device, Device]:
    """
    Draw a Manhattan cross junction.

    Structure:
    - 2 straight bandage leads (horizontal contact pads)
    - 2 angled leads at 45°/135° that cross
    - Junction gap at crossing point
    - Paddle-shaped undercut at all lead ends

    Args:
        width: Junction width (um) - width of angled leads
        layer_pin: PIN layer number (fullcut)
        layer_gap: GAP layer number (undercut)

    Returns:
        (pin_device, gap_device): Tuple of phidl Devices
    """
    # Save original layer settings
    orig_pin = phidl_bridge.LAYER_PIN
    orig_gap = phidl_bridge.LAYER_GAP

    # =========================================================================
    # GEOMETRY PARAMETERS
    # =========================================================================
    bandage_w = 0.2       # Bandage width (um)
    bandage_l = 20        # Bandage length (um)
    angle_w = width       # Angled lead width (um)
    angle_l = 10          # Angled lead length (um)
    uc = 0.5              # Undercut border width (um)
    hor_offset = 1.5      # Horizontal spacing between bandages (um)
    ver_offset = 1        # Vertical spacing between bandages (um)

    try:
        phidl_bridge.LAYER_PIN = layer_pin
        phidl_bridge.LAYER_GAP = layer_gap

        pin_chip = Chip('pin_temp', size=(50, 50), two_layer=False)
        gap_chip = Chip('gap_temp', size=(50, 50), two_layer=False)

        # =====================================================================
        # DRAW GEOMETRY - 2 bandages + 2 angled leads
        # =====================================================================

        # Bandage 1: Left horizontal lead
        pos1 = (-hor_offset - bandage_l/2, 0)
        draw_rectangle_cpw(pin_chip, gap_chip, pos1,
                          width=bandage_w, length=bandage_l, direction=0)

        # Bandage 2: Right horizontal lead (offset vertically)
        pos2 = (hor_offset + bandage_l/2, -ver_offset)
        draw_rectangle_cpw(pin_chip, gap_chip, pos2,
                          width=bandage_w, length=bandage_l, direction=0)

        # Angled lead 1: 45° diagonal
        pos3 = (-2*hor_offset, 2*hor_offset/3)
        draw_rectangle_cpw(pin_chip, gap_chip, pos3,
                          width=angle_w, length=1.25*angle_l, direction=45)

        # Angled lead 2: 135° diagonal (perpendicular to lead 1)
        pos4 = (2*hor_offset, hor_offset - ver_offset)
        draw_rectangle_cpw(pin_chip, gap_chip, pos4,
                          width=angle_w, length=1.25*angle_l, direction=135)

        # Center and return devices
        pin_dev = pin_chip.device
        gap_dev = gap_chip.device
        pin_dev.move(origin=pin_dev.center, destination=(0, 0))
        gap_dev.move(origin=gap_dev.center, destination=(0, 0))

        return pin_dev, gap_dev

    finally:
        phidl_bridge.LAYER_PIN = orig_pin
        phidl_bridge.LAYER_GAP = orig_gap


# ============================================================================
# GRID GENERATORS
# ============================================================================

def create_dose_test_grid(junction_func: Callable,
                         geometry: Tuple[float, float],
                         dose_fullcut_range: Tuple[float, float],
                         dose_undercut_range: Tuple[float, float],
                         n_rows: int = 6,
                         n_cols: int = 12,
                         spacing: float = 50,
                         start_pos: Tuple[float, float] = (0, 0),
                         base_layer_fc: int = 200,
                         base_layer_uc: int = 600) -> Tuple[Device, List]:
    """
    Create a dose test grid - same geometry, varying doses.

    Args:
        junction_func: Function(width, gap, layer_pin, layer_gap) -> (pin_dev, gap_dev)
        geometry: (width, gap) fixed geometry
        dose_fullcut_range: (min, max) fullcut doses (uC/cm^2)
        dose_undercut_range: (min, max) undercut doses (uC/cm^2)
        n_rows: Number of rows (undercut dose sweep)
        n_cols: Number of columns (fullcut dose sweep)
        spacing: Grid spacing (um)
        start_pos: (x, y) starting position
        base_layer_fc: Base layer number for fullcut
        base_layer_uc: Base layer number for undercut

    Returns:
        (grid_device, dose_table)
    """
    grid = Device('dose_test_grid')
    dose_table = []

    # Add clearing dose layer for junction labels
    dose_table.append((2, 3000, 'clearing'))

    width, gap = geometry
    dose_fc_values = np.linspace(dose_fullcut_range[0], dose_fullcut_range[1], n_cols)
    dose_uc_values = np.linspace(dose_undercut_range[0], dose_undercut_range[1], n_rows)

    base_x, base_y = start_pos

    for i in range(n_cols):
        for j in range(n_rows):
            # Position
            xpos = base_x + i * spacing
            ypos = base_y + j * spacing

            # Layers
            layer_fc = base_layer_fc + i
            layer_uc = base_layer_uc + j

            # Get dose values for this junction
            dose_fc = dose_fc_values[i]
            dose_uc = dose_uc_values[j]

            # Draw junction
            pin_dev, gap_dev = junction_func(width, gap, layer_fc, layer_uc)

            ref = grid << pin_dev
            ref.move(destination=(xpos, ypos))

            ref = grid << gap_dev
            ref.move(destination=(xpos, ypos))

            # Add label on top of junction showing DOSE VALUES (not layer numbers)
            label_text = f'{dose_fc:.0f}/{dose_uc:.0f}'
            text = pg.text(label_text, size=6, layer=2, justify='center')
            text_ref = grid << text
            text_ref.move(destination=(xpos, ypos + 25))  # Above junction

            # Add enclosing box around junction region (label layer)
            box = pg.rectangle(size=(80, 80), layer=1)
            box_ref = grid << box
            box_ref.move(origin=box_ref.center, destination=(xpos, ypos + 10))  # Centered on junction+label

            # Store doses
            if layer_fc not in [d[0] for d in dose_table]:
                dose_table.append((layer_fc, dose_fc, 'fullcut'))
            if layer_uc not in [d[0] for d in dose_table]:
                dose_table.append((layer_uc, dose_uc*4, 'undercut'))  # *4 for BEAMER

    return grid, dose_table


def create_dose_array_grid(junction_func: Callable,
                           dose_fullcut: float,
                           dose_undercut: float,
                           width_range: Tuple[float, float],
                           gap_range: Tuple[float, float],
                           n_rows: int = 5,
                           n_cols: int = 5,
                           spacing: float = 50,
                           start_pos: Tuple[float, float] = (0, 0),
                           layer_pin: int = 20,
                           layer_gap: int = 60) -> Device:
    """
    Create a dose array grid - varying geometry, fixed doses.

    Args:
        junction_func: Function(width, gap, layer_pin, layer_gap) -> (pin_dev, gap_dev)
        dose_fullcut: Fixed fullcut dose for PIN layer
        dose_undercut: Fixed undercut dose for GAP layer
        width_range: (min, max) junction widths (um)
        gap_range: (min, max) junction gaps (um)
        n_rows: Number of rows (gap sweep)
        n_cols: Number of columns (width sweep)
        spacing: Grid spacing (um)
        start_pos: (x, y) starting position
        layer_pin: PIN layer number (same for all)
        layer_gap: GAP layer number (same for all)

    Returns:
        grid_device
    """
    grid = Device('dose_array_grid')

    widths = np.linspace(width_range[0], width_range[1], n_cols)
    gaps = np.linspace(gap_range[0], gap_range[1], n_rows)

    base_x, base_y = start_pos

    for i, width in enumerate(widths):
        for j, gap in enumerate(gaps):
            # Position
            xpos = base_x + i * spacing
            ypos = base_y + j * spacing

            # Draw junction with varying geometry
            pin_dev, gap_dev = junction_func(width, gap, layer_pin, layer_gap)

            ref = grid << pin_dev
            ref.move(destination=(xpos, ypos))

            ref = grid << gap_dev
            ref.move(destination=(xpos, ypos))

            # Add label on top of junction (clearing dose layer 2)
            label_text = f'{width:.2f}/{gap:.2f}'
            text = pg.text(label_text, size=6, layer=2, justify='center')
            text_ref = grid << text
            text_ref.move(destination=(xpos, ypos + 25))  # Above junction

            # Add enclosing box around junction region (label layer)
            box = pg.rectangle(size=(80, 80), layer=1)
            box_ref = grid << box
            box_ref.move(origin=box_ref.center, destination=(xpos, ypos + 10))  # Centered on junction+label

    return grid


def create_undercut_test_grid(width_range: Tuple[float, float],
                               uc_range: Tuple[float, float],
                               gap: float = 0.2,
                               n_rows: int = 5,
                               n_cols: int = 5,
                               spacing: float = 50,
                               start_pos: Tuple[float, float] = (0, 0),
                               layer_pin: int = 20,
                               layer_gap: int = 60) -> Device:
    """
    Create an undercut test grid - varying junction width and undercut border.

    Args:
        width_range: (min, max) junction widths (um)
        uc_range: (min, max) undercut border widths (um)
        gap: Fixed junction gap (um)
        n_rows: Number of rows (uc sweep)
        n_cols: Number of columns (width sweep)
        spacing: Grid spacing (um)
        start_pos: (x, y) starting position
        layer_pin: PIN layer number
        layer_gap: GAP layer number

    Returns:
        grid_device
    """
    grid = Device('undercut_test_grid')

    widths = np.linspace(width_range[0], width_range[1], n_cols)
    ucs = np.linspace(uc_range[0], uc_range[1], n_rows)

    base_x, base_y = start_pos

    for i, width in enumerate(widths):
        for j, uc in enumerate(ucs):
            # Position
            xpos = base_x + i * spacing
            ypos = base_y + j * spacing

            # Draw junction with varying width and uc
            pin_dev, gap_dev = draw_dolan_junction_variable_uc(width, gap, layer_pin, layer_gap, uc=uc)

            ref = grid << pin_dev
            ref.move(destination=(xpos, ypos))

            ref = grid << gap_dev
            ref.move(destination=(xpos, ypos))

    return grid


def create_manhattan_sweep_grid(width_range: Tuple[float, float],
                                n_junctions: int = 20,
                                n_cols: int = 10,
                                spacing: float = 500,
                                start_pos: Tuple[float, float] = (0, 0),
                                layer_pin: int = 20,
                                layer_gap: int = 60) -> Device:
    """
    Create a 1D width sweep of Manhattan junctions in 2D grid layout.

    Args:
        width_range: (min, max) junction widths (um)
        n_junctions: Total number of junctions to create
        n_cols: Number of junctions per row before wrapping
        spacing: Grid spacing (um)
        start_pos: (x, y) starting position
        layer_pin: PIN layer number
        layer_gap: GAP layer number

    Returns:
        grid_device with Manhattan junctions in 2D layout

    Example:
        # 20 junctions, 0.1-0.5 um width, 10 per row (2 rows total)
        grid = create_manhattan_sweep_grid(
            width_range=(0.1, 0.5),
            n_junctions=20,
            n_cols=10,
            spacing=500
        )
    """
    grid = Device('manhattan_sweep')

    # Generate width values
    widths = np.linspace(width_range[0], width_range[1], n_junctions)

    base_x, base_y = start_pos

    # Layout in 2D grid (wrap to new row after n_cols)
    for idx, width in enumerate(widths):
        # Calculate grid position
        col = idx % n_cols
        row = idx // n_cols

        xpos = base_x + col * spacing
        ypos = base_y + row * spacing

        # Draw junction with current width
        pin_dev, gap_dev = draw_manhattan_junction(
            width=width,
            layer_pin=layer_pin,
            layer_gap=layer_gap
        )

        # Add to grid
        ref_pin = grid << pin_dev
        ref_pin.move(destination=(xpos, ypos))

        ref_gap = grid << gap_dev
        ref_gap.move(destination=(xpos, ypos))

        # Add label on top of junction showing width value (clearing dose layer 2)
        label_text = f'{width:.2f}'
        text = pg.text(label_text, size=6, layer=2, justify='center')
        text_ref = grid << text
        text_ref.move(destination=(xpos, ypos + 25))  # Above junction

        # Add enclosing box around junction region (label layer)
        box = pg.rectangle(size=(80, 80), layer=1)
        box_ref = grid << box
        box_ref.move(origin=box_ref.center, destination=(xpos, ypos + 10))  # Centered on junction+label

    return grid


def draw_manhattan_junction_for_dose_test(width: float, gap: float,
                                          layer_pin: int, layer_gap: int) -> Tuple[Device, Device]:
    """
    Wrapper for Manhattan junction compatible with dose test grid.

    Note: gap parameter is ignored (Manhattan junction has fixed crossing geometry)

    Args:
        width: Junction width (um)
        gap: Ignored (kept for compatibility with dose test interface)
        layer_pin: PIN layer number
        layer_gap: GAP layer number

    Returns:
        (pin_device, gap_device): Tuple of phidl Devices
    """
    return draw_manhattan_junction(width=width, layer_pin=layer_pin, layer_gap=layer_gap)


def add_grid_labels(chip: Device, grid_type: str,
                   x_values: np.ndarray, y_values: np.ndarray,
                   x_label: str, y_label: str,
                   start_pos: Tuple[float, float],
                   spacing: float,
                   label_layer: int = 1):
    """
    Add labels to a grid.

    Args:
        chip: Chip device to add labels to
        grid_type: 'dose_test', 'dose_array', or 'undercut_test'
        x_values: Values for column labels
        y_values: Values for row labels
        x_label: Label for x-axis (e.g., 'FC', 'Width')
        y_label: Label for y-axis (e.g., 'UC', 'Gap')
        start_pos: (x, y) grid starting position
        spacing: Grid spacing
        label_layer: Layer number for labels
    """
    base_x, base_y = start_pos
    n_cols = len(x_values)
    n_rows = len(y_values)

    # Scale text size based on spacing (for compact grids)
    # Offsets adjusted to avoid clash with 80x80 um boxes
    if spacing <= 100:
        label_size = 8
        title_size = 12
        col_offset = -70   # Below boxes (boxes extend to -30)
        row_offset = -90   # Left of boxes (boxes extend to -40)
        title_offset = -100
    else:
        label_size = 25
        title_size = 35
        col_offset = -80
        row_offset = -120
        title_offset = -150

    # Column labels
    for i, val in enumerate(x_values):
        xpos = base_x + i * spacing
        ypos = base_y + col_offset

        text = pg.text(f'{x_label}:{val:.0f}' if grid_type == 'dose_test' else f'{val:.2f}',
                      size=label_size, layer=label_layer, justify='center')
        ref = chip << text
        ref.move(destination=(xpos, ypos))

    # Row labels
    for j, val in enumerate(y_values):
        xpos = base_x + row_offset
        ypos = base_y + j * spacing

        text = pg.text(f'{y_label}:{val:.0f}' if grid_type == 'dose_test' else f'{val:.2f}',
                      size=label_size, layer=label_layer, justify='right')
        ref = chip << text
        ref.move(destination=(xpos, ypos))

    # Title
    title_y = base_y + title_offset
    if grid_type == 'dose_test':
        title = pg.text(f'Dose Test: {x_label} vs {y_label}', size=title_size, layer=label_layer, justify='center')
    elif grid_type == 'dose_array':
        title = pg.text(f'Dose Array: {x_label} vs {y_label}', size=title_size, layer=label_layer, justify='center')
    else:  # undercut_test
        title = pg.text(f'Undercut Test: {x_label} vs {y_label}', size=title_size, layer=label_layer, justify='center')

    ref = chip << title
    ref.move(destination=(base_x + (n_cols-1)*spacing/2, title_y))


# ============================================================================
# MAIN CHIP GENERATOR
# ============================================================================

class DoseChipGenerator:
    """
    Main class for generating comprehensive dose testing chips.
    """

    def __init__(self, chip_size: Tuple[float, float] = (5000, 5000)):
        """
        Initialize chip generator.

        Args:
            chip_size: (width, height) in um
        """
        self.chip_size = chip_size
        self.chip = Device('DOSE_CHIP')
        self.dose_table = []
        self._dose_arrays = []  # Store dose array metadata for documentation
        self.label_layer = 1

        # Add chip boundary rectangle (7mm x 7mm centered at origin)
        boundary = pg.rectangle(size=chip_size, layer=0)
        ref = self.chip << boundary
        ref.move(origin=ref.center, destination=(0, 0))

    def add_dose_test(self, name: str, junction_func: Callable,
                     geometry: Tuple[float, float],
                     dose_fullcut_range: Tuple[float, float],
                     dose_undercut_range: Tuple[float, float],
                     position: Tuple[float, float],
                     n_rows: int = 6, n_cols: int = 12,
                     spacing: float = 400):
        """
        Add a dose test grid to the chip.
        """
        print(f'  Adding dose test: {name}')
        grid, doses = create_dose_test_grid(
            junction_func, geometry,
            dose_fullcut_range, dose_undercut_range,
            n_rows, n_cols, spacing, position
        )

        self.chip << grid
        self.dose_table.extend(doses)

        # Add labels
        dose_fc = np.linspace(dose_fullcut_range[0], dose_fullcut_range[1], n_cols)
        dose_uc = np.linspace(dose_undercut_range[0], dose_undercut_range[1], n_rows)
        add_grid_labels(self.chip, 'dose_test', dose_fc, dose_uc,
                       'FC', 'UC', position, spacing, self.label_layer)

    def add_dose_array(self, name: str, junction_func: Callable,
                      dose_fullcut: float,
                      dose_undercut: float,
                      width_range: Tuple[float, float],
                      gap_range: Tuple[float, float],
                      position: Tuple[float, float],
                      n_rows: int = 5, n_cols: int = 5,
                      spacing: float = 400):
        """
        Add a dose array grid to the chip.

        Args:
            name: Name for this array
            junction_func: Function(width, gap, layer_pin, layer_gap) -> (pin_dev, gap_dev)
            dose_fullcut: Fixed fullcut dose for PIN layer (layer 20)
            dose_undercut: Fixed undercut dose for GAP layer (layer 60)
            width_range: (min, max) junction widths (um)
            gap_range: (min, max) junction gaps (um)
            position: (x, y) starting position
            n_rows: Number of rows
            n_cols: Number of columns
            spacing: Grid spacing (um)
        """
        print(f'  Adding dose array: {name}')
        grid = create_dose_array_grid(
            junction_func, dose_fullcut, dose_undercut,
            width_range, gap_range,
            n_rows, n_cols, spacing, position
        )

        self.chip << grid

        # Store dose information for documentation
        self._dose_arrays.append({
            'name': name,
            'dose_fullcut': dose_fullcut,
            'dose_undercut': dose_undercut,
            'layer_pin': 20,
            'layer_gap': 60
        })

        # Add doses to dose table
        if 20 not in [d[0] for d in self.dose_table]:
            self.dose_table.append((20, dose_fullcut, 'fullcut'))
        if 60 not in [d[0] for d in self.dose_table]:
            self.dose_table.append((60, dose_undercut*4, 'undercut'))  # *4 for BEAMER

        # Add labels
        widths = np.linspace(width_range[0], width_range[1], n_cols)
        gaps = np.linspace(gap_range[0], gap_range[1], n_rows)
        add_grid_labels(self.chip, 'dose_array', widths, gaps,
                       'W', 'G', position, spacing, self.label_layer)

    def add_undercut_test(self, name: str,
                         width_range: Tuple[float, float],
                         uc_range: Tuple[float, float],
                         gap: float,
                         position: Tuple[float, float],
                         n_rows: int = 5, n_cols: int = 5,
                         spacing: float = 50):
        """
        Add an undercut test grid to the chip.
        """
        print(f'  Adding undercut test: {name}')
        grid = create_undercut_test_grid(
            width_range, uc_range, gap,
            n_rows, n_cols, spacing, position
        )

        self.chip << grid

        # Add labels
        widths = np.linspace(width_range[0], width_range[1], n_cols)
        ucs = np.linspace(uc_range[0], uc_range[1], n_rows)
        add_grid_labels(self.chip, 'undercut_test', widths, ucs,
                       'W', 'UC', position, spacing, self.label_layer)

    def add_manhattan_sweep(self, name: str,
                           width_range: Tuple[float, float],
                           position: Tuple[float, float],
                           n_junctions: int = 20,
                           n_cols: int = 10,
                           spacing: float = 500,
                           dose_fullcut: float = 1450,
                           dose_undercut: float = 350):
        """
        Add Manhattan junction width sweep to chip.

        Args:
            name: Name for this sweep
            width_range: (min, max) widths (um)
            position: (x, y) starting position
            n_junctions: Total number of junctions
            n_cols: Junctions per row before wrapping
            spacing: Grid spacing (um)
            dose_fullcut: Fixed fullcut dose for layer 20 (default 1450)
            dose_undercut: Fixed undercut dose for layer 60 (default 350)
        """
        print(f'  Adding Manhattan width sweep: {name}')
        grid = create_manhattan_sweep_grid(
            width_range, n_junctions, n_cols, spacing, position
        )

        self.chip << grid

        # Add doses to dose table (layers 20 and 60)
        if 20 not in [d[0] for d in self.dose_table]:
            self.dose_table.append((20, dose_fullcut, 'fullcut'))
        if 60 not in [d[0] for d in self.dose_table]:
            self.dose_table.append((60, dose_undercut*4, 'undercut'))  # *4 for BEAMER

        # Add grid labels
        widths = np.linspace(width_range[0], width_range[1], n_junctions)
        n_rows = (n_junctions + n_cols - 1) // n_cols  # Ceiling division

        # Get unique widths for columns and rows
        col_widths = widths[:n_cols] if n_cols <= n_junctions else widths
        row_indices = np.arange(n_rows)

        # For a 1D sweep, label columns with widths and rows with indices
        add_grid_labels(self.chip, 'dose_array', col_widths, row_indices,
                       'Width', 'Row', position, spacing, self.label_layer)

    def add_manhattan_dose_test(self, name: str,
                                geometry: Tuple[float, float],
                                dose_fullcut_range: Tuple[float, float],
                                dose_undercut_range: Tuple[float, float],
                                position: Tuple[float, float],
                                n_rows: int = 6, n_cols: int = 12,
                                spacing: float = 400):
        """
        Add Manhattan junction dose test to chip.

        Varies e-beam doses while keeping junction width fixed.

        Args:
            name: Name for this test
            geometry: (width, gap) - gap is ignored for Manhattan
            dose_fullcut_range: (min, max) fullcut doses (uC/cm^2)
            dose_undercut_range: (min, max) undercut doses (uC/cm^2)
            position: (x, y) starting position
            n_rows: Number of rows (undercut dose sweep)
            n_cols: Number of columns (fullcut dose sweep)
            spacing: Grid spacing (um)
        """
        print(f'  Adding Manhattan dose test: {name}')
        grid, dose_table = create_dose_test_grid(
            draw_manhattan_junction_for_dose_test,
            geometry,
            dose_fullcut_range,
            dose_undercut_range,
            n_rows, n_cols, spacing, position
        )

        self.chip << grid
        self.dose_table.extend(dose_table)

        # Add labels
        dose_fc_values = np.linspace(dose_fullcut_range[0], dose_fullcut_range[1], n_cols)
        dose_uc_values = np.linspace(dose_undercut_range[0], dose_undercut_range[1], n_rows)
        add_grid_labels(self.chip, 'dose_test', dose_fc_values, dose_uc_values,
                       'FC', 'UC', position, spacing, self.label_layer)

    def save(self, filename: str = 'dose_chip.gds'):
        """
        Save chip to GDS file and generate dose table.
        """
        print(f'\nSaving...')

        # Save GDS
        self.chip.write_gds(filename)
        print(f'  {filename}')

        # Save dose table
        dose_table_file = filename.replace('.gds', '_dose_table.txt')
        with open(dose_table_file, 'w') as f:
            f.write('# DOSE TABLE\n')
            f.write(f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write('# Layer, Dose (uC/cm^2)\n')

            # Remove duplicates and sort
            unique_doses = {}
            for layer, dose, dtype in self.dose_table:
                if layer not in unique_doses:
                    unique_doses[layer] = (dose, dtype)

            for layer in sorted(unique_doses.keys()):
                dose, dtype = unique_doses[layer]
                f.write(f'{layer}, {dose:.1f}\n')

            # Add dose array information
            if self._dose_arrays:
                f.write('\n# DOSE ARRAYS (Fixed dose, varying geometry)\n')
                for arr in self._dose_arrays:
                    f.write(f'# {arr["name"]}: Layer {arr["layer_pin"]} = {arr["dose_fullcut"]:.1f} uC/cm^2 (fullcut), '
                           f'Layer {arr["layer_gap"]} = {arr["dose_undercut"]:.1f} uC/cm^2 (undercut)\n')

        print(f'  {dose_table_file}')
        print(f'\nDone! Chip size: {self.chip_size[0]}x{self.chip_size[1]} um')


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    print('='*70)
    print('DOSE CHIP GENERATOR')
    print('='*70)

    # Create chip generator (7x7 mm chip)
    generator = DoseChipGenerator()  # Default: 7000x7000 um (7x7 mm)

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
    generator.save('dose_chip_example.gds')

    print('='*70)
