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
    console.log('🧮 总分计算调试:');
    console.log(`  语文: ${formData.chinese}`);
    console.log(`  数学: ${formData.math}`);
    console.log(`  英语: ${formData.english}`);
    console.log(`  主科合计: ${formData.total_score}`);
    
    if (subjectType === 'science') {
        console.log(`  物理: ${formData.physics}`);
        console.log(`  化学: ${formData.chemistry}`);
        console.log(`  生物: ${formData.biology}`);
        const comprehensive_score = formData.physics + formData.chemistry + formData.biology;
        console.log(`  理科综合小计: ${comprehensive_score}`);
        formData.total_score += comprehensive_score;
    } else {
        console.log(`  政治: ${formData.politics}`);
        console.log(`  历史: ${formData.history}`);
        console.log(`  地理: ${formData.geography}`);
        const comprehensive_score = formData.politics + formData.history + formData.geography;
        console.log(`  文科综合小计: ${comprehensive_score}`);
        formData.total_score += comprehensive_score;
    }
    
    console.log(`🎯 最终总分: ${formData.total_score}`);
    
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
    
    // 获取用户选择的省份和科目（用于优化显示）
    const userProvince = document.getElementById('provinceInput')?.value || null;
    const userSubject = document.querySelector('input[name="subject_type"]:checked')?.value === 'science' ? '理科' : '文科';
    
    console.log('开始处理推荐数据，用户省份:', userProvince, '用户科目:', userSubject);
    console.log('原始推荐数据:', recommendations);
    console.log('推荐数据类型:', typeof recommendations);
    
    if (recommendations && typeof recommendations === 'object') {
        // 获取所有键名
        const keys = Object.keys(recommendations);
        console.log('推荐数据键名:', keys);
        console.log('推荐数据完整结构:', JSON.stringify(recommendations, null, 2));
        
        // 改为直接键名匹配，避免位置依赖导致的错误
        if (keys.length === 3) {
            console.log('使用直接键名匹配（更可靠）');
            
            // 直接通过键名匹配，避免位置依赖
            stretchList = recommendations['冲刺'] || [];
            stableList = recommendations['稳妥'] || [];
            safeList = recommendations['保底'] || [];
            
            console.log(`键名匹配结果: 冲刺 ${stretchList.length}所, 稳妥 ${stableList.length}所, 保底 ${safeList.length}所`);
            console.log('冲刺数据:', stretchList.slice(0, 2)); // 显示前2个
            console.log('稳妥数据:', stableList.slice(0, 2)); // 显示前2个  
            console.log('保底数据:', safeList.slice(0, 2)); // 显示前2个
        } else {
            // 备用方案：键名匹配
            console.log('使用键名匹配方案');
            
            for (let i = 0; i < keys.length; i++) {
                const key = keys[i];
                const keyStr = String(key);
                const data = recommendations[key];
                
                console.log(`处理键 ${i}: ${key} (${keyStr}), 数据长度: ${Array.isArray(data) ? data.length : '非数组'}`);
                
                if (keyStr === '冲刺' || keyStr.indexOf('冲刺') >= 0) {
                    stretchList = Array.isArray(data) ? data : [];
                }
                else if (keyStr === '稳妥' || keyStr.indexOf('稳妥') >= 0) {
                    stableList = Array.isArray(data) ? data : [];
                }
                else if (keyStr === '保底' || keyStr.indexOf('保底') >= 0) {
                    safeList = Array.isArray(data) ? data : [];
                }
            }
        }
        
        allRecommendations = [...stretchList, ...stableList, ...safeList];
        
        console.log('最终结果: 冲刺', stretchList.length, '稳妥', stableList.length, '保底', safeList.length);
        
    } else if (categorized) {
        // 旧格式兼容
        stretchList = categorized['冲刺院校'] || [];
        stableList = categorized['稳妥院校'] || [];
        safeList = categorized['保底院校'] || [];
        
        allRecommendations = recommendations || [];
        console.log('使用旧格式数据');
    }
    
    // 显示推荐列表
    displayRecommendationList('allRecommendationsList', allRecommendations, userProvince, userSubject);
    displayRecommendationList('stretchRecommendationsList', stretchList, userProvince, userSubject);
    displayRecommendationList('stableRecommendationsList', stableList, userProvince, userSubject);
    displayRecommendationList('safeRecommendationsList', safeList, userProvince, userSubject);
    
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
        
        // 重要：在推荐结果显示后初始化省份选择器
        setTimeout(() => {
            console.log('开始初始化推荐卡片中的省份选择器...');
            initCardProvinceSelectors();
        }, 1000); // 稍微延迟确保DOM完全渲染
    }
}

function displayRecommendationList(containerId, universities, province, subject) {
    const container = document.getElementById(containerId);
    
    // 添加详细的调试信息
    console.log(`=== displayRecommendationList 调试信息 ===`);
    console.log(`容器ID: ${containerId}`);
    console.log(`容器是否存在: ${container ? '是' : '否'}`);
    console.log(`院校数据: `, universities);
    console.log(`院校数量: ${universities ? universities.length : 'null'}`);
    console.log(`数据类型: ${typeof universities}`);
    console.log(`是否为数组: ${Array.isArray(universities)}`);
    
    if (!container) {
        console.warn(`容器 ${containerId} 不存在`);
        return;
    }
    
    if (!universities || universities.length === 0) {
        console.log(`${containerId} 显示空状态 - 原因: ${!universities ? '数据为空' : '数组长度为0'}`);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-university"></i>
                <p>暂无符合条件的院校推荐</p>
                <small class="text-muted">调试信息: 容器=${containerId}, 数据长度=${universities ? universities.length : 'null'}</small>
            </div>
        `;
        return;
    }
    
    console.log(`准备显示 ${containerId} 的 ${universities.length} 所院校`);
    
    try {
        const html = universities.map(uni => createUniversityCard(uni, province, subject)).join('');
        container.innerHTML = html;
        console.log(`${containerId} 渲染成功，HTML长度: ${html.length}`);
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

// 生成省份录取分数线HTML的辅助函数
function generateProvinceScoresHtml(province, provinceData, isUserProvince, userSubject) {
    const years = Object.keys(provinceData).sort((a, b) => b - a); // 按年份倒序
    
    if (years.length === 0) {
        return '';
    }
    
    const provinceClass = isUserProvince ? 'user-province' : 'reference-province';
    const provinceLabel = isUserProvince ? province : `${province} (参考)`;
    
    let html = `<div class="province-scores ${provinceClass}">
        <h6 class="province-title">${provinceLabel}</h6>
        <div class="scores-grid">`;
    
    years.forEach(year => {
        const yearData = provinceData[year];
        
        // 优先显示用户选择的科目，然后显示其他科目
        const subjects = Object.keys(yearData);
        const sortedSubjects = subjects.sort((a, b) => {
            if (userSubject && a === userSubject) return -1;
            if (userSubject && b === userSubject) return 1;
            return a.localeCompare(b);
        });
        
        sortedSubjects.forEach(subject => {
            const scoreData = yearData[subject];
            const minScore = scoreData.min_score || scoreData.最低分 || '暂无';
            const rank = scoreData.rank || scoreData.位次 || '未知';
            const enrollment = scoreData.enrollment || scoreData.招生人数 || '未知';
            const batch = scoreData.batch || scoreData.录取批次 || '未知';
            
            const isUserSubject = userSubject && subject === userSubject;
            const subjectClass = isUserSubject ? 'user-subject' : '';
            
            html += `
                <div class="score-item ${subjectClass}">
                    <strong>${year}年${subject}：</strong>
                    <span class="score-value">${minScore}分</span>
                    ${rank !== '未知' ? `<br><small>位次: ${rank}</small>` : ''}
                    ${enrollment !== '未知' ? `<br><small>招生: ${enrollment}人</small>` : ''}
                    ${batch !== '未知' ? `<br><small>批次: ${batch}</small>` : ''}
                </div>
            `;
        });
    });
    
    html += `</div></div>`;
    return html;
}

function createUniversityCard(university, userProvince, userSubject) {
    // 适配不同的数据格式
    const name = university.university_name || university.name || '未知院校';
    const universityData = university.university_data || university;
    
    // 生成唯一ID避免冲突
    const uniqueId = name.replace(/[^\w]/g, '') + '_' + Math.random().toString(36).substr(2, 9);
    
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
    
    // 处理录取分数线数据来源信息
    const isReferenceData = university.is_reference_data || false;
    const referenceProvince = university.reference_province || null;
    let dataSourceInfo = '';
    
    if (isReferenceData && referenceProvince) {
        dataSourceInfo = `
            <div class="data-source-info">
                <small class="text-warning">
                    <i class="fas fa-info-circle"></i> 
                    基于${referenceProvince}省数据推算（本省数据暂缺）
                </small>
            </div>
        `;
    }
    
    // 获取录取分数线信息 - 优先显示用户选择的省份
    const admissionScores = university.admission_scores || universityData.admission_scores || {};
    let scoresHtml = '';

    // 按年份和省份组织分数线数据
    const scoresByProvinceYear = {};
    Object.keys(admissionScores).forEach(key => {
        const scoreData = admissionScores[key];
        if (scoreData && scoreData.year && scoreData.province) {
            const province = scoreData.province;
            const year = scoreData.year;
            const subject = scoreData.subject;
            
            if (!scoresByProvinceYear[province]) {
                scoresByProvinceYear[province] = {};
            }
            if (!scoresByProvinceYear[province][year]) {
                scoresByProvinceYear[province][year] = {};
            }
            scoresByProvinceYear[province][year][subject] = scoreData;
        }
    });

    // 生成分数线HTML - 优先显示用户省份
    const allProvinces = Object.keys(scoresByProvinceYear).sort();
    let userProvinceData = null;
    let otherProvincesData = [];
    
    // 分离用户省份和其他省份数据
    allProvinces.forEach(province => {
        if (userProvince && province === userProvince) {
            userProvinceData = { province, data: scoresByProvinceYear[province] };
        } else {
            otherProvincesData.push({ province, data: scoresByProvinceYear[province] });
        }
    });
    
    // 首先显示用户省份的录取分数线
    if (userProvinceData) {
        scoresHtml += generateProvinceScoresHtml(userProvinceData.province, userProvinceData.data, true, userSubject);
    }
    
    // 如果用户省份没有数据，显示第一个可用省份作为参考
    if (!userProvinceData && otherProvincesData.length > 0) {
        const firstProvince = otherProvincesData[0];
        scoresHtml += generateProvinceScoresHtml(firstProvince.province, firstProvince.data, false, userSubject);
        scoresHtml = `<div class="alert alert-warning alert-sm mt-2 mb-2"><small><i class="fas fa-exclamation-triangle"></i> 本省数据暂缺，显示${firstProvince.province}省数据作为参考</small></div>` + scoresHtml;
    }

    if (!scoresHtml) {
        scoresHtml = '<p class="text-muted">暂无录取分数线数据</p>';
    }
    
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
            
            ${dataSourceInfo}
            
            <!-- 录取分数线 -->
            <div class="detail-section">
                <h5><i class="fas fa-chart-line"></i> 录取分数线</h5>
                
                <!-- 省份选择器 -->
                <div class="province-selector mb-3">
                    <div class="row align-items-center">
                        <div class="col-md-4">
                            <label for="provinceSelect_${uniqueId}" class="form-label">选择查询省份：</label>
                            <select id="provinceSelect_${uniqueId}" class="form-select" onchange="loadScoresByProvinceCard('${name}', '${uniqueId}')">
                                <option value="">请选择省份</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label for="subjectSelect_${uniqueId}" class="form-label">科目类型：</label>
                            <select id="subjectSelect_${uniqueId}" class="form-select" onchange="loadScoresByProvinceCard('${name}', '${uniqueId}')">
                                <option value="理科">理科</option>
                                <option value="文科">文科</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label for="yearSelect_${uniqueId}" class="form-label">年份：</label>
                            <select id="yearSelect_${uniqueId}" class="form-select" onchange="loadScoresByProvinceCard('${name}', '${uniqueId}')">
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button class="btn btn-primary" onclick="loadScoresByProvinceCard('${name}', '${uniqueId}')" style="margin-top: 1.5rem;">
                                <i class="fas fa-search"></i> 查询
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="scores-container" id="scoresContainer_${uniqueId}">
                    <div class="text-center py-3">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">加载中...</span>
                        </div>
                        <p class="mt-2 text-muted">请选择省份查看录取分数线</p>
                    </div>
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
    
    // 生成唯一ID避免与推荐卡片中的元素冲突
    const modalUniqueId = 'modal_' + university.name.replace(/[^\w]/g, '') + '_' + Math.random().toString(36).substr(2, 9);
    
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
    
    // 获取录取分数线信息 - 只显示用户选择的省份
    const userProvince = document.getElementById('provinceInput')?.value || null;
    const userSubject = document.querySelector('input[name="subject_type"]:checked')?.value === 'science' ? '理科' : '文科';
    
    const admissionScores = university.admission_scores || {};
    let scoresHtml = '';
    
    // 按年份和省份组织分数线数据
    const scoresByProvinceYear = {};
    Object.keys(admissionScores).forEach(key => {
        const scoreData = admissionScores[key];
        if (scoreData && scoreData.year && scoreData.province) {
            const province = scoreData.province;
            const year = scoreData.year;
            const subject = scoreData.subject;
            
            if (!scoresByProvinceYear[province]) {
                scoresByProvinceYear[province] = {};
            }
            if (!scoresByProvinceYear[province][year]) {
                scoresByProvinceYear[province][year] = {};
            }
            scoresByProvinceYear[province][year][subject] = scoreData;
        }
    });
    
    // 只显示用户选择的省份
    if (userProvince && scoresByProvinceYear[userProvince]) {
        scoresHtml = generateProvinceScoresHtml(userProvince, scoresByProvinceYear[userProvince], true, userSubject);
    } else if (Object.keys(scoresByProvinceYear).length > 0) {
        // 如果用户省份没有数据，显示第一个可用省份
        const firstProvince = Object.keys(scoresByProvinceYear)[0];
        scoresHtml = generateProvinceScoresHtml(firstProvince, scoresByProvinceYear[firstProvince], false, userSubject);
        scoresHtml = `<div class="alert alert-info"><small>注意：本省数据暂缺，显示${firstProvince}省数据作为参考</small></div>` + scoresHtml;
    }
    
    if (!scoresHtml) {
        scoresHtml = '<div class="text-muted">暂无录取分数线数据</div>';
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
                <h5><i class="fas fa-chart-line"></i> 录取分数线</h5>
                
                <!-- 省份选择器 -->
                <div class="province-selector mb-3">
                    <div class="row align-items-center">
                        <div class="col-md-4">
                            <label for="provinceSelect_${modalUniqueId}" class="form-label">选择查询省份：</label>
                            <select id="provinceSelect_${modalUniqueId}" class="form-select" onchange="loadScoresByProvinceModal('${university.name}', '${modalUniqueId}')">
                                <option value="">请选择省份</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label for="subjectSelect_${modalUniqueId}" class="form-label">科目类型：</label>
                            <select id="subjectSelect_${modalUniqueId}" class="form-select" onchange="loadScoresByProvinceModal('${university.name}', '${modalUniqueId}')">
                                <option value="理科">理科</option>
                                <option value="文科">文科</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label for="yearSelect_${modalUniqueId}" class="form-label">年份：</label>
                            <select id="yearSelect_${modalUniqueId}" class="form-select" onchange="loadScoresByProvinceModal('${university.name}', '${modalUniqueId}')">
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button class="btn btn-primary" onclick="loadScoresByProvinceModal('${university.name}', '${modalUniqueId}')" style="margin-top: 1.5rem;">
                                <i class="fas fa-search"></i> 查询
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="scores-container" id="scoresContainer_${modalUniqueId}">
                    <div class="text-center py-3">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">加载中...</span>
                        </div>
                        <p class="mt-2 text-muted">请选择省份查看录取分数线</p>
                    </div>
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
    
    // 初始化省份选择器（包括动态年份）
    setTimeout(() => {
        initModalProvinceSelector(modalUniqueId);
    }, 100); // 稍微延迟确保DOM已更新
}

// 初始化模态框中的省份选择器
async function initModalProvinceSelector(modalUniqueId) {
    try {
        console.log('开始初始化模态框省份选择器:', modalUniqueId);
        const response = await fetch('/api/provinces');
        const result = await response.json();
        
        if (result.success) {
            const provinceSelect = document.getElementById(`provinceSelect_${modalUniqueId}`);
            const subjectSelect = document.getElementById(`subjectSelect_${modalUniqueId}`);
            const yearSelect = document.getElementById(`yearSelect_${modalUniqueId}`);
            const provinces = result.provinces;
            
            console.log('获取到省份数据:', provinces.length, '个省份');
            
            if (!provinceSelect || !subjectSelect || !yearSelect) {
                console.error('找不到模态框中的选择器元素');
                return;
            }
            
            // 清空现有选项
            provinceSelect.innerHTML = '<option value="">请选择省份</option>';
            
            // 添加省份选项
            provinces.forEach(province => {
                const option = document.createElement('option');
                option.value = province.name;
                option.textContent = province.full_name;
                provinceSelect.appendChild(option);
            });
            
            // 动态计算年份：当前年份的前一年为最新年份
            const currentYear = new Date().getFullYear();
            const latestYear = currentYear - 1; // 默认为当前年份-1年（如2025年则默认2024年）
            
            // 添加更多年份选项以支持历年分数线
            yearSelect.innerHTML = `
                <option value="${latestYear}">${latestYear}年（最新）</option>
                <option value="${latestYear - 1}">${latestYear - 1}年</option>
                <option value="${latestYear - 2}">${latestYear - 2}年</option>
                <option value="${latestYear - 3}">${latestYear - 3}年</option>
                <option value="${latestYear - 4}">${latestYear - 4}年</option>
            `;
            
            // 智能设置默认选择用户当前省份
            const userProvince = document.getElementById('provinceInput')?.value;
            const userSelectedProvince = localStorage.getItem('selectedProvince'); // 从本地存储获取上次选择
            
            if (userProvince && provinceSelect.querySelector(`option[value="${userProvince}"]`)) {
                provinceSelect.value = userProvince;
                localStorage.setItem('selectedProvince', userProvince); // 保存选择
                console.log('设置用户当前省份为默认:', userProvince);
            } else if (userSelectedProvince && provinceSelect.querySelector(`option[value="${userSelectedProvince}"]`)) {
                provinceSelect.value = userSelectedProvince;
                console.log('设置上次选择的省份为默认:', userSelectedProvince);
            }
            
            // 设置默认科目
            const userSubject = document.querySelector('input[name="subject_type"]:checked')?.value;
            const savedSubject = localStorage.getItem('selectedSubject');
            
            if (userSubject) {
                const subjectValue = userSubject === 'science' ? '理科' : '文科';
                subjectSelect.value = subjectValue;
                localStorage.setItem('selectedSubject', subjectValue);
            } else if (savedSubject && subjectSelect.querySelector(`option[value="${savedSubject}"]`)) {
                subjectSelect.value = savedSubject;
            } else {
                subjectSelect.value = '理科';
                localStorage.setItem('selectedSubject', '理科');
            }
            
            // 设置默认年份
            yearSelect.value = latestYear.toString();
            
            console.log(`模态框省份选择器初始化完成，默认年份: ${latestYear}年`);
            
            // 如果已经有省份选择，自动加载录取分数线
            if (provinceSelect.value) {
                // 获取大学名称
                const modalTitle = document.getElementById('universityModalTitle');
                const universityName = modalTitle ? modalTitle.textContent.trim() : '';
                if (universityName) {
                    console.log('自动加载录取分数线:', universityName, provinceSelect.value);
                    // 延迟一点点时间确保DOM完全更新
                    setTimeout(() => loadScoresByProvinceModal(universityName, modalUniqueId), 100);
                }
            }
            
            console.log('模态框省份选择器初始化完成');
        } else {
            console.error('API返回失败:', result.error);
            throw new Error(result.error || '获取省份列表失败');
        }
    } catch (error) {
        console.error('加载省份列表失败:', error);
        // 如果API失败，使用备用方案
        initModalProvinceSelectorFallback(modalUniqueId);
    }
}

// 备用方案：模态框省份选择器初始化
function initModalProvinceSelectorFallback(modalUniqueId) {
    const provinceSelect = document.getElementById(`provinceSelect_${modalUniqueId}`);
    const subjectSelect = document.getElementById(`subjectSelect_${modalUniqueId}`);
    const yearSelect = document.getElementById(`yearSelect_${modalUniqueId}`);
    
    if (!provinceSelect || !subjectSelect || !yearSelect) {
        console.error('找不到模态框中的选择器元素');
        return;
    }
    
    const backupProvinces = [
        {name: '北京', full_name: '北京市'}, {name: '天津', full_name: '天津市'},
        {name: '河北', full_name: '河北省'}, {name: '山西', full_name: '山西省'},
        {name: '内蒙古', full_name: '内蒙古自治区'}, {name: '辽宁', full_name: '辽宁省'},
        {name: '吉林', full_name: '吉林省'}, {name: '黑龙江', full_name: '黑龙江省'},
        {name: '上海', full_name: '上海市'}, {name: '江苏', full_name: '江苏省'},
        {name: '浙江', full_name: '浙江省'}, {name: '安徽', full_name: '安徽省'},
        {name: '福建', full_name: '福建省'}, {name: '江西', full_name: '江西省'},
        {name: '山东', full_name: '山东省'}, {name: '河南', full_name: '河南省'},
        {name: '湖北', full_name: '湖北省'}, {name: '湖南', full_name: '湖南省'},
        {name: '广东', full_name: '广东省'}, {name: '广西', full_name: '广西壮族自治区'},
        {name: '海南', full_name: '海南省'}, {name: '重庆', full_name: '重庆市'},
        {name: '四川', full_name: '四川省'}, {name: '贵州', full_name: '贵州省'},
        {name: '云南', full_name: '云南省'}, {name: '西藏', full_name: '西藏自治区'},
        {name: '陕西', full_name: '陕西省'}, {name: '甘肃', full_name: '甘肃省'},
        {name: '青海', full_name: '青海省'}, {name: '宁夏', full_name: '宁夏回族自治区'},
        {name: '新疆', full_name: '新疆维吾尔自治区'}
    ];
    
    provinceSelect.innerHTML = '<option value="">请选择省份</option>';
    backupProvinces.forEach(province => {
        const option = document.createElement('option');
        option.value = province.name;
        option.textContent = province.full_name;
        provinceSelect.appendChild(option);
    });
    
    // 动态计算年份：当前年份的前一年为最新年份
    const currentYear = new Date().getFullYear();
    const latestYear = currentYear - 1;
    
    // 添加年份选项
    yearSelect.innerHTML = `
        <option value="${latestYear}">${latestYear}年（最新）</option>
        <option value="${latestYear - 1}">${latestYear - 1}年</option>
        <option value="${latestYear - 2}">${latestYear - 2}年</option>
        <option value="${latestYear - 3}">${latestYear - 3}年</option>
        <option value="${latestYear - 4}">${latestYear - 4}年</option>
    `;
    
    // 智能设置默认选择用户当前省份
    const userProvince = document.getElementById('provinceInput')?.value;
    const userSelectedProvince = localStorage.getItem('selectedProvince');
    
    if (userProvince && provinceSelect.querySelector(`option[value="${userProvince}"]`)) {
        provinceSelect.value = userProvince;
        localStorage.setItem('selectedProvince', userProvince);
        console.log('备用方案设置用户当前省份为默认:', userProvince);
    } else if (userSelectedProvince && provinceSelect.querySelector(`option[value="${userSelectedProvince}"]`)) {
        provinceSelect.value = userSelectedProvince;
        console.log('备用方案设置上次选择的省份为默认:', userSelectedProvince);
    }
    
    // 设置默认科目
    const userSubject = document.querySelector('input[name="subject_type"]:checked')?.value;
    const savedSubject = localStorage.getItem('selectedSubject');
    
    if (userSubject) {
        const subjectValue = userSubject === 'science' ? '理科' : '文科';
        subjectSelect.value = subjectValue;
        localStorage.setItem('selectedSubject', subjectValue);
    } else if (savedSubject && subjectSelect.querySelector(`option[value="${savedSubject}"]`)) {
        subjectSelect.value = savedSubject;
    } else {
        subjectSelect.value = '理科';
        localStorage.setItem('selectedSubject', '理科');
    }
    
    // 设置默认年份
    yearSelect.value = latestYear.toString();
    
    console.log(`备用方案模态框初始化完成，默认年份: ${latestYear}年`);
    
    // 如果已经有省份选择，自动加载录取分数线
    if (provinceSelect.value) {
        const modalTitle = document.getElementById('universityModalTitle');
        const universityName = modalTitle ? modalTitle.textContent.trim() : '';
        if (universityName) {
            console.log('自动加载录取分数线:', universityName, provinceSelect.value);
            setTimeout(() => loadScoresByProvinceModal(universityName, modalUniqueId), 100);
        }
    }
    
    console.log('备用方案模态框省份选择器初始化完成');
}

// 根据省份加载录取分数线（用于模态框）
async function loadScoresByProvinceModal(universityName, modalUniqueId) {
    if (!universityName) return;
    
    const provinceSelect = document.getElementById(`provinceSelect_${modalUniqueId}`);
    const subjectSelect = document.getElementById(`subjectSelect_${modalUniqueId}`);
    const yearSelect = document.getElementById(`yearSelect_${modalUniqueId}`);
    const scoresContainer = document.getElementById(`scoresContainer_${modalUniqueId}`);
    
    if (!provinceSelect || !subjectSelect || !yearSelect || !scoresContainer) {
        console.error('找不到模态框中的相关元素:', modalUniqueId);
        return;
    }
    
    let selectedProvince = provinceSelect.value;
    const selectedSubject = subjectSelect.value;
    const selectedYear = parseInt(yearSelect.value);
    
    // 保存用户的选择到本地存储
    if (selectedProvince) {
        localStorage.setItem('selectedProvince', selectedProvince);
    }
    if (selectedSubject) {
        localStorage.setItem('selectedSubject', selectedSubject);
    }
    
    // 如果没有选择省份，尝试使用用户当前选择的省份
    if (!selectedProvince) {
        const userProvince = document.getElementById('provinceInput')?.value;
        if (userProvince) {
            selectedProvince = userProvince;
            provinceSelect.value = userProvince;
            localStorage.setItem('selectedProvince', userProvince);
        } else {
            scoresContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    请先选择省份
                </div>
            `;
            return;
        }
    }
    
    // 显示加载状态
    scoresContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2 text-muted">正在获取${universityName}在${selectedProvince}省的录取分数线...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/university_scores_by_province/${encodeURIComponent(universityName)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                province: selectedProvince,
                subject: selectedSubject,
                year: selectedYear
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            const scores = data.scores;
            
            // 显示分数线数据
            let scoresHtml = '';
            
            if (scores && scores.min_score) {
                scoresHtml = `
                    <div class="score-info-card">
                        <div class="score-header">
                            <h6 class="mb-0">${universityName} · ${selectedProvince}省 · ${selectedSubject}</h6>
                            <span class="badge bg-primary">${selectedYear}年</span>
                        </div>
                        <div class="score-content">
                            <div class="score-stats">
                                <div class="stat-item">
                                    <div class="stat-label">最低分</div>
                                    <div class="stat-value text-danger">${scores.min_score}分</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-label">平均分</div>
                                    <div class="stat-value text-warning">${scores.avg_score || '暂无'}分</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-label">最高分</div>
                                    <div class="stat-value text-success">${scores.max_score || '暂无'}分</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-label">位次</div>
                                    <div class="stat-value text-info">${scores.rank || '暂无'}</div>
                                </div>
                            </div>
                            
                            ${scores.batch ? `<div class="batch-info">录取批次：${scores.batch}</div>` : ''}
                            ${scores.enrollment ? `<div class="enrollment-info">招生人数：${scores.enrollment}人</div>` : ''}
                            
                            ${scores.major_scores && scores.major_scores.length > 0 ? `
                            <div class="major-scores mt-3">
                                <h6>专业分数线</h6>
                                <div class="major-scores-list">
                                    ${scores.major_scores.map(major => `
                                        <div class="major-score-item">
                                            <span class="major-name">${major.major_name}</span>
                                            <span class="major-score">最低分：${major.min_score}分</span>
                                            ${major.enrollment ? `<span class="major-enrollment">招生：${major.enrollment}人</span>` : ''}
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                            ` : ''}
                            
                            <div class="data-source mt-2">
                                <small class="text-muted">
                                    <i class="fas fa-info-circle"></i>
                                    数据来源：${scores.data_source || 'AI实时获取'} | 
                                    可信度：${Math.round((scores.confidence || 0.8) * 100)}% |
                                    更新时间：${data.last_updated ? new Date(data.last_updated).toLocaleString() : '刚刚'}
                                </small>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                scoresHtml = `
                    <div class="alert alert-info">
                        <i class="fas fa-exclamation-circle"></i>
                        暂无${universityName}在${selectedProvince}省${selectedYear}年${selectedSubject}的录取分数线数据
                    </div>
                `;
            }
            
            scoresContainer.innerHTML = scoresHtml;
            
        } else {
            scoresContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    获取录取分数线失败：${result.error}
                </div>
            `;
        }
        
    } catch (error) {
        console.error('获取录取分数线错误:', error);
        scoresContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                网络错误，请稍后重试：${error.message}
            </div>
        `;
    }
}

async function searchUniversities() {
    const query = document.getElementById('searchInput').value;
    const province = document.getElementById('searchProvinceSelect').value;
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
        <div class="search-result-item" onclick="showUniversityDetails('${uni.name}')">
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
        const response = await fetch('/api/provinces');
        const result = await response.json();
        
        if (result.success) {
            // 加载到分数计算表单的省份选择框
            const provinceInput = document.getElementById('provinceInput');
            if (provinceInput) {
                // 清空除了默认选项外的所有选项
                while (provinceInput.children.length > 1) {
                    provinceInput.removeChild(provinceInput.lastChild);
                }
                
                result.provinces.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province.name;
                    option.textContent = province.full_name;
                    provinceInput.appendChild(option);
                });
            }
            
            // 加载到院校搜索的省份选择框 (注意：搜索页面的ID可能不同)
            const searchProvinceSelect = document.getElementById('searchProvinceSelect');
            if (searchProvinceSelect) {
                // 清空除了默认选项外的所有选项
                while (searchProvinceSelect.children.length > 1) {
                    searchProvinceSelect.removeChild(searchProvinceSelect.lastChild);
                }
                
                result.provinces.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province.name;
                    option.textContent = province.full_name;
                    searchProvinceSelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('加载省份数据失败：', error);
        // 如果API失败，尝试使用备用方案
        const backupProvinces = [
            {name: '北京', full_name: '北京市'}, {name: '天津', full_name: '天津市'},
            {name: '河北', full_name: '河北省'}, {name: '山西', full_name: '山西省'},
            {name: '内蒙古', full_name: '内蒙古自治区'}, {name: '辽宁', full_name: '辽宁省'},
            {name: '吉林', full_name: '吉林省'}, {name: '黑龙江', full_name: '黑龙江省'},
            {name: '上海', full_name: '上海市'}, {name: '江苏', full_name: '江苏省'},
            {name: '浙江', full_name: '浙江省'}, {name: '安徽', full_name: '安徽省'},
            {name: '福建', full_name: '福建省'}, {name: '江西', full_name: '江西省'},
            {name: '山东', full_name: '山东省'}, {name: '河南', full_name: '河南省'},
            {name: '湖北', full_name: '湖北省'}, {name: '湖南', full_name: '湖南省'},
            {name: '广东', full_name: '广东省'}, {name: '广西', full_name: '广西壮族自治区'},
            {name: '海南', full_name: '海南省'}, {name: '重庆', full_name: '重庆市'},
            {name: '四川', full_name: '四川省'}, {name: '贵州', full_name: '贵州省'},
            {name: '云南', full_name: '云南省'}, {name: '西藏', full_name: '西藏自治区'},
            {name: '陕西', full_name: '陕西省'}, {name: '甘肃', full_name: '甘肃省'},
            {name: '青海', full_name: '青海省'}, {name: '宁夏', full_name: '宁夏回族自治区'},
            {name: '新疆', full_name: '新疆维吾尔自治区'}
        ];
        
        // 尝试加载到分数计算表单
        const provinceInput = document.getElementById('provinceInput');
        if (provinceInput) {
            provinceInput.innerHTML = '<option value="">请选择省份</option>';
            backupProvinces.forEach(province => {
                const option = document.createElement('option');
                option.value = province.name;
                option.textContent = province.full_name;
                provinceInput.appendChild(option);
            });
        }
        
        // 尝试加载到搜索选择框
        const searchProvinceSelect = document.getElementById('searchProvinceSelect');
        if (searchProvinceSelect) {
            searchProvinceSelect.innerHTML = '<option value="">选择省份</option>';
            backupProvinces.forEach(province => {
                const option = document.createElement('option');
                option.value = province.name;
                option.textContent = province.full_name;
                searchProvinceSelect.appendChild(option);
            });
        }
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

// ============== 录取分数线查询功能 ==============

// 初始化录取分数线查询功能
function initScoreQuery() {
    // 加载省份列表
    loadProvincesForQuery();
    
    // 加载院校列表
    loadUniversitiesForQuery();
    
    // 绑定表单提交事件
    const scoreQueryForm = document.getElementById('scoreQueryForm');
    if (scoreQueryForm) {
        scoreQueryForm.addEventListener('submit', handleScoreQuery);
    }
}

// 加载省份列表（用于查询）
async function loadProvincesForQuery() {
    try {
        const response = await fetch('/api/provinces');
        const result = await response.json();
        
        if (result.success) {
            const provinceSelect = document.getElementById('queryProvinceSelect');
            if (provinceSelect) {
                // 保留默认选项
                const defaultOption = provinceSelect.querySelector('option[value=""]');
                provinceSelect.innerHTML = '';
                if (defaultOption) {
                    provinceSelect.appendChild(defaultOption);
                }
                
                // 添加省份选项
                result.provinces.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province;
                    option.textContent = province;
                    provinceSelect.appendChild(option);
                });
                
                // 如果有保存的选择，自动设置
                const savedProvince = localStorage.getItem('querySelectedProvince');
                if (savedProvince) {
                    provinceSelect.value = savedProvince;
                }
            }
        }
    } catch (error) {
        console.error('加载省份列表失败:', error);
    }
}

// 加载院校列表（用于查询）
async function loadUniversitiesForQuery() {
    try {
        const response = await fetch('/search_universities');
        const result = await response.json();
        
        if (result.success) {
            const universityList = document.getElementById('universityList');
            if (universityList) {
                universityList.innerHTML = '';
                
                // 添加院校选项
                result.results.forEach(university => {
                    const option = document.createElement('option');
                    option.value = university.name;
                    universityList.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('加载院校列表失败:', error);
    }
}

// 处理录取分数线查询表单提交
async function handleScoreQuery(event) {
    event.preventDefault();
    
    const universityName = document.getElementById('universitySelect').value.trim();
    const province = document.getElementById('queryProvinceSelect').value;
    const subject = document.getElementById('querySubjectSelect').value;
    const year = parseInt(document.getElementById('queryYearSelect').value);
    
    // 验证输入
    if (!universityName) {
        showAlert('请输入院校名称', 'warning');
        return;
    }
    
    if (!province) {
        showAlert('请选择查询省份', 'warning');
        return;
    }
    
    // 保存用户选择
    localStorage.setItem('querySelectedProvince', province);
    localStorage.setItem('querySelectedSubject', subject);
    localStorage.setItem('querySelectedYear', year.toString());
    
    // 执行查询
    await performScoreQuery(universityName, province, subject, year);
}

// 执行录取分数线查询
async function performScoreQuery(universityName, province, subject, year) {
    const resultsContainer = document.getElementById('scoreQueryResults');
    
    // 显示加载状态
    resultsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-info" role="status">
                <span class="visually-hidden">查询中...</span>
            </div>
            <p class="mt-2 text-muted">正在查询 ${universityName} 在 ${province} 的 ${year} 年 ${subject} 录取分数线...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/university_scores_by_province/${encodeURIComponent(universityName)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                province: province,
                subject: subject,
                year: year
            })
        });
        
        const result = await response.json();
        
        if (result.success && result.data && result.data.scores) {
            displayScoreQueryResults(universityName, province, subject, year, result.data);
        } else {
            resultsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>暂无数据</strong><br>
                    未找到 ${universityName} 在 ${province} 省 ${year} 年 ${subject} 的录取分数线数据。<br>
                    <small class="text-muted">建议：尝试查询其他年份或省份，或检查院校名称是否正确。</small>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('查询录取分数线失败:', error);
        resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>查询失败</strong><br>
                网络错误，请稍后重试：${error.message}
            </div>
        `;
    }
}

// 显示录取分数线查询结果
function displayScoreQueryResults(universityName, province, subject, year, data) {
    const resultsContainer = document.getElementById('scoreQueryResults');
    const scores = data.scores;
    
    let resultHtml = `
        <div class="card border-info">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">
                    <i class="fas fa-university me-2"></i>
                    ${universityName} - ${province}省 ${year}年 ${subject} 录取分数线
                </h5>
            </div>
            <div class="card-body">
    `;
    
    if (scores && scores.min_score) {
        resultHtml += `
            <div class="row mb-4">
                <div class="col-md-3 text-center">
                    <div class="score-stat-card bg-danger text-white">
                        <div class="score-stat-label">最低分</div>
                        <div class="score-stat-value">${scores.min_score}</div>
                        <div class="score-stat-unit">分</div>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="score-stat-card bg-warning text-white">
                        <div class="score-stat-label">平均分</div>
                        <div class="score-stat-value">${scores.avg_score || '暂无'}</div>
                        <div class="score-stat-unit">${scores.avg_score ? '分' : ''}</div>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="score-stat-card bg-success text-white">
                        <div class="score-stat-label">最高分</div>
                        <div class="score-stat-value">${scores.max_score || '暂无'}</div>
                        <div class="score-stat-unit">${scores.max_score ? '分' : ''}</div>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="score-stat-card bg-info text-white">
                        <div class="score-stat-label">位次</div>
                        <div class="score-stat-value">${scores.rank || '暂无'}</div>
                        <div class="score-stat-unit">${scores.rank ? '名' : ''}</div>
                    </div>
                </div>
            </div>
        `;
        
        // 录取批次和招生人数
        if (scores.batch || scores.enrollment) {
            resultHtml += `
                <div class="row mb-3">
                    ${scores.batch ? `
                    <div class="col-md-6">
                        <div class="info-item">
                            <i class="fas fa-layer-group text-primary"></i>
                            <strong>录取批次：</strong>${scores.batch}
                        </div>
                    </div>
                    ` : ''}
                    ${scores.enrollment ? `
                    <div class="col-md-6">
                        <div class="info-item">
                            <i class="fas fa-users text-success"></i>
                            <strong>招生人数：</strong>${scores.enrollment} 人
                        </div>
                    </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 专业分数线
        if (scores.major_scores && scores.major_scores.length > 0) {
            resultHtml += `
                <div class="major-scores-section mt-4">
                    <h6 class="mb-3">
                        <i class="fas fa-graduation-cap text-primary"></i>
                        专业分数线详情
                    </h6>
                    <div class="table-responsive">
                        <table class="table table-striped table-sm">
                            <thead class="table-dark">
                                <tr>
                                    <th>专业名称</th>
                                    <th>最低分</th>
                                    <th>平均分</th>
                                    <th>招生人数</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${scores.major_scores.map(major => `
                                    <tr>
                                        <td>${major.major_name}</td>
                                        <td><span class="badge bg-danger">${major.min_score || '暂无'}</span></td>
                                        <td><span class="badge bg-warning">${major.avg_score || '暂无'}</span></td>
                                        <td>${major.enrollment || '暂无'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }
        
        // 数据来源信息
        resultHtml += `
            <div class="data-source-info mt-4 p-3 bg-light rounded">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <small class="text-muted">
                            <i class="fas fa-info-circle"></i>
                            <strong>数据来源：</strong>${scores.data_source || 'AI实时获取'} | 
                            <strong>可信度：</strong>${Math.round((scores.confidence || 0.8) * 100)}%
                        </small>
                    </div>
                    <div class="col-md-4 text-end">
                        <small class="text-muted">
                            <i class="fas fa-clock"></i>
                            ${data.last_updated ? new Date(data.last_updated).toLocaleString() : '刚刚更新'}
                        </small>
                    </div>
                </div>
            </div>
        `;
    } else {
        resultHtml += `
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                暂无具体分数线数据，建议尝试查询其他年份或联系院校招生办获取准确信息。
            </div>
        `;
    }
    
    resultHtml += `
            </div>
        </div>
        
        <!-- 操作按钮 -->
        <div class="mt-3 text-center">
            <button class="btn btn-outline-info" onclick="performScoreQuery('${universityName}', '${province}', '${subject}', ${year})">
                <i class="fas fa-redo"></i> 重新查询
            </button>
            <button class="btn btn-outline-secondary ms-2" onclick="showUniversityDetails('${universityName}')">
                <i class="fas fa-info-circle"></i> 查看院校详情
            </button>
        </div>
    `;
    
    resultsContainer.innerHTML = resultHtml;
}

// 在页面加载时初始化录取分数线查询功能
document.addEventListener('DOMContentLoaded', function() {
    initScoreQuery();
});

// 根据省份加载录取分数线（用于推荐卡片）
async function loadScoresByProvinceCard(universityName, uniqueId) {
    if (!universityName) return;
    
    const provinceSelect = document.getElementById(`provinceSelect_${uniqueId}`);
    const subjectSelect = document.getElementById(`subjectSelect_${uniqueId}`);
    const yearSelect = document.getElementById(`yearSelect_${uniqueId}`);
    const scoresContainer = document.getElementById(`scoresContainer_${uniqueId}`);
    
    if (!provinceSelect || !subjectSelect || !yearSelect || !scoresContainer) {
        console.error('找不到相关元素:', uniqueId);
        return;
    }
    
    let selectedProvince = provinceSelect.value;
    const selectedSubject = subjectSelect.value;
    const selectedYear = parseInt(yearSelect.value);
    
    // 保存用户的选择到本地存储
    if (selectedProvince) {
        localStorage.setItem('selectedProvince', selectedProvince);
    }
    if (selectedSubject) {
        localStorage.setItem('selectedSubject', selectedSubject);
    }
    
    // 如果没有选择省份，尝试使用用户当前选择的省份
    if (!selectedProvince) {
        const userProvince = document.getElementById('provinceInput')?.value;
        if (userProvince) {
            selectedProvince = userProvince;
            provinceSelect.value = userProvince;
            localStorage.setItem('selectedProvince', userProvince);
        } else {
            scoresContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    请先选择省份
                </div>
            `;
            return;
        }
    }
    
    // 显示加载状态
    scoresContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2 text-muted">正在获取${universityName}在${selectedProvince}省的录取分数线...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/university_scores_by_province/${encodeURIComponent(universityName)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                province: selectedProvince,
                subject: selectedSubject,
                year: selectedYear
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            const scores = data.scores;
            
            // 显示分数线数据
            let scoresHtml = '';
            
            if (scores && scores.min_score) {
                scoresHtml = `
                    <div class="score-info-card">
                        <div class="score-header">
                            <h6 class="mb-0">${universityName} · ${selectedProvince}省 · ${selectedSubject}</h6>
                            <span class="badge bg-primary">${selectedYear}年</span>
                        </div>
                        <div class="score-content">
                            <div class="score-stats">
                                <div class="stat-item">
                                    <div class="stat-label">最低分</div>
                                    <div class="stat-value text-danger">${scores.min_score}分</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-label">平均分</div>
                                    <div class="stat-value text-warning">${scores.avg_score || '暂无'}分</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-label">最高分</div>
                                    <div class="stat-value text-success">${scores.max_score || '暂无'}分</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-label">位次</div>
                                    <div class="stat-value text-info">${scores.rank || '暂无'}</div>
                                </div>
                            </div>
                            
                            ${scores.batch ? `<div class="batch-info">录取批次：${scores.batch}</div>` : ''}
                            ${scores.enrollment ? `<div class="enrollment-info">招生人数：${scores.enrollment}人</div>` : ''}
                            
                            <div class="data-source mt-2">
                                <small class="text-muted">
                                    <i class="fas fa-info-circle"></i>
                                    数据来源：${scores.data_source || 'AI实时获取'} | 
                                    可信度：${Math.round((scores.confidence || 0.8) * 100)}% |
                                    更新时间：${data.last_updated ? new Date(data.last_updated).toLocaleString() : '刚刚'}
                                </small>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                scoresHtml = `
                    <div class="alert alert-info">
                        <i class="fas fa-exclamation-circle"></i>
                        暂无${universityName}在${selectedProvince}省${selectedYear}年${selectedSubject}的录取分数线数据
                    </div>
                `;
            }
            
            scoresContainer.innerHTML = scoresHtml;
            
        } else {
            scoresContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    获取录取分数线失败：${result.error}
                </div>
            `;
        }
        
    } catch (error) {
        console.error('获取录取分数线错误:', error);
        scoresContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                网络错误，请稍后重试：${error.message}
            </div>
        `;
    }
}

// 初始化推荐卡片中的省份选择器
async function initCardProvinceSelectors() {
    try {
        const response = await fetch('/api/provinces');
        const result = await response.json();
        
        if (result.success) {
            const provinces = result.provinces;
            
            // 获取所有推荐卡片中的省份选择器
            const provinceSelectors = document.querySelectorAll('[id^="provinceSelect_"]');
            const yearSelectors = document.querySelectorAll('[id^="yearSelect_"]');
            const subjectSelectors = document.querySelectorAll('[id^="subjectSelect_"]');
            
            console.log(`找到 ${provinceSelectors.length} 个省份选择器需要初始化`);
            
            // 为每个省份选择器添加省份选项
            provinceSelectors.forEach(provinceSelect => {
                // 清空现有选项，保留默认选项
                const defaultOption = provinceSelect.querySelector('option[value=""]');
                provinceSelect.innerHTML = '';
                if (defaultOption) {
                    provinceSelect.appendChild(defaultOption);
                }
                
                // 添加省份选项
                provinces.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province.name;
                    option.textContent = province.full_name;
                    provinceSelect.appendChild(option);
                });
                
                // 设置默认选择
                const userProvince = document.getElementById('provinceInput')?.value;
                const savedProvince = localStorage.getItem('selectedProvince');
                
                if (userProvince && provinceSelect.querySelector(`option[value="${userProvince}"]`)) {
                    provinceSelect.value = userProvince;
                } else if (savedProvince && provinceSelect.querySelector(`option[value="${savedProvince}"]`)) {
                    provinceSelect.value = savedProvince;
                }
            });
            
            // 初始化年份选择器
            const currentYear = new Date().getFullYear();
            const latestYear = currentYear - 1;
            
            yearSelectors.forEach(yearSelect => {
                yearSelect.innerHTML = `
                    <option value="${latestYear}">${latestYear}年（最新）</option>
                    <option value="${latestYear - 1}">${latestYear - 1}年</option>
                    <option value="${latestYear - 2}">${latestYear - 2}年</option>
                    <option value="${latestYear - 3}">${latestYear - 3}年</option>
                    <option value="${latestYear - 4}">${latestYear - 4}年</option>
                `;
                yearSelect.value = latestYear.toString();
            });
            
            // 设置科目选择器默认值
            const userSubject = document.querySelector('input[name="subject_type"]:checked')?.value;
            const savedSubject = localStorage.getItem('selectedSubject');
            
            subjectSelectors.forEach(subjectSelect => {
                if (userSubject) {
                    const subjectValue = userSubject === 'science' ? '理科' : '文科';
                    subjectSelect.value = subjectValue;
                } else if (savedSubject) {
                    subjectSelect.value = savedSubject;
                } else {
                    subjectSelect.value = '理科';
                }
            });
            
            console.log('推荐卡片省份选择器初始化完成');
            
        } else {
            console.error('获取省份列表失败:', result.error);
            // 使用备用方案
            initCardProvinceSelectorsFallback();
        }
    } catch (error) {
        console.error('初始化省份选择器失败:', error);
        // 使用备用方案
        initCardProvinceSelectorsFallback();
    }
}

// 备用方案：使用硬编码的省份列表
function initCardProvinceSelectorsFallback() {
    const backupProvinces = [
        {name: '北京', full_name: '北京市'}, {name: '天津', full_name: '天津市'},
        {name: '河北', full_name: '河北省'}, {name: '山西', full_name: '山西省'},
        {name: '内蒙古', full_name: '内蒙古自治区'}, {name: '辽宁', full_name: '辽宁省'},
        {name: '吉林', full_name: '吉林省'}, {name: '黑龙江', full_name: '黑龙江省'},
        {name: '上海', full_name: '上海市'}, {name: '江苏', full_name: '江苏省'},
        {name: '浙江', full_name: '浙江省'}, {name: '安徽', full_name: '安徽省'},
        {name: '福建', full_name: '福建省'}, {name: '江西', full_name: '江西省'},
        {name: '山东', full_name: '山东省'}, {name: '河南', full_name: '河南省'},
        {name: '湖北', full_name: '湖北省'}, {name: '湖南', full_name: '湖南省'},
        {name: '广东', full_name: '广东省'}, {name: '广西', full_name: '广西壮族自治区'},
        {name: '海南', full_name: '海南省'}, {name: '重庆', full_name: '重庆市'},
        {name: '四川', full_name: '四川省'}, {name: '贵州', full_name: '贵州省'},
        {name: '云南', full_name: '云南省'}, {name: '西藏', full_name: '西藏自治区'},
        {name: '陕西', full_name: '陕西省'}, {name: '甘肃', full_name: '甘肃省'},
        {name: '青海', full_name: '青海省'}, {name: '宁夏', full_name: '宁夏回族自治区'},
        {name: '新疆', full_name: '新疆维吾尔自治区'}
    ];
    
    const provinceSelectors = document.querySelectorAll('[id^="provinceSelect_"]');
    const yearSelectors = document.querySelectorAll('[id^="yearSelect_"]');
    const subjectSelectors = document.querySelectorAll('[id^="subjectSelect_"]');
    
    // 初始化省份选择器
    provinceSelectors.forEach(provinceSelect => {
        provinceSelect.innerHTML = '<option value="">请选择省份</option>';
        backupProvinces.forEach(province => {
            const option = document.createElement('option');
            option.value = province.name;
            option.textContent = province.full_name;
            provinceSelect.appendChild(option);
        });
        
        // 设置默认选择
        const userProvince = document.getElementById('provinceInput')?.value;
        const savedProvince = localStorage.getItem('selectedProvince');
        
        if (userProvince && provinceSelect.querySelector(`option[value="${userProvince}"]`)) {
            provinceSelect.value = userProvince;
        } else if (savedProvince && provinceSelect.querySelector(`option[value="${savedProvince}"]`)) {
            provinceSelect.value = savedProvince;
        }
    });
    
    // 初始化年份选择器
    const currentYear = new Date().getFullYear();
    const latestYear = currentYear - 1;
    
    yearSelectors.forEach(yearSelect => {
        yearSelect.innerHTML = `
            <option value="${latestYear}">${latestYear}年（最新）</option>
            <option value="${latestYear - 1}">${latestYear - 1}年</option>
            <option value="${latestYear - 2}">${latestYear - 2}年</option>
            <option value="${latestYear - 3}">${latestYear - 3}年</option>
            <option value="${latestYear - 4}">${latestYear - 4}年</option>
        `;
        yearSelect.value = latestYear.toString();
    });
    
    // 设置科目选择器默认值
    const userSubject = document.querySelector('input[name="subject_type"]:checked')?.value;
    const savedSubject = localStorage.getItem('selectedSubject');
    
    subjectSelectors.forEach(subjectSelect => {
        if (userSubject) {
            const subjectValue = userSubject === 'science' ? '理科' : '文科';
            subjectSelect.value = subjectValue;
        } else if (savedSubject) {
            subjectSelect.value = savedSubject;
        } else {
            subjectSelect.value = '理科';
        }
    });
    
    console.log('备用方案：推荐卡片省份选择器初始化完成');
} 