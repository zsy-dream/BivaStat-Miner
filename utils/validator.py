import pandas as pd
import numpy as np


def check_completeness(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    # 简单逻辑：如果没有空值就算完整
    return not df.isnull().values.any()


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    numeric_data = df.select_dtypes(include=[np.number])
    if numeric_data.empty:
        return pd.DataFrame()

    Q1 = numeric_data.quantile(0.25)
    Q3 = numeric_data.quantile(0.75)
    IQR = Q3 - Q1

    outlier_condition = ((numeric_data < (Q1 - 1.5 * IQR)) | (numeric_data > (Q3 + 1.5 * IQR))).any(axis=1)
    return df[outlier_condition]