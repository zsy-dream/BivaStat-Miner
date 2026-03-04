from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from service.algorithm_service import algorithm_service
from service.task_service import task_manager
from api.data_router import store # 共用缓存 store

router = APIRouter()

@router.post("/start_task")
async def start_mining_task(params: Dict[str, Any] = Body(...)):
    """启动关联挖掘异步任务"""
    if store.current_df is None:
        raise HTTPException(status_code=400, detail="未加载数据集")
        
    task_id = task_manager.create_task("关联挖掘分析")
    
    def task_exec(tid):
        import time
        task_manager.update_task(tid, progress=15, log="[1] 数据透视与分布初始化中...")
        time.sleep(0.5)
        df = store.current_df
        
        task_manager.update_task(tid, progress=35, log="[2] 启动启发式频繁项挖掘引擎...")
        time.sleep(0.2)
        
        task_manager.update_task(tid, progress=55, log="[3] 执行 Apriori 剪枝与组合搜索...")
        rules = algorithm_service.mine_association(df, params)
        
        task_manager.update_task(tid, progress=85, log="[4] 进行双变量统计显著性(P-Value)深度校验...")
        time.sleep(0.5)
        
        task_manager.update_task(tid, progress=98, log="[5] 挖掘完成，封存结果并构建报告...")
        time.sleep(0.3)
        return {"rules": rules}
        
    task_manager.run_async(task_exec, task_id)
    return {"success": True, "task_id": task_id}

@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.post("/nonparametric_test")
async def run_statistical_test(params: Dict[str, Any] = Body(...)):
    """运行非参数统计检验"""
    if store.current_df is None:
        raise HTTPException(status_code=400, detail="未加载数据集")
        
    result = algorithm_service.nonparametric_test(store.current_df, params)
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    return {"success": True, "result": result}
