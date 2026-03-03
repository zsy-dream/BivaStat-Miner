import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from typing import Dict, Any, Optional, Tuple, List
from core.logging import logger

class DataService:
    def __init__(self):
        self.scaler = StandardScaler()
        self.min_max_scaler = MinMaxScaler()

    def clean_data(self, data: pd.DataFrame, options: Dict[str, Any] = None) -> pd.DataFrame:
        """
        清洗数据，支持缺失值填充、重复值删除、异常值处理。
        """
        if options is None:
            options = {}
            
        cfg = {
            'missing_num': options.get('missing_num', 'median'),
            'missing_cat': options.get('missing_cat', 'mode'), 
            'outlier': options.get('outlier', 'clip'),
            'outlier_threshold': float(options.get('outlier_threshold', 1.5))
        }

        # 映射页面级 strategy
        strategy = options.get('missing_strategy')
        if strategy:
            if strategy == 'none':
                cfg['missing_num'] = 'none'
                cfg['missing_cat'] = 'none'
            elif strategy == 'drop':
                cfg['missing_num'] = 'drop'
                cfg['missing_cat'] = 'drop'
            elif strategy in ('mean', 'median', 'zero'):
                cfg['missing_num'] = strategy
                cfg['missing_cat'] = 'mode'
        
        df = data.copy()
        initial_shape = df.shape
        df = df.drop_duplicates()
        if df.shape != initial_shape:
            logger.info(f"Removed {initial_shape[0] - df.shape[0]} duplicate rows.")

        # 1. 数值型缺失值
        num_cols = df.select_dtypes(include=[np.number]).columns
        if cfg['missing_num'] == 'drop':
            df = df.dropna(subset=num_cols)
        elif cfg['missing_num'] == 'zero':
            df[num_cols] = df[num_cols].fillna(0)
        elif cfg['missing_num'] == 'mean':
            for col in num_cols:
                df[col] = df[col].fillna(df[col].mean())
        elif cfg['missing_num'] == 'median':
            for col in num_cols:
                df[col] = df[col].fillna(df[col].median())

        # 2. 分类型缺失值
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        if cfg['missing_cat'] == 'drop':
            df = df.dropna(subset=cat_cols)
        elif cfg['missing_cat'] == 'mode':
            for col in cat_cols:
                mode_val = df[col].mode()
                if not mode_val.empty:
                    df[col] = df[col].fillna(mode_val[0])
                else:
                    df[col] = df[col].fillna('Unknown')

        # 3. 异常值处理
        outlier_method = options.get('outlier_method', 'iqr')
        if outlier_method != 'none' and cfg['outlier'] != 'none':
            threshold = cfg['outlier_threshold']
            for col in num_cols:
                series = df[col]
                if series.empty: continue

                if outlier_method == 'iqr':
                    q1, q3 = series.quantile([0.25, 0.75])
                    iqr = q3 - q1
                    lower, upper = q1 - threshold * iqr, q3 + threshold * iqr
                    if cfg['outlier'] == 'drop':
                        df = df[(df[col] >= lower) & (df[col] <= upper)]
                    else:
                        df[col] = series.clip(lower, upper)
                elif outlier_method == 'zscore':
                    z = np.abs(stats.zscore(series, nan_policy='omit'))
                    if cfg['outlier'] == 'drop':
                        df = df[z < threshold]
                    else:
                        valid = series[z < threshold]
                        if not valid.empty:
                            df[col] = series.clip(valid.min(), valid.max())

        # 4. 自动转换与过滤
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = pd.to_numeric(df[col], errors='ignore')
        
        # 移除单一值列
        df = df.loc[:, df.nunique() > 1]
        
        return df.reset_index(drop=True)

    def standardize_data(self, data: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        df = data.copy()
        num_cols = df.select_dtypes(include=[np.number]).columns
        if not num_cols.empty:
            scaler = StandardScaler() if method == 'standard' else MinMaxScaler()
            df[num_cols] = scaler.fit_transform(df[num_cols])
        return df

    def calculate_data_profile(self, data: pd.DataFrame) -> Dict[str, Any]:
        return {
            'shape': data.shape,
            'columns': data.columns.tolist(),
            'dtypes': data.dtypes.astype(str).to_dict(),
            'missing_values': data.isnull().sum().to_dict(),
            'numeric_stats': data.select_dtypes(include=[np.number]).describe().to_dict()
        }

    def validate_data_integrity(self, data: pd.DataFrame) -> Dict[str, Any]:
        warnings = []
        if data.empty: return {'is_valid': False, 'errors': ["数据为空"], 'warnings': []}
        
        dups = data.duplicated().sum()
        if dups > 0: warnings.append(f"发现 {dups} 行重复数据")
        
        missing = data.isnull().sum()
        if missing.sum() > 0:
            cols = missing[missing > 0].index.tolist()
            warnings.append(f"以下列存在缺失: {cols}")
            
        return {'is_valid': True, 'errors': [], 'warnings': warnings}

data_service = DataService()
