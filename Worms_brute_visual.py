"""
Visualización y benchmark de la fuerza bruta (BruteForceTerrain) en consola.

La clase y las bombas viven en brute_force.py (las pruebas unitarias están en
test_brute_force.py); este archivo solo las ejecuta y las dibuja.

Uso (desde la carpeta raíz):
    python Worms_brute_visual.py [semilla] [ancho] [alto] [n_bombas]
    python Worms_brute_visual.py 42 64 64 4
    Usa los mismos argumentos en wormquadtree.py para comparar ambas estructuras.
"""
from __future__ import annotations

import sys
import time
import tracemalloc
from typing import Dict, List, Tuple

from brute_force import Bomb, BruteForceTerrain, random_bombs, run_bombs


def benchmark(width: int, height: int, bombs: List[Bomb]
              ) -> Tuple[BruteForceTerrain, str, Dict[str, float]]:
    """Ejecuta la escena y devuelve el terreno junto con sus métricas."""
    tracemalloc.start()
    terrain = BruteForceTerrain.lower_half_solid(width, height)
    memory_bytes = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    initial_solid = terrain.solid_area()
    initial_map = terrain.to_ascii()

    start = time.perf_counter()
    run_bombs(terrain, bombs, center_offset=0.5)
    bomb_elapsed = time.perf_counter() - start

    area_start = time.perf_counter()
    destroyed_percentage = terrain.destroyed_percentage()
    area_elapsed = time.perf_counter() - area_start

    stats = {
        "bomb_time_ms": bomb_elapsed * 1000,
        "area_time_ms": area_elapsed * 1000,
        "memory_kb": memory_bytes / 1024,
        "destroyed_pct": destroyed_percentage,
        "initial_solid": initial_solid,
        "destroyed_area": initial_solid * destroyed_percentage / 100,
    }
    return terrain, initial_map, stats


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    n_bombs = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    bombs = random_bombs(width, height, n_bombs,
                         max(1, width // 24), max(2, width // 9), seed)
    terrain, initial_map, stats = benchmark(width, height, bombs)

    print(f"Semilla: {seed}")
    print(f"Mapa: {width}x{height} píxeles (Y hacia arriba)")
    print(f"Tierra inicial: {stats['initial_solid']:.0f} píxeles (mitad de abajo)")

    show_map = width <= 100 and height <= 64
    if show_map:
        print("\nMapa inicial:")
        print(initial_map)

    print("\nBombas (x, y, radio):")
    for i, (cx, cy, r) in enumerate(bombs[:10], 1):
        print(f"  {i}. ({cx}, {cy}) radio {r}")
    if len(bombs) > 10:
        print(f"  ... y {len(bombs) - 10} más")

    if show_map:
        print("\nMapa después de las bombas:")
        print(terrain.to_ascii())
    else:
        print("\n(El mapa es muy grande para dibujarlo en consola.)")

    print(f"\nTiempo para aplicar las bombas: {stats['bomb_time_ms']:.3f} ms")
    print(f"Tiempo para calcular el área destruida: {stats['area_time_ms']:.3f} ms")
    print(f"Memoria del mapa: {stats['memory_kb']:.1f} KB")
    print(f"Área destruida: {stats['destroyed_area']:.2f} de "
          f"{stats['initial_solid']:.2f} píxeles² "
          f"({stats['destroyed_pct']:.2f} % del terreno inicial)")


if __name__ == "__main__":
    main()

