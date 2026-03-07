import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import logging
import warnings

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self):
        pass

    def clean_data(self, data: pd.DataFrame, options: dict = None) -> pd.DataFrame:
        """
        清洗数据，支持自定义配置。
        兼容两套配置键，既可以直接传底层参数，也可以传「页面级」策略：
        - missing_num / missing_cat / outlier / outlier_threshold
        - 或 missing_strategy / outlier_method / outlier_threshold
        """
        if options is None:
            options = {}
            
        # 默认配置（底层粒度）
        defaults = {
            'missing_num': 'median',
            'missing_cat': 'mode', 
            'outlier': 'clip',
            'outlier_threshold': 1.5
        }
        # 合并配置
        cfg = {**defaults, **options}

        # --- 兼容页面级策略映射 ---
        # 缺失值整体策略：none / drop / mean / median / mode / zero
        missing_strategy = options.get('missing_strategy')
        if missing_strategy:
            if missing_strategy == 'none':
                cfg['missing_num'] = 'none'
                cfg['missing_cat'] = 'none'
            elif missing_strategy == 'drop':
                cfg['missing_num'] = 'drop'
                cfg['missing_cat'] = 'drop'
            elif missing_strategy in ('mean', 'median', 'zero'):
                cfg['missing_num'] = missing_strategy
                # 分类变量仍然按众数填充
                cfg['missing_cat'] = 'mode'
            elif missing_strategy == 'mode':
                cfg['missing_cat'] = 'mode'
        
        df = data.copy()
        df = df.drop_duplicates()

        # 1. 处理数值型缺失值
        num_cols = df.select_dtypes(include=[np.number]).columns
        if cfg['missing_num'] == 'none':
            # 不对数值缺失做处理
            pass
        elif cfg['missing_num'] == 'drop':
            df = df.dropna(subset=num_cols)
        elif cfg['missing_num'] == 'zero':
            df[num_cols] = df[num_cols].fillna(0)
        elif cfg['missing_num'] == 'mean':
            for col in num_cols:
                df[col] = df[col].fillna(df[col].mean())
        else: # median (default)
            for col in num_cols:
                df[col] = df[col].fillna(df[col].median())

        # 2. 处理分类型缺失值
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        if cfg['missing_cat'] == 'none':
            # 不对分类缺失做处理
            pass
        elif cfg['missing_cat'] == 'drop':
            df = df.dropna(subset=cat_cols)
        elif cfg['missing_cat'] == 'unknown':
            df[cat_cols] = df[cat_cols].fillna('Unknown')
        else: # mode (default)
            for col in cat_cols:
                mode_val = df[col].mode()
                if not mode_val.empty:
                    df[col] = df[col].fillna(mode_val[0])
                else:
                    df[col] = df[col].fillna('Unknown')

        # 3. 处理异常值 (仅针对数值列)
        # 页面级 outlier_method：none / iqr / zscore
        outlier_method = options.get('outlier_method', 'iqr')
        if outlier_method == 'none' or cfg['outlier'] == 'none':
            pass
        else:
            threshold = float(cfg.get('outlier_threshold', 1.5))
            for col in num_cols:
                series = df[col]
                if series.empty:
                    continue

                if outlier_method == 'iqr':
                    Q1 = series.quantile(0.25)
                    Q3 = series.quantile(0.75)
                    IQR = Q3 - Q1
                    lower = Q1 - threshold * IQR
                    upper = Q3 + threshold * IQR

                    if cfg['outlier'] == 'drop':
                        df = df[(df[col] >= lower) & (df[col] <= upper)]
                    else:  # clip
                        df[col] = series.clip(lower, upper)

                elif outlier_method == 'zscore':
                    # 使用 Z-Score 识别异常值
                    z_raw = np.abs(stats.zscore(series.dropna()))
                    z = pd.Series(np.nan, index=series.index)
                    z.loc[series.dropna().index] = z_raw.values
                    if cfg['outlier'] == 'drop':
                        df = df[z.fillna(0) < threshold]
                    else:  # clip：将超出阈值的值截断到边界
                        # 计算在阈值内的最小/最大值
                        valid = series[z < threshold]
                        if valid.empty:
                            continue
                        lower, upper = valid.min(), valid.max()
                        df[col] = series.clip(lower, upper)

        # 4. 类型自动转换
        for column in df.columns:
            if df[column].dtype == 'object':
                try:
                    raw_series = df[column]
                    non_empty_mask = raw_series.notna() & raw_series.astype(str).str.strip().ne('')
                    if non_empty_mask.any():
                        numeric_series = pd.to_numeric(raw_series, errors='coerce')
                        numeric_success = int(numeric_series[non_empty_mask].notna().sum())
                        if numeric_success >= max(1, int(non_empty_mask.sum() * 0.8)):
                            df[column] = numeric_series
                            continue
                except Exception:
                    pass
            if df[column].dtype == 'object':
                try:
                    raw_series = df[column]
                    non_empty_mask = raw_series.notna() & raw_series.astype(str).str.strip().ne('')
                    if non_empty_mask.any():
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', FutureWarning)
                            warnings.simplefilter('ignore', UserWarning)
                            datetime_series = pd.to_datetime(raw_series, errors='coerce')
                        datetime_success = int(datetime_series[non_empty_mask].notna().sum())
                        if datetime_success >= max(1, int(non_empty_mask.sum() * 0.8)):
                            df[column] = datetime_series
                except Exception:
                    pass

        # 移除单一值列
        df = df.loc[:, df.nunique() > 1]
        
        return df.reset_index(drop=True)

    def standardize_data(self, data: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        standardized_data = data.copy()
        numeric_columns = standardized_data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == 0:
            return standardized_data
        if method == 'standard':
            scaler = StandardScaler()
            standardized_data[numeric_columns] = scaler.fit_transform(standardized_data[numeric_columns])
        elif method == 'minmax':
            scaler = MinMaxScaler()
            standardized_data[numeric_columns] = scaler.fit_transform(standardized_data[numeric_columns])
        else:
            raise ValueError("不支持的标准化方法。请选择 'standard' 或 'minmax'")
        return standardized_data

    def transform_data(self, data: pd.DataFrame, method: str = 'none') -> pd.DataFrame:
        """
        变量变换：
        - none    : 不变换
        - log     : 自然对数变换，对非正数自动跳过
        - boxcox  : Box-Cox 变换，仅对 >0 的变量生效
        """
        transformed = data.copy()
        numeric_columns = transformed.select_dtypes(include=[np.number]).columns
        if method == 'none' or len(numeric_columns) == 0:
            return transformed

        for col in numeric_columns:
            series = transformed[col]
            if method == 'log':
                # 对 >0 的值做 log1p，其余保持不变
                positive_mask = series > 0
                transformed.loc[positive_mask, col] = np.log1p(series[positive_mask])
            elif method == 'boxcox':
                positive_mask = series > 0
                if positive_mask.sum() < 2:
                    continue
                try:
                    transformed_vals, _ = stats.boxcox(series[positive_mask])
                    transformed.loc[positive_mask, col] = transformed_vals
                except Exception:
                    # 个别列无法做 boxcox 时静默跳过
                    continue

        return transformed

    def encode_categorical(self, data: pd.DataFrame) -> pd.DataFrame:
        encoded_data = data.copy()
        for column in encoded_data.select_dtypes(include=['object']).columns:
            if encoded_data[column].nunique() < 10:
                encoded_data[column] = pd.Categorical(encoded_data[column]).codes
            else:
                dummies = pd.get_dummies(encoded_data[column], prefix=column)
                encoded_data = pd.concat([encoded_data.drop(column, axis=1), dummies], axis=1)
        return encoded_data

    def calculate_data_profile(self, data: pd.DataFrame) -> dict:
        if data is None or data.empty or len(data.columns) == 0:
            return {
                'shape': (0, 0),
                'columns': [],
                'dtypes': {},
                'missing_values': {},
                'numeric_stats': {},
                'categorical_stats': {}
            }
            
        profile = {
            'shape': data.shape,
            'columns': data.columns.tolist(),
            'dtypes': data.dtypes.astype(str).to_dict(),
            'missing_values': data.isnull().sum().to_dict(),
            'numeric_stats': {},
            'categorical_stats': {}
        }
        
        # 仅对存在的数值列进行描述，且确保列数大于 0
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if not numeric_cols.empty and len(numeric_cols) > 0:
            # describe() on empty DF with columns might still fail in some pandas versions if no actual data exists
            try:
                profile['numeric_stats'] = data[numeric_cols].describe().to_dict()
            except Exception as e:
                logger.warning(f"Error describing numeric columns: {e}")
                profile['numeric_stats'] = {}
            
        categorical_cols = data.select_dtypes(include=['object', 'category', 'string']).columns
        if not categorical_cols.empty:
            for col in categorical_cols:
                try:
                    profile['categorical_stats'][col] = {
                        'unique_count': int(data[col].nunique()),
                        'top_values': data[col].value_counts().head(10).to_dict()
                    }
                except Exception:
                    continue
        return profile

    def validate_data_integrity(self, data: pd.DataFrame) -> dict:
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        if data.empty:
            validation_result['is_valid'] = False
            validation_result['errors'].append("数据为空")
            return validation_result
        duplicate_count = data.duplicated().sum()
        if duplicate_count > 0:
            validation_result['warnings'].append(f"发现 {duplicate_count} 行完全重复的数据")
        missing_data = data.isnull().sum()
        if missing_data.sum() > 0:
            missing_cols = missing_data[missing_data > 0].index.tolist()
            validation_result['warnings'].append(f"以下列存在缺失值: {missing_cols}")
        for col in data.columns:
            try:
                pd.to_numeric(data[col], errors='raise')
            except:
                pass
        return validation_result

    def detect_multicollinearity(self, data: pd.DataFrame) -> dict:
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty or numeric_data.shape[1] < 2:
            return {'correlation_matrix': {}, 'high_correlation_pairs': []}
        correlation_matrix = numeric_data.corr().abs()
        upper_triangle = correlation_matrix.where(
            np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
        )
        high_corr_pairs = [
            (row, col, float(correlation_matrix.loc[row, col]))
            for row in correlation_matrix.columns
            for col in correlation_matrix.columns
            if pd.notna(upper_triangle.loc[row, col]) and upper_triangle.loc[row, col] > 0.8
        ]
        return {
            'correlation_matrix': correlation_matrix.to_dict(),
            'high_correlation_pairs': high_corr_pairs
        }

# =======================================================
# 👇 这里是重点！这就是为什么报错的原因！
#    你之前可能漏掉了这几行实例化代码。
# =======================================================
data_service = DataService()
clean_data = data_service.clean_data
standardize_data = data_service.standardize_data