/**
 * AIProjectDialog - AI 智能项目创建对话框组件 (增强版 v2)
 *
 * 支持完整的交互式流程:
 * 1. 用户输入需求
 * 2. AI 生成澄清问题列表
 * 3. 用户回答问题
 * 4. AI 生成方案（BOM + 参数）
 * 5. 【新增】用户编辑 BOM 和参数
 * 6. 用户确认方案
 * 7. 【新增】生成最终结果并确认
 */

import React, { useState, useEffect } from 'react';
import './AIProjectDialog.css';

interface AIProjectDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: any) => void;
}

interface ClarificationQuestion {
  id: string;
  question: string;
  category: string;
  options?: string[];
  default?: string;
  required: boolean;
}

interface ClarificationResponse {
  questions: ClarificationQuestion[];
  summary: string;
  detected_type: string;
}

interface ComponentSpec {
  name: string;
  model: string;
  package: string;
  quantity: number;
  footprint?: string;
}

interface ParameterSpec {
  key: string;
  value: string;
  unit?: string;
}

interface ProjectSpec {
  name: string;
  description: string;
  components: ComponentSpec[];
  parameters: ParameterSpec[];
}

interface SchematicData {
  components: any[];
  wires: any[];
  nets: any[];
}

type DialogStep = 'input' | 'clarifying' | 'analyzing' | 'preview' | 'editing' | 'generating' | 'confirm' | 'error';

const AIProjectDialog: React.FC<AIProjectDialogProps> = ({
  isOpen,
  onClose,
  onProjectCreated
}) => {
  // 状态
  const [step, setStep] = useState<DialogStep>('input');
  const [inputText, setInputText] = useState('');
  const [clarificationData, setClarificationData] = useState<ClarificationResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [projectSpec, setProjectSpec] = useState<ProjectSpec | null>(null);
  const [schematicData, setSchematicData] = useState<SchematicData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');

  // 编辑状态
  const [editingComponent, setEditingComponent] = useState<number | null>(null);
  const [editingParameter, setEditingParameter] = useState<number | null>(null);
  const [tempComponent, setTempComponent] = useState<ComponentSpec | null>(null);
  const [tempParameter, setTempParameter] = useState<ParameterSpec | null>(null);

  // 最终结果
  const [finalResult, setFinalResult] = useState<any>(null);

  // 重置状态
  useEffect(() => {
    if (!isOpen) {
      setStep('input');
      setInputText('');
      setClarificationData(null);
      setAnswers({});
      setProjectSpec(null);
      setSchematicData(null);
      setError(null);
      setProgress('');
      setEditingComponent(null);
      setEditingParameter(null);
      setFinalResult(null);
    }
  }, [isOpen]);

  // ========== Step 1: 提交需求，获取澄清问题 ==========
  const handleSubmitRequirements = async () => {
    if (!inputText.trim()) {
      setError('请输入项目需求描述');
      return;
    }

    setStep('analyzing');
    setError(null);
    setProgress('正在分析需求...');

    try {
      // 尝试调用 clarify API
      const clarifyResponse = await fetch('/api/v1/ai/clarify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirements: inputText })
      });

      if (clarifyResponse.ok) {
        const data: ClarificationResponse = await clarifyResponse.json();

        // 初始化默认答案
        const defaultAnswers: Record<string, string> = {};
        data.questions.forEach(q => {
          if (q.default) {
            defaultAnswers[q.id] = q.default;
          } else if (q.options && q.options.length > 0) {
            defaultAnswers[q.id] = q.options[0];
          }
        });

        setAnswers(defaultAnswers);
        setClarificationData(data);
        setStep('clarifying');
      } else {
        console.log('Clarify API not available, falling back to direct analyze...');
        await directAnalyze();
      }

    } catch (err: any) {
      console.log('Clarify API error, falling back to direct analyze:', err.message);
      try {
        await directAnalyze();
      } catch (analyzeErr: any) {
        setError(analyzeErr.message || '分析过程出错');
        setStep('error');
      }
    }
  };

  // 直接调用 analyze API（旧流程）
  const directAnalyze = async () => {
    setProgress('正在生成方案...');

    const response = await fetch('/api/v1/ai/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requirements: inputText,
        answers: {}
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'AI 分析失败');
    }

    const data = await response.json();

    setProgress('正在生成项目方案...');
    setProjectSpec(data.spec);

    setProgress('正在生成原理图...');
    setSchematicData(data.schematic);

    setStep('preview');
  };

  // ========== Step 2: 提交答案，生成方案 ==========
  const handleSubmitAnswers = async () => {
    setStep('analyzing');
    setError(null);
    setProgress('正在根据您的需求生成 BOM 和原理图...');

    try {
      const response = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requirements: inputText,
          answers: answers
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '生成方案失败');
      }

      const data = await response.json();

      setProgress('正在生成项目方案...');
      setProjectSpec(data.spec);

      setProgress('正在生成原理图...');
      setSchematicData(data.schematic);

      setStep('preview');

    } catch (err: any) {
      setError(err.message || '生成方案出错');
      setStep('error');
    }
  };

  // ========== 编辑功能 ==========

  // 开始编辑器件
  const startEditComponent = (index: number) => {
    setEditingComponent(index);
    setTempComponent({ ...projectSpec!.components[index] });
  };

  // 保存器件编辑
  const saveComponentEdit = () => {
    if (tempComponent && editingComponent !== null) {
      const newComponents = [...projectSpec!.components];
      newComponents[editingComponent] = tempComponent;
      setProjectSpec({ ...projectSpec!, components: newComponents });
    }
    setEditingComponent(null);
    setTempComponent(null);
  };

  // 取消器件编辑
  const cancelComponentEdit = () => {
    setEditingComponent(null);
    setTempComponent(null);
  };

  // 添加新器件
  const addComponent = () => {
    const newComponent: ComponentSpec = {
      name: '新器件',
      model: '',
      package: '0805',
      quantity: 1
    };
    setProjectSpec({
      ...projectSpec!,
      components: [...projectSpec!.components, newComponent]
    });
  };

  // 删除器件
  const deleteComponent = (index: number) => {
    const newComponents = projectSpec!.components.filter((_, i) => i !== index);
    setProjectSpec({ ...projectSpec!, components: newComponents });
  };

  // 开始编辑参数
  const startEditParameter = (index: number) => {
    setEditingParameter(index);
    setTempParameter({ ...projectSpec!.parameters[index] });
  };

  // 保存参数编辑
  const saveParameterEdit = () => {
    if (tempParameter && editingParameter !== null) {
      const newParameters = [...projectSpec!.parameters];
      newParameters[editingParameter] = tempParameter;
      setProjectSpec({ ...projectSpec!, parameters: newParameters });
    }
    setEditingParameter(null);
    setTempParameter(null);
  };

  // 取消参数编辑
  const cancelParameterEdit = () => {
    setEditingParameter(null);
    setTempParameter(null);
  };

  // 添加新参数
  const addParameter = () => {
    const newParameter: ParameterSpec = {
      key: '新参数',
      value: '',
      unit: ''
    };
    setProjectSpec({
      ...projectSpec!,
      parameters: [...projectSpec!.parameters, newParameter]
    });
  };

  // 删除参数
  const deleteParameter = (index: number) => {
    const newParameters = projectSpec!.parameters.filter((_, i) => i !== index);
    setProjectSpec({ ...projectSpec!, parameters: newParameters });
  };

  // 进入编辑模式
  const enterEditMode = () => {
    setStep('editing');
  };

  // 退出编辑模式
  const exitEditMode = () => {
    setStep('preview');
    setEditingComponent(null);
    setEditingParameter(null);
  };

  // ========== Step 3: 提交方案，生成最终结果 ==========
  const handleSubmitForGeneration = async () => {
    setStep('generating');
    setError(null);
    setProgress('正在生成最终项目...');

    try {
      const response = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectSpec!.name,
          description: projectSpec!.description,
          components: projectSpec!.components,
          parameters: projectSpec!.parameters,
          schematicData: schematicData
        })
      });

      if (!response.ok) {
        throw new Error('创建项目失败');
      }

      const result = await response.json();
      setFinalResult(result);
      setStep('confirm');

    } catch (err: any) {
      setError(err.message || '生成最终结果失败');
      setStep('error');
    }
  };

  // ========== Step 4: 确认最终结果 ==========
  const handleFinalConfirm = () => {
    if (finalResult) {
      onProjectCreated(finalResult);
      onClose();
    }
  };

  // 处理返回修改
  const handleBack = () => {
    if (step === 'clarifying') {
      setStep('input');
    } else if (step === 'preview' || step === 'editing') {
      setStep('clarifying');
    } else if (step === 'confirm') {
      setStep('preview');
    } else if (step === 'error') {
      setStep('input');
      setError(null);
    }
  };

  // 更新答案
  const updateAnswer = (questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  };

  // 跳过可选问题
  const handleSkipOptional = () => {
    handleSubmitAnswers();
  };

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay">
      <div className="dialog-container dialog-container-large">
        {/* 标题栏 */}
        <div className="dialog-header">
          <h2>🤖 AI 智能创建项目</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* 进度指示器 */}
        <div className="progress-indicator">
          <div className={`progress-step ${step === 'input' ? 'active' : ''} ${['clarifying', 'analyzing', 'preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">1</span>
            <span className="step-label">输入需求</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'clarifying' ? 'active' : ''} ${['analyzing', 'preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-label">明确细节</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${['analyzing'].includes(step) ? 'active' : ''} ${['preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-label">生成方案</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${['preview', 'editing'].includes(step) ? 'active' : ''} ${['generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">4</span>
            <span className="step-label">编辑确认</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${['generating'].includes(step) ? 'active' : ''} ${step === 'confirm' ? 'completed' : ''}`}>
            <span className="step-number">5</span>
            <span className="step-label">生成项目</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'confirm' ? 'active' : ''}`}>
            <span className="step-number">6</span>
            <span className="step-label">最终确认</span>
          </div>
        </div>

        {/* 内容区 */}
        <div className="dialog-content">
          {/* Step 1: 输入需求 */}
          {step === 'input' && (
            <div className="step-input">
              <label htmlFor="requirements">
                描述您的项目需求（自然语言）
              </label>
              <textarea
                id="requirements"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="例如：设计一个5V稳压电源，输入220V交流电，输出5V直流电"
                rows={8}
              />
              <p className="hint">
                💡 提示：描述越详细，AI 生成的问题越精准，最终方案越符合您的需求
              </p>
              {error && <p className="error-message">{error}</p>}
            </div>
          )}

          {/* Step 2: 澄清问题 */}
          {step === 'clarifying' && clarificationData && (
            <div className="step-clarifying">
              <div className="detected-info">
                <span className="detected-label">检测到电路类型:</span>
                <span className="detected-type">{clarificationData.detected_type}</span>
              </div>

              <p className="clarifying-hint">
                📋 请回答以下问题，帮助 AI 更精确地生成 BOM 和原理图：
              </p>

              <div className="questions-list">
                {clarificationData.questions.map((q, index) => (
                  <div key={q.id} className={`question-item ${q.required ? 'required' : 'optional'}`}>
                    <div className="question-header">
                      <span className="question-number">{index + 1}</span>
                      <span className="question-text">{q.question}</span>
                      {!q.required && <span className="optional-badge">可选</span>}
                    </div>

                    <div className="question-options">
                      {q.options ? (
                        <div className="options-grid">
                          {q.options.map((option, optIndex) => (
                            <label key={optIndex} className={`option-item ${answers[q.id] === option ? 'selected' : ''}`}>
                              <input
                                type="radio"
                                name={q.id}
                                value={option}
                                checked={answers[q.id] === option}
                                onChange={(e) => updateAnswer(q.id, e.target.value)}
                              />
                              <span>{option}</span>
                            </label>
                          ))}
                        </div>
                      ) : (
                        <input
                          type="text"
                          className="text-input"
                          placeholder={q.default || '请输入...'}
                          value={answers[q.id] || ''}
                          onChange={(e) => updateAnswer(q.id, e.target.value)}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="answers-summary">
                <p>已回答 {Object.keys(answers).filter(k => answers[k]).length} / {clarificationData.questions.length} 个问题</p>
              </div>
            </div>
          )}

          {/* Step 3: 分析中 */}
          {step === 'analyzing' && (
            <div className="step-analyzing">
              <div className="spinner"></div>
              <p className="progress-text">{progress}</p>
            </div>
          )}

          {/* Step 4: 预览结果（带编辑功能） */}
          {(step === 'preview' || step === 'editing') && projectSpec && (
            <div className="step-preview">
              {/* 工具栏 */}
              <div className="preview-toolbar">
                {step === 'preview' ? (
                  <button className="edit-mode-btn" onClick={enterEditMode}>
                    ✏️ 进入编辑模式
                  </button>
                ) : (
                  <button className="exit-edit-btn" onClick={exitEditMode}>
                    ✓ 完成编辑
                  </button>
                )}
              </div>

              {/* 项目方案 */}
              <div className="spec-section">
                <h3>📦 项目方案 {step === 'editing' && <span className="edit-badge">编辑中</span>}</h3>
                <div className="spec-content">
                  <h4>{projectSpec.name}</h4>
                  <p>{projectSpec.description}</p>

                  {/* 技术参数表格 */}
                  {projectSpec.parameters.length > 0 && (
                    <>
                      <h5>
                        技术参数
                        {step === 'editing' && (
                          <button className="add-btn small" onClick={addParameter}>+ 添加参数</button>
                        )}
                      </h5>
                      <table className="params-table editable-table">
                        <thead>
                          <tr>
                            <th>参数名</th>
                            <th>数值</th>
                            <th>单位</th>
                            {step === 'editing' && <th>操作</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {projectSpec.parameters.map((param, idx) => (
                            <tr key={idx}>
                              {editingParameter === idx ? (
                                <>
                                  <td>
                                    <input
                                      type="text"
                                      value={tempParameter?.key || ''}
                                      onChange={(e) => setTempParameter({ ...tempParameter!, key: e.target.value })}
                                      className="inline-input"
                                    />
                                  </td>
                                  <td>
                                    <input
                                      type="text"
                                      value={tempParameter?.value || ''}
                                      onChange={(e) => setTempParameter({ ...tempParameter!, value: e.target.value })}
                                      className="inline-input"
                                    />
                                  </td>
                                  <td>
                                    <input
                                      type="text"
                                      value={tempParameter?.unit || ''}
                                      onChange={(e) => setTempParameter({ ...tempParameter!, unit: e.target.value })}
                                      className="inline-input small"
                                    />
                                  </td>
                                  <td>
                                    <button className="save-btn small" onClick={saveParameterEdit}>💾</button>
                                    <button className="cancel-btn small" onClick={cancelParameterEdit}>✕</button>
                                  </td>
                                </>
                              ) : (
                                <>
                                  <td>{param.key}</td>
                                  <td>{param.value}</td>
                                  <td>{param.unit || ''}</td>
                                  {step === 'editing' && (
                                    <td>
                                      <button className="edit-btn small" onClick={() => startEditParameter(idx)}>✏️</button>
                                      <button className="delete-btn small" onClick={() => deleteParameter(idx)}>🗑️</button>
                                    </td>
                                  )}
                                </>
                              )}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  )}

                  {/* BOM 器件清单 */}
                  <h5>
                    📋 BOM 器件清单 ({projectSpec.components.length} 个器件)
                    {step === 'editing' && (
                      <button className="add-btn small" onClick={addComponent}>+ 添加器件</button>
                    )}
                  </h5>
                  <table className="components-table editable-table">
                    <thead>
                      <tr>
                        <th>器件</th>
                        <th>型号</th>
                        <th>封装</th>
                        <th>数量</th>
                        {step === 'editing' && <th>操作</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {projectSpec.components.map((comp, idx) => (
                        <tr key={idx}>
                          {editingComponent === idx ? (
                            <>
                              <td>
                                <input
                                  type="text"
                                  value={tempComponent?.name || ''}
                                  onChange={(e) => setTempComponent({ ...tempComponent!, name: e.target.value })}
                                  className="inline-input"
                                />
                              </td>
                              <td>
                                <input
                                  type="text"
                                  value={tempComponent?.model || ''}
                                  onChange={(e) => setTempComponent({ ...tempComponent!, model: e.target.value })}
                                  className="inline-input"
                                />
                              </td>
                              <td>
                                <input
                                  type="text"
                                  value={tempComponent?.package || ''}
                                  onChange={(e) => setTempComponent({ ...tempComponent!, package: e.target.value })}
                                  className="inline-input small"
                                />
                              </td>
                              <td>
                                <input
                                  type="number"
                                  value={tempComponent?.quantity || 1}
                                  onChange={(e) => setTempComponent({ ...tempComponent!, quantity: parseInt(e.target.value) || 1 })}
                                  className="inline-input tiny"
                                  min="1"
                                />
                              </td>
                              <td>
                                <button className="save-btn small" onClick={saveComponentEdit}>💾</button>
                                <button className="cancel-btn small" onClick={cancelComponentEdit}>✕</button>
                              </td>
                            </>
                          ) : (
                            <>
                              <td>{comp.name}</td>
                              <td>{comp.model}</td>
                              <td>{comp.package}</td>
                              <td>{comp.quantity}</td>
                              {step === 'editing' && (
                                <td>
                                  <button className="edit-btn small" onClick={() => startEditComponent(idx)}>✏️</button>
                                  <button className="delete-btn small" onClick={() => deleteComponent(idx)}>🗑️</button>
                                </td>
                              )}
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 原理图预览 */}
              {schematicData && (
                <div className="schematic-section">
                  <h3>📐 原理图预览</h3>
                  <div className="schematic-preview">
                    <p>器件数量: {schematicData.components.length}</p>
                    <p>导线数量: {schematicData.wires.length}</p>
                    <p>网络数量: {schematicData.nets.length}</p>

                    <div className="schematic-canvas-wrapper">
                      <svg
                        className="schematic-canvas"
                        viewBox="0 0 500 400"
                        preserveAspectRatio="xMidYMid meet"
                      >
                        <defs>
                          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1a3a5a" strokeWidth="0.5"/>
                          </pattern>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#grid)" />

                        {schematicData.wires?.map((wire: any, index: number) => {
                          const points = wire.points || [];
                          if (points.length < 2) return null;
                          let pathD = `M ${points[0].x} ${points[0].y}`;
                          for (let i = 1; i < points.length; i++) {
                            pathD += ` L ${points[i].x} ${points[i].y}`;
                          }
                          return (
                            <path
                              key={wire.id || `wire-${index}`}
                              d={pathD}
                              fill="none"
                              stroke={wire.net === 'VCC' ? '#4CAF50' : wire.net === 'GND' ? '#F44336' : '#2196F3'}
                              strokeWidth="2"
                            />
                          );
                        })}

                        {schematicData.components.map((comp: any, index: number) => {
                          const x = comp.position?.x || 50;
                          const y = comp.position?.y || 50;
                          const color = '#607D8B';
                          return (
                            <g key={comp.id || `comp-${index}`} transform={`translate(${x - 30}, ${y - 20})`}>
                              <rect width="60" height="40" rx="6" fill={color} fillOpacity="0.2" stroke={color} strokeWidth="2"/>
                              <text x="30" y="25" textAnchor="middle" fontSize="8" fill="#fff">
                                {comp.name?.substring(0, 8) || 'Component'}
                              </text>
                            </g>
                          );
                        })}
                      </svg>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 5: 生成中 */}
          {step === 'generating' && (
            <div className="step-analyzing">
              <div className="spinner"></div>
              <p className="progress-text">{progress}</p>
            </div>
          )}

          {/* Step 6: 最终确认 */}
          {step === 'confirm' && finalResult && (
            <div className="step-confirm">
              <div className="success-icon">✅</div>
              <h3>项目已生成完成！</h3>

              <div className="final-result-card">
                <div className="result-item">
                  <span className="label">项目名称</span>
                  <span className="value">{projectSpec?.name}</span>
                </div>
                <div className="result-item">
                  <span className="label">项目 ID</span>
                  <span className="value code">{finalResult.id}</span>
                </div>
                <div className="result-item">
                  <span className="label">器件数量</span>
                  <span className="value">{projectSpec?.components.length} 个</span>
                </div>
                <div className="result-item">
                  <span className="label">创建时间</span>
                  <span className="value">{new Date().toLocaleString()}</span>
                </div>
              </div>

              <p className="confirm-hint">
                请确认以上信息无误，点击"确认完成"完成项目创建
              </p>
            </div>
          )}

          {/* 错误步骤 */}
          {step === 'error' && (
            <div className="step-error">
              <p className="error-text">❌ {error}</p>
              <button className="retry-btn" onClick={handleBack}>
                重新开始
              </button>
            </div>
          )}
        </div>

        {/* 底部按钮栏 */}
        <div className="dialog-footer">
          {step === 'input' && (
            <>
              <button className="cancel-btn" onClick={onClose}>
                取消
              </button>
              <button
                className="submit-btn"
                onClick={handleSubmitRequirements}
                disabled={!inputText.trim()}
              >
                下一步：明确需求
              </button>
            </>
          )}

          {step === 'clarifying' && (
            <>
              <button className="back-btn" onClick={handleBack}>
                返回修改
              </button>
              <button className="skip-btn" onClick={handleSkipOptional}>
                跳过可选问题
              </button>
              <button className="submit-btn" onClick={handleSubmitAnswers}>
                生成方案
              </button>
            </>
          )}

          {step === 'preview' && (
            <>
              <button className="back-btn" onClick={handleBack}>
                返回修改
              </button>
              <button className="abandon-btn" onClick={onClose}>
                放弃
              </button>
              <button className="edit-btn" onClick={enterEditMode}>
                ✏️ 编辑方案
              </button>
              <button className="submit-btn" onClick={handleSubmitForGeneration}>
                提交并生成项目
              </button>
            </>
          )}

          {step === 'editing' && (
            <>
              <button className="back-btn" onClick={exitEditMode}>
                完成编辑
              </button>
            </>
          )}

          {step === 'confirm' && (
            <>
              <button className="back-btn" onClick={handleBack}>
                返回修改
              </button>
              <button className="abandon-btn" onClick={onClose}>
                放弃
              </button>
              <button className="confirm-btn large" onClick={handleFinalConfirm}>
                ✅ 确认完成
              </button>
            </>
          )}

          {step === 'error' && (
            <button className="retry-btn-large" onClick={handleBack}>
              重新开始
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIProjectDialog;
