# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray@git+https://github.com/pydata/xarray.git@main",
#   "cloudpickle",
#   "s3fs",
#   "h5netcdf",
#   "cftime",
#   "dask",
# ]
# ///

import cloudpickle
import s3fs

print("pre import")
import xarray as xr

print("post import")
#   "cftime",
s3 = s3fs.S3FileSystem(anon=True)
fname = (
    "s3://earthmover-sample-data/netcdf/tas_Amon_GFDL-ESM4_hist-piNTCF_r1i1p1f1_gr1.nc"
)
ds = xr.open_dataset(s3.open(fname), engine="h5netcdf", chunks={})
cloudpickle.loads(cloudpickle.dumps(ds))
