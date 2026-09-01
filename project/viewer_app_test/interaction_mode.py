from enum import Enum, auto


class InteractionMode(Enum):
    """
    Genau EINER dieser Modi ist aktiv, solange eine Maustaste
    gehalten wird. Ersetzt die vormals fünf einzelnen Bool-Flags
    (dragging_object, rotating_object, panning_camera, ...), die
    unabhängig voneinander gesetzt/zurückgesetzt werden mussten
    und dadurch inkonsistent werden konnten.
    """

    NONE = auto()
    PAN = auto()
    ORBIT = auto()
    DRAG_FREE = auto()
    ROTATE = auto()
    DRAG_AXIS = auto()
    DRAG_MARKER = auto()