# 实时AI数据获取系统使用指南

## 🎯 系统概述

高考志愿填报系统现已集成实时AI数据获取功能，能够动态获取院校分数线、录取信息和院校详情，为考生提供更全面、更及时的志愿填报建议。

## 🚀 主要功能

### 1. 实时数据获取
- **院校分数线**: 实时获取任意院校在各省份的历年录取分数线
- **院校信息**: 获取院校详细信息（排名、专业、就业等）
- **全国分数线**: 一次性获取某院校在全国所有省份的分数线
- **批量查询**: 支持同时查询多所院校的数据

### 2. 智能推荐增强
- **实时推荐**: 基于AI实时生成的推荐结果
- **数据融合**: 结合本地数据和AI数据提供更准确的推荐
- **多层次分类**: 冲刺、稳妥、保底三个层次的智能分类

### 3. 缓存优化
- **智能缓存**: 6小时有效期，避免重复查询
- **数据持久化**: SQLite数据库存储，支持离线访问
- **自动清理**: 定期清理过期数据，保持系统高效

## 🔧 配置指南

### 1. AI服务配置

编辑 `config/ai_config.yaml` 文件：

```yaml
ai_services:
  chatglm:
    enabled: true
    api_key: "你的智朴清言API密钥"
    
  qwen:
    enabled: true  
    api_key: "你的通义千问API密钥"
    
  local_llm:
    enabled: false  # 如有本地Ollama服务可启用
```

### 2. 获取API密钥

#### 智朴清言 (ChatGLM)
1. 访问 [https://chatglm.cn](https://chatglm.cn)
2. 注册账号并实名认证
3. 进入开发者控制台
4. 创建API密钥
5. 将密钥配置到 `ai_config.yaml`

#### 通义千问 (Qwen)
1. 访问 [https://dashscope.aliyuncs.com](https://dashscope.aliyuncs.com)
2. 注册阿里云账号
3. 开通通义千问服务
4. 获取API Key
5. 配置到系统中

## 📊 管理面板使用

### 访问管理面板
1. 启动系统后访问: `http://localhost:5010/admin/realtime`
2. 查看系统状态和缓存统计
3. 测试AI服务功能
4. 监控查询日志

### 主要功能
- **系统状态监控**: 实时查看缓存状态、AI服务状态
- **数据测试**: 测试单个院校查询和批量推荐
- **缓存管理**: 清理过期缓存，优化系统性能
- **查询日志**: 查看实时查询记录和错误日志

## 🔍 API接口说明

### 1. 单个院校数据查询
```bash
GET /api/realtime/university_data/{university_name}?province={省份}&subject={科目}&year={年份}
```

### 2. 批量院校分数线查询
```bash
POST /api/realtime/batch_scores
Content-Type: application/json

{
  "universities": ["清华大学", "北京大学"],
  "province": "北京",
  "subject": "理科",
  "year": 2023
}
```

### 3. 实时推荐
```bash
GET /api/realtime/recommendation?score={分数}&province={省份}&subject={科目}
```

### 4. 缓存状态
```bash
GET /api/realtime/cache_status
```

## 🎨 前端集成

### JavaScript调用示例

```javascript
// 获取实时推荐
async function getRealtimeRecommendation(score, province, subject) {
    const response = await fetch(`/api/realtime/recommendation?score=${score}&province=${province}&subject=${subject}`);
    const data = await response.json();
    
    if (data.success) {
        console.log('推荐结果:', data.recommendations);
        console.log('统计信息:', data.statistics);
    }
}

// 查询院校数据
async function getUniversityData(universityName, province, subject) {
    const response = await fetch(`/api/realtime/university_data/${encodeURIComponent(universityName)}?province=${province}&subject=${subject}`);
    const data = await response.json();
    
    if (data.success) {
        console.log('院校数据:', data.data);
    }
}
```

## 🔍 数据质量保证

### 1. 多重验证
- **API响应验证**: 检查AI返回的JSON格式和必要字段
- **数据范围验证**: 确保分数、排名等数据在合理范围内
- **逻辑一致性**: 验证最低分≤平均分≤最高分等逻辑关系

### 2. 备用机制
- **多AI服务**: 优先使用ChatGLM，备用通义千问和本地LLM
- **数据降级**: AI服务不可用时使用智能估算数据
- **缓存优先**: 优先使用缓存数据，减少API调用

### 3. 可信度标识
- **confidence字段**: 标识数据可信度(0-1)
- **数据来源**: 明确标识数据来源（AI生成/缓存/估算）
- **时间戳**: 记录数据获取时间

## 🚦 使用流程

### 1. 系统初始化
```bash
# 1. 安装依赖
pip install aiohttp pyyaml

# 2. 配置AI服务
编辑 config/ai_config.yaml

# 3. 启动系统
python app.py
```

### 2. 基本使用
1. 访问主页: `http://localhost:5010`
2. 输入考生信息获取推荐
3. 系统自动调用AI服务补充数据
4. 查看详细的院校推荐结果

### 3. 高级功能
1. 访问管理面板监控系统状态
2. 使用API接口进行自定义查询
3. 配置多个AI服务提高可用性
4. 定期清理缓存优化性能

## 📈 性能优化

### 1. 缓存策略
- **6小时缓存**: 平衡数据新鲜度和查询效率
- **SQLite存储**: 本地数据库，快速访问
- **自动清理**: 避免缓存数据过多影响性能

### 2. 并发控制
- **异步处理**: 使用asyncio提高并发性能
- **批量查询**: 减少单次查询开销
- **限速机制**: 避免API调用过于频繁

### 3. 错误处理
- **重试机制**: 失败时自动重试，指数退避
- **服务降级**: 主服务不可用时使用备用服务
- **异常捕获**: 完善的错误日志和用户提示

## 🛠️ 故障排除

### 常见问题

#### 1. AI服务连接失败
- 检查API密钥是否正确配置
- 确认网络连接正常
- 查看管理面板的服务状态

#### 2. 推荐结果为空
- 检查省份和科目参数是否正确
- 查看缓存是否有有效数据
- 确认AI服务是否正常响应

#### 3. 缓存数据异常
- 使用管理面板清理过期缓存
- 检查数据库文件权限
- 重启系统重新初始化

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看AI服务日志  
tail -f logs/ai_service.log
```

## 🔒 安全说明

### 1. API密钥安全
- 不要将API密钥提交到代码仓库
- 定期更换API密钥
- 使用环境变量存储敏感信息

### 2. 数据隐私
- 所有查询数据本地缓存，不上传第三方
- AI服务仅用于获取公开院校信息
- 用户个人信息不会发送给AI服务

### 3. 系统安全
- 定期更新依赖包
- 限制管理面板访问权限
- 监控异常查询行为

## 📞 技术支持

如遇到问题或需要技术支持，请：
1. 查看管理面板的错误日志
2. 检查配置文件是否正确
3. 参考本文档的故障排除部分
4. 提交详细的错误信息和日志

---

*最后更新时间: 2024年5月30日* 