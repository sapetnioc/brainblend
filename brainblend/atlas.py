"""Packing of a 3D volume into a 2D RGBA "atlas" image.

Blender shader nodes cannot sample 3D textures, so the volume is stored as a
2D float image: groups of 4 consecutive slices along the third voxel axis are
stored in the R, G, B and A channels of one tile, and tiles are laid out on a
grid. A voxel (i, j, k) is found at

    layer = k // 4,  channel = k % 4
    col = layer % cols,  row = layer // cols
    pixel x = col * nx + i,  pixel y = row * ny + j   (y from the bottom row)

Values are normalised to [0, 1] using (vmin, vmax) so that the image keeps the
best precision; shaders map them back to the original units.
"""

import math

import numpy as np

MAX_TEXTURE_SIZE = 16384


class AtlasLayout:
    def __init__(self, shape):
        self.nx, self.ny, self.nz = (int(s) for s in shape)
        self.layers = (self.nz + 3) // 4
        cols = max(1, math.ceil(math.sqrt(self.layers * self.ny / self.nx)))
        rows = math.ceil(self.layers / cols)
        # Prefer the most compact arrangement (fewest empty tiles).
        cols = math.ceil(self.layers / rows)
        self.cols, self.rows = cols, rows
        self.width = cols * self.nx
        self.height = rows * self.ny

    def check(self, max_size=MAX_TEXTURE_SIZE):
        if self.width > max_size or self.height > max_size:
            raise ValueError(
                f"Volume {self.nx}x{self.ny}x{self.nz} needs a {self.width}x{self.height} "
                f"texture, larger than the {max_size} pixel GPU limit"
            )

    def pixel_of(self, i, j, k):
        """(x, y, channel) of voxel (i, j, k) in the atlas (for tests)."""
        layer, channel = divmod(k, 4)
        row, col = divmod(layer, self.cols)
        return col * self.nx + i, row * self.ny + j, channel


def value_range(data):
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin, vmax = float(finite.min()), float(finite.max())
    if vmax <= vmin:
        vmax = vmin + 1.0
    return vmin, vmax


def robust_range(data, low=1.0, high=99.5, max_samples=2_000_000):
    """Percentile window computed on a subsample of the volume."""
    flat = data.ravel()
    step = max(1, flat.size // max_samples)
    sample = flat[::step]
    lo, hi = np.percentile(sample, [low, high])
    if hi <= lo:
        lo, hi = value_range(data)
    return float(lo), float(hi)


def build_atlas(data, vmin=None, vmax=None):
    """Return (layout, pixels) with pixels a float32 array of shape (H, W, 4)."""
    if data.ndim != 3:
        raise ValueError("expected a 3D array")
    layout = AtlasLayout(data.shape)
    layout.check()
    if vmin is None or vmax is None:
        vmin, vmax = value_range(data)
    nx, ny, nz = data.shape
    norm = (np.asarray(data, dtype=np.float32) - np.float32(vmin)) / np.float32(vmax - vmin)
    padded = np.zeros((nx, ny, layout.rows * layout.cols * 4), dtype=np.float32)
    padded[:, :, :nz] = norm
    # (nx, ny, tiles, 4) -> (tiles, ny, nx, 4)
    tiles = padded.reshape(nx, ny, layout.rows * layout.cols, 4).transpose(2, 1, 0, 3)
    # (rows, cols, ny, nx, 4) -> (rows, ny, cols, nx, 4) -> (H, W, 4)
    pixels = (
        tiles.reshape(layout.rows, layout.cols, ny, nx, 4)
        .transpose(0, 2, 1, 3, 4)
        .reshape(layout.height, layout.width, 4)
    )
    return layout, np.ascontiguousarray(pixels)
