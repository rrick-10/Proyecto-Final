import unittest

from geometry import BoundingSquare, Point, Rect, Segment


class TestPoint(unittest.TestCase):
    def test_distancia(self):
        self.assertEqual(Point(0, 0).dist_sq(Point(3, 4)), 25)
        self.assertEqual(Point(0, 0).dist(Point(3, 4)), 5)


class TestRect(unittest.TestCase):
    def test_area_y_contiene(self):
        r = Rect(0, 0, 2, 3)
        self.assertEqual(r.area, 6)
        self.assertTrue(r.contains_point(Point(2, 3)))   # borde incluido
        self.assertFalse(r.contains_point(Point(2.1, 1)))

    def test_invalido(self):
        with self.assertRaises(ValueError):
            Rect(1, 0, 0, 1)


class TestBoundingSquare(unittest.TestCase):
    def setUp(self):
        self.sq = BoundingSquare(0, 0, 8)

    def test_cuadrantes_segun_documento(self):
        self.assertEqual(self.sq.quadrant_of(Point(5, 5)), "NE")
        self.assertEqual(self.sq.quadrant_of(Point(4, 5)), "NW")   # x == xmid
        self.assertEqual(self.sq.quadrant_of(Point(5, 4)), "SE")   # y == ymid
        self.assertEqual(self.sq.quadrant_of(Point(4, 4)), "SW")

    def test_hijos(self):
        self.assertEqual(self.sq.child("NE"), BoundingSquare(4, 4, 4))
        self.assertEqual(self.sq.child("SW"), BoundingSquare(0, 0, 4))
        self.assertEqual(self.sq.child("NW"), BoundingSquare(0, 4, 4))
        self.assertEqual(self.sq.child("SE"), BoundingSquare(4, 0, 4))

    def test_contiene_borde(self):
        self.assertTrue(self.sq.contains(Point(8, 8)))
        self.assertFalse(self.sq.contains(Point(8.01, 0)))

    def test_interseccion_e_inside(self):
        self.assertTrue(self.sq.intersects(Rect(7, 7, 20, 20)))
        self.assertFalse(self.sq.intersects(Rect(9, 9, 20, 20)))
        self.assertTrue(self.sq.inside(Rect(-1, -1, 9, 9)))
        self.assertFalse(self.sq.inside(Rect(1, 1, 9, 9)))

    def test_min_dist(self):
        self.assertEqual(self.sq.min_dist_sq(Point(4, 4)), 0)
        self.assertEqual(self.sq.min_dist_sq(Point(11, 12)), 9 + 16)

    def test_size_invalido(self):
        with self.assertRaises(ValueError):
            BoundingSquare(0, 0, 0)


# ==============================================================================
# Worms: segmentos, terreno destructible, proyectiles y colisiones físicas
# ==============================================================================

class TestRectColisiones(unittest.TestCase):
    def test_intersects_rect(self):
        r = Rect(0, 0, 4, 4)
        self.assertTrue(r.intersects_rect(Rect(3, 3, 6, 6)))
        self.assertTrue(r.intersects_rect(Rect(4, 4, 6, 6)))      # toca la esquina
        self.assertFalse(r.intersects_rect(Rect(5, 0, 6, 4)))

    def test_intersects_segment(self):
        r = Rect(0, 0, 4, 4)
        self.assertTrue(r.intersects_segment(Segment(Point(-2, 2), Point(6, 2))))
        self.assertTrue(r.intersects_segment(Segment(Point(1, 1), Point(2, 2))))   # adentro
        self.assertFalse(r.intersects_segment(Segment(Point(-2, 5), Point(6, 5))))
        self.assertFalse(r.intersects_segment(Segment(Point(5, -1), Point(5, 9))))  # paralelo afuera
        self.assertFalse(r.intersects_segment(Segment(Point(-3, 3), Point(3, 9))))  # pasa por la esquina de afuera


class TestCircleRelation(unittest.TestCase):
    def setUp(self):
        # Cuadrado en [10, 20] x [10, 20]
        self.sq = BoundingSquare(10, 10, 10)

    def test_outside_totalmente_lejos(self):
        self.assertEqual(self.sq.circle_relation(0, 0, 5), "OUTSIDE")
        self.assertEqual(self.sq.circle_relation(30, 15, 2), "OUTSIDE")

    def test_outside_tangente_exterior(self):
        # La arista está en x = 20; centro en 25 con r = 4.99 (no toca)
        self.assertEqual(self.sq.circle_relation(25, 15, 4.99), "OUTSIDE")

    def test_inside_circulo_engulle_cuadrado(self):
        # Centro en (15, 15), distancia a esquinas ≈ 7.07
        self.assertEqual(self.sq.circle_relation(15, 15, 8.0), "INSIDE")

    def test_inside_circulo_descentrado_pero_engulle(self):
        self.assertEqual(self.sq.circle_relation(5, 5, 25.0), "INSIDE")

    def test_intersects_borde_cruza_esquina(self):
        self.assertEqual(self.sq.circle_relation(22, 22, 5.0), "INTERSECTS")

    def test_intersects_circulo_contenido_dentro_del_cuadrado(self):
        # Explosión contenida dentro de la celda: corta la celda internamente
        self.assertEqual(self.sq.circle_relation(15, 15, 2.0), "INTERSECTS")

    def test_radio_cero_o_invalido(self):
        self.assertEqual(self.sq.circle_relation(15, 15, 0.0), "INTERSECTS")
        with self.assertRaises(ValueError):
            self.sq.circle_relation(15, 15, -1.0)


class TestAABBCollision(unittest.TestCase):
    def setUp(self):
        self.sq = BoundingSquare(0, 0, 10)

    def test_colision_caja_personaje_dentro(self):
        self.assertTrue(self.sq.intersects_aabb(Rect(2, 2, 4, 6)))

    def test_colision_caja_personaje_solapada(self):
        self.assertTrue(self.sq.intersects_aabb(Rect(8, 8, 15, 15)))

    def test_colision_caja_personaje_fuera(self):
        self.assertFalse(self.sq.intersects_aabb(Rect(11, 0, 15, 10)))

    def test_to_rect(self):
        self.assertEqual(self.sq.to_rect(), Rect(0, 0, 10, 10))


class TestProjectileCollision(unittest.TestCase):
    def setUp(self):
        self.sq = BoundingSquare(10, 10, 10)

    def test_proyectil_atraviesa_completamente(self):
        self.assertTrue(self.sq.intersects_projectile(Segment(Point(0, 15), Point(30, 15))))

    def test_proyectil_inicia_o_termina_adentro(self):
        self.assertTrue(self.sq.intersects_projectile(Segment(Point(0, 15), Point(12, 15))))

    def test_proyectil_pasa_de_largo(self):
        self.assertFalse(self.sq.intersects_projectile(Segment(Point(0, 25), Point(30, 25))))

    def test_proyectil_muy_rapido_no_hace_tunneling(self):
        self.assertTrue(self.sq.intersects_projectile(Segment(Point(0, 15), Point(100, 15))))


if __name__ == "__main__":
    unittest.main()
