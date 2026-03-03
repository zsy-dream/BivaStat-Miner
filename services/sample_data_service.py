"""
示例数据生成器服务
提供多种预设数据集，让用户快速体验平台功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import random


class SampleDataGenerator:
    """示例数据生成器"""
    
    def __init__(self):
        self.datasets = {
            'retail': self._generate_retail_data,
            'medical': self._generate_medical_data,
            'financial': self._generate_financial_data,
            'education': self._generate_education_data,
            'marketing': self._generate_marketing_data,
            'iris_extended': self._generate_iris_extended
        }
    
    def get_available_datasets(self) -> Dict[str, Any]:
        """获取可用的示例数据集列表"""
        return {
            'retail': {
                'name': '零售购物篮数据',
                'description': '模拟超市购物行为，包含商品类别、购买时间、顾客特征等',
                'rows': '1000',
                'columns': '12',
                'use_case': '关联规则挖掘、购物篮分析',
                'features': ['商品类别', '购买金额', '会员等级', '支付方式', '时段']
            },
            'medical': {
                'name': '医疗诊断数据',
                'description': '患者症状、检查结果与诊断的关联数据',
                'rows': '800',
                'columns': '15',
                'use_case': '症状关联分析、诊断辅助',
                'features': ['症状', '年龄', '性别', '血压', '血糖', '诊断结果']
            },
            'financial': {
                'name': '金融风险评估数据',
                'description': '客户信用评分、贷款违约风险相关数据',
                'rows': '2000',
                'columns': '18',
                'use_case': '风险因素分析、违约预测',
                'features': ['收入', '信用评分', '负债率', '就业状况', '违约标签']
            },
            'education': {
                'name': '教育成绩分析数据',
                'description': '学生成绩、学习习惯与成绩关联',
                'rows': '1500',
                'columns': '14',
                'use_case': '成绩影响因素分析、学习行为挖掘',
                'features': ['学习时间', '出勤率', '作业完成度', '考试成绩', '课外活动']
            },
            'marketing': {
                'name': '市场营销效果数据',
                'description': '营销活动、客户响应与转化率分析',
                'rows': '1200',
                'columns': '16',
                'use_case': '营销效果评估、客户细分',
                'features': ['渠道', '促销类型', '客户价值', '响应率', '转化率']
            },
            'iris_extended': {
                'name': '扩展鸢尾花数据集',
                'description': '经典鸢尾花数据的扩展版本，增加更多特征',
                'rows': '300',
                'columns': '10',
                'use_case': '多变量关系分析、分类特征挖掘',
                'features': ['花萼长度', '花萼宽度', '花瓣长度', '花瓣宽度', '品种', '生长地']
            }
        }
    
    def generate_dataset(self, dataset_type: str, n_samples: int = None) -> pd.DataFrame:
        """
        生成示例数据集
        
        Args:
            dataset_type: 数据集类型
            n_samples: 样本数量，默认使用预设值
            
        Returns:
            DataFrame
        """
        if dataset_type not in self.datasets:
            raise ValueError(f"不支持的数据集类型: {dataset_type}")
        
        generator = self.datasets[dataset_type]
        return generator(n_samples)
    
    def _generate_retail_data(self, n_samples: int = None) -> pd.DataFrame:
        """生成零售购物篮数据"""
        n = n_samples or 1000
        np.random.seed(42)
        
        # 商品类别
        categories = ['食品', '饮料', '日用品', '电子产品', '服装', '家居', '图书']
        
        # 时段
        hours = ['早晨(6-9)', '上午(9-12)', '中午(12-14)', '下午(14-18)', 
                '晚上(18-22)', '深夜(22-6)']
        
        # 支付方式
        payments = ['现金', '信用卡', '移动支付', '会员卡']
        
        # 会员等级
        membership = ['普通', '银卡', '金卡', '钻石']
        
        data = {
            '顾客ID': [f'CUST_{i:04d}' for i in range(n)],
            '商品类别': np.random.choice(categories, n),
            '购买金额': np.random.lognormal(4, 1, n).round(2),
            '购买数量': np.random.poisson(3, n) + 1,
            '会员等级': np.random.choice(membership, n, p=[0.5, 0.3, 0.15, 0.05]),
            '支付方式': np.random.choice(payments, n, p=[0.15, 0.25, 0.45, 0.15]),
            '时段': np.random.choice(hours, n, p=[0.05, 0.15, 0.20, 0.25, 0.30, 0.05]),
            '是否周末': np.random.choice(['是', '否'], n, p=[0.3, 0.7]),
            '是否有促销': np.random.choice(['是', '否'], n, p=[0.25, 0.75]),
            '门店类型': np.random.choice(['社区店', '商圈店', '旗舰店', '便利店'], n),
            '顾客年龄': np.random.normal(35, 12, n).clip(18, 80).astype(int),
            '满意度评分': np.random.choice([1, 2, 3, 4, 5], n, p=[0.02, 0.05, 0.13, 0.35, 0.45])
        }
        
        df = pd.DataFrame(data)
        
        # 添加关联性：会员等级与购买金额相关
        df.loc[df['会员等级'] == '钻石', '购买金额'] *= 2.5
        df.loc[df['会员等级'] == '金卡', '购买金额'] *= 1.8
        df.loc[df['会员等级'] == '银卡', '购买金额'] *= 1.3
        
        # 添加关联性：促销与满意度
        df.loc[df['是否有促销'] == '是', '满意度评分'] = np.random.choice(
            [1, 2, 3, 4, 5], 
            df['是否有促销'].eq('是').sum(), 
            p=[0.01, 0.03, 0.10, 0.30, 0.56]
        )
        
        return df.round(2)
    
    def _generate_medical_data(self, n_samples: int = None) -> pd.DataFrame:
        """生成医疗诊断数据"""
        n = n_samples or 800
        np.random.seed(42)
        
        # 症状
        symptoms = ['发热', '咳嗽', '头痛', '乏力', '恶心', '胸痛', '呼吸困难', '无症状']
        
        # 诊断结果
        diagnoses = ['感冒', '流感', '肺炎', '支气管炎', '胃炎', '高血压', '正常']
        
        data = {
            '患者ID': [f'PAT_{i:04d}' for i in range(n)],
            '年龄': np.random.normal(45, 18, n).clip(0, 100).astype(int),
            '性别': np.random.choice(['男', '女'], n),
            '主要症状': np.random.choice(symptoms, n),
            '体温': np.random.normal(36.8, 0.8, n).clip(35, 42).round(1),
            '收缩压': np.random.normal(120, 20, n).clip(90, 180).astype(int),
            '舒张压': np.random.normal(80, 12, n).clip(60, 110).astype(int),
            '心率': np.random.normal(75, 12, n).clip(50, 120).astype(int),
            '血糖': np.random.normal(5.5, 1.5, n).clip(3, 15).round(2),
            '白细胞计数': np.random.normal(7, 2, n).clip(3, 15).round(2),
            '就诊科室': np.random.choice(['内科', '呼吸科', '消化科', '心内科', '急诊科'], n),
            '是否住院': np.random.choice(['是', '否'], n, p=[0.2, 0.8]),
            '既往病史': np.random.choice(['无', '高血压', '糖尿病', '心脏病', '多病史'], n),
            '吸烟史': np.random.choice(['从不', '已戒烟', '偶尔', '经常'], n, p=[0.45, 0.15, 0.20, 0.20]),
            '诊断结果': np.random.choice(diagnoses, n)
        }
        
        df = pd.DataFrame(data)
        
        # 添加关联性：发热患者更可能诊断为感冒或流感
        fever_mask = df['主要症状'] == '发热'
        df.loc[fever_mask, '诊断结果'] = np.random.choice(
            ['感冒', '流感', '肺炎', '支气管炎'],
            fever_mask.sum(),
            p=[0.4, 0.35, 0.15, 0.10]
        )
        df.loc[fever_mask, '体温'] += np.random.uniform(0.5, 2, fever_mask.sum())
        
        # 添加关联性：胸痛患者更可能住院
        chest_pain_mask = df['主要症状'] == '胸痛'
        df.loc[chest_pain_mask, '是否住院'] = np.random.choice(
            ['是', '否'],
            chest_pain_mask.sum(),
            p=[0.6, 0.4]
        )
        
        return df
    
    def _generate_financial_data(self, n_samples: int = None) -> pd.DataFrame:
        """生成金融风险评估数据"""
        n = n_samples or 2000
        np.random.seed(42)
        
        data = {
            '客户ID': [f'FIN_{i:05d}' for i in range(n)],
            '年龄': np.random.normal(38, 12, n).clip(18, 70).astype(int),
            '性别': np.random.choice(['男', '女'], n),
            '婚姻状况': np.random.choice(['未婚', '已婚', '离异', '丧偶'], n, p=[0.25, 0.60, 0.10, 0.05]),
            '教育程度': np.random.choice(['高中以下', '大专', '本科', '硕士', '博士'], n, p=[0.15, 0.20, 0.40, 0.20, 0.05]),
            '年收入': np.random.lognormal(11, 0.8, n).round(0),
            '工作年限': np.random.poisson(8, n),
            '信用评分': np.random.normal(650, 100, n).clip(300, 850).astype(int),
            '负债收入比': np.random.beta(2, 5, n).round(3),
            '信用卡数量': np.random.poisson(2, n),
            '贷款次数': np.random.poisson(1, n),
            '逾期次数': np.random.poisson(0.3, n),
            '房产数量': np.random.choice([0, 1, 2, 3], n, p=[0.40, 0.45, 0.12, 0.03]),
            '是否有车': np.random.choice(['是', '否'], n, p=[0.55, 0.45]),
            '就业类型': np.random.choice(['全职', '兼职', '自由职业', '失业', '退休'], n, p=[0.65, 0.10, 0.15, 0.05, 0.05]),
            '申请金额': np.random.lognormal(10, 1, n).round(0),
            '贷款期限': np.random.choice([12, 24, 36, 48, 60], n),
            '违约标签': np.random.choice(['正常', '违约'], n, p=[0.85, 0.15])
        }
        
        df = pd.DataFrame(data)
        
        # 添加关联性：信用评分与违约的关系
        low_credit = df['信用评分'] < 550
        df.loc[low_credit, '违约标签'] = np.random.choice(
            ['正常', '违约'],
            low_credit.sum(),
            p=[0.4, 0.6]
        )
        
        # 添加关联性：高负债收入比增加违约风险
        high_debt = df['负债收入比'] > 0.5
        df.loc[high_debt, '违约标签'] = np.random.choice(
            ['正常', '违约'],
            high_debt.sum(),
            p=[0.5, 0.5]
        )
        
        # 添加关联性：逾期次数与违约
        has_overdue = df['逾期次数'] > 0
        df.loc[has_overdue, '违约标签'] = np.random.choice(
            ['正常', '违约'],
            has_overdue.sum(),
            p=[0.3, 0.7]
        )
        
        # 添加关联性：失业人员违约率高
        unemployed = df['就业类型'] == '失业'
        df.loc[unemployed, '违约标签'] = np.random.choice(
            ['正常', '违约'],
            unemployed.sum(),
            p=[0.3, 0.7]
        )
        
        return df
    
    def _generate_education_data(self, n_samples: int = None) -> pd.DataFrame:
        """生成教育成绩分析数据"""
        n = n_samples or 1500
        np.random.seed(42)
        
        data = {
            '学生ID': [f'STU_{i:04d}' for i in range(n)],
            '年级': np.random.choice(['高一', '高二', '高三'], n),
            '班级': np.random.choice([f'{i}班' for i in range(1, 11)], n),
            '性别': np.random.choice(['男', '女'], n),
            '年龄': np.random.choice([15, 16, 17, 18], n),
            '每日学习时长': np.random.normal(3, 1.5, n).clip(0.5, 10).round(1),
            '每周作业完成率': np.random.beta(7, 2, n).round(2),
            '出勤率': np.random.beta(19, 1, n).round(2),
            '课外活动参与度': np.random.choice(['高', '中', '低'], n, p=[0.2, 0.5, 0.3]),
            '是否参加补习班': np.random.choice(['是', '否'], n, p=[0.35, 0.65]),
            '数学成绩': np.random.normal(75, 15, n).clip(0, 100).astype(int),
            '语文成绩': np.random.normal(78, 12, n).clip(0, 100).astype(int),
            '英语成绩': np.random.normal(72, 18, n).clip(0, 100).astype(int),
            '综合成绩': None,  # 稍后计算
            '学习态度评分': np.random.choice(['优秀', '良好', '一般', '需改进'], n, p=[0.25, 0.40, 0.25, 0.10])
        }
        
        df = pd.DataFrame(data)
        
        # 计算综合成绩
        df['综合成绩'] = (df['数学成绩'] + df['语文成绩'] + df['英语成绩']) / 3
        
        # 添加关联性：学习时长与成绩
        df['数学成绩'] += (df['每日学习时长'] - 3) * 3
        df['语文成绩'] += (df['每日学习时长'] - 3) * 2
        df['英语成绩'] += (df['每日学习时长'] - 3) * 2.5
        
        # 添加关联性：补习班效果
        tutored = df['是否参加补习班'] == '是'
        df.loc[tutored, '数学成绩'] += np.random.normal(5, 3, tutored.sum())
        df.loc[tutored, '语文成绩'] += np.random.normal(4, 3, tutored.sum())
        df.loc[tutored, '英语成绩'] += np.random.normal(6, 4, tutored.sum())
        
        # 确保成绩在有效范围内
        df['数学成绩'] = df['数学成绩'].clip(0, 100).astype(int)
        df['语文成绩'] = df['语文成绩'].clip(0, 100).astype(int)
        df['英语成绩'] = df['英语成绩'].clip(0, 100).astype(int)
        df['综合成绩'] = df['综合成绩'].clip(0, 100).round(1)
        
        # 添加关联性：出勤率影响成绩
        low_attendance = df['出勤率'] < 0.8
        df.loc[low_attendance, '综合成绩'] *= 0.85
        
        return df
    
    def _generate_marketing_data(self, n_samples: int = None) -> pd.DataFrame:
        """生成市场营销效果数据"""
        n = n_samples or 1200
        np.random.seed(42)
        
        channels = ['邮件营销', '社交媒体', '搜索引擎', '展示广告', '短信营销', '线下活动']
        promotions = ['折扣', '满减', '赠品', '积分', '限时', '无促销']
        customer_segments = ['新客户', '普通客户', '忠诚客户', '流失风险', '高价值']
        
        data = {
            '客户ID': [f'MKT_{i:05d}' for i in range(n)],
            '营销渠道': np.random.choice(channels, n),
            '促销类型': np.random.choice(promotions, n, p=[0.25, 0.20, 0.15, 0.20, 0.15, 0.05]),
            '客户细分': np.random.choice(customer_segments, n, p=[0.20, 0.35, 0.25, 0.10, 0.10]),
            '客户年龄': np.random.normal(32, 10, n).clip(18, 70).astype(int),
            '客户价值分': np.random.normal(60, 20, n).clip(10, 100).astype(int),
            '历史购买次数': np.random.poisson(5, n),
            '历史消费金额': np.random.lognormal(6, 1.2, n).round(2),
            '邮件打开率': np.random.beta(3, 7, n).round(3),
            '点击率': np.random.beta(2, 50, n).round(4),
            '访问页面数': np.random.poisson(3, n) + 1,
            '停留时长': np.random.exponential(180, n).round(0),
            '是否响应': np.random.choice(['是', '否'], n, p=[0.15, 0.85]),
            '是否转化': np.random.choice(['是', '否'], n, p=[0.08, 0.92]),
            '转化金额': 0,  # 稍后填充
            '营销活动成本': np.random.lognormal(3, 0.5, n).round(2)
        }
        
        df = pd.DataFrame(data)
        
        # 添加关联性：忠诚客户和高价值客户响应率更高
        loyal_mask = df['客户细分'].isin(['忠诚客户', '高价值'])
        df.loc[loyal_mask, '是否响应'] = np.random.choice(
            ['是', '否'],
            loyal_mask.sum(),
            p=[0.35, 0.65]
        )
        
        # 添加关联性：促销类型影响转化率
        promotion_mask = df['促销类型'] != '无促销'
        df.loc[promotion_mask, '是否转化'] = np.random.choice(
            ['是', '否'],
            promotion_mask.sum(),
            p=[0.12, 0.88]
        )
        
        # 填充转化金额
        converted = df['是否转化'] == '是'
        df.loc[converted, '转化金额'] = np.random.lognormal(5, 0.8, converted.sum()).round(2)
        df.loc[~converted, '转化金额'] = 0
        
        return df
    
    def _generate_iris_extended(self, n_samples: int = None) -> pd.DataFrame:
        """生成扩展鸢尾花数据集"""
        n = n_samples or 300
        np.random.seed(42)
        
        # 原始鸢尾花特征
        species = ['山鸢尾', '变色鸢尾', '维吉尼亚鸢尾']
        locations = ['温室', '野外', '花圃', '实验室']
        
        data = []
        for i in range(n):
            specie = np.random.choice(species)
            
            # 根据品种设置基础特征
            if specie == '山鸢尾':
                sepal_len = np.random.normal(5.0, 0.4)
                sepal_width = np.random.normal(3.4, 0.4)
                petal_len = np.random.normal(1.5, 0.2)
                petal_width = np.random.normal(0.2, 0.1)
            elif specie == '变色鸢尾':
                sepal_len = np.random.normal(5.9, 0.5)
                sepal_width = np.random.normal(2.8, 0.4)
                petal_len = np.random.normal(4.3, 0.5)
                petal_width = np.random.normal(1.3, 0.2)
            else:  # 维吉尼亚
                sepal_len = np.random.normal(6.5, 0.6)
                sepal_width = np.random.normal(3.0, 0.4)
                petal_len = np.random.normal(5.5, 0.6)
                petal_width = np.random.normal(2.0, 0.3)
            
            record = {
                '花萼长度': round(sepal_len, 2),
                '花萼宽度': round(sepal_width, 2),
                '花瓣长度': round(petal_len, 2),
                '花瓣宽度': round(petal_width, 2),
                '品种': specie,
                '生长地': np.random.choice(locations),
                '植株高度': round(np.random.normal(30, 10), 1),
                '叶片数量': np.random.poisson(8) + 3,
                '开花次数': np.random.poisson(2) + 1,
                '健康状况': np.random.choice(['优', '良', '中'], p=[0.5, 0.35, 0.15])
            }
            data.append(record)
        
        df = pd.DataFrame(data)
        
        # 添加特征关联
        df['花瓣面积'] = (df['花瓣长度'] * df['花瓣宽度']).round(2)
        df['花萼面积'] = (df['花萼长度'] * df['花萼宽度']).round(2)
        df['长宽比'] = (df['花瓣长度'] / df['花瓣宽度'].replace(0, 0.1)).round(2)
        
        return df


# 创建全局实例
sample_data_generator = SampleDataGenerator()
