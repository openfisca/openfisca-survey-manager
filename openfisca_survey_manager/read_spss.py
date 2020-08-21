
from pandas import DataFrame
try:
    from savReaderWriter import SavReader
except ModuleNotFoundError:
    pass


def read_spss(spss_file_path):
    with SavReader(spss_file_path, returnHeader=True) as reader:
        for record in reader:
            print(record)
            # records_got.append(record)

    data_frame = DataFrame(list(SavReader(spss_file_path)))
    print(data_frame.info())

    return data_frame
