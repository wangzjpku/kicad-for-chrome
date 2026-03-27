/**
 * Layer Calculator Service (Frontend TypeScript Version)
 *
 * 对应后端 agent/services/layer_calculator.py
 * 用于前端估算PCB层数需求
 */

export interface LayerRecommendation {
  layer_count: number;
  primary_reason: string;
  reasons: string[];
  confidence: number;
  alternatives: Record<number, string>;
  warnings: string[];
  analysis?: CircuitAnalysis;
}

export interface CircuitAnalysis {
  circuit_type: string;
  complexity: string;
  high_speed_signal_ghz: number;
  high_speed_io_count: number;
  differential_pair_count: number;
  power_rails_count: number;
  max_current_ma: number;
  is_power_critical: boolean;
  component_count: number;
  estimated_pins: number;
  has_rf: boolean;
  has_impedance_control: boolean;
  has_analog_mixed: boolean;
  is_high_density: boolean;
}

interface CircuitData {
  components?: string[];
  requirements?: string;
  nets?: Array<{ name: string; type?: string }>;
  high_speed_signals?: Array<{ frequency_ghz?: number }>;
  power_rails?: Array<{ current_ma?: number }>;
}

/**
 * 分析电路数据并返回层数推荐
 */
export function calculateLayerRecommendation(circuitData: CircuitData): LayerRecommendation {
  // 解析需求文本中的关键词
  const requirements = (circuitData.requirements || '').toLowerCase();

  // 初始化分析结果
  const analysis: CircuitAnalysis = {
    circuit_type: 'digital',
    complexity: 'standard',
    high_speed_signal_ghz: 0,
    high_speed_io_count: 0,
    differential_pair_count: 0,
    power_rails_count: circuitData.power_rails?.length || 0,
    max_current_ma: Math.max(...(circuitData.power_rails?.map(r => r.current_ma || 0) || [0])),
    is_power_critical: false,
    component_count: circuitData.components?.length || 0,
    estimated_pins: (circuitData.components?.length || 0) * 4,
    has_rf: /rf|wi-fi|wifi|bluetooth|radio/.test(requirements),
    has_impedance_control: /impedance|differential/.test(requirements),
    has_analog_mixed: /adc|dac|audio|analog|sensor/.test(requirements),
    is_high_density: (circuitData.components?.length || 0) > 50,
  };

  // 检测高速信号
  const highSpeedSignals = circuitData.high_speed_signals || [];
  if (highSpeedSignals.length > 0) {
    analysis.high_speed_signal_ghz = Math.max(...highSpeedSignals.map(s => s.frequency_ghz || 0));
    analysis.high_speed_io_count = highSpeedSignals.length;
  }

  // 检测 USB/Ethernet 等高速接口
  if (/usb|ethernet|pcie|ddr|hdmi/.test(requirements)) {
    analysis.high_speed_io_count = Math.max(analysis.high_speed_io_count, 8);
  }

  // 检测差分对
  const nets = circuitData.nets || [];
  let diffPairCount = 0;
  for (const net of nets) {
    const netName = (net.name || '').toLowerCase();
    const netType = (net.type || '').toLowerCase();
    if (netType === 'differential' || netName.includes('diff') || netName.includes('pair')) {
      diffPairCount++;
    }
    // 检测 _P/_N 后缀模式
    if (/_p[_\-]|_n[_\-]/.test(netName)) {
      diffPairCount++;
    }
  }
  analysis.differential_pair_count = Math.floor(diffPairCount / 2);

  // 检测电源关键电路
  if (/motor|driver|mosfet|power/.test(requirements)) {
    analysis.is_power_critical = true;
    analysis.circuit_type = 'power';
  }

  // 计算层数
  let baseLayers = 2;
  const reasons: string[] = [];
  const warnings: string[] = [];
  let confidence = 0.9;

  // 极高频/差分对 → 6层
  if (analysis.high_speed_signal_ghz >= 5) {
    reasons.push(`超高频信号 (${analysis.high_speed_signal_ghz.toFixed(1)} GHz >= 5 GHz)`);
    baseLayers = Math.max(baseLayers, 6);
    confidence = 0.95;
  }

  if (analysis.differential_pair_count >= 4) {
    reasons.push(`差分对数量 (${analysis.differential_pair_count} 对 >= 4 对)`);
    baseLayers = Math.max(baseLayers, 6);
    confidence = 0.95;
  }

  // 高速/多IO → 4层
  if (analysis.high_speed_signal_ghz > 1) {
    reasons.push(`高频信号 (${analysis.high_speed_signal_ghz.toFixed(1)} GHz > 1 GHz)`);
    baseLayers = Math.max(baseLayers, 4);
    confidence = 0.9;
  }

  if (analysis.high_speed_io_count > 20) {
    reasons.push(`高速 IO 数量 (${analysis.high_speed_io_count} > 20)`);
    baseLayers = Math.max(baseLayers, 4);
    confidence = 0.9;
  } else if (analysis.high_speed_io_count >= 8) {
    reasons.push('高速接口 (USB/Ethernet 等)');
    baseLayers = Math.max(baseLayers, 4);
    confidence = 0.85;
  }

  if (analysis.has_impedance_control) {
    reasons.push('需要阻抗控制');
    baseLayers = Math.max(baseLayers, 4);
    confidence = 0.85;
  }

  // 电源完整性 → 4层
  if (analysis.power_rails_count > 3) {
    reasons.push(`多电源设计 (${analysis.power_rails_count} 路电源)`);
    baseLayers = Math.max(baseLayers, 4);
    confidence = 0.9;
  }

  if (analysis.max_current_ma > 10000) {
    reasons.push(`高电流设计 (${(analysis.max_current_ma / 1000).toFixed(0)}A > 10A)`);
    baseLayers = Math.max(baseLayers, 4);
    confidence = 0.9;
    warnings.push('高电流电路建议使用电源平面和更宽的走线');
  }

  // 简单电路 → 1层 (仅当没有高速信号、多电源或高电流需求时)
  if (analysis.component_count <= 5 &&
      analysis.high_speed_io_count < 8 &&
      analysis.high_speed_signal_ghz === 0 &&
      analysis.power_rails_count <= 1 &&
      analysis.max_current_ma <= 1000) {
    baseLayers = Math.min(baseLayers, 1);
    reasons.push('简单电路，可使用单面板降低成本');
  }

  // RF电路
  if (analysis.has_rf) {
    reasons.push('RF 电路需要专门的布局考虑');
    baseLayers = Math.max(baseLayers, 4);
    warnings.push('RF 电路建议使用专门的RF板材');
  }

  // 模拟混合信号
  if (analysis.has_analog_mixed) {
    reasons.push('模拟混合信号电路');
    baseLayers = Math.max(baseLayers, 4);
    warnings.push('建议使用独立的模拟和数字地平面');
  }

  // 替代方案
  const alternatives: Record<number, string> = {};
  if (baseLayers > 2) {
    alternatives[2] = '降低性能要求，减少高速IO，使用低速协议';
  }
  if (baseLayers > 4) {
    alternatives[4] = '降低信号频率要求，使用并行总线替代高速串行';
  }

  // 高密度警告
  if (analysis.is_high_density && baseLayers < 4) {
    warnings.push('高密度设计建议使用4层或更多层以提高布线灵活性');
  }

  if (analysis.is_power_critical && baseLayers < 4) {
    warnings.push('电源关键电路建议使用4层以获得更好的电源完整性');
  }

  // 确定复杂度
  if (analysis.high_speed_signal_ghz >= 5 || analysis.differential_pair_count >= 4) {
    analysis.complexity = 'advanced';
  } else if (analysis.high_speed_signal_ghz > 1 || analysis.high_speed_io_count > 20 || analysis.has_impedance_control) {
    analysis.complexity = 'high_speed';
  } else if (analysis.power_rails_count > 3 || analysis.max_current_ma > 10000) {
    analysis.complexity = 'complex';
  } else if (analysis.component_count > 10) {
    analysis.complexity = 'standard';
  } else {
    analysis.complexity = 'simple';
  }

  return {
    layer_count: baseLayers,
    primary_reason: reasons[0] || '标准双层板设计',
    reasons,
    confidence,
    alternatives,
    warnings,
    analysis,
  };
}
