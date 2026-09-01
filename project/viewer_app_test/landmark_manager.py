import numpy as np
import vtk
import pyvista as pv

from .config import MARKER_COLOR, MARKER_RADIUS


class LandmarkManager:
    """
    Verwaltet benannte 3D-Marker (z.B. 'left_elbow') je Objekt-Slot.

    Marker werden relativ zum Objekt gespeichert (als Punkt im
    unverformten Koordinatensystem des Meshes zum Zeitpunkt der
    Platzierung), nicht als feste Weltkoordinate. Dadurch "kleben"
    sie am Objekt und folgen automatisch Verschiebung, Rotation UND
    Skalierung - dafür muss nach jeder Transformation
    update_positions_for_slot() aufgerufen werden (siehe SceneManager).
    """

    def __init__(self, plotter):
        self._plotter = plotter
        self._markers = {}       # (slot, label) -> {"actor": actor, "local_point": np.array}
        self._actor_lookup = {}  # actor -> (slot, label)

    def add_marker(self, slot, label, world_position, actor):
        self.remove_marker(slot, label)

        local_point = self._world_to_local(world_position, actor)

        sphere = pv.Sphere(radius=MARKER_RADIUS)
        marker_actor = self._plotter.add_mesh(
            sphere,
            color=MARKER_COLOR,
            name=f"marker_{slot}_{label}",
        )
        marker_actor.SetPosition(*world_position)

        self._markers[(slot, label)] = {
            "actor": marker_actor,
            "local_point": local_point,
        }
        self._actor_lookup[marker_actor] = (slot, label)

    def remove_marker(self, slot, label):
        entry = self._markers.pop((slot, label), None)

        if entry is None:
            return

        self._actor_lookup.pop(entry["actor"], None)
        self._plotter.remove_actor(entry["actor"], render=False)

    def label_for_actor(self, actor):
        return self._actor_lookup.get(actor)

    def world_position(self, slot, label):
        entry = self._markers.get((slot, label))

        if entry is None:
            return None

        return np.array(entry["actor"].GetPosition(), dtype=float)

    def all_marker_actors(self):
        """Alle aktuell existierenden Marker-Actors, unabhängig vom Slot."""
        return [entry["actor"] for entry in self._markers.values()]

    def update_positions_for_slot(self, slot, actor):
        """
        Berechnet die Weltposition aller Marker dieses Slots aus dem
        gespeicherten lokalen Punkt + der AKTUELLEN Actor-Matrix neu.
        Muss nach jeder Bewegung/Rotation/Skalierung aufgerufen werden.
        """
        for (marker_slot, _label), entry in self._markers.items():
            if marker_slot != slot:
                continue

            world_position = self._local_to_world(entry["local_point"], actor)
            entry["actor"].SetPosition(*world_position)

    def move_marker(self, slot, label, movement):
        entry = self._markers.get((slot, label))

        if entry is None:
            return

        entry["actor"].AddPosition(*movement)

    def finalize_marker_position(self, slot, label, actor):
        """
        Verankert den Marker nach einem manuellen Drag neu am Objekt:
        der aktuelle Weltpunkt wird relativ zur AKTUELLEN Actor-Matrix
        als neuer 'local_point' gespeichert. Ohne das würde der Marker
        bei der nächsten Objekt-Transformation auf seine ursprüngliche
        (vor dem Drag gültige) relative Position zurückspringen.
        """
        entry = self._markers.get((slot, label))

        if entry is None:
            return

        world_position = np.array(entry["actor"].GetPosition(), dtype=float)
        entry["local_point"] = self._world_to_local(world_position, actor)


    def world_positions_for_slot(self, slot):
        """dict: label -> aktuelle Weltposition (np.array) - Eingabe fürs Fitting."""
        return {
            marker_label: np.array(entry["actor"].GetPosition(), dtype=float)
            for (marker_slot, marker_label), entry in self._markers.items()
            if marker_slot == slot
        }

    def clear_for_slot(self, slot):
        labels = [
            marker_label
            for (marker_slot, marker_label) in list(self._markers.keys())
            if marker_slot == slot
        ]
        for label in labels:
            self.remove_marker(slot, label)

    # ------------------------------------------------------------
    # Transform-Hilfsfunktionen
    #
    # Die Actor-Matrix von VTK kombiniert Position, Origin,
    # Rotation und Scale bereits vollständig in einer 4x4-Matrix.
    # Ein Weltpunkt lässt sich damit in "lokale" (unverformte)
    # Koordinaten umrechnen und später wieder zurück - unabhängig
    # davon, wie sich die Matrix danach verändert.
    # ------------------------------------------------------------

    @staticmethod
    def _world_to_local(world_position, actor):
        inverse = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Invert(actor.GetMatrix(), inverse)
        return LandmarkManager._apply_matrix(inverse, world_position)

    @staticmethod
    def _local_to_world(local_point, actor):
        return LandmarkManager._apply_matrix(actor.GetMatrix(), local_point)

    @staticmethod
    def _apply_matrix(matrix, point):
        homogeneous = [point[0], point[1], point[2], 1.0]
        result = [0.0, 0.0, 0.0, 0.0]
        matrix.MultiplyPoint(homogeneous, result)
        return np.array(result[:3], dtype=float)