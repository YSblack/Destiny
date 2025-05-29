from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
import logging
import os
from datetime import datetime
from config import Config
from models.university_data import get_university_database
from typing import Dict, Any
import json

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
    """分数计算和院校推荐"""
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
        
        # 获取适合的院校推荐
        recommendations = []
        universities = db.get_all_universities()
        
        for name, uni_data in universities.items():
            # 检查该院校是否有对应省份和科目的录取分数线
            admission_scores = uni_data.get('admission_scores', {})
            
            # 查找匹配的分数线数据，优先使用最新年份
            matching_scores = []
            for year in [2023, 2022, 2021]:  # 按年份优先级查找
                score_key = f"{province}_{year}_{subject}"
                if score_key in admission_scores:
                    matching_scores.append((year, admission_scores[score_key]))
            
            if not matching_scores:
                continue  # 没有匹配的分数线数据
            
            # 使用最新年份的数据
            year, score_data = matching_scores[0]
            min_score = score_data.get('min_score', 0)
            avg_score = score_data.get('avg_score', 0)
            
            if min_score == 0 and avg_score == 0:
                continue
            
            # 如果没有平均分，用最低分+15作为估算
            if avg_score == 0:
                avg_score = min_score + 15
            
            # 推荐逻辑：冲刺、稳妥、保底
            score_diff = score - min_score
            avg_diff = score - avg_score
            
            # 更合理的分类逻辑
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
                continue  # 分数太低，不推荐
            
            # 检查偏好匹配
            preference_match = True
            if preferences:
                uni_type = uni_data.get('type', '')
                if not any(pref in uni_type for pref in preferences):
                    # 如果不匹配偏好，降低优先级
                    probability_num -= 10
            
            # 获取排名信息
            ranking = db.get_ranking(name)
            
            recommendations.append({
                'university_name': name,
                'university_data': uni_data,
                'ranking': ranking,
                'category': category,
                'probability': probability,
                'probability_num': max(0, probability_num),
                'min_score': min_score,
                'avg_score': avg_score,
                'score_difference': score_diff,
                'avg_difference': avg_diff,
                'data_source': score_data.get('data_source', '模拟数据'),
                'data_year': year
            })
        
        # 按概率和分数差异排序
        recommendations.sort(key=lambda x: (-x['probability_num'], -x['score_difference']))
        
        # 分类返回，每类限制数量
        result = {
            '冲刺': [r for r in recommendations if r['category'] == '冲刺'][:15],
            '稳妥': [r for r in recommendations if r['category'] == '稳妥'][:15],
            '保底': [r for r in recommendations if r['category'] == '保底'][:10]
        }
        
        # 计算分数分析
        score_analysis = calculate_score_analysis(score, province, subject)
        
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
            'debug_info': {
                'total_universities': len(universities),
                'matched_universities': len(recommendations),
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
                'province': university.get('province', ''),
                'city': university.get('city', ''),
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
def get_data_sources_status():
    """获取数据源状态"""
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
                    
                    recommendations.append({
                        'university_name': name,
                        'university_data': uni_data,
                        'ranking': ranking,
                        'category': category,
                        'probability': probability,
                        'min_score': min_score,
                        'avg_score': avg_score,
                        'score_difference': score - min_score
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
def get_university_details_legacy(university_name):
    """获取院校详情（兼容前端调用）"""
    try:
        university = db.get_university_by_name(university_name)
        if not university:
            return jsonify({
                'success': False,
                'error': f'院校 "{university_name}" 不存在'
            }), 404
        
        # 获取额外信息
        ranking = db.get_ranking(university_name)
        
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
                'province': university.get('province', ''),
                'city': university.get('city', ''),
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
        keyword = request.args.get('q', '')
        province = request.args.get('province', '')
        university_type = request.args.get('type', '')
        
        # 获取院校数据
        if keyword:
            universities = db.search_universities(keyword)
        elif province:
            universities = db.get_universities_by_province(province)
        elif university_type:
            universities = db.get_universities_by_type(university_type)
        else:
            universities = db.get_all_universities()
        
        # 转换数据格式以适配前端
        results = []
        for name, uni_data in universities.items():
            location = uni_data.get('location', {})
            ranking_data = db.get_ranking(name)
            
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
                'province': location.get('province', ''),
                'city': location.get('city', ''),
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