"""
Demo, benchmarking y comparación de rendimiento:
Region Quadtree (wormquadtree.py) vs bitmap de fuerza bruta (brute_force.py).

Corre desde la carpeta raíz del proyecto:   python demo_worms.py
No requiere librerías externas.
"""
from __future__ import annotations

import argparse
import random
import time
import tracemalloc

from brute_force import BruteForceTerrain
from wormquadtree import RegionQuadTree

CENTRO = 0.5      # el píxel (x, y) de la fuerza bruta se evalúa en su centro


def run_quadtree(U, surface_y, bombs, max_depth=6):
    tracemalloc.start()
    t0 = time.perf_counter()
    qt = RegionQuadTree(U=U, max_depth=max_depth)
    qt.generate_terrain(surface_y)
    for cx, cy, r in bombs:
        qt.explosion(cx, cy, r)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return qt, elapsed, peak / 1024


def run_brute_force(U, surface_y, bombs):
    tracemalloc.start()
    t0 = time.perf_counter()
    bf = BruteForceTerrain(int(U), int(U))
    bf.generate_terrain(surface_y)
    for cx, cy, r in bombs:
        bf.carve_circle(cx, cy, r, center_offset=CENTRO)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return bf, elapsed, peak / 1024


def run_benchmark(include_large=False):
    # (tamaño U del mapa, profundidad del quadtree, nº de bombas, rango de radios)
    configuraciones = [
        (200, 6, [10, 100, 500, 1000], (5, 15)),
        (1024, 8, [100, 1000], (20, 60)),
    ]
    if include_large:
        configuraciones.append((4096, 10, [100], (80, 240)))

    ancho = 96
    print("=" * ancho)
    print("   BENCHMARK & DEMO: REGION QUADTREE VS BITMAP DE FUERZA BRUTA".center(ancho))
    print("=" * ancho)
    if include_large:
        print("Modo grande: incluye un mapa de 4096 x 4096; "
              "la fuerza bruta puede requerir más de 128 MiB.")
    print(f"{'Método':<24} | {'Bombas':<6} | {'Tiempo (s)':<10} | "
          f"{'Memoria (KiB)':<13} | {'% destruido':<11} | {'Nodos':<6}")

    for U, depth, bomb_counts, (r_min, r_max) in configuraciones:
        print("=" * ancho)
        print(f"Mapa {U} x {U}, terreno hasta y = {U / 2:g}, radios {r_min}-{r_max}")
        print("-" * ancho)
        for n in bomb_counts:
            rng = random.Random(42)
            bombs = [(rng.uniform(0.1 * U, 0.9 * U), rng.uniform(0.1 * U, 0.9 * U),
                      rng.uniform(r_min, r_max)) for _ in range(n)]
            qt, qt_time, qt_mem = run_quadtree(U, U / 2, bombs, depth)
            bf, bf_time, bf_mem = run_brute_force(U, U / 2, bombs)

            print(f"{f'Quadtree (prof. {depth})':<24} | {n:<6} | {qt_time:<10.4f} | "
                  f"{qt_mem:<13.1f} | {qt.destroyed_percentage():<11.2f} | {qt.node_count():<6}")
            print(f"{f'Fuerza bruta ({U}x{U})':<24} | {n:<6} | {bf_time:<10.4f} | "
                  f"{bf_mem:<13.1f} | {bf.destroyed_percentage():<11.2f} | {'-':<6}")
            if bf_time >= qt_time:
                print(f"--> Quadtree {bf_time / qt_time:.2f}x más rápido")
            else:
                print(f"--> Fuerza bruta {qt_time / bf_time:.2f}x más rápida")
            print("-" * ancho)

    print("\n--- DEMO: terreno tras 3 explosiones (Quadtree) ---")
    demo_qt = RegionQuadTree(U=100.0, max_depth=5)
    demo_qt.generate_terrain(50.0)
    demo_qt.explosion(30.0, 40.0, 15.0)
    demo_qt.explosion(70.0, 45.0, 12.0)
    demo_qt.explosion(50.0, 30.0, 10.0)
    print(demo_qt.to_ascii(cols=40, rows=15))
    print(f"Área sólida restante: {demo_qt.solid_area():.2f} / {demo_qt.total_area():.2f}"
          f"  ({demo_qt.destroyed_percentage():.2f} % del terreno inicial destruido)")

    print("\n--- DEMO: la misma escena con fuerza bruta (referencia) ---")
    demo_bf = BruteForceTerrain(100, 100)
    demo_bf.generate_terrain(50.0)
    for cx, cy, r in [(30.0, 40.0, 15.0), (70.0, 45.0, 12.0), (50.0, 30.0, 10.0)]:
        demo_bf.carve_circle(cx, cy, r, center_offset=CENTRO)
    print(f"Píxeles sólidos restantes: {demo_bf.solid_area()} / {demo_bf.total_area()}"
          f"  ({demo_bf.destroyed_percentage():.2f} % del terreno inicial destruido)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compara quadtree y fuerza bruta en terreno destructible.")
    parser.add_argument(
        "--large",
        action="store_true",
        help="incluye una prueba de estrés con un mapa de 4096 x 4096",
    )
    run_benchmark(include_large=parser.parse_args().large)

