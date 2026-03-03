from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DataPreview(BaseModel):
    shape: tuple[int, int]
    columns: List[str]
    filename: str
    path: str
    preview: List[Dict[str, Any]]

class ColumnInfo(BaseModel):
    name: str
    type: str
    missing: int
    unique: int

class DataProfile(BaseModel):
    success: bool
    columns_info: List[ColumnInfo]
    shape: tuple[int, int]
    preview: List[Dict[str, Any]]

class PreprocessingOptions(BaseModel):
    missing_value_strategy: str = "median"
    normalize_method: str = "none"
    transform_method: str = "none"
    outlier_method: str = "iqr"

class PreprocessingRequest(BaseModel):
    file_path: str
    options: PreprocessingOptions = PreprocessingOptions()

class PreprocessingResponse(BaseModel):
    success: bool
    message: str
    cleaned_path: str
    shape_before: tuple[int, int]
    shape_after: tuple[int, int]
    preview: List[Dict[str, Any]]

class QualityReportSummary(BaseModel):
    rows: int
    cols: int
    total_missing: int
    missing_rate: float
    warnings: List[str]
    errors: List[str]

class ChartData(BaseModel):
    labels: List[str]
    values: List[int]

class QualityReportResponse(BaseModel):
    success: bool
    summary: QualityReportSummary
    missing_chart: ChartData
    profile: Dict[str, Any]
