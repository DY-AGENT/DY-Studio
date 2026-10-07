import importlib.util
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@unittest.skipUnless(
    all(importlib.util.find_spec(name) for name in ('skimage', 'torch', 'trimesh'))
    and (Path(__file__).resolve().parents[1] / 'data/engines/mesh/tsr').is_dir(),
    'Run this test after installing the 3D engine and its dependencies.')
class MeshAdapterTests(unittest.TestCase):
    def test_sphere_keeps_axes_volume_and_outward_surface(self):
        import torch
        import trimesh
        import worker
        worker.setup_source('mesh')
        from tsr.models.isosurface import MarchingCubeHelper
        coord = torch.linspace(-1, 1, 24)
        x, y, z = torch.meshgrid(coord, coord, coord, indexing='ij')
        vertices, faces = MarchingCubeHelper(24)(x*x + y*y + z*z - .5)
        mesh = trimesh.Trimesh((vertices * 2 - 1).numpy(), faces.numpy())
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_winding_consistent)
        expected = 4 * math.pi / 3 * math.sqrt(.5)**3
        self.assertGreater(mesh.volume, 0, 'GLB surfaces must face outward.')
        self.assertAlmostEqual(mesh.volume / expected, 1, delta=.025)
        for axis in range(3):
            self.assertAlmostEqual(mesh.bounds[0][axis], -math.sqrt(.5), delta=.015)
            self.assertAlmostEqual(mesh.bounds[1][axis], math.sqrt(.5), delta=.015)
