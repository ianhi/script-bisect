# Test script with missing imports - simulates GitHub issue script
x = np.array([1], dtype=np.uint32)
y = np.array([1.0], dtype=np.float32)
v = np.array([[1]], dtype=np.uint32)

da_2d = DataArray(v, dims=["x", "y"], coords={"x": x, "y": y})
df_2d = da_2d.to_dataframe(name="v")
print(df_2d.reset_index().dtypes)
