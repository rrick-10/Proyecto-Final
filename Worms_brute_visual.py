"""
Visualización y benchmark de la fuerza bruta (BruteForceTerrain) en consola.

La clase y las bombas viven en brute_force.py (las pruebas unitarias están en
test_brute_force.py); este archivo solo las ejecuta y las dibuja.

Uso (desde la carpeta raíz):
    python Worms_brute_visual.py [semilla] [ancho] [alto] [n_bombas]
    python Worms_brute_visual.py 7 48 16 4
"""
from __future__ import annotations

import random
import sys
import time
import tracemalloc
from typing import Dict, List

from brute_force import Bomb, BruteForceTerrain, random_bombs, run_bombs


def benchmark(width: int, height: int, bombs: List[Bomb]) -> Dict[str, float]:
    """Tiempo de aplicar las bombas, memoria del mapa y % destruido."""
    tracemalloc.start()
    terrain = BruteForceTerrain.lower_half_solid(width, height)
    memory_bytes = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    start = time.perf_counter()
    run_bombs(terrain, bombs)
    elapsed = time.perf_counter() - start

    return {
        "time_ms": elapsed * 1000,
        "memory_kb": memory_bytes / 1024,
        "destroyed_pct": terrain.destroyed_percentage(),
    }


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randrange(1_000_000)
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    n_bombs = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    bombs = random_bombs(width, height, n_bombs,
                         max(1, width // 24), max(2, width // 9), seed)
    stats = benchmark(width, height, bombs)

    terrain = BruteForceTerrain.lower_half_solid(width, height)
    initial_solid = terrain.solid_area()

    print(f"Semilla: {seed}")
    print(f"Mapa: {width}x{height} píxeles (Y hacia arriba)")
    print(f"Tierra inicial: {initial_solid} píxeles (mitad de abajo)")

    show_map = width <= 100 and height <= 40
    if show_map:
        print("\nMapa inicial:")
        print(terrain.to_ascii())

    print("\nBombas (x, y, radio):")
    for i, (cx, cy, r) in enumerate(bombs[:10], 1):
        print(f"  {i}. ({cx}, {cy}) radio {r}")
    if len(bombs) > 10:
        print(f"  ... y {len(bombs) - 10} más")

    run_bombs(terrain, bombs)

    if show_map:
        print("\nMapa después de las bombas:")
        print(terrain.to_ascii())
    else:
        print("\n(El mapa es muy grande para dibujarlo en consola.)")

    destroyed_px = initial_solid - terrain.solid_area()
    print(f"\nTiempo: {stats['time_ms']:.3f} ms")
    print(f"Memoria del mapa: {stats['memory_kb']:.1f} KB")
    print(f"Destruido: {destroyed_px} de {initial_solid} píxeles "
          f"({terrain.destroyed_percentage():.2f} %)")


if __name__ == "__main__":
    main()
