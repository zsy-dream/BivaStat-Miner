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
        task_manager.update_task(tid, progress=10, log="正在加载数据...")
        df = store.current_df
        # 预加载
        task_manager.update_task(tid, progress=30, log="开始执行挖掘算法...")
        rules = algorithm_service.mine_association(df, params)
        task_manager.update_task(tid, progress=80, log="规则生成完毕，进行显著性检验...")
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
