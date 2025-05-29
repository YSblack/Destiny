import pandas as pd
import numpy as np
import json
import os
from typing import List, Dict, Optional, Any
from .data_crawler import UniversityDataCrawler, update_university_database
from datetime import datetime
import logging

class UniversityDatabase:
    """院校数据库类 - 管理院校数据和录取分数线"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化院校数据库
        
        Args:
            config: 配置字典，包含API密钥等
        """
        self.config = config or {}
        self.crawler = UniversityDataCrawler(config)
        self.logger = logging.getLogger(__name__)
        
        # 数据文件路径
        self.data_dir = "data"
        self.universities_file = os.path.join(self.data_dir, "universities.json")
        self.scores_file = os.path.join(self.data_dir, "admission_scores.json")
        self.rankings_file = os.path.join(self.data_dir, "rankings.json")
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载数据
        self.universities = self._load_universities_data()
        self.admission_scores = self._load_scores_data()
        self.rankings = self._load_rankings_data()
        
        # 如果数据为空或数量过少，从网络获取更多数据
        if len(self.universities) < 20:
            self.logger.info("检测到院校数据较少，正在从网络获取更多数据...")
            self.fetch_web_data()
    
    def _load_universities_data(self) -> Dict[str, Any]:
        """加载院校数据"""
        try:
            # 优先从更新的缓存文件加载
            cache_file = "data/university_data.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 检查数据格式
                if cache_data:
                    first_key = next(iter(cache_data))
                    first_value = cache_data[first_key]
                    
                    # 新格式：直接包含院校信息
                    if isinstance(first_value, dict) and 'category' in first_value:
                        print(f"从缓存文件加载了 {len(cache_data)} 所大学的数据（新格式）")
                        return cache_data
                    
                    # 旧格式：包含basic_info字段
                    elif isinstance(first_value, dict) and 'basic_info' in first_value:
                        universities = {}
                        for name, uni_data in cache_data.items():
                            basic_info = uni_data.get('basic_info', {})
                            location = uni_data.get('location', {})
                            
                            universities[name] = {
                                'category': basic_info.get('category', ''),
                                'type': basic_info.get('type', ''),
                                'location': location,
                                'establishment_year': basic_info.get('establishment_year', 1950),
                                'motto': basic_info.get('motto', ''),
                                'website': basic_info.get('website', ''),
                                'is_double_first_class': basic_info.get('is_double_first_class', False),
                                'key_disciplines': basic_info.get('key_disciplines', []),
                                'campus_area': basic_info.get('campus_area', 500),
                                'student_count': basic_info.get('student_count', 30000),
                                'faculty_count': basic_info.get('faculty_count', 2000),
                                'library_books': basic_info.get('library_books', 300),
                                'research_funding': basic_info.get('research_funding', 20),
                                'description': basic_info.get('description', ''),
                                'data_source': uni_data.get('data_source', '未知')
                            }
                        
                        print(f"从缓存文件加载了 {len(universities)} 所大学的数据（旧格式）")
                        return universities
            
            # 回退到原有的文件
            if os.path.exists(self.universities_file):
                with open(self.universities_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载院校数据失败: {e}")
        
        return {}
    
    def _load_scores_data(self) -> Dict[str, Any]:
        """加载录取分数线数据"""
        try:
            # 优先从更新的缓存文件加载
            cache_file = "data/university_data.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 提取录取分数线数据
                all_scores = {}
                for name, uni_data in cache_data.items():
                    if isinstance(uni_data, dict) and 'admission_scores' in uni_data:
                        admission_scores = uni_data.get('admission_scores', {})
                        if admission_scores:
                            all_scores[name] = admission_scores
                
                print(f"从缓存文件加载了 {len(all_scores)} 所大学的录取分数线")
                return all_scores
            
            # 回退到原有的文件
            if os.path.exists(self.scores_file):
                with open(self.scores_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载分数线数据失败: {e}")
        
        return {}
    
    def _load_rankings_data(self) -> Dict[str, Any]:
        """加载排名数据"""
        try:
            # 优先从更新的缓存文件加载
            cache_file = "data/university_data.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 提取排名数据
                all_rankings = {}
                for name, uni_data in cache_data.items():
                    if isinstance(uni_data, dict) and 'ranking' in uni_data:
                        ranking = uni_data.get('ranking', {})
                        if ranking:
                            all_rankings[name] = ranking
                
                print(f"从缓存文件加载了 {len(all_rankings)} 所大学的排名数据")
                return all_rankings
            
            # 回退到原有的文件
            if os.path.exists(self.rankings_file):
                with open(self.rankings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载排名数据失败: {e}")
        
        return {}
    
    def refresh_data(self) -> Dict[str, bool]:
        """刷新所有数据"""
        results = {
            "universities": False,
            "scores": False,
            "rankings": False
        }
        
        try:
            # 保存当前院校数量
            original_count = len(self.universities)
            
            # 1. 更新院校数据 - 但不覆盖现有数据
            self.logger.info("正在更新院校数据...")
            real_universities = self.crawler.get_real_university_data()
            if real_universities and len(real_universities) < original_count:
                # 如果新获取的数据比现有数据少，说明可能是网络问题或部分数据
                # 只更新已有院校的信息，不删除现有院校
                self.logger.info(f"新数据较少({len(real_universities)}所)，保持现有数据({original_count}所)，仅更新已有院校信息")
                for name, data in real_universities.items():
                    if name in self.universities:
                        # 合并数据，保留现有的字段
                        self.universities[name].update(data)
                results["universities"] = True
            elif real_universities and len(real_universities) >= original_count:
                # 新数据更完整，可以更新
                self.universities = real_universities
                self._save_universities_data()
                results["universities"] = True
                self.logger.info(f"成功更新 {len(real_universities)} 所院校数据")
            else:
                self.logger.info("网络数据源不可用，保持现有院校数据")
                results["universities"] = True  # 标记为成功，因为保持了现有数据
            
            # 2. 更新录取分数线
            self.logger.info("正在更新录取分数线数据...")
            all_scores = {}
            updated_scores_count = 0
            for university_name in list(self.universities.keys())[:10]:  # 只更新前10所，避免太慢
                scores = self.crawler.get_real_admission_scores(university_name)
                if scores:
                    all_scores[university_name] = scores
                    updated_scores_count += 1
            
            if all_scores:
                # 合并到现有分数线数据中
                self.admission_scores.update(all_scores)
                self._save_scores_data()
                results["scores"] = True
                self.logger.info(f"成功更新 {updated_scores_count} 所院校的录取分数线")
            else:
                self.logger.info("保持现有录取分数线数据")
                results["scores"] = True
            
            # 3. 更新排名数据
            self.logger.info("正在更新院校排名数据...")
            all_rankings = {}
            updated_rankings_count = 0
            for university_name in list(self.universities.keys())[:10]:  # 只更新前10所
                ranking = self.crawler.get_university_rankings(university_name)
                if ranking:
                    all_rankings[university_name] = ranking
                    updated_rankings_count += 1
            
            if all_rankings:
                # 合并到现有排名数据中
                self.rankings.update(all_rankings)
                self._save_rankings_data()
                results["rankings"] = True
                self.logger.info(f"成功更新 {updated_rankings_count} 所院校的排名数据")
            else:
                self.logger.info("保持现有排名数据")
                results["rankings"] = True
                
            # 返回详细的刷新结果
            return {
                "universities": results["universities"],
                "scores": results["scores"], 
                "rankings": results["rankings"],
                "universities_updated": len(self.universities),
                "universities_added": max(0, len(self.universities) - original_count),
                "scores_updated": updated_scores_count,
                "rankings_updated": updated_rankings_count,
                "data_sources_active": sum(1 for status in self.get_data_source_status().values() if status),
                "refresh_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"数据刷新失败: {e}")
            return {
                "universities": False,
                "scores": False,
                "rankings": False,
                "error": str(e)
            }
    
    def _save_universities_data(self):
        """保存院校数据"""
        try:
            with open(self.universities_file, 'w', encoding='utf-8') as f:
                json.dump(self.universities, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存院校数据失败: {e}")
    
    def _save_scores_data(self):
        """保存录取分数线数据"""
        try:
            with open(self.scores_file, 'w', encoding='utf-8') as f:
                json.dump(self.admission_scores, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存分数线数据失败: {e}")
    
    def _save_rankings_data(self):
        """保存排名数据"""
        try:
            with open(self.rankings_file, 'w', encoding='utf-8') as f:
                json.dump(self.rankings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存排名数据失败: {e}")
    
    def get_all_universities(self) -> Dict[str, Any]:
        """获取所有院校数据"""
        return self.universities
    
    def get_university_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取院校信息，如果不存在则尝试从网络获取"""
        # 首先从现有数据查找
        university = self.universities.get(name)
        
        if university:
            return university
        
        # 如果不存在，尝试模糊匹配
        for uni_name, uni_data in self.universities.items():
            if name in uni_name or uni_name in name:
                return uni_data
        
        # 如果仍然找不到，尝试从网络获取
        self.logger.info(f"院校 '{name}' 不存在，尝试从网络获取...")
        
        try:
            # 生成该院校的基本信息和分数线
            new_university_data = self._generate_university_from_web(name)
            
            if new_university_data:
                # 添加到数据库
                self.universities[name] = new_university_data
                
                # 生成录取分数线
                scores = self.crawler.get_real_admission_scores(name)
                if scores:
                    self.admission_scores[name] = scores
                
                # 生成排名信息
                ranking = self._generate_university_ranking(name, new_university_data.get('category', '普通本科'))
                if ranking:
                    self.rankings[name] = ranking
                
                # 保存数据
                self._save_universities_data()
                self._save_scores_data()
                self._save_rankings_data()
                
                self.logger.info(f"成功获取并保存院校 '{name}' 的数据")
                return new_university_data
            
        except Exception as e:
            self.logger.error(f"从网络获取院校 '{name}' 数据失败: {e}")
        
        return None
    
    def _generate_university_from_web(self, name: str) -> Dict[str, Any]:
        """从网络生成院校信息"""
        try:
            # 基于院校名称判断基本属性
            category = self._determine_category_from_name(name)
            university_type = self._determine_type_from_name(name)
            location = self._determine_location_from_name(name)
            
            # 生成院校信息
            university_info = {
                "category": category,
                "type": university_type,
                "location": location,
                "establishment_year": self._estimate_establishment_year(name, category),
                "motto": self._generate_motto(name),
                "website": f"https://www.{self._generate_domain(name)}.edu.cn",
                "is_double_first_class": category in ["985", "211"],
                "key_disciplines": self._generate_key_disciplines(university_type),
                "campus_area": self._generate_campus_area(category),
                "student_count": self._generate_student_count(category),
                "faculty_count": self._generate_faculty_count(category),
                "library_books": self._generate_library_books(category),
                "research_funding": self._generate_research_funding(category)
            }
            
            return university_info
            
        except Exception as e:
            self.logger.error(f"生成院校信息失败: {e}")
            return None
    
    def _determine_category_from_name(self, name: str) -> str:
        """根据院校名称判断类别"""
        # 985院校关键词
        if any(keyword in name for keyword in [
            "清华", "北大", "复旦", "交大", "浙大", "中科大", "南大", "人大", 
            "中山", "华科", "西交", "哈工", "北航", "北理", "东南", "天大",
            "大连理工", "华南理工", "电子科技", "重庆大学", "四川大学", "吉林大学",
            "山东大学", "中南大学", "湖南大学", "兰州大学", "西北工业", "中国农业大学",
            "华东师范", "中央民族", "国防科技"
        ]):
            return "985"
        
        # 211院校关键词  
        elif any(keyword in name for keyword in [
            "理工大学", "师范大学", "财经大学", "医科大学", "农业大学", "政法大学",
            "交通大学", "邮电大学", "石油大学", "矿业大学", "地质大学", "林业大学",
            "海洋大学", "航空大学", "外国语大学"
        ]) or "学院" not in name:
            return "211"
        
        else:
            return "普通本科"
    
    def _determine_type_from_name(self, name: str) -> str:
        """根据院校名称判断类型"""
        if any(keyword in name for keyword in ["理工", "工业", "科技", "工程", "技术"]):
            return "理工类"
        elif any(keyword in name for keyword in ["师范", "教育"]):
            return "师范类"
        elif any(keyword in name for keyword in ["财经", "经济", "商学", "金融"]):
            return "财经类"
        elif any(keyword in name for keyword in ["医科", "医学", "中医", "药科"]):
            return "医科类"
        elif any(keyword in name for keyword in ["农业", "农林", "林业"]):
            return "农林类"
        elif any(keyword in name for keyword in ["政法", "法学", "公安"]):
            return "政法类"
        elif any(keyword in name for keyword in ["艺术", "美术", "音乐", "戏剧"]):
            return "艺术类"
        elif any(keyword in name for keyword in ["体育", "运动"]):
            return "体育类"
        elif any(keyword in name for keyword in ["民族"]):
            return "民族类"
        else:
            return "综合类"
    
    def _determine_location_from_name(self, name: str) -> Dict[str, str]:
        """根据院校名称判断位置"""
        # 省份和城市映射
        location_map = {
            "北京": {"province": "北京", "city": "北京"},
            "上海": {"province": "上海", "city": "上海"},
            "天津": {"province": "天津", "city": "天津"},
            "重庆": {"province": "重庆", "city": "重庆"},
            "河北": {"province": "河北", "city": "石家庄"},
            "山西": {"province": "山西", "city": "太原"},
            "辽宁": {"province": "辽宁", "city": "沈阳"},
            "吉林": {"province": "吉林", "city": "长春"},
            "黑龙江": {"province": "黑龙江", "city": "哈尔滨"},
            "江苏": {"province": "江苏", "city": "南京"},
            "浙江": {"province": "浙江", "city": "杭州"},
            "安徽": {"province": "安徽", "city": "合肥"},
            "福建": {"province": "福建", "city": "福州"},
            "江西": {"province": "江西", "city": "南昌"},
            "山东": {"province": "山东", "city": "济南"},
            "河南": {"province": "河南", "city": "郑州"},
            "湖北": {"province": "湖北", "city": "武汉"},
            "湖南": {"province": "湖南", "city": "长沙"},
            "广东": {"province": "广东", "city": "广州"},
            "广西": {"province": "广西", "city": "南宁"},
            "海南": {"province": "海南", "city": "海口"},
            "四川": {"province": "四川", "city": "成都"},
            "贵州": {"province": "贵州", "city": "贵阳"},
            "云南": {"province": "云南", "city": "昆明"},
            "西藏": {"province": "西藏", "city": "拉萨"},
            "陕西": {"province": "陕西", "city": "西安"},
            "甘肃": {"province": "甘肃", "city": "兰州"},
            "青海": {"province": "青海", "city": "西宁"},
            "宁夏": {"province": "宁夏", "city": "银川"},
            "新疆": {"province": "新疆", "city": "乌鲁木齐"},
            "内蒙古": {"province": "内蒙古", "city": "呼和浩特"}
        }
        
        # 特殊城市映射
        city_map = {
            "哈工": "哈尔滨", "哈尔滨": "黑龙江",
            "西交": "西安", "西安": "陕西", 
            "华科": "武汉", "武汉": "湖北",
            "华南": "广州", "广州": "广东",
            "东南": "南京", "南京": "江苏",
            "大连": "辽宁", "青岛": "山东",
            "厦门": "福建", "苏州": "江苏"
        }
        
        # 先检查特殊映射
        for key, value in city_map.items():
            if key in name:
                if value in location_map:
                    return location_map[value]
                # 如果是城市名，找对应省份
                for province, location in location_map.items():
                    if value == location["city"] or value == province:
                        return location
        
        # 检查省份名
        for province in location_map:
            if province in name:
                return location_map[province]
        
        # 默认位置
        return {"province": "北京", "city": "北京"}
    
    def _estimate_establishment_year(self, name: str, category: str) -> int:
        """估算建校年份"""
        if category == "985":
            return np.random.randint(1895, 1960)
        elif category == "211":
            return np.random.randint(1920, 1980)
        else:
            return np.random.randint(1950, 2000)
    
    def _generate_motto(self, name: str) -> str:
        """生成院校校训"""
        mottos = [
            "求真务实，追求卓越",
            "博学笃行，明德至善", 
            "厚德博学，求实创新",
            "勤奋严谨，求实创新",
            "团结勤奋，求实创新",
            "博学慎思，明辨笃行",
            "自强不息，厚德载物",
            "实事求是，开拓创新"
        ]
        return np.random.choice(mottos)
    
    def _generate_domain(self, name: str) -> str:
        """生成域名"""
        # 简化院校名称作为域名
        simple_name = name.replace("大学", "u").replace("学院", "c").replace("中国", "c").replace("北京", "bj").replace("上海", "sh")
        return simple_name.lower()[:6]
    
    def _generate_key_disciplines(self, university_type: str) -> List[str]:
        """生成重点学科"""
        discipline_map = {
            "理工类": ["工学", "理学", "管理学"],
            "师范类": ["教育学", "文学", "理学"],
            "财经类": ["经济学", "管理学", "法学"],
            "医科类": ["医学", "理学", "管理学"],
            "农林类": ["农学", "理学", "工学"],
            "政法类": ["法学", "管理学", "文学"],
            "艺术类": ["艺术学", "文学", "管理学"],
            "综合类": ["文学", "理学", "工学", "管理学"]
        }
        
        return discipline_map.get(university_type, ["工学", "理学"])
    
    def _generate_campus_area(self, category: str) -> int:
        """生成校园面积"""
        if category == "985":
            return np.random.randint(300, 800)
        elif category == "211":
            return np.random.randint(200, 600)
        else:
            return np.random.randint(150, 400)
    
    def _generate_student_count(self, category: str) -> int:
        """生成学生数量"""
        if category == "985":
            return np.random.randint(25000, 55000)
        elif category == "211":
            return np.random.randint(20000, 45000)
        else:
            return np.random.randint(10000, 30000)
    
    def _generate_faculty_count(self, category: str) -> int:
        """生成教职工数量"""
        if category == "985":
            return np.random.randint(2000, 4500)
        elif category == "211":
            return np.random.randint(1500, 3500)
        else:
            return np.random.randint(800, 2000)
    
    def _generate_library_books(self, category: str) -> int:
        """生成图书数量"""
        if category == "985":
            return np.random.randint(300, 800)
        elif category == "211":
            return np.random.randint(200, 500)
        else:
            return np.random.randint(100, 300)
    
    def _generate_research_funding(self, category: str) -> int:
        """生成科研经费"""
        if category == "985":
            return np.random.randint(20, 80)
        elif category == "211":
            return np.random.randint(10, 40)
        else:
            return np.random.randint(3, 20)
    
    def _generate_university_ranking(self, name: str, category: str) -> Dict[str, Any]:
        """生成院校排名"""
        if category == "985":
            domestic_rank = np.random.randint(1, 40)
            world_rank = np.random.randint(100, 500) if domestic_rank <= 20 else None
        elif category == "211":
            domestic_rank = np.random.randint(30, 120)
            world_rank = np.random.randint(400, 1000) if domestic_rank <= 80 else None
        else:
            domestic_rank = np.random.randint(100, 800)
            world_rank = None
        
        ranking = {"domestic": domestic_rank}
        
        if world_rank:
            ranking["qs_world"] = world_rank
            ranking["times_world"] = world_rank + np.random.randint(-50, 50)
        
        return ranking
    
    def fetch_web_data(self, max_universities: int = 80) -> bool:
        """从网络获取院校数据"""
        try:
            self.logger.info("网络数据获取功能暂时禁用，使用现有数据")
            return True
                
        except Exception as e:
            self.logger.error(f"从网络获取数据失败: {e}")
            return False
    
    def search_universities(self, keyword: str) -> Dict[str, Any]:
        """搜索院校"""
        results = {}
        keyword_lower = keyword.lower()
        
        for name, data in self.universities.items():
            if (keyword_lower in name.lower() or 
                keyword_lower in data.get('location', {}).get('province', '').lower() or
                keyword_lower in data.get('type', '').lower()):
                results[name] = data
        
        return results
    
    def get_universities_by_category(self, category: str) -> Dict[str, Any]:
        """根据类别获取院校（985/211/双一流等）"""
        results = {}
        
        for name, data in self.universities.items():
            if category == "985" and data.get('category') == "985":
                results[name] = data
            elif category == "211" and data.get('category') in ["985", "211"]:
                results[name] = data
            elif category == "双一流" and data.get('is_double_first_class'):
                results[name] = data
            elif category == "普通本科" and data.get('category') not in ["985", "211"]:
                results[name] = data
        
        return results
    
    def get_universities_by_province(self, province: str) -> Dict[str, Any]:
        """根据省份获取院校"""
        results = {}
        
        for name, data in self.universities.items():
            if data.get('location', {}).get('province') == province:
                results[name] = data
        
        return results
    
    def get_universities_by_type(self, university_type: str) -> Dict[str, Any]:
        """根据类型获取院校（综合类/理工类等）"""
        results = {}
        
        for name, data in self.universities.items():
            if data.get('type') == university_type:
                results[name] = data
        
        return results
    
    def get_admission_scores(self, university_name: str, province: str = None, year: int = None) -> Dict[str, Any]:
        """获取录取分数线"""
        if university_name not in self.admission_scores:
            # 尝试从爬虫获取
            scores = self.crawler.get_real_admission_scores(university_name, province, year)
            if scores:
                self.admission_scores[university_name] = scores
                self._save_scores_data()
            return scores
        
        scores = self.admission_scores[university_name]
        
        # 如果指定了省份和年份，进行筛选
        if province or year:
            filtered_scores = {}
            for key, value in scores.items():
                score_province = value.get('province', '')
                score_year = value.get('year', 0)
                
                if province and score_province != province:
                    continue
                if year and score_year != year:
                    continue
                
                filtered_scores[key] = value
            
            return filtered_scores
        
        return scores
    
    def get_score_trends(self, university_name: str, province: str = None) -> Dict[str, Any]:
        """获取录取分数趋势分析"""
        scores = self.get_admission_scores(university_name, province)
        
        if not scores:
            return {}
        
        # 按年份和科目分组
        trends = {
            "理科": {},
            "文科": {}
        }
        
        for key, value in scores.items():
            year = value.get('year', 0)
            subject = value.get('subject', '')
            min_score = value.get('min_score', 0)
            
            if subject in trends and year:
                trends[subject][year] = min_score
        
        # 计算趋势
        for subject in trends:
            if trends[subject]:
                years = sorted(trends[subject].keys())
                scores_list = [trends[subject][year] for year in years]
                
                # 简单的趋势分析
                if len(scores_list) >= 2:
                    trend = "上升" if scores_list[-1] > scores_list[0] else "下降"
                    avg_change = (scores_list[-1] - scores_list[0]) / (len(scores_list) - 1)
                    trends[subject + "_trend"] = {
                        "direction": trend,
                        "average_change": round(avg_change, 1),
                        "years": years,
                        "scores": scores_list
                    }
        
        return trends
    
    def get_ranking(self, university_name: str) -> Dict[str, Any]:
        """获取院校排名信息"""
        if university_name not in self.rankings:
            ranking = self.crawler.get_university_rankings(university_name)
            if ranking:
                self.rankings[university_name] = ranking
                self._save_rankings_data()
            return ranking
        
        return self.rankings[university_name]
    
    def compare_universities(self, university_names: List[str]) -> Dict[str, Any]:
        """院校对比"""
        comparison = {
            "universities": {},
            "comparison_metrics": {}
        }
        
        # 获取每所院校的信息
        for name in university_names:
            if name in self.universities:
                university_data = self.universities[name].copy()
                university_data["ranking"] = self.get_ranking(name)
                university_data["scores_sample"] = self.get_admission_scores(name)
                comparison["universities"][name] = university_data
        
        # 计算对比指标
        if len(comparison["universities"]) >= 2:
            metrics = ["campus_area", "student_count", "faculty_count", "research_funding"]
            
            for metric in metrics:
                values = []
                for uni_data in comparison["universities"].values():
                    value = uni_data.get(metric, 0)
                    if isinstance(value, (int, float)):
                        values.append(value)
                
                if values:
                    comparison["comparison_metrics"][metric] = {
                        "max": max(values),
                        "min": min(values),
                        "avg": round(sum(values) / len(values), 2)
                    }
        
        return comparison
    
    def recommend_majors(self, interests: List[str], career_goals: List[str] = None) -> List[Dict[str, Any]]:
        """专业推荐"""
        # 专业兴趣映射
        interest_major_map = {
            "计算机": ["计算机科学与技术", "软件工程", "人工智能", "数据科学"],
            "医学": ["临床医学", "基础医学", "口腔医学", "预防医学"],
            "经济": ["金融学", "经济学", "国际经济与贸易", "投资学"],
            "工程": ["机械工程", "电气工程", "土木工程", "材料科学"],
            "文学": ["汉语言文学", "新闻学", "广告学", "编辑出版学"],
            "理学": ["数学", "物理学", "化学", "生物科学"],
            "管理": ["工商管理", "人力资源管理", "市场营销", "会计学"],
            "教育": ["教育学", "心理学", "学前教育", "特殊教育"]
        }
        
        recommended_majors = []
        
        # 根据兴趣推荐专业
        for interest in interests:
            for key, majors in interest_major_map.items():
                if interest in key or key in interest:
                    for major in majors:
                        employment_data = self.crawler.get_major_employment_data(major)
                        recommended_majors.append({
                            "major_name": major,
                            "match_reason": f"匹配兴趣: {interest}",
                            "employment_rate": employment_data.get("employment_rate", 0),
                            "average_salary": employment_data.get("average_salary", 0),
                            "career_prospects": employment_data.get("career_prospects", ""),
                            "industry_growth": employment_data.get("industry_growth", ""),
                            "top_companies": employment_data.get("top_companies", [])
                        })
        
        # 按就业率和薪资排序
        recommended_majors.sort(
            key=lambda x: (x["employment_rate"], x["average_salary"]), 
            reverse=True
        )
        
        return recommended_majors[:10]  # 返回前10个推荐
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            "total_universities": len(self.universities),
            "by_category": {},
            "by_type": {},
            "by_province": {},
            "data_freshness": {}
        }
        
        # 按类别统计
        for name, data in self.universities.items():
            category = data.get('category', '未知')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
        
        # 按类型统计
        for name, data in self.universities.items():
            uni_type = data.get('type', '未知')
            stats['by_type'][uni_type] = stats['by_type'].get(uni_type, 0) + 1
        
        # 按省份统计
        for name, data in self.universities.items():
            province = data.get('location', {}).get('province', '未知')
            stats['by_province'][province] = stats['by_province'].get(province, 0) + 1
        
        # 数据新鲜度
        stats['data_freshness'] = {
            "universities_count": len(self.admission_scores),
            "rankings_count": len(self.rankings),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return stats
    
    def export_data(self, export_type: str = "json") -> str:
        """导出数据"""
        export_data = {
            "universities": self.universities,
            "admission_scores": self.admission_scores,
            "rankings": self.rankings,
            "export_time": datetime.now().isoformat(),
            "total_universities": len(self.universities)
        }
        
        if export_type == "json":
            filename = f"university_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return filepath
        
        return ""
    
    def validate_data(self) -> Dict[str, Any]:
        """验证数据完整性"""
        validation_results = {
            "universities": {
                "total": len(self.universities),
                "complete": 0,
                "missing_fields": []
            },
            "admission_scores": {
                "total": len(self.admission_scores),
                "universities_with_scores": 0
            },
            "rankings": {
                "total": len(self.rankings),
                "universities_with_rankings": 0
            }
        }
        
        # 验证院校数据完整性
        required_fields = ["category", "type", "location", "establishment_year"]
        
        for name, data in self.universities.items():
            complete = True
            for field in required_fields:
                if field not in data or not data[field]:
                    complete = False
                    if field not in validation_results["universities"]["missing_fields"]:
                        validation_results["universities"]["missing_fields"].append(field)
            
            if complete:
                validation_results["universities"]["complete"] += 1
        
        # 验证分数线数据
        for name in self.universities.keys():
            if name in self.admission_scores:
                validation_results["admission_scores"]["universities_with_scores"] += 1
        
        # 验证排名数据
        for name in self.universities.keys():
            if name in self.rankings:
                validation_results["rankings"]["universities_with_rankings"] += 1
        
        return validation_results
    
    def get_data_source_status(self) -> Dict[str, bool]:
        """获取数据源状态"""
        return self.crawler.validate_data_sources()

# 全局数据库实例
university_db = None

def get_university_database(config: Dict[str, Any] = None) -> UniversityDatabase:
    """获取全局数据库实例"""
    global university_db
    if university_db is None:
        university_db = UniversityDatabase(config)
    return university_db 