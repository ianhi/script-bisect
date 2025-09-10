# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "xarray",
#     "zarr",
# ]
# ///

import numpy as np
import xarray as xr

data = xr.DataArray(
    data=np.zeros((2, 2)),
    dims=["x", "y"],
    coords=dict(y=np.array(["a", "b"], dtype=object)),
)
data.to_zarr("test.zarr", mode="w")
data = xr.open_zarr("test.zarr")
data.to_zarr("test2.zarr", mode="w")
# File "numcodecs/vlen.pyx", line 104, in numcodecs.vlen.VLenUTF8.encode
# TypeError: expected unicode string, found 2
