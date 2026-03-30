/**
 * PCB Design API Service
 *
 * Phase 3-4: DRC检查和层叠配置API
 */

import axios from 'axios';

const API_BASE = '/api';

// Types
export interface DRCViolation {
  rule_name: string;
  rule_type: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  net1?: string;
  net2?: string;
  component?: string;
  x?: number;
  y?: number;
  expected?: number;
  actual?: number;
  layer?: string;
}

export interface DRCResult {
  passed: boolean;
  error_count: number;
  warning_count: number;
  info_count: number;
  violations: DRCViolation[];
  statistics: Record<string, unknown>;
  duration_ms: number;
}

export interface LayerStackupTemplate {
  id: string;
  name: string;
  layer_count: number;
  total_thickness: number;
  layers: {
    name: string;
    type: 'signal' | 'plane' | 'mixed';
    plane_type?: 'GND' | 'PWR';
    thickness: number;
  }[];
  best_for: string[];
}

export interface ImpedanceCalculation {
  impedance: number;
  trace_width: number;
  dielectric_thickness: number;
  dk: number;
  propagation_delay: number;
  coupling: string;
  diff_spacing?: number;
}

/**
 * DRC API
 */
export const DRCApi = {
  /**
   * 运行高级DRC检查
   */
  async runAdvancedCheck(
    projectId: string,
    pcbData: Record<string, unknown>,
    manufacturer: string = 'jlcpcb',
    level: string = 'standard'
  ): Promise<DRCResult> {
    const response = await axios.post(`${API_BASE}/drc/advanced-check`, {
      project_id: projectId,
      pcb_data: pcbData,
      manufacturer,
      level,
    });
    return response.data;
  },

  /**
   * 获取制造商能力参数
   */
  async getManufacturerCapabilities(
    manufacturer: string,
    level: string = 'standard'
  ): Promise<{
    manufacturer: string;
    level: string;
    capabilities: Record<string, number>;
    net_classes: Record<string, {
      track_width: number;
      clearance: number;
      via_diameter: number;
      via_drill: number;
    }>;
    rules_summary: Record<string, unknown>;
  }> {
    const response = await axios.get(
      `${API_BASE}/drc/capabilities/${manufacturer}?level=${level}`
    );
    return response.data;
  },

  /**
   * 获取详细规则列表
   */
  async getDetailedRules(
    ruleType?: string,
    severity?: string
  ): Promise<{
    rules: {
      name: string;
      type: string;
      value: number;
      tolerance: number;
      severity: string;
      description: string;
      category: string;
    }[];
    count: number;
    by_type: Record<string, number>;
  }> {
    const params = new URLSearchParams();
    if (ruleType) params.append('rule_type', ruleType);
    if (severity) params.append('severity', severity);

    const response = await axios.get(
      `${API_BASE}/drc/rules-detailed?${params.toString()}`
    );
    return response.data;
  },

  /**
   * 检查间距
   */
  async checkClearance(
    net1: string,
    net2: string,
    distance: number,
    minClearance: number = 0.2
  ): Promise<{
    passed: boolean;
    net1: string;
    net2: string;
    distance: number;
    min_clearance: number;
    violation: boolean;
    message: string;
  }> {
    const response = await axios.get(
      `${API_BASE}/drc/check-clearance?net1=${net1}&net2=${net2}&distance=${distance}&min_clearance=${minClearance}`
    );
    return response.data;
  },
};

/**
 * Layer Stackup API
 */
export const LayerStackupApi = {
  /**
   * 获取层叠模板列表
   */
  async getTemplates(): Promise<LayerStackupTemplate[]> {
    // 目前使用前端硬编码，后续可以从后端获取
    return [
      {
        id: '2layer',
        name: '2层板',
        layer_count: 2,
        total_thickness: 1.6,
        layers: [
          { name: 'F.Cu', type: 'signal', thickness: 0.035 },
          { name: 'B.Cu', type: 'signal', thickness: 0.035 },
        ],
        best_for: ['简单电路', '低成本设计', '原型验证'],
      },
      {
        id: '4layer_standard',
        name: '4层板标准',
        layer_count: 4,
        total_thickness: 1.6,
        layers: [
          { name: 'F.Cu', type: 'signal', thickness: 0.035 },
          { name: 'GND', type: 'plane', plane_type: 'GND', thickness: 0.035 },
          { name: 'PWR', type: 'plane', plane_type: 'PWR', thickness: 0.035 },
          { name: 'B.Cu', type: 'signal', thickness: 0.035 },
        ],
        best_for: ['高速信号', '电源完整性', 'EMI控制'],
      },
      {
        id: '4layer_thin',
        name: '4层板薄型',
        layer_count: 4,
        total_thickness: 1.0,
        layers: [
          { name: 'F.Cu', type: 'signal', thickness: 0.035 },
          { name: 'GND', type: 'plane', plane_type: 'GND', thickness: 0.035 },
          { name: 'PWR', type: 'plane', plane_type: 'PWR', thickness: 0.035 },
          { name: 'B.Cu', type: 'signal', thickness: 0.035 },
        ],
        best_for: ['空间受限', '移动设备', '可穿戴设备'],
      },
      {
        id: '6layer_standard',
        name: '6层板标准',
        layer_count: 6,
        total_thickness: 1.6,
        layers: [
          { name: 'F.Cu', type: 'signal', thickness: 0.035 },
          { name: 'GND1', type: 'plane', plane_type: 'GND', thickness: 0.035 },
          { name: 'In1.Cu', type: 'signal', thickness: 0.035 },
          { name: 'In2.Cu', type: 'signal', thickness: 0.035 },
          { name: 'PWR', type: 'plane', plane_type: 'PWR', thickness: 0.035 },
          { name: 'B.Cu', type: 'signal', thickness: 0.035 },
        ],
        best_for: ['复杂电路', '多电源域', '高速总线'],
      },
      {
        id: '6layer_optimized',
        name: '6层板优化',
        layer_count: 6,
        total_thickness: 1.6,
        layers: [
          { name: 'F.Cu', type: 'signal', thickness: 0.035 },
          { name: 'In1.Cu', type: 'signal', thickness: 0.035 },
          { name: 'GND', type: 'plane', plane_type: 'GND', thickness: 0.035 },
          { name: 'PWR', type: 'plane', plane_type: 'PWR', thickness: 0.035 },
          { name: 'In2.Cu', type: 'signal', thickness: 0.035 },
          { name: 'B.Cu', type: 'signal', thickness: 0.035 },
        ],
        best_for: ['高频设计', '差分信号', '阻抗控制'],
      },
    ];
  },

  /**
   * 计算阻抗
   * 目前在前端计算，后续可以调用后端API
   */
  calculateImpedance(
    traceWidth: number,
    dielectricThickness: number,
    dk: number,
    copperThickness: number,
    coupling: 'single' | 'diff',
    diffSpacing?: number
  ): ImpedanceCalculation {
    // Microstrip formula
    const zSingle = 87 / Math.sqrt(dk + 1.41) *
      Math.log(5.98 * dielectricThickness / (0.8 * traceWidth + copperThickness));

    let impedance = zSingle;
    if (coupling === 'diff' && diffSpacing) {
      impedance = 2 * zSingle * (1 - 0.48 * Math.exp(-0.96 * diffSpacing / dielectricThickness));
    }

    const delay = 3.34 * Math.sqrt(dk);

    return {
      impedance: Math.round(impedance * 10) / 10,
      trace_width: traceWidth,
      dielectric_thickness: dielectricThickness,
      dk,
      propagation_delay: Math.round(delay * 10) / 10,
      coupling,
      diff_spacing: coupling === 'diff' ? diffSpacing : undefined,
    };
  },

  /**
   * 反推线宽
   */
  reverseCalculateWidth(
    targetImpedance: number,
    dielectricThickness: number,
    dk: number,
    copperThickness: number,
    coupling: 'single' | 'diff',
    diffSpacing?: number
  ): number {
    let low = 0.05;
    let high = 5.0;
    let bestWidth = 0.25;

    for (let i = 0; i < 20; i++) {
      const mid = (low + high) / 2;
      const result = this.calculateImpedance(
        mid, dielectricThickness, dk, copperThickness, coupling, diffSpacing
      );

      if (Math.abs(result.impedance - targetImpedance) < 0.5) {
        bestWidth = mid;
        break;
      }

      if (result.impedance > targetImpedance) {
        low = mid;
      } else {
        high = mid;
      }
      bestWidth = mid;
    }

    return Math.round(bestWidth * 1000) / 1000;
  },
};

export default {
  DRC: DRCApi,
  LayerStackup: LayerStackupApi,
};