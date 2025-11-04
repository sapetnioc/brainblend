import numpy as np
import openvdb

volume = np.zeros([30, 30, 30])
volume[20:30, :, 2] = 0.5
volume[:, 20, 10:15] = 0.5
volume[5:10, 5:10, 5:10] = 1
volume[15:20, 15:20, 15:20] = 1

grid = openvdb.FloatGrid()
grid.copyFromArray(volume.astype(float))

grid.transform = openvdb.createLinearTransform(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
)
grid.gridClass = openvdb.GridClass.FOG_VOLUME
grid.name = "density"

openvdb.write("/tmp/test.vdb", grid)
