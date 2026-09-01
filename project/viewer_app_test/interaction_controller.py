import numpy as np
import vtk
from PySide6.QtCore import Qt

from .interaction_mode import InteractionMode
from .config import DEPTH_MOVE_SPEED


class InteractionController:
    """
    Einziger Ort, an dem Maus-/Tastatur-Events interpretiert werden.
    Delegiert die eigentliche Arbeit an SceneManager und
    CameraController und rendert danach genau einmal pro Event.
    """

    def __init__(self, plotter, scene_manager, camera_controller, on_marker_point_picked=None):
        self._plotter = plotter
        self._scene = scene_manager
        self._camera = camera_controller
        self._on_marker_point_picked = on_marker_point_picked

        self._picker = vtk.vtkPropPicker()

        # vtkCellPicker statt vtkPropPicker für Marker: liefert über
        # GetPickPosition() den exakten 3D-Punkt auf der Mesh-
        # Oberfläche, nicht nur den getroffenen Actor.
        self._marker_picker = vtk.vtkCellPicker()
        self._marker_picker.SetTolerance(0.0005)

        # Separater Picker, der AUSSCHLIESSLICH gegen die Marker-Kugeln
        # testet (Körper-Mesh wird komplett ignoriert). Nötig, weil ein
        # Marker, der unter die Oberfläche geschoben wurde, sonst vom
        # davor liegenden Mesh "verdeckt" bliebe - unabhängig von
        # dessen Transparenz, da diese die Tiefenwerte nicht verändert.
        self._marker_only_picker = vtk.vtkCellPicker()
        self._marker_only_picker.SetTolerance(0.0005)

        self._mode = InteractionMode.NONE
        self._last_pos = None
        self._gizmo_axis_vector = None
        self._dragging_marker = None  # (slot, label) während DRAG_MARKER

        self._connect_events()

    def _connect_events(self):
        interactor = self._plotter.interactor

        interactor.mousePressEvent = self.mouse_press
        interactor.mouseMoveEvent = self.mouse_move
        interactor.mouseReleaseEvent = self.mouse_release
        interactor.wheelEvent = self.mouse_wheel
        interactor.keyPressEvent = self.key_press

        # Nötig, damit der Interactor Tastatur-Events (z.B. Escape)
        # überhaupt empfängt.
        interactor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------
    # Picking
    # ------------------------------------------------------------

    def _pick_actor(self, x, y):
        # vtkPropPicker: pixelgenau, keine Toleranz.
        height = self._plotter.interactor.GetSize()[1]
        self._picker.Pick(x, height - y, 0, self._plotter.renderer)
        return self._picker.GetActor()

    def _pick_marker_actor(self, x, y):
        marker_actors = self._scene.landmarks.all_marker_actors()

        if not marker_actors:
            return None

        # Pick-Liste bei jedem Aufruf neu aufbauen, da sich Marker
        # jederzeit ändern können (hinzugefügt/entfernt).
        self._marker_only_picker.InitializePickList()
        for marker_actor in marker_actors:
            self._marker_only_picker.AddPickList(marker_actor)
        self._marker_only_picker.PickFromListOn()

        height = self._plotter.interactor.GetSize()[1]
        self._marker_only_picker.Pick(x, height - y, 0, self._plotter.renderer)

        return self._marker_only_picker.GetActor()

    def _place_marker(self, event):
        x = int(event.position().x())
        y = int(event.position().y())
        height = self._plotter.interactor.GetSize()[1]

        self._marker_picker.Pick(x, height - y, 0, self._plotter.renderer)
        actor = self._marker_picker.GetActor()

        if actor is None or not self._scene.is_selectable(actor):
            return

        slot = self._scene.slot_for_actor(actor)
        position = np.array(self._marker_picker.GetPickPosition(), dtype=float)

        if self._on_marker_point_picked is not None:
            self._on_marker_point_picked(slot, position)

    def _remove_marker(self, event):
        x = int(event.position().x())
        y = int(event.position().y())

        actor = self._pick_marker_actor(x, y)

        if actor is None:
            return

        self._scene.remove_marker_at_actor(actor)

    # ------------------------------------------------------------
    # Maus-Events
    # ------------------------------------------------------------

    def mouse_press(self, event):
        self._last_pos = event.position()
        self._mode = InteractionMode.NONE
        self._gizmo_axis_vector = None

        button = event.button()

        ctrl_held = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

        # STRG + LINKS auf einem VORHANDENEN Marker -> Marker verschieben
        # STRG + LINKS auf der Objektoberfläche -> neuen Marker setzen
        if ctrl_held and button == Qt.MouseButton.LeftButton:
            x = int(event.position().x())
            y = int(event.position().y())

            marker_actor = self._pick_marker_actor(x, y)
            marker_hit = (
                self._scene.marker_hit_at(marker_actor)
                if marker_actor is not None
                else None
            )

            if marker_hit is not None:
                self._dragging_marker = marker_hit
                self._mode = InteractionMode.DRAG_MARKER
            else:
                self._place_marker(event)

            event.accept()
            return

        # STRG + RECHTS -> vorhandenen Marker entfernen
        if ctrl_held and button == Qt.MouseButton.RightButton:
            self._remove_marker(event)
            event.accept()
            return

        # MITTLERE MAUSTASTE -> Kamera schwenken (kein Picking nötig)
        if button == Qt.MouseButton.MiddleButton:
            self._mode = InteractionMode.PAN
            event.accept()
            return

        x = int(event.position().x())
        y = int(event.position().y())
        actor = self._pick_actor(x, y)

        gizmo_hit = self._scene.gizmo.axis_for(actor)

        # GIZMO-PFEIL GETROFFEN (nur linke Maustaste: Verschieben
        # entlang genau einer Achse)
        if gizmo_hit is not None and button == Qt.MouseButton.LeftButton:
            _, axis_vector = gizmo_hit
            self._gizmo_axis_vector = axis_vector
            self._mode = InteractionMode.DRAG_AXIS
            event.accept()
            return

        # OBJEKT GETROFFEN
        if self._scene.is_selectable(actor):
            self._scene.select(actor)

            if button == Qt.MouseButton.LeftButton:
                self._mode = InteractionMode.DRAG_FREE
            elif button == Qt.MouseButton.RightButton:
                self._mode = InteractionMode.ROTATE

            event.accept()
            return

        # HINTERGRUND GETROFFEN
        if button == Qt.MouseButton.LeftButton:
            self._scene.deselect()
            self._mode = InteractionMode.ORBIT

        # Rechtsklick auf den Hintergrund: bewusst keine Wirkung,
        # damit "rechts = drehen" ausschließlich für Objekte gilt.
        event.accept()

    def mouse_move(self, event):
        if self._last_pos is None:
            return

        current_pos = event.position()
        dx = current_pos.x() - self._last_pos.x()
        dy = current_pos.y() - self._last_pos.y()

        handlers = {
            InteractionMode.PAN: lambda: self._camera.pan(dx, dy),
            InteractionMode.ORBIT: lambda: self._camera.orbit(dx, dy),
            InteractionMode.DRAG_AXIS: lambda: self._drag_axis(dx, dy),
            InteractionMode.ROTATE: lambda: self._scene.rotate_selected(dx, dy),
            InteractionMode.DRAG_FREE: lambda: self._drag_free(dx, dy, event),
            InteractionMode.DRAG_MARKER: lambda: self._drag_marker(dx, dy, event),
        }

        handler = handlers.get(self._mode)

        if handler is not None:
            handler()
            self._plotter.render()

        self._last_pos = current_pos
        event.accept()

    def mouse_release(self, event):
        if self._mode == InteractionMode.DRAG_MARKER and self._dragging_marker is not None:
            slot, label = self._dragging_marker
            self._scene.finalize_marker_drag(slot, label)

        self._mode = InteractionMode.NONE
        self._gizmo_axis_vector = None
        self._dragging_marker = None
        self._last_pos = None
        event.accept()

    def mouse_wheel(self, event):

        scale_requested = (
            self._scene.selected is not None
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        )

        if scale_requested:
            self._scene.scale_selected(event.angleDelta().y())
        else:
            self._camera.zoom(event.angleDelta().y())


        self._scene.refresh_gizmo_size()
        self._plotter.render()
        event.accept()

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._scene.deselect()
        elif event.key() == Qt.Key.Key_T:
            self._scene.toggle_transparency_selected()
            self._plotter.render()
        event.accept()

    # ------------------------------------------------------------
    # Bewegungs-Logik, die mehr als einen einzeiligen Delegate-Call
    # braucht
    # ------------------------------------------------------------

    def _drag_free(self, dx, dy, event):
        # SHIFT + LINKS -> Bewegung in Blickrichtung (Tiefe)
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            view, _, _ = self._camera.view_vectors()
            movement = view * (-dy * DEPTH_MOVE_SPEED)
        # LINKS -> Bewegung in der Bildschirmebene, exakt unter dem
        # Mauszeiger (siehe CameraController.screen_delta_to_world)
        else:
            reference_point = self._scene.selected.center
            movement = self._camera.screen_delta_to_world(dx, dy, reference_point)

        self._scene.move_selected(movement)

    def _drag_marker(self, dx, dy, event):
        if self._dragging_marker is None:
            return

        slot, label = self._dragging_marker
        reference_point = self._scene.marker_world_position(slot, label)

        if reference_point is None:
            return

        # SHIFT + ZIEHEN -> Marker in Blickrichtung verschieben (Tiefe)
        # -> so bekommt man den Marker ins Objektinnere (z.B. auf die
        # anatomische Gelenkmitte statt nur auf die Oberfläche).
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            view, _, _ = self._camera.view_vectors()
            movement = view * (-dy * DEPTH_MOVE_SPEED)
        # Exakt unter dem Mauszeiger, unabhängig von Objektgröße/Zoom.
        else:
            movement = self._camera.screen_delta_to_world(dx, dy, reference_point)

        self._scene.move_marker(slot, label, movement)


    def _drag_axis(self, dx, dy):
        if self._scene.selected is None or self._gizmo_axis_vector is None:
            return

        center = self._scene.selected.center
        axis = self._gizmo_axis_vector

        # Die 3D-Achse ins Bildschirmkoordinatensystem projizieren.
        # p1 - p0 ergibt die Richtung, in der ein Weltschritt von
        # 1.0 entlang der Achse auf dem Bildschirm erscheint.
        p0 = self._camera.world_to_display(center)
        p1 = self._camera.world_to_display(center + axis)

        # VTKs Display-Y läuft von unten nach oben, Qt-Events laufen
        # von oben nach unten -> Y invertieren.
        screen_axis = np.array([p1[0] - p0[0], -(p1[1] - p0[1])])
        length_sq = np.dot(screen_axis, screen_axis)

        # Achse zeigt (fast) genau zur Kamera bzw. von ihr weg ->
        # auf dem Bildschirm nicht als Linie sichtbar, Ziehen nicht
        # sinnvoll abbildbar.
        if length_sq < 1e-6:
            return

        mouse_delta = np.array([dx, dy])
        t = np.dot(mouse_delta, screen_axis) / length_sq

        self._scene.move_selected(axis * t)
