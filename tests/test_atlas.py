import numpy as np

from brainblend import atlas, volume


def test_atlas_roundtrip():
    rng = np.random.default_rng(0)
    data = rng.random((7, 5, 11)).astype(np.float32)
    layout, pixels = atlas.build_atlas(data, 0.0, 1.0)
    assert pixels.shape == (layout.height, layout.width, 4)
    for i in range(7):
        for j in range(5):
            for k in range(11):
                x, y, c = layout.pixel_of(i, j, k)
                assert pixels[y, x, c] == data[i, j, k]


def test_typical_sizes_fit_gpu():
    for shape in [(256, 256, 180), (512, 512, 300), (512, 512, 512)]:
        layout = atlas.AtlasLayout(shape)
        layout.check()
        assert layout.cols * layout.rows * 4 >= shape[2]


def test_split_affine_with_shear_and_flip():
    a = np.array([[-0.9, 0.2, 0.0, 10.0], [0.1, 1.1, 0.3, -5.0], [0.0, -0.2, 2.5, 3.0], [0, 0, 0, 1]])
    obj, residual = volume.split_affine(a)
    rot = obj[:3, :3]
    assert np.allclose(rot @ rot.T, np.eye(3))
    assert np.isclose(np.linalg.det(rot), 1.0)
    assert np.allclose(obj @ residual, a)
