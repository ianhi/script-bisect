#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     # "zarr==3.0.2,<3.0.3", # WORKS
#     "zarr==3.0.2", # FAILS
#     "numcodecs==0.15.0",
#     "zfpy==1.0.1",
#     "pcodec==0.3.2",
# ]
# ///

import numpy as np
import zarr
from numcodecs.zarr3 import ZFPY, PCodec

for serializer in [ZFPY(mode=4, tolerance=0.01), PCodec(level=8, mode_spec="auto")]:
    array = zarr.create_array(
        store=zarr.storage.MemoryStore(),
        shape=[2, 2],
        chunks=[2, 1],
        dtype=np.float32,
        serializer=serializer,
    )
    array[...] = np.array([[0, 1], [2, 3]])
