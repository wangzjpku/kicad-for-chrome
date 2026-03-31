/**
 * DesignWizard.tsx - 设计向导组件
 *
 * 步骤化的设计确认流程:
 * Step 1: 规划 (Plan) - 显示电路分析结果、层数推荐、元件清单
 * Step 2: 原理图 (Schematic) - 预览生成的原理图
 * Step 3: 布局 (Layout) - 预览PCB布局
 * Step 4: 制造 (Manufacture) - 导出文件确认
 *
 * 每个步骤需要用户确认才能进入下一步
 */

import React, { useState, useCallback } from 'react';
import { ParsedRequirements } from './MadLibsInput';
import { LayerRecommendation } from '../../services/layerCalculator';
import { aiApi, pcbApi, projectApi, exportApi, schematicApi, AIDesignResult, CircuitData, PCBGenerationResult } from '../../services/api';
import SchematicPreview from './SchematicPreview';
import PCBLayoutPreview from './PCBLayoutPreview';
import RoutingPreview from './RoutingPreview';
import GenerationAnimation from './GenerationAnimation';

interface DesignWizardProps {
  requirements: string;
  parsedData: ParsedRequirements;
  layerRecommendation?: LayerRecommendation;
  onComplete: () => void;
  onCancel: () => void;
  onBack: () => void;
}

export type DesignStep = 'plan' | 'schematic' | 'layout' | 'manufacture';

interface StepConfig {
  id: DesignStep;
  title: string;
  icon: string;
  description: string;
}

const STEPS: StepConfig[] = [
  { id: 'plan', title: '规划', icon: '📋', description: '确认电路分析和推荐配置' },
  { id: 'schematic', title: '原理图', icon: '⚡', description: '查看生成的原理图' },
  { id: 'layout', title: '布局', icon: '🔲', description: '确认PCB布局方案' },
  { id: 'manufacture', title: '制造', icon: '📦', description: '导出制造文件' },
];

const THEME = {
  bg: {
    primary: '#1e1e1e',
    secondary: '#2d2d2d',
    panel: '#383838',
    canvas: '#1a1a1a',
  },
  border: {
    default: '#4a4a4a',
  },
  text: {
    primary: '#e0e0e0',
    secondary: '#a0a0a0',
    muted: '#707070',
  },
  accent: {
    primary: '#4a9eff',
    success: '#4caf50',
    warning: '#ff9800',
    error: '#f44336',
  },
};

export const DesignWizard: React.FC<DesignWizardProps> = ({
  requirements,
  parsedData,
  layerRecommendation,
  onComplete,
  onCancel,
  onBack,
}) => {
  const [currentStep, setCurrentStep] = useState<DesignStep>('plan');
  const [stepHistory, setStepHistory] = useState<DesignStep[]>(['plan']);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');
  const [designResult, setDesignResult] = useState<AIDesignResult | null>(null);
  const [circuitData, setCircuitData] = useState<CircuitData | null>(null);
  const [pcbResult, setPcbResult] = useState<PCBGenerationResult | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);

  // Phase 7E: Multi-step agent progress
  const [agentSteps, setAgentSteps] = useState<Array<{
    step: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    message: string;
  }>>([]);

  // 获取步骤索引
  const getStepIndex = (step: DesignStep): number => {
    return STEPS.findIndex(s => s.id === step);
  };

  const currentIndex = getStepIndex(currentStep);

  // 下一步
  const handleNext = useCallback(async () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex < STEPS.length) {
      setIsGenerating(true);
      setGenerationProgress('');

      const nextStep = STEPS[nextIndex];

      // 如果是进入原理图步骤，调用AI生成
      if (nextStep.id === 'schematic') {
        try {
          setGenerationProgress('正在分析需求...');
          const result = await aiApi.designCircuit({
            requirements,
            project_name: `design_${Date.now()}`,
            generator_version: 'v2',
            max_iterations: 3,
            auto_fix: true,
            validate: true,
          });

          setDesignResult(result);

          // 存储电路数据用于预览
          if (result.circuit_data) {
            setCircuitData(result.circuit_data);
          }

          if (!result.success) {
            setGenerationProgress(`生成失败: ${result.message}`);
            // 显示错误但允许继续
          } else {
            setGenerationProgress('原理图生成完成!');
          }
        } catch (error) {
          console.error('AI design failed:', error);
          setGenerationProgress('生成失败，请重试');
        }
      } else if (nextStep.id === 'layout') {
        try {
          setGenerationProgress('正在生成PCB布局...');

          // 从电路数据构建 PCB 生成请求
          const components = (circuitData?.components || []).map((comp: any) => ({
            ref: comp.reference || comp.name || `C${Math.random()}`,
            symbol: comp.symbol_library || comp.name || 'Device:R',
            footprint: comp.footprint || 'Package:DIP-8',
            width: 10.0,
            height: 10.0,
          }));

          const nets = (circuitData?.nets || []).map((net: any, i: number) => ({
            name: net.name || `N${i + 1}`,
            source_ref: net.connections?.[0]?.component || 'U1',
            source_pin: parseInt(net.connections?.[0]?.pin || '1', 10),
            target_ref: net.connections?.[1]?.component || 'U2',
            target_pin: parseInt(net.connections?.[1]?.pin || '1', 10),
          }));

          const layerCount = layerRecommendation?.layer_count || 2;
          const layers = layerCount >= 4
            ? ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
            : ['F.Cu', 'B.Cu'];

          const result = await pcbApi.generate({
            requirements,
            board: {
              width: 100,
              height: 80,
              layers,
            },
            components,
            nets,
            placement_strategy: 'balanced',
            routing_strategy: 'manhattan',
          });

          setPcbResult(result);

          if (!result.success) {
            setGenerationProgress(`布局生成失败: ${result.message}`);
          } else {
            setGenerationProgress('PCB布局生成完成!');
          }
        } catch (error) {
          console.error('PCB generation failed:', error);
          setGenerationProgress('布局生成失败，请重试');
        }
      } else if (nextStep.id === 'manufacture') {
        setGenerationProgress('正在准备制造文件...');
        try {
          // 1. 创建项目（如果还没有）
          let projId = projectId;
          if (!projId) {
            setGenerationProgress('正在创建项目...');
            const projectName = `design_${Date.now()}`;
            const projResult = await projectApi.createProject({
              name: projectName,
              description: `AI Generated: ${requirements.substring(0, 50)}...`,
            });
            if (projResult.success && projResult.data?.id) {
              projId = projResult.data.id;
              setProjectId(projId);
            }
          }

          if (!projId) {
            setGenerationProgress('项目创建失败');
            setIsGenerating(false);
            return;
          }

          // 2. 保存原理图数据
          if (circuitData) {
            setGenerationProgress('正在保存原理图...');
            await schematicApi.saveSchematic(projId, { components: circuitData.components || [], nets: circuitData.nets || [] } as any).catch(() => {});
          }

          // 3. 保存 PCB 数据
          if (pcbResult) {
            setGenerationProgress('正在保存PCB布局...');
            const pcbData = {
              footprints: (pcbResult.placements || []).map((p: any) => ({
                reference: p.reference,
                footprint: p.footprint || 'Unknown',
                position: { x: p.x, y: p.y },
                rotation: p.rotation || 0,
              })),
              tracks: (pcbResult.routes || []).map((r: any) => ({
                net: r.net,
                width: r.width || 0.5,
                points: r.points || [],
                layer: r.layer || 'F.Cu',
              })),
              boardWidth: pcbResult.board_outline?.width || 100,
              boardHeight: pcbResult.board_outline?.height || 80,
            };
            await pcbApi.savePCB(projId, pcbData as any).catch(() => {});
          }

          // 4. 导出制造文件
          setGenerationProgress('正在导出Gerber文件...');
          const gerberResult = await exportApi.exportGerber(projId);
          setGenerationProgress('正在导出BOM...');
          const bomResult = await exportApi.exportBOM(projId);
          setGenerationProgress('正在导出钻孔文件...');
          const drillResult = await exportApi.exportDrill(projId);

          setGenerationProgress('制造文件已准备完成!');
        } catch (error) {
          console.error('Manufacturing export failed:', error);
          setGenerationProgress('制造文件生成失败，请重试');
        }
      } else {
        // 其他步骤模拟进度
        for (let i = 0; i < 3; i++) {
          await new Promise(resolve => setTimeout(resolve, 300));
          setGenerationProgress(`正在生成${nextStep.title}...`);
        }
      }

      await new Promise(resolve => setTimeout(resolve, 500));
      setGenerationProgress('');
      setIsGenerating(false);

      setStepHistory(prev => [...prev, STEPS[nextIndex].id]);
      setCurrentStep(STEPS[nextIndex].id);
    } else {
      onComplete();
    }
  }, [currentIndex, onComplete, requirements, projectId, circuitData, pcbResult]);

  // 上一步
  const handleBack = useCallback(() => {
    if (stepHistory.length > 1) {
      const newHistory = stepHistory.slice(0, -1);
      setStepHistory(newHistory);
      setCurrentStep(newHistory[newHistory.length - 1]);
    } else {
      onBack();
    }
  }, [stepHistory, onBack]);

  // 跳转到特定步骤
  const goToStep = useCallback((step: DesignStep) => {
    const targetIndex = getStepIndex(step);
    const currentIdx = getStepIndex(currentStep);

    // 只能回退，不能跳过
    if (targetIndex <= currentIdx) {
      const newHistory = [...stepHistory.slice(0, targetIndex + 1)];
      setStepHistory(newHistory);
      setCurrentStep(step);
    }
  }, [currentStep, stepHistory]);

  // 渲染步骤指示器
  const renderStepIndicator = () => (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '16px 24px',
      borderBottom: `1px solid ${THEME.border.default}`,
      backgroundColor: THEME.bg.panel,
    }}>
      {STEPS.map((step, index) => {
        const isActive = step.id === currentStep;
        const isPast = getStepIndex(step.id) < currentIndex;
        const isClickable = index <= currentIndex;

        return (
          <React.Fragment key={step.id}>
            <button
              onClick={() => isClickable && goToStep(step.id)}
              disabled={!isClickable}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                backgroundColor: isActive ? THEME.bg.secondary : 'transparent',
                border: `2px solid ${isActive ? THEME.accent.primary : isPast ? THEME.accent.success : THEME.border.default}`,
                borderRadius: 20,
                cursor: isClickable ? 'pointer' : 'not-allowed',
                opacity: isClickable ? 1 : 0.5,
                transition: 'all 0.2s',
              }}
            >
              <span style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                backgroundColor: isActive ? THEME.accent.primary : isPast ? THEME.accent.success : 'transparent',
                border: `2px solid ${isActive ? THEME.accent.primary : isPast ? THEME.accent.success : THEME.border.default}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                color: isActive || isPast ? '#fff' : THEME.text.muted,
              }}>
                {isPast ? '✓' : index + 1}
              </span>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: isActive ? THEME.text.primary : THEME.text.secondary }}>
                  {step.icon} {step.title}
                </div>
              </div>
            </button>

            {index < STEPS.length - 1 && (
              <div style={{
                width: 40,
                height: 2,
                backgroundColor: isPast ? THEME.accent.success : THEME.border.default,
                margin: '0 8px',
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );

  // 渲染规划步骤
  const renderPlanStep = () => (
    <div style={{ padding: 24, maxHeight: 500, overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 16px 0', color: THEME.text.primary, fontSize: 16 }}>
        📋 电路分析与推荐配置
      </h3>

      {/* 需求描述 */}
      <div style={{
        padding: 16,
        backgroundColor: THEME.bg.primary,
        borderRadius: 8,
        marginBottom: 16,
        borderLeft: `3px solid ${THEME.accent.primary}`,
      }}>
        <div style={{ color: THEME.text.muted, fontSize: 11, marginBottom: 4 }}>您的需求</div>
        <div style={{ color: THEME.text.primary, fontSize: 14, lineHeight: 1.6 }}>
          {requirements}
        </div>
      </div>

      {/* 解析的数据 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ color: THEME.text.muted, fontSize: 11, marginBottom: 8 }}>解析结果</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
          {parsedData.device && (
            <div style={infoBoxStyle}>
              <div style={infoLabelStyle}>设备类型</div>
              <div style={infoValueStyle}>{parsedData.device}</div>
            </div>
          )}
          {parsedData.power && (
            <div style={infoBoxStyle}>
              <div style={infoLabelStyle}>电源</div>
              <div style={infoValueStyle}>{parsedData.power}</div>
            </div>
          )}
          {parsedData.useCase && (
            <div style={infoBoxStyle}>
              <div style={infoLabelStyle}>使用场景</div>
              <div style={infoValueStyle}>{parsedData.useCase}</div>
            </div>
          )}
        </div>
        {parsedData.features.length > 0 && (
          <div style={{ ...infoBoxStyle, gridColumn: '1 / -1', marginTop: 8 }}>
            <div style={infoLabelStyle}>功能特性</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
              {parsedData.features.map(f => (
                <span key={f} style={{
                  padding: '4px 10px',
                  backgroundColor: THEME.accent.primary,
                  borderRadius: 12,
                  fontSize: 11,
                  color: '#fff',
                }}>
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 层数推荐 */}
      {layerRecommendation && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: THEME.text.muted, fontSize: 11, marginBottom: 8 }}>推荐PCB层数</div>
          <div style={{
            padding: 16,
            backgroundColor: THEME.bg.primary,
            borderRadius: 8,
            border: `2px solid ${THEME.accent.success}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                fontSize: 32,
                fontWeight: 700,
                color: THEME.accent.success,
              }}>
                {layerRecommendation.layer_count}
              </div>
              <div>
                <div style={{ fontSize: 14, color: THEME.text.primary, fontWeight: 600 }}>
                  层板
                </div>
                <div style={{ fontSize: 12, color: THEME.text.secondary }}>
                  {layerRecommendation.primary_reason}
                </div>
              </div>
            </div>
            {layerRecommendation.reasons.length > 1 && (
              <div style={{ marginTop: 12 }}>
                {layerRecommendation.reasons.slice(1).map((reason, i) => (
                  <div key={i} style={{ fontSize: 12, color: THEME.text.secondary, marginTop: 4 }}>
                    • {reason}
                  </div>
                ))}
              </div>
            )}
            {layerRecommendation.warnings.length > 0 && (
              <div style={{ marginTop: 12, padding: 8, backgroundColor: 'rgba(255,152,0,0.1)', borderRadius: 4 }}>
                {layerRecommendation.warnings.map((warning, i) => (
                  <div key={i} style={{ fontSize: 11, color: THEME.accent.warning }}>
                    ⚠ {warning}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 复杂度 */}
      <div style={{
        padding: 12,
        backgroundColor: THEME.bg.secondary,
        borderRadius: 8,
        border: `1px solid ${THEME.border.default}`,
      }}>
        <div style={{ fontSize: 12, color: THEME.text.secondary }}>
          💡 置信度: <span style={{ color: THEME.accent.success }}>{(layerRecommendation?.confidence ?? 0.9) * 100}%</span>
          {layerRecommendation?.confidence && layerRecommendation.confidence < 0.9 && (
            <span style={{ color: THEME.accent.warning }}> (建议人工复核)</span>
          )}
        </div>
      </div>
    </div>
  );

  // 渲染原理图步骤
  const renderSchematicStep = () => (
    <div style={{ padding: 24, maxHeight: 500, overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 16px 0', color: THEME.text.primary, fontSize: 16 }}>
        ⚡ 原理图预览
      </h3>

      <div style={{
        padding: 40,
        backgroundColor: THEME.bg.canvas,
        borderRadius: 8,
        border: `1px solid ${THEME.border.default}`,
        minHeight: 300,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {isGenerating ? (
          <GenerationAnimation
            stage="generating"
            progress={50}
            message={generationProgress}
            substeps={['分析需求', '选择元件', '生成原理图', '验证连接']}
          />
        ) : designResult ? (
          <>
            <div style={{
              fontSize: 48,
              marginBottom: 16,
              color: designResult.success ? THEME.accent.success : THEME.accent.error
            }}>
              {designResult.success ? '✓' : '✗'}
            </div>
            <div style={{ marginBottom: 8, color: THEME.text.primary, fontWeight: 600 }}>
              {designResult.success ? '原理图生成成功!' : '生成失败'}
            </div>
            <div style={{ fontSize: 13, color: THEME.text.secondary, textAlign: 'center', maxWidth: 400 }}>
              {designResult.message}
            </div>

            {/* Visual schematic preview */}
            {designResult.success && circuitData && circuitData.components && circuitData.components.length > 0 && (
              <div style={{ marginTop: 16, width: '100%', maxWidth: 520 }}>
                <SchematicPreview
                  components={circuitData.components}
                  nets={circuitData.nets || []}
                  width={500}
                  height={280}
                />
                <div style={{ fontSize: 10, color: THEME.text.muted, marginTop: 4, textAlign: 'center' }}>
                  拖拽平移 | 滚轮缩放 | {circuitData.components.length} 个元件, {circuitData.nets?.length || 0} 条网络
                </div>
              </div>
            )}

            {designResult.output_path && (
              <div style={{
                marginTop: 12,
                padding: '8px 12px',
                backgroundColor: THEME.bg.primary,
                borderRadius: 4,
                fontSize: 11,
                color: THEME.text.muted,
              }}>
                输出路径: {designResult.output_path}
              </div>
            )}
            {designResult.errors.length > 0 && (
              <div style={{
                marginTop: 12,
                padding: 8,
                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                borderRadius: 4,
                fontSize: 11,
                color: THEME.accent.error,
                maxWidth: 400,
              }}>
                {designResult.errors.map((err, i) => (
                  <div key={i}>⚠ {String(err.message || JSON.stringify(err))}</div>
                ))}
              </div>
            )}

            {/* AI 助手集成提示 */}
            {designResult.success && (
              <div style={{
                marginTop: 16,
                padding: 12,
                backgroundColor: 'rgba(74, 158, 255, 0.1)',
                borderRadius: 8,
                border: `1px solid ${THEME.accent.primary}`,
                fontSize: 12,
                color: THEME.text.secondary,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 14, marginRight: 6 }}>🤖</span>
                  <span style={{ color: THEME.accent.primary, fontWeight: 500 }}>需要微调原理图？</span>
                </div>
                <div>
                  点击右下角 <span style={{ color: THEME.accent.primary }}>AI 助手</span> 按钮，
                  可以用自然语言描述修改需求，如"把R1的值改为10k"或"添加一个LED指示灯"。
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚡</div>
            <div style={{ marginBottom: 8 }}>原理图将在您确认后生成</div>
            <div style={{ fontSize: 12, color: THEME.text.muted }}>
              基于您的需求: {parsedData.device || '自定义电路'}
            </div>
          </>
        )}
      </div>

      <div style={{
        marginTop: 16,
        padding: 12,
        backgroundColor: THEME.bg.secondary,
        borderRadius: 8,
        fontSize: 12,
        color: THEME.text.secondary,
      }}>
        💡 下一步将根据电路分析结果自动选择符号库并生成原理图
      </div>
    </div>
  );

  // 渲染布局步骤
  const renderLayoutStep = () => (
    <div style={{ padding: 24, maxHeight: 500, overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 16px 0', color: THEME.text.primary, fontSize: 16 }}>
        🔲 PCB布局预览
      </h3>

      <div style={{
        padding: 40,
        backgroundColor: THEME.bg.canvas,
        borderRadius: 8,
        border: `1px solid ${THEME.border.default}`,
        minHeight: 300,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {isGenerating ? (
          <GenerationAnimation
            stage="placing"
            progress={50}
            message={generationProgress}
            substeps={['计算布局', '放置元件', '优化间距', '布线规划']}
          />
        ) : pcbResult ? (
          <>
            <div style={{
              fontSize: 48,
              marginBottom: 16,
              color: pcbResult.success ? THEME.accent.success : THEME.accent.error
            }}>
              {pcbResult.success ? '✓' : '✗'}
            </div>
            <div style={{ marginBottom: 8, color: THEME.text.primary, fontWeight: 600 }}>
              {pcbResult.success ? 'PCB布局生成成功!' : '布局生成失败'}
            </div>
            <div style={{ fontSize: 13, color: THEME.text.secondary, textAlign: 'center', maxWidth: 400 }}>
              {pcbResult.message}
            </div>

            {/* Visual PCB layout + routing preview */}
            {pcbResult.success && (
              <div style={{ marginTop: 16, width: '100%', maxWidth: 520 }}>
                <PCBLayoutPreview
                  placements={(pcbResult.placements || []).map((p: any) => ({
                    reference: p.reference || '',
                    footprint: p.footprint || '',
                    x: p.x || 0,
                    y: p.y || 0,
                    rotation: p.rotation || 0,
                    width: p.width || 5,
                    height: p.height || 3,
                  }))}
                  routes={(pcbResult.routes || []).map((r: any) => ({
                    net: r.net || '',
                    points: r.points || [],
                    layer: r.layer || 'F.Cu',
                    width: r.width || 0.25,
                  }))}
                  boardOutline={{
                    width: pcbResult.board_outline?.width || 100,
                    height: pcbResult.board_outline?.height || 80,
                  }}
                />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 8 }}>
                  {[
                    { label: '元件', value: pcbResult.placements?.length || 0 },
                    { label: '网络', value: pcbResult.routes?.length || 0 },
                    { label: '过孔', value: pcbResult.vias?.length || 0 },
                    { label: '尺寸', value: `${pcbResult.board_outline?.width || 100}×${pcbResult.board_outline?.height || 80}mm` },
                  ].map((item, i) => (
                    <div key={i} style={{ textAlign: 'center', padding: 4, backgroundColor: THEME.bg.primary, borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: THEME.text.muted }}>{item.label}</div>
                      <div style={{ fontSize: 13, color: THEME.text.primary, fontWeight: 600 }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI 助手集成提示 */}
            {pcbResult?.success && (
              <div style={{
                marginTop: 16,
                padding: 12,
                backgroundColor: 'rgba(74, 158, 255, 0.1)',
                borderRadius: 8,
                border: `1px solid ${THEME.accent.primary}`,
                fontSize: 12,
                color: THEME.text.secondary,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 14, marginRight: 6 }}>🤖</span>
                  <span style={{ color: THEME.accent.primary, fontWeight: 500 }}>需要调整布局？</span>
                </div>
                <div>
                  点击右下角 <span style={{ color: THEME.accent.primary }}>AI 助手</span> 按钮，
                  可以用自然语言描述修改需求，如"把晶振移到右下角"或"增加电源和地之间的距离"。
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🔲</div>
            <div style={{ marginBottom: 8 }}>PCB布局将在您确认后生成</div>
            <div style={{ fontSize: 12, color: THEME.text.muted }}>
              推荐层数: {layerRecommendation?.layer_count ?? 2}层
            </div>
          </>
        )}
      </div>

      <div style={{
        marginTop: 16,
        padding: 12,
        backgroundColor: THEME.bg.secondary,
        borderRadius: 8,
        fontSize: 12,
        color: THEME.text.secondary,
      }}>
        💡 布局将考虑信号完整性、热管理和元件间距优化
      </div>
    </div>
  );

  // 渲染制造步骤
  const renderManufactureStep = () => (
    <div style={{ padding: 24, maxHeight: 500, overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 16px 0', color: THEME.text.primary, fontSize: 16 }}>
        📦 导出制造文件
      </h3>

      {/* 设计摘要 */}
      <div style={{
        padding: 16,
        backgroundColor: THEME.bg.primary,
        borderRadius: 8,
        marginBottom: 16,
        borderLeft: `3px solid ${THEME.accent.primary}`,
      }}>
        <div style={{ fontSize: 12, color: THEME.text.muted, marginBottom: 8 }}>设计摘要</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
          <div style={{ fontSize: 12 }}>
            <span style={{ color: THEME.text.muted }}>原理图元件: </span>
            <span style={{ color: THEME.text.primary }}>{circuitData?.components?.length || 0}</span>
          </div>
          <div style={{ fontSize: 12 }}>
            <span style={{ color: THEME.text.muted }}>PCB元件: </span>
            <span style={{ color: THEME.text.primary }}>{pcbResult?.placements?.length || 0}</span>
          </div>
          <div style={{ fontSize: 12 }}>
            <span style={{ color: THEME.text.muted }}>推荐层数: </span>
            <span style={{ color: THEME.text.primary }}>{layerRecommendation?.layer_count || 2}层</span>
          </div>
          <div style={{ fontSize: 12 }}>
            <span style={{ color: THEME.text.muted }}>网络数量: </span>
            <span style={{ color: THEME.text.primary }}>{pcbResult?.routes?.length || (circuitData?.nets?.length || 0)}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {[
          { icon: '📄', name: 'Gerber文件', desc: 'PCB制造文件 (.gbr)', checked: true },
          { icon: '🔧', name: '钻孔文件', desc: 'NC Drill (.drl)', checked: true },
          { icon: '📋', name: 'BOM物料清单', desc: '元件采购清单 (.csv)', checked: true },
          { icon: '📐', name: 'STEP文件', desc: '3D模型 (.step)', checked: false },
        ].map((item, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: 16,
              backgroundColor: THEME.bg.primary,
              borderRadius: 8,
              border: `1px solid ${item.checked ? THEME.accent.success : THEME.border.default}`,
            }}
          >
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 8,
              backgroundColor: THEME.bg.secondary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              marginRight: 12,
            }}>
              {item.icon}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, color: THEME.text.primary, fontWeight: 500 }}>
                {item.name}
              </div>
              <div style={{ fontSize: 12, color: THEME.text.secondary }}>
                {item.desc}
              </div>
            </div>
            <div style={{
              width: 24,
              height: 24,
              borderRadius: '50%',
              backgroundColor: item.checked ? THEME.accent.success : 'transparent',
              border: `2px solid ${item.checked ? THEME.accent.success : THEME.border.default}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              color: '#fff',
            }}>
              {item.checked ? '✓' : ''}
            </div>
          </div>
        ))}
      </div>

      <div style={{
        marginTop: 16,
        padding: 12,
        backgroundColor: 'rgba(74, 158, 255, 0.1)',
        borderRadius: 8,
        border: `1px solid ${THEME.accent.primary}`,
        fontSize: 12,
        color: THEME.text.secondary,
      }}>
        📌 点击「完成」将生成所有选中的文件。文件将保存到您的项目目录，可通过项目菜单下载。
      </div>
    </div>
  );

  // 渲染当前步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 'plan':
        return renderPlanStep();
      case 'schematic':
        return renderSchematicStep();
      case 'layout':
        return renderLayoutStep();
      case 'manufacture':
        return renderManufactureStep();
      default:
        return null;
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.7)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        width: 700,
        maxWidth: '95vw',
        maxHeight: '90vh',
        backgroundColor: THEME.bg.secondary,
        borderRadius: 12,
        boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: `1px solid ${THEME.border.default}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: THEME.text.primary }}>
              设计向导
            </div>
            <div style={{ fontSize: 12, color: THEME.text.muted, marginTop: 2 }}>
              步骤 {currentIndex + 1}/4: {STEPS[currentIndex].description}
            </div>
          </div>
          <button
            onClick={onCancel}
            style={{
              background: 'none',
              border: 'none',
              color: THEME.text.muted,
              cursor: 'pointer',
              fontSize: 20,
              padding: 4,
            }}
          >
            ×
          </button>
        </div>

        {/* Step Indicator */}
        {renderStepIndicator()}

        {/* Content */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {renderStepContent()}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 20px',
          borderTop: `1px solid ${THEME.border.default}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: THEME.bg.panel,
        }}>
          <button
            onClick={handleBack}
            disabled={currentStep === 'plan' && stepHistory.length === 1}
            style={{
              padding: '10px 20px',
              backgroundColor: 'transparent',
              border: `1px solid ${THEME.border.default}`,
              borderRadius: 6,
              color: THEME.text.secondary,
              fontSize: 13,
              cursor: currentStep === 'plan' && stepHistory.length === 1 ? 'not-allowed' : 'pointer',
              opacity: currentStep === 'plan' && stepHistory.length === 1 ? 0.5 : 1,
            }}
          >
            ← 上一步
          </button>

          <button
            onClick={handleNext}
            disabled={isGenerating}
            style={{
              padding: '10px 24px',
              backgroundColor: THEME.accent.primary,
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              fontSize: 13,
              fontWeight: 500,
              cursor: isGenerating ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            {isGenerating ? (
              <>
                <span style={{ animation: 'spin 1s linear infinite' }}>⟳</span>
                生成中...
              </>
            ) : currentIndex === STEPS.length - 1 ? (
              <>完成设计 ✓</>
            ) : (
              <>下一步 →</>
            )}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

const infoBoxStyle: React.CSSProperties = {
  padding: 12,
  backgroundColor: '#252525',
  borderRadius: 6,
  border: `1px solid ${THEME.border.default}`,
};

const infoLabelStyle = {
  fontSize: 10,
  color: THEME.text.muted,
  marginBottom: 2,
};

const infoValueStyle = {
  fontSize: 13,
  color: THEME.text.primary,
  fontWeight: 500,
};

export default DesignWizard;
