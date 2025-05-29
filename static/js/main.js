// 高考志愿填报系统 - 前端交互脚本

document.addEventListener('DOMContentLoaded', function() {
    // 初始化
    initializeApp();
    
    // 绑定事件
    bindEvents();
    
    // 加载省份数据
    loadProvinces();
});

function initializeApp() {
    console.log('高考志愿填报系统初始化完成');
}

function bindEvents() {
    // 文理科切换
    document.querySelectorAll('input[name="subject_type"]').forEach(radio => {
        radio.addEventListener('change', toggleSubjects);
    });
    
    // 表单提交
    document.getElementById('scoreForm').addEventListener('submit', handleScoreSubmit);
    
    // 搜索按钮
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchUniversities();
        }
    });
}

function toggleSubjects() {
    const selectedType = document.querySelector('input[name="subject_type"]:checked').value;
    const scienceSubjects = document.getElementById('science-subjects');
    const liberalSubjects = document.getElementById('liberal-subjects');
    
    if (selectedType === 'science') {
        scienceSubjects.style.display = 'block';
        liberalSubjects.style.display = 'none';
        // 清空文科科目
        ['politics', 'history', 'geography'].forEach(id => {
            document.getElementById(id).value = '';
        });
    } else {
        scienceSubjects.style.display = 'none';
        liberalSubjects.style.display = 'block';
        // 清空理科科目
        ['physics', 'chemistry', 'biology'].forEach(id => {
            document.getElementById(id).value = '';
        });
    }
}

async function handleScoreSubmit(e) {
    e.preventDefault();
    
    // 显示加载状态
    showLoading();
    
    try {
        // 收集表单数据
        const formData = collectFormData();
        
        // 计算总分并获取推荐
        const result = await calculateScore(formData);
        
        if (result.success) {
            // 显示分数分析
            displayScoreAnalysis(result);
            
            // 显示推荐结果
            displayRecommendationsFromResult(result);
        } else {
            showError('分数计算失败：' + result.error);
        }
    } catch (error) {
        showError('系统错误：' + error.message);
    } finally {
        hideLoading();
    }
}

function collectFormData() {
    const subjectType = document.querySelector('input[name="subject_type"]:checked').value;
    const province = document.getElementById('provinceInput').value;
    
    const formData = {
        chinese: parseFloat(document.getElementById('chinese').value) || 0,
        math: parseFloat(document.getElementById('math').value) || 0,
        english: parseFloat(document.getElementById('english').value) || 0,
        subject_type: subjectType,
        province: province,
        preferences: []
    };
    
    // 收集综合科目分数
    if (subjectType === 'science') {
        formData.physics = parseFloat(document.getElementById('physics').value) || 0;
        formData.chemistry = parseFloat(document.getElementById('chemistry').value) || 0;
        formData.biology = parseFloat(document.getElementById('biology').value) || 0;
    } else {
        formData.politics = parseFloat(document.getElementById('politics').value) || 0;
        formData.history = parseFloat(document.getElementById('history').value) || 0;
        formData.geography = parseFloat(document.getElementById('geography').value) || 0;
    }
    
    // 计算总分
    formData.total_score = formData.chinese + formData.math + formData.english;
    if (subjectType === 'science') {
        formData.total_score += formData.physics + formData.chemistry + formData.biology;
    } else {
        formData.total_score += formData.politics + formData.history + formData.geography;
    }
    
    // 收集偏好
    document.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
        formData.preferences.push(checkbox.value);
    });
    
    return formData;
}

async function calculateScore(formData) {
    // 验证必要字段
    if (!formData.province) {
        throw new Error('请选择所在省份');
    }
    
    if (formData.total_score <= 0) {
        throw new Error('请输入有效的考试成绩');
    }
    
    // 准备发送给后端的数据
    const requestData = {
        score: formData.total_score,
        province: formData.province,
        subject: formData.subject_type === 'science' ? '理科' : '文科',
        preferences: formData.preferences
    };
    
    const response = await fetch('/calculate_score', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    
    const result = await response.json();
    
    // 添加客户端计算的详细信息
    if (result.success) {
        result.total_score = formData.total_score;
        result.subject_type = formData.subject_type;
        result.detailed_scores = {
            chinese: formData.chinese,
            math: formData.math,
            english: formData.english,
            physics: formData.physics || 0,
            chemistry: formData.chemistry || 0,
            biology: formData.biology || 0,
            politics: formData.politics || 0,
            history: formData.history || 0,
            geography: formData.geography || 0
        };
    }
    
    return result;
}

function displayScoreAnalysis(scoreResult) {
    const analysisHtml = `
        <div class="score-analysis">
            <div class="score-display">${scoreResult.total_score} 分</div>
            <div class="text-center mb-3">
                <h5>您的高考总分</h5>
                <p class="mb-0">科目类型：${scoreResult.subject_type === 'science' ? '理科' : '文科'}</p>
            </div>
            
            <div class="analysis-grid">
                <div class="analysis-item">
                    <h5>分数水平</h5>
                    <div class="value" id="scoreLevel">分析中...</div>
                </div>
                <div class="analysis-item">
                    <h5>排名百分位</h5>
                    <div class="value" id="percentile">计算中...</div>
                </div>
                <div class="analysis-item">
                    <h5>一本线差距</h5>
                    <div class="value" id="tierDiff">对比中...</div>
                </div>
                <div class="analysis-item">
                    <h5>省内排名</h5>
                    <div class="value" id="provinceRank">估算中...</div>
                </div>
                <div class="analysis-item">
                    <h5>推荐可信度</h5>
                    <div class="value">95%</div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('scoreAnalysis').innerHTML = analysisHtml;
    document.getElementById('score-result').style.display = 'block';
    
    // 滚动到结果区域
    document.getElementById('score-result').scrollIntoView({ 
        behavior: 'smooth' 
    });
}

function displayRecommendationsFromResult(result) {
    displayRecommendations(result.recommendations, result.categorized);
    updateScoreAnalysisDetails(result.score_analysis);
}

function updateScoreAnalysisDetails(scoreAnalysis) {
    if (scoreAnalysis) {
        // 更新分数水平
        const scoreLevelElement = document.getElementById('scoreLevel');
        if (scoreLevelElement) {
            scoreLevelElement.textContent = scoreAnalysis.position_description || '计算中...';
        }
        
        // 更新排名百分位
        const percentileElement = document.getElementById('percentile');
        if (percentileElement) {
            percentileElement.textContent = `超越${scoreAnalysis.beat_percentage || 0}%考生`;
        }
        
        // 更新一本线差距
        const tierDiffElement = document.getElementById('tierDiff');
        if (tierDiffElement) {
            const tierDiff = scoreAnalysis.tier_difference || 0;
            if (tierDiff > 0) {
                tierDiffElement.textContent = `高出${tierDiff}分`;
                // 安全地设置className
                if (tierDiffElement.classList) {
                    tierDiffElement.classList.remove('text-danger', 'text-warning');
                    tierDiffElement.classList.add('text-success');
                } else {
                    tierDiffElement.className = 'text-success';
                }
            } else if (tierDiff < 0) {
                tierDiffElement.textContent = `低于${Math.abs(tierDiff)}分`;
                if (tierDiffElement.classList) {
                    tierDiffElement.classList.remove('text-success', 'text-warning');
                    tierDiffElement.classList.add('text-danger');
                } else {
                    tierDiffElement.className = 'text-danger';
                }
            } else {
                tierDiffElement.textContent = '刚好达线';
                if (tierDiffElement.classList) {
                    tierDiffElement.classList.remove('text-success', 'text-danger');
                    tierDiffElement.classList.add('text-warning');
                } else {
                    tierDiffElement.className = 'text-warning';
                }
            }
        }
        
        // 更新省内排名估算
        const rankElement = document.getElementById('provinceRank');
        if (rankElement && scoreAnalysis.estimated_rank) {
            rankElement.textContent = `省内约第${scoreAnalysis.estimated_rank}名`;
        }
    } else {
        // 如果没有分析数据，显示默认状态
        const elements = ['scoreLevel', 'percentile', 'tierDiff'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '计算中...';
            }
        });
    }
}

function displayRecommendations(recommendations, categorized) {
    // 处理推荐数据格式
    let allRecommendations = [];
    let stretchList = [];
    let stableList = [];
    let safeList = [];
    
    console.log('=== FINAL FIX displayRecommendations 调试 (v20250529v6-hotfix) ===');
    console.log('JavaScript版本: v20250529v6-hotfix');
    console.log('当前时间:', new Date().toISOString());
    console.log('原始推荐数据:', recommendations);
    console.log('推荐数据类型:', typeof recommendations);
    
    if (recommendations && typeof recommendations === 'object') {
        // 获取所有键名
        const keys = Object.keys(recommendations);
        console.log('所有键名:', keys);
        console.log('键名数量:', keys.length);
        
        // 基于API返回的确切顺序：['保底', '冲刺', '稳妥']
        // 直接按位置匹配，这是最可靠的方法
        if (keys.length === 3) {
            console.log('使用位置匹配（API顺序: 保底,冲刺,稳妥）');
            
            safeList = recommendations[keys[0]] || [];      // 第0位：保底
            stretchList = recommendations[keys[1]] || [];   // 第1位：冲刺  
            stableList = recommendations[keys[2]] || [];    // 第2位：稳妥
            
            console.log(`位置匹配结果:`);
            console.log(`  保底[${keys[0]}]: ${safeList.length}所`);
            console.log(`  冲刺[${keys[1]}]: ${stretchList.length}所`);
            console.log(`  稳妥[${keys[2]}]: ${stableList.length}所`);
        } else {
            // 备用方案：键名匹配
            console.log('使用键名匹配方案');
            
            for (let i = 0; i < keys.length; i++) {
                const key = keys[i];
                const keyStr = String(key);
                const data = recommendations[key];
                
                console.log(`键名[${i}]: "${keyStr}" (长度: ${keyStr.length}), 数据: ${Array.isArray(data) ? data.length : 'not array'} 项`);
                
                // 多种匹配方式
                if (keyStr === '冲刺' || keyStr.indexOf('冲刺') >= 0 || keyStr.includes('冲刺')) {
                    stretchList = Array.isArray(data) ? data : [];
                    console.log(`✓ 匹配到冲刺: ${stretchList.length}所`);
                }
                else if (keyStr === '稳妥' || keyStr.indexOf('稳妥') >= 0 || keyStr.includes('稳妥')) {
                    stableList = Array.isArray(data) ? data : [];
                    console.log(`✓ 匹配到稳妥: ${stableList.length}所`);
                }
                else if (keyStr === '保底' || keyStr.indexOf('保底') >= 0 || keyStr.includes('保底')) {
                    safeList = Array.isArray(data) ? data : [];
                    console.log(`✓ 匹配到保底: ${safeList.length}所`);
                }
            }
        }
        
        allRecommendations = [...stretchList, ...stableList, ...safeList];
        
        console.log('=== 最终结果 ===');
        console.log('冲刺院校:', stretchList.length);
        console.log('稳妥院校:', stableList.length);
        console.log('保底院校:', safeList.length);
        console.log('总计院校:', allRecommendations.length);
        
        if (stableList.length > 0) {
            console.log('稳妥院校示例:', stableList[0].university_name);
        } else {
            console.error('❌ 严重错误：稳妥院校列表为空！');
            console.error('调试信息：', {
                keys: keys,
                keysLength: keys.length,
                firstKeyData: recommendations[keys[0]] ? recommendations[keys[0]].length : 'null',
                secondKeyData: recommendations[keys[1]] ? recommendations[keys[1]].length : 'null', 
                thirdKeyData: recommendations[keys[2]] ? recommendations[keys[2]].length : 'null'
            });
        }
        
    } else if (categorized) {
        // 旧格式兼容
        stretchList = categorized['冲刺院校'] || [];
        stableList = categorized['稳妥院校'] || [];
        safeList = categorized['保底院校'] || [];
        
        allRecommendations = recommendations || [];
        console.log('使用旧格式数据');
    }
    
    // 显示推荐列表
    console.log('=== 开始显示推荐列表 ===');
    console.log('准备传递给stableRecommendationsList的数据长度:', stableList.length);
    
    displayRecommendationList('allRecommendationsList', allRecommendations);
    displayRecommendationList('stretchRecommendationsList', stretchList);
    displayRecommendationList('stableRecommendationsList', stableList);
    displayRecommendationList('safeRecommendationsList', safeList);
    
    // 显示推荐区域
    const recommendationsElement = document.getElementById('recommendations');
    if (recommendationsElement) {
        recommendationsElement.style.display = 'block';
        console.log('推荐区域已显示');
        
        // 滚动到推荐区域
        setTimeout(() => {
            recommendationsElement.scrollIntoView({ 
                behavior: 'smooth' 
            });
        }, 500);
    } else {
        console.error('推荐区域元素不存在');
    }
}

function displayRecommendationList(containerId, universities) {
    const container = document.getElementById(containerId);
    
    console.log(`=== displayRecommendationList 调试 ===`);
    console.log(`容器ID: ${containerId}`);
    console.log(`容器存在: ${!!container}`);
    console.log(`院校数量: ${universities ? universities.length : 0}`);
    console.log(`院校数据:`, universities);
    
    if (!container) {
        console.warn(`容器 ${containerId} 不存在`);
        return;
    }
    
    if (!universities || universities.length === 0) {
        console.log(`${containerId} 显示空状态`);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-university"></i>
                <p>暂无符合条件的院校推荐</p>
                <small class="text-muted">调试信息: 容器=${containerId}, 数据长度=${universities ? universities.length : 'null'}</small>
            </div>
        `;
        return;
    }
    
    console.log(`显示 ${containerId} 的 ${universities.length} 所院校`);
    
    try {
        const html = universities.map(uni => createUniversityCard(uni)).join('');
        container.innerHTML = html;
        console.log(`${containerId} 渲染成功`);
    } catch (error) {
        console.error(`显示推荐列表时出错 (${containerId}):`, error);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>显示推荐结果时出错</p>
                <small class="text-muted">错误: ${error.message}</small>
            </div>
        `;
    }
}

function createUniversityCard(university) {
    // 适配不同的数据格式
    const name = university.university_name || university.name || '未知院校';
    const universityData = university.university_data || university;
    
    const location = universityData.location || {};
    const province = location.province || universityData.province || '未知';
    const city = location.city || universityData.city || '';
    
    // 处理排名信息
    const ranking = university.ranking || universityData.ranking || {};
    let rankingText = '未排名';
    if (ranking && typeof ranking === 'object') {
        if (ranking.domestic_rank || ranking.domestic) {
            const rank = ranking.domestic_rank || ranking.domestic;
            rankingText = `国内第${rank}名`;
        } else if (ranking.qs_world_rank || ranking.qs_world) {
            const rank = ranking.qs_world_rank || ranking.qs_world;
            rankingText = `QS世界第${rank}名`;
        } else if (ranking.times_world_rank || ranking.times_world) {
            const rank = ranking.times_world_rank || ranking.times_world;
            rankingText = `泰晤士第${rank}名`;
        }
    } else if (ranking && typeof ranking === 'string') {
        rankingText = ranking;
    } else if (ranking && typeof ranking === 'number') {
        rankingText = `第${ranking}名`;
    }
    
    const category = universityData.category || '未知';
    const type = universityData.type || '未知';
    const establishmentYear = universityData.establishment_year || universityData.founded_year || '未知';
    
    const advantages = universityData.advantages || universityData.key_disciplines || [];
    const advantagesText = Array.isArray(advantages) ? advantages.join('、') : (advantages || '暂无信息');
    
    const minScore = university.min_score || '未知';
    const avgScore = university.avg_score || '未知';
    const probability = university.probability || '未知';
    const probabilityClass = university.category === '冲刺' ? 'warning' : 
                           university.category === '稳妥' ? 'success' : 'primary';
    
    return `
        <div class="university-card">
            <div class="university-header">
                <div class="university-name">${name}</div>
                <div class="probability-badge">
                    <span class="badge bg-${probabilityClass}">${university.category || '推荐'}</span>
                    <small class="text-muted">录取概率: ${probability}</small>
                </div>
            </div>
            
            <div class="university-info">
                <div class="info-item">
                    <i class="fas fa-map-marker-alt"></i>
                    ${province} ${city}
                </div>
                <div class="info-item">
                    <i class="fas fa-star"></i>
                    排名: ${rankingText}
                </div>
                <div class="info-item">
                    <i class="fas fa-calendar"></i>
                    建校: ${establishmentYear}年
                </div>
                ${universityData.is_double_first_class ? 
                    '<div class="info-item"><i class="fas fa-graduation-cap"></i>双一流</div>' : 
                    ''
                }
            </div>
            
            <div class="university-tags">
                <span class="tag tag-level">${category}</span>
                <span class="tag tag-type">${type}</span>
                <span class="tag tag-location">${province}</span>
            </div>
            
            <div class="score-info">
                <div class="score-item">
                    <span class="label">最低分:</span>
                    <span class="value">${minScore}分</span>
                </div>
                <div class="score-item">
                    <span class="label">平均分:</span>
                    <span class="value">${avgScore}分</span>
                </div>
            </div>
            
            <div class="advantages">
                <strong>优势学科：</strong>
                <span>${advantagesText}</span>
            </div>
            
            <div class="card-actions">
                <button class="btn btn-outline-primary btn-sm" onclick="showUniversityDetails('${name}')">
                    查看详情
                </button>
            </div>
        </div>
    `;
}

async function showUniversityDetails(universityId) {
    try {
        console.log('获取院校详情:', universityId);
        
        // URL编码处理中文院校名
        const encodedId = encodeURIComponent(universityId);
        const response = await fetch(`/university_details/${encodedId}`);
        const result = await response.json();
        
        if (result.success) {
            displayUniversityModal(result.university);
        } else {
            showError('获取院校详情失败：' + result.error);
        }
    } catch (error) {
        console.error('获取院校详情错误:', error);
        showError('获取院校详情时发生错误：' + error.message);
    }
}

function displayUniversityModal(university) {
    const modalTitle = document.getElementById('universityModalTitle');
    const modalBody = document.getElementById('universityModalBody');
    
    modalTitle.textContent = university.name;
    
    // 获取位置信息
    const location = university.location || {};
    const province = location.province || '未知';
    const city = location.city || '';
    
    // 获取排名信息
    const ranking = university.ranking || {};
    const domesticRank = ranking.domestic_rank || ranking.domestic || '未知';
    let rankingText = '未知';
    if (domesticRank !== '未知') {
        rankingText = `第${domesticRank}名`;
    }
    
    // 获取基本信息
    const category = university.category || '未知';
    const type = university.type || '未知';
    const establishmentYear = university.establishment_year || university.founded_year || '未知';
    const motto = university.motto || '未知';
    const website = university.website || '';
    const isDoubleFirstClass = university.is_double_first_class || false;
    
    // 获取设施信息
    const campusArea = university.campus_area || '未知';
    const studentCount = university.student_count || '未知';
    const facultyCount = university.faculty_count || '未知';
    const libraryBooks = university.library_books || '未知';
    const researchFunding = university.research_funding || '未知';
    const dormitoryInfo = university.dormitory_info || '暂无信息';
    const diningFacilities = university.dining_facilities || '暂无信息';
    const sportsFacilities = university.sports_facilities || '暂无信息';
    
    // 获取优势学科
    const advantages = university.advantages || university.key_disciplines || [];
    const advantagesText = Array.isArray(advantages) ? advantages.join('、') : (advantages || '暂无信息');
    
    // 获取描述
    const description = university.description || `${university.name}是一所具有悠久历史和深厚底蕴的高等学府。`;
    
    // 获取录取分数线信息
    const admissionScores = university.admission_scores || {};
    let scoresHtml = '';
    
    // 按年份和科目组织分数线数据
    const scoresByYear = {};
    Object.keys(admissionScores).forEach(key => {
        const scoreData = admissionScores[key];
        if (scoreData && scoreData.year && scoreData.province === '山西') {
            const year = scoreData.year;
            const subject = scoreData.subject;
            
            if (!scoresByYear[year]) {
                scoresByYear[year] = {};
            }
            scoresByYear[year][subject] = scoreData;
        }
    });
    
    // 生成分数线HTML
    const years = Object.keys(scoresByYear).sort((a, b) => b - a); // 按年份倒序
    years.forEach(year => {
        const yearData = scoresByYear[year];
        
        Object.keys(yearData).forEach(subject => {
            const scoreData = yearData[subject];
            const minScore = scoreData.min_score || '暂无分';
            const rank = scoreData.rank || '未知';
            const enrollment = scoreData.enrollment || '未知';
            const batch = scoreData.batch || '未知';
            
            scoresHtml += `
                <div class="score-item">
                    <strong>${year}${subject}：</strong>
                    <span class="score-value">${minScore}分</span>
                    ${rank !== '未知' ? `<br><small>位次: ${rank}</small>` : ''}
                    ${enrollment !== '未知' ? `<br><small>招生: ${enrollment}人</small>` : ''}
                    ${batch !== '未知' ? `<br><small>批次: ${batch}</small>` : ''}
                </div>
            `;
        });
    });
    
    if (!scoresHtml) {
        scoresHtml = '<div class="score-item">暂无录取分数线数据</div>';
    }
    
    // 获取专业信息
    const majors = university.majors || [];
    let majorsHtml = '';
    
    if (majors.length > 0) {
        majorsHtml = majors.map(major => `
            <div class="major-item">
                <div class="major-name">${major.name}</div>
                <div class="major-details">
                    ${major.enrollment ? `招生: ${major.enrollment}人` : ''}
                    ${major.score_difference ? ` | 分差: +${major.score_difference}分` : ''}
                    ${major.employment_rate ? ` | 就业率: ${major.employment_rate}%` : ''}
                </div>
                ${major.description ? `<div class="major-desc">${major.description}</div>` : ''}
            </div>
        `).join('');
    } else {
        majorsHtml = '<div class="no-data">暂无专业信息</div>';
    }
    
    // 获取就业信息
    const employment = university.employment || {};
    const employmentRate = employment.employment_rate || '未知';
    const averageSalary = employment.average_salary || '未知';
    const topEmployers = employment.top_employers || [];
    const careerProspects = employment.career_prospects || '暂无信息';
    
    // 获取数据来源
    const dataSources = university.data_sources || [];
    const dataSource = dataSources.length > 0 ? dataSources.join(', ') : (university.data_source || '模拟数据');
    
    modalBody.innerHTML = `
        <div class="university-details">
            <!-- 基本信息 -->
            <div class="detail-section">
                <h5><i class="fas fa-info-circle"></i> 基本信息</h5>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="label">院校类型：</span>
                        <span class="value">${type}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">办学层次：</span>
                        <span class="value">${category}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">所在地区：</span>
                        <span class="value">${province}${city ? ' ' + city : ''}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">建校时间：</span>
                        <span class="value">${establishmentYear}年</span>
                    </div>
                    <div class="info-item">
                        <span class="label">全国排名：</span>
                        <span class="value">${rankingText}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">是否双一流：</span>
                        <span class="value">${isDoubleFirstClass ? '是' : '否'}</span>
                    </div>
                    ${motto !== '未知' ? `
                    <div class="info-item full-width">
                        <span class="label">校训：</span>
                        <span class="value">${motto}</span>
                    </div>
                    ` : ''}
                    ${website ? `
                    <div class="info-item full-width">
                        <span class="label">官方网站：</span>
                        <span class="value"><a href="${website}" target="_blank">${website}</a></span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            <!-- 录取分数线 -->
            <div class="detail-section">
                <h5><i class="fas fa-chart-line"></i> 录取分数线 (山西地区)</h5>
                <div class="scores-grid">
                    ${scoresHtml}
                </div>
            </div>
            
            <!-- 就业信息 -->
            ${employment && Object.keys(employment).length > 0 ? `
            <div class="detail-section">
                <h5><i class="fas fa-briefcase"></i> 就业信息</h5>
                <div class="info-grid">
                    ${employmentRate !== '未知' ? `
                    <div class="info-item">
                        <span class="label">就业率：</span>
                        <span class="value">${employmentRate}%</span>
                    </div>
                    ` : ''}
                    ${averageSalary !== '未知' ? `
                    <div class="info-item">
                        <span class="label">平均薪资：</span>
                        <span class="value">${averageSalary}元/月</span>
                    </div>
                    ` : ''}
                    ${topEmployers.length > 0 ? `
                    <div class="info-item full-width">
                        <span class="label">主要雇主：</span>
                        <span class="value">${topEmployers.join('、')}</span>
                    </div>
                    ` : ''}
                    ${careerProspects !== '暂无信息' ? `
                    <div class="info-item full-width">
                        <span class="label">就业前景：</span>
                        <span class="value">${careerProspects}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            ` : ''}
            
            <!-- 招生专业信息 -->
            <div class="detail-section">
                <h5><i class="fas fa-graduation-cap"></i> 招生专业信息</h5>
                <div class="majors-container">
                    ${majorsHtml}
                </div>
            </div>
            
            <!-- 基本数据 -->
            <div class="detail-section">
                <h5><i class="fas fa-database"></i> 基本数据</h5>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="label">校园面积：</span>
                        <span class="value">${campusArea !== '未知' ? campusArea + '公顷' : '未知'}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">在校学生：</span>
                        <span class="value">${studentCount !== '未知' ? studentCount + '人' : '未知'}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">教职工数：</span>
                        <span class="value">${facultyCount !== '未知' ? facultyCount + '人' : '未知'}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">图书馆藏书：</span>
                        <span class="value">${libraryBooks !== '未知' ? libraryBooks + '万册' : '未知'}</span>
                    </div>
                    ${researchFunding !== '未知' ? `
                    <div class="info-item">
                        <span class="label">科研经费：</span>
                        <span class="value">${researchFunding}亿元</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            <!-- 校园设施 -->
            ${dormitoryInfo !== '暂无信息' || diningFacilities !== '暂无信息' || sportsFacilities !== '暂无信息' ? `
            <div class="detail-section">
                <h5><i class="fas fa-building"></i> 校园设施</h5>
                <div class="facilities-info">
                    ${dormitoryInfo !== '暂无信息' ? `
                    <div class="facility-item">
                        <strong>住宿条件：</strong>${dormitoryInfo}
                    </div>
                    ` : ''}
                    ${diningFacilities !== '暂无信息' ? `
                    <div class="facility-item">
                        <strong>餐饮设施：</strong>${diningFacilities}
                    </div>
                    ` : ''}
                    ${sportsFacilities !== '暂无信息' ? `
                    <div class="facility-item">
                        <strong>体育设施：</strong>${sportsFacilities}
                    </div>
                    ` : ''}
                </div>
            </div>
            ` : ''}
            
            <!-- 优势学科 -->
            <div class="detail-section">
                <h5><i class="fas fa-star"></i> 优势学科</h5>
                <div class="advantages-text">
                    ${advantagesText}
                </div>
            </div>
            
            <!-- 院校描述 -->
            <div class="detail-section">
                <h5><i class="fas fa-file-alt"></i> 院校描述</h5>
                <div class="description-text">
                    ${description}
                </div>
            </div>
            
            <!-- 数据来源 -->
            <div class="detail-section">
                <div class="data-source">
                    <small><i class="fas fa-info-circle"></i> 数据来源: ${dataSource}</small>
                </div>
            </div>
        </div>
    `;
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('universityDetailModal'));
    modal.show();
}

async function searchUniversities() {
    const query = document.getElementById('searchInput').value;
    const province = document.getElementById('provinceSelect').value;
    const type = document.getElementById('typeSelect').value;
    
    try {
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (province) params.append('province', province);
        if (type) params.append('type', type);
        
        const response = await fetch(`/search_universities?${params}`);
        const result = await response.json();
        
        if (result.success) {
            displaySearchResults(result.results);
        } else {
            showError('搜索失败：' + result.error);
        }
    } catch (error) {
        showError('搜索时发生错误：' + error.message);
    }
}

function displaySearchResults(universities) {
    const container = document.getElementById('searchResults');
    
    if (!universities || universities.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <p>未找到符合条件的院校</p>
            </div>
        `;
        return;
    }
    
    const html = universities.map(uni => `
        <div class="search-result-item" onclick="showUniversityDetails(${uni.id})">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${uni.name}</h6>
                    <small class="text-muted">
                        ${uni.province} ${uni.city} | ${uni.type} | ${uni.level} | 排名:${uni.ranking}
                    </small>
                    <p class="mt-2 mb-0">${uni.description}</p>
                </div>
                <div class="text-end">
                    ${uni.is_double_first_class ? '<span class="badge bg-warning">双一流</span>' : ''}
                    ${uni.has_graduate_program ? '<span class="badge bg-info">研究生</span>' : ''}
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

async function loadProvinces() {
    try {
        const response = await fetch('/provinces');
        const result = await response.json();
        
        if (result.success) {
            // 加载到分数计算表单的省份选择框
            const provinceInput = document.getElementById('provinceInput');
            if (provinceInput) {
                result.provinces.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province;
                    option.textContent = province;
                    provinceInput.appendChild(option);
                });
            }
            
            // 加载到院校搜索的省份选择框
            const provinceSelect = document.getElementById('provinceSelect');
            if (provinceSelect) {
                result.provinces.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province;
                    option.textContent = province;
                    provinceSelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('加载省份数据失败：', error);
    }
}

function getCurrentScore() {
    // 从页面获取当前输入的总分
    const chinese = parseFloat(document.getElementById('chinese').value) || 0;
    const math = parseFloat(document.getElementById('math').value) || 0;
    const english = parseFloat(document.getElementById('english').value) || 0;
    
    const subjectType = document.querySelector('input[name="subject_type"]:checked').value;
    let comprehensive = 0;
    
    if (subjectType === 'science') {
        comprehensive = (parseFloat(document.getElementById('physics').value) || 0) +
                      (parseFloat(document.getElementById('chemistry').value) || 0) +
                      (parseFloat(document.getElementById('biology').value) || 0);
    } else {
        comprehensive = (parseFloat(document.getElementById('politics').value) || 0) +
                       (parseFloat(document.getElementById('history').value) || 0) +
                       (parseFloat(document.getElementById('geography').value) || 0);
    }
    
    return chinese + math + english + comprehensive;
}

function showLoading() {
    // 可以添加全局加载指示器
    document.body.style.cursor = 'wait';
}

function hideLoading() {
    document.body.style.cursor = 'default';
}

function showError(message) {
    // 简单的错误提示，可以使用更好的UI组件
    alert(message);
}

// 平滑滚动到锚点
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// 数据同步功能
async function syncLatestData() {
    const syncBtn = document.getElementById('syncDataBtn');
    const originalHtml = syncBtn.innerHTML;
    
    try {
        // 更新按钮状态
        syncBtn.disabled = true;
        syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>同步中...';
        
        // 显示同步进度提示
        showSyncProgress('开始同步最新数据...');
        
        // 调用后端数据刷新接口
        const response = await fetch('/admin/refresh_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSyncProgress('数据同步成功！', 'success');
            
            // 显示同步结果
            if (result.results) {
                let message = '同步完成:\n';
                if (result.results.universities_updated !== undefined) {
                    message += `• 院校数据: ${result.results.universities_updated}所\n`;
                }
                if (result.results.scores_updated !== undefined) {
                    message += `• 分数线数据: ${result.results.scores_updated}条\n`;
                }
                if (result.results.rankings_updated !== undefined) {
                    message += `• 排名数据: ${result.results.rankings_updated}所\n`;
                }
                
                showSyncProgress(message, 'success');
            }
            
            // 3秒后隐藏进度提示
            setTimeout(hideSyncProgress, 3000);
            
        } else {
            showSyncProgress(`同步失败: ${result.error}`, 'error');
            setTimeout(hideSyncProgress, 5000);
        }
        
    } catch (error) {
        console.error('数据同步错误:', error);
        showSyncProgress(`同步失败: ${error.message}`, 'error');
        setTimeout(hideSyncProgress, 5000);
    } finally {
        // 恢复按钮状态
        syncBtn.disabled = false;
        syncBtn.innerHTML = originalHtml;
    }
}

function showSyncProgress(message, type = 'info') {
    // 移除现有的进度提示
    hideSyncProgress();
    
    // 创建进度提示框
    const progressDiv = document.createElement('div');
    progressDiv.id = 'syncProgress';
    progressDiv.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} position-fixed`;
    progressDiv.style.cssText = `
        top: 80px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        border-radius: 8px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    const iconClass = type === 'success' ? 'fa-check-circle' : 
                     type === 'error' ? 'fa-exclamation-triangle' : 
                     'fa-info-circle';
    
    progressDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas ${iconClass} me-2"></i>
            <div style="white-space: pre-line;">${message}</div>
        </div>
    `;
    
    document.body.appendChild(progressDiv);
    
    // 添加动画样式
    if (!document.querySelector('#syncProgressStyles')) {
        const style = document.createElement('style');
        style.id = 'syncProgressStyles';
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
}

function hideSyncProgress() {
    const progressDiv = document.getElementById('syncProgress');
    if (progressDiv) {
        progressDiv.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => {
            if (progressDiv.parentNode) {
                progressDiv.parentNode.removeChild(progressDiv);
            }
        }, 300);
    }
}

// 检查数据源状态
async function checkDataSourceStatus() {
    try {
        const response = await fetch('/admin/data_sources');
        const result = await response.json();
        
        if (result.success) {
            updateDataSourceIndicator(result.data);
        }
    } catch (error) {
        console.warn('无法检查数据源状态:', error);
    }
}

function updateDataSourceIndicator(status) {
    // 可以在页面上添加数据源状态指示器
    const syncBtn = document.getElementById('syncDataBtn');
    if (syncBtn && status) {
        const hasActiveSource = Object.values(status).some(s => s === true);
        if (!hasActiveSource) {
            syncBtn.title = '注意: 当前没有可用的在线数据源，将使用本地缓存数据';
            syncBtn.classList.add('btn-outline-warning');
            syncBtn.classList.remove('btn-outline-light');
        }
    }
}

// 页面加载时检查数据源状态
document.addEventListener('DOMContentLoaded', function() {
    // 延迟检查数据源状态，避免影响页面加载
    setTimeout(checkDataSourceStatus, 2000);
}); 