/**
 * AIProjectDialog - AI 智能项目创建对话框组件
 * 支持自然语言输入，AI 分析生成项目方案和原理图
 */

import React, { useState, useEffect } from 'react';
import './AIProjectDialog.css';

interface AIProjectDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: any) => void;
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

type DialogStep = 'input' | 'analyzing' | 'preview' | 'error';

const AIProjectDialog: React.FC<AIProjectDialogProps> = ({
  isOpen,
  onClose,
  onProjectCreated
}) => {
  const [step, setStep] = useState<DialogStep>('input');
  const [inputText, setInputText] = useState('');
  const [projectSpec, setProjectSpec] = useState<ProjectSpec | null>(null);
  const [schematicData, setSchematicData] = useState<SchematicData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');

  // 重置状态
  useEffect(() => {
    if (!isOpen) {
      setStep('input');
      setInputText('');
      setProjectSpec(null);
      setSchematicData(null);
      setError(null);
      setProgress('');
    }
  }, [isOpen]);

  // 处理提交
  const handleSubmit = async () => {
    if (!inputText.trim()) {
      setError('请输入项目需求描述');
      return;
    }

    setStep('analyzing');
    setError(null);
    setProgress('正在分析需求...');

    try {
      // 调用 AI 分析 API
      const response = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirements: inputText })
      });

      if (!response.ok) {
        // 尝试从响应中获取详细错误信息
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'AI 分析失败，请重试');
        } catch (e: any) {
          if (e.message === 'AI 分析失败，请重试') {
            throw e;
          }
          // 如果无法解析JSON，使用默认消息
          throw new Error(`AI 分析失败 (${response.status}): 请重试`);
        }
      }

      const data = await response.json();

      setProgress('正在生成项目方案...');
      setProjectSpec(data.spec);

      setProgress('正在生成原理图...');
      setSchematicData(data.schematic);

      setStep('preview');
    } catch (err: any) {
      setError(err.message || '分析过程出错，请重试');
      setStep('error');
    }
  };

  // 处理确认创建
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
      setError(err.message || '创建项目失败，请重试');
    }
  };

  // 处理放弃
  const handleAbandon = () => {
    onClose();
  };

  // 处理返回修改
  const handleBack = () => {
    setStep('input');
    setProjectSpec(null);
    setSchematicData(null);
  };

  // 处理重试
  const handleRetry = () => {
    setStep('input');
    setError(null);
  };

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay">
      <div className="dialog-container">
        {/* 标题栏 */}
        <div className="dialog-header">
          <h2>AI 智能创建项目</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* 内容区 */}
        <div className="dialog-content">
          {/* 输入步骤 */}
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
                提示：描述越详细，生成的项目方案越准确
              </p>
              {error && <p className="error-message">{error}</p>}
            </div>
          )}

          {/* 分析步骤 */}
          {step === 'analyzing' && (
            <div className="step-analyzing">
              <div className="spinner"></div>
              <p className="progress-text">{progress}</p>
            </div>
          )}

          {/* 预览步骤 */}
          {step === 'preview' && projectSpec && (
            <div className="step-preview">
              {/* 项目方案 */}
              <div className="spec-section">
                <h3>项目方案</h3>
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

                  {projectSpec.components.length > 0 && (
                    <>
                      <h5>器件选型</h5>
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
                    </>
                  )}
                </div>
              </div>

              {/* 原理图预览 */}
              {schematicData && (
                <div className="schematic-section">
                  <h3>原理图预览</h3>
                  <div className="schematic-preview">
                    <p>器件数量: {schematicData.components.length}</p>
                    <p>导线数量: {schematicData.wires.length}</p>
                    <p>网络数量: {schematicData.nets.length}</p>

                    {/* 通用原理图可视化预览 */}
                    <div className="schematic-canvas-wrapper">
                      <svg
                        className="schematic-canvas"
                        viewBox="0 0 500 400"
                        preserveAspectRatio="xMidYMid meet"
                      >
                        {/* 绘制网格背景 */}
                        <defs>
                          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1a3a5a" strokeWidth="0.5"/>
                          </pattern>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#grid)" />

                        {/* 绘制导线 - 放在底层 */}
                        {schematicData.wires?.map((wire: any, index: number) => {
                          const points = wire.points || [];
                          if (points.length < 2) return null;

                          // 创建路径
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
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          );
                        })}

                        {/* 绘制元件 */}
                        {schematicData.components.map((comp: any, index: number) => {
                          const x = comp.position?.x || 50;
                          const y = comp.position?.y || 50;

                          // 根据元件类型选择颜色和符号
                          const isPower = comp.name?.includes('电容') || comp.name?.includes('电源') || comp.name?.includes('变压器');
                          const isResistor = comp.name?.includes('电阻');
                          const isDiode = comp.name?.includes('二极管') || comp.name?.includes('整流');
                          const isLED = comp.name?.includes('LED') || comp.name?.includes('灯');
                          const isIC = comp.name?.includes('芯片') || comp.name?.includes('定时器') || comp.name?.includes('555');
                          const isConnector = comp.name?.includes('接口') || comp.name?.includes('排针');
                          const isFuse = comp.name?.includes('保险') || comp.name?.includes('丝');

                          const color = isPower ? '#FF9800' :
                                       isResistor ? '#9C27B0' :
                                       isDiode ? '#E91E63' :
                                       isLED ? '#4CAF50' :
                                       isIC ? '#2196F3' :
                                       isConnector ? '#00BCD4' :
                                       isFuse ? '#F44336' : '#607D8B';

                          const symbol = isPower ? '⚡' :
                                       isResistor ? '▣' :
                                       isDiode ? '▶' :
                                       isLED ? '💡' :
                                       isIC ? '⬡' :
                                       isConnector ? '🔌' :
                                       isFuse ? '⛑' : '⬡';

                          return (
                            <g key={comp.id || `comp-${index}`} transform={`translate(${x - 30}, ${y - 20})`}>
                              {/* 元件框 */}
                              <rect
                                x="0"
                                y="0"
                                width="60"
                                height="40"
                                rx="6"
                                fill={color}
                                fillOpacity="0.2"
                                stroke={color}
                                strokeWidth="2"
                              />
                              {/* 元件符号 */}
                              <text x="30" y="18" textAnchor="middle" fontSize="16">{symbol}</text>
                              {/* 元件名称 */}
                              <text x="30" y="32" textAnchor="middle" fontSize="8" fill="#fff">
                                {comp.name?.substring(0, 8) || 'Component'}
                              </text>
                              {/* 元件引脚 */}
                              <circle cx="0" cy="20" r="3" fill="#fff"/>
                              <circle cx="60" cy="20" r="3" fill="#fff"/>
                            </g>
                          );
                        })}

                        {/* 绘制网络标签 */}
                        {schematicData.nets?.map((net: any, index: number) => {
                          return (
                            <text
                              key={net.id || `net-${index}`}
                              x="450"
                              y={30 + index * 20}
                              fontSize="12"
                              fill={net.name === 'VCC' ? '#4CAF50' : net.name === 'GND' ? '#F44336' : '#2196F3'}
                            >
                              {net.name}
                            </text>
                          );
                        })}
                      </svg>
                    </div>

                    {/* 元件列表详情 */}
                    <div className="schematic-components-detail">
                      <h4>器件清单</h4>
                      <div className="component-cards">
                        {schematicData.components.map((comp: any, index: number) => (
                          <div key={comp.id || index} className="component-card">
                            <span className="card-symbol">
                              {comp.name?.includes('电容') ? '⚡' :
                               comp.name?.includes('电阻') ? '▣' :
                               comp.name?.includes('LED') ? '💡' :
                               comp.name?.includes('二极管') ? '▶' :
                               comp.name?.includes('保险') ? '⛑' : '⬡'}
                            </span>
                            <div className="card-info">
                              <div className="card-name">{comp.name}</div>
                              <div className="card-model">{comp.model}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 错误步骤 */}
          {step === 'error' && (
            <div className="step-error">
              <p className="error-text">{error}</p>
              {(error?.includes('余额') || error?.includes('API') || error?.includes('智谱')) && (
                <p className="error-hint">请访问 https://open.bigmodel.cn/ 检查API余额</p>
              )}
              <button className="retry-btn" onClick={handleRetry}>
                重新输入
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
                onClick={handleSubmit}
                disabled={!inputText.trim()}
              >
                开始分析
              </button>
            </>
          )}

          {step === 'preview' && (
            <>
              <button className="back-btn" onClick={handleBack}>
                返回修改
              </button>
              <button className="abandon-btn" onClick={handleAbandon}>
                放弃
              </button>
              <button className="confirm-btn" onClick={handleConfirm}>
                确认创建
              </button>
            </>
          )}

          {step === 'error' && (
            <button className="retry-btn-large" onClick={handleRetry}>
              重新输入
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIProjectDialog;
