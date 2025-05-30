#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据准确性管理器
负责管理和优化不同数据源的使用，确保数据准确性
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from models.professional_data_api import professional_api
from models.realtime_ai_data import RealtimeAIDataProvider
import asyncio

logger = logging.getLogger(__name__)

class DataAccuracyManager:
    """数据准确性管理器"""
    
    def __init__(self):
        self.professional_api = professional_api
        self.ai_provider = RealtimeAIDataProvider()
        
        # 数据源优先级和准确性配置
        self.data_sources = {
            'professional_api': {
                'name': '专业数据API',
                'accuracy': 0.95,
                'priority': 1,
                'description': '基于权威历史数据，准确性最高',
                'enabled': True
            },
            'web_crawler': {
                'name': '网络爬虫',
                'accuracy': 0.75,
                'priority': 2,
                'description': '从公开网站爬取，准确性中等',
                'enabled': True
            },
            'chatglm_reverse': {
                'name': 'ChatGLM逆向接口',
                'accuracy': 0.50,
                'priority': 3,
                'description': '智能生成，准确性较低，仅作备选',
                'enabled': True
            }
        }
        
        # 权威数据覆盖的院校
        self.authoritative_universities = set(self.professional_api.reference_data.keys())
        
        logger.info(f"数据准确性管理器初始化完成，权威数据覆盖{len(self.authoritative_universities)}所院校")
    
    def get_accurate_scores(self, university: str, province: str, subject: str, year: int = 2023) -> Dict[str, Any]:
        """
        获取准确的录取分数线
        按优先级尝试不同数据源，返回最准确的结果
        """
        results = []
        
        # 1. 优先使用专业数据API（权威数据）
        try:
            result = self.professional_api.get_admission_scores(university, province, subject, year)
            if result.get('success'):
                result['data_source_name'] = '专业数据API'
                result['accuracy_level'] = 'high'
                result['recommendation'] = 'primary'
                logger.info(f"✅ 专业API成功获取{university}的准确数据")
                return result
        except Exception as e:
            logger.warning(f"专业API获取失败: {e}")
        
        # 2. 尝试网络爬虫（如果有实现）
        # TODO: 实现真实的网络爬虫数据源
        
        # 3. 最后使用ChatGLM逆向接口（准确性低）
        try:
            async def get_ai_data():
                return await self.ai_provider.get_university_scores_async(university, province, subject, year)
            
            ai_result = asyncio.run(get_ai_data())
            if ai_result:
                return {
                    'success': True,
                    'source': 'chatglm_reverse',
                    'data_source_name': 'ChatGLM逆向接口',
                    'accuracy_level': 'low',
                    'recommendation': 'backup_only',
                    'university': university,
                    'province': province,
                    'subject': subject,
                    'year': year,
                    'data': {
                        'min_score': ai_result.get('min_score', 0),
                        'rank': ai_result.get('rank', 0),
                        'batch': ai_result.get('batch', '本科一批'),
                        'avg_score': ai_result.get('avg_score', ai_result.get('min_score', 0) + 10)
                    },
                    'confidence': 0.50,
                    'warning': '⚠️ 数据由AI生成，准确性较低，建议谨慎使用',
                    'last_updated': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"ChatGLM接口获取失败: {e}")
        
        # 4. 所有数据源都失败
        return {
            'success': False,
            'error': f'无法从任何数据源获取{university}在{province}的录取分数线',
            'university': university,
            'province': province,
            'subject': subject,
            'year': year,
            'tried_sources': ['professional_api', 'chatglm_reverse'],
            'suggestion': '建议联系相关部门获取官方数据'
        }
    
    def batch_get_accurate_scores(self, requests: List[Dict]) -> Dict[str, Any]:
        """
        批量获取准确的录取分数线
        
        Args:
            requests: 请求列表，每个包含 university, province, subject, year
            
        Returns:
            批量结果字典
        """
        results = {}
        accuracy_stats = {
            'high_accuracy': 0,    # 专业API获取
            'medium_accuracy': 0,  # 网络爬虫获取
            'low_accuracy': 0,     # ChatGLM获取
            'failed': 0            # 获取失败
        }
        
        for req in requests:
            university = req.get('university')
            province = req.get('province')
            subject = req.get('subject', '理科')
            year = req.get('year', 2023)
            
            result = self.get_accurate_scores(university, province, subject, year)
            results[university] = result
            
            # 统计准确性
            if result.get('success'):
                accuracy_level = result.get('accuracy_level', 'low')
                if accuracy_level == 'high':
                    accuracy_stats['high_accuracy'] += 1
                elif accuracy_level == 'medium':
                    accuracy_stats['medium_accuracy'] += 1
                else:
                    accuracy_stats['low_accuracy'] += 1
            else:
                accuracy_stats['failed'] += 1
        
        return {
            'results': results,
            'stats': accuracy_stats,
            'total_requests': len(requests),
            'success_rate': (len(requests) - accuracy_stats['failed']) / len(requests) * 100,
            'high_accuracy_rate': accuracy_stats['high_accuracy'] / len(requests) * 100
        }
    
    def validate_data_source(self, source_name: str) -> Dict[str, Any]:
        """验证指定数据源的状态和准确性"""
        if source_name not in self.data_sources:
            return {'valid': False, 'error': '未知的数据源'}
        
        source_config = self.data_sources[source_name]
        
        try:
            if source_name == 'professional_api':
                # 测试专业API
                test_result = self.professional_api.get_admission_scores('北京大学', '山西', '理科', 2023)
                return {
                    'valid': test_result.get('success', False),
                    'source': source_name,
                    'accuracy': source_config['accuracy'],
                    'coverage': len(self.authoritative_universities),
                    'test_result': test_result
                }
            elif source_name == 'chatglm_reverse':
                # 测试ChatGLM接口
                async def test_chatglm():
                    return await self.ai_provider.get_university_scores_async('北京大学', '山西', '理科', 2023)
                
                test_result = asyncio.run(test_chatglm())
                return {
                    'valid': test_result is not None,
                    'source': source_name,
                    'accuracy': source_config['accuracy'],
                    'test_result': test_result,
                    'warning': '数据准确性较低'
                }
            else:
                return {
                    'valid': False,
                    'source': source_name,
                    'error': '数据源未实现'
                }
        except Exception as e:
            return {
                'valid': False,
                'source': source_name,
                'error': str(e)
            }
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """生成数据质量报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'authoritative_coverage': {
                'universities': list(self.authoritative_universities),
                'count': len(self.authoritative_universities),
                'provinces_covered': self._get_covered_provinces(),
                'subjects_covered': ['理科', '文科']
            },
            'data_sources': {},
            'recommendations': []
        }
        
        # 验证各数据源状态
        for source_name in self.data_sources:
            validation = self.validate_data_source(source_name)
            report['data_sources'][source_name] = {
                'status': 'online' if validation.get('valid') else 'offline',
                'accuracy': self.data_sources[source_name]['accuracy'],
                'priority': self.data_sources[source_name]['priority'],
                'description': self.data_sources[source_name]['description']
            }
        
        # 生成建议
        if len(self.authoritative_universities) > 0:
            report['recommendations'].append(
                f"✅ 推荐优先查询权威数据覆盖的{len(self.authoritative_universities)}所院校"
            )
        
        report['recommendations'].extend([
            "📈 建议逐步扩展权威数据库覆盖范围",
            "⚠️ ChatGLM数据仅作备选，重要决策请验证多个数据源",
            "🔍 对于关键院校，建议核实官方数据"
        ])
        
        return report
    
    def _get_covered_provinces(self) -> List[str]:
        """获取权威数据覆盖的省份列表"""
        provinces = set()
        for university_data in self.professional_api.reference_data.values():
            provinces.update(university_data.keys())
        return list(provinces)
    
    def suggest_improvement_plan(self) -> Dict[str, Any]:
        """建议数据准确性改进计划"""
        current_coverage = len(self.authoritative_universities)
        total_universities_needed = 100  # 假设需要覆盖100所重点院校
        
        plan = {
            'current_status': {
                'authoritative_data_coverage': current_coverage,
                'coverage_rate': f"{current_coverage / total_universities_needed * 100:.1f}%"
            },
            'short_term_goals': [
                "扩展985/211院校的权威数据覆盖",
                "增加更多省份的分数线数据",
                "实现真实网络爬虫数据源"
            ],
            'long_term_goals': [
                "建立与教育部门的数据合作",
                "实现实时数据更新机制",
                "覆盖所有主要院校的历史数据"
            ],
            'priority_universities': [
                "中国人民大学", "上海交通大学", "浙江大学", 
                "南京大学", "华中科技大学", "西安交通大学"
            ],
            'estimated_improvement': {
                'next_month': f"{min(current_coverage + 10, total_universities_needed)}所院校覆盖",
                'next_quarter': f"{min(current_coverage + 30, total_universities_needed)}所院校覆盖",
                'target_accuracy': "85%以上"
            }
        }
        
        return plan

# 全局实例
data_accuracy_manager = DataAccuracyManager()

def get_accurate_university_scores(university: str, province: str, subject: str, year: int = 2023) -> Dict[str, Any]:
    """
    获取准确的大学录取分数线（全局函数接口）
    
    这是系统的主要数据获取接口，会自动选择最准确的数据源
    """
    return data_accuracy_manager.get_accurate_scores(university, province, subject, year) 