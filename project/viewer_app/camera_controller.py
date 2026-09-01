import numpy as np

from .config import (
    CLIP_NEAR,
    CLIP_FAR,
    PAN_SPEED,
    ORBIT_SPEED,
    ZOOM_IN_FACTOR,
    ZOOM_OUT_FACTOR,
)


class CameraController:
    """
    Kapselt sämtliche Kamera-Operationen (Pan, Orbit, Zoom, Clipping,
    Weltkoordinaten -> Bildschirm). Rendert bewusst NICHT selbst -
    das entscheidet der Aufrufer (siehe InteractionController),
    damit bei zusammengesetzten Aktionen nicht mehrfach gerendert wird.
    """

    def __init__(self, plotter):
        self._plotter = plotter

    @property
    def camera(self):
        return self._plotter.camera

    @property
    def position(self):
        return np.array(self.camera.GetPosition(), dtype=float)

    def set_clipping_range(self):
        self.camera.SetClippingRange(CLIP_NEAR, CLIP_FAR)

    def view_vectors(self):
        """Normalisierte (view, up, right) Vektoren der aktuellen Kamera."""
        position = self.position
        focal = np.array(self.camera.GetFocalPoint(), dtype=float)
        up = np.array(self.camera.GetViewUp(), dtype=float)

        view = focal - position
        view /= np.linalg.norm(view)
        up = up / np.linalg.norm(up)

        right = np.cross(view, up)
        right /= np.linalg.norm(right)

        return view, up, right

    def pan(self, dx, dy):
        _, up, right = self.view_vectors()

        position = self.position
        focal = np.array(self.camera.GetFocalPoint(), dtype=float)

        distance = np.linalg.norm(focal - position)
        scale = distance * PAN_SPEED

        movement = (-right * dx + up * dy) * scale

        self.camera.SetPosition(*(position + movement))
        self.camera.SetFocalPoint(*(focal + movement))
        self.set_clipping_range()

    def orbit(self, dx, dy):
        self.camera.Azimuth(-dx * ORBIT_SPEED)
        self.camera.Elevation(dy * ORBIT_SPEED)
        self.camera.OrthogonalizeViewUp()
        self.set_clipping_range()

    def zoom(self, wheel_delta):
        factor = ZOOM_IN_FACTOR if wheel_delta > 0 else ZOOM_OUT_FACTOR

        position = self.position
        focal = np.array(self.camera.GetFocalPoint(), dtype=float)
        direction = focal - position

        self.camera.SetPosition(*(focal - direction * factor))
        self.set_clipping_range()

    def screen_delta_to_world(self, dx, dy, reference_point):
        """
        Rechnet eine Bildschirm-Pixel-Bewegung (dx, dy) exakt in eine
        Raum-Verschiebung um, bezogen auf die Tiefe von
        `reference_point`-Objekten. Dadurch bleibt der gezogene Punkt exakt
        unter dem Mauszeiger - im Gegensatz zu einem festen
        Geschwindigkeitsfaktor, der bei unterschiedlicher Entfernung/
        Objektgröße zu schnell oder zu langsam wirkt.
        """
        _, up, right = self.view_vectors()

        viewport_height = self._plotter.interactor.GetSize()[1]

        if viewport_height <= 0:
            return np.zeros(3)

        if self.camera.GetParallelProjection():
            # Orthografische Kamera: Weltgröße pro Pixel ist konstant,
            # unabhängig von der Entfernung.
            world_per_pixel = (2.0 * self.camera.GetParallelScale()) / viewport_height
        else:
            # Perspektivische Kamera (Standardfall): Weltgröße pro
            # Pixel hängt von der Entfernung zum gezogenen Punkt ab.
            distance = np.linalg.norm(
                np.array(reference_point, dtype=float) - self.position
            )
            view_angle_rad = np.radians(self.camera.GetViewAngle())
            world_per_pixel = (
                2.0 * distance * np.tan(view_angle_rad / 2.0)
            ) / viewport_height

        return (right * dx - up * dy) * world_per_pixel


    def world_to_display(self, point):
        renderer = self._plotter.renderer

        renderer.SetWorldPoint(point[0], point[1], point[2], 1.0)
        renderer.WorldToDisplay()

        return np.array(renderer.GetDisplayPoint()[:2], dtype=float)
