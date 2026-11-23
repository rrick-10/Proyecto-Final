"""Region Quadtree para terreno destructible (estilo Worms).

A diferencia de quadtree.py (que guarda puntos), aquí cada celda guarda un
ESTADO (SOLID / EMPTY / MIXED) y las explosiones circulares dividen o colapsan
celdas. Usa la geometría de geometry.py (BoundingSquare.circle_relation) y se
valida contra la fuerza bruta BruteForceTerrain de brute_force.py.

Convención de ejes: Y crece hacia arriba (igual que geometry.py y brute_force.py).
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Iterator, Optional

from geometry import BoundingSquare


class CellState(Enum):
    """Estados del Region Quadtree para el entorno destructible."""
    EMPTY = 0  # Aire / Espacio transitable / Destruido
    SOLID = 1  # Terreno / Colisión intacta
    MIXED = 2  # Nodo interno que contiene terreno y aire


QUADRANTS = ("NW", "NE", "SW", "SE")
_FLIP = {"N": "S", "S": "N", "E": "W", "W": "E"}


class QuadTreeNode:
    def __init__(self, boundary: BoundingSquare, depth: int, max_depth: int,
                 parent: Optional["QuadTreeNode"] = None,
                 quadrant: Optional[str] = None,
                 state: CellState = CellState.EMPTY):
        self.boundary = boundary
        self.depth = depth
        self.max_depth = max_depth
        self.parent = parent
        self.quadrant = quadrant
        self.state = state
        self.children: Dict[str, QuadTreeNode] = {}

    @property
    def divided(self) -> bool:
        """Un nodo está dividido si posee hijos."""
        return bool(self.children)

    # ---- Inicialización de Terreno ------------------------------------
    def init_half_solid(self, surface_y: float) -> None:
        """
        Genera un terreno inicial: SOLID por debajo de surface_y, EMPTY por encima.
        Fuerza divisiones en la frontera (MIXED) hasta max_depth.
        """
        top = self.boundary.y + self.boundary.size
        bottom = self.boundary.y

        if top <= surface_y:
            self.state = CellState.SOLID
            self.children.clear()
        elif bottom >= surface_y:
            self.state = CellState.EMPTY
            self.children.clear()
        else:
            if self.depth < self.max_depth:
                self.subdivide()
                for child in self.children.values():
                    child.init_half_solid(surface_y)
                self.try_collapse()
            else:
                self.state = CellState.SOLID if self.boundary.ymid <= surface_y else CellState.EMPTY

    # ---- Operaciones Estructurales ------------------------------------
    def subdivide(self) -> None:
        """
        Divide la hoja en NW, NE, SW, SE.
        Los hijos heredan el estado SOLID o EMPTY del padre.
        Si el padre era MIXED, los hijos inician en EMPTY.
        """
        if self.divided or self.depth >= self.max_depth:
            return

        inherited_state = self.state if self.state != CellState.MIXED else CellState.EMPTY

        for name in QUADRANTS:
            self.children[name] = QuadTreeNode(
                boundary=self.boundary.child(name),
                depth=self.depth + 1,
                max_depth=self.max_depth,
                parent=self,
                quadrant=name,
                state=inherited_state
            )

        self.state = CellState.MIXED

    # ---- Físicas Destructibles ----------------------------------------
    def carve_circle(self, cx: float, cy: float, radius: float) -> None:
        """Destruye el terreno en un radio circular (sustracción booleana recursiva)."""
        if self.state == CellState.EMPTY:
            return

        relation = self.boundary.circle_relation(cx, cy, radius)

        # Caso 1: El cráter no toca este cuadrante
        if relation == "OUTSIDE":
            return

        # Caso 2: El cráter engulle todo el cuadrante
        if relation == "INSIDE":
            self.state = CellState.EMPTY
            self.children.clear()
            return

        # Caso 3: INTERSECTS (el borde del cráter corta este cuadrante)
        # Control de resolución espacial: evita recursión infinita
        if self.depth >= self.max_depth:
            self.state = CellState.EMPTY
            self.children.clear()
            return

        if not self.divided:
            self.subdivide()

        for child in self.children.values():
            child.carve_circle(cx, cy, radius)

        self.try_collapse()

    def try_collapse(self) -> None:
        """Compacta el subárbol si los 4 hijos comparten el mismo estado homogéneo."""
        if not self.divided:
            return

        unique_states = {child.state for child in self.children.values()}

        # Solo colapsamos si todos los hijos tienen EXACTAMENTE el mismo estado,
        # no es MIXED, y ninguno está subdividido.
        if len(unique_states) == 1 and CellState.MIXED not in unique_states:
            if all(not child.divided for child in self.children.values()):
                self.state = unique_states.pop()
                self.children.clear()
                return

        self.state = CellState.MIXED

    # ---- Consulta de punto (colisión) -----------------------------------
    def leaf_at(self, px: float, py: float) -> Optional["QuadTreeNode"]:
        """Hoja que contiene (px, py); None si cae fuera de este nodo."""
        if not self.boundary.contains_xy(px, py):
            return None
        node = self
        while node.divided:
            node = node.children[node.boundary.quadrant_of_xy(px, py)]
        return node

    # ---- Búsqueda de Vecinos sin coordenadas (Teorema 14.2) -----------
    def find_neighbor(self, direction: str) -> Optional["QuadTreeNode"]:
        """Vecino en 'N','S','E','W' de tamaño igual o mayor (None si no hay)."""
        if self.parent is None:
            return None
        q = self.quadrant
        axis = 0 if direction in "NS" else 1
        if q[axis] == _FLIP[direction]:
            return self.parent.children[q[:axis] + direction + q[axis + 1:]]

        n = self.parent.find_neighbor(direction)
        if n is None or not n.divided:
            return n

        mirror = q[:axis] + _FLIP[q[axis]] + q[axis + 1:]
        return n.children[mirror]

    # ---- Utilidades del Árbol -----------------------------------------
    def node_count(self) -> int:
        if not self.divided:
            return 1
        return 1 + sum(child.node_count() for child in self.children.values())

    def current_depth(self) -> int:
        if not self.divided:
            return self.depth
        return max(child.current_depth() for child in self.children.values())

    def leaves(self) -> Iterator["QuadTreeNode"]:
        """Generador que produce solo las hojas terminales activas del subárbol."""
        if not self.divided:
            yield self
        else:
            for child in self.children.values():
                yield from child.leaves()


class RegionQuadTree:
    """Controlador principal del mapa destructible."""

    def __init__(self, U: float, max_depth: int = 8):
        self.U = U
        self.max_depth = max_depth
        self.root = QuadTreeNode(
            boundary=BoundingSquare(0, 0, U),
            depth=0,
            max_depth=max_depth
        )
        self._initial_solid = 0.0

    def generate_terrain(self, surface_y: float) -> None:
        """Inicializa el mapa: sólido por debajo de surface_y, aire por encima.
        El sólido resultante queda como el 100 % de destroyed_percentage()."""
        self.root.init_half_solid(surface_y)
        self._initial_solid = self.solid_area()

    def leaves(self) -> Iterator[QuadTreeNode]:
        """Devuelve todas las hojas del árbol."""
        return self.root.leaves()

    def node_count(self) -> int:
        """Devuelve el total de nodos en la estructura actual."""
        return self.root.node_count()

    def depth(self) -> int:
        """Profundidad máxima alcanzada por alguna hoja."""
        return self.root.current_depth()

    # ---- Operaciones de Terreno (API de Videojuego) --------------------
    def carve_circle(self, cx: float, cy: float, radius: float) -> None:
        """Aplica un impacto circular de bomba sobre el terreno."""
        if radius < 0:
            raise ValueError("El radio de la explosión no puede ser negativo")
        self.root.carve_circle(cx, cy, radius)

    def explosion(self, cx: float, cy: float, radius: float) -> None:
        """Alias semántico para carve_circle."""
        self.carve_circle(cx, cy, radius)

    def is_solid(self, x: float, y: float) -> bool:
        """Colisión de un punto con el terreno: O(profundidad). Fuera del mapa = aire."""
        leaf = self.root.leaf_at(x, y)
        return leaf is not None and leaf.state == CellState.SOLID

    def solid_area(self) -> float:
        """Calcula el área total de terreno sólido restante sumando hojas SOLID: O(hojas)."""
        return sum(
            leaf.boundary.size ** 2
            for leaf in self.leaves()
            if leaf.state == CellState.SOLID
        )

    def total_area(self) -> float:
        """Área geométrica total del mapa."""
        return self.U * self.U

    def destroyed_area(self) -> float:
        """Calcula el área total de espacio vacío (destruido o aire)."""
        return self.total_area() - self.solid_area()

    def destruction_percentage(self) -> float:
        """Porcentaje del MAPA completo que es aire/vacío [0.0 - 100.0]
        (incluye el aire que ya había antes de cualquier explosión)."""
        return (self.destroyed_area() / self.total_area()) * 100.0

    def destroyed_percentage(self) -> float:
        """Porcentaje del terreno sólido INICIAL que ya fue destruido [0.0 - 100.0].
        Misma definición que BruteForceTerrain.destroyed_percentage."""
        if self._initial_solid == 0:
            return 0.0
        return 100.0 * (self._initial_solid - self.solid_area()) / self._initial_solid

    # ---- Visualización ---------------------------------------------------
    def to_ascii(self, cols: int = 40, rows: int = 15,
                 solid_char: str = "#", air_char: str = ".") -> str:
        """Dibujo del terreno en consola (fila de arriba primero)."""
        step_x = self.U / cols
        step_y = self.U / rows
        lines = []
        for r in range(rows):
            py = (rows - 1 - r) * step_y + step_y / 2
            lines.append("".join(
                solid_char if self.is_solid(c * step_x + step_x / 2, py) else air_char
                for c in range(cols)))
        return "\n".join(lines)
