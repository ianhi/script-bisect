# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "zarr==3.0.8"
# ]
# ///
#
# This script automatically imports the development branch of zarr to check for issues

from zarr.codecs import BloscCodec

b = BloscCodec()
b.to_dict()
# ValueError: `typesize` needs to be set for serialization.
