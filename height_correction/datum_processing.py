"""GPS height from datum files with pressure data"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib import cm
from matplotlib.colors import Normalize

from config import DATA_DIR, DATUM_FILES


#### Manually tuned filtering parameters ####

cutoff = 2e-3  # Hz
slope = 12  # db per octave


#### Helper functions ####


def datum_datetime(df: pd.DataFrame):
    """Parse datetime object from several columns in datum

    Args:
        df (pd.DataFrame): read from datum .csv file

    Returns:
        pd.Series: parsed datetime64 Series
    """
    datetime = (
        df.loc[:, "time"]
        .astype(str)
        .str.cat(
            others=[
                df.loc[:, "year"].astype(str),
                df.loc[:, "month"].astype(str).apply(lambda s: s.rjust(2, "0")),
                df.loc[:, "day"].astype(str).apply(lambda s: s.rjust(2, "0")),
            ],
            sep=" ",
        )
    )

    datetime = pd.to_datetime(datetime, format=r"%H%M%S %Y %m %d")
    datetime.name = "datetime"

    return datetime


def validate_chunk(ch: pd.DataFrame) -> bool:
    """Check chunk validity for processing

    Args:
        ch (pd.DataFrame): chunk generated by continuous_chunks

    Returns:
        bool: validity flag
    """
    H = ch.loc[:, "H"].to_numpy()
    if H.size < 10:
        return False
    if np.std(H) < 1:
        return False
    return True


def continuous_intervals(df: pd.DataFrame, dt_tolerance_medians: int = 100):
    """Generator function to extrat continuous periods of time from datum

    Args:
        df (pd.DataFrame): read from datum .csv file
        dt_tolerance_medians (int): chunk break is set when timedelta
            between subsequent measurements exceeds median delta multiplied
            by this argument

    Yields:
        pd.DataFrame: copy of current time interval from df
    """
    if "datetime" not in df.columns:
        datetime = datum_datetime(df)
        df.drop(columns=["year", "month", "day", "time"], inplace=True)
        df.insert(0, "datetime", datetime)
    else:
        datetime = df.loc[:, "datetime"]

    timedeltas = np.diff(datetime.to_numpy())
    time_step = np.median(timedeltas)
    chunk_breaks = np.where(timedeltas > time_step * dt_tolerance_medians)

    chunk_breaks = list(chunk_breaks[0] + 1)
    chunk_breaks.append(df.shape[0])
    chunk_breaks.insert(0, 0)
    for chunk_start, chunk_end in zip(chunk_breaks[:-1], chunk_breaks[1:]):
        ch = df.iloc[chunk_start:chunk_end, :]
        if validate_chunk(ch):
            yield ch


def intervals_from_datum_files():
    for datum_file in DATUM_FILES:
        df = pd.read_csv(DATA_DIR + datum_file)
        for ch in continuous_intervals(df):
            yield ch
