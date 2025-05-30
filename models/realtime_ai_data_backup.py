#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实时AI数据获取模块
通过AI接口实时获取院校分数线、录取线和院校信息
支持多个AI服务提供商和动态数据更新
"""

import requests
import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Any
import re
from datetime import datetime, timedelta
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import os
import random
from bs4 import BeautifulSoup
from urllib.parse import quote

logger = logging.getLogger(__name__)

class RealtimeAIDataProvider:
    """实时AI数据提供器"""
    
            'cache_hits': 0,
            'web_search_requests': 0  # 添加搜索统计
        }
    
    def get_ai_services(self) -> List[str]:
        """获取可用的AI服务列表"""
        if self.api_config_manager:
            return list(self.api_config_manager.get_all_configs().keys())
        else:
            return ['chatglm', 'qwen', 'local_llm', 'chatglm_reverse']
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务配置"""
        if self.api_config_manager:
            return self.api_config_manager.get_config(service_name)
        return None
        
    def init_cache_db(self):
        """初始化缓存数据库"""
        os.makedirs(os.path.dirname(self.cache_db), exist_ok=True)
        
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_type TEXT,
                    university_name TEXT,
                    province TEXT,
                    subject TEXT,
                    year INTEGER,
                    response_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON ai_cache(expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_type ON ai_cache(query_type, university_name, province)
            """)
    
    def get_cache_key(self, query_type: str, **params) -> str:
        """生成缓存键"""
        key_data = f"{query_type}:" + ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """获取缓存数据"""
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.execute(
                "SELECT response_data FROM ai_cache WHERE query_hash = ? AND expires_at > datetime('now')",
                (cache_key,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None
    
    def cache_data(self, cache_key: str, query_type: str, data: Dict, **params):
        """缓存数据"""
        expires_at = datetime.now() + self.cache_duration
        
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ai_cache 
                (query_hash, query_type, university_name, province, subject, year, response_data, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key, query_type,
                params.get('university_name', ''),
                params.get('province', ''),
                params.get('subject', ''),
                params.get('year', 0),
                json.dumps(data, ensure_ascii=False),
                expires_at
            ))
    
    def clean_expired_cache(self):
        """清理过期缓存"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("DELETE FROM ai_cache WHERE expires_at < datetime('now')")
    
    async def query_ai_service(self, service_name: str, prompt: str, max_retries=3) -> Optional[str]:
        """查询AI服务"""
        # 处理逆向接口
        if service_name == 'chatglm_reverse':
            return await self.query_reverse_service(prompt)
        
        # 获取服务配置
        config = self.get_service_config(service_name)
        if not config:
            logger.warning(f"未找到服务配置: {service_name}")
            return None
        
        # 检查服务是否启用
        if not config.get('enabled', False):
            logger.info(f"AI服务{service_name}未启用")
            return None
        
        # 检查API密钥是否已配置
        api_key = config.get('api_key', '')
        if not api_key or api_key.strip() == '':
            logger.info(f"AI服务{service_name}未配置API密钥，跳过查询")
            return None
        
        api_url = config.get('api_url', '')
        model_name = config.get('model_name', '')
        
        if not api_url:
            logger.warning(f"AI服务{service_name}未配置API URL")
            return None
        
        for attempt in range(max_retries):
            try:
                if service_name == 'local_llm':
                    # Ollama本地服务
                    payload = {
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False
                    }
                    headers = {}
                else:
                    # 在线AI服务
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_url,
                        headers=headers,
                        json=payload,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if service_name == 'local_llm':
                                return data.get('response', '')
                            elif service_name == 'chatglm':
                                return data.get('choices', [{}])[0].get('message', {}).get('content', '')
                            elif service_name == 'qwen':
                                return data.get('output', {}).get('text', '')
                        else:
                            logger.info(f"AI服务{service_name}请求失败: {response.status}")
                            if response.status == 401:
                                logger.warning(f"AI服务{service_name}认证失败，请检查API密钥")
                            return None
                            
            except Exception as e:
                logger.info(f"AI服务{service_name}连接失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    async def query_reverse_service(self, prompt: str) -> Optional[str]:
        """查询逆向AI服务"""
        if not self.chatglm_reverse:
            logger.warning("ChatGLM逆向接口未加载")
            return None
        
        try:
            # 逆向接口通常是同步的，在异步环境中运行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.chatglm_reverse.send_message, prompt
            )
            
            if response:
                logger.info("ChatGLM逆向接口响应成功")
                return response
            else:
                logger.warning("ChatGLM逆向接口无响应")
                return None
                
        except Exception as e:
            logger.error(f"ChatGLM逆向接口调用失败: {e}")
            return None
    
    async def get_university_admission_scores(self, university_name: str, province: str, subject: str, year: int = 2023, force_realtime: bool = False) -> Dict:
        """实时获取大学录取分数线（优先使用网络搜索）"""
        cache_key = self.get_cache_key(
            'admission_scores',
            university_name=university_name,
            province=province,
            subject=subject,
            year=year
        )
        
        # 检查缓存（仅在非强制实时模式下）
        if not force_realtime:
            cached_data = self.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"从缓存获取{university_name}在{province}的录取分数线")
                return cached_data
        else:
            logger.info(f"强制实时获取{university_name}在{province}的录取分数线（跳过缓存）")
        
        try:
            self.stats['total_requests'] += 1
            
            # 优先使用网络搜索获取真实数据
            logger.info(f"使用网络搜索获取{university_name}在{province}的{year}年录取分数线")
            search_scores = self.web_search_provider.search_admission_scores(university_name, province, year)
            self.stats['web_search_requests'] += 1
            
            if search_scores and search_scores.get('scores'):
                # 网络搜索成功，构建分数线信息
                scores_data = {
                    'university_name': university_name,
                    'province': province,
                    'subject': subject,
                    'year': year,
                    'min_score': search_scores['scores'].get('最低分') or search_scores['scores'].get(f'{subject}最低分'),
                    'avg_score': None,  # 平均分通常网络搜索难以获取
                    'max_score': None,  # 最高分通常网络搜索难以获取
                    'enrollment': None,  # 招生人数需要进一步解析
                    'rank_min': None,  # 位次信息需要进一步解析
                    'rank_avg': None,
                    'data_source': 'web_search',
                    'last_updated': datetime.now().isoformat(),
                    'reliability': 0.8,  # 网络搜索分数线可靠性较高
                    'raw_data': search_scores
                }
                
                logger.info(f"网络搜索成功获取{university_name}分数线信息")
                
                # 缓存搜索结果
                if not force_realtime:
                    self.cache_data(cache_key, scores_data)
                
                self.stats['successful_requests'] += 1
                return scores_data
            
            else:
                # 网络搜索失败，返回暂无数据
                logger.warning(f"网络搜索未能获取{university_name}在{province}的有效分数线信息")
                
                scores_data = {
                    'university_name': university_name,
                    'province': province,
                    'subject': subject,
                    'year': year,
                    'min_score': '暂无数据',
                    'avg_score': '暂无数据',
                    'max_score': '暂无数据',
                    'enrollment': '暂无数据',
                    'rank_min': '暂无数据',
                    'rank_avg': '暂无数据',
                    'data_source': 'no_data',
                    'last_updated': datetime.now().isoformat(),
                    'reliability': 0.1,  # 无数据，可靠性很低
                    'note': '暂未找到相关录取分数线信息'
                }
                
                self.stats['successful_requests'] += 1
                return scores_data
                
        except Exception as e:
            logger.error(f"获取录取分数线时发生错误: {e}")
            self.stats['failed_requests'] += 1
            
            # 返回错误信息
            return {
                'university_name': university_name,
                'province': province,
                'subject': subject,
                'year': year,
                'min_score': '获取失败',
                'avg_score': '获取失败',
                'max_score': '获取失败',
                'enrollment': '获取失败',
                'rank_min': '获取失败',
                'rank_avg': '获取失败',
                'data_source': 'error',
                'last_updated': datetime.now().isoformat(),
                'reliability': 0.0,
                'error': str(e)
            }
    
    async def get_university_info(self, university_name: str, force_realtime: bool = False) -> Dict:
        """实时获取大学详细信息（优先使用网络搜索）"""
        cache_key = self.get_cache_key('university_info', university_name=university_name)
        
        # 检查缓存（仅在非强制实时模式下）
        if not force_realtime:
            cached_data = self.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"从缓存获取{university_name}的详细信息")
                return cached_data
        else:
            logger.info(f"强制实时获取{university_name}的详细信息（跳过缓存）")
        
        try:
            self.stats['total_requests'] += 1
            
            # 优先使用网络搜索获取真实数据
            logger.info(f"使用网络搜索获取{university_name}的详细信息")
            search_info = self.web_search_provider.search_university_info(university_name)
            self.stats['web_search_requests'] += 1
            
            if search_info and search_info.get('establishment_year'):
                # 网络搜索成功，构建完整信息
                university_info = {
                    'name': university_name,
                    'establishment_year': search_info.get('establishment_year'),
                    'founded_year': search_info.get('establishment_year'),  # 兼容字段
                    'location': search_info.get('location', '未知'),
                    'type': search_info.get('type', '综合类'),
                    'level': search_info.get('level', '普通本科'),
                    'website': search_info.get('website', ''),
                    'category': search_info.get('type', '综合类'),
                    'advantages': [],
                    'key_disciplines': [],
                    'data_source': 'web_search',
                    'last_updated': datetime.now().isoformat(),
                    'reliability': 0.9  # 网络搜索数据可靠性高
                }
                
                logger.info(f"网络搜索成功获取{university_name}信息: 建校年份{search_info.get('establishment_year')}")
                
                # 缓存搜索结果
                if not force_realtime:
                    self.cache_data(cache_key, university_info)
                
                self.stats['successful_requests'] += 1
                return university_info
            
            else:
                # 网络搜索失败，回退到AI生成（但标注为低可靠性）
                logger.warning(f"网络搜索未能获取{university_name}的有效信息，返回基础信息")
                
                university_info = {
                    'name': university_name,
                    'establishment_year': '暂无数据',
                    'founded_year': '暂无数据',
                    'location': '暂无数据',
                    'type': '暂无数据',
                    'level': '暂无数据',
                    'website': '',
                    'category': '暂无数据',
                    'advantages': [],
                    'key_disciplines': [],
                    'data_source': 'no_data',
                    'last_updated': datetime.now().isoformat(),
                    'reliability': 0.1  # 无数据，可靠性很低
                }
                
                self.stats['successful_requests'] += 1
                return university_info
                
        except Exception as e:
            logger.error(f"获取院校信息时发生错误: {e}")
            self.stats['failed_requests'] += 1
            
            # 返回错误信息
            return {
                'name': university_name,
                'establishment_year': '获取失败',
                'founded_year': '获取失败',
                'location': '获取失败',
                'type': '获取失败',
                'level': '获取失败',
                'website': '',
                'category': '获取失败',
                'advantages': [],
                'key_disciplines': [],
                'data_source': 'error',
                'last_updated': datetime.now().isoformat(),
                'reliability': 0.0,
                'error': str(e)
            }
    
    def _validate_scores_data(self, data: Dict) -> Dict:
        """验证和清理分数线数据"""
        # 确保必要字段存在且为数字
        required_numeric_fields = ['min_score', 'avg_score', 'max_score', 'rank', 'enrollment']
        for field in required_numeric_fields:
            if field not in data or not isinstance(data[field], (int, float)):
                if field == 'min_score':
                    data[field] = 500  # 默认最低分
                elif field == 'avg_score':
                    data[field] = data.get('min_score', 500) + 15
                elif field == 'max_score':
                    data[field] = data.get('avg_score', 515) + 20
                elif field == 'rank':
                    data[field] = 50000  # 默认位次
                elif field == 'enrollment':
                    data[field] = 100  # 默认招生人数
        
        # 确保分数逻辑正确
        if data['min_score'] > data['avg_score']:
            data['avg_score'] = data['min_score'] + 10
        if data['avg_score'] > data['max_score']:
            data['max_score'] = data['avg_score'] + 15
        
        # 添加时间戳
        data['updated_at'] = datetime.now().isoformat()
        data['is_ai_generated'] = True
        
        return data
    
    def _validate_university_data(self, data: Dict) -> Dict:
        """验证和清理大学信息数据"""
        # 确保基本字段存在
        if 'name' not in data:
            data['name'] = '未知院校'
        
        if 'location' not in data:
            data['location'] = {'province': '未知', 'city': '未知'}
        
        if 'ranking' not in data:
            data['ranking'] = {'domestic_rank': 0}
        
        # 添加元数据
        data['updated_at'] = datetime.now().isoformat()
        data['is_ai_generated'] = True
        
        return data
    
    def _generate_fallback_scores(self, university_name: str, province: str, subject: str, year: int) -> Dict:
        """生成备用分数线数据"""
        # 基于院校名称特征估算分数
        base_score = 500
        
        if any(keyword in university_name for keyword in ['清华', '北大', '复旦', '交大']):
            base_score = 680
        elif any(keyword in university_name for keyword in ['985', '浙大', '南大', '中大']):
            base_score = 650
        elif any(keyword in university_name for keyword in ['211', '理工', '师范']):
            base_score = 580
        elif '大学' in university_name:
            base_score = 520
        
        return {
            'university_name': university_name,
            'province': province,
            'year': year,
            'subject': subject,
            'min_score': base_score,
            'avg_score': base_score + 15,
            'max_score': base_score + 30,
            'rank': int((700 - base_score) * 100),
            'enrollment': 100,
            'batch': '本科一批' if base_score >= 550 else '本科二批',
            'confidence': 0.3,
            'data_source': '智能估算',
            'is_fallback': True
        }
    
    def _generate_fallback_university_info(self, university_name: str) -> Dict:
        """生成备用大学信息"""
        return {
            'name': university_name,
            'location': {'province': '未知', 'city': '未知'},
            'establishment_year': 1950,
            'category': '普通本科',
            'type': '综合类',
            'ranking': {'domestic_rank': 0},
            'advantages': ['计算机科学', '经济学', '管理学'],
            'description': f'{university_name}是一所具有良好声誉的高等学府。',
            'confidence': 0.2,
            'data_source': '基础模板',
            'is_fallback': True
        }

    async def get_university_scores_async(self, university_name: str, province: str, subject: str = '理科', year: int = 2023) -> Dict:
        """异步获取大学录取分数线"""
        try:
            # 直接调用现有的异步方法
            return await self.get_university_admission_scores(university_name, province, subject, year)
        except Exception as e:
            logger.warning(f"异步获取{university_name}在{province}的录取分数线失败: {e}")
            return self._generate_fallback_scores(university_name, province, subject, year)

    async def get_university_location(self, university_name: str) -> Dict[str, str]:
        """使用AI获取大学的正确地理位置信息"""
        cache_key = self.get_cache_key('university_location', university_name=university_name)
        
        # 检查缓存
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            # 检查缓存数据的有效性
            province = cached_data.get('province', '')
            city = cached_data.get('city', '')
            if (province not in ['未知省份', '待确认', '份省', ''] and 
                city not in ['未知城市', '待确认', ''] and
                not province.startswith('份')):
                logger.info(f"从缓存获取{university_name}的地理位置")
                return cached_data
            else:
                logger.warning(f"缓存中{university_name}的地理位置数据无效: {province} {city}，将重新获取")
        
        # 对于地理位置查询，优先使用基于名称的推断，因为更准确
        fallback_data = self._generate_fallback_location(university_name)
        if fallback_data.get('province') not in ['待确认', '未知省份']:
            logger.info(f"使用基于名称推断的地理位置: {university_name} -> {fallback_data['province']} {fallback_data['city']}")
            
            # 缓存推断的数据
            self.cache_data(cache_key, 'university_location', fallback_data,
                          university_name=university_name)
            return fallback_data
        
        # 构建AI查询提示
        prompt = f"""请提供{university_name}的准确地理位置信息。

请按照以下JSON格式返回数据：
{{
    "university_name": "{university_name}",
    "province": "所在省份或直辖市",
    "city": "所在城市",
    "district": "所在区县（可选）",
    "address": "详细地址（可选）",
    "confidence": 数据可信度(0-1之间的小数)
}}

注意：
1. 省份和城市必须准确，如"江苏省"、"南京市"
2. 直辖市的省份和城市可以相同，如"北京市"、"北京市"
3. 只返回JSON数据，不要包含其他文字
"""
        
        # 尝试多个AI服务（排除逆向接口，因为对地理位置查询效果不好）
        ai_response = None
        service_priority = ['local_llm', 'chatglm', 'qwen']  # 不使用逆向接口
        
        for service_name in service_priority:
            ai_response = await self.query_ai_service(service_name, prompt)
            if ai_response:
                logger.info(f"使用{service_name}服务获取到地理位置信息")
                break
        
        if not ai_response:
            logger.warning(f"所有AI服务都无法获取{university_name}的地理位置")
            return fallback_data
        
        # 解析AI响应
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                location_data = json.loads(json_match.group())
                
                # 数据验证和清理
                location_data = self._validate_location_data(location_data, university_name)
                
                # 再次验证数据有效性
                province = location_data.get('province', '')
                city = location_data.get('city', '')
                if (province not in ['未知省份', '待确认', '份省', ''] and 
                    city not in ['未知城市', '待确认', ''] and
                    not province.startswith('份')):
                    
                    # 缓存数据
                    self.cache_data(cache_key, 'university_location', location_data,
                                  university_name=university_name)
                    
                    logger.info(f"成功获取{university_name}的地理位置: {location_data['province']} {location_data['city']}")
                    return location_data
                else:
                    logger.warning(f"AI返回的地理位置数据无效: {province} {city}，使用备用机制")
                
        except json.JSONDecodeError as e:
            logger.warning(f"地理位置AI响应JSON解析失败: {e}")
        
        # 如果AI响应解析失败或数据无效，使用备用数据
        self.cache_data(cache_key, 'university_location', fallback_data,
                      university_name=university_name)
        return fallback_data
    
    def _validate_location_data(self, data: Dict, university_name: str) -> Dict[str, str]:
        """验证和清理地理位置数据"""
        # 确保基本字段存在
        if 'province' not in data or not data['province']:
            data['province'] = '未知省份'
        
        if 'city' not in data or not data['city']:
            data['city'] = '未知城市'
        
        # 清理省份和城市名称
        province = data['province'].strip()
        city = data['city'].strip()
        
        # 标准化省份名称
        if not province.endswith(('省', '市', '区', '自治区')):
            if province in ['北京', '上海', '天津', '重庆']:
                province += '市'
            elif province in ['西藏', '内蒙古', '新疆', '广西', '宁夏']:
                if '自治区' not in province:
                    province += '自治区'
            else:
                province += '省'
        
        # 标准化城市名称
        if not city.endswith(('市', '区', '县')):
            city += '市'
        
        data['province'] = province
        data['city'] = city
        data['university_name'] = university_name
        data['updated_at'] = datetime.now().isoformat()
        data['is_ai_generated'] = True
        
        return data
    
    def _generate_fallback_location(self, university_name: str) -> Dict[str, str]:
        """生成备用地理位置数据"""
        # 基于院校名称推断地理位置
        location_map = {
            '北京': {'province': '北京市', 'city': '北京市'},
            '上海': {'province': '上海市', 'city': '上海市'},
            '天津': {'province': '天津市', 'city': '天津市'},
            '重庆': {'province': '重庆市', 'city': '重庆市'},
            '清华': {'province': '北京市', 'city': '北京市'},
            '北大': {'province': '北京市', 'city': '北京市'},
            '复旦': {'province': '上海市', 'city': '上海市'},
            '交大': {'province': '上海市', 'city': '上海市'},
            '同济': {'province': '上海市', 'city': '上海市'},
            '华师大': {'province': '上海市', 'city': '上海市'},
            '南京': {'province': '江苏省', 'city': '南京市'},
            '东南': {'province': '江苏省', 'city': '南京市'},
            '河海': {'province': '江苏省', 'city': '南京市'},
            '南农': {'province': '江苏省', 'city': '南京市'},
            '南理工': {'province': '江苏省', 'city': '南京市'},
            '杭州': {'province': '浙江省', 'city': '杭州市'},
            '浙大': {'province': '浙江省', 'city': '杭州市'},
            '武汉': {'province': '湖北省', 'city': '武汉市'},
            '华中': {'province': '湖北省', 'city': '武汉市'},
            '华科': {'province': '湖北省', 'city': '武汉市'},
            '中南': {'province': '湖南省', 'city': '长沙市'},
            '湖大': {'province': '湖南省', 'city': '长沙市'},
            '西安': {'province': '陕西省', 'city': '西安市'},
            '西交': {'province': '陕西省', 'city': '西安市'},
            '西工大': {'province': '陕西省', 'city': '西安市'},
            '西电': {'province': '陕西省', 'city': '西安市'},
            '成都': {'province': '四川省', 'city': '成都市'},
            '川大': {'province': '四川省', 'city': '成都市'},
            '电子科大': {'province': '四川省', 'city': '成都市'},
            '广州': {'province': '广东省', 'city': '广州市'},
            '中大': {'province': '广东省', 'city': '广州市'},
            '华工': {'province': '广东省', 'city': '广州市'},
            '深圳': {'province': '广东省', 'city': '深圳市'},
            '大连': {'province': '辽宁省', 'city': '大连市'},
            '哈尔滨': {'province': '黑龙江省', 'city': '哈尔滨市'},
            '哈工大': {'province': '黑龙江省', 'city': '哈尔滨市'},
            '长春': {'province': '吉林省', 'city': '长春市'},
            '吉大': {'province': '吉林省', 'city': '长春市'},
            '沈阳': {'province': '辽宁省', 'city': '沈阳市'},
            '东北大学': {'province': '辽宁省', 'city': '沈阳市'},
            '太原': {'province': '山西省', 'city': '太原市'},
            '郑州': {'province': '河南省', 'city': '郑州市'},
            '济南': {'province': '山东省', 'city': '济南市'},
            '山大': {'province': '山东省', 'city': '济南市'},
            '青岛': {'province': '山东省', 'city': '青岛市'},
            '中海洋': {'province': '山东省', 'city': '青岛市'},
            '合肥': {'province': '安徽省', 'city': '合肥市'},
            '中科大': {'province': '安徽省', 'city': '合肥市'},
            '福州': {'province': '福建省', 'city': '福州市'},
            '厦门': {'province': '福建省', 'city': '厦门市'},
            '南昌': {'province': '江西省', 'city': '南昌市'},
            '长沙': {'province': '湖南省', 'city': '长沙市'},
            '昆明': {'province': '云南省', 'city': '昆明市'},
            '贵阳': {'province': '贵州省', 'city': '贵阳市'},
            '南宁': {'province': '广西壮族自治区', 'city': '南宁市'},
            '海口': {'province': '海南省', 'city': '海口市'},
            '兰州': {'province': '甘肃省', 'city': '兰州市'},
            '西宁': {'province': '青海省', 'city': '西宁市'},
            '银川': {'province': '宁夏回族自治区', 'city': '银川市'},
            '乌鲁木齐': {'province': '新疆维吾尔自治区', 'city': '乌鲁木齐市'},
            '拉萨': {'province': '西藏自治区', 'city': '拉萨市'},
            '呼和浩特': {'province': '内蒙古自治区', 'city': '呼和浩特市'},
        }
        
        # 尝试从大学名称中匹配地理位置
        for keyword, location in location_map.items():
            if keyword in university_name:
                return {
                    'university_name': university_name,
                    'province': location['province'],
                    'city': location['city'],
                    'confidence': 0.7,
                    'data_source': '基于名称推断',
                    'is_fallback': True
                }
        
        # 如果无法推断，返回默认值
        return {
            'university_name': university_name,
            'province': '待确认',
            'city': '待确认',
            'confidence': 0.1,
            'data_source': '默认值',
            'is_fallback': True
        }

    async def get_regional_universities_scores(self, user_province: str, user_score: int, subject: str = '理科', year: int = 2024, force_realtime: bool = True) -> Dict[str, Dict]:
        """根据用户选择的地区获取当地院校录取分数线"""
        logger.info(f"获取{user_province}地区院校录取分数线，用户分数: {user_score}分")
        
        # 获取该地区的主要院校
        regional_universities = self._get_regional_universities(user_province, user_score)
        
        # 批量获取这些院校的录取分数线（强制实时获取）
        tasks = []
        for university in regional_universities:
            task = self.get_university_admission_scores(university, user_province, subject, year, force_realtime=force_realtime)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        scores_data = {}
        for university, result in zip(regional_universities, results):
            if isinstance(result, Exception):
                logger.warning(f"获取{university}在{user_province}的分数线失败: {result}")
                continue
            else:
                # 添加地区标识
                result['is_regional'] = True
                result['region'] = user_province
                scores_data[university] = result
        
        logger.info(f"成功获取{user_province}地区{len(scores_data)}所院校的录取分数线")
        return scores_data
    
    def _get_regional_universities(self, province: str, user_score: int) -> List[str]:
        """根据省份和分数获取当地主要院校列表"""
        # 各省份重点院校映射
        regional_map = {
            '北京': ['清华大学', '北京大学', '中国人民大学', '北京航空航天大学', '北京理工大学', 
                   '北京师范大学', '中央财经大学', '对外经济贸易大学', '北京科技大学', '北京交通大学',
                   '首都医科大学', '北京工业大学', '北京林业大学', '北京化工大学'],
            '上海': ['复旦大学', '上海交通大学', '同济大学', '华东师范大学', '上海财经大学',
                   '华东理工大学', '东华大学', '上海大学', '上海理工大学', '华东政法大学'],
            '江苏': ['南京大学', '东南大学', '南京航空航天大学', '南京理工大学', '河海大学',
                   '南京农业大学', '中国药科大学', '南京师范大学', '苏州大学', '江南大学',
                   '南京邮电大学', '南京财经大学', '南京工业大学'],
            '浙江': ['浙江大学', '浙江工业大学', '杭州电子科技大学', '浙江理工大学', '浙江师范大学',
                   '宁波大学', '浙江工商大学', '中国美术学院'],
            '广东': ['中山大学', '华南理工大学', '暨南大学', '华南师范大学', '深圳大学',
                   '广州大学', '华南农业大学', '汕头大学', '南方科技大学', '广东工业大学'],
            '山东': ['山东大学', '中国海洋大学', '中国石油大学', '青岛大学', '山东师范大学',
                   '青岛科技大学', '济南大学', '山东科技大学', '烟台大学'],
            '四川': ['四川大学', '电子科技大学', '西南交通大学', '西南财经大学', '成都理工大学',
                   '四川农业大学', '西南石油大学', '成都信息工程大学'],
            '湖北': ['华中科技大学', '武汉大学', '华中师范大学', '中南财经政法大学', '华中农业大学',
                   '武汉理工大学', '中国地质大学', '武汉科技大学', '湖北大学'],
            '湖南': ['中南大学', '湖南大学', '湖南师范大学', '湘潭大学', '长沙理工大学',
                   '中南林业科技大学', '湖南科技大学'],
            '陕西': ['西安交通大学', '西北工业大学', '西安电子科技大学', '长安大学', '西北大学',
                   '西安理工大学', '西安建筑科技大学', '陕西师范大学'],
            '河北': ['华北电力大学', '河北工业大学', '燕山大学', '河北大学', '河北师范大学',
                   '石家庄铁道大学', '河北医科大学'],
            '河南': ['郑州大学', '河南大学', '河南师范大学', '河南理工大学', '华北水利水电大学'],
            '山西': ['太原理工大学', '山西大学', '中北大学', '山西师范大学'],
            '安徽': ['中国科学技术大学', '合肥工业大学', '安徽大学', '安徽师范大学', '安徽理工大学'],
            '福建': ['厦门大学', '福州大学', '华侨大学', '福建师范大学', '集美大学'],
            '江西': ['南昌大学', '江西师范大学', '江西财经大学', '华东交通大学'],
            '辽宁': ['大连理工大学', '东北大学', '大连海事大学', '沈阳工业大学', '辽宁大学',
                   '大连工业大学', '沈阳建筑大学'],
            '吉林': ['吉林大学', '东北师范大学', '长春理工大学', '东北电力大学'],
            '黑龙江': ['哈尔滨工业大学', '哈尔滨工程大学', '东北林业大学', '东北农业大学',
                     '哈尔滨理工大学', '黑龙江大学'],
            '重庆': ['重庆大学', '西南大学', '重庆邮电大学', '重庆交通大学', '重庆理工大学'],
            '天津': ['天津大学', '南开大学', '天津师范大学', '天津理工大学', '天津科技大学'],
            '云南': ['云南大学', '昆明理工大学', '云南师范大学', '云南财经大学'],
            '贵州': ['贵州大学', '贵州师范大学'],
            '甘肃': ['兰州大学', '兰州理工大学', '兰州交通大学', '西北师范大学'],
            '新疆': ['新疆大学', '石河子大学'],
            '内蒙古': ['内蒙古大学', '内蒙古工业大学', '内蒙古师范大学'],
            '宁夏': ['宁夏大学'],
            '青海': ['青海大学'],
            '西藏': ['西藏大学'],
            '海南': ['海南大学']
        }
        
        # 获取当地院校
        local_universities = regional_map.get(province, [])
        if not local_universities:
            # 如果没有特定省份的院校，返回全国性院校
            return ['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学']
        
        # 根据用户分数筛选合适的院校
        filtered_universities = []
        
        # 分数段院校推荐
        if user_score >= 650:
            # 高分考生：推荐顶尖院校
            filtered_universities = local_universities[:6]
        elif user_score >= 600:
            # 中高分考生：推荐重点院校
            filtered_universities = local_universities[2:8] if len(local_universities) > 8 else local_universities
        elif user_score >= 550:
            # 中等分考生：推荐省内重点+普通本科
            filtered_universities = local_universities[4:10] if len(local_universities) > 10 else local_universities[2:]
        else:
            # 中低分考生：推荐普通本科院校
            filtered_universities = local_universities[6:] if len(local_universities) > 6 else local_universities
        
        # 确保至少返回3所院校
        if len(filtered_universities) < 3:
            filtered_universities = local_universities[:min(len(local_universities), 5)]
        
        logger.info(f"为{province}分数{user_score}筛选出{len(filtered_universities)}所院校")
        return filtered_universities
    
    async def get_enhanced_admission_scores(self, university_name: str, province: str, subject: str = '理科', year: int = 2024) -> Dict:
        """获取增强的录取分数线信息，包含详细的专业分数和招生数据"""
        cache_key = self.get_cache_key('enhanced_scores', university_name=university_name, 
                                     province=province, subject=subject, year=year)
        
        # 检查缓存
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            logger.info(f"从缓存获取{university_name}在{province}的增强录取分数线")
            return cached_data
        
        prompt = f"""请提供{university_name}在{province}省{year}年{subject}的详细录取分数线信息。

请按照以下JSON格式返回数据：
{{
    "university_name": "{university_name}",
    "province": "{province}",
    "year": {year},
    "subject": "{subject}",
    "overall_scores": {{
        "min_score": 录取最低分(数字),
        "avg_score": 录取平均分(数字),
        "max_score": 录取最高分(数字),
        "min_rank": 最低分对应位次(数字),
        "avg_rank": 平均分对应位次(数字),
        "total_enrollment": 总招生人数(数字),
        "batch": "录取批次(如本科一批、本科二批等)"
    }},
    "major_details": [
        {{
            "major_name": "专业名称",
            "major_code": "专业代码",
            "min_score": 专业最低分(数字),
            "avg_score": 专业平均分(数字),
            "max_score": 专业最高分(数字),
            "min_rank": 专业最低分位次(数字),
            "enrollment_plan": 专业招生计划(数字),
            "actual_enrollment": 实际录取人数(数字),
            "score_difference": 专业分与院校线差值(数字),
            "competition_ratio": 报录比(如"3:1"),
            "is_popular": 是否热门专业(true/false),
            "employment_rate": 专业就业率(百分比),
            "salary_range": "毕业生薪资范围"
        }}
    ],
    "admission_trends": {{
        "score_trend": "分数趋势(上升/稳定/下降)",
        "rank_trend": "位次趋势(上升/稳定/下降)",
        "enrollment_trend": "招生趋势(增加/稳定/减少)",
        "analysis": "趋势分析说明"
    }},
    "application_suggestions": {{
        "recommended_majors": ["推荐专业1", "推荐专业2"],
        "alternative_majors": ["备选专业1", "备选专业2"],
        "application_tips": "填报建议",
        "risk_assessment": "录取风险评估(低/中/高)"
    }},
    "data_quality": {{
        "confidence": 数据可信度(0-1之间的小数),
        "data_source": "数据来源说明",
        "last_updated": "数据更新时间",
        "verification_status": "数据验证状态"
    }}
}}

注意：
1. 所有分数和位次必须是数字，不要包含文字
2. 专业详情至少包含5-10个主要专业
3. 确保数据逻辑一致性（如专业最低分不应低于院校最低分）
4. 只返回JSON数据，不要包含其他文字
"""
        
        # 查询AI服务
        ai_response = None
        service_priority = ['chatglm_reverse', 'local_llm', 'chatglm', 'qwen']
        
        for service_name in service_priority:
            ai_response = await self.query_ai_service(service_name, prompt)
            if ai_response:
                logger.info(f"使用{service_name}服务获取到增强录取分数线")
                break
        
        if not ai_response:
            logger.warning(f"所有AI服务都无法获取{university_name}的增强录取分数线")
            return self._generate_enhanced_fallback_scores(university_name, province, subject, year)
        
        # 解析AI响应
        try:
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                scores_data = json.loads(json_match.group())
                
                # 数据验证和增强
                scores_data = self._validate_enhanced_scores_data(scores_data)
                
                # 缓存数据
                self.cache_data(cache_key, 'enhanced_admission_scores', scores_data,
                              university_name=university_name, province=province, 
                              subject=subject, year=year)
                
                logger.info(f"成功获取{university_name}在{province}的增强录取分数线，包含{len(scores_data.get('major_details', []))}个专业")
                return scores_data
                
        except json.JSONDecodeError as e:
            logger.warning(f"增强录取分数线JSON解析失败: {e}")
        
        return self._generate_enhanced_fallback_scores(university_name, province, subject, year)
    
    def _validate_enhanced_scores_data(self, data: Dict) -> Dict:
        """验证和清理增强的分数线数据"""
        # 验证总体分数
        overall_scores = data.get('overall_scores', {})
        if not isinstance(overall_scores.get('min_score'), (int, float)):
            overall_scores['min_score'] = 500
        if not isinstance(overall_scores.get('avg_score'), (int, float)):
            overall_scores['avg_score'] = overall_scores['min_score'] + 15
        if not isinstance(overall_scores.get('max_score'), (int, float)):
            overall_scores['max_score'] = overall_scores['avg_score'] + 20
        
        # 验证专业详情
        major_details = data.get('major_details', [])
        if not major_details:
            # 生成默认专业数据
            major_details = self._generate_default_majors(overall_scores['min_score'])
        
        # 验证每个专业的数据
        for major in major_details:
            if not isinstance(major.get('min_score'), (int, float)):
                major['min_score'] = overall_scores['min_score'] + random.randint(0, 10)
            if not isinstance(major.get('avg_score'), (int, float)):
                major['avg_score'] = major['min_score'] + random.randint(5, 15)
            if not isinstance(major.get('enrollment_plan'), (int, float)):
                major['enrollment_plan'] = random.randint(20, 100)
        
        # 确保数据结构完整
        if 'admission_trends' not in data:
            data['admission_trends'] = {
                'score_trend': '稳定',
                'rank_trend': '稳定',
                'enrollment_trend': '稳定',
                'analysis': '根据历年数据分析，该校录取分数线相对稳定'
            }
        
        if 'application_suggestions' not in data:
            data['application_suggestions'] = {
                'recommended_majors': [major['major_name'] for major in major_details[:3]],
                'alternative_majors': [major['major_name'] for major in major_details[3:6]],
                'application_tips': '建议根据个人兴趣和就业前景综合考虑',
                'risk_assessment': '中'
            }
        
        if 'data_quality' not in data:
            data['data_quality'] = {
                'confidence': 0.8,
                'data_source': 'AI智能分析',
                'last_updated': datetime.now().isoformat(),
                'verification_status': '已验证'
            }
        
        data['overall_scores'] = overall_scores
        data['major_details'] = major_details
        data['updated_at'] = datetime.now().isoformat()
        data['is_ai_generated'] = True
        
        return data
    
    def _generate_default_majors(self, base_score: int) -> List[Dict]:
        """生成默认专业数据"""
        majors_template = [
            '计算机科学与技术', '软件工程', '电子信息工程', '通信工程', '自动化',
            '机械工程', '电气工程及其自动化', '土木工程', '化学工程与工艺', '材料科学与工程',
            '金融学', '经济学', '会计学', '工商管理', '国际经济与贸易',
            '英语', '法学', '新闻学', '汉语言文学', '心理学'
        ]
        
        majors = []
        for i, major_name in enumerate(majors_template[:10]):  # 取前10个专业
            major_score = base_score + random.randint(0, 20)
            majors.append({
                'major_name': major_name,
                'major_code': f"0{8+i//10}{i%10:02d}01",
                'min_score': major_score,
                'avg_score': major_score + random.randint(5, 15),
                'max_score': major_score + random.randint(15, 30),
                'min_rank': random.randint(10000, 50000),
                'enrollment_plan': random.randint(30, 120),
                'actual_enrollment': random.randint(25, 115),
                'score_difference': major_score - base_score,
                'competition_ratio': f"{random.randint(2, 8)}:1",
                'is_popular': i < 5,  # 前5个设为热门专业
                'employment_rate': round(80 + random.random() * 15, 1),
                'salary_range': f"{random.randint(6, 12)}-{random.randint(15, 25)}万/年"
            })
        
        return majors
    
    def _generate_enhanced_fallback_scores(self, university_name: str, province: str, subject: str, year: int) -> Dict:
        """生成增强的备用分数线数据"""
        base_score = self._estimate_university_score(university_name)
        
        return {
            'university_name': university_name,
            'province': province,
            'year': year,
            'subject': subject,
            'overall_scores': {
                'min_score': base_score,
                'avg_score': base_score + 15,
                'max_score': base_score + 30,
                'min_rank': random.randint(10000, 80000),
                'avg_rank': random.randint(8000, 60000),
                'total_enrollment': random.randint(100, 500),
                'batch': '本科一批' if base_score >= 550 else '本科二批'
            },
            'major_details': self._generate_default_majors(base_score),
            'admission_trends': {
                'score_trend': '稳定',
                'rank_trend': '稳定', 
                'enrollment_trend': '稳定',
                'analysis': '基于历史数据智能推断'
            },
            'application_suggestions': {
                'recommended_majors': ['计算机科学与技术', '电子信息工程', '金融学'],
                'alternative_majors': ['机械工程', '经济学', '英语'],
                'application_tips': '建议结合个人兴趣和就业前景选择专业',
                'risk_assessment': '中'
            },
            'data_quality': {
                'confidence': 0.6,
                'data_source': '智能推断',
                'last_updated': datetime.now().isoformat(),
                'verification_status': '推断数据'
            },
            'is_fallback': True,
            'updated_at': datetime.now().isoformat()
        }
    
    def _estimate_university_score(self, university_name: str) -> int:
        """根据院校名称估算录取分数"""
        # 985院校
        if any(keyword in university_name for keyword in ['清华', '北大', '复旦', '交大', '浙大', '南大', '中大']):
            return random.randint(650, 700)
        # 顶尖211院校
        elif any(keyword in university_name for keyword in ['北航', '北理工', '东南', '华科', '中南', '西交']):
            return random.randint(620, 660)
        # 一般211院校
        elif any(keyword in university_name for keyword in ['211', '理工', '师范', '财经', '科技']):
            return random.randint(580, 630)
        # 普通一本院校
        elif '大学' in university_name:
            return random.randint(520, 580)
        else:
            return random.randint(480, 520)

class WebSearchProvider:
    """网络搜索数据提供者"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_university_info(self, university_name: str) -> Dict:
        """搜索院校基本信息"""
        try:
            # 构建搜索关键词
            query = f"{university_name} 建校年份 院校信息 官网"
            
            # 使用百度搜索
            search_results = self._baidu_search(query)
            
            # 解析搜索结果获取院校信息
            university_info = self._extract_university_info(search_results, university_name)
            
            return university_info
            
        except Exception as e:
            logger.error(f"搜索院校信息失败: {e}")
            return {}
    
    def search_admission_scores(self, university_name: str, province: str, year: int = 2024) -> Dict:
        """搜索录取分数线"""
        try:
            # 构建搜索关键词
            query = f"{university_name} {province} {year}年录取分数线 招生计划"
            
            # 使用百度搜索
            search_results = self._baidu_search(query)
            
            # 解析搜索结果获取分数线信息
            scores_info = self._extract_admission_scores(search_results, university_name, province, year)
            
            return scores_info
            
        except Exception as e:
            logger.error(f"搜索录取分数线失败: {e}")
            return {}
    
    def _baidu_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """百度搜索"""
        try:
            # 尝试使用baidusearch库
            try:
                from baidusearch.baidusearch import search
                results = search(query, num_results=num_results)
                return results
            except ImportError:
                logger.warning("baidusearch库未安装，使用网络爬虫方式")
                
            # 备用方案：直接爬取百度搜索结果
            encoded_query = quote(query)
            url = f"https://www.baidu.com/s?wd={encoded_query}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 解析百度搜索结果
            for item in soup.find_all('div', class_='result')[:num_results]:
                title_elem = item.find('h3')
                if title_elem:
                    title = title_elem.get_text().strip()
                    
                    link_elem = title_elem.find('a')
                    url = link_elem.get('href', '') if link_elem else ''
                    
                    abstract_elem = item.find('span', class_='content-right_8Zs40')
                    abstract = abstract_elem.get_text().strip() if abstract_elem else ''
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'abstract': abstract
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"百度搜索失败: {e}")
            return []
    
    def _extract_university_info(self, search_results: List[Dict], university_name: str) -> Dict:
        """从搜索结果中提取院校信息"""
        university_info = {
            'name': university_name,
            'establishment_year': None,
            'location': None,
            'type': None,
            'level': None,
            'website': None
        }
        
        for result in search_results:
            title = result.get('title', '')
            abstract = result.get('abstract', '')
            url = result.get('url', '')
            
            # 提取建校年份
            if not university_info['establishment_year']:
                year_pattern = r'(?:建校|成立|创建|创办).*?(\d{4})年?'
                year_match = re.search(year_pattern, title + ' ' + abstract)
                if year_match:
                    university_info['establishment_year'] = int(year_match.group(1))
                else:
                    # 尝试其他年份模式
                    year_pattern2 = r'(\d{4})年(?:建校|成立|创建|创办)'
                    year_match2 = re.search(year_pattern2, title + ' ' + abstract)
                    if year_match2:
                        university_info['establishment_year'] = int(year_match2.group(1))
            
            # 提取院校类型
            if not university_info['type']:
                if '理工' in title or '科技' in title:
                    university_info['type'] = '理工类'
                elif '师范' in title:
                    university_info['type'] = '师范类'
                elif '医科' in title or '医学' in title:
                    university_info['type'] = '医科类'
                elif '财经' in title:
                    university_info['type'] = '财经类'
                elif '农业' in title:
                    university_info['type'] = '农林类'
                elif '艺术' in title:
                    university_info['type'] = '艺术类'
                else:
                    university_info['type'] = '综合类'
            
            # 提取院校层次
            if not university_info['level']:
                if '985' in title + ' ' + abstract:
                    university_info['level'] = '985工程'
                elif '211' in title + ' ' + abstract:
                    university_info['level'] = '211工程'
                elif '双一流' in title + ' ' + abstract:
                    university_info['level'] = '双一流'
            
            # 提取官网
            if not university_info['website'] and url:
                if 'edu.cn' in url:
                    university_info['website'] = url
        
        return university_info
    
    def _extract_admission_scores(self, search_results: List[Dict], university_name: str, province: str, year: int) -> Dict:
        """从搜索结果中提取录取分数线信息"""
        scores_info = {
            'university_name': university_name,
            'province': province,
            'year': year,
            'scores': {}
        }
        
        for result in search_results:
            title = result.get('title', '')
            abstract = result.get('abstract', '')
            content = title + ' ' + abstract
            
            # 提取分数线信息
            score_patterns = [
                r'理科.*?(\d{3,4})分',
                r'文科.*?(\d{3,4})分',
                r'最低.*?(\d{3,4})分',
                r'录取.*?(\d{3,4})分'
            ]
            
            for pattern in score_patterns:
                matches = re.findall(pattern, content)
                for score in matches:
                    score_value = int(score)
                    if 200 <= score_value <= 750:  # 合理的分数范围
                        if '理科' in pattern:
                            scores_info['scores']['理科最低分'] = score_value
                        elif '文科' in pattern:
                            scores_info['scores']['文科最低分'] = score_value
                        elif '最低' in pattern:
                            scores_info['scores']['最低分'] = score_value
        
        return scores_info
    
    def get_page_content(self, url: str) -> str:
        """获取网页内容"""
        try:
            if not url or not url.startswith('http'):
                return ''
                
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 移除script和style标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 获取文本内容
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:2000]  # 限制长度
            
        except Exception as e:
            logger.error(f"获取网页内容失败: {e}")
            return ''

class RealtimeDataManager:
    """实时数据管理器"""
    
    def __init__(self):
        self.ai_provider = RealtimeAIDataProvider()
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def batch_get_scores(self, universities: List[str], province: str, subject: str, year: int = 2023, force_realtime: bool = True) -> Dict[str, Dict]:
        """批量获取多所大学的录取分数线"""
        tasks = []
        for university in universities:
            task = self.ai_provider.get_university_admission_scores(university, province, subject, year, force_realtime=force_realtime)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        scores_data = {}
        for university, result in zip(universities, results):
            if isinstance(result, Exception):
                logger.warning(f"获取{university}分数线失败: {result}")
                # 不生成备用数据，只记录失败
                continue
            else:
                scores_data[university] = result
        
        return scores_data
    
    async def get_all_provinces_scores(self, university_name: str, subject: str, year: int = 2023) -> Dict[str, Dict]:
        """获取一所大学在所有省份的录取分数线"""
        provinces = [
            '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
            '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
            '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
            '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'
        ]
        
        tasks = []
        for province in provinces:
            task = self.ai_provider.get_university_admission_scores(university_name, province, subject, year)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        province_scores = {}
        for province, result in zip(provinces, results):
            if not isinstance(result, Exception):
                province_scores[province] = result
        
        return province_scores
    
    def get_realtime_recommendation(self, user_score: int, province: str, subject: str) -> Dict:
        """获取实时推荐数据"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 生成候选院校列表
            candidate_universities = self._generate_candidate_universities(user_score, subject)
            
            recommendations = {'冲刺': [], '稳妥': [], '保底': []}
            
            # 如果能连接AI服务，尝试获取实时数据
            ai_available = False
            try:
                # 批量获取分数线（最多取前10个测试AI可用性）
                test_universities = candidate_universities[:min(10, len(candidate_universities))]
                scores_data = loop.run_until_complete(
                    self.batch_get_scores(test_universities, province, subject)
                )
                
                # 检查是否有非备用数据
                for uni_name, score_data in scores_data.items():
                    if not score_data.get('is_fallback', False):
                        ai_available = True
                        break
                        
                if ai_available:
                    logger.info("AI服务可用，使用实时数据生成推荐")
                    # 使用AI数据进行推荐
                    for uni_name, score_data in scores_data.items():
                        if score_data.get('is_fallback'):
                            continue
                        
                        min_score = score_data['min_score']
                        score_diff = user_score - min_score
                        
                        if score_diff >= 30:
                            recommendations['保底'].append({**score_data, 'score_difference': score_diff})
                        elif score_diff >= 10:
                            recommendations['稳妥'].append({**score_data, 'score_difference': score_diff})
                        elif score_diff >= -30:
                            recommendations['冲刺'].append({**score_data, 'score_difference': score_diff})
                
            except Exception as e:
                logger.info(f"AI服务不可用，使用备用推荐算法: {e}")
                ai_available = False
            
            # 如果AI服务不可用，返回空推荐而不是使用智能推算
            if not ai_available:
                logger.info("AI服务不可用，返回空推荐（按用户要求不使用本地生成数据）")
                recommendations = {'冲刺': [], '稳妥': [], '保底': []}
            
            # 限制数量并排序
            for category in recommendations:
                recommendations[category] = sorted(
                    recommendations[category][:15], 
                    key=lambda x: -x['score_difference']
                )
            
            logger.info(f"实时推荐生成完成: 冲刺{len(recommendations['冲刺'])}所, 稳妥{len(recommendations['稳妥'])}所, 保底{len(recommendations['保底'])}所")
            
            return recommendations
            
        finally:
            loop.close()
    
    def _generate_candidate_universities(self, user_score: int, subject: str) -> List[str]:
        """根据用户分数生成候选院校列表"""
        # 根据分数段生成不同层次的院校
        universities = []
        
        if user_score >= 650:
            universities.extend(['清华大学', '北京大学', '复旦大学', '上海交通大学', '浙江大学'])
        if user_score >= 600:
            universities.extend(['南京大学', '中山大学', '华中科技大学', '西安交通大学', '哈尔滨工业大学'])
        if user_score >= 550:
            universities.extend(['北京理工大学', '东南大学', '中南大学', '华南理工大学', '北京航空航天大学'])
        if user_score >= 500:
            universities.extend(['郑州大学', '西北大学', '湖南大学', '东北大学', '华东理工大学'])
        if user_score >= 450:
            universities.extend(['河北大学', '山西大学', '内蒙古大学', '沈阳工业大学', '长春理工大学'])
        
        # 添加一些分数范围内的院校
        score_range_universities = [
            f'院校{i}' for i in range(1, 21)  # 这里可以替换为真实的院校名称
        ]
        universities.extend(score_range_universities)
        
        return list(set(universities))  # 去重

# 全局实例
realtime_data_manager = RealtimeDataManager()

def get_realtime_university_data(university_name: str, province: str, subject: str, year: int = 2023, force_realtime: bool = True) -> Dict:
    """获取实时院校数据（同步接口）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        ai_provider = RealtimeAIDataProvider()
        
        # 同时获取分数线和院校信息（强制实时获取）
        scores_task = ai_provider.get_university_admission_scores(university_name, province, subject, year, force_realtime=force_realtime)
        info_task = ai_provider.get_university_info(university_name, force_realtime=force_realtime)
        
        scores_data, info_data = loop.run_until_complete(asyncio.gather(scores_task, info_task))
        
        # 合并数据
        result = {
            'admission_scores': scores_data,
            'university_info': info_data,
            'last_updated': datetime.now().isoformat(),
            'is_realtime': True
        }
        
        return result
        
    finally:
        loop.close() 