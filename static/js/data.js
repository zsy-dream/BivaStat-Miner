// 全局数据存储对象
var currentAnalysisData = {
    rules: [],
    summary: {
        total_rules: 0,
        significant_rules: 0,
        avg_confidence: 0,
        avg_support: 0
    },
    // 模拟数据，防止页面加载时报错
    chart_data: {
        x_values: [],
        y_values: [],
        values: [],
        labels: []
    }
};

// 数据处理工具函数
const DataManager = {
    setRules: function(rules) {
        currentAnalysisData.rules = rules;
    },

    getRules: function() {
        return currentAnalysisData.rules;
    },

    clearData: function() {
        currentAnalysisData.rules = [];
        currentAnalysisData.summary = {};
    }
};