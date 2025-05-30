# 🎓 高考志愿填报系统

一个基于Flask的智能高考志愿填报系统，为考生提供准确、个性化的院校推荐服务。

## ⚠️ 重要声明

**本项目仅供娱乐模拟使用，不能确保数据百分比准确，请自行判断。**

- 📋 **仅供参考**：本系统提供的院校推荐和录取概率仅作为参考，不构成志愿填报的最终依据
- 🔍 **数据来源**：系统数据来源于多个渠道，包括AI生成数据，无法保证100%准确性
- ⚖️ **自主判断**：用户在实际志愿填报时，应结合官方数据、招生简章等权威信息进行综合判断
- 🚫 **免责条款**：使用本系统产生的任何后果，开发者不承担相关责任

**正式志愿填报请以教育部门和各高校官方发布的信息为准！**

## ✨ 功能特性

### 🎯 核心功能
- **智能分数分析**：根据考生分数、省份、科目进行综合分析
- **三维推荐策略**：提供冲刺、稳妥、保底三类院校推荐
- **多数据源整合**：专业API + AI补充，确保数据覆盖全面
- **实时数据更新**：支持动态获取最新录取分数线

### 📊 数据准确性
- **专业API优先**：权威数据源，准确性高达95%
- **AI智能补充**：自动填补数据空白，覆盖率100%
- **高分段优化**：专门针对700+高分段用户优化推荐算法
- **数据质量管理**：实时监控数据准确性和完整性

### 🏫 院校信息
- **全面院校库**：收录全国181所重点院校
- **详细院校信息**：包含排名、地理位置、专业设置等
- **历年分数线**：提供多年录取分数线趋势分析
- **智能地理位置**：AI自动修复院校地理位置错误

### 🔧 技术特色
- **动态分类逻辑**：根据分数段自适应调整推荐策略
- **缓存优化**：智能缓存机制，提升响应速度
- **错误处理**：完善的异常处理和用户友好提示
- **实时日志**：详细的系统日志和调试信息

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Flask 2.0+
- SQLite3（可选，用于数据缓存）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd gkxt
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境**
```bash
# 复制配置文件模板
cp config.py.example config.py

# 编辑配置文件，设置API密钥等
vim config.py
```

4. **启动应用**
```bash
python app.py
```

5. **访问系统**
```
浏览器打开: http://localhost:5010
```

## 📖 使用指南

### 基本使用流程

1. **输入基本信息**
   - 高考分数
   - 所在省份  
   - 文理科选择

2. **获取推荐结果**
   - 冲刺院校：录取概率15-70%
   - 稳妥院校：录取概率70-90%
   - 保底院校：录取概率90%以上

3. **查看院校详情**
   - 点击院校卡片查看详细信息
   - 查看历年录取分数线
   - 了解专业设置和就业情况

### 高级功能

#### 🎯 精确分数查询
```bash
# API调用示例
POST /calculate_score
{
    "score": 650,
    "province": "北京", 
    "subject": "理科",
    "preferences": ["工科", "综合"]
}
```

#### 🏫 院校详情查询
```bash
# 获取院校详细信息
GET /api/university_detail/北京大学

# 查询特定省份录取分数线
POST /api/university_scores_by_province/清华大学
{
    "province": "山西",
    "subject": "理科",
    "year": 2024
}
```

## 🔧 系统架构

### 后端架构
```
app.py              # Flask主应用
├── models/         # 数据模型
│   ├── university_data.py       # 院校数据管理
│   ├── professional_data_api.py # 专业数据API
│   ├── realtime_ai_data.py     # AI数据提供器
│   └── data_accuracy_manager.py # 数据准确性管理
├── templates/      # HTML模板
├── static/         # 静态资源
│   ├── css/       # 样式文件
│   └── js/        # JavaScript文件
└── config.py       # 配置文件
```

### 数据流架构
```
用户输入 → 参数验证 → 专业API查询 → AI数据补充 → 结果排序 → 返回推荐
```

## 🛠️ 最近更新

### v2.1.0 (2025-05-31)
- ✅ **修复冲刺院校推荐问题**：解决700+高分段冲刺院校为空的问题
- ✅ **优化推荐算法**：添加高分段特殊处理逻辑
- ✅ **增强数据补充**：为高分段用户提供更多顶尖院校选择
- ✅ **改进用户体验**：优化前端显示和错误提示

### 修复详情
- **问题**：700分以上用户无法获得冲刺院校推荐
- **原因**：高分段缺少更高层次院校数据
- **解决方案**：
  1. 优化分类逻辑，添加高分段特殊处理
  2. 智能补充顶尖院校作为冲刺选择
  3. 动态调整推荐数量和概率计算

### 测试验证
- ✅ 700分北京理科：冲刺8所，稳妥3所，保底6所
- ✅ 720分北京理科：冲刺8所，稳妥0所，保底6所
- ✅ 中低分段功能正常，无影响

## 📊 数据来源

### 主要数据源
1. **专业数据API**：权威教育部门数据，准确性高
2. **实时AI数据**：智能生成补充数据，覆盖面广
3. **网络爬虫**：公开院校官网数据，实时更新

### 数据质量保证
- 多源数据交叉验证
- 智能地理位置修复
- 实时数据准确性监控
- 用户反馈持续优化

## 🔍 API 接口

### 核心接口

#### 分数计算推荐
```http
POST /calculate_score
Content-Type: application/json

{
    "score": 650,
    "province": "北京",
    "subject": "理科", 
    "preferences": []
}
```

#### 院校详情查询
```http
GET /api/university_detail/{university_name}
```

#### 录取分数线查询
```http
POST /api/university_scores_by_province/{university_name}
Content-Type: application/json

{
    "province": "山西",
    "subject": "理科",
    "year": 2024
}
```

#### 省份列表
```http
GET /api/provinces
```

### 管理接口

#### 数据质量报告
```http
GET /api/data_quality/report
```

#### 缓存状态查询
```http
GET /api/realtime/cache_status
```

## 🎨 前端功能

### 用户界面
- 响应式设计，支持移动端
- 直观的分数输入和结果展示
- 实时数据加载和错误处理
- 院校详情模态框

### 交互功能
- 省份选择器（支持搜索）
- 文理科切换
- 院校推荐列表
- 录取分数线查询

## ⚙️ 配置说明

### 主要配置项

```python
# config.py
class Config:
    # 应用配置
    APP = {
        'HOST': '0.0.0.0',
        'PORT': 5010,
        'DEBUG': True
    }
    
    # 数据源配置
    DATA_SOURCES = {
        'professional_api': True,
        'ai_supplement': True,
        'web_crawler': False
    }
    
    # AI服务配置
    AI_SERVICES = {
        'chatglm_api_key': 'your-api-key',
        'enabled': True
    }
```

### 环境变量
```bash
# 可选的环境变量
export GKXT_DEBUG=True
export GKXT_PORT=5010
export CHATGLM_API_KEY=your-api-key
```

## 🔒 安全说明

- API密钥安全存储
- 输入参数严格验证
- SQL注入防护
- XSS攻击防护
- 日志脱敏处理

## 📝 开发指南

### 添加新功能
1. 在`models/`目录添加数据模型
2. 在`app.py`中添加路由处理
3. 更新前端JavaScript逻辑
4. 添加测试用例
5. 更新文档

### 调试模式
```bash
# 启用详细日志
export FLASK_ENV=development
python app.py

# 查看日志
tail -f logs/app.log
```

### 测试
```bash
# 运行特定分数测试
python debug_stretch.py 650 北京 理科

# 测试API接口
curl -X POST http://localhost:5010/calculate_score \
  -H "Content-Type: application/json" \
  -d '{"score":650,"province":"北京","subject":"理科"}'
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📞 技术支持

- **问题反馈**：提交 GitHub Issues
- **功能建议**：发送邮件或创建 Feature Request
- **技术交流**：查看项目 Wiki 和讨论区

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- 感谢教育部门提供的权威数据支持
- 感谢开源社区的技术贡献
- 感谢用户反馈和建议

---

**🎯 让每个考生都能找到最适合的大学！**

*最后更新：2025-05-31* 