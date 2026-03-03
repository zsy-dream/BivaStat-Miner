// 统一使用 Plotly.js 的图表封装库
const ChartLib = {
    // 基础配置
    defaults: {
        responsive: true,
        displayModeBar: true, // 显示工具栏（下载、缩放等）
        displaylogo: false, // 不显示 Plotly logo
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    },

    // 渲染图表的通用入口
    render: function(elementId, type, data, layoutOverride = {}) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Chart container #${elementId} not found`);
            return;
        }

        let plotData = [];
        let layout = {
            autosize: true,
            margin: { t: 40, r: 20, b: 40, l: 50 },
            font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' },
            hovermode: 'closest',
            ...layoutOverride
        };

        // 根据类型分发处理
        switch (type) {
            case 'heatmap':
                plotData = this._createHeatmapData(data);
                layout.title = layout.title || '双变量关联热力图';
                break;
            case 'scatter':
                plotData = this._createScatterData(data);
                layout.title = layout.title || '双变量散点图';
                break;
            case 'bar':
                plotData = this._createBarData(data);
                layout.title = layout.title || '关联规则支持度分布';
                break;
            case 'line':
                plotData = this._createLineData(data);
                layout.title = layout.title || '趋势分析';
                break;
            case 'pie':
                plotData = this._createPieData(data);
                layout.title = layout.title || '占比分布';
                break;
            default:
                console.warn(`Unsupported chart type: ${type}`);
                return;
        }

        // 渲染图表
        Plotly.newPlot(element, plotData, layout, this.defaults);
        
        // 自适应大小
        window.addEventListener('resize', () => {
            Plotly.Plots.resize(element);
        });
    },

    // --- 内部数据转换方法 ---

    _createHeatmapData: function(data) {
        // 期望 data 结构: { values: [[...]], x_labels: [...], y_labels: [...] }
        return [{
            z: data.values,
            x: data.x_labels,
            y: data.y_labels,
            type: 'heatmap',
            colorscale: 'Viridis',
            colorbar: { title: '强度' },
            hovertemplate: 'X: %{x}<br>Y: %{y}<br>值: %{z}<extra></extra>'
        }];
    },

    _createScatterData: function(data) {
        // 期望 data 结构: { x_values: [...], y_values: [...], text: [...] }
        return [{
            x: data.x_values,
            y: data.y_values,
            mode: 'markers',
            type: 'scatter',
            text: data.text || null, // 悬浮显示的额外文本
            marker: {
                size: 10,
                color: data.y_values, // 根据 Y 值着色
                colorscale: 'Bluered',
                opacity: 0.7,
                line: { width: 1, color: 'white' }
            },
            hovertemplate: 'X: %{x}<br>Y: %{y}<extra>%{text}</extra>'
        }];
    },

    _createBarData: function(data) {
        // 期望 data 结构: { labels: [...], values: [...] }
        return [{
            x: data.labels,
            y: data.values,
            type: 'bar',
            marker: {
                color: '#667eea', // 统一主题色
                opacity: 0.8
            },
            hovertemplate: '%{x}: %{y:.3f}<extra></extra>'
        }];
    },
    
    _createLineData: function(data) {
        // 期望 data 结构: { labels: [...], values: [...] }
        return [{
            x: data.labels,
            y: data.values,
            type: 'scatter', // Plotly 中 line chart 也是 scatter
            mode: 'lines+markers',
            line: { shape: 'spline', color: '#764ba2', width: 3 },
            marker: { size: 6 }
        }];
    },

    _createPieData: function(data) {
         // 期望 data 结构: { labels: [...], values: [...] }
        return [{
            labels: data.labels,
            values: data.values,
            type: 'pie',
            textinfo: 'label+percent',
            insidetextorientation: 'radial',
            hole: 0.4 // 甜甜圈图
        }];
    },

    // 导出图表图片
    downloadImage: function(elementId, format = 'png', filename = 'chart') {
        const element = document.getElementById(elementId);
        if (element) {
            Plotly.downloadImage(element, {format: format, filename: filename});
        }
    }
};

// 导出全局变量
window.ChartLib = ChartLib;
