import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, PowerTransformer
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.feature_selection import SelectKBest, f_classif, f_regression, mutual_info_classif
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
import logging
from typing import Dict, Any, List, Tuple, Optional
from utils.error_handler import DataException, ValidationException

logger = logging.getLogger(__name__)

class EnhancedPreprocessingService:
    """增强的数据预处理服务，提供全面的数据清洗和转换功能"""
    
    def __init__(self):
        # 工厂方法，每次调用生成新实例，避免多次 fit 复用旧状态
        self._scaler_factories = {
            'standard': lambda: StandardScaler(),
            'minmax': lambda: MinMaxScaler(),
            'robust': lambda: RobustScaler(),
            'power': lambda: PowerTransformer(method='yeo-johnson')
        }
        self._imputer_factories = {
            'mean': lambda: SimpleImputer(strategy='mean'),
            'median': lambda: SimpleImputer(strategy='median'),
            'mode': lambda: SimpleImputer(strategy='most_frequent'),
            'constant': lambda: SimpleImputer(strategy='constant', fill_value=0),
            'knn': lambda: KNNImputer(n_neighbors=5)
        }
    
    def comprehensive_preprocessing(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """综合预处理流程（兼容前端参数名）"""
        try:
            result = {
                'original_shape': df.shape,
                'steps_applied': [],
                'processing_log': [],
                'final_df': df.copy()
            }
            
            # --- 参数名映射与补全 ---
            # 1. 缺失值
            mv_cfg = config.get('missing_values', config.get('missing_value', {}))
            if mv_cfg and mv_cfg.get('strategy', mv_cfg.get('method', 'none')) != 'none':
                # 兼容 strategy -> method
                if 'strategy' in mv_cfg:
                    mv_cfg['method'] = mv_cfg['strategy']
                mv_cfg['enabled'] = True
                result['final_df'] = self.handle_missing_values(result['final_df'], mv_cfg)
                result['steps_applied'].append('missing_value_handling')
                result['processing_log'].append(f"完成缺失值处理 ({mv_cfg['method']})")
            
            # 2. 异常值
            ol_cfg = config.get('outliers', config.get('outlier_detection', {}))
            if ol_cfg and ol_cfg.get('method', 'none') != 'none':
                ol_cfg['enabled'] = True
                result['final_df'] = self.handle_outliers(result['final_df'], ol_cfg)
                result['steps_applied'].append('outlier_handling')
                result['processing_log'].append(f"完成异常值处理 ({ol_cfg['method']})")
                
            # 3. 标准化
            nm_cfg = config.get('normalize', config.get('normalization', {}))
            if nm_cfg and nm_cfg.get('method', 'none') != 'none':
                nm_cfg['enabled'] = True
                result['final_df'] = self.normalize_data(result['final_df'], nm_cfg)
                result['steps_applied'].append('normalization')
                result['processing_log'].append(f"完成数据标准化 ({nm_cfg['method']})")

            # 4. 特征编码
            enc_cfg = config.get('encode', config.get('encoding', {}))
            if enc_cfg and enc_cfg.get('method', 'none') != 'none':
                enc_method = enc_cfg.get('method', 'auto')
                if enc_method == 'auto':
                    result['final_df'] = self._auto_encode_categorical_features(result['final_df'], enc_cfg)
                    result['processing_log'].append("完成特征编码 (auto: 低基数 One-Hot / 高基数 Label)")
                else:
                    result['final_df'] = self.encode_categorical_features(result['final_df'], enc_cfg)
                    result['processing_log'].append(f"完成特征编码 ({enc_method})")
                result['steps_applied'].append('encoding')
            
            # 5. 特征选择
            fs_cfg = config.get('feature_selection', {})
            if fs_cfg.get('enabled', False):
                result['final_df'] = self.select_features(result['final_df'], fs_cfg)
                result['steps_applied'].append('feature_selection')
                result['processing_log'].append("完成特征选择")
            
            # 6. 降维处理
            dr_cfg = config.get('dimensionality_reduction', {})
            if dr_cfg.get('enabled', False):
                result['final_df'] = self.reduce_dimensions(result['final_df'], dr_cfg)
                result['steps_applied'].append('dimensionality_reduction')
                result['processing_log'].append("完成降维处理")
            
            result['final_shape'] = result['final_df'].shape
            result['success'] = True
            
            return result
            
        except Exception as e:
            logger.error(f"综合预处理失败: {str(e)}")
            raise DataException(f"综合预处理失败: {str(e)}")

    def _auto_encode_categorical_features(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """自动编码：低基数做 One-Hot，高基数做 Label 编码"""
        result_df = df.copy()
        columns = config.get('columns', []) or result_df.select_dtypes(include=['object', 'category']).columns.tolist()
        threshold = int(config.get('onehot_threshold', 12) or 12)

        for col in columns:
            if col not in result_df.columns:
                continue
            unique_count = int(result_df[col].nunique(dropna=True))
            if unique_count <= threshold:
                dummies = pd.get_dummies(result_df[col], prefix=col, drop_first=config.get('drop_first', False))
                result_df = pd.concat([result_df.drop(col, axis=1), dummies], axis=1)
            else:
                result_df[col] = pd.Categorical(result_df[col]).codes
        return result_df
    
    def assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """评估数据质量并计算评分"""
        try:
            quality_report = {
                'basic_info': {
                    'shape': df.shape,
                    'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
                    'dtypes': {str(k): int(v) for k, v in df.dtypes.value_counts().to_dict().items()}
                },
                'missing_values': {},
                'duplicates': {},
                'outliers': {},
                'data_consistency': {},
                'overall_score': 100.0
            }
            
            # 缺失值分析
            missing_analysis = df.isnull().sum()
            total_missing = int(missing_analysis.sum())
            missing_percentage = (missing_analysis / len(df)) * 100
            quality_report['missing_values'] = {
                'total_missing': total_missing,
                'missing_percentage_by_column': {k: float(v) for k, v in missing_percentage.to_dict().items()},
                'columns_with_missing': missing_analysis[missing_analysis > 0].index.tolist(),
                'high_missing_columns': missing_percentage[missing_percentage > 50].index.tolist()
            }
            
            # 扣分：缺失值 (每1%扣2分)
            avg_missing_rate = (total_missing / (df.shape[0] * df.shape[1])) if df.size > 0 else 0
            quality_report['overall_score'] -= (avg_missing_rate * 200)
            
            # 重复值分析
            duplicates_count = df.duplicated().sum()
            quality_report['duplicates'] = {
                'total_duplicates': duplicates_count,
                'duplicate_percentage': (duplicates_count / len(df)) * 100
            }
            
            # 异常值分析（仅数值列）
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            outlier_info = {}
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                outlier_info[col] = {
                    'count': len(outliers),
                    'percentage': (len(outliers) / len(df)) * 100,
                    'bounds': {'lower': lower_bound, 'upper': upper_bound}
                }
            quality_report['outliers'] = outlier_info
            
            # 数据一致性检查
            consistency_issues = []
            
            # 检查负值在应该为正值的列
            for col in numeric_cols:
                if 'amount' in col.lower() or 'price' in col.lower() or 'quantity' in col.lower():
                    negative_count = (df[col] < 0).sum()
                    if negative_count > 0:
                        consistency_issues.append(f"{col}: {negative_count} 个负值")
            
            # 检查日期列的异常值
            date_cols = df.select_dtypes(include=['datetime64']).columns
            for col in date_cols:
                future_dates = (df[col] > pd.Timestamp.now()).sum()
                if future_dates > 0:
                    consistency_issues.append(f"{col}: {future_dates} 个未来日期")
            
            quality_report['data_consistency'] = {
                'issues_found': consistency_issues,
                'issue_count': len(consistency_issues)
            }
            
            return quality_report
            
        except Exception as e:
            logger.error(f"数据质量评估失败: {str(e)}")
            raise DataException(f"数据质量评估失败: {str(e)}")
    
    def handle_missing_values(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """处理缺失值"""
        try:
            method = config.get('method', 'median')
            threshold = config.get('threshold', 0.5)  # 缺失值比例阈值
            
            result_df = df.copy()
            
            # 删除缺失值比例过高的列
            missing_ratio = df.isnull().sum() / len(df)
            cols_to_drop = missing_ratio[missing_ratio > threshold].index.tolist()
            if cols_to_drop:
                result_df = result_df.drop(columns=cols_to_drop)
                logger.info(f"删除缺失值比例过高的列: {cols_to_drop}")
            
            # 按列类型处理缺失值
            numeric_cols = result_df.select_dtypes(include=[np.number]).columns
            categorical_cols = result_df.select_dtypes(include=['object', 'category']).columns
            
            if method in ['mean', 'median', 'mode', 'constant', 'knn']:
                if len(numeric_cols) > 0:
                    if method == 'knn':
                        imputer = KNNImputer(n_neighbors=config.get('knn_neighbors', 5))
                        result_df[numeric_cols] = imputer.fit_transform(result_df[numeric_cols])
                    else:
                        strategy = 'most_frequent' if method == 'mode' else method
                        fill_value = config.get('fill_value', 0) if method == 'constant' else None
                        imputer = SimpleImputer(strategy=strategy, fill_value=fill_value)
                        result_df[numeric_cols] = imputer.fit_transform(result_df[numeric_cols])
                
                # 分类变量使用众数填充
                if len(categorical_cols) > 0:
                    for col in categorical_cols:
                        mode_value = result_df[col].mode()
                        if not mode_value.empty:
                            result_df[col] = result_df[col].fillna(mode_value[0])
                        else:
                            result_df[col] = result_df[col].fillna('Unknown')
            
            elif method == 'drop':
                # 删除包含缺失值的行
                result_df = result_df.dropna()
            
            elif method == 'forward_fill':
                # 前向填充
                result_df = result_df.ffill()
            
            elif method == 'backward_fill':
                # 后向填充
                result_df = result_df.bfill()
            
            return result_df
            
        except Exception as e:
            logger.error(f"缺失值处理失败: {str(e)}")
            raise DataException(f"缺失值处理失败: {str(e)}")
    
    def handle_outliers(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """处理异常值"""
        try:
            method = config.get('method', 'iqr')
            action = config.get('action', 'clip')  # 'clip', 'remove', 'transform'
            
            result_df = df.copy()
            numeric_cols = result_df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                if method == 'iqr':
                    Q1 = result_df[col].quantile(0.25)
                    Q3 = result_df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                elif method == 'zscore':
                    z_scores = np.abs(stats.zscore(result_df[col].dropna()))
                    threshold = config.get('zscore_threshold', 3)
                    lower_bound = result_df[col].mean() - threshold * result_df[col].std()
                    upper_bound = result_df[col].mean() + threshold * result_df[col].std()
                    
                elif method == 'dbscan':
                    # 使用DBSCAN检测异常值
                    data_reshaped = result_df[col].dropna().values.reshape(-1, 1)
                    dbscan = DBSCAN(eps=config.get('eps', 0.5), min_samples=config.get('min_samples', 5))
                    clusters = dbscan.fit_predict(data_reshaped)
                    outliers_mask = clusters == -1
                    
                    if action == 'remove':
                        outlier_indices = result_df[col].dropna().index[outliers_mask]
                        result_df = result_df.drop(outlier_indices)
                    continue
                
                else:
                    continue
                
                # 处理异常值
                if action == 'clip':
                    result_df[col] = result_df[col].clip(lower_bound, upper_bound)
                elif action == 'remove':
                    result_df = result_df[(result_df[col] >= lower_bound) & (result_df[col] <= upper_bound)]
                elif action == 'transform':
                    # 使用对数变换减少异常值影响
                    if (result_df[col] > 0).all():
                        result_df[col] = np.log1p(result_df[col])
            
            return result_df
            
        except Exception as e:
            logger.error(f"异常值处理失败: {str(e)}")
            raise DataException(f"异常值处理失败: {str(e)}")
    
    def normalize_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """数据标准化/归一化"""
        try:
            method = config.get('method', 'standard')
            columns = config.get('columns', [])  # 指定列，空则处理所有数值列
            
            result_df = df.copy()
            
            if not columns:
                columns = result_df.select_dtypes(include=[np.number]).columns.tolist()
            
            if method in self._scaler_factories:
                scaler = self._scaler_factories[method]()
                result_df[columns] = scaler.fit_transform(result_df[columns])
            else:
                raise ValidationException(f"不支持的标准化方法: {method}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"数据标准化失败: {str(e)}")
            raise DataException(f"数据标准化失败: {str(e)}")
    
    def encode_categorical_features(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """编码分类特征"""
        try:
            method = config.get('method', 'onehot')
            columns = config.get('columns', [])  # 指定列，空则处理所有分类列
            
            result_df = df.copy()
            
            if not columns:
                columns = result_df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            for col in columns:
                if col not in result_df.columns:
                    continue
                
                if method == 'onehot':
                    # 独热编码
                    dummies = pd.get_dummies(result_df[col], prefix=col, drop_first=config.get('drop_first', False))
                    result_df = pd.concat([result_df.drop(col, axis=1), dummies], axis=1)
                    
                elif method == 'label':
                    # 标签编码
                    result_df[col] = pd.Categorical(result_df[col]).codes
                    
                elif method == 'target':
                    # 目标编码（需要目标变量）
                    target_col = config.get('target_column')
                    if target_col and target_col in result_df.columns:
                        # 添加空值检查防止 NoneType groups 错误
                        if result_df is None or result_df.empty:
                            raise ValidationException("数据为空，无法进行目标编码")
                        if col not in result_df.columns or target_col not in result_df.columns:
                            raise ValidationException(f"指定的列不存在: {col}, {target_col}")
                        target_mean = result_df.groupby(col)[target_col].mean()
                        result_df[f'{col}_target_encoded'] = result_df[col].map(target_mean)
                        result_df = result_df.drop(col, axis=1)
            
            return result_df
            
        except Exception as e:
            logger.error(f"特征编码失败: {str(e)}")
            raise DataException(f"特征编码失败: {str(e)}")
    
    def select_features(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """特征选择"""
        try:
            method = config.get('method', 'univariate')
            k = config.get('k', 10)
            target_col = config.get('target_column')
            
            if not target_col or target_col not in df.columns:
                logger.warning("未指定目标列，跳过特征选择")
                return df
            
            result_df = df.copy()
            X = result_df.drop(columns=[target_col])
            y = result_df[target_col]
            
            # 只选择数值特征进行选择
            numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
            X_numeric = X[numeric_features]
            
            if method == 'univariate':
                if y.dtype == 'object' or len(y.unique()) < 20:  # 分类问题
                    selector = SelectKBest(score_func=f_classif, k=min(k, len(numeric_features)))
                else:  # 回归问题
                    selector = SelectKBest(score_func=f_regression, k=min(k, len(numeric_features)))
                
                X_selected = selector.fit_transform(X_numeric, y)
                selected_features = [numeric_features[i] for i in selector.get_support(indices=True)]
                
                # 保留非数值特征和选中的数值特征
                non_numeric_features = [col for col in X.columns if col not in numeric_features]
                final_features = non_numeric_features + selected_features
                
                result_df = result_df[final_features + [target_col]]
            
            elif method == 'mutual_info':
                selector = SelectKBest(score_func=mutual_info_classif, k=min(k, len(numeric_features)))
                X_selected = selector.fit_transform(X_numeric, y)
                selected_features = [numeric_features[i] for i in selector.get_support(indices=True)]
                
                non_numeric_features = [col for col in X.columns if col not in numeric_features]
                final_features = non_numeric_features + selected_features
                
                result_df = result_df[final_features + [target_col]]
            
            return result_df
            
        except Exception as e:
            logger.error(f"特征选择失败: {str(e)}")
            raise DataException(f"特征选择失败: {str(e)}")
    
    def reduce_dimensions(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """降维处理"""
        try:
            method = config.get('method', 'pca')
            n_components = config.get('n_components', 0.95)  # 可以是整数或解释方差比例
            
            result_df = df.copy()
            numeric_cols = result_df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) < 2:
                logger.warning("数值特征少于2个，跳过降维")
                return result_df
            
            X = result_df[numeric_cols]
            
            if method == 'pca':
                pca = PCA(n_components=n_components)
                X_pca = pca.fit_transform(X)
                
                # 创建新的列名
                if isinstance(n_components, int):
                    pca_cols = [f'PC{i+1}' for i in range(n_components)]
                else:
                    pca_cols = [f'PC{i+1}' for i in range(X_pca.shape[1])]
                
                pca_df = pd.DataFrame(X_pca, columns=pca_cols, index=result_df.index)
                
                # 保留非数值特征
                non_numeric_cols = [col for col in result_df.columns if col not in numeric_cols]
                result_df = pd.concat([result_df[non_numeric_cols], pca_df], axis=1)
            
            return result_df
            
        except Exception as e:
            logger.error(f"降维处理失败: {str(e)}")
            raise DataException(f"降维处理失败: {str(e)}")
    
    def generate_preprocessing_report(self, preprocessing_result: Dict[str, Any]) -> str:
        """生成预处理报告"""
        try:
            report = []
            report.append("# 数据预处理报告\n")
            
            # 基本信息
            report.append("## 基本信息")
            report.append(f"- 原始数据形状: {preprocessing_result['original_shape']}")
            report.append(f"- 处理后数据形状: {preprocessing_result['final_shape']}")
            report.append(f"- 应用的处理步骤: {', '.join(preprocessing_result['steps_applied'])}\n")
            
            # 数据质量报告
            if 'quality_report' in preprocessing_result:
                report.append("## 数据质量评估")
                quality = preprocessing_result['quality_report']
                
                # 缺失值信息
                missing = quality['missing_values']
                report.append(f"- 总缺失值数量: {missing['total_missing']}")
                report.append(f"- 高缺失值列(>50%): {len(missing['high_missing_columns'])}")
                
                # 重复值信息
                duplicates = quality['duplicates']
                report.append(f"- 重复行数量: {duplicates['total_duplicates']}")
                report.append(f"- 重复行比例: {duplicates['duplicate_percentage']:.2f}%")
                
                # 异常值信息
                outliers = quality['outliers']
                total_outliers = sum(info['count'] for info in outliers.values())
                report.append(f"- 异常值总数: {total_outliers}")
                
                # 一致性问题
                consistency = quality['data_consistency']
                report.append(f"- 数据一致性问题: {consistency['issue_count']}")
                report.append("")
            
            # 处理日志
            report.append("## 处理日志")
            for i, log in enumerate(preprocessing_result['processing_log'], 1):
                report.append(f"{i}. {log}")
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"生成预处理报告失败: {str(e)}")
            return f"报告生成失败: {str(e)}"

# 创建全局实例
enhanced_preprocessing_service = EnhancedPreprocessingService()
