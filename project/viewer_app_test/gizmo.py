import numpy as np
import pyvista as pv

from .config import (
    AXIS_VECTORS,
    AXIS_COLORS,
    GIZMO_LENGTH,
    GIZMO_REFERENCE_DISTANCE,
)


class Gizmo:
    """
    Zeichnet und verwaltet die drei Achsen-Pfeile der aktuellen
    Auswahl. Kennt weder SceneManager noch Interaction-Logik -
    nur "zeig dies an dieser Stelle in dieser Größe".
    """

    def __init__(self, plotter):
        self._plotter = plotter
        self._actors = []
        self._axis_by_actor = {}

    @property
    def is_visible(self):
        return bool(self._actors)

    def axis_for(self, actor):
        """
        Liefert (axis_name, axis_vector), falls `actor` einer der
        Gizmo-Pfeile ist, sonst None.
        """
        return self._axis_by_actor.get(actor)

    def show(self, center):
        self.remove()

        for axis_name, axis_vector in AXIS_VECTORS.items():
            arrow_mesh = pv.Arrow(
                start=(0, 0, 0),
                direction=tuple(axis_vector),
                scale=GIZMO_LENGTH,
            )

            arrow_actor = self._plotter.add_mesh(
                arrow_mesh,
                color=AXIS_COLORS[axis_name],
                name=f"gizmo_{axis_name}",
                lighting=False,
            )
            arrow_actor.SetPosition(*center)

            self._actors.append(arrow_actor)
            self._axis_by_actor[arrow_actor] = (axis_name, axis_vector)

    def update_size(self, center, camera_position):
        if not self._actors:
            return

        distance = np.linalg.norm(camera_position - center)
        scale = distance / GIZMO_REFERENCE_DISTANCE

        for actor in self._actors:
            actor.SetScale(scale, scale, scale)
            actor.SetPosition(*center)

    def move(self, movement):
        for actor in self._actors:
            position = np.array(actor.GetPosition(), dtype=float)
            actor.SetPosition(*(position + movement))

    def remove(self):
        for actor in self._actors:
            self._plotter.remove_actor(actor, render=False)

        self._actors = []
        self._axis_by_actor = {}
