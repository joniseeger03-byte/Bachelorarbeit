from PySide6 import QtWidgets
from pyvistaqt import QtInteractor
import pyvista as pv

from .camera_controller import CameraController
from .scene_manager import SceneManager
from .interaction_controller import InteractionController
from .body_model_loader import BodyModelLoader
from .config import (
    BODYSCAN_COLOR,
    SMPL_COLOR,
    SMPLX_COLOR,
    LANDMARK_LABELS,
    UNIT_MILLIMETERS,
    UNIT_METERS,
    UNIT_UNKNOWN,
)

class MainWindow(QtWidgets.QMainWindow):
    """
    Reine UI-Klasse: Layout, Buttons, Datei-Dialoge. Die eigentliche
    3D-Logik steckt vollständig in SceneManager / CameraController /
    InteractionController - MainWindow verdrahtet sie nur.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("3D Viewer")
        self.resize(1200, 800)

        self._setup_ui()
        self._setup_scene()

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------

    def _setup_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QGridLayout(central_widget)

        self.plotter = QtInteractor(central_widget)
        

        self.button_import_scan = QtWidgets.QPushButton("Import Scan-Object")
        
        self.button_import_smpl = QtWidgets.QPushButton("Import SMPL-Object")
        self.button_import_smplx = QtWidgets.QPushButton("Import SMPL-X-Object")

        self.button_remove_scan = QtWidgets.QPushButton("Remove Scan-Object")
        self.button_remove_smpl = QtWidgets.QPushButton("Remove SMPL-Object")
        self.button_remove_smplx = QtWidgets.QPushButton("Remove SMPL-X-Object")

        self.button_quit = QtWidgets.QPushButton("Programm beenden")
        self.button_reset_camera = QtWidgets.QPushButton("Reset Kamera Position")

        buttons = [self.button_import_scan,
                    self.button_import_smpl,
                    self.button_import_smplx,
                    self.button_remove_scan,
                    self.button_remove_smpl,
                    self.button_remove_smplx,
                    self.button_quit,
                    self.button_reset_camera,]

        layout.addWidget(self.plotter, 0, 0, len(buttons) + 1, 1)

        for row, button in enumerate(buttons):
            layout.addWidget(button, row, 1)

        self.button_import_scan.clicked.connect(
            lambda: self._import_via_dialog(
                "bodyscan", 
                BODYSCAN_COLOR, 
                r"C:\Users\Jonas Seeger\Documents\Bachelorprojekt JS\python workspace\scan_models",
                ask_unit_mode=True,
                file_filter="Scan-Objekt (*.obj)",
                mesh_loader= pv.read),
        )
        self.button_reset_camera.clicked.connect(self.plotter.view_xy)

        self.button_quit.clicked.connect(self.close)

        self.button_import_smpl.clicked.connect(
            lambda: self._import_via_dialog(
                "smpl", 
                SMPL_COLOR,
                r"C:\Users\Jonas Seeger\Documents\Bachelorprojekt JS\python workspace\smpl_models",
                file_filter="SMPL Modell (*.npz)",
                mesh_loader=self.body_model_loader.load,
            )
        )
        self.button_import_smplx.clicked.connect(
            lambda: self._import_via_dialog(
                "smplx", SMPLX_COLOR,
                r"C:\Users\Jonas Seeger\Documents\Bachelorprojekt JS\python workspace\smplx_models",
                file_filter="SMPL-X Modell (*.npz)",
                mesh_loader=self.body_model_loader.load,
            )
        )

        self.button_remove_scan.clicked.connect(
            lambda: self.remove_object("bodyscan")
        )
        self.button_remove_smpl.clicked.connect(
            lambda: self.remove_object("smpl")
        )
        self.button_remove_smplx.clicked.connect(
            lambda: self.remove_object("smplx")
        )

    def remove_object(self, slot):
        try:
            self.scene_manager._remove_slot(slot, 1)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                f"No Object",
                str(e)
            )

    def _setup_scene(self):
        self.plotter.show_axes()
        self.plotter.set_background("white")
        self.body_model_loader = BodyModelLoader()

        self.camera_controller = CameraController(self.plotter)
        self.camera_controller.set_clipping_range()
        self.plotter.reset_camera()

        self.scene_manager = SceneManager(self.plotter, self.camera_controller)

        self.interaction_controller = InteractionController(
            self.plotter, 
            self.scene_manager, 
            self.camera_controller,
            on_marker_point_picked=self._on_marker_point_picked,
        )

    # ------------------------------------------------------------
    # Datei-Import
    # ------------------------------------------------------------

    def _ask_unit_mode(self):
        options = {
            "Scanner-Export (Milimeter, ÷1000 zu Meter)": UNIT_MILLIMETERS,
            "Meter (bereits korrekt skaliert)": UNIT_METERS,
            "Unbekannt (auf Referenzhöhe normalisieren)": UNIT_UNKNOWN,
        }

        choice, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Skalierung der Datei",
            "In welcher Einheit liegt diese Datei vor?",
            list(options.keys()),
            0,
            False,
        )

        if not ok:
            return None

        return options[choice]

    def _import_via_dialog(self, slot, color, path, file_filter, mesh_loader, ask_unit_mode=False,):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Datei auswählen", path, file_filter
        )

        if not file_path:
            QtWidgets.QMessageBox.warning(
                self,
                "Keine Datei ausgewählt",
                f"Es wurde keine {file_filter} ausgewählt.",
            )
            return

        unit_mode = UNIT_METERS

        if ask_unit_mode:
            unit_mode = self._ask_unit_mode()

            if unit_mode is None:
                return

        try:
            self.scene_manager.import_object(slot, file_path, color, mesh_loader, unit_mode)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Fehler beim Laden der Datei",
                f"Die Datei konnte nicht geladen werden:\n{e}",
            )
    # ------------------------------------------------------------
    # Marker benennen
    # ------------------------------------------------------------
    
    def _on_marker_point_picked(self, slot, position):
        if slot is None:
            return

        label, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Marker benennen",
            "Landmark auswählen:",
            LANDMARK_LABELS,
            0,
            False,
        )

        if not ok:
            return

        self.scene_manager.add_marker(slot, label, position)
    # ------------------------------------------------------------
    # Fenster schließen
    # ------------------------------------------------------------

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Beenden",
            "Möchten Sie die Anwendung wirklich beenden?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
