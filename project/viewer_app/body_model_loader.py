import numpy as np
import pyvista as pv


class BodyModelLoader:
    """
    Lädt eine rohe SMPL- oder SMPL-X-Modell-Datei (.npz), wie sie bei
    der Konvertierung der offiziellen .pkl-Modelldateien entsteht.

    SMPL- und SMPL-X-Modelle unterscheiden sich in Vertex-Anzahl und
    zusätzlichen Feldern (Hand-/Gesichts-Komponenten bei SMPL-X),
    teilen sich aber 'v_template' (T-Pose-Vertices) und 'f' (Faces) -
    für die reine Anzeige reicht das, unabhängig vom konkreten Modell.
    Die restlichen Felder (shapedirs, posedirs, weights, ...) werden
    hier nicht benötigt, sind aber für späteres Fitting vorhanden.
    """

    def load(self, npz_path):
        data = np.load(npz_path)

        if "v_template" not in data or "f" not in data:
            raise ValueError(
                "Die Datei enthält kein SMPL/SMPL-X-Modell im "
                "erwarteten Format (Felder 'v_template' und 'f' fehlen)."
            )

        vertices = np.asarray(data["v_template"], dtype=np.float64)
        faces = np.asarray(data["f"], dtype=np.int64)

        n_faces = faces.shape[0]
        pv_faces = np.hstack(
            [np.full((n_faces, 1), faces.shape[1]), faces]
        ).astype(np.int64).ravel()

        return pv.PolyData(vertices, pv_faces)