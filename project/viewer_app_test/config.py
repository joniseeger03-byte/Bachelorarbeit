import numpy as np

# ==========================================================
# Gizmo
# ==========================================================

AXIS_VECTORS = {
    "x": np.array([1.0, 0.0, 0.0]),
    "y": np.array([0.0, 1.0, 0.0]),
    "z": np.array([0.0, 0.0, 1.0]),
}

AXIS_COLORS = {
    "x": "red",
    "y": "green",
    "z": "blue",
}

GIZMO_LENGTH = 1.0
GIZMO_REFERENCE_DISTANCE = 10.0

# ==========================================================
# Auswahl / Objekte
# ==========================================================

SELECTION_COLOR = (0.0, 1.0, 0.0)

BODYSCAN_COLOR = "tan"
SMPL_COLOR = "lightblue"
SMPLX_COLOR = "orchid"

# ==========================================================
# Kamera
# ==========================================================

CLIP_NEAR = 0.01
CLIP_FAR = 10000.0

PAN_SPEED = 0.001
ORBIT_SPEED = 0.5
ZOOM_IN_FACTOR = 0.9
ZOOM_OUT_FACTOR = 1.1

# ==========================================================
# Objekt-Bewegung
# ==========================================================

#freie Verschiebung nutzt eine exakte perspektivische Rückprojektion 
# statt eines festen Geschwindigkeitsfaktors - Punkt bleibt exakt 
# unter dem Mauszeiger, unabhängig von Zoom/Objektgröße/Entfernung.
DEPTH_MOVE_SPEED = 0.01

# ==========================================================
# Objekt-Skalierung
# ==========================================================

SCALE_STEP_UP = 1.05
SCALE_STEP_DOWN = 0.95

MIN_SCALE = 0.005
MAX_SCALE = 50.0

# ==========================================================
# Landmarks
# ==========================================================

LANDMARK_LABELS = [
    "head_top",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

# ==========================================================
# Marker
# ==========================================================

MARKER_COLOR = "yellow"
# Fester Radius ergibt bei unterschiedlich großen Objekten (Scan vs.
# SMPL vs. Testkörper) unpassende Marker-Größen. Stattdessen wird der
# Radius beim Setzen relativ zur Bounding-Box-Diagonale des jeweiligen
# Zielobjekts berechnet (siehe LandmarkManager._proportional_radius).
MARKER_RADIUS_RATIO = 0.015
MARKER_MIN_RADIUS = 0.003
MARKER_MAX_RADIUS = 0.05

# ==========================================================
# Transparenz (zum Platzieren innenliegender Marker)
# ==========================================================

OPAQUE_OPACITY = 1.0
TRANSPARENT_OPACITY = 0.35

# ==========================================================
# Einheiten-Umrechnung beim Import
# ==========================================================

MM_TO_M = 0.001

# Referenz-Körperhöhe (Meter) als Fallback, falls beim Import einer
# Datei mit unbekannter Skala noch kein anderes Objekt geladen ist.
# Entspricht ungefähr der SMPL-Neutral-Körpergröße.
DEFAULT_REFERENCE_HEIGHT = 1.66

# Welche Mesh-Achse die "Höhe" (vertikal) repräsentiert.
# 0 = X, 1 = Y, 2 = Z - anhand der Scan-/SMPL-Diagnose bestätigt: Y.
HEIGHT_AXIS = 1

UNIT_MILLIMETERS = "mm"
UNIT_METERS = "m"
UNIT_UNKNOWN = "unknown"