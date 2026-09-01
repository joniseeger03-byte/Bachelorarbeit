import numpy as np

from .config import MAX_SCALE, MIN_SCALE

class SceneObject:
    """
    Wrapt einen einzelnen VTK/PyVista-Actor zusammen mit den Daten,
    die für Auswahl-Highlighting und Manipulation nötig sind.

    Kennt absichtlich nichts von Gizmo, Kamera oder Qt-Events -
    reine Datenhaltung + einfache Transform-Operationen.
    """

    def __init__(self, actor, original_color):
        self.actor = actor
        self.original_color = original_color

    @property
    def center(self):
        """
        Mittelpunkt in Weltkoordinaten = Position + Origin.

        WICHTIG: Origin wird beim Laden auf den geometrischen
        Mittelpunkt des Meshes gesetzt (siehe SceneManager),
        damit Rotationen um das Objekt selbst statt um den
        Weltursprung erfolgen.
        """
        position = np.array(self.actor.GetPosition(), dtype=float)
        origin = np.array(self.actor.GetOrigin(), dtype=float)
        return position + origin

    def highlight(self, color):
        self.actor.GetProperty().SetColor(*color)

    def restore_color(self):
        self.actor.GetProperty().SetColor(*self.original_color)

    def move(self, movement):
        self.actor.AddPosition(*movement)

    def rotate(self, dx, dy):
        self.actor.RotateY(dx)
        self.actor.RotateX(dy)

    def scale_by(self,factor):
        current = np.array(self.actor.GetScale(), dtype=float)
        new_scale= np.clip(current * factor, MIN_SCALE, MAX_SCALE)
        self.actor.SetScale(*new_scale)

    def toggle_transparency(self):
        from .config import OPAQUE_OPACITY, TRANSPARENT_OPACITY

        prop = self.actor.GetProperty()
        is_transparent = prop.GetOpacity() < 1.0
        prop.SetOpacity(OPAQUE_OPACITY if is_transparent else TRANSPARENT_OPACITY)