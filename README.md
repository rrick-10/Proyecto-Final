# Quadtree 2D en Python vs. búsqueda por fuerza bruta

Implementación de un **Quadtree de puntos en 2D** en Python, comparada contra una línea base de **fuerza bruta** (O(n) por consulta). El proyecto incluye:

- Construcción del árbol por inserción, con capacidad por hoja y profundidad máxima `log2(U)`.
- Consultas espaciales: **rango**, **conteo**, **densidad**, **radio** y **vecino más cercano** (búsqueda best-first).
- **Búsqueda de vecinos por celda** (`N`, `S`, `E`, `W`): se sube al ancestro común y se baja por el cuadrante espejo, sin usar coordenadas (Teorema 14.2).
- **Balanceo 2:1** (extensión del Cap. 14): celdas que comparten arista o vértice no difieren en tamaño por más de un factor de 2.
- Generadores de datasets sintéticos reproducibles (uniforme y por clusters gaussianos).
- Pruebas unitarias donde la fuerza bruta funciona como **oráculo de correctitud** del Quadtree.
- **Versión Worms:** un *Region Quadtree* de terreno destructible (explosiones circulares, colapso de nodos, colisión de puntos) validado contra un bitmap de fuerza bruta.

## Contexto

| Dato | Detalle |
|---|---|
| **Proyecto** | Quadtree 2D vs. fuerza bruta |
| **Materia** | Estructura de Datos y Algoritmos |
| **Universidad** | Universidad Anáhuac |
| **Equipo** | _(escribe aquí los nombres de los integrantes)_ |

## Requisitos

- **Python 3.14** (versión usada en el desarrollo con PyCharm; el código también se verificó con Python 3.13).
- **No requiere librerías externas**: todo corre con la librería estándar (`dataclasses`, `heapq`, `random`, `unittest`, etc.). No hay `requirements.txt` ni nada que instalar.

Para ver tu versión:

```bash
python --version
```

> En algunos sistemas (macOS/Linux) el comando es `python3` en lugar de `python`.

## Estructura del proyecto

```
.
├── geometry.py              # Point, Segment, Rect y BoundingSquare (cuadrantes, intersección, círculos, proyectiles)
├── quadtree.py              # QuadTreeNode y QuadTree (inserción, consultas, vecinos, balanceo 2:1)
├── wormquadtree.py          # RegionQuadTree: terreno destructible (Worms)
├── brute_force.py           # Fuerza bruta: sobre puntos y BruteForceTerrain (bitmap de terreno)
├── datasets.py              # Generadores de datasets sintéticos y de rectángulos de consulta
├── demo.py                  # Quadtree de puntos vs fuerza bruta: igualdad de resultados y tiempos
├── demo_worms.py            # Region Quadtree vs bitmap de fuerza bruta: benchmark y dibujo en consola
├── Worms_brute_visual.py    # Dibuja y mide solo la fuerza bruta del terreno
├── test_geometry.py         # Pruebas unitarias de geometry.py (incluye círculos, AABB y proyectiles)
├── test_brute_force.py      # Pruebas unitarias de brute_force.py (puntos y terreno)
├── test_quadtree.py         # Pruebas unitarias de quadtree.py (incluye comparación contra fuerza bruta)
└── test_quadtree_worms.py   # Pruebas de wormquadtree.py contra BruteForceTerrain
```

| Archivo | Qué hace |
|---|---|
| `geometry.py` | Define `Point`, `Segment`, `Rect` (rectángulo cerrado) y `BoundingSquare` (celda del árbol, con `circle_relation`, `intersects_aabb` e `intersects_projectile` para Worms). El eje Y crece hacia arriba en todo el proyecto. Fija la convención de cuadrantes: `NE: x > xmid, y > ymid`, `NW: x <= xmid, y > ymid`, `SE: x > xmid, y <= ymid`, `SW: x <= xmid, y <= ymid`. Las regiones son **cerradas**: un punto sobre el borde pertenece a la región. |
| `quadtree.py` | `QuadTree.from_points`, `insert`, `range_query`, `count_in_range`, `density`, `radius_query`, `nearest_neighbor`, `neighbor`/`find_neighbor`, `leaf_at`, `leaves`, `depth`, `node_count`, `balance`, `is_balanced`. |
| `brute_force.py` | `range_query`, `count_in_range`, `density`, `radius_query` y `nearest_neighbor`, recorriendo los `n` puntos en cada consulta. Además `BruteForceTerrain`: bitmap de terreno con `carve_circle`, `is_solid`, `solid_area` y `destroyed_percentage`. |
| `wormquadtree.py` | `RegionQuadTree` y `CellState` (`SOLID`/`EMPTY`/`MIXED`): `generate_terrain`, `carve_circle`/`explosion`, `is_solid`, `solid_area`, `destroyed_percentage`, `to_ascii`. Los nodos se subdividen donde el borde del cráter corta la celda y se colapsan cuando sus 4 hijos quedan iguales. |
| `datasets.py` | `uniform_points`, `clustered_points` y `random_query_rect`, todos con semilla fija para que los resultados sean reproducibles. |
| `demo.py` | Construye el Quadtree, corre las mismas consultas con ambos métodos, comprueba que los resultados sean idénticos y mide los tiempos. |

## Cómo ejecutar

Todos los comandos se corren **desde la carpeta raíz del proyecto** (la que contiene `geometry.py`, `quadtree.py`, etc.).

### 1. Ejecutar la fuerza bruta y compararla con el Quadtree

`brute_force.py` es un módulo de funciones (no tiene `main`), así que se ejecuta a través del demo, que lo usa como referencia:

```bash
python demo.py
```

El demo genera 20,000 puntos (uniformes y en clusters), lanza 200 consultas de rango sobre cada dataset con ambos métodos, **verifica con un `assert` que los resultados sean idénticos** y muestra los tiempos. Salida de ejemplo (los tiempos varían según la computadora):

```
uniforme   build=  116.3 ms | 200 consultas: fuerza bruta=   298.3 ms, quadtree=    49.6 ms | d=8 nodos=14717
clusters   build=  143.9 ms | 200 consultas: fuerza bruta=   324.0 ms, quadtree=    51.0 ms | d=10 nodos=14501
```

Si los resultados difirieran, el programa se detiene con el mensaje `¡resultados distintos!`.

También puedes usar la fuerza bruta directamente desde Python:

```python
from geometry import Point, Rect
from datasets import uniform_points
import brute_force as bf

pts = uniform_points(1000, 256, seed=1)          # 1000 puntos en [0, 256] x [0, 256]
print(len(bf.range_query(pts, Rect(0, 0, 64, 64))))
print(bf.nearest_neighbor(pts, Point(128, 128)))
```

### 2. Ejecutar la versión Worms

```bash
python demo_worms.py                       # benchmark Quadtree vs fuerza bruta + dibujo del terreno
python Worms_brute_visual.py 7 48 16 4     # solo la fuerza bruta: semilla, ancho, alto, n.º de bombas
```

El Quadtree guarda el terreno con una resolución de `U / 2^max_depth`, así que destruye **un poco más** que el bitmap (la celda de máxima profundidad que toca el cráter se vacía completa). En mapas chicos el bitmap es igual de rápido; el Quadtree gana en tiempo y memoria cuando el mapa es grande (por ejemplo 1024 x 1024).

### 3. Ejecutar las pruebas unitarias

Todas las pruebas (geometría, fuerza bruta, Quadtree y Worms):

```bash
python -m unittest -v
```

Un archivo en particular:

```bash
python -m unittest -v test_geometry
python -m unittest -v test_brute_force
python -m unittest -v test_quadtree
python -m unittest -v test_quadtree_worms
```

O ejecutando el archivo directamente:

```bash
python test_quadtree.py
```

Resultado esperado: `Ran 84 tests` y al final `OK`.

### 4. Uso básico del Quadtree

```python
from geometry import Point, Rect
from datasets import clustered_points
from quadtree import QuadTree

U = 256
pts = clustered_points(500, U, seed=1)
qt = QuadTree.from_points(pts, U, capacity=4)

print(len(qt), qt.depth(), qt.node_count())
print(len(qt.range_query(Rect(10, 10, 120, 200))))   # puntos en el rectángulo
print(qt.nearest_neighbor(Point(100, 100)))          # vecino más cercano

qt.balance()                                         # balanceo 2:1
print(qt.is_balanced())                              # True
```

## Qué verifican las pruebas

- **Construcción:** inserción, puntos fuera del dominio, puntos en los bordes, duplicados (sin recursión infinita), profundidad máxima `log2(U)`, conservación de todos los puntos y cota de nodos `O((d+1)·n)`.
- **Contra fuerza bruta:** el Quadtree y la fuerza bruta devuelven exactamente lo mismo en consultas de rango, conteo, densidad, radio y vecino más cercano (datasets uniformes y por clusters, distintos tamaños y capacidades).
- **Vecinos por celda:** `find_neighbor` coincide con la búsqueda por coordenadas y la raíz no tiene vecinos.
- **Worms:** el `RegionQuadTree` y el bitmap `BruteForceTerrain` coinciden (área y porcentaje destruido dentro de tolerancia, colisión de puntos en más del 95 % del mapa) en impactos simples, superpuestos, en esquinas y en secuencias largas; los nodos colapsan al destruir todo el terreno.
- **Balanceo 2:1:** se detecta un árbol desbalanceado, `balance()` logra la regla 2:1 (verificada con un chequeo independiente O(L²)), no pierde puntos ni cambia las consultas, y es idempotente.
