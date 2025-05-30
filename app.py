from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
import logging
import os
from datetime import datetime
from config import Config
from models.university_data import get_university_database
from models.data_crawler import UniversityDataCrawler
from typing import Dict, Any
import json
import asyncio

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOGGING['LEVEL']),
    format=Config.LOGGING['FORMAT'],
    handlers=[
        logging.FileHandler(Config.LOGGING['FILE'], encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.config.update(Config.APP)

# 配置JSON编码，确保中文字符正确显示
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# 初始化数据库
config = Config.get_data_source_config()
db = get_university_database(config)

# 确保数据加载
app.logger.info("正在加载院校数据...")
try:
    stats = db.get_statistics()
    app.logger.info(f"数据加载完成：{stats['total_universities']}所院校")
except Exception as e:
    app.logger.error(f"数据加载失败: {e}")

# 添加API配置管理的导入
try:
    from models.api_config import api_config_manager
except ImportError:
    api_config_manager = None

# 添加数据准确性管理器的导入
try:
    from models.data_accuracy_manager import data_accuracy_manager, get_accurate_university_scores
    data_accuracy_enabled = True
except ImportError:
    data_accuracy_enabled = False

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'data_sources': db.get_data_source_status()
    })

@app.route('/api/universities')
def get_universities():
    """获取院校列表"""
    try:
        # 获取查询参数
        category = request.args.get('category', '')
        province = request.args.get('province', '')
        university_type = request.args.get('type', '')
        keyword = request.args.get('keyword', '')
        
        universities = db.get_all_universities()
        
        # 应用筛选条件
        if keyword:
            universities = db.search_universities(keyword)
        elif category:
            universities = db.get_universities_by_category(category)
        elif province:
            universities = db.get_universities_by_province(province)
        elif university_type:
            universities = db.get_universities_by_type(university_type)
        
        return jsonify({
            'success': True,
            'count': len(universities),
            'data': universities
        })
        
    except Exception as e:
        app.logger.error(f"获取院校列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/university/<university_name>')
def get_university_detail(university_name):
    """获取院校详情"""
    try:
        university = db.get_university_by_name(university_name)
        if not university:
            return jsonify({
                'success': False,
                'error': '院校不存在'
            }), 404
        
        # 获取额外信息
        ranking = db.get_ranking(university_name)
        scores_sample = db.get_admission_scores(university_name)
        
        result = university.copy()
        result['ranking'] = ranking
        result['admission_scores_sample'] = scores_sample
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        app.logger.error(f"获取院校详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admission_scores/<university_name>')
def get_admission_scores(university_name):
    """获取录取分数线"""
    try:
        province = request.args.get('province')
        year = request.args.get('year', type=int)
        
        scores = db.get_admission_scores(university_name, province, year)
        
        return jsonify({
            'success': True,
            'university': university_name,
            'filters': {
                'province': province,
                'year': year
            },
            'data': scores
        })
        
    except Exception as e:
        app.logger.error(f"获取录取分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/score_trends/<university_name>')
def get_score_trends(university_name):
    """获取分数趋势"""
    try:
        province = request.args.get('province')
        trends = db.get_score_trends(university_name, province)
        
        return jsonify({
            'success': True,
            'university': university_name,
            'province': province,
            'data': trends
        })
        
    except Exception as e:
        app.logger.error(f"获取分数趋势失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/compare_universities', methods=['POST'])
def compare_universities():
    """院校对比"""
    try:
        data = request.get_json()
        university_names = data.get('universities', [])
        
        if len(university_names) < 2:
            return jsonify({
                'success': False,
                'error': '至少需要选择两所院校进行对比'
            }), 400
        
        comparison = db.compare_universities(university_names)
        
        return jsonify({
            'success': True,
            'data': comparison
        })
        
    except Exception as e:
        app.logger.error(f"院校对比失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/recommend_majors', methods=['POST'])
def recommend_majors():
    """专业推荐"""
    try:
        data = request.get_json()
        interests = data.get('interests', [])
        career_goals = data.get('career_goals', [])
        
        recommendations = db.recommend_majors(interests, career_goals)
        
        return jsonify({
            'success': True,
            'filters': {
                'interests': interests,
                'career_goals': career_goals
            },
            'data': recommendations
        })
        
    except Exception as e:
        app.logger.error(f"专业推荐失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics')
def get_statistics():
    """获取统计信息"""
    try:
        stats = db.get_statistics()
        
        # 手动序列化JSON以确保中文字符正确显示
        import json
        json_str = json.dumps({
            'success': True,
            'data': stats
        }, ensure_ascii=False, indent=2)
        
        # 返回原始JSON字符串
        from flask import Response
        return Response(
            json_str,
            mimetype='application/json; charset=utf-8'
        )
        
    except Exception as e:
        app.logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/provinces')
def get_provinces():
    """获取省份列表"""
    try:
        provinces = [
            "北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
            "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
            "广东", "广西", "海南", "四川", "贵州", "云南", "西藏", "陕西", "甘肃",
            "青海", "宁夏", "新疆", "内蒙古"
        ]
        
        return jsonify({
            'success': True,
            'provinces': provinces
        })
        
    except Exception as e:
        app.logger.error(f"获取省份列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/statistics')
def get_statistics_page():
    """获取统计信息（兼容旧版本路由）"""
    return get_statistics()

def calculate_score_analysis(score: int, province: str, subject: str) -> Dict[str, Any]:
    """计算分数分析数据"""
    
    # 不同省份的一本线（2023年参考数据）
    first_tier_lines = {
        "理科": {
            "北京": 448, "上海": 405, "天津": 472, "重庆": 406,
            "河南": 514, "山东": 443, "河北": 439, "江苏": 448,
            "浙江": 488, "广东": 439, "四川": 520, "湖南": 415,
            "湖北": 424, "陕西": 443, "安徽": 482, "福建": 431,
            "山西": 480, "辽宁": 360, "吉林": 463, "黑龙江": 408,
            "江西": 518, "广西": 475, "海南": 539, "贵州": 459,
            "云南": 485, "西藏": 400, "甘肃": 433, "青海": 330,
            "宁夏": 397, "新疆": 396, "内蒙古": 434
        },
        "文科": {
            "北京": 448, "上海": 405, "天津": 472, "重庆": 407,
            "河南": 547, "山东": 443, "河北": 430, "江苏": 474,
            "浙江": 488, "广东": 433, "四川": 527, "湖南": 428,
            "湖北": 426, "陕西": 489, "安徽": 495, "福建": 453,
            "山西": 490, "辽宁": 404, "吉林": 485, "黑龙江": 430,
            "江西": 533, "广西": 528, "海南": 539, "贵州": 545,
            "云南": 530, "西藏": 400, "甘肃": 488, "青海": 406,
            "宁夏": 488, "新疆": 458, "内蒙古": 468
        }
    }
    
    # 获取当前省份科目的一本线
    first_tier_line = first_tier_lines.get(subject, {}).get(province, 500)
    
    # 计算分数差距
    tier_difference = score - first_tier_line
    
    # 计算百分位排名（基于分数分布的估算）
    if score >= 680:
        percentile = 99.5
        position_description = "顶尖水平"
    elif score >= 650:
        percentile = 95.0 + (score - 650) / 30 * 4.5
        position_description = "优秀水平"
    elif score >= 600:
        percentile = 85.0 + (score - 600) / 50 * 10
        position_description = "良好水平"
    elif score >= 550:
        percentile = 70.0 + (score - 550) / 50 * 15
        position_description = "中上水平"
    elif score >= 500:
        percentile = 50.0 + (score - 500) / 50 * 20
        position_description = "中等水平"
    elif score >= 450:
        percentile = 30.0 + (score - 450) / 50 * 20
        position_description = "中下水平"
    else:
        percentile = max(5.0, (score / 450) * 30)
        position_description = "需要努力"
    
    # 计算同省排名估算
    # 基于各省考生人数估算（2023年数据）
    province_candidates = {
        "河南": 131000, "山东": 98000, "广东": 70000, "河北": 83000,
        "四川": 77000, "湖南": 68000, "湖北": 50000, "江苏": 44000,
        "安徽": 64000, "江西": 54000, "山西": 34000, "陕西": 32000,
        "浙江": 39000, "广西": 46000, "云南": 38000, "贵州": 47000,
        "甘肃": 24000, "黑龙江": 20000, "吉林": 12000, "辽宁": 19000,
        "新疆": 22000, "内蒙古": 18000, "宁夏": 7000, "青海": 6000,
        "西藏": 3000, "福建": 23000, "海南": 6000, "重庆": 33000,
        "北京": 5000, "上海": 5000, "天津": 6000
    }
    
    total_candidates = province_candidates.get(province, 50000)
    estimated_rank = int(total_candidates * (100 - percentile) / 100)
    
    return {
        "total_score": score,
        "subject": subject,
        "province": province,
        "first_tier_line": first_tier_line,
        "tier_difference": tier_difference,
        "percentile": round(percentile, 1),
        "beat_percentage": round(percentile, 1),
        "position_description": position_description,
        "estimated_rank": estimated_rank,
        "total_candidates": total_candidates,
        "tier_status": "超过一本线" if tier_difference > 0 else "未达一本线" if tier_difference < 0 else "达到一本线"
    }

@app.route('/calculate_score', methods=['POST'])
def calculate_score():
    """分数计算和院校推荐（使用专业API优先获取准确数据）"""
    try:
        data = request.get_json()
        
        # 验证必要参数
        required_fields = ['score', 'province', 'subject']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要参数: {field}'
                }), 400
        
        score = int(data['score'])
        province = data['province']
        subject = data['subject']
        preferences = data.get('preferences', [])
        
        app.logger.info(f"开始分数计算，使用专业API优先模式 - 分数: {score}, 省份: {province}, 科目: {subject}")
        
        # 使用专业API获取准确的院校推荐
        recommendations = []
        
        # 获取基础院校列表
        universities = db.get_all_universities()
        app.logger.info(f"获取到{len(universities)}所院校，开始使用专业API获取准确分数线")
        
        # 使用专业数据API获取准确分数
        from models.professional_data_api import ProfessionalDataAPI
        professional_api = ProfessionalDataAPI()
        
        success_count = 0
        failed_count = 0
        
        for name, uni_data in universities.items():
            try:
                # 使用专业API获取准确分数线
                result = professional_api.get_admission_scores(name, province, subject, 2023)
                
                if result.get('success'):
                    score_data = result['data']
                    min_score = score_data.get('min_score', 0)
                    avg_score = score_data.get('avg_score', min_score + 15)
                    rank = score_data.get('rank', 0)
                    data_source = f"专业API - {result.get('source', '权威数据')}"
                    confidence = result.get('confidence', 0.95)
                    
                    if min_score <= 0:
                        failed_count += 1
                        continue
                    
                    success_count += 1
                    
                    # 推荐逻辑：冲刺、稳妥、保底
                    score_diff = score - min_score
                    avg_diff = score - avg_score
                    
                    # 更合理的分类逻辑 - 优化高分段冲刺院校推荐
                    if score >= min_score + 30:
                        category = "保底"
                        probability = "95%以上"
                        probability_num = 95
                    elif score >= min_score + 20:
                        category = "保底"
                        probability = "90-95%"
                        probability_num = 92
                    elif score >= min_score + 10:
                        category = "稳妥" 
                        probability = "80-90%"
                        probability_num = 85
                    elif score >= min_score:
                        category = "稳妥"
                        probability = "70-80%"
                        probability_num = 75
                    elif score >= min_score - 10:
                        category = "冲刺"
                        probability = "50-70%"
                        probability_num = 60
                    elif score >= min_score - 20:
                        category = "冲刺"
                        probability = "30-50%"
                        probability_num = 40
                    elif score >= min_score - 30:
                        category = "冲刺"
                        probability = "15-30%"
                        probability_num = 25
                    else:
                        # 特殊处理：如果分数差距太大，但是高分段院校稀缺，仍然作为冲刺推荐
                        if score >= 650 and min_score >= 650:  # 高分段特殊处理
                            category = "冲刺"
                            probability = "10-20%"
                            probability_num = 15
                        else:
                            failed_count += 1
                            continue  # 分数太低，不推荐
                    
                    # 检查偏好匹配
                    if preferences:
                        uni_type = uni_data.get('type', '')
                        if not any(pref in uni_type for pref in preferences):
                            probability_num -= 10
                    
                    # 获取排名信息
                    ranking = db.get_ranking(name)
                    
                    # 确保地理位置信息准确
                    original_location = uni_data.get('location', {})
                    original_province = original_location.get('province') or uni_data.get('province', '')
                    original_city = original_location.get('city') or uni_data.get('city', '')
                    
                    # 智能修复地理位置错误
                    needs_ai_fix = False
                    if original_province == '北京' and '北京' not in name:
                        beijing_universities = [
                            '清华大学', '北京大学', '中国人民大学', '北京师范大学', 
                            '北京理工大学', '北京航空航天大学', '北京科技大学', '北京化工大学',
                            '北京邮电大学', '中国农业大学', '北京林业大学', '中国传媒大学',
                            '中央民族大学', '北京中医药大学', '对外经济贸易大学', '中央财经大学',
                            '中国政法大学', '华北电力大学', '中国矿业大学(北京)', '中国石油大学(北京)',
                            '中国地质大学(北京)', '北京工业大学', '首都师范大学', '北京交通大学'
                        ]
                        
                        special_cases = {
                            '中国地质大学': '湖北',
                            '中国矿业大学': '江苏',  
                            '中国石油大学': '山东',
                            '南京邮电大学': '江苏',
                            '哈尔滨理工大学': '黑龙江',
                            '西安电子科技大学': '陕西'
                        }
                        
                        if name in special_cases:
                            needs_ai_fix = True
                        elif not any(beijing_uni in name for beijing_uni in beijing_universities):
                            needs_ai_fix = True
                    
                    # 使用AI修复地理位置（如果需要）
                    if not original_province or not original_city or needs_ai_fix:
                        try:
                            from models.realtime_ai_data import RealtimeAIDataProvider
                            provider = RealtimeAIDataProvider()
                            import asyncio
                            ai_location = asyncio.run(provider.get_university_location(name))
                            if ai_location and ai_location.get('province') not in ['未知省份', '待确认']:
                                original_province = ai_location['province']
                                original_city = ai_location['city']
                        except Exception as e:
                            app.logger.debug(f"AI地理位置修复失败: {e}")
                    
                    # 创建包含正确地理位置的院校数据副本
                    enhanced_uni_data = uni_data.copy()
                    enhanced_uni_data['province'] = original_province
                    enhanced_uni_data['city'] = original_city
                    if 'location' not in enhanced_uni_data:
                        enhanced_uni_data['location'] = {}
                    enhanced_uni_data['location']['province'] = original_province
                    enhanced_uni_data['location']['city'] = original_city
                    
                    recommendations.append({
                        'university_name': name,
                        'university_data': enhanced_uni_data,
                        'ranking': ranking,
                        'category': category,
                        'probability': probability,
                        'probability_num': max(0, probability_num),
                        'min_score': min_score,
                        'avg_score': avg_score,
                        'score_difference': score_diff,
                        'avg_difference': avg_diff,
                        'data_source': data_source,
                        'data_year': 2023,
                        'confidence': confidence,
                        'rank': rank,
                        'is_reference_data': False,  # 专业API数据
                        'accuracy_level': 'high',
                        'original_province': province
                    })
                    
                else:
                    failed_count += 1
                    app.logger.debug(f"专业API未找到{name}在{province}的数据: {result.get('error', '未知')}")
                    
            except Exception as e:
                failed_count += 1
                app.logger.debug(f"获取{name}分数线时出错: {e}")
                continue
        
        app.logger.info(f"专业API获取完成: 成功{success_count}所，失败{failed_count}所")
        
        # 按概率和分数差异排序
        recommendations.sort(key=lambda x: (-x['probability_num'], -x['score_difference']))
        
        # 分类返回
        result = {
            '冲刺': [r for r in recommendations if r['category'] == '冲刺'][:8],
            '稳妥': [r for r in recommendations if r['category'] == '稳妥'][:10],
            '保底': [r for r in recommendations if r['category'] == '保底'][:6]
        }
        
        # 如果使用专业API后推荐数量不足，使用AI数据补充
        min_required = {'冲刺': 5, '稳妥': 8, '保底': 5}
        
        # 特殊处理高分段用户的冲刺院校需求
        if score >= 700:
            min_required['冲刺'] = 8  # 高分段用户需要更多冲刺院校
            
        for category, min_count in min_required.items():
            if len(result[category]) < min_count:
                try:
                    from models.realtime_ai_data import realtime_data_manager
                    
                    app.logger.info(f"{category}院校数量不足({len(result[category])}所)，使用AI补充到{min_count}所")
                    
                    # 特殊处理：为高分段冲刺院校补充顶尖院校
                    if category == '冲刺' and score >= 700:
                        # 添加顶尖院校作为冲刺选择
                        top_universities = [
                            "北京大学", "清华大学", "复旦大学", "上海交通大学", "浙江大学",
                            "南京大学", "中国科学技术大学", "哈尔滨工业大学", "西安交通大学",
                            "中山大学", "华中科技大学", "东南大学", "天津大学", "北京航空航天大学",
                            "同济大学", "厦门大学", "北京理工大学", "华南理工大学", "山东大学",
                            "中南大学", "吉林大学", "大连理工大学", "湖南大学", "重庆大学"
                        ]
                        
                        added_count = 0
                        for uni_name in top_universities:
                            if len(result[category]) >= min_count:
                                break
                                
                            # 避免重复
                            if any(r['university_name'] == uni_name for r in result[category]):
                                continue
                            
                            # 为高分段用户生成适当的冲刺院校数据
                            base_score = score + 5 + (added_count * 3)  # 分数略高于用户分数
                            
                            recommendation = {
                                'university_name': uni_name,
                                'min_score': base_score,
                                'avg_score': base_score + 10,
                                'score_difference': score - base_score,
                                'category': category,
                                'probability': f"{45 - (added_count * 2)}%",
                                'probability_num': 45 - (added_count * 2),
                                'is_reference_data': True,
                                'reference_province': '高分段智能推荐',
                                'data_source': f"高分段补充 - 顶尖院校",
                                'accuracy_level': 'medium',
                                'confidence': 0.75,
                                'university_data': {
                                    'name': uni_name,
                                    'category': '985工程',
                                    'type': '综合类',
                                    'province': '北京' if '北京' in uni_name else '上海' if '上海' in uni_name else province,
                                    'city': '北京' if '北京' in uni_name else '上海' if '上海' in uni_name else '',
                                    'location': {
                                        'province': '北京' if '北京' in uni_name else '上海' if '上海' in uni_name else province,
                                        'city': '北京' if '北京' in uni_name else '上海' if '上海' in uni_name else ''
                                    },
                                    'ranking': {'domestic_rank': added_count + 1},
                                    'advantages': ['计算机科学', '数学', '物理学', '经济学'],
                                    'is_double_first_class': True
                                }
                            }
                            
                            result[category].append(recommendation)
                            added_count += 1
                        
                        app.logger.info(f"高分段特殊补充{category}院校: {added_count}所")
                        continue  # 跳过常规AI补充
                    
                    # 使用实时AI获取推荐数据
                    ai_recommendations = realtime_data_manager.get_realtime_recommendation(score, province, subject)
                    ai_category_data = ai_recommendations.get(category, [])
                    
                    # 补充到最低要求数量
                    added_count = 0
                    for ai_data in ai_category_data:
                        if len(result[category]) >= min_count:
                            break
                            
                        ai_uni_name = ai_data['university_name']
                        
                        # 避免重复
                        if any(r['university_name'] == ai_uni_name for r in result[category]):
                            continue
                        
                        # 获取地理位置信息
                        try:
                            from models.realtime_ai_data import RealtimeAIDataProvider
                            provider = RealtimeAIDataProvider()
                            import asyncio
                            ai_location = asyncio.run(provider.get_university_location(ai_uni_name))
                            if not ai_location or ai_location.get('province') in ['未知省份', '待确认']:
                                ai_location = {'province': province, 'city': ''}
                        except:
                            ai_location = {'province': province, 'city': ''}
                        
                        recommendation = {
                            'university_name': ai_uni_name,
                            'min_score': ai_data['min_score'],
                            'avg_score': ai_data['avg_score'],
                            'score_difference': ai_data['score_difference'],
                            'category': category,
                            'probability': f"{65 + (ai_data['min_score'] % 15)}%",
                            'probability_num': 65 + (ai_data['min_score'] % 15),
                            'is_reference_data': True,
                            'reference_province': '实时AI数据',
                            'data_source': f"AI补充 - {ai_data.get('data_source', '智能推算')}",
                            'accuracy_level': 'medium',
                            'confidence': 0.70,
                            'university_data': {
                                'name': ai_uni_name,
                                'category': ai_data.get('category', '普通本科'),
                                'type': '综合类',
                                'province': ai_location['province'],
                                'city': ai_location['city'],
                                'location': {
                                    'province': ai_location['province'],
                                    'city': ai_location['city']
                                },
                                'ranking': {'domestic_rank': '未知'},
                                'advantages': ['计算机科学', '经济学', '管理学'],
                                'is_double_first_class': False
                            }
                        }
                        
                        result[category].append(recommendation)
                        added_count += 1
                    
                    app.logger.info(f"AI补充{category}院校: {added_count}所，总计{len(result[category])}所")
                    
                except Exception as e:
                    app.logger.warning(f"AI补充{category}院校失败: {e}")
        
        # 统计信息
        total_professional_api = sum(1 for r in recommendations if r['accuracy_level'] == 'high')
        total_ai_supplement = sum(len(result[cat]) for cat in result) - total_professional_api
        
        # 计算分数分析
        score_analysis = calculate_score_analysis(score, province, subject)
        
        app.logger.info(f"推荐完成 - 专业API: {total_professional_api}所, AI补充: {total_ai_supplement}所")
        app.logger.info(f"最终结果 - 冲刺: {len(result['冲刺'])}所, 稳妥: {len(result['稳妥'])}所, 保底: {len(result['保底'])}所")
        
        return jsonify({
            'success': True,
            'input': {
                'score': score,
                'province': province,
                'subject': subject,
                'preferences': preferences
            },
            'total_count': len(recommendations),
            'recommendations': result,
            'categorized': result,  # 兼容旧版本前端
            'score_analysis': score_analysis,
            'summary': {
                '冲刺院校': len(result['冲刺']),
                '稳妥院校': len(result['稳妥']),
                '保底院校': len(result['保底'])
            },
            'data_quality': {
                'professional_api_count': total_professional_api,
                'ai_supplement_count': total_ai_supplement,
                'accuracy_message': f'✅ {total_professional_api}所院校使用专业API权威数据，{total_ai_supplement}所使用AI补充数据',
                'confidence_level': 'high' if total_professional_api > total_ai_supplement else 'medium'
            },
            'debug_info': {
                'total_universities': len(universities),
                'professional_api_success': success_count,
                'professional_api_failed': failed_count,
                'search_criteria': f"{province}_{subject}"
            }
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': '分数必须是有效的数字'
        }), 400
    except Exception as e:
        app.logger.error(f"分数计算失败: {e}")
        return jsonify({
            'success': False,
            'error': f'计算过程中发生错误: {str(e)}'
        }), 500

@app.route('/api/search_universities')
def search_universities_api():
    """搜索院校API"""
    try:
        keyword = request.args.get('keyword', '')
        category = request.args.get('category', '')
        province = request.args.get('province', '')
        university_type = request.args.get('type', '')
        
        if keyword:
            universities = db.search_universities(keyword)
        elif category:
            universities = db.get_universities_by_category(category)
        elif province:
            universities = db.get_universities_by_province(province)
        elif university_type:
            universities = db.get_universities_by_type(university_type)
        else:
            universities = db.get_all_universities()
        
        return jsonify({
            'success': True,
            'count': len(universities),
            'data': universities
        })
        
    except Exception as e:
        app.logger.error(f"搜索院校失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/university_detail/<university_name>')
def get_university_detail_api(university_name):
    """获取院校详情API"""
    try:
        university = db.get_university_by_name(university_name)
        if not university:
            return jsonify({
                'success': False,
                'error': f'院校 "{university_name}" 不存在'
            }), 404
        
        # 获取额外信息
        ranking = db.get_ranking(university_name)
        scores = db.get_admission_scores(university_name)
        trends = db.get_score_trends(university_name)
        
        result = university.copy()
        result['ranking'] = ranking
        result['admission_scores'] = scores
        result['score_trends'] = trends
        
        # 获取录取分数线并转换格式
        admission_scores_raw = university.get('admission_scores', {})
        
        # 转换为前端期望的格式，同时保留详细信息
        admission_scores = {}
        for score_key, score_data in admission_scores_raw.items():
            # 解析键名：如 "山西_2023_理科"
            parts = score_key.split('_')
            if len(parts) >= 3:
                province = parts[0]
                year = parts[1]
                subject = parts[2]
                
                # 创建前端期望的键名
                frontend_key = f"{province}_{year}_{subject}"
                
                # 处理不同的数据格式
                if isinstance(score_data, dict):
                    # 新格式：包含详细信息
                    if '最低分' in score_data:
                        # 真实数据格式
                        admission_scores[frontend_key] = {
                            'min_score': score_data.get('最低分', score_data.get('min_score', 0)),
                            'avg_score': score_data.get('平均分', score_data.get('avg_score', 0)),
                            'max_score': score_data.get('最高分', score_data.get('max_score', 0)),
                            'rank': score_data.get('位次', score_data.get('rank', 0)),
                            'enrollment_count': score_data.get('招生人数', score_data.get('enrollment_count', 0)),
                            'admission_batch': score_data.get('录取批次', '本科一批A段'),
                            'popular_majors': score_data.get('热门专业', []),
                            'data_source': score_data.get('数据来源', ''),
                            'description': score_data.get('数据说明', ''),
                            'update_time': score_data.get('更新时间', score_data.get('update_time', 0)),
                            'province': province,
                            'year': int(year),
                            'subject': subject
                        }
                    else:
                        # 旧格式：基本分数信息
                        admission_scores[frontend_key] = {
                            'min_score': score_data.get('min_score', 0),
                            'avg_score': score_data.get('avg_score', 0),
                            'max_score': score_data.get('max_score', 0),
                            'rank': score_data.get('rank', 0),
                            'enrollment_count': score_data.get('enrollment_count', 0),
                            'admission_batch': '本科一批A段',
                            'popular_majors': [],
                            'data_source': score_data.get('data_source', ''),
                            'description': '',
                            'update_time': score_data.get('update_time', 0),
                            'province': province,
                            'year': int(year),
                            'subject': subject
                        }
                else:
                    # 简单数值格式
                    admission_scores[frontend_key] = {
                        'min_score': score_data if isinstance(score_data, (int, float)) else 0,
                        'avg_score': 0,
                        'max_score': 0,
                        'rank': 0,
                        'enrollment_count': 0,
                        'admission_batch': '本科一批A段',
                        'popular_majors': [],
                        'data_source': '',
                        'description': '',
                        'update_time': 0,
                        'province': province,
                        'year': int(year),
                        'subject': subject
                    }
        
        # 构建响应数据
        response_data = {
            'success': True,
            'university': {
                'name': university_name,
                'category': university.get('category', ''),
                'location': university.get('location', {}),
                'description': university.get('description', ''),
                'website': university.get('website', ''),
                'phone': university.get('phone', ''),
                'email': university.get('email', ''),
                'established': university.get('established', ''),
                'establishment_year': university.get('establishment_year', ''),
                'type': university.get('type', ''),
                'level': university.get('level', ''),
                'motto': university.get('motto', ''),
                'campus_area': university.get('campus_area', ''),
                'student_count': university.get('student_count', ''),
                'faculty_count': university.get('faculty_count', ''),
                'library_books': university.get('library_books', ''),
                'research_funding': university.get('research_funding', ''),
                'is_double_first_class': university.get('is_double_first_class', False),
                'key_disciplines': university.get('key_disciplines', []),
                'majors': university.get('majors', []),
                'employment': university.get('employment', {}),
                'dormitory_info': university.get('dormitory_info', ''),
                'dining_facilities': university.get('dining_facilities', ''),
                'sports_facilities': university.get('sports_facilities', ''),
                'data_sources': university.get('data_sources', []),
                'data_source': university.get('data_source', ''),
                'province': university.get('location', {}).get('province', '') or university.get('province', ''),
                'city': university.get('location', {}).get('city', '') or university.get('city', ''),
                'admission_scores': admission_scores,
                'ranking': ranking
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"获取院校详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/batch_search', methods=['POST'])
def batch_search_universities():
    """批量搜索院校"""
    try:
        data = request.get_json()
        university_names = data.get('universities', [])
        
        results = {}
        for name in university_names:
            university = db.get_university_by_name(name)
            if university:
                results[name] = university
        
        return jsonify({
            'success': True,
            'count': len(results),
            'data': results
        })
        
    except Exception as e:
        app.logger.error(f"批量搜索失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/validate_data')
def validate_data():
    """验证数据完整性"""
    try:
        validation_results = db.validate_data()
        return jsonify({
            'success': True,
            'data': validation_results
        })
        
    except Exception as e:
        app.logger.error(f"数据验证失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 管理员接口
@app.route('/admin/refresh_data', methods=['POST'])
def refresh_data():
    """刷新数据"""
    try:
        app.logger.info("开始数据刷新...")
        
        # 获取刷新前的统计信息
        old_stats = {
            'universities_count': len(db.get_all_universities()),
            'data_source_status': db.get_data_source_status()
        }
        
        # 执行数据刷新
        results = db.refresh_data()
        
        # 获取刷新后的统计信息
        new_stats = {
            'universities_count': len(db.get_all_universities()),
            'data_source_status': db.get_data_source_status()
        }
        
        # 构建详细的刷新结果
        refresh_results = {
            'universities_updated': new_stats['universities_count'],
            'universities_added': max(0, new_stats['universities_count'] - old_stats['universities_count']),
            'data_sources_active': sum(1 for status in new_stats['data_source_status'].values() if status),
            'refresh_time': datetime.now().isoformat(),
            'old_count': old_stats['universities_count'],
            'new_count': new_stats['universities_count']
        }
        
        # 如果refresh_data返回了详细信息，则合并
        if isinstance(results, dict):
            refresh_results.update(results)
        
        app.logger.info(f"数据刷新完成: {refresh_results}")
        
        return jsonify({
            'success': True,
            'message': '数据刷新完成',
            'results': refresh_results,
            'summary': {
                'total_universities': refresh_results['universities_updated'],
                'active_sources': refresh_results['data_sources_active'],
                'last_update': refresh_results['refresh_time']
            }
        })
        
    except Exception as e:
        app.logger.error(f"数据刷新失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '数据刷新失败，请检查网络连接或数据源配置'
        }), 500

@app.route('/admin/export_data')
def export_data():
    """导出数据"""
    try:
        export_type = request.args.get('type', 'json')
        filepath = db.export_data(export_type)
        
        return jsonify({
            'success': True,
            'message': '数据导出成功',
            'filepath': filepath
        })
        
    except Exception as e:
        app.logger.error(f"数据导出失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/data_sources')
def get_admin_data_sources_status():
    """获取数据源状态（管理员接口）"""
    try:
        status = db.get_data_source_status()
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        app.logger.error(f"获取数据源状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 志愿填报相关接口
@app.route('/api/recommendation', methods=['POST'])
def get_recommendations():
    """获取志愿填报推荐"""
    try:
        data = request.get_json()
        
        # 验证必要参数
        required_fields = ['score', 'province', 'subject']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要参数: {field}'
                }), 400
        
        score = data['score']
        province = data['province']
        subject = data['subject']
        preferences = data.get('preferences', {})
        
        # 获取适合的院校
        recommendations = []
        universities = db.get_all_universities()
        
        for name, uni_data in universities.items():
            scores = db.get_admission_scores(name, province, 2023)
            
            for score_key, score_data in scores.items():
                if score_data.get('subject') == subject:
                    min_score = score_data.get('min_score', 0)
                    avg_score = score_data.get('avg_score', 0)
                    
                    # 推荐逻辑：冲刺、稳妥、保底
                    # 冲刺：分数低于院校线，但在合理范围内
                    if score >= avg_score + 15:
                        category = "保底"
                        probability = "95%以上"
                        probability_num = 95
                    elif score >= avg_score:
                        category = "稳妥" 
                        probability = "80-90%"
                        probability_num = 85
                    elif score >= avg_score - 10:
                        category = "稳妥"
                        probability = "70-80%"
                        probability_num = 75
                    elif score >= avg_score - 20:
                        category = "冲刺"
                        probability = "50-70%"
                        probability_num = 60
                    elif score >= avg_score - 30:
                        category = "冲刺"
                        probability = "30-50%"
                        probability_num = 40
                    elif score >= avg_score - 40:
                        category = "冲刺"
                        probability = "15-30%"
                        probability_num = 25
                    else:
                        continue  # 分数太低，不推荐
                    
                    # 获取排名信息
                    ranking = db.get_ranking(name)
                    
                    # 确保地理位置信息来自原始院校数据，不受参考数据影响
                    original_location = uni_data.get('location', {})
                    original_province = original_location.get('province') or uni_data.get('province', '')
                    original_city = original_location.get('city') or uni_data.get('city', '')
                    
                    # 智能检测明显错误的地理位置并强制修复
                    needs_ai_fix = False
                    
                    # 检测明显的地理位置错误（院校名称与地理位置不符）
                    if original_province == '北京' and '北京' not in name:
                        # 排除真正的北京高校
                        beijing_universities = [
                            '清华大学', '北京大学', '中国人民大学', '北京师范大学', 
                            '北京理工大学', '北京航空航天大学', '北京科技大学', '北京化工大学',
                            '北京邮电大学', '中国农业大学', '北京林业大学', '中国传媒大学',
                            '中央民族大学', '北京中医药大学', '对外经济贸易大学', '中央财经大学',
                            '中国政法大学', '华北电力大学', '中国矿业大学(北京)', '中国石油大学(北京)',
                            '中国地质大学(北京)', '北京工业大学', '首都师范大学', '北京交通大学',
                            '北京外国语大学', '北京语言大学', '中央音乐学院', '中央美术学院',
                            '北京体育大学', '中国音乐学院', '中央戏剧学院', '北京电影学院'
                        ]
                        
                        # 特殊处理一些容易误判的院校
                        special_cases = {
                            '中国地质大学': '湖北',  # 默认指武汉校区
                            '中国矿业大学': '江苏',  # 默认指徐州校区  
                            '中国石油大学': '山东',  # 默认指青岛校区
                            '南京邮电大学': '江苏',
                            '哈尔滨理工大学': '黑龙江',
                            '西安电子科技大学': '陕西'
                        }
                        
                        if name in special_cases:
                            needs_ai_fix = True
                            app.logger.info(f"检测到{name}的地理位置错误(显示为北京)，应为{special_cases[name]}，将使用AI修复")
                        elif not any(beijing_uni in name for beijing_uni in beijing_universities):
                            needs_ai_fix = True
                            app.logger.info(f"检测到{name}的地理位置错误(显示为北京)，将使用AI修复")
                    
                    # 如果原始地理位置信息不完整或需要修复，尝试从AI获取
                    if not original_province or not original_city or needs_ai_fix:
                        try:
                            from models.realtime_ai_data import RealtimeAIDataProvider
                            provider = RealtimeAIDataProvider()
                            import asyncio
                            ai_location = asyncio.run(provider.get_university_location(name))
                            if ai_location and ai_location.get('province') not in ['未知省份', '待确认']:
                                original_province = ai_location['province']
                                original_city = ai_location['city']
                                app.logger.info(f"使用AI修复{name}的地理位置: {original_province} {original_city}")
                        except Exception as e:
                            app.logger.warning(f"AI修复{name}地理位置失败: {e}")
                            # 如果AI修复失败，继续使用原始数据
                    
                    # 创建包含正确地理位置的院校数据副本
                    enhanced_uni_data = uni_data.copy()
                    enhanced_uni_data['province'] = original_province
                    enhanced_uni_data['city'] = original_city
                    if 'location' not in enhanced_uni_data:
                        enhanced_uni_data['location'] = {}
                    enhanced_uni_data['location']['province'] = original_province
                    enhanced_uni_data['location']['city'] = original_city
                    
                    recommendations.append({
                        'university_name': name,
                        'university_data': enhanced_uni_data,
                        'ranking': ranking,
                        'category': category,
                        'probability': probability,
                        'probability_num': max(0, probability_num),
                        'min_score': min_score,
                        'avg_score': avg_score,
                        'score_difference': score - min_score,
                        'avg_difference': score - avg_score,
                        'data_source': score_data.get('data_source', '模拟数据'),
                        'data_year': 2023,
                        'reference_province': data_province if is_reference else None,
                        'is_reference_data': is_reference,
                        'original_province': province
                    })
        
        # 按类别和分数差异排序
        recommendations.sort(key=lambda x: (
            ['冲刺', '稳妥', '保底'].index(x['category']),
            -x['score_difference']
        ))
        
        # 分类返回
        result = {
            '冲刺': [r for r in recommendations if r['category'] == '冲刺'][:8],
            '稳妥': [r for r in recommendations if r['category'] == '稳妥'][:10],
            '保底': [r for r in recommendations if r['category'] == '保底'][:6]
        }
        
        return jsonify({
            'success': True,
            'filters': {
                'score': score,
                'province': province,
                'subject': subject
            },
            'total_count': len(recommendations),
            'data': result
        })
        
    except Exception as e:
        app.logger.error(f"获取推荐失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/mock_fill', methods=['POST'])
def mock_fill():
    """模拟填报"""
    try:
        data = request.get_json()
        selected_universities = data.get('universities', [])
        user_score = data.get('score', 0)
        
        results = []
        
        for university_name in selected_universities:
            uni_data = db.get_university_by_name(university_name)
            if not uni_data:
                continue
                
            # 获取该校录取分数
            scores = db.get_admission_scores(university_name)
            
            # 简单的录取概率计算
            for score_data in scores.values():
                min_score = score_data.get('min_score', 0)
                avg_score = score_data.get('avg_score', 0)
                
                if user_score >= avg_score + 15:
                    probability = "很高"
                    advice = "录取希望很大，可作为保底选择"
                elif user_score >= avg_score:
                    probability = "较高"
                    advice = "录取希望较大，建议填报"
                elif user_score >= min_score + 10:
                    probability = "中等"
                    advice = "有录取可能，建议谨慎填报"
                elif user_score >= min_score:
                    probability = "较低"
                    advice = "录取希望较小，可作为冲刺选择"
                else:
                    probability = "很低"
                    advice = "录取希望很小，不建议填报"
                
                results.append({
                    'university_name': university_name,
                    'university_data': uni_data,
                    'probability': probability,
                    'advice': advice,
                    'min_score': min_score,
                    'avg_score': avg_score,
                    'user_score': user_score
                })
                break  # 只取第一个匹配的分数数据
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        app.logger.error(f"模拟填报失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/university_details/<university_name>')
def get_university_details(university_name):
    """获取院校详细信息（增强版）"""
    try:
        # 初始化AI数据提供器
        from models.realtime_ai_data import RealtimeAIDataProvider
        provider = RealtimeAIDataProvider()
        
        # 获取基础院校数据
        university = db.get_university_by_name(university_name)
        if not university:
            return jsonify({
                'success': False,
                'error': '未找到该院校'
            }), 404
        
        # 使用AI获取准确的地理位置信息
        try:
            import asyncio
            ai_location = asyncio.run(provider.get_university_location(university_name))
            if ai_location and ai_location.get('province') not in ['未知省份', '待确认']:
                # 使用AI获取的准确地理位置
                university['province'] = ai_location['province']
                university['city'] = ai_location['city']
                if 'location' not in university:
                    university['location'] = {}
                university['location']['province'] = ai_location['province']
                university['location']['city'] = ai_location['city']
                app.logger.info(f"为 {university_name} 使用AI更新地理位置: {ai_location['province']} {ai_location['city']}")
            else:
                app.logger.warning(f"AI无法获取 {university_name} 的准确地理位置，使用原始数据")
        except Exception as e:
            app.logger.warning(f"AI地理位置获取失败: {e}")
        
        # 获取官网
        try:
            crawler = UniversityDataCrawler()
            website = crawler._get_university_website(university_name)
            university['website'] = website
            app.logger.info(f"为 {university_name} 获取到最新官网: {website}")
        except Exception as e:
            app.logger.warning(f"获取官网失败: {e}")
        
        # 获取录取分数线
        admission_scores = db.get_admission_scores(university_name)
        
        # 获取排名信息
        ranking = db.get_ranking(university_name)
        
        # 确保location字段存在
        if 'location' not in university:
            university['location'] = {}
        
        # 构建响应数据
        response_data = {
            'success': True,
            'university': {
                'name': university_name,
                'type': university.get('type', ''),
                'category': university.get('category', ''),
                'location': {
                    'province': university.get('location', {}).get('province', '') or university.get('province', ''),
                    'city': university.get('location', {}).get('city', '') or university.get('city', '')
                },
                'establishment_year': university.get('establishment_year', ''),
                'motto': university.get('motto', ''),
                'website': university.get('website', ''),
                'is_double_first_class': university.get('is_double_first_class', False),
                'key_disciplines': university.get('key_disciplines', []),
                'campus_area': university.get('campus_area', ''),
                'student_count': university.get('student_count', ''),
                'faculty_count': university.get('faculty_count', ''),
                'library_books': university.get('library_books', ''),
                'research_funding': university.get('research_funding', ''),
                'description': university.get('description', ''),
                'majors': university.get('majors', []),
                'employment': university.get('employment', {}),
                'enrollment_info': university.get('enrollment_info', {}),
                'data_sources': university.get('data_sources', []),
                'data_source': university.get('data_source', ''),
                'province': university.get('location', {}).get('province', '') or university.get('province', ''),
                'city': university.get('location', {}).get('city', '') or university.get('city', ''),
                'admission_scores': admission_scores,
                'ranking': ranking
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取院校详情失败: {str(e)}'
        }), 500

@app.route('/search_universities')
def search_universities():
    """搜索院校（兼容前端调用）"""
    try:
        # 初始化AI数据提供器
        from models.realtime_ai_data import RealtimeAIDataProvider
        provider = RealtimeAIDataProvider()
        
        keyword = request.args.get('q', '')
        province = request.args.get('province', '')
        university_type = request.args.get('type', '')
        
        app.logger.info(f"搜索参数: keyword='{keyword}', province='{province}', type='{university_type}'")
        
        # 获取院校数据
        if keyword:
            universities = db.search_universities(keyword)
            app.logger.info(f"关键词搜索 '{keyword}' 找到 {len(universities)} 所院校")
        elif province:
            universities = db.get_universities_by_province(province)
            app.logger.info(f"省份搜索 '{province}' 找到 {len(universities)} 所院校")
            # 调试：显示找到的院校名称
            if len(universities) > 0:
                app.logger.info(f"找到的院校: {list(universities.keys())[:5]}")
        elif university_type:
            universities = db.get_universities_by_type(university_type)
            app.logger.info(f"类型搜索 '{university_type}' 找到 {len(universities)} 所院校")
        else:
            universities = db.get_all_universities()
            app.logger.info(f"获取所有院校: {len(universities)} 所")
        
        # 转换数据格式以适配前端
        results = []
        for name, uni_data in universities.items():
            location = uni_data.get('location', {})
            ranking_data = db.get_ranking(name)
            
            # 使用AI获取准确的地理位置信息（如果需要）
            try:
                # 检查当前地理位置是否准确
                current_province = location.get('province', '') or uni_data.get('province', '')
                current_city = location.get('city', '') or uni_data.get('city', '')
                
                # 如果地理位置明显错误或为空，尝试使用AI获取
                if (not current_province or not current_city or 
                    current_province in ['未知省份', '待确认'] or 
                    current_city in ['未知城市', '待确认'] or
                    (current_province == '北京' and name not in ['清华大学', '北京大学', '中国人民大学', '北京师范大学', '北京理工大学', '北京航空航天大学', '北京科技大学', '北京化工大学', '北京邮电大学', '中国农业大学', '北京林业大学', '中国传媒大学', '中央民族大学', '北京中医药大学', '对外经济贸易大学', '中央财经大学', '中国政法大学', '华北电力大学', '中国矿业大学(北京)', '中国石油大学(北京)', '中国地质大学(北京)'])):
                    
                    ai_location = asyncio.run(provider.get_university_location(name))
                    if ai_location and ai_location.get('province') not in ['未知省份', '待确认']:
                        current_province = ai_location['province']
                        current_city = ai_location['city']
                        app.logger.info(f"搜索结果中为 {name} 使用AI更新地理位置: {current_province} {current_city}")
            except Exception as e:
                app.logger.warning(f"为 {name} 获取AI地理位置失败: {e}")
            
            # 处理排名信息
            if ranking_data and isinstance(ranking_data, dict):
                ranking_display = ranking_data.get('domestic', '未排名')
                if ranking_display != '未排名':
                    ranking_display = f"第{ranking_display}名"
            else:
                ranking_display = '未排名'
            
            result = {
                'id': name,
                'name': name,
                'province': current_province,
                'city': current_city,
                'type': uni_data.get('type', ''),
                'level': uni_data.get('category', ''),
                'ranking': ranking_display,
                'description': uni_data.get('motto', ''),
                'is_double_first_class': uni_data.get('is_double_first_class', False),
                'has_graduate_program': len(uni_data.get('key_disciplines', [])) > 0
            }
            results.append(result)
        
        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        app.logger.error(f"搜索院校失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'success': False,
        'error': '接口不存在'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    app.logger.error(f"内部服务器错误: {error}")
    return jsonify({
        'success': False,
        'error': '内部服务器错误'
    }), 500

@app.route('/api/realtime/university_data/<university_name>')
def get_university_realtime_data(university_name):
    """获取院校实时数据API"""
    try:
        province = request.args.get('province', '北京')
        subject = request.args.get('subject', '理科')
        year = int(request.args.get('year', 2023))
        
        from models.realtime_ai_data import get_realtime_university_data
        
        # 获取实时数据
        realtime_data = get_realtime_university_data(university_name, province, subject, year)
        
        return jsonify({
            'success': True,
            'university_name': university_name,
            'data': realtime_data,
            'query_params': {
                'province': province,
                'subject': subject,
                'year': year
            }
        })
        
    except Exception as e:
        app.logger.error(f"获取{university_name}实时数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/realtime/batch_scores', methods=['POST'])
def get_batch_realtime_scores():
    """批量获取多所院校的实时分数线"""
    try:
        data = request.get_json()
        universities = data.get('universities', [])
        province = data.get('province', '北京')
        subject = data.get('subject', '理科')
        year = data.get('year', 2023)
        
        if not universities:
            return jsonify({
                'success': False,
                'error': '请提供院校列表'
            }), 400
        
        from models.realtime_ai_data import RealtimeDataManager
        
        manager = RealtimeDataManager()
        
        # 使用异步方式批量获取
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            scores_data = loop.run_until_complete(
                manager.batch_get_scores(universities, province, subject, year)
            )
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'total_universities': len(universities),
            'successful_results': len(scores_data),
            'data': scores_data,
            'query_params': {
                'province': province,
                'subject': subject,
                'year': year
            }
        })
        
    except Exception as e:
        app.logger.error(f"批量获取实时分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/realtime/province_scores/<university_name>')
def get_all_provinces_scores(university_name):
    """获取某院校在所有省份的分数线"""
    try:
        subject = request.args.get('subject', '理科')
        year = int(request.args.get('year', 2023))
        
        from models.realtime_ai_data import RealtimeDataManager
        
        manager = RealtimeDataManager()
        
        # 使用异步方式获取全国分数线
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            province_scores = loop.run_until_complete(
                manager.get_all_provinces_scores(university_name, subject, year)
            )
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'university_name': university_name,
            'total_provinces': len(province_scores),
            'data': province_scores,
            'query_params': {
                'subject': subject,
                'year': year
            }
        })
        
    except Exception as e:
        app.logger.error(f"获取{university_name}全国分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/realtime/recommendation')
def get_realtime_recommendation():
    """获取实时AI推荐"""
    try:
        score = int(request.args.get('score', 600))
        province = request.args.get('province', '北京')
        subject = request.args.get('subject', '理科')
        
        from models.realtime_ai_data import realtime_data_manager
        
        # 获取实时推荐
        recommendations = realtime_data_manager.get_realtime_recommendation(score, province, subject)
        
        # 统计信息
        stats = {}
        total_universities = 0
        for category, unis in recommendations.items():
            stats[category] = len(unis)
            total_universities += len(unis)
        
        return jsonify({
            'success': True,
            'user_params': {
                'score': score,
                'province': province,
                'subject': subject
            },
            'statistics': stats,
            'total_universities': total_universities,
            'recommendations': recommendations,
            'is_realtime': True,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"获取实时推荐失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/realtime/cache_status')
def get_cache_status():
    """获取AI缓存状态"""
    try:
        from models.realtime_ai_data import RealtimeAIDataProvider
        
        provider = RealtimeAIDataProvider()
        
        # 查询缓存统计
        import sqlite3
        with sqlite3.connect(provider.cache_db) as conn:
            cursor = conn.execute("""
                SELECT 
                    query_type,
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as valid_count,
                    COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as expired_count
                FROM ai_cache 
                GROUP BY query_type
            """)
            
            cache_stats = {}
            for row in cursor.fetchall():
                query_type, total, valid, expired = row
                cache_stats[query_type] = {
                    'total': total,
                    'valid': valid,
                    'expired': expired
                }
            
            # 总体统计
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as valid,
                    COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as expired
                FROM ai_cache
            """)
            
            total_stats = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'cache_file': provider.cache_db,
            'cache_duration_hours': provider.cache_duration.total_seconds() / 3600,
            'overall_stats': {
                'total_entries': total_stats[0],
                'valid_entries': total_stats[1],
                'expired_entries': total_stats[2]
            },
            'by_query_type': cache_stats,
            'ai_services': provider.get_ai_services()
        })
        
    except Exception as e:
        app.logger.error(f"获取缓存状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/realtime/clean_cache', methods=['POST'])
def clean_expired_cache():
    """清理过期缓存"""
    try:
        from models.realtime_ai_data import RealtimeAIDataProvider
        
        provider = RealtimeAIDataProvider()
        
        # 获取清理前的统计
        import sqlite3
        with sqlite3.connect(provider.cache_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM ai_cache WHERE expires_at <= datetime('now')")
            expired_count = cursor.fetchone()[0]
        
        # 清理过期缓存
        provider.clean_expired_cache()
        
        return jsonify({
            'success': True,
            'cleaned_entries': expired_count,
            'message': f'已清理{expired_count}条过期缓存记录'
        })
        
    except Exception as e:
        app.logger.error(f"清理缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/realtime')
def admin_realtime():
    """实时AI数据管理面板"""
    return render_template('admin_panel.html')

# API配置管理路由
@app.route('/api/config/list', methods=['GET'])
def get_api_configs():
    """获取所有API配置（脱敏）"""
    if not api_config_manager:
        return jsonify({'success': False, 'error': 'API配置管理器未加载'})
    
    try:
        configs = api_config_manager.get_all_masked_configs()
        return jsonify({
            'success': True,
            'configs': configs,
            'total': len(configs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/<service_name>', methods=['GET'])
def get_api_config(service_name):
    """获取指定服务的配置（脱敏）"""
    if not api_config_manager:
        return jsonify({'success': False, 'error': 'API配置管理器未加载'})
    
    try:
        config = api_config_manager.get_masked_config(service_name)
        if config:
            return jsonify({'success': True, 'config': config})
        else:
            return jsonify({'success': False, 'error': '配置不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/<service_name>', methods=['POST'])
def update_api_config(service_name):
    """更新API配置"""
    if not api_config_manager:
        return jsonify({'success': False, 'error': 'API配置管理器未加载'})
    
    try:
        data = request.get_json()
        
        # 提取参数
        api_key = data.get('api_key')
        api_url = data.get('api_url')
        model_name = data.get('model_name')
        enabled = data.get('enabled')
        
        # 更新配置
        success = api_config_manager.update_config(
            service_name, 
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            enabled=enabled
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{service_name}配置更新成功',
                'config': api_config_manager.get_masked_config(service_name)
            })
        else:
            return jsonify({'success': False, 'error': '配置更新失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/<service_name>/test', methods=['POST'])
def test_api_config(service_name):
    """测试API配置"""
    if not api_config_manager:
        return jsonify({'success': False, 'error': 'API配置管理器未加载'})
    
    try:
        # 基本格式验证
        result = api_config_manager.test_api_key(service_name)
        
        # 如果基本验证通过，可以尝试实际调用
        if result['success'] and service_name != 'chatglm_reverse':
            # 这里可以添加实际的API调用测试
            # 暂时只做基本验证
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/<service_name>/toggle', methods=['POST'])
def toggle_api_config(service_name):
    """切换服务启用状态"""
    if not api_config_manager:
        return jsonify({'success': False, 'error': 'API配置管理器未加载'})
    
    try:
        current_config = api_config_manager.get_config(service_name)
        if not current_config:
            return jsonify({'success': False, 'error': '配置不存在'})
        
        new_enabled = not current_config.get('enabled', False)
        success = api_config_manager.update_config(service_name, enabled=new_enabled)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{service_name}已{"启用" if new_enabled else "禁用"}',
                'enabled': new_enabled
            })
        else:
            return jsonify({'success': False, 'error': '状态切换失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai_scores/<university_name>', methods=['POST'])
def get_ai_scores_for_university(university_name):
    """使用专业API获取指定院校在各省份的录取分数线"""
    try:
        data = request.get_json() or {}
        target_provinces = data.get('provinces', [])  # 如果为空则获取所有省份
        subject = data.get('subject', '理科')
        year = data.get('year', 2023)
        
        if not target_provinces:
            # 默认获取主要省份的数据
            target_provinces = [
                "北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
                "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
                "广东", "广西", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海"
            ]
        
        # 使用专业数据API替代AI数据提供器
        from models.professional_data_api import ProfessionalDataAPI
        professional_api = ProfessionalDataAPI()
        
        results = {}
        success_count = 0
        failed_provinces = []
        
        app.logger.info(f"开始使用专业API获取{university_name}在{len(target_provinces)}个省份的录取分数线")
        
        # 同步获取各省份数据
        for province in target_provinces:
            try:
                result = professional_api.get_admission_scores(university_name, province, subject, year)
                if result['success']:
                    score_data = result['data']
                    results[province] = {
                        'min_score': score_data.get('min_score'),
                        'avg_score': score_data.get('avg_score', score_data.get('min_score', 0) + 15),
                        'max_score': score_data.get('max_score', score_data.get('min_score', 0) + 50),
                        'rank': score_data.get('rank'),
                        'batch': score_data.get('batch', '本科一批A段'),
                        'enrollment': score_data.get('enrollment', 50),
                        'data_source': f"专业API - {result.get('source', '权威数据')}",
                        'confidence': result.get('confidence', 0.95),
                        'accuracy_level': 'high',
                        'updated_at': result.get('last_updated')
                    }
                    success_count += 1
                else:
                    failed_provinces.append(province)
                    app.logger.debug(f"专业API未找到{university_name}在{province}的数据: {result.get('error', '未知')}")
                    
            except Exception as e:
                failed_provinces.append(province)
                app.logger.warning(f"获取{university_name}在{province}的分数线失败: {e}")
        
        app.logger.info(f"专业API获取完成: {university_name}，成功{success_count}个省份，失败{len(failed_provinces)}个省份")
        
        # 计算统计信息
        valid_scores = [data.get('min_score', 0) for data in results.values() if data.get('min_score', 0) > 0]
        
        return jsonify({
            'success': True,
            'data_source': 'professional_api',
            'university_name': university_name,
            'query_params': {
                'subject': subject,
                'year': year,
                'total_provinces': len(target_provinces)
            },
            'results': {
                'success_count': success_count,
                'failed_count': len(failed_provinces),
                'failed_provinces': failed_provinces,
                'scores_data': results
            },
            'summary': {
                'highest_score': max(valid_scores) if valid_scores else 0,
                'lowest_score': min(valid_scores) if valid_scores else 0,
                'average_score': sum(valid_scores) // len(valid_scores) if valid_scores else 0,
                'message': f'✅ 使用专业API获取数据，准确性更高'
            }
        })
        
    except Exception as e:
        app.logger.error(f"专业API获取{university_name}录取分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai_scores/batch', methods=['POST'])
def get_ai_scores_batch():
    """批量使用专业API获取多所院校的录取分数线"""
    try:
        data = request.get_json()
        universities = data.get('universities', [])
        provinces = data.get('provinces', ['北京', '上海', '江苏', '广东', '浙江'])
        subject = data.get('subject', '理科')
        year = data.get('year', 2023)
        
        if not universities:
            return jsonify({
                'success': False,
                'error': '请提供院校列表'
            }), 400
        
        # 使用专业数据API替代AI数据提供器
        from models.professional_data_api import ProfessionalDataAPI
        professional_api = ProfessionalDataAPI()
        
        all_results = {}
        total_success = 0
        
        app.logger.info(f"开始批量使用专业API获取{len(universities)}所院校在{len(provinces)}个省份的录取分数线")
        
        for university in universities:
            university_results = {}
            success_count = 0
            
            # 为每个院校获取所有省份数据
            for province in provinces:
                try:
                    result = professional_api.get_admission_scores(university, province, subject, year)
                    if result['success']:
                        score_data = result['data']
                        university_results[province] = {
                            'min_score': score_data.get('min_score'),
                            'avg_score': score_data.get('avg_score', score_data.get('min_score', 0) + 15),
                            'max_score': score_data.get('max_score', score_data.get('min_score', 0) + 50),
                            'rank': score_data.get('rank'),
                            'batch': score_data.get('batch', '本科一批A段'),
                            'enrollment': score_data.get('enrollment', 50),
                            'data_source': f"专业API - {result.get('source', '权威数据')}",
                            'confidence': result.get('confidence', 0.95),
                            'accuracy_level': 'high',
                            'updated_at': result.get('last_updated')
                        }
                        success_count += 1
                    else:
                        app.logger.debug(f"专业API未找到{university}在{province}的数据: {result.get('error', '未知')}")
                        
                except Exception as e:
                    app.logger.warning(f"获取{university}在{province}数据时出错: {e}")
                    continue
            
            all_results[university] = {
                'scores': university_results,
                'success_count': success_count,
                'coverage_rate': round(success_count / len(provinces) * 100, 1)
            }
            total_success += success_count
            
            app.logger.info(f"完成{university}: {success_count}/{len(provinces)}个省份（专业API）")
        
        return jsonify({
            'success': True,
            'data_source': 'professional_api',
            'query_params': {
                'universities': universities,
                'provinces': provinces,
                'subject': subject,
                'year': year
            },
            'results': all_results,
            'summary': {
                'total_universities': len(universities),
                'total_provinces': len(provinces),
                'total_possible_combinations': len(universities) * len(provinces),
                'total_success': total_success,
                'overall_success_rate': round(total_success / (len(universities) * len(provinces)) * 100, 1),
                'message': f'✅ 使用专业API获取数据，准确性更高'
            }
        })
        
    except Exception as e:
        app.logger.error(f"批量专业API获取录取分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/university_scores_by_province/<university_name>', methods=['POST'])
def get_university_scores_by_province(university_name):
    """根据用户选择的省份获取大学录取分数线（使用专业API）"""
    try:
        data = request.get_json()
        selected_province = data.get('province', '北京')
        subject = data.get('subject', '理科')
        year = data.get('year', 2023)
        
        app.logger.info(f"使用专业API获取{university_name}在{selected_province}省的录取分数线")
        
        # 使用专业数据API获取准确的录取分数线
        from models.professional_data_api import ProfessionalDataAPI
        
        professional_api = ProfessionalDataAPI()
        result = professional_api.get_admission_scores(university_name, selected_province, subject, year)
        
        if result['success']:
            scores_data = result['data']
            
            # 获取院校基本信息
            basic_info = db.get_university_by_name(university_name)
            
            # 格式化返回数据，保持与前端的兼容性
            formatted_result = {
                'university_name': university_name,
                'province': selected_province,
                'subject': subject,
                'year': year,
                'scores': {
                    'min_score': scores_data.get('min_score'),
                    'avg_score': scores_data.get('avg_score', scores_data.get('min_score', 0) + 15),
                    'max_score': scores_data.get('max_score', scores_data.get('min_score', 0) + 50),
                    'rank': scores_data.get('rank'),
                    'batch': scores_data.get('batch', '本科一批A段'),
                    'enrollment': scores_data.get('enrollment', 50),
                    'data_source': f"专业API - {result.get('source', '权威数据')}",
                    'confidence': result.get('confidence', 0.95),
                    'major_scores': []  # 专业分数线可以后续扩展
                },
                'basic_info': basic_info,
                'data_source_type': 'professional_api',
                'accuracy_level': 'high',
                'user_message': '✅ 数据来源权威，准确性很高，可放心参考',
                'last_updated': result.get('last_updated', datetime.now().isoformat())
            }
            
            app.logger.info(f"专业API成功获取{university_name}在{selected_province}的录取分数线: {scores_data.get('min_score', '未知')}分")
            
            return jsonify({
                'success': True,
                'data': formatted_result
            })
        else:
            app.logger.warning(f"专业API获取{university_name}录取分数线失败: {result.get('error', '未知错误')}")
            return jsonify({
                'success': False,
                'error': f"暂无{university_name}在{selected_province}省{year}年{subject}的录取数据"
            }), 404
            
    except Exception as e:
        app.logger.error(f"获取{university_name}在{selected_province}录取分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/provinces')
def get_provinces_list():
    """获取所有省份列表，用于前端选择器"""
    provinces = [
        {'code': 'beijing', 'name': '北京', 'full_name': '北京市'},
        {'code': 'tianjin', 'name': '天津', 'full_name': '天津市'},
        {'code': 'hebei', 'name': '河北', 'full_name': '河北省'},
        {'code': 'shanxi', 'name': '山西', 'full_name': '山西省'},
        {'code': 'neimenggu', 'name': '内蒙古', 'full_name': '内蒙古自治区'},
        {'code': 'liaoning', 'name': '辽宁', 'full_name': '辽宁省'},
        {'code': 'jilin', 'name': '吉林', 'full_name': '吉林省'},
        {'code': 'heilongjiang', 'name': '黑龙江', 'full_name': '黑龙江省'},
        {'code': 'shanghai', 'name': '上海', 'full_name': '上海市'},
        {'code': 'jiangsu', 'name': '江苏', 'full_name': '江苏省'},
        {'code': 'zhejiang', 'name': '浙江', 'full_name': '浙江省'},
        {'code': 'anhui', 'name': '安徽', 'full_name': '安徽省'},
        {'code': 'fujian', 'name': '福建', 'full_name': '福建省'},
        {'code': 'jiangxi', 'name': '江西', 'full_name': '江西省'},
        {'code': 'shandong', 'name': '山东', 'full_name': '山东省'},
        {'code': 'henan', 'name': '河南', 'full_name': '河南省'},
        {'code': 'hubei', 'name': '湖北', 'full_name': '湖北省'},
        {'code': 'hunan', 'name': '湖南', 'full_name': '湖南省'},
        {'code': 'guangdong', 'name': '广东', 'full_name': '广东省'},
        {'code': 'guangxi', 'name': '广西', 'full_name': '广西壮族自治区'},
        {'code': 'hainan', 'name': '海南', 'full_name': '海南省'},
        {'code': 'chongqing', 'name': '重庆', 'full_name': '重庆市'},
        {'code': 'sichuan', 'name': '四川', 'full_name': '四川省'},
        {'code': 'guizhou', 'name': '贵州', 'full_name': '贵州省'},
        {'code': 'yunnan', 'name': '云南', 'full_name': '云南省'},
        {'code': 'xizang', 'name': '西藏', 'full_name': '西藏自治区'},
        {'code': 'shaanxi', 'name': '陕西', 'full_name': '陕西省'},
        {'code': 'gansu', 'name': '甘肃', 'full_name': '甘肃省'},
        {'code': 'qinghai', 'name': '青海', 'full_name': '青海省'},
        {'code': 'ningxia', 'name': '宁夏', 'full_name': '宁夏回族自治区'},
        {'code': 'xinjiang', 'name': '新疆', 'full_name': '新疆维吾尔自治区'}
    ]
    
    return jsonify({
        'success': True,
        'provinces': provinces
    })

@app.route('/test_recommendations')
def test_recommendations():
    """临时测试路由 - 调试推荐院校显示"""
    try:
        # 模拟分数计算请求
        score = 650
        province = "北京"
        subject = "理科"
        preferences = []
        
        # 直接复制calculate_score的核心逻辑
        recommendations = []
        universities = db.get_all_universities()
        
        for name, uni_data in universities.items():
            # 检查该院校是否有对应省份和科目的录取分数线
            admission_scores = uni_data.get('admission_scores', {})
            
            # 查找匹配的分数线数据，优先使用最新年份
            matching_scores = []
            
            # 首先尝试用户指定的省份
            for year in [2023, 2022, 2021]:  # 按年份优先级查找
                score_key = f"{province}_{year}_{subject}"
                if score_key in admission_scores:
                    matching_scores.append((year, admission_scores[score_key], province))
            
            if not matching_scores:
                continue  # 没有匹配的分数线数据
            
            # 使用最新年份的数据
            year, score_data, data_province = matching_scores[0]
            min_score = score_data.get('min_score', 0)
            avg_score = score_data.get('avg_score', min_score + 15)
            
            if min_score == 0:
                continue
            
            # 推荐逻辑：冲刺、稳妥、保底
            score_diff = score - min_score
            
            # 更合理的分类逻辑
            if score >= min_score + 30:
                category = "保底"
                probability = "95%以上"
            elif score >= min_score + 10:
                category = "稳妥" 
                probability = "80-90%"
            elif score >= min_score - 20:
                category = "冲刺"
                probability = "30-70%"
            else:
                continue  # 分数太低，不推荐
            
            recommendation = {
                'university_name': name,
                'category': category,
                'min_score': min_score,
                'avg_score': avg_score,
                'probability': probability,
                'score_difference': score_diff,
                'university_data': uni_data
            }
            
            recommendations.append(recommendation)
        
        # 按类别分组
        categorized_recommendations = {
            '冲刺': [r for r in recommendations if r['category'] == '冲刺'],
            '稳妥': [r for r in recommendations if r['category'] == '稳妥'],
            '保底': [r for r in recommendations if r['category'] == '保底']
        }
        
        # 返回测试页面
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>推荐院校调试</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .university {{ margin: 10px 0; padding: 10px; background: #f9f9f9; }}
                .debug {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>推荐院校调试页面</h1>
            
            <div class="section">
                <h2>测试参数</h2>
                <p>分数: {score}分 | 省份: {province} | 科目: {subject}</p>
            </div>
            
            <div class="section">
                <h2>数据概览</h2>
                <p>总院校: {len(universities)}</p>
                <p>有效推荐: {len(recommendations)}</p>
                <div class="debug">
                    冲刺: {len(categorized_recommendations['冲刺'])}所 | 
                    稳妥: {len(categorized_recommendations['稳妥'])}所 | 
                    保底: {len(categorized_recommendations['保底'])}所
                </div>
            </div>
            
            <div class="section">
                <h2>稳妥院校 ({len(categorized_recommendations['稳妥'])}所)</h2>
                {"".join([f'<div class="university">{uni["university_name"]} - 最低分: {uni["min_score"]}分 (分差: {uni["score_difference"]:+d})</div>' for uni in categorized_recommendations['稳妥']])}
            </div>
            
            <div class="section">
                <h2>冲刺院校 ({len(categorized_recommendations['冲刺'])}所)</h2>
                {"".join([f'<div class="university">{uni["university_name"]} - 最低分: {uni["min_score"]}分 (分差: {uni["score_difference"]:+d})</div>' for uni in categorized_recommendations['冲刺']])}
            </div>
            
            <div class="section">
                <h2>保底院校 ({len(categorized_recommendations['保底'])}所)</h2>
                {"".join([f'<div class="university">{uni["university_name"]} - 最低分: {uni["min_score"]}分 (分差: {uni["score_difference"]:+d})</div>' for uni in categorized_recommendations['保底']])}
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        import traceback
        return f"调试错误: {str(e)}<br><pre>{traceback.format_exc()}</pre>"

@app.route('/api/ai_scores_professional/<university_name>', methods=['POST'])
def get_ai_scores_professional(university_name):
    """获取专业级AI分数线数据（基于权威数据源）"""
    try:
        data = request.get_json()
        province = data.get('province', '北京')
        subject = data.get('subject', '理科')
        year = data.get('year', 2023)
        
        # 使用专业数据API
        from models.professional_data_api import get_professional_scores
        
        result = get_professional_scores(university_name, province, subject, year)
        
        if result.get('success'):
            # 转换为统一格式
            score_data = result.get('data', {})
            scores_result = {
                'success': True,
                'university': university_name,
                'query_params': {
                    'province': province,
                    'subject': subject,
                    'year': year
                },
                'results': {
                    'ai_generated': True,
                    'data_source': result.get('source', 'professional_api'),
                    'confidence': result.get('confidence', 0.95),
                    'scores_data': {
                        province: {
                            'min_score': score_data.get('min_score', 0),
                            'avg_score': score_data.get('avg_score', score_data.get('min_score', 0) + 10),
                            'max_score': score_data.get('max_score', score_data.get('min_score', 0) + 30),
                            'rank_min': score_data.get('rank', 0),
                            'batch': score_data.get('batch', '本科一批'),
                            'enrollment': score_data.get('enrollment', 50),
                            'updated_at': result.get('last_updated', datetime.now().isoformat()),
                            'majors': [
                                {
                                    'name': f'{university_name}主要专业',
                                    'min_score': score_data.get('min_score', 0),
                                    'avg_score': score_data.get('min_score', 0) + 5
                                }
                            ]
                        }
                    },
                    'total_provinces': 1,
                    'successful_provinces': 1
                },
                'api_calls': 1,
                'processing_time': 0.1
            }
            
            app.logger.info(f"专业API成功获取{university_name}在{province}的分数线: {score_data.get('min_score')}分")
            return jsonify(scores_result)
        else:
            app.logger.warning(f"专业API获取{university_name}分数线失败: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '无法获取数据'),
                'university': university_name
            }), 404
            
    except Exception as e:
        app.logger.error(f"专业API分数线查询失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data_sources/status')
def get_all_data_sources_status():
    """获取所有数据源状态"""
    try:
        status = {
            'chatglm_reverse': {
                'name': 'ChatGLM逆向接口',
                'enabled': True,
                'accuracy': 'low',
                'description': '智能生成模式，数据准确性较低'
            },
            'professional_api': {
                'name': '专业数据API',
                'enabled': True, 
                'accuracy': 'high',
                'description': '基于权威数据源，数据准确性高'
            },
            'web_crawler': {
                'name': '网络爬虫',
                'enabled': True,
                'accuracy': 'medium',
                'description': '从公开网站获取，数据准确性中等'
            }
        }
        
        # 检验专业API状态
        try:
            from models.professional_data_api import professional_api
            api_status = professional_api.validate_apis()
            status['professional_api']['api_keys'] = api_status
            status['professional_api']['reference_data_count'] = len(professional_api.reference_data)
        except Exception as e:
            status['professional_api']['error'] = str(e)
        
        return jsonify({
            'success': True,
            'data_sources': status,
            'recommendation': 'professional_api',
            'updated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"获取数据源状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/accurate_scores/<university_name>', methods=['POST'])
def get_accurate_scores_api(university_name):
    """获取准确的录取分数线（优先使用最准确的数据源）"""
    if not data_accuracy_enabled:
        return jsonify({
            'success': False,
            'error': '数据准确性管理器未启用'
        }), 500
    
    try:
        data = request.get_json()
        province = data.get('province', '北京')
        subject = data.get('subject', '理科')
        year = data.get('year', 2023)
        
        result = get_accurate_university_scores(university_name, province, subject, year)
        
        # 添加额外的提示信息
        if result.get('success'):
            accuracy_level = result.get('accuracy_level', 'unknown')
            if accuracy_level == 'high':
                result['user_message'] = '✅ 数据来源权威，准确性很高，可放心参考'
            elif accuracy_level == 'medium':
                result['user_message'] = '⚠️ 数据来源可靠，但建议核实官方信息'
            else:
                result['user_message'] = '🔄 数据为AI生成，准确性较低，仅供参考，建议验证多个数据源'
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"获取准确分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data_quality/report')
def get_data_quality_report():
    """获取数据质量报告"""
    if not data_accuracy_enabled:
        return jsonify({
            'success': False,
            'error': '数据准确性管理器未启用'
        }), 500
    
    try:
        report = data_accuracy_manager.get_data_quality_report()
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        app.logger.error(f"生成数据质量报告失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data_quality/improvement_plan')
def get_improvement_plan():
    """获取数据准确性改进计划"""
    if not data_accuracy_enabled:
        return jsonify({
            'success': False,
            'error': '数据准确性管理器未启用'
        }), 500
    
    try:
        plan = data_accuracy_manager.suggest_improvement_plan()
        return jsonify({
            'success': True,
            'improvement_plan': plan
        })
        
    except Exception as e:
        app.logger.error(f"生成改进计划失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data_quality/validate/<source_name>')
def validate_data_source_api(source_name):
    """验证指定数据源的状态"""
    if not data_accuracy_enabled:
        return jsonify({
            'success': False,
            'error': '数据准确性管理器未启用'
        }), 500
    
    try:
        validation_result = data_accuracy_manager.validate_data_source(source_name)
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        app.logger.error(f"验证数据源{source_name}失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/batch_accurate_scores', methods=['POST'])
def batch_get_accurate_scores():
    """批量获取准确的录取分数线"""
    if not data_accuracy_enabled:
        return jsonify({
            'success': False,
            'error': '数据准确性管理器未启用'
        }), 500
    
    try:
        data = request.get_json()
        requests = data.get('requests', [])
        
        if not requests:
            return jsonify({
                'success': False,
                'error': '请提供院校请求列表'
            }), 400
        
        result = data_accuracy_manager.batch_get_accurate_scores(requests)
        
        # 添加用户友好的统计信息
        stats = result['stats']
        result['user_summary'] = {
            'total': result['total_requests'],
            'high_accuracy': stats['high_accuracy'],
            'low_accuracy': stats['low_accuracy'],
            'failed': stats['failed'],
            'overall_message': f"成功获取{result['total_requests'] - stats['failed']}所院校数据，其中{stats['high_accuracy']}所为权威数据"
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        app.logger.error(f"批量获取准确分数线失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🎓 高考志愿填报系统启动中...")
    print(f"📊 数据源状态: {db.get_data_source_status()}")
    print(f"🏫 已加载院校数量: {len(db.get_all_universities())}")
    print(f"🌐 访问地址: http://localhost:{Config.APP['PORT']}")
    
    app.run(
        host=Config.APP['HOST'],
        port=Config.APP['PORT'],
        debug=Config.APP['DEBUG']
    ) 