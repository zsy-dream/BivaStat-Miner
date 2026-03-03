import json
import os
from typing import Dict

class ConfigManager:
    _instance = None
    _config_path = "config.json"
    _default_params = {
        "algorithm": {
            "min_support": 0.05,
            "min_confidence": 0.4,
            "min_lift": 1.0,
            "max_len": 5,
            "p_value_threshold": 0.05,
            "confidence_interval": 0.95,
            "test_method": "auto",
            "heuristic_factor": 1.5
        },
        "preprocessing": {
            "missing_value_strategy": "median",
            "outlier_detection": True,
            "outlier_method": "iqr",
            "outlier_threshold": 1.5,
            "standardization": False,
            "encoding_method": "onehot"
        },
        "security": {
            "max_file_size_mb": 100,
            "allowed_extensions": ["csv", "xlsx", "xls", "json"],
            "enable_content_scan": True,
            "max_cache_entries": 10,
            "max_memory_mb": 512
        },
        "system": {
            "cache_enabled": True,
            "cache_ttl_seconds": 3600,
            "log_level": "INFO",
            "enable_debug": False
        },
        "visualization": {
            "chart_theme": "plotly",
            "color_palette": "viridis",
            "figure_size": [10, 8],
            "dpi": 300,
            "interactive": True
        },
        "export": {
            "default_format": "csv",
            "include_metadata": True,
            "compression": False
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._config_data = self._default_params.copy()
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                self._deep_update(self._config_data, saved_config)
            except Exception as e:
                raise RuntimeError(f"Failed to load configuration: {str(e)}")

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def load_params(self) -> Dict:
        return self._config_data.copy()

    def save_params(self, params: Dict) -> None:
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=4, ensure_ascii=False)
            self._config_data = params.copy()
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {str(e)}")

    def get_param(self, key_path: str, default=None):
        keys = key_path.split('.')
        current = self._config_data
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def set_param(self, key_path: str, value) -> None:
        keys = key_path.split('.')
        current = self._config_data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save_params(self._config_data)

    def reset_to_defaults(self) -> None:
        self._config_data = self._default_params.copy()
        self.save_params(self._config_data)

    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证算法参数
            min_support = self.get_param("algorithm.min_support")
            if min_support is None or not (0 < min_support <= 1):
                return False
                
            min_confidence = self.get_param("algorithm.min_confidence")
            if min_confidence is None or not (0 < min_confidence <= 1):
                return False
            
            # 验证安全参数
            max_file_size = self.get_param("security.max_file_size_mb")
            if max_file_size is None or not (1 <= max_file_size <= 1000):
                return False
            
            # 验证预处理参数
            missing_strategy = self.get_param("preprocessing.missing_value_strategy")
            if missing_strategy not in ['none', 'drop', 'mean', 'median', 'mode', 'zero']:
                return False
            
            return True
        except Exception:
            return False

    def get_security_params(self) -> Dict:
        """获取安全配置参数"""
        return self.get_param("security", {})
    
    def get_system_params(self) -> Dict:
        """获取系统配置参数"""
        return self.get_param("system", {})

    def update_algorithm_params(self, **kwargs) -> None:
        current_params = self.get_param("algorithm", {})
        current_params.update(kwargs)
        self.set_param("algorithm", current_params)

    def update_preprocessing_params(self, **kwargs) -> None:
        current_params = self.get_param("preprocessing", {})
        current_params.update(kwargs)
        self.set_param("preprocessing", current_params)

    def update_visualization_params(self, **kwargs) -> None:
        current_params = self.get_param("visualization", {})
        current_params.update(kwargs)
        self.set_param("visualization", current_params)

    def get_algorithm_params(self) -> Dict:
        return self.get_param("algorithm", {})

    def get_preprocessing_params(self) -> Dict:
        return self.get_param("preprocessing", {})

    def get_visualization_params(self) -> Dict:
        return self.get_param("visualization", {})

    def export_config(self, filepath: str) -> None:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to export configuration: {str(e)}")

    def import_config(self, filepath: str) -> None:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            self._deep_update(self._default_params, imported_config)
            self.save_params(self._default_params)
        except Exception as e:
            raise RuntimeError(f"Failed to import configuration: {str(e)}")

config_manager = ConfigManager()

def load_params() -> Dict:
    return config_manager.load_params()

def save_params(params: Dict) -> None:
    config_manager.save_params(params)