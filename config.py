import os
from typing import Dict, Any

class Config:
    """配置管理类"""
    
    # 数据源API配置
    DATA_SOURCES = {
        # 咕咕数据 - 高考分数线数据
        'GUGUDATA_KEY': os.getenv('GUGUDATA_KEY', ''),
        'GUGUDATA_URL': 'https://api.gugudata.com/metadata/ceeprovince',
        
        # 昂焱数据 - 高校信息数据  
        'AYSHUJU_KEY': os.getenv('AYSHUJU_KEY', ''),
        'AYSHUJU_URL': 'https://www.ayshuju.com/data/edu/college',
        
        # 学信网 - 学历验证
        'CHSI_URL': 'https://zwfw.moe.gov.cn/chsi/',
        
        # 阳光高考平台
        'GAOKAO_PLATFORM_URL': 'https://gkcx.eol.cn',
        
        # 软科排名
        'SHANGHAIRANKING_URL': 'https://www.shanghairanking.cn'
    }
    
    # 数据库配置
    DATABASE = {
        'DATA_DIR': 'data',
        'UNIVERSITIES_FILE': 'universities.json',
        'SCORES_FILE': 'admission_scores.json',
        'RANKINGS_FILE': 'rankings.json',
        'BACKUP_DIR': 'backups',
        'MAX_BACKUPS': 10
    }
    
    # 爬虫配置
    CRAWLER = {
        'REQUEST_TIMEOUT': 10,
        'REQUEST_DELAY': 0.5,  # 请求间隔
        'MAX_RETRIES': 3,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'ENABLE_CACHE': True,
        'CACHE_EXPIRE_HOURS': 24
    }
    
    # 应用配置
    APP = {
        'HOST': '0.0.0.0',
        'PORT': 5010,
        'DEBUG': True,
        'SECRET_KEY': os.getenv('SECRET_KEY', 'your-secret-key-here'),
        'JSON_AS_ASCII': False
    }
    
    # 日志配置
    LOGGING = {
        'LEVEL': 'INFO',
        'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'FILE': 'logs/app.log',
        'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
        'BACKUP_COUNT': 5
    }
    
    # 分数线计算配置
    SCORE_CALCULATION = {
        'BASE_SCORES': {
            '985': {'理科': 650, '文科': 620},
            '211': {'理科': 600, '文科': 580},
            '普通本科': {'理科': 520, '文科': 500},
            '专科': {'理科': 400, '文科': 380}
        },
        'PROVINCE_FACTORS': {
            '北京': 0.95, '上海': 0.95, '天津': 0.96,
            '河南': 1.08, '山东': 1.06, '河北': 1.07,
            '江苏': 1.03, '浙江': 1.02, '广东': 1.01,
            '四川': 1.04, '湖南': 1.05, '湖北': 1.04,
            '陕西': 1.03, '安徽': 1.04, '福建': 1.02,
            '江西': 1.03, '辽宁': 1.01, '吉林': 1.02,
            '黑龙江': 1.01, '山西': 1.04, '重庆': 1.02,
            '广西': 1.01, '云南': 1.02, '贵州': 1.03,
            '海南': 0.98, '甘肃': 1.01, '青海': 0.99,
            '宁夏': 0.98, '新疆': 0.99, '西藏': 0.95,
            '内蒙古': 1.01
        },
        'YEAR_FLUCTUATION': (-0.03, 0.03),  # 年度波动范围
        'SCORE_RANGE': (200, 750)  # 分数范围
    }
    
    # 院校类型映射
    UNIVERSITY_TYPES = {
        '综合类': ['综合大学', '师范大学'],
        '理工类': ['理工大学', '工业大学', '科技大学', '工程大学'],
        '师范类': ['师范大学', '师范学院', '教育大学'],
        '财经类': ['财经大学', '经济大学', '商学院', '金融大学'],
        '医科类': ['医科大学', '医学院', '中医药大学'],
        '农林类': ['农业大学', '林业大学', '农学院'],
        '政法类': ['政法大学', '法学院', '公安大学'],
        '艺术类': ['艺术大学', '艺术学院', '音乐学院', '美术学院'],
        '体育类': ['体育大学', '体育学院'],
        '民族类': ['民族大学', '民族学院'],
        '军事类': ['军事大学', '军事学院', '国防大学']
    }
    
    # 专业就业数据
    MAJOR_EMPLOYMENT = {
        '计算机科学与技术': {
            'employment_rate': 96.8,
            'average_salary': 12500,
            'career_prospects': '优秀',
            'industry_growth': '高增长'
        },
        '软件工程': {
            'employment_rate': 95.6,
            'average_salary': 11800,
            'career_prospects': '优秀',
            'industry_growth': '高增长'
        },
        '人工智能': {
            'employment_rate': 94.2,
            'average_salary': 15200,
            'career_prospects': '极佳',
            'industry_growth': '爆发增长'
        },
        '数据科学与大数据技术': {
            'employment_rate': 93.5,
            'average_salary': 13800,
            'career_prospects': '优秀',
            'industry_growth': '高增长'
        },
        '金融学': {
            'employment_rate': 88.5,
            'average_salary': 9800,
            'career_prospects': '良好',
            'industry_growth': '稳定增长'
        },
        '临床医学': {
            'employment_rate': 92.1,
            'average_salary': 8600,
            'career_prospects': '稳定',
            'industry_growth': '稳定增长'
        },
        '电气工程及其自动化': {
            'employment_rate': 91.3,
            'average_salary': 10200,
            'career_prospects': '良好',
            'industry_growth': '稳定增长'
        },
        '机械工程': {
            'employment_rate': 89.7,
            'average_salary': 8900,
            'career_prospects': '良好',
            'industry_growth': '中等增长'
        }
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取完整配置"""
        return {
            'data_sources': cls.DATA_SOURCES,
            'database': cls.DATABASE,
            'crawler': cls.CRAWLER,
            'app': cls.APP,
            'logging': cls.LOGGING,
            'score_calculation': cls.SCORE_CALCULATION,
            'university_types': cls.UNIVERSITY_TYPES,
            'major_employment': cls.MAJOR_EMPLOYMENT
        }
    
    @classmethod
    def get_data_source_config(cls) -> Dict[str, str]:
        """获取数据源配置"""
        return {
            'gugudata_key': cls.DATA_SOURCES['GUGUDATA_KEY'],
            'ayshuju_key': cls.DATA_SOURCES['AYSHUJU_KEY']
        }

# 环境变量配置示例（.env文件格式）
ENV_EXAMPLE = """
# 数据源API密钥
GUGUDATA_KEY=your-gugudata-api-key
AYSHUJU_KEY=your-ayshuju-api-key

# 应用密钥
SECRET_KEY=your-secret-key-here

# 数据库配置（如果使用外部数据库）
DATABASE_URL=your-database-url

# 其他配置
DEBUG=True
LOG_LEVEL=INFO
"""

def create_env_file():
    """创建.env示例文件"""
    if not os.path.exists('.env.example'):
        with open('.env.example', 'w', encoding='utf-8') as f:
            f.write(ENV_EXAMPLE)
        print("已创建 .env.example 文件，请复制为 .env 并填入真实的API密钥")

if __name__ == "__main__":
    create_env_file() 