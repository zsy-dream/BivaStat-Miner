import requests, json

base = 'http://127.0.0.1:8001/api/visualization/create_chart'

tests = [
    ('correlation_heatmap', {'chart_type': 'correlation_heatmap', 'use_current_data': True, 'config': {'width': 800, 'height': 600}}),
    ('scatter', {'chart_type': 'scatter', 'use_current_data': True, 'x_col': '特征1', 'y_col': '特征2', 'config': {'width': 800, 'height': 600, 'add_trendline': True, 'show_regression_info': True}}),
    ('distribution', {'chart_type': 'distribution', 'use_current_data': True, 'column': '特征1', 'config': {'width': 800, 'height': 600}}),
    ('box', {'chart_type': 'box', 'use_current_data': True, 'value_col': '特征1', 'group_col': '特征2', 'config': {'width': 800, 'height': 600}}),
    ('bar', {'chart_type': 'bar', 'use_current_data': True, 'x_col': '特征1', 'y_col': '特征2', 'config': {'width': 800, 'height': 600}}),
    ('line', {'chart_type': 'line', 'use_current_data': True, 'x_col': '特征1', 'y_col': '特征2', 'config': {'width': 800, 'height': 600}}),
]

for name, payload in tests:
    try:
        r = requests.post(base, json=payload, timeout=30)
        d = r.json()
        if d.get('success'):
            html = d.get('data', {}).get('chart_html', '')
            has_plotly = 'Plotly' in html
            print(f'[OK] {name}: html={len(html)} chars, has_Plotly_call={has_plotly}')
        else:
            err = d.get('error', str(d)[:200])
            print(f'[FAIL] {name}: {err}')
    except Exception as e:
        print(f'[ERROR] {name}: {e}')

# Test report generation
print('\n=== Report Test ===')
try:
    r = requests.post('http://127.0.0.1:8001/api/report/generate_report', json={
        'report_type': 'general_analysis',
        'include_ai_summary': True
    }, timeout=60)
    d = r.json()
    if d.get('success'):
        rd = d.get('data', d)
        report = rd.get('report', rd)
        print(f'Report generated: {list(report.keys()) if isinstance(report, dict) else type(report)}')
        # Check if report has real data
        if isinstance(report, dict):
            exec_summary = report.get('executive_summary', '')
            if exec_summary:
                print(f'Executive summary length: {len(exec_summary)} chars')
                print(f'Preview: {exec_summary[:200]}...')
            ai_sum = report.get('ai_summary', '')
            if ai_sum:
                print(f'AI summary length: {len(ai_sum)} chars')
                print(f'AI Preview: {ai_sum[:200]}...')
    else:
        print(f'Report FAILED: {d.get("error", str(d)[:300])}')
except Exception as e:
    print(f'Report ERROR: {e}')
