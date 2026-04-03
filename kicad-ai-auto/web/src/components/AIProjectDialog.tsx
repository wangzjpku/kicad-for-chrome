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
import { useSchematicStore } from '../stores/schematicStore';
import { useAuthStore } from '../stores/authStore';
import './AIProjectDialog.css';

interface AIProjectDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: CreatedProject) => void;
}

// 创建的项目返回类型
interface CreatedProject {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived' | 'deleted';
  schematic?: SchematicData;
  pcb?: Record<string, unknown>;
  createdAt?: string;
  updatedAt?: string;
  ownerId?: string;
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

// 原理图元件类型
interface SchematicComponent {
  id: string;
  name: string;
  model: string;
  reference: string;
  position: { x: number; y: number };
  pins: Array<{ number: string; name: string; position: { x: number; y: number } }>;
}

// 导线类型
interface SchematicWire {
  id: string;
  points: Array<{ x: number; y: number }>;
  net?: string;
}

// 网络类型
interface SchematicNet {
  id: string;
  name: string;
}

interface SchematicData {
  components: SchematicComponent[];
  wires: SchematicWire[];
  nets: SchematicNet[];
}

// PCB 数据类型
interface PCBData {
  width: number;
  height: number;
  layers: number;
  thickness: number;
  silkscreen: boolean;
  soldermask: string;
  components: Array<{
    id: string;
    reference: string;
    footprint: string;
    position: { x: number; y: number };
    rotation: number;
  }>;
  nets: Array<{
    id: string;
    name: string;
  }>;
  traces: Array<{
    net: string;
    width: number;
    points: Array<{ x: number; y: number }>;
  }>;
}

// PCB 参数
interface PCBParams {
  width: number;
  height: number;
  layers: number;
  thickness: number;
  silkscreen: boolean;
  soldermask: string;
}

type DialogStep =
  | 'input'           // 输入需求
  | 'clarifying'      // 明确细节
  | 'analyzing'       // 分析中
  | 'schematic_preview' // 原理图预览
  | 'pcb_params'     // PCB 参数询问
  | 'pcb_preview'    // PCB 预览
  | 'editing'         // 编辑确认
  | 'generating'      // 生成项目
  | 'confirm'         // 最终确认
  | 'error';          // 错误

// H3 Fix: BOM去重函数 - 合并相同(name, model, package)的元件，累加数量
function deduplicateComponents(components: ComponentSpec[]): ComponentSpec[] {
  const seen = new Map<string, ComponentSpec>();
  for (const comp of components) {
    const key = `${comp.name}|${comp.model}|${comp.package || comp.footprint || ''}`;
    if (seen.has(key)) {
      const existing = seen.get(key)!;
      existing.quantity += comp.quantity || 1;
    } else {
      seen.set(key, { ...comp, quantity: comp.quantity || 1 });
    }
  }
  return Array.from(seen.values());
}

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
  const [pcbData, setPcbData] = useState<PCBData | null>(null);
  const [pcbParams, setPcbParams] = useState<PCBParams>({
    width: 100,
    height: 80,
    layers: 2,
    thickness: 1.6,
    silkscreen: true,
    soldermask: 'green'
  });
  const [error, setError] = useState<string | null>(null);

  // 缩放和拖动状态
  const [schematicZoom, setSchematicZoom] = useState(1);
  const [schematicPan, setSchematicPan] = useState({ x: 0, y: 0 });
  const [isDraggingSchematic, setIsDraggingSchematic] = useState(false);
  const [dragStartSchematic, setDragStartSchematic] = useState({ x: 0, y: 0 });

  const [pcbZoom, setPcbZoom] = useState(1);
  const [pcbPan, setPcbPan] = useState({ x: 0, y: 0 });
  const [isDraggingPcb, setIsDraggingPcb] = useState(false);
  const [dragStartPcb, setDragStartPcb] = useState({ x: 0, y: 0 });
  const [progress, setProgress] = useState<string>('');

  // 编辑状态
  const [editingComponent, setEditingComponent] = useState<number | null>(null);
  const [editingParameter, setEditingParameter] = useState<number | null>(null);
  const [tempComponent, setTempComponent] = useState<ComponentSpec | null>(null);
  const [tempParameter, setTempParameter] = useState<ParameterSpec | null>(null);

// 最终结果类型
interface FinalResult {
  project: CreatedProject;
  schematic: SchematicData;
  message: string;
}

// 上传文件类型
interface UploadedFile {
  id: string;
  name: string;
  path: string;
  type: string;
  size: number;
}

  // 最终结果
  const [finalResult, setFinalResult] = useState<FinalResult | null>(null);

  // 文件上传状态
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [fileInputValue, setFileInputValue] = useState('');

  // 重置状态
  useEffect(() => {
    if (!isOpen) {
      setStep('input');
      setInputText('');
      setClarificationData(null);
      setAnswers({});
      setProjectSpec(null);
      setSchematicData(null);
      setPcbData(null);
      setPcbParams({
        width: 100,
        height: 80,
        layers: 2,
        thickness: 1.6,
        silkscreen: true,
        soldermask: 'green'
      });
      setError(null);
      setProgress('');
      setEditingComponent(null);
      setEditingParameter(null);
      setFinalResult(null);
      setUploadedFiles([]);
      setFileInputValue('');
      // 重置缩放和拖动状态
      setSchematicZoom(1);
      setSchematicPan({ x: 0, y: 0 });
      setPcbZoom(1);
      setPcbPan({ x: 0, y: 0 });
    }
  }, [isOpen]);

  // ========== 缩放和拖动处理函数 ==========
  // 原理图缩放
  const handleSchematicWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.2, Math.min(5, schematicZoom * delta));
    setSchematicZoom(newZoom);
  };

  // 原理图拖动开始
  const handleSchematicMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDraggingSchematic(true);
      setDragStartSchematic({ x: e.clientX - schematicPan.x, y: e.clientY - schematicPan.y });
    }
  };

  // 原理图拖动中
  const handleSchematicMouseMove = (e: React.MouseEvent) => {
    if (isDraggingSchematic) {
      setSchematicPan({
        x: e.clientX - dragStartSchematic.x,
        y: e.clientY - dragStartSchematic.y
      });
    }
  };

  // 原理图拖动结束
  const handleSchematicMouseUp = () => {
    setIsDraggingSchematic(false);
  };

  // PCB 缩放
  const handlePcbWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.2, Math.min(5, pcbZoom * delta));
    setPcbZoom(newZoom);
  };

  // PCB 拖动开始
  const handlePcbMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDraggingPcb(true);
      setDragStartPcb({ x: e.clientX - pcbPan.x, y: e.clientY - pcbPan.y });
    }
  };

  // PCB 拖动中
  const handlePcbMouseMove = (e: React.MouseEvent) => {
    if (isDraggingPcb) {
      setPcbPan({
        x: e.clientX - dragStartPcb.x,
        y: e.clientY - dragStartPcb.y
      });
    }
  };

  // PCB 拖动结束
  const handlePcbMouseUp = () => {
    setIsDraggingPcb(false);
  };

  // 重置视图
  const resetSchematicView = () => {
    setSchematicZoom(1);
    setSchematicPan({ x: 0, y: 0 });
  };

  const resetPcbView = () => {
    setPcbZoom(1);
    setPcbPan({ x: 0, y: 0 });
  };

  // ========== Step 1: 提交需求，获取澄清问题 ==========
  const handleSubmitRequirements = async () => {
    if (!inputText.trim()) {
      setError('请输入项目需求描述');
      return;
    }

    setStep('analyzing');
    setError(null);
    setProgress('正在分析需求...');

    // 创建超时控制器 (30秒超时)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      // 获取认证token
      const token = useAuthStore.getState().token;
      const authHeaders = token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };

      // 尝试调用 clarify API（包含文件信息）
      const clarifyResponse = await fetch('/api/v1/ai/clarify', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          requirements: inputText,
          attachments: uploadedFiles.map(f => ({
            name: f.name,
            path: f.path,
            type: f.type
          }))
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (clarifyResponse.ok) {
        const data: ClarificationResponse = await clarifyResponse.json();

        // 初始化默认答案（H1 Fix: 不自动选择，让用户主动选择）
        const defaultAnswers: Record<string, string> = {};
        data.questions.forEach(q => {
          if (q.default) {
            defaultAnswers[q.id] = q.default;
          }
          // 不再自动选择第一个选项，避免"220V AC"等错误预选
        });

        setAnswers(defaultAnswers);
        setClarificationData(data);
        setStep('clarifying');
      } else {
        await directAnalyze();
      }

    } catch (err: unknown) {
      clearTimeout(timeoutId);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      // 如果是超时或网络错误，回退到 directAnalyze
      const errorName = err instanceof Error ? err.name : '';
      if (errorName === 'AbortError' || errorName === 'TypeError') {
        try {
          await directAnalyze();
        } catch (analyzeErr: unknown) {
          const analyzeMessage = analyzeErr instanceof Error ? analyzeErr.message : '分析过程出错';
          setError(analyzeMessage);
          setStep('error');
        }
      } else {
        try {
          await directAnalyze();
        } catch (analyzeErr: unknown) {
          const analyzeMessage = analyzeErr instanceof Error ? analyzeErr.message : '分析过程出错';
          setError(analyzeMessage);
          setStep('error');
        }
      }
    }
  };

  // 直接调用 analyze API（旧流程）
  const directAnalyze = async () => {
    setProgress('正在生成方案...');

    // 创建超时控制器 (120秒超时 - AI分析可能需要更长时间)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      // 获取认证token
      const token = useAuthStore.getState().token;
      const authHeaders = token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };

      const response = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          requirements: inputText,
          answers: {},
          attachments: uploadedFiles.map(f => ({
            name: f.name,
            path: f.path,
            type: f.type
          }))
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'AI 分析失败');
      }

      const data = await response.json();

      setProgress('正在生成项目方案...');
      // H3 Fix: 对AI返回的BOM进行去重
      const dedupedSpec = {
        ...data.spec,
        components: deduplicateComponents(data.spec?.components || []),
      };
      setProjectSpec(dedupedSpec);

      // 从AI返回的参数中提取PCB尺寸
      if (data.spec?.parameters) {
        const pcbSizeParam = data.spec.parameters.find(
          (p: ParameterSpec) => p.key === 'PCB尺寸' || p.key === 'pcb_size' || p.key === 'PCB尺寸(mm)'
        );
        if (pcbSizeParam?.value) {
          const sizeMatch = pcbSizeParam.value.match(/(\d+)\s*[xX*×]\s*(\d+)/);
          if (sizeMatch) {
            const width = parseInt(sizeMatch[1], 10);
            const height = parseInt(sizeMatch[2], 10);
            if (width > 0 && height > 0) {
              setPcbParams(prev => ({ ...prev, width, height }));
            }
          }
        }
      }

      setProgress('正在生成原理图...');
      setSchematicData(data.schematic);

      setStep('schematic_preview');
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if (err instanceof Error && err.name === 'AbortError') {
        throw new Error('AI 分析超时 (120秒)，请检查网络连接或稍后重试');
      }
      throw err;
    }
  };

  // ========== Step 2: 提交答案，生成方案 ==========
  const handleSubmitAnswers = async () => {
    setStep('analyzing');
    setError(null);
    setProgress('正在生成原理图方案...');

    // 创建超时控制器 (120秒超时 - AI分析可能需要更长时间)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      // 获取认证token
      const token = useAuthStore.getState().token;
      const authHeaders = token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };

      const response = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          requirements: inputText,
          answers: answers,
          attachments: uploadedFiles.map(f => ({
            name: f.name,
            path: f.path,
            type: f.type
          })),
          mode: 'schematic_only'  // 只生成原理图
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '生成方案失败');
      }

      const data = await response.json();

      setProgress('正在生成项目方案...');
      // H3 Fix: 对AI返回的BOM进行去重
      const dedupedSpec = {
        ...data.spec,
        components: deduplicateComponents(data.spec?.components || []),
      };
      setProjectSpec(dedupedSpec);

      // 从AI返回的参数中提取PCB尺寸
      if (data.spec?.parameters) {
        const pcbSizeParam = data.spec.parameters.find(
          (p: ParameterSpec) => p.key === 'PCB尺寸' || p.key === 'pcb_size' || p.key === 'PCB尺寸(mm)'
        );
        if (pcbSizeParam?.value) {
          // 解析尺寸格式: "50x40" 或 "50*40" 或 "50×40"
          const sizeMatch = pcbSizeParam.value.match(/(\d+)\s*[xX*×]\s*(\d+)/);
          if (sizeMatch) {
            const width = parseInt(sizeMatch[1], 10);
            const height = parseInt(sizeMatch[2], 10);
            if (width > 0 && height > 0) {
              setPcbParams(prev => ({ ...prev, width, height }));
            }
          }
        }
      }

      setProgress('正在生成原理图...');
      setSchematicData(data.schematic);

      // 跳转到原理图预览步骤
      setStep('schematic_preview');

    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if (err instanceof Error && err.name === 'AbortError') {
        setError('AI 分析超时 (120秒)，请检查网络连接或稍后重试。如果问题持续，请联系管理员检查后端 AI 服务配置。');
      } else {
        const errorMessage = err instanceof Error ? err.message : '生成方案出错';
        setError(errorMessage);
      }
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
    setStep('schematic_preview');
    setEditingComponent(null);
    setEditingParameter(null);
  };

  // ========== Step 3: 提交方案，生成最终结果 ==========
  const handleSubmitForGeneration = async () => {
    setStep('generating');
    setError(null);
    setProgress('正在生成最终项目...');

    // 创建超时控制器 (120秒超时)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      // Start project creation

      // 确保projectSpec和schematicData有值
      if (!projectSpec) {
        throw new Error('项目规格不存在，请重新开始');
      }

      // 构建请求数据 - 确保所有字段都有值
      const requestData = {
        name: projectSpec?.name || 'AI生成项目',
        description: projectSpec?.description || '',
        components: projectSpec?.components || [],
        parameters: projectSpec?.parameters || [],
        schematicData: schematicData || { components: [], wires: [], nets: [], netLabels: [], powerSymbols: [] },
        pcbData: pcbData || null,  // PCB数据
        pcbParams: pcbParams || null  // PCB参数
      };

      // 获取认证token
      const token = useAuthStore.getState().token;
      const authHeaders = token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };

      const response = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify(requestData),
        signal: controller.signal
      });


      clearTimeout(timeoutId);


      if (!response.ok) {
        // 处理409冲突错误（项目名称已存在）
        if (response.status === 409) {
          // 自动重命名项目（添加时间戳）
          const timestamp = Date.now();
          requestData.name = `${requestData.name}-${timestamp}`;

          const retryResponse = await fetch('/api/v1/projects', {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(requestData),
            signal: controller.signal
          });

          clearTimeout(timeoutId);

          if (!retryResponse.ok) {
            throw new Error('创建项目失败: ' + retryResponse.status);
          }

          const result = await retryResponse.json();
          const finalRes = result.project ? result : {
            project: result,
            schematic: null,
            message: '项目创建成功'
          };
          setFinalResult(finalRes);
          setStep('confirm');
          return;
        }
        const errorText = await response.text(); void errorText;
        throw new Error('创建项目失败: ' + response.status);
      }

      const result = await response.json();

      // 处理API返回格式：直接返回项目对象或包装格式
      const finalRes = result.project ? result : {
        project: result,
        schematic: null,
        message: '项目创建成功'
      };
      setFinalResult(finalRes);
      setStep('confirm');

    } catch (err: unknown) {
      clearTimeout(timeoutId);

      if (err instanceof Error && err.name === 'AbortError') {
        setError('创建项目超时，请稍后重试');
      } else {
        const errorMessage = err instanceof Error ? err.message : '生成最终结果失败';
        setError(errorMessage);
      }
      // 即使出错也进入confirm阶段，允许用户重试
      setStep('confirm');
    }
  };

  // ========== Step 4: 确认最终结果 ==========
  const handleFinalConfirm = () => {
    if (finalResult && finalResult.project) {
      onProjectCreated(finalResult.project);
      onClose();
    }
  };

  // 处理返回修改
  // 确认原理图，进入 PCB 参数步骤
  const confirmSchematic = () => {
    setStep('pcb_params');
  };

  // 提交 PCB 参数，生成 PCB 方案
  const handleSubmitPcbParams = async () => {
    setStep('analyzing');
    setError(null);
    setProgress('正在生成 PCB 方案...');

    // 创建超时控制器 (60秒超时)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      // 获取认证token
      const token = useAuthStore.getState().token;
      const authHeaders = token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };

      const response = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          requirements: inputText,
          answers: answers,
          attachments: uploadedFiles.map(f => ({
            name: f.name,
            path: f.path,
            type: f.type
          })),
          mode: 'pcb_only',
          pcb_params: pcbParams,
          schematic: schematicData
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '生成PCB方案失败');
      }

      const data = await response.json();
      setPcbData(data.pcb);
      setStep('pcb_preview');

    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if (err instanceof Error && err.name === 'AbortError') {
        setError('PCB 生成超时 (60秒)，请检查网络连接或稍后重试');
      } else {
        const errorMessage = err instanceof Error ? err.message : '生成PCB方案出错';
        setError(errorMessage);
      }
      setStep('error');
    }
  };

  const handleBack = () => {
    if (step === 'clarifying') {
      setStep('input');
    } else if (step === 'schematic_preview') {
      setStep('clarifying');
    } else if (step === 'pcb_params') {
      setStep('schematic_preview');
    } else if (step === 'pcb_preview' || step === 'editing') {
      setStep('pcb_params');
    } else if (step === 'confirm') {
      setStep('pcb_preview');
    } else if (step === 'error') {
      setStep('input');
      setError(null);
    }
  };

  // 计算已回答的问题数量（只计算必答问题）
  const getAnsweredCount = () => {
    if (!clarificationData) return 0;
    const requiredQuestions = clarificationData.questions.filter(q => q.required);
    let count = 0;
    requiredQuestions.forEach(q => {
      // H1 Fix: 只要用户选择了答案（不为空）就算已回答
      if (answers[q.id] && answers[q.id].trim() !== '') {
        count++;
      }
    });
    return count;
  };

  // 更新答案
  const updateAnswer = (questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  };

  // 跳过可选问题
  const handleSkipOptional = () => {
    handleSubmitAnswers();
  };

  // ========== 文件上传功能 ==========

  // 处理文件路径输入
  const handleFilePathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFileInputValue(e.target.value);
  };

  // 添加文件到列表
  const handleAddFile = () => {
    const filePath = fileInputValue.trim();
    if (!filePath) return;

    // 检查文件是否已存在
    if (uploadedFiles.some(f => f.path === filePath)) {
      setError('该文件已添加');
      setTimeout(() => setError(null), 2000);
      return;
    }

    // 提取文件名
    const fileName = filePath.split(/[/\\]/).pop() || filePath;

    // 根据文件扩展名判断类型
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    let fileType = 'other';
    if (ext === 'pdf') fileType = 'pdf';
    else if (['sch', 'schdoc'].includes(ext)) fileType = 'schematic';
    else if (['kicad_pcb', 'pcb'].includes(ext)) fileType = 'pcb';
    else if (['bom', 'csv'].includes(ext)) fileType = 'bom';
    else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)) fileType = 'image';

    const newFile: UploadedFile = {
      id: Date.now().toString(),
      name: fileName,
      path: filePath,
      type: fileType,
      size: 0
    };

    setUploadedFiles([...uploadedFiles, newFile]);
    setFileInputValue('');
    setError(null);
  };

  // 移除文件
  const handleRemoveFile = (fileId: string) => {
    setUploadedFiles(uploadedFiles.filter(f => f.id !== fileId));
  };

  // 获取文件类型图标
  const getFileTypeIcon = (type: string) => {
    switch (type) {
      case 'pdf': return '📄';
      case 'schematic': return '📐';
      case 'pcb': return '🔲';
      case 'bom': return '📋';
      case 'image': return '🖼️';
      default: return '📁';
    }
  };

  if (!isOpen) return null;

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
          <div className={`progress-step ${step === 'input' ? 'active' : ''} ${['clarifying', 'schematic_preview', 'pcb_params', 'pcb_preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">1</span>
            <span className="step-label">输入需求</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'clarifying' ? 'active' : ''} ${['schematic_preview', 'pcb_params', 'pcb_preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-label">明确细节</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'schematic_preview' ? 'active' : ''} ${['pcb_params', 'pcb_preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-label">原理图确认</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'pcb_params' ? 'active' : ''} ${['pcb_preview', 'editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">4</span>
            <span className="step-label">PCB参数</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'pcb_preview' ? 'active' : ''} ${['editing', 'generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">5</span>
            <span className="step-label">PCB确认</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${['editing'].includes(step) ? 'active' : ''} ${['generating', 'confirm'].includes(step) ? 'completed' : ''}`}>
            <span className="step-number">6</span>
            <span className="step-label">编辑确认</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'generating' ? 'active' : ''} ${step === 'confirm' ? 'completed' : ''}`}>
            <span className="step-number">7</span>
            <span className="step-label">生成项目</span>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step === 'confirm' ? 'active' : ''}`}>
            <span className="step-number">8</span>
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

              {/* 文件上传区域 - 左下角 */}
              <div className="file-upload-section">
                <div className="file-upload-header">
                  <span className="file-upload-icon">📎</span>
                  <span className="file-upload-title">附加参考资料（可选）</span>
                  <span className="file-upload-hint">可添加芯片PDF手册、原理图等参考资料</span>
                </div>

                <div className="file-input-row">
                  <input
                    type="text"
                    className="file-path-input"
                    value={fileInputValue}
                    onChange={handleFilePathChange}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddFile()}
                    placeholder="输入文件路径，例如：C:\docs\chip_manual.pdf"
                  />
                  <button
                    className="browse-btn"
                    onClick={() => {
                      // 触发系统文件选择对话框
                      const input = document.createElement('input');
                      input.type = 'file';
                      input.multiple = false;
                      input.onchange = (e) => {
                        const file = (e.target as HTMLInputElement).files?.[0];
                        if (file) {
                          // 浏览器中 File 对象没有 path，使用 name 并提示用户补全路径
                          setFileInputValue(file.name);
                        }
                      };
                      input.click();
                    }}
                  >
                    📂 浏览
                  </button>
                  <button
                    className="add-file-btn"
                    onClick={handleAddFile}
                    disabled={!fileInputValue.trim()}
                  >
                    + 添加
                  </button>
                </div>

                {/* 已添加的文件列表 */}
                {uploadedFiles.length > 0 && (
                  <div className="file-list">
                    {uploadedFiles.map((file) => (
                      <div key={file.id} className="file-item">
                        <span className="file-icon">{getFileTypeIcon(file.type)}</span>
                        <span className="file-name" title={file.path}>{file.name}</span>
                        <span className="file-type-badge">{file.type.toUpperCase()}</span>
                        <button
                          className="remove-file-btn"
                          onClick={() => handleRemoveFile(file.id)}
                          title="移除文件"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

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
                <p>已回答 {getAnsweredCount()} / {clarificationData.questions.filter(q => q.required).length} 个必答问题</p>
              </div>
            </div>
          )}

          {/* Step 3: 分析中 */}
          {step === 'analyzing' && (
            <div className="step-analyzing">
              <div className="spinner"></div>
              <p className="progress-text">{progress}</p>
              <p className="progress-hint">请稍候，AI 正在分析中...</p>
              {/* 添加取消按钮以支持 T32.3 测试 */}
              <button className="cancel-btn" onClick={onClose}>
                取消
              </button>
            </div>
          )}

          {/* Step 3: 原理图预览和方案 */}
          {(step === 'schematic_preview' || step === 'editing') && projectSpec && (
            <div className="step-preview">
              {/* 原理图预览 */}
              <div className="spec-section">
                <div className="preview-header">
                  <h3>📐 原理图预览</h3>
                  <div className="zoom-controls">
                    <button onClick={() => setSchematicZoom(z => Math.max(0.2, z - 0.2))} title="缩小">➖</button>
                    <span>{Math.round(schematicZoom * 100)}%</span>
                    <button onClick={() => setSchematicZoom(z => Math.min(5, z + 0.2))} title="放大">➕</button>
                    <button onClick={resetSchematicView} title="重置">🔄</button>
                  </div>
                </div>
                <div className="schematic-stats">
                  <p>器件数量: {schematicData?.components.length || 0}</p>
                  <p>导线数量: {schematicData?.wires.length || 0}</p>
                  <p>网络数量: {schematicData?.nets.length || 0}</p>
                </div>

                {schematicData && (
                  <div
                    className="schematic-canvas-wrapper"
                    onWheel={handleSchematicWheel}
                    onMouseDown={handleSchematicMouseDown}
                    onMouseMove={handleSchematicMouseMove}
                    onMouseUp={handleSchematicMouseUp}
                    onMouseLeave={handleSchematicMouseUp}
                    style={{ cursor: isDraggingSchematic ? 'grabbing' : 'grab' }}
                  >
                    <svg
                      className="schematic-canvas"
                      viewBox={`${-schematicPan.x / schematicZoom} ${-schematicPan.y / schematicZoom} ${600 / schematicZoom} ${400 / schematicZoom}`}
                      preserveAspectRatio="xMidYMid meet"
                    >
                      <defs>
                        <pattern id="schematic-grid" width={20 * schematicZoom} height={20 * schematicZoom} patternUnits="userSpaceOnUse">
                          <path d={`M ${20 * schematicZoom} 0 L 0 0 0 ${20 * schematicZoom}`} fill="none" stroke="#1a3a5a" strokeWidth="0.5"/>
                        </pattern>
                      </defs>
                      <rect
                        x={-schematicPan.x / schematicZoom - 1000}
                        y={-schematicPan.y / schematicZoom - 1000}
                        width={2000 / schematicZoom}
                        height={2000 / schematicZoom}
                        fill="url(#schematic-grid)"
                      />

                      {/* 绘制导线 */}
                      {schematicData.wires?.map((wire: SchematicWire, index: number) => {
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
                            strokeWidth={2 / schematicZoom}
                          />
                        );
                      })}

                      {/* 绘制元件 */}
                      {schematicData.components.map((comp: SchematicComponent, index: number) => {
                        const x = comp.position?.x || 50;
                        const y = comp.position?.y || 50;
                        const color = '#607D8B';
                        const size = 60 / schematicZoom;
                        return (
                          <g key={comp.id || `comp-${index}`} transform={`translate(${x - size/2}, ${y - size/3})`}>
                            <rect width={size} height={size * 0.67} rx={4/schematicZoom} fill={color} fillOpacity="0.3" stroke={color} strokeWidth={2/schematicZoom}/>
                            <text x={size/2} y={size/4} textAnchor="middle" fontSize={10/schematicZoom} fill="#fff">
                              {comp.reference || comp.name?.substring(0, 8) || 'U'}
                            </text>
                            <text x={size/2} y={size/2} textAnchor="middle" fontSize={8/schematicZoom} fill="#aaa">
                              {comp.name?.substring(0, 8) || 'Component'}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                  </div>
                )}
              </div>

              {/* BOM 器件清单（带封装信息） */}
              <div className="spec-section">
                <h3>📋 器件清单 ({projectSpec.components.length} 个器件)</h3>
                <table className="components-table">
                  <thead>
                    <tr>
                      <th>器件</th>
                      <th>型号</th>
                      <th>KiCad封装</th>
                      <th>数量</th>
                    </tr>
                  </thead>
                  <tbody>
                    {projectSpec.components.map((comp, idx) => (
                      <tr key={idx}>
                        <td>{comp.name}</td>
                        <td>{comp.model}</td>
                        <td className="footprint-cell">{comp.package || comp.footprint || '-'}</td>
                        <td>{comp.quantity}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 工具栏 */}
              <div className="preview-toolbar">
                <button className="edit-mode-btn" onClick={enterEditMode}>
                  ✏️ 进入编辑模式
                </button>
              </div>

              {/* 项目方案 */}
              <div className="spec-section">
                <h3>📦 项目方案 {step === 'editing' && <span className="edit-badge">编辑中</span>}</h3>
                <div className="spec-content">
                  <div className="project-name-edit">
                    {step === 'editing' ? (
                      <input
                        type="text"
                        value={projectSpec.name}
                        onChange={(e) => setProjectSpec({ ...projectSpec, name: e.target.value })}
                        className="project-name-input"
                      />
                    ) : (
                      <h4>{projectSpec.name}</h4>
                    )}
                  </div>
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

                  {/* BOM 器件清单 - 可编辑 */}
                  <h5>
                    📋 器件清单 ({projectSpec.components.length} 个器件)
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
            </div>
          )}

          {/* Step 4: PCB 参数询问 */}
          {step === 'pcb_params' && (
            <div className="step-pcb-params">
              <div className="pcb-params-intro">
                <h3>🔧 PCB 板参数设置</h3>
                <p>请设置 PCB 板的规格参数</p>
              </div>

              <div className="pcb-params-grid">
                <div className="param-group">
                  <label>PCB 宽度 (mm)</label>
                  <input
                    type="number"
                    value={pcbParams.width}
                    onChange={(e) => setPcbParams({ ...pcbParams, width: parseFloat(e.target.value) || 100 })}
                    min={10}
                    max={500}
                  />
                </div>

                <div className="param-group">
                  <label>PCB 高度 (mm)</label>
                  <input
                    type="number"
                    value={pcbParams.height}
                    onChange={(e) => setPcbParams({ ...pcbParams, height: parseFloat(e.target.value) || 80 })}
                    min={10}
                    max={500}
                  />
                </div>

                <div className="param-group">
                  <label>板层数量</label>
                  <select
                    value={pcbParams.layers}
                    onChange={(e) => setPcbParams({ ...pcbParams, layers: parseInt(e.target.value) })}
                  >
                    <option value={1}>单面板 (1层)</option>
                    <option value={2}>双面板 (2层)</option>
                    <option value={4}>四层板 (4层)</option>
                    <option value={6}>六层板 (6层)</option>
                  </select>
                </div>

                <div className="param-group">
                  <label>板厚度 (mm)</label>
                  <select
                    value={pcbParams.thickness}
                    onChange={(e) => setPcbParams({ ...pcbParams, thickness: parseFloat(e.target.value) })}
                  >
                    <option value={0.8}>0.8mm (轻薄型)</option>
                    <option value={1.0}>1.0mm</option>
                    <option value={1.2}>1.2mm</option>
                    <option value={1.6}>1.6mm (标准)</option>
                    <option value={2.0}>2.0mm</option>
                  </select>
                </div>

                <div className="param-group">
                  <label>丝印层</label>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      id="silkscreen"
                      checked={pcbParams.silkscreen}
                      onChange={(e) => setPcbParams({ ...pcbParams, silkscreen: e.target.checked })}
                    />
                    <label htmlFor="silkscreen">包含丝印层 (元器件标识)</label>
                  </div>
                </div>

                <div className="param-group">
                  <label>阻焊颜色</label>
                  <select
                    value={pcbParams.soldermask}
                    onChange={(e) => setPcbParams({ ...pcbParams, soldermask: e.target.value })}
                  >
                    <option value="green">绿色 (标准)</option>
                    <option value="red">红色</option>
                    <option value="blue">蓝色</option>
                    <option value="yellow">黄色</option>
                    <option value="white">白色</option>
                    <option value="black">黑色</option>
                  </select>
                </div>
              </div>

              <div className="pcb-preview-size">
                <span className="size-label">PCB 尺寸预览:</span>
                <div
                  className="pcb-size-visual"
                  style={{
                    width: `${Math.min(pcbParams.width * 2, 200)}px`,
                    height: `${Math.min(pcbParams.height * 2, 160)}px`,
                    backgroundColor: pcbParams.soldermask,
                  }}
                >
                  <span>{pcbParams.width} x {pcbParams.height} mm</span>
                </div>
              </div>
            </div>
          )}

          {/* Step 5: PCB 预览 */}
          {step === 'pcb_preview' && pcbData && (
            <div className="step-pcb-preview">
              <div className="spec-section">
                <div className="preview-header">
                  <h3>🔲 PCB 预览</h3>
                  <div className="zoom-controls">
                    <button onClick={() => setPcbZoom(z => Math.max(0.2, z - 0.2))} title="缩小">➖</button>
                    <span>{Math.round(pcbZoom * 100)}%</span>
                    <button onClick={() => setPcbZoom(z => Math.min(5, z + 0.2))} title="放大">➕</button>
                    <button onClick={resetPcbView} title="重置">🔄</button>
                  </div>
                </div>
                <div className="pcb-stats">
                  <p>PCB 尺寸: {pcbData.width} x {pcbData.height} mm</p>
                  <p>板层: {pcbData.layers} 层</p>
                  <p>器件数量: {pcbData.components.length}</p>
                  <p>网络数量: {pcbData.nets.length}</p>
                </div>

                <div
                  className="pcb-canvas-wrapper"
                  onWheel={handlePcbWheel}
                  onMouseDown={handlePcbMouseDown}
                  onMouseMove={handlePcbMouseMove}
                  onMouseUp={handlePcbMouseUp}
                  onMouseLeave={handlePcbMouseUp}
                  style={{ cursor: isDraggingPcb ? 'grabbing' : 'grab' }}
                >
                  <svg
                    className="pcb-canvas"
                    viewBox={`${-pcbPan.x / pcbZoom} ${-pcbPan.y / pcbZoom} ${400 / pcbZoom} ${320 / pcbZoom}`}
                    preserveAspectRatio="xMidYMid meet"
                  >
                    <defs>
                      <pattern id="pcb-grid" width={20 * pcbZoom} height={20 * pcbZoom} patternUnits="userSpaceOnUse">
                        <path d={`M ${20 * pcbZoom} 0 L 0 0 0 ${20 * pcbZoom}`} fill="none" stroke="#1a3a5a" strokeWidth="0.5"/>
                      </pattern>
                    </defs>

                    {/* 网格背景 */}
                    <rect
                      x={-pcbPan.x / pcbZoom - 1000}
                      y={-pcbPan.y / pcbZoom - 1000}
                      width={2000 / pcbZoom}
                      height={2000 / pcbZoom}
                      fill="url(#pcb-grid)"
                    />

                    {/* PCB 边框 */}
                    <rect
                      x="10" y="10"
                      width={pcbData.width * 2}
                      height={pcbData.height * 2}
                      fill={pcbData.soldermask === 'green' ? '#1a5a1a' : pcbData.soldermask === 'blue' ? '#1a3a5a' : pcbData.soldermask === 'red' ? '#5a1a1a' : pcbData.soldermask === 'white' ? '#3a3a3a' : '#1a5a1a'}
                      stroke="#fff"
                      strokeWidth={2 / pcbZoom}
                    />

                    {/* 器件位置 */}
                    {pcbData.components.map((comp, idx) => {
                      const x = comp.position?.x || 50;
                      const y = comp.position?.y || 50;
                      const size = 40 / pcbZoom;
                      return (
                        <g key={comp.id || idx} transform={`translate(${x * 2 - size/2}, ${y * 2 - size/3})`}>
                          <rect
                            width={size}
                            height={size * 0.67}
                            rx={4 / pcbZoom}
                            fill="#444"
                            stroke="#888"
                            strokeWidth={2 / pcbZoom}
                          />
                          <text x={size/2} y={size/4} textAnchor="middle" fontSize={10 / pcbZoom} fill="#fff">
                            {comp.reference}
                          </text>
                        </g>
                      );
                    })}

                    {/* 走线 */}
                    {pcbData.traces && pcbData.traces.map((trace, idx) => (
                      <polyline
                        key={`trace-${idx}`}
                        points={trace.points.map(p => `${p.x * 2},${p.y * 2}`).join(' ')}
                        fill="none"
                        stroke="#ffa500"
                        strokeWidth={trace.width * 2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    ))}
                  </svg>
                </div>
              </div>
            </div>
          )}

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
                  <input
                    type="text"
                    value={projectSpec?.name}
                    onChange={(e) => setProjectSpec({ ...projectSpec!, name: e.target.value })}
                    className="project-name-input-confirm"
                  />
                </div>
                <div className="result-item">
                  <span className="label">项目 ID</span>
                  <span className="value code">{finalResult?.project?.id || 'N/A'}</span>
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
              <button
                className="submit-btn"
                onClick={handleSubmitAnswers}
                disabled={getAnsweredCount() < clarificationData.questions.filter(q => q.required).length}
              >
                生成方案
              </button>
            </>
          )}

          {step === 'schematic_preview' && (
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
              <button className="submit-btn" onClick={confirmSchematic}>
                确认原理图，下一步
              </button>
            </>
          )}

          {step === 'pcb_params' && (
            <>
              <button className="back-btn" onClick={handleBack}>
                返回原理图
              </button>
              <button className="submit-btn" onClick={handleSubmitPcbParams}>
                生成 PCB 方案
              </button>
            </>
          )}

          {step === 'pcb_preview' && (
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
              {/* 添加两个按钮文本以兼容测试 T36.1 */}
              <button className="confirm-btn large confirm-create-btn" onClick={handleFinalConfirm}>
                ✅ 确认创建
              </button>
              <button className="confirm-btn large" onClick={handleFinalConfirm} style={{display: 'none'}}>
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
