# -*- coding: utf-8 -*-
"""
phidl_bridge.py

Compatibility bridge layer for migrating from mask_maker to phidl.
Provides mask_maker-compatible API that uses phidl underneath.

Created: 2026-02-07
Author: Migration from mask_maker to phidl
"""

import numpy as np
import phidl.geometry as pg
from phidl import Device, Port, CrossSection, Path
from typing import Tuple, Optional, Union


# Layer definitions (matching mask_maker conventions)
LAYER_PIN = 1  # Conductor layer (metal)
LAYER_GAP = 2  # Ground plane / undercut layer


class StateTracker:
    """
    Tracks position and direction state for compatibility with mask_maker's
    Structure.last and Structure.last_direction attributes.

    Provides stateful drawing context that can be converted to/from phidl Ports.
    """

    def __init__(self, position: Tuple[float, float] = (0, 0), direction: float = 0):
        """
        Initialize state tracker.

        Args:
            position: Starting (x, y) coordinates in micrometers
            direction: Starting angle in degrees (0=right, 90=up, 180=left, 270=down)
        """
        self.last = position  # Current position (x, y)
        self.last_direction = direction  # Current direction in degrees
        self._port_stack = []  # For nested component tracking

    def move(self, distance: float, direction: Optional[float] = None):
        """
        Move the current position by distance in the specified direction.
        Mimics mask_maker's Structure.move() method.

        Args:
            distance: Distance to move in micrometers
            direction: Direction to move in degrees. If None, uses last_direction
        """
        if direction is None:
            direction = self.last_direction

        # Convert angle to radians
        theta = np.radians(direction)

        # Calculate new position
        dx = distance * np.cos(theta)
        dy = distance * np.sin(theta)

        self.last = (self.last[0] + dx, self.last[1] + dy)

    def to_port(self, name: str = 'current') -> Port:
        """
        Convert current state to a phidl Port object.

        Args:
            name: Name for the port

        Returns:
            Port object with current position and orientation
        """
        return Port(
            name=name,
            midpoint=self.last,
            orientation=self.last_direction,
            width=0  # Will be set by CPW components
        )

    def from_port(self, port: Port):
        """
        Update state from a phidl Port object.

        Args:
            port: Port to extract position and orientation from
        """
        self.last = tuple(port.midpoint)
        self.last_direction = port.orientation

    def save_state(self):
        """Save current state to stack (for nested component drawing)."""
        self._port_stack.append((self.last, self.last_direction))

    def restore_state(self):
        """Restore state from stack."""
        if self._port_stack:
            self.last, self.last_direction = self._port_stack.pop()


class TwoLayerManager:
    """
    Manages synchronized drawing on pin (conductor) and gap (ground) layers.

    Replicates mask_maker's pin_layer and gap_layer synchronization, ensuring
    that CPW features are correctly drawn on both layers with proper offsets.
    """

    def __init__(self, device: Optional[Device] = None, two_layer: bool = False):
        """
        Initialize two-layer manager.

        Args:
            device: phidl Device to draw into. If None, creates new Device.
            two_layer: If True, draw on both PIN and GAP layers. If False, only PIN layer.
        """
        self.device = device if device is not None else Device('two_layer')
        self.pin_state = StateTracker()
        self.gap_state = StateTracker()
        self.two_layer = two_layer

        # Keep states synchronized
        self._sync_states = True

    def add_cpw_straight(self, length: float, pinw: float, gapw: float,
                        layer_pin: int = LAYER_PIN, layer_gap: int = LAYER_GAP):
        """
        Add a straight CPW segment to both pin and gap layers.

        Args:
            length: Length of the segment in micrometers
            pinw: Pin (conductor) width in micrometers
            gapw: Gap width on each side in micrometers
            layer_pin: GDS layer for conductor
            layer_gap: GDS layer for ground/undercut

        Returns:
            Tuple of (pin_ref, gap_ref) - references to added geometry
        """
        position = self.pin_state.last
        direction = self.pin_state.last_direction

        # Calculate endpoint
        theta = np.radians(direction)
        end_pos = (
            position[0] + length * np.cos(theta),
            position[1] + length * np.sin(theta)
        )

        # Create polygons directly in the main device (no intermediate devices)
        # This allows automatic merging of adjacent segments

        theta = np.radians(direction)
        dx_along = length * np.cos(theta)
        dy_along = length * np.sin(theta)
        dx_perp = -np.sin(theta)  # Perpendicular direction
        dy_perp = np.cos(theta)

        # For optical (two_layer=False): only draw full width on PIN layer
        # For e-beam (two_layer=True): draw pin on PIN layer, gap on GAP layer

        if self.two_layer:
            # E-beam mode: draw separate geometries on PIN and GAP layers
            # Pin layer (conductor)
            if pinw > 0:
                pin_points = [
                    (position[0] - pinw/2 * dx_perp, position[1] - pinw/2 * dy_perp),
                    (position[0] + pinw/2 * dx_perp, position[1] + pinw/2 * dy_perp),
                    (end_pos[0] + pinw/2 * dx_perp, end_pos[1] + pinw/2 * dy_perp),
                    (end_pos[0] - pinw/2 * dx_perp, end_pos[1] - pinw/2 * dy_perp)
                ]
                self.device.add_polygon(pin_points, layer=layer_pin)

            # Gap layer (undercut - slightly larger than pin)
            gap_width = pinw + 2 * gapw
            gap_points = [
                (position[0] - gap_width/2 * dx_perp, position[1] - gap_width/2 * dy_perp),
                (position[0] + gap_width/2 * dx_perp, position[1] + gap_width/2 * dy_perp),
                (end_pos[0] + gap_width/2 * dx_perp, end_pos[1] + gap_width/2 * dy_perp),
                (end_pos[0] - gap_width/2 * dx_perp, end_pos[1] - gap_width/2 * dy_perp)
            ]
            self.device.add_polygon(gap_points, layer=layer_gap)
        else:
            # Optical mode: draw on PIN layer
            if gapw > 0:
                if pinw == 0:
                    # Case 1: Solid rectangle (pinw=0, gapw=width/2)
                    # Draw ONE solid bar of width 2*gapw
                    total_width = 2 * gapw
                    solid_points = [
                        (position[0] - total_width/2 * dx_perp, position[1] - total_width/2 * dy_perp),
                        (position[0] + total_width/2 * dx_perp, position[1] + total_width/2 * dy_perp),
                        (end_pos[0] + total_width/2 * dx_perp, end_pos[1] + total_width/2 * dy_perp),
                        (end_pos[0] - total_width/2 * dx_perp, end_pos[1] - total_width/2 * dy_perp)
                    ]
                    self.device.add_polygon(solid_points, layer=layer_pin)
                else:
                    # Case 2: Two striplines (pinw>0)
                    # Draw TWO separate rectangles with gap between them
                    left_center_offset = pinw/2 + gapw/2
                    left_points = [
                        (position[0] - (left_center_offset + gapw/2) * dx_perp,
                         position[1] - (left_center_offset + gapw/2) * dy_perp),
                        (position[0] - (left_center_offset - gapw/2) * dx_perp,
                         position[1] - (left_center_offset - gapw/2) * dy_perp),
                        (end_pos[0] - (left_center_offset - gapw/2) * dx_perp,
                         end_pos[1] - (left_center_offset - gapw/2) * dy_perp),
                        (end_pos[0] - (left_center_offset + gapw/2) * dx_perp,
                         end_pos[1] - (left_center_offset + gapw/2) * dy_perp)
                    ]
                    self.device.add_polygon(left_points, layer=layer_pin)

                    # Right stripline
                    right_center_offset = pinw/2 + gapw/2
                    right_points = [
                        (position[0] + (right_center_offset - gapw/2) * dx_perp,
                         position[1] + (right_center_offset - gapw/2) * dy_perp),
                        (position[0] + (right_center_offset + gapw/2) * dx_perp,
                         position[1] + (right_center_offset + gapw/2) * dy_perp),
                        (end_pos[0] + (right_center_offset + gapw/2) * dx_perp,
                         end_pos[1] + (right_center_offset + gapw/2) * dy_perp),
                        (end_pos[0] + (right_center_offset - gapw/2) * dx_perp,
                         end_pos[1] + (right_center_offset - gapw/2) * dy_perp)
                    ]
                    self.device.add_polygon(right_points, layer=layer_pin)

        refs = []

        # Update state
        self.pin_state.last = end_pos
        self.gap_state.last = end_pos

        return tuple(refs)

    def add_cpw_taper(self, length: float, start_pinw: float, stop_pinw: float,
                     start_gapw: float, stop_gapw: float,
                     layer_pin: int = LAYER_PIN, layer_gap: int = LAYER_GAP):
        """
        Add a tapered CPW segment to both pin and gap layers.

        Args:
            length: Length of the taper in micrometers
            start_pinw: Starting pin width
            stop_pinw: Ending pin width
            start_gapw: Starting gap width
            stop_gapw: Ending gap width
            layer_pin: GDS layer for conductor
            layer_gap: GDS layer for ground/undercut

        Returns:
            Tuple of (pin_ref, gap_ref)
        """
        position = self.pin_state.last
        direction = self.pin_state.last_direction

        # Calculate endpoint
        theta = np.radians(direction)
        end_pos = (
            position[0] + length * np.cos(theta),
            position[1] + length * np.sin(theta)
        )

        # Create trapezoid polygons directly in main device
        theta = np.radians(direction)
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        # Helper function to rotate and translate a point
        def transform_point(x_local, y_local):
            # Rotate by direction angle
            x_rot = x_local * cos_t - y_local * sin_t
            y_rot = x_local * sin_t + y_local * cos_t
            # Translate to position
            return (position[0] + x_rot, position[1] + y_rot)

        if self.two_layer:
            # E-beam mode: draw separate geometries on PIN and GAP layers
            # Pin layer taper
            if start_pinw > 0 or stop_pinw > 0:
                pin_points = [
                    transform_point(0, -start_pinw/2),
                    transform_point(length, -stop_pinw/2),
                    transform_point(length, stop_pinw/2),
                    transform_point(0, start_pinw/2)
                ]
                self.device.add_polygon(pin_points, layer=layer_pin)

            # Gap layer taper (undercut)
            start_gap_width = start_pinw + 2 * start_gapw
            stop_gap_width = stop_pinw + 2 * stop_gapw

            gap_points = [
                transform_point(0, -start_gap_width/2),
                transform_point(length, -stop_gap_width/2),
                transform_point(length, stop_gap_width/2),
                transform_point(0, start_gap_width/2)
            ]
            self.device.add_polygon(gap_points, layer=layer_gap)
        else:
            # Optical mode: draw on PIN layer
            if start_gapw > 0 or stop_gapw > 0:
                if start_pinw == 0 and stop_pinw == 0:
                    # Case 1: Solid tapered rectangle (pinw=0, use gapw)
                    start_total = 2 * start_gapw
                    stop_total = 2 * stop_gapw
                    solid_points = [
                        transform_point(0, -start_total/2),
                        transform_point(length, -stop_total/2),
                        transform_point(length, stop_total/2),
                        transform_point(0, start_total/2)
                    ]
                    self.device.add_polygon(solid_points, layer=layer_pin)
                else:
                    # Case 2: Two tapered striplines
                    start_left_offset = start_pinw/2 + start_gapw/2
                    stop_left_offset = stop_pinw/2 + stop_gapw/2

                    left_points = [
                        transform_point(0, -(start_left_offset + start_gapw/2)),
                        transform_point(0, -(start_left_offset - start_gapw/2)),
                        transform_point(length, -(stop_left_offset - stop_gapw/2)),
                        transform_point(length, -(stop_left_offset + stop_gapw/2))
                    ]
                    self.device.add_polygon(left_points, layer=layer_pin)

                    # Right stripline (tapered)
                    right_points = [
                        transform_point(0, (start_left_offset - start_gapw/2)),
                        transform_point(0, (start_left_offset + start_gapw/2)),
                        transform_point(length, (stop_left_offset + stop_gapw/2)),
                        transform_point(length, (stop_left_offset - stop_gapw/2))
                    ]
                    self.device.add_polygon(right_points, layer=layer_pin)
            elif start_pinw > 0 or stop_pinw > 0:
                # Case 3: Solid taper using pinw (gapw=0)
                solid_points = [
                    transform_point(0, -start_pinw/2),
                    transform_point(length, -stop_pinw/2),
                    transform_point(length, stop_pinw/2),
                    transform_point(0, start_pinw/2)
                ]
                self.device.add_polygon(solid_points, layer=layer_pin)

        refs = []

        # Update state (new position and widths become current)
        self.pin_state.last = end_pos
        self.gap_state.last = end_pos

        return tuple(refs)

    def add_cpw_bend(self, angle: float, radius: float, pinw: float, gapw: float,
                    segments: int = 60, layer_pin: int = LAYER_PIN,
                    layer_gap: int = LAYER_GAP):
        """
        Add a curved CPW bend to both pin and gap layers.

        Matches mask_maker's CPWBend behavior:
        - Positive angle = CCW (counter-clockwise)
        - Negative angle = CW (clockwise)
        - Properly handles arc center calculation
        - Updates position to end of arc

        Args:
            angle: Bend angle in degrees (positive = CCW, negative = CW)
            radius: Bend radius in micrometers
            pinw: Pin width
            gapw: Gap width
            segments: Number of segments for arc approximation
            layer_pin: GDS layer for conductor
            layer_gap: GDS layer for ground/undercut

        Returns:
            Tuple of (pin_ref, gap_ref)
        """
        # Handle zero angle case (mask_maker returns early)
        if angle == 0:
            return tuple()

        position = self.pin_state.last
        direction = self.pin_state.last_direction

        # Calculate arc center (matches mask_maker logic)
        # For CCW (positive): center is perpendicular to the left (direction + 90)
        # For CW (negative): center is perpendicular to the right (direction - 90)
        asign = 1 if angle > 0 else -1
        center_angle = direction + asign * 90
        center_theta = np.radians(center_angle)
        center = (
            position[0] + radius * np.cos(center_theta),
            position[1] + radius * np.sin(center_theta)
        )

        # Generate arc points
        arc_points = self._generate_arc_points(
            center=center,
            radius=radius,
            start_angle=direction - asign * 90,  # Radial angle to start point
            sweep_angle=abs(angle),
            segments=segments,
            ccw=(angle > 0)
        )

        # Add polygons directly to main device (no intermediate devices)
        refs = []

        if self.two_layer:
            # E-beam mode: draw separate geometries on PIN and GAP layers
            # Pin layer
            if pinw > 0:
                pin_path = self._extrude_path(arc_points, pinw)
                self.device.add_polygon(pin_path, layer=layer_pin)

            # Gap layer (undercut)
            gap_width = pinw + 2 * gapw
            gap_path = self._extrude_path(arc_points, gap_width)
            self.device.add_polygon(gap_path, layer=layer_gap)
        else:
            # Optical mode: draw on PIN layer
            if gapw > 0:
                if pinw == 0:
                    # Case 1: Solid arc (pinw=0)
                    # Draw ONE arc of width 2*gapw
                    total_width = 2 * gapw
                    solid_path = self._extrude_path(arc_points, total_width)
                    self.device.add_polygon(solid_path, layer=layer_pin)
                else:
                    # Case 2: Two concentric arcs (striplines)
                    # Inner arc (closer to center)
                    inner_radius = radius - (pinw/2 + gapw/2)
                    inner_arc_points = self._generate_arc_points(
                        center=center,
                        radius=inner_radius,
                        start_angle=direction - asign * 90,
                        sweep_angle=abs(angle),
                        segments=segments,
                        ccw=(angle > 0)
                    )
                    inner_path = self._extrude_path(inner_arc_points, gapw)
                    self.device.add_polygon(inner_path, layer=layer_pin)

                    # Outer arc (farther from center)
                    outer_radius = radius + (pinw/2 + gapw/2)
                    outer_arc_points = self._generate_arc_points(
                        center=center,
                        radius=outer_radius,
                        start_angle=direction - asign * 90,
                        sweep_angle=abs(angle),
                        segments=segments,
                        ccw=(angle > 0)
                    )
                    outer_path = self._extrude_path(outer_arc_points, gapw)
                    self.device.add_polygon(outer_path, layer=layer_pin)

        # Update state (matches mask_maker)
        new_direction = direction + angle
        # Rotate start point around center by the angle
        dx = position[0] - center[0]
        dy = position[1] - center[1]
        angle_rad = np.radians(angle)
        new_pos = (
            center[0] + dx * np.cos(angle_rad) - dy * np.sin(angle_rad),
            center[1] + dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
        )

        self.pin_state.last = new_pos
        self.pin_state.last_direction = new_direction
        self.gap_state.last = new_pos
        self.gap_state.last_direction = new_direction

        return tuple(refs)

    def _generate_arc_points(self, center: Tuple[float, float], radius: float,
                            start_angle: float, sweep_angle: float,
                            segments: int, ccw: bool = True) -> list:
        """
        Generate points along an arc.

        Args:
            center: Center point of the arc
            radius: Radius of the arc
            start_angle: Starting angle in degrees (radial angle from center)
            sweep_angle: Sweep angle in degrees (always positive)
            segments: Number of points to generate
            ccw: True for counter-clockwise, False for clockwise

        Returns:
            List of (x, y) points along the arc
        """
        angles = np.linspace(0, sweep_angle, segments)
        start_rad = np.radians(start_angle)

        points = []
        for a in angles:
            # For CW, subtract the angle; for CCW, add it
            angle_offset = np.radians(a) if ccw else -np.radians(a)
            angle_rad = start_rad + angle_offset
            x = center[0] + radius * np.cos(angle_rad)
            y = center[1] + radius * np.sin(angle_rad)
            points.append((x, y))

        return points

    def _extrude_path(self, centerline: list, width: float) -> list:
        """Extrude a centerline path to create a polygon with given width."""
        # Convert to numpy array
        points = np.array(centerline)

        # Calculate tangent vectors at each point
        tangents = np.diff(points, axis=0)
        tangents = np.vstack([tangents[0], tangents])  # Repeat first tangent

        # Normalize tangents
        norms = np.linalg.norm(tangents, axis=1, keepdims=True)
        tangents = tangents / (norms + 1e-10)

        # Calculate perpendicular vectors
        perps = np.column_stack([-tangents[:, 1], tangents[:, 0]])

        # Generate offset points
        offset = width / 2
        upper = points + offset * perps
        lower = points - offset * perps

        # Combine into closed polygon
        polygon = np.vstack([upper, lower[::-1]])

        return polygon.tolist()


class CPWSegment:
    """
    Abstract base class for CPW segment components.

    Provides common interface for straight, taper, and bend segments.
    """

    def __init__(self, layer_pin: int = LAYER_PIN, layer_gap: int = LAYER_GAP):
        """
        Initialize CPW segment.

        Args:
            layer_pin: GDS layer for conductor
            layer_gap: GDS layer for ground/undercut
        """
        self.layer_pin = layer_pin
        self.layer_gap = layer_gap
        self.device = Device(self.__class__.__name__)

    def get_device(self) -> Device:
        """Return the phidl Device."""
        return self.device


# Compatibility functions that mimic mask_maker API

def CPWStraight(structure, length: float, pinw: Optional[float] = None,
               gapw: Optional[float] = None):
    """
    Compatibility function for mask_maker's CPWStraight.

    Draws a straight CPW segment and updates the structure's state.

    Args:
        structure: Structure, StateTracker, or TwoLayerManager object
        length: Length of the segment
        pinw: Pin width (uses structure default if None)
        gapw: Gap width (uses structure default if None)
    """
    # Use defaults if not specified
    if pinw is None:
        pinw = getattr(structure, 'pinw', 10.0)
    if gapw is None:
        gapw = getattr(structure, 'gapw', 5.0)

    # Handle different structure types
    if isinstance(structure, Structure):
        # Check if this is a layer-specific structure (pin_layer or gap_layer)
        if hasattr(structure, '_target_gds_layer'):
            # Layer-specific: draw only on the target layer
            structure._manager.add_cpw_straight(length, pinw, gapw,
                                               layer_pin=structure._target_gds_layer,
                                               layer_gap=structure._target_gds_layer)
        else:
            # Normal structure: use global layer settings
            structure._manager.add_cpw_straight(length, pinw, gapw,
                                               layer_pin=LAYER_PIN,
                                               layer_gap=LAYER_GAP)
        # Update structure's state
        structure.last = structure._manager.pin_state.last
        structure.last_direction = structure._manager.pin_state.last_direction
    elif isinstance(structure, TwoLayerManager):
        structure.add_cpw_straight(length, pinw, gapw)
    elif isinstance(structure, StateTracker):
        # For standalone StateTracker, just update position
        structure.move(length)
    else:
        raise TypeError(f"Unsupported structure type: {type(structure)}")


def CPWLinearTaper(structure, length: float, start_pinw: float, stop_pinw: float,
                  start_gapw: float, stop_gapw: float):
    """
    Compatibility function for mask_maker's CPWLinearTaper.

    Draws a tapered CPW segment and updates the structure's state.

    Args:
        structure: Structure, StateTracker, or TwoLayerManager object
        length: Length of the taper
        start_pinw: Starting pin width
        stop_pinw: Ending pin width
        start_gapw: Starting gap width
        stop_gapw: Ending gap width
    """
    if isinstance(structure, Structure):
        # Check if this is a layer-specific structure
        if hasattr(structure, '_target_gds_layer'):
            # Layer-specific: draw only on the target layer
            structure._manager.add_cpw_taper(length, start_pinw, stop_pinw,
                                            start_gapw, stop_gapw,
                                            layer_pin=structure._target_gds_layer,
                                            layer_gap=structure._target_gds_layer)
        else:
            # Normal structure: use global layer settings
            structure._manager.add_cpw_taper(length, start_pinw, stop_pinw,
                                            start_gapw, stop_gapw,
                                            layer_pin=LAYER_PIN,
                                            layer_gap=LAYER_GAP)
        # Update structure's state and widths
        structure.last = structure._manager.pin_state.last
        structure.last_direction = structure._manager.pin_state.last_direction
        structure.pinw = stop_pinw
        structure.gapw = stop_gapw
    elif isinstance(structure, TwoLayerManager):
        structure.add_cpw_taper(length, start_pinw, stop_pinw,
                               start_gapw, stop_gapw)
        # Update current widths
        structure.device.pinw = stop_pinw
        structure.device.gapw = stop_gapw
    elif isinstance(structure, StateTracker):
        structure.move(length)
    else:
        raise TypeError(f"Unsupported structure type: {type(structure)}")


def CPWBend(structure, angle: float, pinw: Optional[float] = None,
           gapw: Optional[float] = None, radius: Optional[float] = None,
           polyarc: bool = True, segments: int = 60):
    """
    Compatibility function for mask_maker's CPWBend.

    Draws a curved CPW bend and updates the structure's state.
    Matches mask_maker behavior:
    - Returns early if angle == 0
    - Positive angle = CCW (counter-clockwise)
    - Negative angle = CW (clockwise)
    - polyarc parameter currently always uses polygon approximation

    Args:
        structure: Structure, StateTracker, or TwoLayerManager object
        angle: Bend angle in degrees (positive = CCW, negative = CW)
        pinw: Pin width (uses structure default if None)
        gapw: Gap width (uses structure default if None)
        radius: Bend radius (uses structure default if None)
        polyarc: If True, uses polygonal approximation (always True in phidl)
        segments: Number of segments for arc approximation
    """
    # Handle zero angle (mask_maker returns early)
    if angle == 0:
        return

    # Use defaults if not specified (matches mask_maker logic)
    if pinw is None:
        pinw = getattr(structure, 'pinw', 10.0)
    if gapw is None:
        gapw = getattr(structure, 'gapw', 5.0)
    if radius is None:
        # Try to get radius from structure or defaults
        radius = structure._get_default('radius', 50.0) if isinstance(structure, Structure) else getattr(structure, 'radius', 50.0)

    if isinstance(structure, Structure):
        # Check if this is a layer-specific structure
        if hasattr(structure, '_target_gds_layer'):
            # Layer-specific: draw only on the target layer
            structure._manager.add_cpw_bend(angle, radius, pinw, gapw, segments,
                                           layer_pin=structure._target_gds_layer,
                                           layer_gap=structure._target_gds_layer)
        else:
            # Normal structure: use default behavior
            structure._manager.add_cpw_bend(angle, radius, pinw, gapw, segments)
        # Update structure's state
        structure.last = structure._manager.pin_state.last
        structure.last_direction = structure._manager.pin_state.last_direction
    elif isinstance(structure, TwoLayerManager):
        structure.add_cpw_bend(angle, radius, pinw, gapw, segments)
    elif isinstance(structure, StateTracker):
        # For standalone StateTracker, update position and direction
        # Calculate new position by rotating around arc center
        asign = 1 if angle > 0 else -1
        center_angle = structure.last_direction + asign * 90
        center_theta = np.radians(center_angle)
        center = (
            structure.last[0] + radius * np.cos(center_theta),
            structure.last[1] + radius * np.sin(center_theta)
        )

        # Rotate start point around center
        dx = structure.last[0] - center[0]
        dy = structure.last[1] - center[1]
        angle_rad = np.radians(angle)
        new_pos = (
            center[0] + dx * np.cos(angle_rad) - dy * np.sin(angle_rad),
            center[1] + dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
        )

        structure.last = new_pos
        structure.last_direction = structure.last_direction + angle
    else:
        raise TypeError(f"Unsupported structure type: {type(structure)}")


# Convenience function for creating a new drawing context
def create_structure(position: Tuple[float, float] = (0, 0),
                    direction: float = 0,
                    pinw: float = 10.0,
                    gapw: float = 5.0,
                    radius: float = 50.0) -> TwoLayerManager:
    """
    Create a new TwoLayerManager with specified defaults.

    Args:
        position: Starting position
        direction: Starting direction in degrees
        pinw: Default pin width
        gapw: Default gap width
        radius: Default bend radius

    Returns:
        TwoLayerManager ready for drawing
    """
    manager = TwoLayerManager()
    manager.pin_state.last = position
    manager.pin_state.last_direction = direction
    manager.gap_state.last = position
    manager.gap_state.last_direction = direction

    # Store defaults
    manager.device.pinw = pinw
    manager.device.gapw = gapw
    manager.device.radius = radius

    return manager


# ============================================================================
# MASK_MAKER COMPATIBILITY CLASSES
# ============================================================================

class ChipDefaults:
    """
    Compatibility wrapper for mask_maker's ChipDefaults.
    Stores default parameters for chip design.
    """
    def __init__(self):
        # Default values matching mask_maker
        self.Q = 1000
        self.radius = 50
        self.segments = 6
        self.pinw_rsn = 2.0
        self.gapw_rsn = 8.5
        self.pinw = 1.5
        self.gapw = 1.0
        self.center_gapw = 1
        self.imp_rsn = 80.0
        self.solid = False


class Chip:
    """
    Compatibility wrapper for mask_maker's Chip class.
    Represents a GDS chip/die with multiple structures.
    """
    def __init__(self, name, author="", size=(7000, 1900), mask_id_loc=None,
                 chip_id_loc=None, textsize=(300, 300), two_layer=False, solid=False):
        """
        Initialize a chip.

        Args:
            name: Chip name
            author: Author name
            size: Chip size (width, height) in micrometers
            mask_id_loc: Location for mask ID label
            chip_id_loc: Location for chip ID label
            textsize: Text size for labels
            two_layer: If True, creates separate pin and gap layers
            solid: If True, uses solid fills
        """
        self.name = name
        self.author = author
        self.size = size
        self.mask_id_loc = mask_id_loc
        self.chip_id_loc = chip_id_loc
        self.textsize = textsize
        self.two_layer = two_layer
        self.solid = solid

        # Create main device
        self.device = Device(name)

        # Store entities for mask_maker compatibility
        self.entities = []

        # Convenience points
        self.midpt = (size[0]/2, size[1]/2)
        self.top_left = (0, size[1])
        self.top_right = size
        self.bottom_left = (0, 0)
        self.bottom_right = (size[0], 0)

    def append(self, entity):
        """Add an entity to the chip (mask_maker compatibility)."""
        self.entities.append(entity)
        # If entity is a phidl Device, add it as reference
        if isinstance(entity, Device):
            self.device << entity

    def label_chip(self, drawing=None, maskid=None, chipid=None, author=None,
                   offset=(0, 0), textsize=None):
        """
        Add text labels to chip (mask_maker compatibility).
        Currently simplified - full text rendering would need additional work.
        """
        if textsize is None:
            textsize = self.textsize

        # Store labels for later rendering
        if not hasattr(self, '_labels'):
            self._labels = []

        if chipid:
            self._labels.append({
                'text': chipid,
                'position': offset,
                'size': textsize
            })

        # In a full implementation, would use phidl's text rendering
        # For now, just store the label information

    def save(self, fname=None):
        """Save chip to GDS file."""
        if fname is None:
            fname = f"{self.name}.gds"

        # Merge all geometry before saving using boolean union
        self._merge_geometry()

        self.device.write_gds(fname)
        return fname

    def write_gds(self, fname):
        """Alias for save() for phidl compatibility."""
        return self.save(fname)

    def get_merged_device(self):
        """Get a merged version of the device for visualization."""
        self._merge_geometry()
        return self.device

    def _merge_geometry(self):
        """Merge all overlapping/touching polygons on the same layer."""
        # Try shapely first (most reliable)
        try:
            from shapely.geometry import Polygon, MultiPolygon
            from shapely.ops import unary_union

            polys_by_layer = self.device.get_polygons(by_spec=True)
            if not polys_by_layer:
                return

            merged_device = Device(f"{self.name}_merged")

            for layer_spec, polygons in polys_by_layer.items():
                if len(polygons) == 0:
                    continue

                try:
                    shapely_polys = [Polygon(poly) for poly in polygons if len(poly) >= 3]
                    if not shapely_polys:
                        continue

                    merged_shape = unary_union(shapely_polys)

                    if isinstance(merged_shape, Polygon):
                        coords = np.array(merged_shape.exterior.coords)
                        merged_device.add_polygon(coords, layer=layer_spec)
                    elif isinstance(merged_shape, MultiPolygon):
                        for geom in merged_shape.geoms:
                            coords = np.array(geom.exterior.coords)
                            merged_device.add_polygon(coords, layer=layer_spec)

                except Exception as e:
                    print(f"Warning: Could not merge layer {layer_spec}: {e}")
                    for poly in polygons:
                        merged_device.add_polygon(poly, layer=layer_spec)

            self.device = merged_device
            return

        except ImportError:
            pass

        # Try gdspy as fallback
        try:
            import gdspy

            # Flatten the device hierarchy first
            flat_device = self.device.flatten()

            # Get polygons by layer
            polys_by_layer = flat_device.get_polygons(by_spec=True)
            if not polys_by_layer:
                return

            merged_device = Device(f"{self.name}_merged")

            for layer_spec, polygons in polys_by_layer.items():
                if len(polygons) == 0:
                    continue

                try:
                    # Create gdspy polygons
                    gds_polys = [gdspy.Polygon(poly, layer=layer_spec[0], datatype=layer_spec[1])
                                for poly in polygons if len(poly) >= 3]

                    if not gds_polys:
                        continue

                    # Use gdspy boolean OR to merge
                    merged = gdspy.boolean(gds_polys, None, 'or', layer=layer_spec[0], datatype=layer_spec[1])

                    # Add back to device
                    if isinstance(merged, list):
                        for poly in merged:
                            merged_device.add_polygon(poly.polygons[0], layer=layer_spec)
                    else:
                        merged_device.add_polygon(merged.polygons[0], layer=layer_spec)

                except Exception as e:
                    print(f"Warning: Could not merge layer {layer_spec} with gdspy: {e}")
                    for poly in polygons:
                        merged_device.add_polygon(poly, layer=layer_spec)

            self.device = merged_device
            return

        except ImportError:
            pass

        print("Warning: Neither shapely nor gdspy available for geometry merging")
        print("Install shapely for best results: pip install shapely")

        # Replace the device with merged version
        self.device = merged_device


class Structure:
    """
    Compatibility wrapper for mask_maker's Structure class.
    Provides stateful drawing context.
    """
    def __init__(self, chip, start=(0, 0), direction=0, defaults=None, layer='0'):
        """
        Initialize a structure.

        Args:
            chip: Parent Chip object
            start: Starting position (x, y)
            direction: Starting direction in degrees
            defaults: ChipDefaults object with default parameters
            layer: Layer name
        """
        self.chip = chip
        self._last = start
        self._last_direction = direction
        self.layer = layer
        self.color = 0

        # Store defaults (can be ChipDefaults object or dict)
        if defaults is None:
            defaults = ChipDefaults()
        self.defaults = defaults

        # Set default width parameters (handle both object and dict)
        if isinstance(defaults, dict):
            self.pinw = defaults.get('pinw', 10.0)
            self.gapw = defaults.get('gapw', 5.0)
        else:
            self.pinw = getattr(defaults, 'pinw', 10.0)
            self.gapw = getattr(defaults, 'gapw', 5.0)

        # Create TwoLayerManager for drawing
        self._manager = TwoLayerManager(chip.device, two_layer=chip.two_layer)
        self._manager.pin_state.last = start
        self._manager.pin_state.last_direction = direction
        self._manager.gap_state.last = start
        self._manager.gap_state.last_direction = direction

        # For two-layer mode, create separate layer structures
        # BUT: Don't create sub-layers if we're already a layer structure (prevents recursion!)
        if chip.two_layer and layer not in ['pin', 'gap']:
            self.pin_layer = self._create_layer_structure('pin')
            self.gap_layer = self._create_layer_structure('gap')

            # Link states so they stay synchronized
            self.pin_layer._parent = self
            self.gap_layer._parent = self

    @property
    def last(self):
        """Get current position."""
        return self._last

    @last.setter
    def last(self, value):
        """Set current position and sync with manager."""
        self._last = value
        self._manager.pin_state.last = value
        self._manager.gap_state.last = value
        # Update layer states if two_layer
        if self.chip.two_layer and hasattr(self, 'pin_layer'):
            self.pin_layer._last = value
            self.gap_layer._last = value

    @property
    def last_direction(self):
        """Get current direction."""
        return self._last_direction

    @last_direction.setter
    def last_direction(self, value):
        """Set current direction and sync with manager."""
        self._last_direction = value
        self._manager.pin_state.last_direction = value
        self._manager.gap_state.last_direction = value
        # Update layer states if two_layer
        if self.chip.two_layer and hasattr(self, 'pin_layer'):
            self.pin_layer._last_direction = value
            self.gap_layer._last_direction = value

    def _create_layer_structure(self, layer_name):
        """Create a sub-structure for a specific layer."""
        # Create a shallow copy of chip with two_layer=False to prevent layer structures
        # from trying to draw on both layers
        class SingleLayerChip:
            def __init__(self, parent_chip, target_layer):
                self.device = parent_chip.device
                self.two_layer = False  # Layer structures only draw on one layer
                self.size = parent_chip.size
                self.name = parent_chip.name
                self._target_layer = target_layer  # Which GDS layer to use

        single_chip = SingleLayerChip(self.chip,
                                     LAYER_PIN if layer_name == 'pin' else LAYER_GAP)

        layer_struct = Structure(single_chip, start=self.last,
                                direction=self.last_direction,
                                defaults=self.defaults, layer=layer_name)
        layer_struct._is_layer = True
        layer_struct._layer_name = layer_name
        layer_struct._target_gds_layer = single_chip._target_layer
        return layer_struct

    def move(self, distance, direction=None):
        """
        Move the current position.

        Args:
            distance: Distance to move in micrometers
            direction: Direction to move (uses last_direction if None)
        """
        if direction is None:
            direction = self.last_direction

        theta = np.radians(direction)
        dx = distance * np.cos(theta)
        dy = distance * np.sin(theta)

        # Use property setter which will sync everything
        self.last = (self.last[0] + dx, self.last[1] + dy)

    def append(self, entity):
        """Add an entity to the structure."""
        self.chip.append(entity)

    def _get_default(self, key, fallback):
        """Get a default value from defaults (handles both dict and object)."""
        if isinstance(self.defaults, dict):
            return self.defaults.get(key, fallback)
        else:
            return getattr(self.defaults, key, fallback)

    @property
    def __dict__(self):
        """Override to provide attribute access (mask_maker compatibility)."""
        return {
            'pinw': self.pinw,
            'gapw': self.gapw,
            'last': self._last,
            'last_direction': self._last_direction,
            'radius': self._get_default('radius', 50.0)
        }


# ============================================================================
# GEOMETRY HELPER FUNCTIONS (mask_maker compatibility)
# ============================================================================

def rotate_pt(p, angle, center=(0, 0)):
    """
    Rotates point p=(x,y) about point center by CCW angle (in degrees).
    Matches mask_maker's rotate_pt function.
    """
    dx = p[0] - center[0]
    dy = p[1] - center[1]
    theta = np.radians(angle)
    return (
        center[0] + dx * np.cos(theta) - dy * np.sin(theta),
        center[1] + dx * np.sin(theta) + dy * np.cos(theta)
    )


def ang2pt(direction, distance):
    """
    Convert angle and distance to (x, y) offset.
    Matches mask_maker's ang2pt function.
    """
    theta = np.radians(direction)
    dx = distance * np.cos(theta)
    dy = distance * np.sin(theta)
    return (dx, dy)


def vadd(p1, p2):
    """Vector addition."""
    return (p1[0] + p2[0], p1[1] + p2[1])


def abs_rect(chip, p0, p1, layer=1):
    """
    Draw an absolute rectangle.
    Matches mask_maker's abs_rect function.
    """
    rect = pg.rectangle(size=(abs(p1[0]-p0[0]), abs(p1[1]-p0[1])), layer=layer)
    rect_ref = chip.device << rect
    rect_ref.move(origin=(0, 0), destination=(min(p0[0], p1[0]), min(p0[1], p1[1])))
    return rect_ref


# ============================================================================
# WAFER MASK CLASS (stub for compatibility)
# ============================================================================

class WaferMask:
    """
    Stub for mask_maker's WaferMask class.
    For full wafer-level layout, would need more comprehensive implementation.
    """
    def __init__(self, name, diameter=101600, flat_angle=270, flat_distance=48200,
                 wafer_padding=2500, chip_size=(1600, 25950), dicing_border=200,
                 etchtype=False, wafer_edge=True, dashed_dicing_border=80,
                 ndashes=2, dice_corner=False, square_arr=False):
        """Initialize wafer mask (simplified)."""
        self.name = name
        self.diameter = diameter
        self.chip_size = chip_size
        self.chips = []

        print(f"WaferMask created: {name}")
        print(f"Chip size: {chip_size}")

    def add_chip(self, chip, layer=1, label=True, save_folder=None):
        """
        Add a chip to the wafer.
        Returns the saved filename.
        """
        self.chips.append(chip)

        # Save chip as GDS (phidl native format)
        if save_folder:
            fname = f"{save_folder}\\{self.name}-{chip.name}.gds"
        else:
            fname = f"{self.name}-{chip.name}.gds"

        chip.save(fname)
        return fname

    def save(self, name=None):
        """Save wafer mask with all chips as GDS."""
        if name is None:
            name = f"{self.name}_wafer.gds"

        # Ensure .gds extension
        if not name.endswith('.gds'):
            name = name.replace('.dxf', '.gds') if '.dxf' in name else name + '.gds'

        # Create a wafer-level device
        wafer = Device(f"{self.name}_wafer")

        # Add all chips to the wafer
        # For now, just stack them or place them in a simple grid
        # In a full implementation, would use proper wafer layout
        for i, chip in enumerate(self.chips):
            ref = wafer << chip.device
            # Simple positioning - just offset each chip
            # In production, would use proper wafer coordinates
            ref.movex(i * (self.chip_size[0] + 500))

        # Merge geometry before saving
        if hasattr(wafer, 'flatten'):
            wafer = wafer.flatten()

        # Save the wafer as GDS
        wafer.write_gds(name)
        print(f"✅ Wafer mask saved to: {name}")
        return name


if __name__ == '__main__':
    # Simple test
    print("phidl_bridge module loaded successfully")

    # Create a test structure
    manager = create_structure(position=(0, 0), direction=0)
    print(f"Initial state: position={manager.pin_state.last}, direction={manager.pin_state.last_direction}")

    # Draw a simple CPW
    manager.add_cpw_straight(100, pinw=10, gapw=5)
    print(f"After straight: position={manager.pin_state.last}, direction={manager.pin_state.last_direction}")

    # Add a bend
    manager.add_cpw_bend(90, radius=50, pinw=10, gapw=5)
    print(f"After bend: position={manager.pin_state.last}, direction={manager.pin_state.last_direction}")

    # Save test output
    manager.device.write_gds('test_phidl_bridge.gds')
    print("Test GDS saved to: test_phidl_bridge.gds")
