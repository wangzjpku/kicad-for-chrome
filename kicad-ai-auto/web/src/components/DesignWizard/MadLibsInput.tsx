/**
 * MadLibsInput.tsx - 结构化需求输入组件
 *
 * 类似 Flux.ai 的 Mad Libs 风格输入:
 * "Make me a [device] with [features] powered by [power] for [use case]"
 *
 * 支持字段:
 * - device: 设备类型 (温度传感器、LED控制器等)
 * - features: 功能特性 (WiFi、蓝牙、USB等)
 * - power: 电源 (USB-C、电池、AC-DC等)
 * - useCase: 使用场景 (消费电子、工业控制等)
 */

import React, { useState, useCallback } from 'react';
import { aiApi, AIAnalyzeResult } from '../../services/api';

interface FieldValue {
  value: string;
  options?: string[];
}

interface MadLibsInputProps {
  onSubmit: (requirements: string, parsedData: ParsedRequirements) => void;
  defaultExpanded?: boolean;
}

export interface ParsedRequirements {
  device: string;
  features: string[];
  power: string;
  useCase: string;
  additionalRequirements: string;
}

// 预定义选项
const DEVICE_OPTIONS = [
  '温度传感器',
  '湿度传感器',
  'LED控制器',
  '电机驱动器',
  '电源管理模块',
  '数据采集器',
  'IoT网关',
  'BLE蓝牙模块',
  'WiFi模块',
  'USB转串口',
];

const FEATURE_OPTIONS = [
  'WiFi',
  '蓝牙 BLE',
  'USB-C',
  'USB',
  'Ethernet',
  'RS485',
  'CAN总线',
  'I2C',
  'SPI',
  'UART',
  'ADC输入',
  'DAC输出',
  'PWM输出',
  'GPIO扩展',
  '显示接口',
  '存储扩展',
];

const POWER_OPTIONS = [
  'USB-C (5V)',
  'USB (5V)',
  '12V DC',
  '24V DC',
  '3.3V DC',
  '5V DC',
  'AC-DC 220V',
  '锂电池 3.7V',
  '锂电池 7.4V',
  '太阳能电池',
  'PoE',
];

const USE_CASE_OPTIONS = [
  '消费电子产品',
  '工业控制',
  '智能家居',
  '医疗设备',
  '汽车电子',
  '物联网设备',
  '教育实验',
  '原型开发',
  '智能农业',
  '环境监测',
];

const THEME = {
  bg: {
    primary: '#1e1e1e',
    secondary: '#2d2d2d',
    panel: '#383838',
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
  },
};

export const MadLibsInput: React.FC<MadLibsInputProps> = ({
  onSubmit,
  defaultExpanded = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [fields, setFields] = useState<Record<string, FieldValue>>({
    device: { value: '', options: DEVICE_OPTIONS },
    features: { value: '', options: FEATURE_OPTIONS },
    power: { value: '', options: POWER_OPTIONS },
    useCase: { value: '', options: USE_CASE_OPTIONS },
  });
  const [customText, setCustomText] = useState('');
  const [useCustomText, setUseCustomText] = useState(false);

  // 更新字段值
  const handleFieldChange = useCallback((field: string, value: string) => {
    setFields(prev => ({
      ...prev,
      [field]: { ...prev[field], value },
    }));
  }, []);

  // 切换选项
  const toggleFeature = useCallback((feature: string) => {
    setFields(prev => {
      const current = prev.features.value;
      const features = current ? current.split(',').map(f => f.trim()) : [];

      if (features.includes(feature)) {
        return {
          ...prev,
          features: { ...prev.features, value: features.filter(f => f !== feature).join(', ') },
        };
      } else {
        return {
          ...prev,
          features: { ...prev.features, value: [...features, feature].join(', ') },
        };
      }
    });
  }, []);

  // 生成自然语言描述
  const generateNaturalLanguage = useCallback(() => {
    const parts: string[] = [];

    if (fields.device.value) {
      parts.push(`设计一个${fields.device.value}`);
    }
    if (fields.features.value) {
      parts.push(`具有${fields.features.value}功能`);
    }
    if (fields.power.value) {
      parts.push(`电源为${fields.power.value}`);
    }
    if (fields.useCase.value) {
      parts.push(`用于${fields.useCase.value}`);
    }

    return parts.join('，') + '。';
  }, [fields]);

  // 处理提交
  const handleSubmit = async () => {
    const requirements = useCustomText ? customText : generateNaturalLanguage();

    // 解析数据
    const parsedData: ParsedRequirements = {
      device: fields.device.value,
      features: fields.features.value ? fields.features.value.split(',').map(f => f.trim()) : [],
      power: fields.power.value,
      useCase: fields.useCase.value,
      additionalRequirements: '',
    };

    // 调用AI分析
    setIsAnalyzing(true);
    try {
      const response = await aiApi.analyzeRequirements(requirements);
      if (response.success && response.data) {
        onSubmit(requirements, parsedData);
      }
    } catch (error) {
      console.error('AI analysis failed:', error);
      // 即使AI分析失败，也继续提交
      onSubmit(requirements, parsedData);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 检查是否可以提交
  const canSubmit = useCustomText
    ? customText.trim().length > 0
    : fields.device.value || fields.features.value;

  if (!isExpanded) {
    return (
      <div
        onClick={() => setIsExpanded(true)}
        style={{
          position: 'fixed',
          top: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          backgroundColor: THEME.bg.secondary,
          border: `1px solid ${THEME.border.default}`,
          borderRadius: 12,
          padding: '12px 24px',
          cursor: 'pointer',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        }}
      >
        <span style={{ color: THEME.text.secondary, fontSize: 14 }}>
          ⚡ 快速创建设计
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        width: 600,
        maxWidth: '90vw',
        backgroundColor: THEME.bg.secondary,
        border: `1px solid ${THEME.border.default}`,
        borderRadius: 12,
        boxShadow: '0 4px 30px rgba(0,0,0,0.4)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          backgroundColor: THEME.bg.panel,
          padding: '12px 16px',
          borderBottom: `1px solid ${THEME.border.default}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ color: THEME.text.primary, fontSize: 14, fontWeight: 600 }}>
            描述您的电路设计
          </div>
          <div style={{ color: THEME.text.muted, fontSize: 11, marginTop: 2 }}>
            填写下方字段或使用自定义描述
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(false)}
          style={{
            background: 'none',
            border: 'none',
            color: THEME.text.muted,
            cursor: 'pointer',
            fontSize: 18,
            padding: 4,
          }}
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: 16 }}>
        {/* 模式切换 */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button
            onClick={() => setUseCustomText(false)}
            style={{
              flex: 1,
              padding: '8px 12px',
              backgroundColor: !useCustomText ? THEME.accent.primary : 'transparent',
              border: `1px solid ${useCustomText ? THEME.border.default : THEME.accent.primary}`,
              borderRadius: 6,
              color: !useCustomText ? '#fff' : THEME.text.secondary,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            引导输入
          </button>
          <button
            onClick={() => setUseCustomText(true)}
            style={{
              flex: 1,
              padding: '8px 12px',
              backgroundColor: useCustomText ? THEME.accent.primary : 'transparent',
              border: `1px solid ${useCustomText ? THEME.accent.primary : THEME.border.default}`,
              borderRadius: 6,
              color: useCustomText ? '#fff' : THEME.text.secondary,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            自定义描述
          </button>
        </div>

        {useCustomText ? (
          /* 自定义文本输入 */
          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="例如：设计一个具有WiFi和蓝牙功能的温度传感器，电源为USB-C，用于智能家居场景"
            style={{
              width: '100%',
              minHeight: 100,
              padding: 12,
              backgroundColor: THEME.bg.primary,
              border: `1px solid ${THEME.border.default}`,
              borderRadius: 8,
              color: THEME.text.primary,
              fontSize: 13,
              fontFamily: 'inherit',
              resize: 'vertical',
              boxSizing: 'border-box',
            }}
          />
        ) : (
          /* Mad Libs 字段输入 */
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Device */}
            <div>
              <label style={{ color: THEME.text.secondary, fontSize: 11, marginBottom: 4, display: 'block' }}>
                设备类型
              </label>
              <select
                value={fields.device.value}
                onChange={(e) => handleFieldChange('device', e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: THEME.bg.primary,
                  border: `1px solid ${THEME.border.default}`,
                  borderRadius: 6,
                  color: THEME.text.primary,
                  fontSize: 13,
                }}
              >
                <option value="">选择设备类型...</option>
                {DEVICE_OPTIONS.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>

            {/* Features */}
            <div>
              <label style={{ color: THEME.text.secondary, fontSize: 11, marginBottom: 4, display: 'block' }}>
                功能特性 (可多选)
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {FEATURE_OPTIONS.map(feature => {
                  const isSelected = fields.features.value.includes(feature);
                  return (
                    <button
                      key={feature}
                      onClick={() => toggleFeature(feature)}
                      style={{
                        padding: '6px 10px',
                        backgroundColor: isSelected ? THEME.accent.primary : 'transparent',
                        border: `1px solid ${isSelected ? THEME.accent.primary : THEME.border.default}`,
                        borderRadius: 16,
                        color: isSelected ? '#fff' : THEME.text.secondary,
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      {feature}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Power */}
            <div>
              <label style={{ color: THEME.text.secondary, fontSize: 11, marginBottom: 4, display: 'block' }}>
                电源
              </label>
              <select
                value={fields.power.value}
                onChange={(e) => handleFieldChange('power', e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: THEME.bg.primary,
                  border: `1px solid ${THEME.border.default}`,
                  borderRadius: 6,
                  color: THEME.text.primary,
                  fontSize: 13,
                }}
              >
                <option value="">选择电源类型...</option>
                {POWER_OPTIONS.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>

            {/* Use Case */}
            <div>
              <label style={{ color: THEME.text.secondary, fontSize: 11, marginBottom: 4, display: 'block' }}>
                使用场景
              </label>
              <select
                value={fields.useCase.value}
                onChange={(e) => handleFieldChange('useCase', e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: THEME.bg.primary,
                  border: `1px solid ${THEME.border.default}`,
                  borderRadius: 6,
                  color: THEME.text.primary,
                  fontSize: 13,
                }}
              >
                <option value="">选择使用场景...</option>
                {USE_CASE_OPTIONS.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>

            {/* Preview */}
            <div
              style={{
                marginTop: 8,
                padding: 12,
                backgroundColor: THEME.bg.primary,
                borderRadius: 8,
                borderLeft: `3px solid ${THEME.accent.primary}`,
              }}
            >
              <div style={{ color: THEME.text.muted, fontSize: 10, marginBottom: 4 }}>
                预览
              </div>
              <div style={{ color: THEME.text.primary, fontSize: 13, lineHeight: 1.5 }}>
                {generateNaturalLanguage() || '请填写上方字段...'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: `1px solid ${THEME.border.default}`,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 8,
        }}
      >
        <button
          onClick={() => setIsExpanded(false)}
          style={{
            padding: '8px 16px',
            backgroundColor: 'transparent',
            border: `1px solid ${THEME.border.default}`,
            borderRadius: 6,
            color: THEME.text.secondary,
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          取消
        </button>
        <button
          onClick={handleSubmit}
          disabled={!canSubmit || isAnalyzing}
          style={{
            padding: '8px 20px',
            backgroundColor: canSubmit && !isAnalyzing ? THEME.accent.primary : THEME.text.muted,
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            fontSize: 12,
            fontWeight: 500,
            cursor: canSubmit && !isAnalyzing ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {isAnalyzing ? (
            <>
              <span style={{ animation: 'spin 1s linear infinite' }}>⟳</span>
              分析中...
            </>
          ) : (
            <>开始设计 →</>
          )}
        </button>
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

export default MadLibsInput;
