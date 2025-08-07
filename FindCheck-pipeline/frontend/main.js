const API_BASE_URL = ''; // Leave empty for relative paths

document.addEventListener('DOMContentLoaded', () => {
    const regulationSelect = document.getElementById('regulation-select');
    const companyInput = document.getElementById('company-input');
    const companyList = document.getElementById('company-list');
    const shareholderInputContainer = document.getElementById('shareholder-input-container');
    const shareholderInput = document.getElementById('shareholder-input');
    const shareholderList = document.getElementById('shareholder-list');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const runCheckButton = document.getElementById('run-check');
    const resultsSelect = document.getElementById('results-select');
    const loadResultButton = document.getElementById('load-result');
    const loadingSpinner = document.getElementById('loading');
    const graphContainer = document.getElementById('echarts-graph');
    const graphPlaceholder = document.getElementById('graph-placeholder');
    const mdReportSection = document.querySelector('.md-report-section');
    const reportPlaceholder = document.getElementById('report-placeholder');
    const reportLoading = document.getElementById('report-loading');
    const reportContent = document.getElementById('report-content');
    const downloadJsonButton = document.getElementById('download-json');
    const downloadMdButton = document.getElementById('download-md');

    let myChart = echarts.init(graphContainer);

    // 添加窗口大小调整事件监听器
    window.addEventListener('resize', () => {
        myChart.resize();
    });

    // 初始化时显示占位符
    graphPlaceholder.style.display = 'block';
    if (reportPlaceholder) reportPlaceholder.style.display = 'block';
    if (reportContent) reportContent.style.display = 'none';
    if (reportLoading) reportLoading.style.display = 'none';

    // 添加下载按钮事件监听器
    downloadJsonButton.addEventListener('click', () => {
        const resultPath = resultsSelect.value;
        if (!resultPath) {
            alert('请先选择或运行一个检查结果。');
            return;
        }
        window.open(`${API_BASE_URL}/api/download/json/${resultPath}`, '_blank');
    });

    downloadMdButton.addEventListener('click', () => {
        const resultPath = resultsSelect.value;
        if (!resultPath) {
            alert('请先选择或运行一个检查结果。');
            return;
        }
        window.open(`${API_BASE_URL}/api/download/report/${resultPath}`, '_blank');
    });

    // 加载法规列表
    fetch(`${API_BASE_URL}/api/regulations`)
        .then(response => response.json())
        .then(data => {
            data.regulations.forEach(reg => {
                const option = document.createElement('option');
                option.value = reg.id;
                option.textContent = reg.name;
                regulationSelect.appendChild(option);
            });
            
            // 如果有法规可选，则默认加载第一个法规的公司列表
            if (data.regulations.length > 0) {
                const defaultRegulationId = data.regulations[0].id;
                loadCompaniesForRegulation(defaultRegulationId);
                
                // 检查是否是regulation_08，如果是则显示股东输入框
                if (defaultRegulationId === "regulation_08") {
                    shareholderInputContainer.style.display = "block";
                    // 确保在下一个渲染周期添加可见类
                    setTimeout(() => {
                        shareholderInputContainer.classList.add("visible");
                    }, 10);
                } else {
                    shareholderInputContainer.style.display = "none";
                    shareholderInputContainer.classList.remove("visible");
                }
                
                // 如果用户直接选择了regulation_08，也要显示股东输入框
                regulationSelect.addEventListener('change', handleRegulationChange);
                // 触发一次change事件，以确保界面状态正确
                const event = new Event('change');
                regulationSelect.dispatchEvent(event);
            }
        })
        .catch(error => {
            console.error('Error fetching regulations:', error);
            alert('无法加载法规列表。请确保后端服务正在运行。');
        });
    
    // 加载已有结果列表
    fetch(`${API_BASE_URL}/api/results`)
        .then(response => response.json())
        .then(data => {
            resultsSelect.innerHTML = ''; // 清空旧选项
            data.results.forEach(result => {
                const option = document.createElement('option');
                option.value = result.path;
                // 新的命名格式
                option.textContent = result.path.replace(/_/g, ' ').replace('.json', '');
                resultsSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error fetching results:', error);
            alert('无法加载已有结果列表。请确保后端服务正在运行。');
        });
    
    // 当公司名称改变且当前选择的是regulation_08时，加载对应的股东列表
    companyInput.addEventListener('change', (event) => {
        const selectedRegulationId = regulationSelect.value;
        const companyName = event.target.value;
        
        if (selectedRegulationId === "regulation_08" && companyName) {
            loadShareholdersForCompany(selectedRegulationId, companyName);
        }
    });

    // 当法规选择改变时的处理函数
    function handleRegulationChange(event) {
        const selectedRegulationId = event.target ? event.target.value : regulationSelect.value;
        loadCompaniesForRegulation(selectedRegulationId);
        
        // 检查是否是regulation_08，如果是则显示股东输入框
        if (selectedRegulationId === "regulation_08") {
            shareholderInputContainer.style.display = "block";
            // 添加动画类
            setTimeout(() => {
                shareholderInputContainer.classList.add("visible");
            }, 10); // 延迟10毫秒以确保DOM更新
        } else {
            // 先移除动画类，然后隐藏元素
            shareholderInputContainer.classList.remove("visible");
            // 等待动画完成后隐藏元素
            setTimeout(() => {
                shareholderInputContainer.style.display = "none";
                // 清空股东输入框和列表
                shareholderInput.value = "";
                shareholderList.innerHTML = "";
            }, 300); // 300毫秒与CSS过渡时间一致
        }
    }

    // 加载指定法规的公司列表
    function loadCompaniesForRegulation(regulationId) {
        if (!regulationId) return;
        
        // 清空原有的公司列表
        companyList.innerHTML = '';
        
        // 显示加载提示
        companyInput.placeholder = "正在加载公司列表...";
        companyInput.disabled = true;
        
        fetch(`${API_BASE_URL}/api/companies/${regulationId}`)
            .then(response => response.json())
            .then(data => {
                // 恢复输入框状态
                companyInput.placeholder = "输入或选择公司名称";
                companyInput.disabled = false;
                
                // 填充公司列表
                if (data.companies && data.companies.length > 0) {
                    data.companies.forEach(company => {
                        const option = document.createElement('option');
                        option.value = company;
                        companyList.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching companies:', error);
                companyInput.placeholder = "输入公司名称";
                companyInput.disabled = false;
            });
    }
    
    // 加载指定公司的股东列表
    function loadShareholdersForCompany(regulationId, companyName) {
        if (!regulationId || !companyName || regulationId !== "regulation_08") return;
        
        // 清空原有的股东列表
        shareholderList.innerHTML = '';
        
        // 显示加载提示
        shareholderInput.placeholder = "正在加载股东列表...";
        shareholderInput.disabled = true;
        
        fetch(`${API_BASE_URL}/api/shareholders/${regulationId}/${encodeURIComponent(companyName)}`)
            .then(response => response.json())
            .then(data => {
                // 恢复输入框状态
                shareholderInput.placeholder = "输入或选择股东";
                shareholderInput.disabled = false;
                
                // 填充股东列表
                if (data.shareholders && data.shareholders.length > 0) {
                    data.shareholders.forEach(shareholder => {
                        const option = document.createElement('option');
                        option.value = shareholder;
                        shareholderList.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching shareholders:', error);
                shareholderInput.placeholder = "输入股东";
                shareholderInput.disabled = false;
            });
    }

    // 运行新的检查
    runCheckButton.addEventListener('click', () => {
        const regulationId = regulationSelect.value;
        const companyName = companyInput.value;
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        
        // 股东参数，只在regulation_08时需要
        const shareholder = regulationId === "regulation_08" ? shareholderInput.value : "";

        if (!regulationId || !companyName) {
            alert('请选择一个法规并输入公司名称。');
            return;
        }
        
        // 如果是regulation_08，检查是否输入了股东
        if (regulationId === "regulation_08" && !shareholder) {
            alert('请输入或选择股东。');
            return;
        }

        loadingSpinner.style.display = 'block';
        graphPlaceholder.style.display = 'none'; // 隐藏占位符
        myChart.clear();
        
        if (reportPlaceholder) reportPlaceholder.style.display = 'none';
        if (reportLoading) reportLoading.style.display = 'block';
        if (reportContent) reportContent.style.display = 'none';

        // 准备请求数据
        const requestData = {
            regulation_id: regulationId,
            company_name: companyName,
        };

        // 只有在有值时才添加日期范围
        if (startDate) {
            requestData.start_date = startDate;
        }
        if (endDate) {
            requestData.end_date = endDate;
        }
        
        // 只有在regulation_08且有值时才添加股东参数
        if (regulationId === "regulation_08" && shareholder) {
            requestData.shareholder = shareholder;
        }

        // 发送检查请求
        fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            loadingSpinner.style.display = 'none';
            graphPlaceholder.style.display = 'none';
            
            // 渲染图表
            renderGraph(data);
            
            // 刷新结果列表获取最新的文件夹路径
            refreshResultsList()
                .then(() => {
                    // 如果返回了result_path，使用它来加载报告
                    if (data.result_path) {
                        loadComplianceReport(data.result_path);
                    } else {
                        // 否则使用最新的结果
                        fetch(`${API_BASE_URL}/api/results`)
                            .then(response => response.json())
                            .then(resultsData => {
                                if (resultsData.results && resultsData.results.length > 0) {
                                    // 获取最新结果的路径
                                    const latestResultPath = resultsData.results[0].path;
                                    loadComplianceReport(latestResultPath);
                                }
                            })
                            .catch(error => {
                                console.error('Error loading report:', error);
                                if (reportLoading) reportLoading.style.display = 'none';
                                if (reportPlaceholder) reportPlaceholder.style.display = 'block';
                            });
                    }
                });
        })
        .catch(error => {
            console.error('Error running compliance check:', error);
            loadingSpinner.style.display = 'none';
            graphPlaceholder.style.display = 'block';
            if (reportPlaceholder) reportPlaceholder.style.display = 'block';
            if (reportLoading) reportLoading.style.display = 'none';
            alert('执行合规检查时出错，请稍后重试。');
        });
    });
    
    // 加载已有结果
    loadResultButton.addEventListener('click', () => {
        const resultPath = resultsSelect.value;
        
        if (!resultPath) {
            alert('请选择一个结果。');
            return;
        }
        
        // 显示加载状态
        loadingSpinner.style.display = 'block';
        graphPlaceholder.style.display = 'none'; // 隐藏占位符
        myChart.clear();
        
        // 显示报告加载状态
        const reportPlaceholder = document.getElementById('report-placeholder');
        const reportLoading = document.getElementById('report-loading');
        const reportContent = document.getElementById('report-content');
        
        if (reportPlaceholder) reportPlaceholder.style.display = 'none';
        if (reportLoading) reportLoading.style.display = 'block';
        if (reportContent) reportContent.style.display = 'none';
        
        // 加载图表数据
        fetch(`${API_BASE_URL}/api/result/${resultPath}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                loadingSpinner.style.display = 'none';
                graphPlaceholder.style.display = 'none'; // 确保图表渲染后占位符是隐藏的
                renderGraph(data);
                
                // 加载合规报告
                loadComplianceReport(resultPath);
            })
            .catch(error => {
                loadingSpinner.style.display = 'none';
                console.error('Error loading result:', error);
                alert(`加载结果时出错: ${error.message}.`);
                
                // 重置报告区域
                if (reportPlaceholder) reportPlaceholder.style.display = 'block';
                if (reportLoading) reportLoading.style.display = 'none';
                if (reportContent) reportContent.style.display = 'none';
            });
    });
    
    // 刷新结果列表
    function refreshResultsList() {
        return fetch(`${API_BASE_URL}/api/results`)
            .then(response => response.json())
            .then(data => {
                resultsSelect.innerHTML = ''; // 清空
                data.results.forEach(result => {
                    const option = document.createElement('option');
                    option.value = result.path;
                    option.textContent = result.path.replace(/_/g, ' ').replace('.json', '');
                    resultsSelect.appendChild(option);
                });
                
                if (data.results.length > 0) {
                    resultsSelect.value = data.results[0].path;
                }
                return data; // 返回数据以便调用者使用
            })
            .catch(error => {
                console.error('Error refreshing results list:', error);
                return Promise.reject(error); // 返回一个拒绝的Promise
            });
    }

    // 加载合规报告函数
    function loadComplianceReport(resultPath) {
        // 初始化DOM元素
        const reportPlaceholder = document.getElementById('report-placeholder');
        const reportLoading = document.getElementById('report-loading');
        const reportContent = document.getElementById('report-content');
        
        if (!reportPlaceholder || !reportLoading || !reportContent) {
            console.error('报告相关DOM元素未找到');
            return;
        }
        
        // 显示加载状态
        reportPlaceholder.style.display = 'none';
        reportLoading.style.display = 'block';
        reportContent.style.display = 'none';
        reportContent.innerHTML = ''; // 清空之前的内容
        
        console.log(`正在加载报告，路径: ${resultPath}`);
        
        // 正确构建结果路径 - 使用当前选择的完整路径
        fetch(`${API_BASE_URL}/api/report/${resultPath}`)
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        // 报告可能还在生成中，不显示错误，继续等待
                        console.log('报告未找到，可能正在生成中，将在5秒后重试...');
                        setTimeout(() => loadComplianceReport(resultPath), 5000);
                        return null; // 返回null终止后续处理
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (!data) return; // 如果是null（404处理中返回的），则终止
                
                const mdContent = data.report;
                if (!mdContent) {
                    reportLoading.style.display = 'none';
                    reportContent.style.display = 'block';
                    reportContent.innerHTML = '<div class="error-text">无法生成合规报告</div>';
                    return;
                }
                
                // 确保marked库已加载
                if (typeof marked === 'undefined') {
                    console.error('Marked库未加载');
                    
                    // 简单的Markdown格式处理作为后备
                    const html = mdContent
                        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
                        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
                        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
                        .replace(/^- (.*$)/gm, '<li>$1</li>')
                        .replace(/\*\*(.*)\*\*/g, '<strong>$1</strong>')
                        .replace(/\n/g, '<br>');
                    
                    reportContent.innerHTML = `<div class="markdown-content">${html}</div>`;
                } else {
                    // 使用Marked库渲染Markdown
                    try {
                        // 首先去除文档开头的```markdown标记（如果有）
                        let cleanContent = mdContent;
                        if (cleanContent.startsWith('```markdown')) {
                            cleanContent = cleanContent.substring('```markdown'.length);
                            // 查找结尾的```
                            const endIndex = cleanContent.lastIndexOf('```');
                            if (endIndex !== -1) {
                                cleanContent = cleanContent.substring(0, endIndex);
                            }
                        }
                        
                        // 配置marked选项
                        marked.setOptions({
                            breaks: true,      // 将\n转换为<br>
                            gfm: true,         // 使用GitHub风格的Markdown
                            headerIds: true,   // 为标题添加id属性
                            mangle: false      // 不混淆标题ID
                        });
                        
                        reportContent.innerHTML = `<div class="markdown-content">${marked.parse(cleanContent)}</div>`;
                        
                        // 渲染后初始化mermaid图表
                        if (typeof mermaid !== 'undefined') {
                            try {
                                console.log('渲染mermaid图表...');
                                setTimeout(() => {
                                    mermaid.init(undefined, document.querySelectorAll('.mermaid'));
                                }, 100);
                            } catch (mermaidError) {
                                console.error('Mermaid渲染错误:', mermaidError);
                            }
                        }
                    } catch (e) {
                        console.error('Markdown渲染错误:', e);
                        reportContent.textContent = mdContent; // 作为纯文本显示
                    }
                }
                
                // 隐藏加载，显示内容
                reportLoading.style.display = 'none';
                reportContent.style.display = 'block';
            })
            .catch(error => {
                console.error('Error loading compliance report:', error);
                
                // 不显示加载错误，而是继续等待
                if (error.message.includes('404')) {
                    console.log('报告未找到，可能正在生成中，将在5秒后重试...');
                    setTimeout(() => loadComplianceReport(resultPath), 5000);
                } else {
                    reportLoading.style.display = 'none';
                    reportContent.style.display = 'block';
                    reportContent.innerHTML = '<div class="loading-text">正在生成报告，请稍候...</div>';
                    
                    // 10秒后再次尝试
                    setTimeout(() => loadComplianceReport(resultPath), 10000);
                }
            });
    }

    function renderGraph(data) {
        graphPlaceholder.style.display = 'none'; // 渲染图表时再次确保占位符隐藏
        const graphData = data.graph;
        const metadata = data.metadata;
        const finalStatus = data.final_compliance_status || {};

        // 构建主副标题
        const mainTitle = `${metadata.company_name} 合规检查`;
        const dateSubtitle = `(${metadata.date_range[0] || '...'} to ${metadata.date_range[1] || '...'})`;
        const subTitle = `${metadata.regulation_name} ${dateSubtitle}`;
        
        // 添加合规状态摘要
        const statusSummary = finalStatus.summary || "合规状态未知";
        const statusDetails = `违规: ${finalStatus.violation_count || 0} | 合规: ${finalStatus.success_count || 0} | 排除: ${finalStatus.excluded_count || 0} | 强制: ${finalStatus.forced_count || 0}`;

        // 定义关系样式
        const relationStyles = {
            'refer_to': {'color': '#5B8DB6', 'type': 'dashed', 'label': '#2A4E6E'},
            'exclude': {'color': '#B1443C', 'type': 'dashed', 'label': '#7D2F28'},
            'only_include': {'color': '#5F8EA9', 'type': 'solid', 'label': '#2F5266'},
            'should_include': {'color': '#7CA17D', 'type': 'solid', 'label': '#3F5940'},
            'default': {'color': '#9E9E9E', 'type': 'dotted', 'label': '#757575'}
        };

        const option = {
            title: {
                text: mainTitle,
                subtext: `${subTitle}\n${statusSummary}\n${statusDetails}`,
                subtextStyle: {
                    lineHeight: 18
                },
                top: 'top',
                left: 'center'
            },
            tooltip: {
                confine: true, // 确保 tooltip 始终在图表区域内
                enterable: true, // 允许鼠标进入 tooltip
                extraCssText: 'max-width: 400px; white-space: normal; word-wrap: break-word;', // 样式设置
                formatter: function (params) {
                    if (params.dataType === 'node') {
                        const categoryName = graphData.categories[params.data.category].name;
                        const details = params.data.value; // 从value中获取详细信息
                        
                        // 检查details是否为我们定义的object
                        if (typeof details === 'object' && details !== null) {
                            let tooltip = `<b>ID: ${params.data.id}</b><br/>` +
                                   `<b>类别:</b> ${categoryName}<br/>` +
                                   `<b>状态:</b> ${details.status}<br/>` +
                                   `--------------------<br/>`;
                            
                            // 添加违规详情（如果有）
                            const violationDetails = details.evaluation_details;
                            // 确保violationDetails是一个数组且包含元素
                            if (Array.isArray(violationDetails) && violationDetails.length > 0) {
                                console.log("Debugging: violationDetails array received by formatter:", violationDetails); // 调试信息
                                tooltip += '<b>违规详情 (前3条):</b><br/>';
                                violationDetails.slice(0, 3).forEach((v, i) => {
                                    console.log(`Debugging: Inspecting violation record ${i + 1}:`, v); // 调试信息
                                    console.log(`Debugging: Value of v['日期'] is:`, v['日期']); // 调试信息
                                    const date = v['日期'] ? new Date(v['日期']).toLocaleDateString() : '无日期';
                                    tooltip += `<div style="margin-left: 10px;">` +
                                               `<b>记录 ${i + 1} (${date}):</b><br/>` +
                                               `<div style="margin-left: 15px;">` +
                                               `Subject: ${v._subject_passed ? '✅ 通过' : '❌ 失败'}<br/>` +
                                               `Condition: ${v._condition_passed ? '✅ 通过' : '❌ 失败'}<br/>` +
                                               `Constraint: ${v._constraint_passed ? '✅ 通过' : '❌ 失败'}<br/>` +
                                               `</div></div>`;
                                });
                                if (violationDetails.length > 3) {
                                    tooltip += `&nbsp;&nbsp;... (共 ${violationDetails.length} 条违规)<br/>`;
                                }
                                tooltip += `--------------------<br/>`;
                            // 如果不是数组而是字符串，则直接显示
                            } else if (typeof violationDetails === 'string') {
                                tooltip += `<b>详情:</b> ${violationDetails}<br/>--------------------<br/>`;
                            }
                            
                            // 添加单元基本信息
                            tooltip += `<b>Subject:</b> ${details.subject || '无'}<br/>` +
                                      `<b>Condition:</b> ${details.condition || '无'}<br/>` +
                                      `<b>Constraint:</b> ${details.constraint || '无'}<br/>`;
                            
                            // 添加上下文信息（如果有）
                            if (details.contextual_info) {
                                tooltip += `<b>Context:</b> ${details.contextual_info}<br/>`;
                            }
                            
                            return tooltip;
                        }
                        // 兼容根节点和法条节点
                        return `<b>${params.data.name}</b><br/>ID: ${params.data.id}<br/>类别: ${categoryName}`;
                    } else if (params.dataType === 'edge') {
                        return `关系: ${params.data.value || '层次关系'}`;
                    }
                    return params.name;
                }
            },
            legend: [{
                data: graphData.categories.map(a => a.name),
                orient: 'vertical',
                left: 'left',
                top: 'bottom',
                itemGap: 12,
                selected: {
                    // 默认显示所有类别
                    "合规": true,
                    "违规": true,
                    "未执行": true,
                    "执行错误": true,
                    "法条": true,
                    "法规根节点": true,
                    "被排除": true,
                    "被强制包含": true
                }
            }],
            series: [{
                type: 'graph',
                layout: 'force',
                data: graphData.nodes,
                links: graphData.links,
                categories: graphData.categories,
                roam: true,
                draggable: true, // 允许节点拖动
                label: {
                    show: true,
                    position: 'right',
                    formatter: function(params) {
                        // 根节点和法条节点显示名称，其他节点显示ID
                        if (params.data.category === 4 || params.data.category === 5) {
                            return params.data.name;
                        }
                        // 对于其他节点，只显示ID的数字部分
                        const idParts = params.data.id.split('_');
                        if (idParts.length >= 2) {
                            return idParts[1] + (idParts.length > 2 ? '_' + idParts[2] : '');
                        }
                        return params.data.name;
                    }
                },
                edgeSymbol: ['none', 'arrow'], // 边两端显示无和箭头，表示方向
                edgeSymbolSize: [4, 8],
                edgeLabel: {
                    show: true,
                    formatter: function(params) {
                        return params.data.value || ''; // 显示关系名称
                    },
                    color: '#333',
                    fontSize: 9
                },
                lineStyle: {
                    opacity: 0.9,
                    width: 2,
                    curveness: 0.1
                },
                force: {
                    repulsion: 150, // 增加排斥力，使节点更分散
                    edgeLength: [50, 120], // 层次边短，关系边长
                    layoutAnimation: true,
                    gravity: 0.1 // 轻微的向心力
                },
                emphasis: {
                    focus: 'adjacency',
                    lineStyle: {
                        width: 10
                    }
                }
            }]
        };

        myChart.setOption(option, true); // 使用 true 来确保旧配置被完全替换
        
        // 自适应窗口大小
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }
}); 