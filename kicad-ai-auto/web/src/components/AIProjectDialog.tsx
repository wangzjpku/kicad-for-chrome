/**
 * AIProjectDialog - AI 智能项目创建对话框组件 (增强版)
 *
 * 支持交互式问答流程:
 * 1. 用户输入初始需求
 * 2. AI 生成澄清问题列表
 * 3. 用户回答问题
 * 4. AI 生成完整 BOM 和原理图
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

interface ProjectSpec {
  name: string;
  description: string;
  components: ComponentSpec[];
  parameters: ParameterSpec[];
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

interface SchematicData {
  components: any[];
  wires: any[];
  nets: any[];
}

type DialogStep = 'input' | 'clarifying' | 'analyzing' | 'preview' | 'error';

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
        // clarify API 可用，显示问答界面
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
        // clarify API 不可用，直接调用 analyze API（旧流程兼容）
        console.log('Clarify API not available, falling back to direct analyze...');
        await directAnalyze();
      }

    } catch (err: any) {
      // 网络错误，尝试直接分析
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

  // ========== Step 3: 确认创建项目 ==========
  const handleConfirm = async () => {
    if (!projectSpec) return;

    try {
      const response = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectSpec.name,
          description: projectSpec.description,
          schematicData: schematicData
        })
      });

      if (!response.ok) {
        throw new Error('创建项目失败');
      }

      const newProject = await response.json();
      onProjectCreated(newProject);
      onClose();
    } catch (err: any) {
      setError(err.message || '创建项目失败');
    }
  };

  // 处理返回修改
  const handleBack = () => {
    if (step === 'clarifying') {
      setStep('input');
    } else if (step === 'preview') {
      setStep('clarifying');
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
    // 直接提交当前答案
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
          <div className={`progress-step ${step === 'input' ? 'active' : ''} ${['clarifying', 'analyzing', 'preview'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">1</span>
            <span className="step-label">输入需求</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'clarifying' ? 'active' : ''} ${['analyzing', 'preview'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-label">明确细节</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${['analyzing'].includes(step) ? 'active' : ''} ${step === 'preview' ? 'completed' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-label">生成方案</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'preview' ? 'active' : ''}`}>
            <span className="step-number">4</span>
            <span className="step-label">确认创建</span>
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
                placeholder="例如：设计一个5V稳压电源，输入220V交流电，输出5V直流电，电流1A"
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

          {/* Step 4: 预览结果 */}
          {step === 'preview' && projectSpec && (
            <div className="step-preview">
              {/* 项目方案 */}
              <div className="spec-section">
                <h3>📦 项目方案</h3>
                <div className="spec-content">
                  <h4>{projectSpec.name}</h4>
                  <p>{projectSpec.description}</p>

                  {projectSpec.parameters.length > 0 && (
                    <>
                      <h5>技术参数</h5>
                      <table className="params-table">
                        <tbody>
                          {projectSpec.parameters.map((param, idx) => (
                            <tr key={idx}>
                              <td>{param.key}</td>
                              <td>{param.value} {param.unit || ''}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  )}

                  <h5>📋 BOM 器件清单</h5>
                  <table className="components-table">
                    <thead>
                      <tr>
                        <th>器件</th>
                        <th>型号</th>
                        <th>封装</th>
                        <th>数量</th>
                      </tr>
                    </thead>
                    <tbody>
                      {projectSpec.components.map((comp, idx) => (
                        <tr key={idx}>
                          <td>{comp.name}</td>
                          <td>{comp.model}</td>
                          <td>{comp.package}</td>
                          <td>{comp.quantity}</td>
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
              <button className="confirm-btn" onClick={handleConfirm}>
                ✅ 确认创建项目
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
