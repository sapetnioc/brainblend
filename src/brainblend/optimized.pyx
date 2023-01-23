import numpy as np

def array_to_rgba(array):
    min: float = array.min()
    max: float = array.max()
    result = np.empty(array.shape + (4,), dtype=np.float32)
    for z in range(array.shape[0]):
        for y in range(array.shape[1]):
            for x in range(array.shape[2]):
                v: float = (array[z, y, x] - min) / (max - min)
                result[z, y, x] = [v, v, v, 1.0]
    return result