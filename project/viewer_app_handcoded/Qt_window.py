import sys 
import signal

from pyvistaqt import QtInteractor
import pyvista as pv

from PySide6 import QtWidgets

def get_file_path(window):
    # datei muss path haben um geöffnet zu werden
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        window, 
        "Datei auswählen",
        "",
        "OBJ-Dateien (*.obj);;NPZ-Dateien (*.npz);;Alle Dateien (*)"
    )
    print(f"Ausgewählte Datei: {file_path}")
    return file_path

def load_mesh(window, plotter):
    # plotter für die pv 3D-Objekte und window für die referenz 
    # auf das hauptfenster, damit die dateiauswahl dialoge modal sind
    
    file_path = get_file_path(window)
    if not file_path:
       QtWidgets.QMessageBox.warning(
            window,
            "Keine Datei ausgewählt",
            "Es wurde keine Datei ausgewählt.",
        )
    else:
        # pv.read ist für .obj Dateien, np.load für .npz Dateien + weitere Verarbeitung
        mesh = pv.read(file_path)

        actor = plotter.add_mesh(
            mesh,
            color="lightblue",
            smooth_shading=True,
            lighting=True,
        )

        actor.SetOrigin(*mesh.center)

        plotter.render()

        pass

def main():


    #GUI stuff

    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("3D Viewer")
    window.showMaximized()

    central_widget= QtWidgets.QWidget()
    window.setCentralWidget(central_widget)
    layout = QtWidgets.QGridLayout(central_widget)

    # plotter für 3D-Objekte
    plotter = QtInteractor(central_widget)

    # sidebar für Buttons und sonstige bedienelemente
    sidebar = QtWidgets.QWidget()
    sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
    

    #Buttons
    import_button = QtWidgets.QPushButton("Import Object")
    position_button = QtWidgets.QPushButton("Reset position")

    sidebar_layout.addWidget(import_button)
    sidebar_layout.addWidget(position_button)

    sidebar_layout.addStretch()
    sidebar_layout.setContentsMargins(0,0,0,0)

    layout.addWidget(plotter, 0, 0)
    layout.addWidget(sidebar, 0, 1)

    # label
    mouse_position = QtWidgets.QLabel("X: 0.00, Y: 0.00, Z: 0.00")


    # buttons bekommen Funktion zugewiesen
    import_button.clicked.connect(lambda: load_mesh(window, plotter))

    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()