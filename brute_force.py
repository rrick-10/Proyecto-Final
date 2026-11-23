"""Líneas base de FUERZA BRUTA (oráculos de correctitud).

Tiene dos partes:

1. Puntos (para quadtree.py): range_query, count_in_range, density,
   radius_query y nearest_neighbor, recorriendo los n puntos en cada consulta, O(n).

2. Terreno destructible (para wormquadtree.py): BruteForceTerrain, un bitmap
   2D donde cada píxel es sólido o aire. Sirve para comprobar que el
   RegionQuadTree destruye lo mismo que la fuerza bruta y para medir tiempo
   y memoria.

Convención de ejes (la misma que el Quadtree): Y crece HACIA ARRIBA. La fila
y = 0 es la de abajo, y el píxel (x, y) ocupa [x, x+1) x [y, y+1).
"""
from __future__ import annotations

import math
import random
from typing import Callable, List, Optional, Sequence, Tuple

from geometry import Point, Rect


# =========================================================================
# 1. Fuerza bruta sobre puntos
# =========================================================================
def range_query(points: Sequence[Point], rect: Rect) -> List[Point]:
    """Puntos dentro del rectángulo (bordes incluidos)."""
    return [p for p in points if rect.contains_point(p)]


def count_in_range(points: Sequence[Point], rect: Rect) -> int:
    return sum(1 for p in points if rect.contains_point(p))


def density(points: Sequence[Point], rect: Rect) -> float:
    """Densidad = puntos en la región / área de la región."""
    if rect.area <= 0:
        raise ValueError("La región debe tener área > 0")
    return count_in_range(points, rect) / rect.area


def radius_query(points: Sequence[Point], center: Point, r: float) -> List[Point]:
    """Vecinos a distancia <= r de center."""
    if r < 0:
        raise ValueError("r debe ser >= 0")
    r2 = r * r
    return [p for p in points if p.dist_sq(center) <= r2]


def nearest_neighbor(points: Sequence[Point], q: Point,
                     exclude: Optional[Point] = None) -> Optional[Point]:
    """Punto más cercano a q. `exclude` omite ese objeto exacto (identidad),
    útil para buscar el vecino de un punto que ya pertenece al conjunto."""
    best, best_d = None, float("inf")
    for p in points:
        if p is exclude:
            continue
        d = p.dist_sq(q)
        if d < best_d:
            best, best_d = p, d
    return best


# =========================================================================
# 2. Fuerza bruta sobre terreno destructible (Worms)
# =========================================================================
class BruteForceTerrain:
    """Bitmap 2D de terreno: grid[y][x] es True si el píxel es sólido."""

    def __init__(self, width: int, height: int, solid: bool = False) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width y height deben ser positivos")
        self.width = width
        self.height = height
        self.grid: List[List[bool]] = [[solid] * width for _ in range(height)]
        self._initial_solid = width * height if solid else 0

    # ---- construcción -----------------------------------------------------
    def generate_terrain(self, surface_y: float) -> None:
        """Sólido por debajo de surface_y, aire por encima (un píxel es sólido
        si su centro y + 0.5 <= surface_y). Mismo terreno que
        RegionQuadTree.generate_terrain."""
        for y in range(self.height):
            solid = (y + 0.5) <= surface_y
            self.grid[y] = [solid] * self.width
        self.reset_baseline()

    @classmethod
    def lower_half_solid(cls, width: int, height: int) -> "BruteForceTerrain":
        terrain = cls(width, height, solid=False)
        terrain.generate_terrain(height / 2)
        return terrain

    def reset_baseline(self) -> None:
        """Fija el sólido actual como el 100 % para destroyed_percentage."""
        self._initial_solid = self.solid_area()

    def copy(self) -> "BruteForceTerrain":
        other = BruteForceTerrain(self.width, self.height)
        other.grid = [row[:] for row in self.grid]
        other._initial_solid = self._initial_solid
        return other

    # ---- destrucción -------------------------------------------------------
    def carve_circle(self, cx: float, cy: float, radius: float,
                     center_offset: float = 0.0) -> int:
        """Borra los píxeles sólidos dentro del disco (cx, cy, radius).

        Devuelve cuántos píxeles destruyó. El píxel (x, y) se evalúa en
        (x + center_offset, y + center_offset): con 0.0 se prueba su esquina
        (coordenadas enteras); con 0.5 su centro, que es lo que usa el
        Quadtree al compararse contra esta fuerza bruta.
        """
        if radius < 0:
            raise ValueError("radius no puede ser negativo")
        r2 = radius * radius

        x_min = max(0, math.floor(cx - radius - center_offset))
        x_max = min(self.width - 1, math.ceil(cx + radius - center_offset))
        y_min = max(0, math.floor(cy - radius - center_offset))
        y_max = min(self.height - 1, math.ceil(cy + radius - center_offset))

        destroyed = 0
        for y in range(y_min, y_max + 1):
            dy = (y + center_offset) - cy
            row = self.grid[y]
            for x in range(x_min, x_max + 1):
                dx = (x + center_offset) - cx
                if row[x] and dx * dx + dy * dy <= r2:
                    row[x] = False
                    destroyed += 1
        return destroyed

    # ---- consultas ---------------------------------------------------------
    def solid_area(self) -> int:
        """Píxeles sólidos que quedan."""
        return sum(sum(row) for row in self.grid)

    def total_area(self) -> int:
        return self.width * self.height

    def destroyed_area(self) -> int:
        """Píxeles que ahora son aire (los destruidos y el aire original)."""
        return self.total_area() - self.solid_area()

    def is_solid(self, x: float, y: float) -> bool:
        """Colisión de un punto con el terreno (fuera del mapa = aire)."""
        px, py = math.floor(x), math.floor(y)
        if px < 0 or py < 0 or px >= self.width or py >= self.height:
            return False
        return self.grid[py][px]

    def destroyed_percentage(self) -> float:
        """% del terreno sólido INICIAL que ya fue destruido [0, 100]."""
        if self._initial_solid == 0:
            return 0.0
        remaining = self.solid_area()
        return 100.0 * (self._initial_solid - remaining) / self._initial_solid

    def mismatches(self, query: Callable[[int, int], bool]
                   ) -> List[Tuple[int, int, bool, bool]]:
        """Compara contra otra estructura: lista de (x, y, esperado, obtenido)
        donde query(x, y) no coincide con este bitmap."""
        diffs = []
        for y in range(self.height):
            for x in range(self.width):
                expected = self.grid[y][x]
                got = bool(query(x, y))
                if expected != got:
                    diffs.append((x, y, expected, got))
        return diffs

    def to_ascii(self, solid_char: str = "#", air_char: str = ".") -> str:
        """Dibujo en consola con la fila de arriba primero (y crece hacia arriba)."""
        return "\n".join(
            "".join(solid_char if c else air_char for c in row)
            for row in reversed(self.grid)
        )


# =========================================================================
# Bombas aleatorias (compartidas por los demos y las pruebas)
# =========================================================================
Bomb = Tuple[float, float, float]      # (cx, cy, radio)


def random_bombs(width: int, height: int, n: int, r_min: int, r_max: int,
                 seed: int = 0) -> List[Bomb]:
    rng = random.Random(seed)
    return [(rng.randrange(width), rng.randrange(height), rng.randint(r_min, r_max))
            for _ in range(n)]


def run_bombs(terrain: BruteForceTerrain, bombs: List[Bomb],
              center_offset: float = 0.0) -> None:
    for cx, cy, r in bombs:
        terrain.carve_circle(cx, cy, r, center_offset)
