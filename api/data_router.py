import os
import uuid
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from schema.data import PreprocessingRequest, PreprocessingResponse, QualityReportResponse
from service.data_service import data_service
from core.logging import logger
from typing import Dict, Any

router = APIRouter()

# 简易全局状态（在真正应用中应使用缓存服务或数据库，这里保持轻量）
class MemStore:
    current_df: pd.DataFrame = None
    current_path: str = None
    cache: Dict[str, pd.DataFrame] = {}

store = MemStore()

@router.post("/upload_data")
async def upload_data(file: UploadFile = File(...)):
    """上传数据并解析"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.csv', '.xlsx', '.xls', '.json'):
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    temp_path = os.path.join(upload_dir, f"{uuid.uuid4()}{ext}")
    
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        if ext == '.csv':
            df = pd.read_csv(temp_path)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(temp_path)
        else: # .json
            df = pd.read_json(temp_path)
            
        store.current_df = df
        store.current_path = temp_path
        store.cache[temp_path] = df
        
        return {
            "success": True,
            "filename": file.filename,
            "path": temp_path,
            "shape": df.shape,
            "columns": list(df.columns),
            "preview": df.head(10).fillna("").to_dict(orient="records")
        }
    except Exception as e:
        logger.error(f"Upload and parse failed: {e}")
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current")
async def get_current_data():
    """获取当前加载的数据详情"""
    if store.current_df is None:
        return {"success": False, "message": "未加载任何数据"}
    
    return {
        "success": True,
        "shape": store.current_df.shape,
        "filename": os.path.basename(store.current_path),
        "path": store.current_path,
        "columns": list(store.current_df.columns),
        "preview": store.current_df.head(10).fillna("").to_dict(orient="records")
    }

@router.post("/preprocess_data")
async def preprocess_data(req: PreprocessingRequest):
    """预处理数据"""
    df = store.cache.get(req.file_path)
    if df is None:
        raise HTTPException(status_code=404, detail="文件缓存已过期或不存在")
    
    try:
        cleaned_df = data_service.clean_data(df, req.options.model_dump())
        cleaned_path = req.file_path + ".cleaned"
        store.current_df = cleaned_df
        store.current_path = cleaned_path
        store.cache[cleaned_path] = cleaned_df
        
        return {
            "success": True,
            "message": "清洗完成",
            "cleaned_path": cleaned_path,
            "shape_before": df.shape,
            "shape_after": cleaned_df.shape,
            "preview": cleaned_df.head(10).fillna("").to_dict(orient="records")
        }
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quality_report")
async def get_quality_report(body: Dict[str, str] = Body(...)):
    """生成数据质量报告"""
    file_path = body.get('file_path')
    df = store.cache.get(file_path) if file_path else store.current_df
    
    if df is None:
        raise HTTPException(status_code=404, detail="未找到目标数据")
        
    profile = data_service.calculate_data_profile(df)
    validation = data_service.validate_data_integrity(df)
    
    missing_sum = sum(profile['missing_values'].values())
    total_cells = df.shape[0] * df.shape[1]
    
    # 构造柱状图数据
    sorted_missing = sorted(profile['missing_values'].items(), key=lambda x: x[1], reverse=True)[:12]
    
    return {
        "success": True,
        "summary": {
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "total_missing": int(missing_sum),
            "missing_rate": float(missing_sum / total_cells) if total_cells > 0 else 0,
            "warnings": validation['warnings'],
            "errors": validation['errors']
        },
        "missing_chart": {
            "labels": [k for k, _ in sorted_missing],
            "values": [int(v) for _, v in sorted_missing]
        }
    }
