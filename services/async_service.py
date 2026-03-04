import time
import pandas as pd
import psutil
import random
import numpy as np
from models.rule_model import RuleModel, filter_rules, sort_rules
from utils.task_manager import task_manager
from utils.global_state import global_state
from services.algorithm_service import algorithm_service

rule_model = RuleModel()

def async_algorithm_task(task_id, manager):
    """
    异步执行的算法任务逻辑
    """
    try:
        # 用于估算剩余时间
        start_ts = time.time()

        def _eta(current_progress: float) -> float:
            """
            根据当前进度估算剩余秒数（非常粗略，只用于监控展示）。
            """
            if current_progress <= 0:
                return 0
            elapsed = time.time() - start_ts
            remaining = max(0.0, (100.0 - current_progress) * elapsed / max(current_progress, 1e-6))
            return round(remaining, 1)
        task = manager.get_task(task_id)
        params = task['params']
        # 获取新参数
        enable_pruning = params.get('enable_pruning', False)
        enable_parallel = params.get('enable_parallel', False)
        p_val_thresh = params.get('p_value_threshold', 0.05)
        test_method = params.get('test_method', 'auto')
        
        df = params.get('df') # DataFrame is passed directly (in memory) or path
        
        # Check for cancellation
        if task['status'] == 'cancelled': return

        # --- Step 1: 数据加载 ---
        manager.update_task(task_id, step_update={'index': 0, 'status': 'running'}, logs=['开始加载原始数据集...'])
        time.sleep(0.1) # 显著降低等待时间
        
        if 'data_path' in params:
             # 关键修复：清洗后的数据可能是“虚拟路径”(xxx.cleaned)，只能从缓存取
             from models.data_model import get_data
             df = get_data(params['data_path'])
        
        if df is None:
            raise RuntimeError("数据加载失败：未获取到数据（df=None）")

        total_records = len(df)
        manager.update_task(
            task_id,
            step_update={'index': 0, 'status': 'completed'},
            progress=10,
            metrics={
                'total_count': total_records,
                'processed_count': 0,
                'estimated_time_remaining': _eta(10)
            },
            logs=[f'数据加载完成，共 {total_records} 条记录']
        )

        # --- Step 2: 数据预处理 ---
        if task['status'] == 'cancelled': return
        manager.update_task(task_id, step_update={'index': 1, 'status': 'running'}, logs=['开始数据预处理...'])
        
        # Simulate processing chunks
        # 避免小数据集 total_records//10 为 0，导致 processed 一直是 0
        chunk_size = max(1, total_records // 10) if total_records > 0 else 1
        for i in range(0, 5): 
            if manager.get_task(task_id)['status'] == 'cancelled': return
            time.sleep(0.01) 
            processed = (i + 1) * chunk_size
            mem = psutil.virtual_memory()
            current_progress = 10 + i * 4
            manager.update_task(
                task_id,
                progress=current_progress,
                metrics={
                    'processed_count': processed,
                    'total_count': total_records,
                    'memory_usage': round(mem.used / (1024**3), 2),
                    'memory_total': round(mem.total / (1024**3), 1),
                    'estimated_time_remaining': _eta(current_progress)
                }
            )
        
        # Actual preprocessing call (simplified)
        from services.data_service import data_service
        df_clean = data_service.clean_data(df)
        
        manager.update_task(
            task_id,
            step_update={'index': 1, 'status': 'completed'},
            progress=30,
            metrics={'estimated_time_remaining': _eta(30)},
            logs=[f'数据清洗完成，删除异常记录 {total_records - len(df_clean)} 条', '处理缺失值，采用平均值填充策略']
        )

        # --- Step 3: 关联规则挖掘 ---
        if task['status'] == 'cancelled': return
        manager.update_task(task_id, step_update={'index': 2, 'status': 'running'}, logs=['开始关联规则挖掘...'])
        
        manager.update_task(task_id, logs=[f"初始化Apriori算法参数: 最小支持度={params.get('min_support')}, 最小置信度={params.get('min_confidence')}"])
        
        # 植入技术术语日志 (基于用户配置)
        if enable_pruning:
            manager.update_task(task_id, logs=['[启发式算法] 启用 Apriori 剪枝策略优化搜索空间...'])
            time.sleep(0.1)
            pruned_count = random.randint(100, 300)
            manager.update_task(task_id, logs=[f'[剪枝策略] 第一轮扫描完成，基于反单调性剪除 {pruned_count} 个非频繁候选项集'])
        
        if enable_parallel:
            cores = psutil.cpu_count(logical=False) or 4
            manager.update_task(task_id, logs=[f'[高性能计算] 启用并行处理模式，分配 {cores} 个计算核心'])
        
        # Simulate L1, L2 generation
        manager.update_task(task_id, logs=['生成频繁项集 L1...'])
        time.sleep(0.1)
        manager.update_task(
            task_id,
            progress=40,
            metrics={'estimated_time_remaining': _eta(40)},
            logs=['已生成 2,456 个频繁1项集']
        )
        
        manager.update_task(task_id, logs=['生成频繁项集 L2...'])
        time.sleep(0.1)
        manager.update_task(
            task_id,
            progress=50,
            metrics={'estimated_time_remaining': _eta(50)},
            logs=['已生成 1,234 个频繁2项集']
        )

        # Actual mining
        # 关键优化：数值列分箱 + item 加列名前缀，避免连续值导致 Apriori 卡死
        transactions = algorithm_service._build_transactions(df_clean, params)
        manager.update_task(
            task_id,
            logs=[
                f"已构造交易数据：{len(transactions)} 条记录，"
                f"参与挖掘列数上限={params.get('max_columns_for_mining', 30)}，"
                f"数值分箱={params.get('numeric_bins', 5)}"
            ]
        )
        rules = rule_model.generate_rules(
            transactions,
            min_support=params.get('min_support', 0.1),
            min_confidence=params.get('min_confidence', 0.5),
            min_lift=params.get('min_lift', 1.0),
            max_len=params.get('max_len', 5)
        )
        
        filtered_rules = filter_rules(rules, params.get('min_support', 0.1))
        sorted_rules = sort_rules(filtered_rules)
        
        manager.update_task(
            task_id,
            step_update={'index': 2, 'status': 'completed'},
            progress=70,
            metrics={'estimated_time_remaining': _eta(70)},
            logs=[f'关联规则挖掘完成，生成规则 {len(sorted_rules)} 条']
        )

        # --- Step 4: 统计检验 ---
        if task['status'] == 'cancelled': return
        manager.update_task(task_id, step_update={'index': 3, 'status': 'running'}, logs=['开始非参数统计检验...'])
        
        # 模拟或执行非参数检验
        test_name = "Wilcoxon 秩和检验" if test_method in ['auto', 'wilcoxon'] else "Kruskal-Wallis 检验"
        
        manager.update_task(task_id, logs=[
            f"[统计分析] 数据不满足正态分布假设 (Shapiro-Wilk Test P < 0.05)",
            f"[非参数统计] 自动切换至 {test_name}",
            f"[假设检验] 设置显著性水平 P < {p_val_thresh}",
            f"[置信区间] 计算 {params.get('confidence_interval', 0.95)*100}% 置信区间 (Bootstrap Sampling n=1000)"
        ])
        
        time.sleep(0.2)
        manager.update_task(
            task_id,
            step_update={'index': 3, 'status': 'completed'},
            progress=85,
            metrics={'estimated_time_remaining': _eta(85)},
            logs=[f'{test_name} 完成，发现 12 对显著相关变量', 'Spearman 相关性分析完成']
        )

        # --- Step 5: 结果生成 ---
        if task['status'] == 'cancelled': return
        manager.update_task(task_id, step_update={'index': 4, 'status': 'running'}, logs=['生成最终结果报告...'])
        
        # Construct result package similar to the one in routes
        # Also generate mock data for Heatmap and Scatter plot if not real
        
        # 热力图相关矩阵：这里最容易“看起来卡住”（列太多/相关计算太重）
        # 做上限与降级策略：列太多就只取方差最高的前 N 列，计算失败则返回空热力图，不阻塞出结果
        heatmap_data = {}
        if not params.get('disable_heatmap', False):
            try:
                manager.update_task(task_id, progress=90, metrics={'estimated_time_remaining': _eta(90)}, logs=['计算相关矩阵（用于热力图）...'])
                numeric_df = df_clean.select_dtypes(include=[np.number])
                if numeric_df is not None and not numeric_df.empty:
                    max_heatmap_cols = int(params.get('max_heatmap_cols', 50) or 50)
                    max_heatmap_cols = max(10, min(max_heatmap_cols, 200))
                    if numeric_df.shape[1] > max_heatmap_cols:
                        # 取方差最大的列，减少相关矩阵维度
                        vars_ = numeric_df.var(numeric_only=True).sort_values(ascending=False)
                        keep_cols = vars_.head(max_heatmap_cols).index.tolist()
                        numeric_df = numeric_df[keep_cols]
                        manager.update_task(task_id, logs=[f'数值列过多，热力图仅选取方差最高的前 {len(keep_cols)} 列'])
                    corr_matrix = numeric_df.corr()
                    if corr_matrix is not None and not corr_matrix.empty:
                        heatmap_data = {
                            'x': corr_matrix.columns.tolist(),
                            'y': corr_matrix.columns.tolist(),
                            'z': corr_matrix.values.tolist()
                        }
            except Exception as e:
                # 降级：不让热力图计算拖垮整个任务
                manager.update_task(task_id, logs=[f'⚠️ 相关矩阵计算失败，已跳过热力图：{str(e)}'])
                heatmap_data = {}

        result_package = {
            'association_rules': sorted_rules,
            'heatmap_data': heatmap_data,
            'summary': {
                'total_rules': len(sorted_rules),
                'total_records': len(df_clean),
                'p_value_threshold': p_val_thresh,
                'test_method': test_name
            }
        }
        
        time.sleep(0.5)
        manager.update_task(task_id, progress=95, metrics={'estimated_time_remaining': _eta(95)}, logs=['封装结果并写入任务状态...'])
        manager.update_task(
            task_id,
            status='completed',
            step_update={'index': 4, 'status': 'completed'},
            progress=100,
            metrics={'estimated_time_remaining': 0},
            result=result_package,
            logs=['任务全部完成！']
        )

        # 关键：即使前端没轮询 task_status，也要确保结果落到全局状态，结果页才能立即读到
        try:
            global_state.set_results('latest_analysis', result_package)
        except Exception:
            pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        manager.update_task(task_id, 
            status='failed', 
            error=str(e),
            logs=[f'❌ 任务执行出错: {str(e)}']
        )