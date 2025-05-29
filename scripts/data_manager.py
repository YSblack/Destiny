#!/usr/bin/env python3
"""
高考志愿填报系统 - 数据管理脚本
用于更新院校数据、生成统计报告、数据维护等
"""

import sys
import os
import argparse
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_crawler import UniversityDataCrawler, update_university_database
from models.university_data import UniversityDatabase

class DataManager:
    """数据管理器"""
    
    def __init__(self):
        self.crawler = UniversityDataCrawler()
        self.db = None
    
    def update_all_data(self):
        """更新所有院校数据"""
        print("=" * 60)
        print("开始更新院校数据...")
        print("=" * 60)
        
        try:
            # 备份现有数据
            self._backup_existing_data()
            
            # 获取最新数据
            latest_data = update_university_database()
            
            print(f"\n✅ 数据更新完成！")
            print(f"   共获取 {len(latest_data['universities'])} 所院校数据")
            print(f"   录取分数线覆盖 {len(latest_data['admission_scores'])} 所院校")
            print(f"   专业排名数据 {len(latest_data['majors'])} 个专业")
            
            # 生成更新报告
            self._generate_update_report(latest_data)
            
            return True
            
        except Exception as e:
            print(f"❌ 数据更新失败: {e}")
            return False
    
    def _backup_existing_data(self):
        """备份现有数据"""
        backup_file = f"university_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if os.path.exists("university_data.json"):
            try:
                with open("university_data.json", 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 已备份现有数据到: {backup_file}")
                
            except Exception as e:
                print(f"⚠️  备份数据时出现警告: {e}")
    
    def _generate_update_report(self, data):
        """生成更新报告"""
        report = {
            "update_time": datetime.now().isoformat(),
            "statistics": data.get('statistics', {}),
            "data_sources": {
                "universities": len(data['universities']),
                "admission_scores": len(data['admission_scores']),
                "majors": len(data['majors']),
                "rankings": len(data['rankings'])
            },
            "university_breakdown": {
                "985_211": len([u for u in data['universities'] if '985' in u.get('level', '')]),
                "double_first_class": len([u for u in data['universities'] if u.get('is_double_first_class')]),
                "total": len(data['universities'])
            }
        }
        
        report_file = f"update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 更新报告已生成: {report_file}")
            
            # 打印摘要
            print(f"\n📊 数据摘要:")
            print(f"   985/211院校: {report['university_breakdown']['985_211']} 所")
            print(f"   双一流院校: {report['university_breakdown']['double_first_class']} 所")
            print(f"   总院校数量: {report['university_breakdown']['total']} 所")
            
        except Exception as e:
            print(f"⚠️  生成报告时出现警告: {e}")
    
    def validate_data(self):
        """验证数据完整性"""
        print("=" * 60)
        print("开始验证数据完整性...")
        print("=" * 60)
        
        try:
            self.db = UniversityDatabase()
            
            issues = []
            warnings = []
            
            # 验证院校数据
            universities = self.db.universities
            
            if not universities:
                issues.append("未找到任何院校数据")
                return False
            
            print(f"✅ 发现 {len(universities)} 所院校")
            
            # 验证必要字段
            required_fields = ['id', 'name', 'province', 'type', 'level', 'ranking']
            
            for uni in universities:
                for field in required_fields:
                    if field not in uni or uni[field] is None:
                        issues.append(f"院校 {uni.get('name', 'Unknown')} 缺少字段: {field}")
            
            # 验证录取分数线数据
            score_coverage = len(self.db.admission_scores)
            if score_coverage < len(universities) * 0.8:
                warnings.append(f"录取分数线覆盖率较低: {score_coverage}/{len(universities)}")
            
            # 验证排名数据
            rankings = [uni.get('ranking', 999) for uni in universities]
            if len(set(rankings)) != len(rankings):
                warnings.append("发现重复的院校排名")
            
            # 打印验证结果
            if issues:
                print(f"\n❌ 发现 {len(issues)} 个严重问题:")
                for issue in issues[:10]:  # 最多显示10个
                    print(f"   - {issue}")
                if len(issues) > 10:
                    print(f"   ... 还有 {len(issues) - 10} 个问题")
                return False
            
            if warnings:
                print(f"\n⚠️  发现 {len(warnings)} 个警告:")
                for warning in warnings:
                    print(f"   - {warning}")
            
            print(f"\n✅ 数据验证完成，总体状况良好")
            return True
            
        except Exception as e:
            print(f"❌ 数据验证失败: {e}")
            return False
    
    def generate_statistics(self):
        """生成统计信息"""
        print("=" * 60)
        print("生成详细统计信息...")
        print("=" * 60)
        
        try:
            if not self.db:
                self.db = UniversityDatabase()
            
            stats = self.db.get_statistics()
            
            print(f"\n📊 院校统计:")
            print(f"   总院校数量: {stats.get('total_universities', 0)}")
            
            # 按层次统计
            by_level = stats.get('by_level', {})
            if by_level:
                print(f"\n   按办学层次:")
                for level, count in sorted(by_level.items()):
                    print(f"     {level}: {count} 所")
            
            # 按类型统计
            by_type = stats.get('by_type', {})
            if by_type:
                print(f"\n   按院校类型:")
                for type_name, count in sorted(by_type.items()):
                    print(f"     {type_name}: {count} 所")
            
            # 按省份统计
            by_province = stats.get('by_province', {})
            if by_province:
                print(f"\n   按省份分布 (前10名):")
                sorted_provinces = sorted(by_province.items(), key=lambda x: x[1], reverse=True)
                for province, count in sorted_provinces[:10]:
                    print(f"     {province}: {count} 所")
            
            # 获取顶尖院校
            top_unis = self.db.get_top_universities(limit=10)
            if top_unis:
                print(f"\n   顶尖院校 (前10名):")
                for uni in top_unis:
                    print(f"     {uni['ranking']:2d}. {uni['name']} ({uni['province']})")
            
            # 双一流院校
            double_first_class = self.db.get_double_first_class_universities()
            print(f"\n   双一流院校: {len(double_first_class)} 所")
            
            return True
            
        except Exception as e:
            print(f"❌ 生成统计信息失败: {e}")
            return False
    
    def export_data(self, format_type='json'):
        """导出数据"""
        print("=" * 60)
        print(f"导出数据 (格式: {format_type})...")
        print("=" * 60)
        
        try:
            if not self.db:
                self.db = UniversityDatabase()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format_type.lower() == 'json':
                filename = f"university_data_export_{timestamp}.json"
                success = self.db.export_data(filename)
                
            elif format_type.lower() == 'excel':
                import pandas as pd
                
                filename = f"university_data_export_{timestamp}.xlsx"
                
                # 创建Excel文件
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    # 院校基本信息
                    df_unis = pd.DataFrame(self.db.universities)
                    df_unis.to_excel(writer, sheet_name='院校信息', index=False)
                    
                    # 录取分数线
                    scores_data = []
                    for uni_id, scores in self.db.admission_scores.items():
                        for year, year_scores in scores.items():
                            for subject, score in year_scores.items():
                                scores_data.append({
                                    'university_id': uni_id,
                                    'year': year,
                                    'subject_type': subject,
                                    'score': score
                                })
                    
                    if scores_data:
                        df_scores = pd.DataFrame(scores_data)
                        df_scores.to_excel(writer, sheet_name='录取分数线', index=False)
                    
                    # 统计信息
                    stats = self.db.get_statistics()
                    if stats:
                        df_stats = pd.DataFrame([stats])
                        df_stats.to_excel(writer, sheet_name='统计信息', index=False)
                
                success = True
                
            else:
                print(f"❌ 不支持的导出格式: {format_type}")
                return False
            
            if success:
                print(f"✅ 数据导出成功: {filename}")
                return True
            else:
                print(f"❌ 数据导出失败")
                return False
                
        except Exception as e:
            print(f"❌ 导出数据时出错: {e}")
            return False
    
    def clean_old_files(self, days=7):
        """清理旧文件"""
        print("=" * 60)
        print(f"清理 {days} 天前的旧文件...")
        print("=" * 60)
        
        import glob
        from datetime import datetime, timedelta
        
        patterns = [
            "university_data_backup_*.json",
            "update_report_*.json",
            "university_data_export_*.json",
            "university_data_export_*.xlsx"
        ]
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        cleaned_count += 1
                        print(f"   删除: {file_path}")
                except Exception as e:
                    print(f"   删除失败 {file_path}: {e}")
        
        print(f"\n✅ 清理完成，删除了 {cleaned_count} 个文件")
        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='高考志愿填报系统 - 数据管理工具')
    
    parser.add_argument('command', choices=[
        'update', 'validate', 'stats', 'export', 'clean', 'all'
    ], help='执行的命令')
    
    parser.add_argument('--format', choices=['json', 'excel'], default='json',
                       help='导出格式 (仅用于export命令)')
    
    parser.add_argument('--days', type=int, default=7,
                       help='保留天数 (仅用于clean命令)')
    
    args = parser.parse_args()
    
    manager = DataManager()
    
    print(f"\n🎓 高考志愿填报系统 - 数据管理工具")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"命令: {args.command}")
    
    success = True
    
    if args.command == 'update':
        success = manager.update_all_data()
        
    elif args.command == 'validate':
        success = manager.validate_data()
        
    elif args.command == 'stats':
        success = manager.generate_statistics()
        
    elif args.command == 'export':
        success = manager.export_data(args.format)
        
    elif args.command == 'clean':
        success = manager.clean_old_files(args.days)
        
    elif args.command == 'all':
        success = (
            manager.update_all_data() and
            manager.validate_data() and
            manager.generate_statistics() and
            manager.export_data('json')
        )
    
    if success:
        print(f"\n🎉 命令 '{args.command}' 执行成功！")
        return 0
    else:
        print(f"\n💥 命令 '{args.command}' 执行失败！")
        return 1

if __name__ == '__main__':
    exit(main()) 