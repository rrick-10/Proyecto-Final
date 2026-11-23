"""
Pruebas del RegionQuadTree (terreno destructible tipo Worms) contra la fuerza
bruta BruteForceTerrain de brute_force.py (el oráculo de correctitud).

Se ejecutan junto con todo lo demás con:   python -m unittest -v
o solo este archivo con:                   python -m unittest -v test_quadtree_worms

Equivalencia de escalas: el mapa mide U x U unidades y la fuerza bruta usa un
bitmap de U x U píxeles (1 píxel = 1 unidad), evaluando cada píxel en su centro
(center_offset=0.5).
"""

import unittest

from brute_force import BruteForceTerrain
from wormquadtree import CellState, RegionQuadTree

U = 100
CENTRO = 0.5            # el píxel (x, y) se evalúa en (x + 0.5, y + 0.5)


def par(surface_y=50.0, max_depth=6):
    """Devuelve (quadtree, fuerza bruta) con el mismo terreno inicial."""
    qt = RegionQuadTree(U=U, max_depth=max_depth)
    qt.generate_terrain(surface_y)
    bf = BruteForceTerrain(U, U)
    bf.generate_terrain(surface_y)
    return qt, bf


def explotar(qt, bf, bombas):
    for cx, cy, r in bombas:
        qt.explosion(cx, cy, r)
        bf.carve_circle(cx, cy, r, center_offset=CENTRO)


class TestTerrenoInicial(unittest.TestCase):
    def test_mitad_inferior_solida(self):
        qt, bf = par()
        self.assertEqual(qt.solid_area(), U * U / 2)
        self.assertEqual(qt.solid_area(), bf.solid_area())
        self.assertEqual(qt.destroyed_percentage(), 0.0)

    def test_terreno_se_representa_con_pocos_nodos(self):
        qt, _ = par()
        # una línea recta horizontal a mitad del mapa no necesita subdividir
        self.assertEqual(qt.node_count(), 5)
        self.assertEqual(qt.depth(), 1)

    def test_superficie_irregular_es_aproximacion_acotada(self):
        qt, bf = par(surface_y=37.3, max_depth=6)
        celda = U / 2 ** 6
        self.assertLessEqual(abs(qt.solid_area() - bf.solid_area()), U * celda)


class TestContraFuerzaBruta(unittest.TestCase):
    """El Quadtree y el bitmap destruyen (casi) lo mismo."""

    ESCENARIOS = [
        ("Un solo impacto", [(50.0, 40.0, 15.0)]),
        ("Varios impactos separados",
         [(25.0, 30.0, 10.0), (75.0, 40.0, 12.0), (50.0, 20.0, 8.0)]),
        ("Impactos cercanos o superpuestos", [(50.0, 40.0, 15.0), (58.0, 42.0, 15.0)]),
        ("Múltiples impactos sobre una misma zona",
         [(50.0, 40.0, 5.0), (50.0, 40.0, 10.0), (50.0, 40.0, 20.0)]),
        ("Impactos en bordes o esquinas",
         [(0.0, 0.0, 15.0), (100.0, 0.0, 15.0), (50.0, 0.0, 10.0)]),
        ("Secuencia grande de bombas", [
            (20.0, 20.0, 8.0), (40.0, 30.0, 12.0), (60.0, 25.0, 10.0),
            (80.0, 45.0, 15.0), (35.0, 15.0, 7.0), (70.0, 35.0, 14.0)]),
    ]

    def test_area_destruida_equivalente(self):
        tolerancia = (U * U) * 0.04
        for nombre, bombas in self.ESCENARIOS:
            with self.subTest(escenario=nombre):
                qt, bf = par()
                explotar(qt, bf, bombas)
                self.assertLessEqual(
                    abs(qt.destroyed_area() - bf.destroyed_area()), tolerancia,
                    f"'{nombre}': QuadTree={qt.destroyed_area():.2f}, "
                    f"BF={bf.destroyed_area():.2f}")

    def test_porcentaje_destruido_equivalente(self):
        for nombre, bombas in self.ESCENARIOS:
            with self.subTest(escenario=nombre):
                qt, bf = par()
                explotar(qt, bf, bombas)
                self.assertAlmostEqual(qt.destroyed_percentage(),
                                       bf.destroyed_percentage(), delta=8.0)

    def test_colision_de_punto_coincide_en_casi_todo_el_mapa(self):
        """is_solid del Quadtree vs is_solid de la fuerza bruta, en el centro
        de cada píxel: solo pueden diferir en la franja de borde de los cráteres."""
        for nombre, bombas in self.ESCENARIOS:
            with self.subTest(escenario=nombre):
                qt, bf = par()
                explotar(qt, bf, bombas)
                difieren = bf.mismatches(lambda x, y: qt.is_solid(x + 0.5, y + 0.5))
                self.assertLessEqual(len(difieren), 0.05 * U * U)

    def test_el_quadtree_no_destruye_menos_que_la_fuerza_bruta_en_el_centro(self):
        """El centro de cada explosión siempre queda destruido en ambos."""
        qt, bf = par()
        bombas = [(50.0, 40.0, 15.0), (20.0, 30.0, 10.0)]
        explotar(qt, bf, bombas)
        for cx, cy, _ in bombas:
            self.assertFalse(qt.is_solid(cx, cy))
            self.assertFalse(bf.is_solid(cx, cy))


class TestColisionDePunto(unittest.TestCase):
    def test_tierra_aire_y_fuera_del_mapa(self):
        qt, _ = par()
        self.assertTrue(qt.is_solid(10, 10))
        self.assertFalse(qt.is_solid(10, 90))
        self.assertFalse(qt.is_solid(-1, 10))
        self.assertFalse(qt.is_solid(10, U + 1))

    def test_crater_deja_aire(self):
        qt, _ = par()
        qt.explosion(50, 50, 10)
        self.assertFalse(qt.is_solid(50, 45))
        self.assertTrue(qt.is_solid(50, 10))

    def test_leaf_at_devuelve_hoja_con_estado(self):
        qt, _ = par()
        hoja = qt.root.leaf_at(10, 10)
        self.assertFalse(hoja.divided)
        self.assertEqual(hoja.state, CellState.SOLID)
        self.assertIsNone(qt.root.leaf_at(-5, 10))


class TestColapsoDeNodos(unittest.TestCase):
    """Pruebas para verificar el colapso de nodos en el Quadtree."""

    def test_node_collapse_on_complete_destruction(self):
        qt = RegionQuadTree(U=100.0, max_depth=6)
        qt.generate_terrain(surface_y=50.0)

        nodos_iniciales = qt.node_count()
        qt.explosion(cx=50.0, cy=25.0, radius=80.0)
        nodos_despues = qt.node_count()

        self.assertLess(nodos_despues, nodos_iniciales)
        self.assertEqual(qt.root.state, CellState.EMPTY)
        self.assertEqual(qt.root.node_count(), 1)

    def test_terrain_correctness_after_collapse(self):
        qt = RegionQuadTree(U=100.0, max_depth=5)
        qt.generate_terrain(surface_y=50.0)

        qt.explosion(cx=50.0, cy=50.0, radius=20.0)
        nodos_intermedios = qt.node_count()

        qt.explosion(cx=50.0, cy=50.0, radius=100.0)
        nodos_finales = qt.node_count()

        self.assertLess(nodos_finales, nodos_intermedios)
        self.assertEqual(qt.solid_area(), 0.0)
        self.assertEqual(qt.destroyed_area(), 100.0 * 100.0)
        self.assertEqual(qt.destroyed_percentage(), 100.0)

    def test_explosion_en_el_aire_no_cambia_nada(self):
        qt, _ = par()
        antes = (qt.node_count(), qt.solid_area())
        qt.explosion(50, 90, 10)
        self.assertEqual((qt.node_count(), qt.solid_area()), antes)

    def test_radio_negativo(self):
        qt, _ = par()
        with self.assertRaises(ValueError):
            qt.explosion(50, 50, -1)

    def test_no_supera_la_profundidad_maxima(self):
        qt, _ = par(max_depth=4)
        qt.explosion(33.3, 41.7, 7.7)
        self.assertLessEqual(qt.depth(), 4)

    def test_areas_suman_el_total(self):
        qt, _ = par()
        qt.explosion(50, 40, 15)
        self.assertAlmostEqual(qt.solid_area() + qt.destroyed_area(), qt.total_area())


class TestVecinos(unittest.TestCase):
    def test_vecinos_de_celdas_hermanas(self):
        qt = RegionQuadTree(U=64, max_depth=3)
        qt.root.subdivide()
        nw, ne = qt.root.children["NW"], qt.root.children["NE"]
        sw = qt.root.children["SW"]
        self.assertIs(nw.find_neighbor("E"), ne)
        self.assertIs(nw.find_neighbor("S"), sw)
        self.assertIsNone(nw.find_neighbor("W"))      # borde del mapa
        self.assertIsNone(qt.root.find_neighbor("N"))


class TestVisualizacion(unittest.TestCase):
    def test_ascii_tiene_el_tamano_pedido_y_tierra_abajo(self):
        qt, _ = par()
        filas = qt.to_ascii(cols=20, rows=10).split("\n")
        self.assertEqual(len(filas), 10)
        self.assertTrue(all(len(f) == 20 for f in filas))
        self.assertEqual(filas[0], "." * 20)          # arriba: aire
        self.assertEqual(filas[-1], "#" * 20)         # abajo: tierra


if __name__ == "__main__":
    unittest.main()
