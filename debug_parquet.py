import pyarrow.parquet as pq
import pyarrow as pa
import numpy as np
arr = pa.array([1, 2, np.nan, 3])
print(arr)
print(arr.type)
arr = arr.cast(pa.int16(), safe=False)
print(arr)
print(arr.type)
fill_value = pa.scalar(5, type=pa.float64())
arr = arr.fill_null(fill_value)
print(arr)
arr = arr.if_else(arr, 0, 1)
print(arr)
# arr = pa.array([1, 2, None, 4, None])
# arr.fill_null(pa.array([10, 20, 30, 40, 50]))

# Open the Parquet file
file = pq.ParquetFile('/home/ben/LEXIMPACT/openfisca-survey-manager/openfisca_survey_manager/tests/data_files/test_multiple_parquet_collection/person/person-0.parquet')

# Get the metadata of the file
metadata = file.metadata

# Get the number of row groups
num_row_groups = metadata.num_row_groups

# Print the number of row groups
print(f'Number of row groups: {num_row_groups}')

# Get the schema of the file
schema = file.schema

# Print the schema
# print("schema", schema)
print(f'Number of columns: {len(schema)}')
for field in schema:
    print(f'  {field.name}: {field.physical_type}')

# Iterate over the row groups and print their metadata
for i in [0, num_row_groups-1]:
    rg = metadata.row_group(i)
    print(f'Row Group {i}:')
    print(f'  Row count: {rg.num_rows}')
    print(f'  Total byte size: {rg.total_byte_size} bytes')


