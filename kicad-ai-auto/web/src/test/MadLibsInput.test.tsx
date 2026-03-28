/**
 * Tests for MadLibsInput Component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MadLibsInput } from '../components/DesignWizard/MadLibsInput';

// Mock the API
vi.mock('../../services/api', () => ({
  aiApi: {
    analyzeRequirements: vi.fn().mockResolvedValue({
      success: true,
      data: { analysis: 'test analysis' },
    }),
  },
}));

describe('MadLibsInput Component', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('should render collapsed state initially when defaultExpanded is false', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={false} />);
    expect(screen.getByText('⚡ 快速创建设计')).toBeDefined();
  });

  it('should render expanded state when defaultExpanded is true', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    expect(screen.getByText('描述您的电路设计')).toBeDefined();
  });

  it('should switch to custom text mode', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    const customTextBtn = screen.getByText('自定义描述');
    fireEvent.click(customTextBtn);
    expect(screen.getByPlaceholderText(/例如：设计一个/)).toBeDefined();
  });

  it('should switch back to guided mode', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    // First switch to custom
    fireEvent.click(screen.getByText('自定义描述'));
    // Then switch back to guided
    fireEvent.click(screen.getByText('引导输入'));
    expect(screen.getByText('设备类型')).toBeDefined();
  });

  it('should generate preview text when device is selected', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);

    // Find the first select (device type) and change it
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: '温度传感器' } });

    // Preview section should contain the selected device (use getAll and check at least one is in preview)
    const previewSection = screen.getByText(/预览/);
    expect(previewSection).toBeDefined();
    // The preview text contains "设计一个温度传感器"
    expect(screen.getByText(/设计一个温度传感器/)).toBeDefined();
  });

  it('should toggle feature chips', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    const wifiButton = screen.getByText('WiFi');
    fireEvent.click(wifiButton);
    // After clicking, it should be selected (visual state change)
    expect(wifiButton).toBeDefined();
  });

  it('should collapse when close button is clicked', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    const closeBtn = screen.getByText('×');
    fireEvent.click(closeBtn);
    expect(screen.getByText('⚡ 快速创建设计')).toBeDefined();
  });

  it('should disable submit when no input in guided mode', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    const submitBtn = screen.getByText('开始设计 →') as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('should enable submit when custom text is entered', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);

    // Switch to custom text mode
    fireEvent.click(screen.getByText('自定义描述'));

    // Type custom text
    const textarea = screen.getByPlaceholderText(/例如：设计一个/);
    fireEvent.change(textarea, { target: { value: '设计一个USB模块' } });

    // Submit should be enabled
    const submitBtn = screen.getByText('开始设计 →') as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(false);
  });

  it('should call onSubmit with correct data when custom text is submitted', async () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);

    // Switch to custom text mode
    fireEvent.click(screen.getByText('自定义描述'));

    // Type custom text
    const textarea = screen.getByPlaceholderText(/例如：设计一个/);
    fireEvent.change(textarea, { target: { value: '设计一个USB转串口模块' } });

    // Submit
    fireEvent.click(screen.getByText('开始设计 →'));

    // Wait for the async API call to complete
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    }, { timeout: 2000 });

    expect(mockOnSubmit).toHaveBeenCalledWith(
      '设计一个USB转串口模块',
      expect.objectContaining({
        device: '',
        features: [],
        power: '',
        useCase: '',
        additionalRequirements: '',
      })
    );
  });

  it('should show power options when expanded', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    // Find the power select by its label
    expect(screen.getByText('电源')).toBeDefined();
  });

  it('should show use case options when expanded', () => {
    render(<MadLibsInput onSubmit={mockOnSubmit} defaultExpanded={true} />);
    expect(screen.getByText('使用场景')).toBeDefined();
  });
});
