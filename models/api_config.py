#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API配置管理模块
用于管理各种AI服务的API密钥和配置
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)

class APIConfigManager:
    """API配置管理器"""
    
    def __init__(self):
        self.config_file = "data/api_config.json"
        self.config_db = "data/api_config.db"
        self.ensure_data_dir()
        self.init_config_db()
        self.config_cache = {}
        self.load_config()
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs("data", exist_ok=True)
    
    def init_config_db(self):
        """初始化配置数据库"""
        with sqlite3.connect(self.config_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_configs (
                    service_name TEXT PRIMARY KEY,
                    api_key TEXT,
                    api_url TEXT,
                    model_name TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入默认配置
            default_configs = [
                ('chatglm', '', 'https://open.bigmodel.cn/api/paas/v4/chat/completions', 'glm-4', 0),
                ('qwen', '', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', 'qwen-turbo', 0),
                ('local_llm', '', 'http://localhost:11434/api/generate', 'llama2:13b', 0),
                ('chatglm_reverse', '', '', 'chatglm-reverse', 1)
            ]
            
            for service_name, api_key, api_url, model_name, enabled in default_configs:
                conn.execute("""
                    INSERT OR IGNORE INTO api_configs 
                    (service_name, api_key, api_url, model_name, enabled)
                    VALUES (?, ?, ?, ?, ?)
                """, (service_name, api_key, api_url, model_name, enabled))
    
    def load_config(self):
        """加载配置"""
        try:
            with sqlite3.connect(self.config_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM api_configs")
                rows = cursor.fetchall()
                
                self.config_cache = {}
                for row in rows:
                    self.config_cache[row['service_name']] = {
                        'api_key': row['api_key'],
                        'api_url': row['api_url'],
                        'model_name': row['model_name'],
                        'enabled': bool(row['enabled']),
                        'updated_at': row['updated_at']
                    }
                
                logger.info(f"加载了{len(self.config_cache)}个API配置")
                
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.config_cache = {}
    
    def get_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取指定服务的配置"""
        return self.config_cache.get(service_name)
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        return self.config_cache.copy()
    
    def update_config(self, service_name: str, api_key: str = None, api_url: str = None, 
                     model_name: str = None, enabled: bool = None) -> bool:
        """更新配置"""
        try:
            # 构建更新语句
            updates = []
            params = []
            
            if api_key is not None:
                updates.append("api_key = ?")
                params.append(api_key)
            
            if api_url is not None:
                updates.append("api_url = ?")
                params.append(api_url)
            
            if model_name is not None:
                updates.append("model_name = ?")
                params.append(model_name)
            
            if enabled is not None:
                updates.append("enabled = ?")
                params.append(enabled)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(service_name)
            
            with sqlite3.connect(self.config_db) as conn:
                conn.execute(f"""
                    UPDATE api_configs 
                    SET {', '.join(updates)}
                    WHERE service_name = ?
                """, params)
                
                # 更新缓存
                if service_name not in self.config_cache:
                    self.config_cache[service_name] = {}
                
                if api_key is not None:
                    self.config_cache[service_name]['api_key'] = api_key
                if api_url is not None:
                    self.config_cache[service_name]['api_url'] = api_url
                if model_name is not None:
                    self.config_cache[service_name]['model_name'] = model_name
                if enabled is not None:
                    self.config_cache[service_name]['enabled'] = enabled
                
                self.config_cache[service_name]['updated_at'] = datetime.now().isoformat()
                
                logger.info(f"更新{service_name}配置成功")
                return True
                
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def delete_config(self, service_name: str) -> bool:
        """删除配置"""
        try:
            with sqlite3.connect(self.config_db) as conn:
                conn.execute("DELETE FROM api_configs WHERE service_name = ?", (service_name,))
                
                if service_name in self.config_cache:
                    del self.config_cache[service_name]
                
                logger.info(f"删除{service_name}配置成功")
                return True
                
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False
    
    def test_api_key(self, service_name: str) -> Dict[str, Any]:
        """测试API密钥"""
        config = self.get_config(service_name)
        if not config:
            return {'success': False, 'message': '配置不存在'}
        
        if not config['api_key']:
            return {'success': False, 'message': 'API密钥为空'}
        
        # 这里可以添加实际的API测试逻辑
        # 暂时返回基本验证结果
        if len(config['api_key']) < 10:
            return {'success': False, 'message': 'API密钥格式不正确'}
        
        return {'success': True, 'message': 'API密钥格式正确'}
    
    def get_masked_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取脱敏的配置信息"""
        config = self.get_config(service_name)
        if not config:
            return None
        
        masked_config = config.copy()
        api_key = config.get('api_key', '')
        
        if api_key:
            # 脱敏处理：只显示前4位和后4位
            if len(api_key) > 8:
                masked_config['api_key'] = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
            else:
                masked_config['api_key'] = '*' * len(api_key)
        
        return masked_config
    
    def get_all_masked_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有脱敏的配置"""
        masked_configs = {}
        for service_name in self.config_cache:
            masked_configs[service_name] = self.get_masked_config(service_name)
        return masked_configs
    
    def export_config(self) -> Dict[str, Any]:
        """导出配置（脱敏）"""
        return {
            'configs': self.get_all_masked_configs(),
            'export_time': datetime.now().isoformat(),
            'total_services': len(self.config_cache)
        }
    
    def get_enabled_services(self) -> List[str]:
        """获取启用的服务列表"""
        enabled_services = []
        for service_name, config in self.config_cache.items():
            if config.get('enabled', False):
                enabled_services.append(service_name)
        return enabled_services

# 全局实例
api_config_manager = APIConfigManager()

def get_api_config(service_name: str) -> Optional[Dict[str, Any]]:
    """获取API配置的便捷函数"""
    return api_config_manager.get_config(service_name)

def update_api_config(service_name: str, **kwargs) -> bool:
    """更新API配置的便捷函数"""
    return api_config_manager.update_config(service_name, **kwargs)

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    manager = APIConfigManager()
    
    # 测试更新配置
    manager.update_config('chatglm', api_key='test_key_123456789', enabled=True)
    
    # 测试获取配置
    config = manager.get_config('chatglm')
    print(f"ChatGLM配置: {config}")
    
    # 测试脱敏配置
    masked = manager.get_masked_config('chatglm')
    print(f"脱敏配置: {masked}")
    
    # 测试导出
    export = manager.export_config()
    print(f"导出配置: {export}") 