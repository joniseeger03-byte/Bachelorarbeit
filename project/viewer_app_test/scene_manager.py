import pyvista as pv

from .scene_object import SceneObject
from .gizmo import Gizmo
from .landmark_manager  import LandmarkManager
from .config import (
    SELECTION_COLOR,
    SCALE_STEP_DOWN,
    SCALE_STEP_UP,
    MM_TO_M,
    DEFAULT_REFERENCE_HEIGHT,
    HEIGHT_AXIS,
    UNIT_MILLIMETERS,
    UNIT_METERS,
    UNIT_UNKNOWN,
)


class SceneManager:
    """
    Verwaltet die geladenen Objekte (in benannten "Slots", z.B.
    'bodyscan' / 'smpl'), die aktuelle Auswahl und den Gizmo.

    Kennt weder Qt noch Maus-Events - reine Szenenlogik.
    """

    def __init__(self, plotter, camera_controller):
        self._plotter = plotter
        self._camera = camera_controller

        self.gizmo = Gizmo(plotter)
        self.landmarks = LandmarkManager(plotter)

        self._objects_by_slot = {}    # slot_name -> SceneObject | None
        self._objects_by_actor = {}   # actor -> SceneObject
        self.selected = None

        

    # ------------------------------------------------------------
    # Laden
    # ------------------------------------------------------------

    def import_object(
        self, slot, path, color, mesh_loader=pv.read, unit_mode=UNIT_METERS
    ):
        """
        Lädt eine OBJ-Datei in den angegebenen Slot. Ein vorhandenes
        Objekt im selben Slot wird vorher vollständig entfernt.

        Ersetzt die vormals fast identischen load_obj()/load_smpl()
        Methoden durch eine einzige generische Implementierung.

        unit_mode steuert, wie die geladenen Koordinaten interpretiert
        werden (siehe _apply_unit_mode) - nötig, weil z.B. Scanner-
        Exporte oft in Millimetern vorliegen, SMPL/SMPL-X aber in
        Metern, und Web-Testkörper oft eine völlig beliebige,
        unbekannte Skala haben.
        """
        mesh = mesh_loader(path)
        mesh = self._apply_unit_mode(mesh, slot, unit_mode)

        if slot in self._objects_by_slot:
            self._remove_slot(slot, 0)
        


        actor = self._plotter.add_mesh(
            mesh,
            color=color,
            smooth_shading=True,
            lighting=True,
        )

        # Origin auf den geometrischen Mittelpunkt legen, damit
        # Rotationen um das Objekt selbst statt um den Weltursprung
        # erfolgen (siehe SceneObject.center).
        actor.SetOrigin(*mesh.center)

        scene_object = SceneObject(
            actor,
            original_color=actor.GetProperty().GetColor(),
        )

        self._objects_by_slot[slot] = scene_object
        self._objects_by_actor[actor] = scene_object

        self._plotter.reset_camera()
        self._camera.set_clipping_range()
        self.refresh_gizmo_size()

        self._plotter.render()
        
        return scene_object

    def _apply_unit_mode(self, mesh, slot, unit_mode):
        if unit_mode == UNIT_MILLIMETERS:
            mesh.points = mesh.points * MM_TO_M

        elif unit_mode == UNIT_UNKNOWN:
            current_height = self._mesh_height(mesh)

            if current_height > 1e-9:
                target_height = self._reference_height_excluding(slot)
                mesh.points = mesh.points * (target_height / current_height)

        # UNIT_METERS: Koordinaten bereits korrekt, nichts zu tun.

        return mesh

    def _reference_height_excluding(self, slot):
        """
        Aktuelle (bereits transformierte) Höhe eines ANDEREN geladenen
        Objekts als Referenz für eine Höhen-Normalisierung. Fällt auf
        DEFAULT_REFERENCE_HEIGHT zurück, wenn noch nichts anderes
        geladen ist.
        """
        for other_slot, scene_object in self._objects_by_slot.items():
            if other_slot == slot or scene_object is None:
                continue

            height = self._actor_height(scene_object.actor)

            if height > 1e-9:
                return height

        return DEFAULT_REFERENCE_HEIGHT

    @staticmethod
    def _mesh_height(mesh):
        bounds = mesh.bounds
        return bounds[HEIGHT_AXIS * 2 + 1] - bounds[HEIGHT_AXIS * 2]

    @staticmethod
    def _actor_height(actor):
        # GetBounds() liefert die Welt-Bounding-Box INKLUSIVE aktueller
        # Position/Rotation/Skalierung - anders als _mesh_height, das
        # nur die rohen (noch unskalierten) Mesh-Koordinaten betrachtet.
        bounds = actor.GetBounds()
        return bounds[HEIGHT_AXIS * 2 + 1] - bounds[HEIGHT_AXIS * 2]


    def _remove_slot(self, slot, button):
        existing = self._objects_by_slot.get(slot)    

        if existing is None:
            if button:
                raise NameError(f"Kein {slot} im Viewer geladen")
            return 

        if self.selected is existing:
            self.deselect()

        self._objects_by_actor.pop(existing.actor, None)
        self._plotter.remove_actor(existing.actor)
        self._objects_by_slot[slot] = None

        # Marker gehören zum entfernten Objekt - sonst blieben sie
        # "schwebend" ohne zugehöriges Mesh in der Szene stehen.
        self.landmarks.clear_for_slot(slot)

    # ------------------------------------------------------------
    # Auswahl
    # ------------------------------------------------------------

    def is_selectable(self, actor):
        return actor in self._objects_by_actor

    def slot_for_actor(self, actor):
        scene_object = self._objects_by_actor.get(actor)

        if scene_object is None:
            return None

        return self._slot_for_scene_object(scene_object)

    def _slot_for_scene_object(self, scene_object):
        for slot, obj in self._objects_by_slot.items():
            if obj is scene_object:
                return slot
        return None

# Marker

    def add_marker(self, slot, label, position):
        scene_object = self._objects_by_slot.get(slot)

        if scene_object is None:
            return

        self.landmarks.add_marker(slot, label, position, scene_object.actor)
        self._plotter.render()

    def remove_marker_at_actor(self, actor):
        hit = self.landmarks.label_for_actor(actor)
        if hit is None:
            return False

        slot, label = hit
        self.landmarks.remove_marker(slot, label)
        self._plotter.render()
        return True

    def marker_hit_at(self, actor):
        """(slot, label) falls actor ein Marker ist, sonst None."""
        return self.landmarks.label_for_actor(actor)

    def move_marker(self, slot, label, movement):
        self.landmarks.move_marker(slot, label, movement)

    def marker_world_position(self, slot, label):
        return self.landmarks.world_position(slot, label)

    def finalize_marker_drag(self, slot, label):
        scene_object = self._objects_by_slot.get(slot)

        if scene_object is None:
            return

        self.landmarks.finalize_marker_position(slot, label, scene_object.actor)

    def toggle_transparency_selected(self):
        if self.selected is None:
            return

        self.selected.toggle_transparency()

    def select(self, actor):
        self.deselect()

        scene_object = self._objects_by_actor[actor]
        scene_object.highlight(SELECTION_COLOR)

        self.selected = scene_object
        self.gizmo.show(scene_object.center)

        self.refresh_gizmo_size()

        self._plotter.render()

    def deselect(self):
        if self.selected is None:
            return

        self.selected.restore_color()
        self.selected = None
        self.gizmo.remove()

        self._plotter.render()

    # ------------------------------------------------------------
    # Manipulation der Auswahl
    #
    # Rendern NICHT selbst (siehe CameraController) - der
    # InteractionController entscheidet, wann gerendert wird.
    # ------------------------------------------------------------

    def move_selected(self, movement):
        if self.selected is None:
            return

        self.selected.move(movement)
        self.gizmo.move(movement)
        self._update_markers_for_selected()

    def rotate_selected(self, dx, dy):
        if self.selected is None:
            return

        self.selected.rotate(dx, dy)
        self._update_markers_for_selected()

    def scale_selected(self, wheel_delta):
        if self.selected is None:
            return

        factor = SCALE_STEP_UP if wheel_delta > 0 else SCALE_STEP_DOWN
        self.selected.scale_by(factor)
        self._update_markers_for_selected()

    def _update_markers_for_selected(self):
        slot = self._slot_for_scene_object(self.selected)

        if slot is None:
            return

        self.landmarks.update_positions_for_slot(slot, self.selected.actor)

    def refresh_gizmo_size(self):
        if self.selected is None:
            return

        self.gizmo.update_size(self.selected.center, self._camera.position)
