// ======================== 数据管理相关类型 ========================

/** 数据集基本信息 */
export interface DataInfo {
    filename: string;
    path: string;
    shape: [number, number];
    columns: string[];
    preview: Record<string, unknown>[];
}

export interface DataQualityAssessment {
    overall_score?: number;
    missing_values?: {
        total_missing?: number;
        high_missing_columns?: string[];
    };
    duplicates?: {
        total_duplicates?: number;
        duplicate_percentage?: number;
    };
    data_consistency?: {
        issue_count?: number;
    };
}

export type MiningReadinessLevel = 'good' | 'limited' | 'weak' | 'poor';

export interface MiningExcludedColumn {
    name: string;
    reason: string;
    unique_count?: number;
    unique_ratio?: number;
    dtype?: string;
}

export interface MiningTopItem {
    item: string;
    count: number;
    support: number;
}

export interface MiningTransactionSummary {
    transaction_count: number;
    avg_items_per_transaction: number;
    min_items_per_transaction: number;
    max_items_per_transaction: number;
    empty_transactions: number;
    frequent_single_items_at_threshold: number;
}

export interface MiningDiagnostics {
    readiness_score: number;
    readiness_level: MiningReadinessLevel;
    summary: string;
    dataset_shape?: {
        rows: number;
        cols: number;
    };
    candidate_columns: string[];
    selected_columns: string[];
    preferred_columns?: string[];
    excluded_columns: MiningExcludedColumn[];
    warnings: string[];
    suggestions: string[];
    recommended_params?: Partial<MiningParams>;
    candidate_overview?: {
        candidate_count?: number;
        selected_count?: number;
        excluded_count?: number;
        categorical_candidate_count?: number;
        numeric_candidate_count?: number;
        average_unique_ratio?: number;
    };
    transaction_summary?: MiningTransactionSummary;
    top_items?: MiningTopItem[];
    effective_params?: Record<string, unknown>;
    attempts_run?: number;
}

export interface MiningFallbackAttempt {
    name: string;
    strategy: string;
    reason?: string;
    params?: Record<string, unknown>;
    rules_found: number;
    selected_for_output?: boolean;
    selected_columns: string[];
    excluded_columns_count?: number;
    excluded_columns_preview?: MiningExcludedColumn[];
    transaction_count?: number;
    avg_items_per_transaction?: number;
    min_items_per_transaction?: number;
    max_items_per_transaction?: number;
    empty_transactions?: number;
    frequent_single_items_at_threshold?: number;
    top_items?: MiningTopItem[];
    top_lift?: number;
    top_confidence?: number;
    warnings?: string[];
}

/** 预处理配置 */
export interface PreprocessingConfig {
    missing_values: {
        strategy: string;
        fill_value?: number | string;
        columns?: string[];
    };
    outliers: {
        method: string;
        threshold: number;
        action: string;
        columns?: string[];
    };
    normalize: {
        method: string;
        columns?: string[];
    };
    encode?: {
        method: string;
    };
}

/** 质量报告 */
export interface QualityReport {
    success: boolean;
    summary?: {
        overall_score: number;
        warnings: string[];
    };
    missing_chart?: {
        labels: string[];
        values: number[];
    };
    assessment?: Record<string, unknown>;
}

/** 预处理结果 */
export interface ProcessingResult {
    processing_log: string[];
    final_shape: number[];
}

// ======================== 算法配置相关类型 ========================

/** 关联规则挖掘参数 */
export interface MiningParams {
    min_support: number;
    min_confidence: number;
    min_lift: number;
    max_len: number;
    enable_pruning: boolean;
}

/** 统计检验参数 */
export interface StatsParams {
    test_method: string;
    p_value_threshold: number;
    confidence_level: number;
    alternative: string;
}

/** 数据集画像 */
export interface DataProfile {
    rows: number;
    cols: number;
    columns: string[];
    numeric_cols: string[];
    categorical_cols: string[];
}

export interface ProfileRecommendations {
    min_support?: number;
    min_confidence?: number;
    min_lift?: number;
    p_value_threshold?: number;
    suggested_tests?: string[];
    summary_text?: string;
    overall_score?: number;
}

// ======================== 分析结果相关类型 ========================

/** 单条关联规则 */
export interface AssociationRule {
    antecedents: string[];
    consequents: string[];
    support: number;
    confidence: number;
    lift: number;
    conviction?: number;
    length?: number;
    p_value?: number;
    test_method?: string;
    significant?: boolean;
}

/** 统计检验结果 */
export interface StatisticalTestResult {
    test_name: string;
    statistic: number;
    p_value: number;
    significant: boolean;
    effect_size?: number;
    interpretation?: string;
}

/** 任务状态 */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'stopped' | 'cancelled' | 'paused';

export interface TaskStep {
    name: string;
    status: string;
}

export interface TaskResultSummary {
    total_rules?: number;
    significant_rules?: number;
    avg_confidence?: number;
    avg_support?: number;
    total_records?: number;
    p_value_threshold?: number;
    test_method?: string;
    adaptive_mode_used?: boolean;
    selected_attempt_name?: string;
    selected_attempt_strategy?: string;
    readiness_score?: number;
    readiness_level?: MiningReadinessLevel;
}

/** 任务对象 */
export interface Task {
    task_id: string;
    status: TaskStatus;
    progress: number;
    eta_seconds?: number;
    memory_usage?: number;
    message?: string;
    start_time?: string;
    type?: string;
    rules_found: number;
    records: number;
    logs: string[];
    has_result?: boolean;
    steps?: TaskStep[];
    result?: {
        rules: AssociationRule[];
        stats_results?: StatisticalTestResult[];
        radar_data?: RadarDataItem[];
        heatmap_data?: Record<string, unknown>;
        summary?: TaskResultSummary;
        mining_diagnostics?: MiningDiagnostics;
        warnings?: string[];
        fallback_attempts?: MiningFallbackAttempt[];
        selected_attempt?: MiningFallbackAttempt;
        ai_analysis?: string;
        ai_analysis_updated_at?: string;
    };
}

/** 历史任务列表项 */
export interface TaskHistoryItem {
    task_id: string;
    status: TaskStatus;
    start_time: string;
    type: string;
    rules_found: number;
    records: number;
}

/** 雷达图数据项 */
export interface RadarDataItem {
    metric: string;
    value: number;
    fullMark: number;
}

// ======================== 可视化相关类型 ========================

/** 图表元数据 */
export interface ChartMeta {
    correlation?: number;
    regression_stats?: {
        r_squared: number;
        p_value: number;
        slope: number;
        intercept?: number;
    };
    sampling_info?: {
        sampled: boolean;
        total_points: number;
        displayed_points: number;
        max_points: number;
        sample_method?: string | null;
    };
    category_limit_info?: {
        truncated: boolean;
        total_categories_before_limit: number;
        displayed_categories: number;
        max_categories: number;
    };
    network_limit_info?: {
        truncated: boolean;
        total_rules_before_limit: number;
        displayed_rules: number;
        max_rules: number;
    };
    dashboard_limit_info?: {
        row_sampled: boolean;
        total_rows: number;
        displayed_rows: number;
        max_rows: number;
        numeric_columns_total: number;
        numeric_columns_considered: string[];
        max_numeric_cols: number;
        max_categories: number;
        categorical_columns_available: string[];
    };
}

/** 图表类型配置 */
export interface ChartTypeConfig {
    id: string;
    name: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    color: string;
}

/** 图表生成配置 */
export interface ChartGenerationConfig {
    x_col: string;
    y_col: string;
    add_trendline: boolean;
    show_regression_info: boolean;
    method?: 'pearson' | 'spearman' | 'kendall';
    colorscale?: 'RdBu_r' | 'viridis' | 'plasma';
    bins?: number;
    top_n?: number;
    xaxis_angle?: number;
    show_points?: boolean;
    show_markers?: boolean;
    trendline_window?: number;
}

// ======================== 报告相关类型 ========================

/** 报告表单 */
export interface ReportForm {
    title: string;
    templateType: 'basic' | 'financial_risk' | 'medical_research' | 'market_analysis';
    author: string;
    date: string;
    include_visuals: boolean;
}

// ======================== 通用 API 响应 ========================

export interface ApiResponse<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
    [key: string]: unknown;
}

// ======================== 首页统计 ========================

export interface HomeStats {
    tasks: number;
    rules: number;
    records: number;
}
