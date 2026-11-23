import unittest

import brute_force as bf
from brute_force import BruteForceTerrain
from geometry import Point, Rect


class TestBruteForce(unittest.TestCase):
    def setUp(self):
        self.pts = [Point(1, 1), Point(2, 2), Point(5, 5), Point(9, 9), Point(5, 1)]

    def test_range_query(self):
        res = bf.range_query(self.pts, Rect(0, 0, 5, 5))
        self.assertEqual(set(res), {Point(1, 1), Point(2, 2), Point(5, 5), Point(5, 1)})

    def test_range_vacio(self):
        self.assertEqual(bf.range_query(self.pts, Rect(6, 6, 8, 8)), [])

    def test_count_y_density(self):
        r = Rect(0, 0, 4, 4)                       # área 16, 2 puntos
        self.assertEqual(bf.count_in_range(self.pts, r), 2)
        self.assertAlmostEqual(bf.density(self.pts, r), 2 / 16)

    def test_density_area_cero(self):
        with self.assertRaises(ValueError):
            bf.density(self.pts, Rect(1, 1, 1, 5))

    def test_radius(self):
        res = bf.radius_query(self.pts, Point(1, 1), 2 ** 0.5)
        self.assertEqual(set(res), {Point(1, 1), Point(2, 2)})
        with self.assertRaises(ValueError):
            bf.radius_query(self.pts, Point(0, 0), -1)

    def test_nearest(self):
        self.assertEqual(bf.nearest_neighbor(self.pts, Point(8, 8)), Point(9, 9))

    def test_nearest_excluyendo_el_mismo(self):
        p = self.pts[0]
        self.assertEqual(bf.nearest_neighbor(self.pts, p, exclude=p), Point(2, 2))

    def test_nearest_vacio(self):
        self.assertIsNone(bf.nearest_neighbor([], Point(0, 0)))


class TestBruteForceTerrain(unittest.TestCase):
    """Terreno destructible (bitmap 2D, Y hacia arriba)."""

    def test_tamano_invalido(self):
        with self.assertRaises(ValueError):
            BruteForceTerrain(0, 5)

    def test_terreno_sin_solido_no_destruye(self):
        t = BruteForceTerrain(16, 16, solid=False)
        self.assertEqual(t.carve_circle(8, 8, 3), 0)
        self.assertEqual(t.destroyed_percentage(), 0.0)

    def test_radio_cero_borra_un_pixel(self):
        t = BruteForceTerrain(16, 16, solid=True)
        self.assertEqual(t.carve_circle(5, 5, 0), 1)
        self.assertFalse(t.is_solid(5, 5))
        self.assertTrue(t.is_solid(6, 5))

    def test_pixeles_por_radio(self):
        for r, esperado in [(1, 5), (2, 13), (3, 29)]:
            t = BruteForceTerrain(32, 32, solid=True)
            self.assertEqual(t.carve_circle(16, 16, r), esperado)
            self.assertEqual(t.solid_area(), 32 * 32 - esperado)

    def test_borde_del_circulo_incluido(self):
        t = BruteForceTerrain(16, 16, solid=True)
        t.carve_circle(5, 5, 3)
        self.assertFalse(t.is_solid(8, 5))
        self.assertTrue(t.is_solid(9, 5))

    def test_explosion_repetida_no_destruye_dos_veces(self):
        t = BruteForceTerrain(32, 32, solid=True)
        t.carve_circle(16, 16, 5)
        self.assertEqual(t.carve_circle(16, 16, 3), 0)

    def test_explosiones_en_las_orillas_y_fuera(self):
        t = BruteForceTerrain(8, 8, solid=True)
        self.assertEqual(t.carve_circle(-1, -1, 2), 1)
        self.assertEqual(t.carve_circle(100, 100, 3), 0)

    def test_radio_negativo(self):
        with self.assertRaises(ValueError):
            BruteForceTerrain(8, 8).carve_circle(1, 1, -1)

    def test_mitad_inferior_solida_y_hacia_arriba(self):
        t = BruteForceTerrain.lower_half_solid(8, 8)
        self.assertEqual(t.solid_area(), 32)
        self.assertTrue(t.is_solid(3, 3))       # fila de abajo: tierra
        self.assertFalse(t.is_solid(3, 4))      # arriba: aire
        self.assertEqual(t.carve_circle(4, 3, 1), 4)   # cruz de 5 px, 1 cae en el aire
        self.assertEqual(t.destroyed_percentage(), 12.5)

    def test_generate_terrain_centro_del_pixel(self):
        t = BruteForceTerrain(10, 10)
        t.generate_terrain(5.0)
        self.assertEqual(t.solid_area(), 50)
        self.assertEqual(t.total_area(), 100)
        self.assertEqual(t.destroyed_area(), 50)

    def test_center_offset(self):
        t = BruteForceTerrain(8, 8, solid=True)
        # con 0.5 el píxel se evalúa en su centro: radio 0.5 -> solo (3, 3)
        self.assertEqual(t.carve_circle(3.5, 3.5, 0.5, center_offset=0.5), 1)
        self.assertFalse(t.is_solid(3.5, 3.5))

    def test_copy_y_mismatches(self):
        t = BruteForceTerrain.lower_half_solid(8, 8)
        t.carve_circle(4, 2, 1)
        ref = t.copy()
        self.assertEqual(t.mismatches(lambda x, y: ref.grid[y][x]), [])
        self.assertEqual(len(t.mismatches(lambda x, y: True)),
                         8 * 8 - t.solid_area())
        ref.carve_circle(0, 0, 0)                 # la copia es independiente
        self.assertNotEqual(t.solid_area(), ref.solid_area())

    def test_to_ascii_arriba_primero(self):
        t = BruteForceTerrain.lower_half_solid(4, 4)
        self.assertEqual(t.to_ascii().split("\n"), ["....", "....", "####", "####"])

    def test_random_bombs_reproducibles(self):
        a = bf.random_bombs(48, 16, 5, 2, 5, seed=3)
        self.assertEqual(a, bf.random_bombs(48, 16, 5, 2, 5, seed=3))
        t = BruteForceTerrain.lower_half_solid(48, 16)
        bf.run_bombs(t, a)
        self.assertGreaterEqual(t.destroyed_percentage(), 0.0)


if __name__ == "__main__":
    unittest.main()
