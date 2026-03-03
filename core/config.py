import os
import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class AlgorithmSettings(BaseModel):
    min_support: float = 0.05
    min_confidence: float = 0.4
    min_lift: float = 1.0
    max_len: int = 5
    p_value_threshold: float = 0.05
    confidence_interval: float = 0.95
    test_method: str = "auto"
    heuristic_factor: float = 1.5

class PreprocessingSettings(BaseModel):
    missing_value_strategy: str = "median"
    outlier_detection: bool = True
    outlier_method: str = "iqr"
    outlier_threshold: float = 1.5
    standardization: bool = False
    encoding_method: str = "onehot"

class SecuritySettings(BaseModel):
    max_file_size_mb: int = 100
    allowed_extensions: list[str] = ["csv", "xlsx", "xls", "json", "parquet", "hdf5"]
    enable_content_scan: bool = True
    max_cache_entries: int = 10
    max_memory_mb: int = 512
    secret_key: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "default-secret-key"))

class SystemSettings(BaseModel):
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    log_level: str = "INFO"
    enable_debug: bool = False
    port: int = 8000
    host: str = "0.0.0.0"

class VisualizationSettings(BaseModel):
    chart_theme: str = "plotly"
    color_palette: str = "viridis"
    figure_size: list[int] = [10, 8]
    dpi: int = 300
    interactive: bool = True

class ExportSettings(BaseModel):
    default_format: str = "csv"
    include_metadata: bool = True
    compression: bool = False

class Settings(BaseSettings):
    algorithm: AlgorithmSettings = AlgorithmSettings()
    preprocessing: PreprocessingSettings = PreprocessingSettings()
    security: SecuritySettings = SecuritySettings()
    system: SystemSettings = SystemSettings()
    visualization: VisualizationSettings = VisualizationSettings()
    export: ExportSettings = ExportSettings()
    
    model_config = {
        "env_file": ".env",
        "env_nested_delimiter": "__",
        "extra": "ignore" 
    }

    def save_to_json(self, path: str = "config.json"):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=4))

    @classmethod
    def load_from_json(cls, path: str = "config.json") -> "Settings":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    return cls(**data)
                except Exception as e:
                    return cls()
        return cls()

settings = Settings.load_from_json()
