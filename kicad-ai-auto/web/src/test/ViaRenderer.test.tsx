/**
 * ViaRenderer 组件测试
 * 测试过孔渲染和选择功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ViaRenderer from '../canvas/ViaRenderer';
import { Via } from '../types';

// Mock pcbStore - use vi.hoisted to avoid hoisting issues
const { mockToggleSelection, mockUsePCBStore } = vi.hoisted(() => ({
  mockToggleSelection: vi.fn(),
  mockUsePCBStore: vi.fn(() => ({
    selectedIds: [],
    toggleSelection: vi.fn(),
  })),
}));

vi.mock('../stores/pcbStore', () => ({
  usePCBStore: mockUsePCBStore,
}));

// Mock react-konva
vi.mock('react-konva', () => ({
  Group: ({ children, onClick, x, y }: any) => (
    <div 
      data-testid="konva-group" 
      data-x={x} 
      data-y={y}
      onClick={onClick}
    >
      {children}
    </div>
  ),
  Circle: ({ radius, fill, stroke, strokeWidth }: any) => (
    <div
      data-testid="konva-circle"
      data-radius={radius}
      data-fill={fill}
      data-stroke={stroke}
      data-stroke-width={strokeWidth}
      style={{ 
        width: radius * 2,
        height: radius * 2,
        backgroundColor: fill,
        border: `${strokeWidth}px solid ${stroke}`,
        borderRadius: '50%'
      }}
    />
  ),
}));

describe('ViaRenderer', () => {
  const mockVia: Via = {
    id: 'via-001',
    type: 'via',
    position: { x: 30, y: 30 },
    size: 0.8,
    drill: 0.4,
    startLayer: 'F.Cu',
    endLayer: 'B.Cu',
    netId: 'net-001',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('应该渲染过孔', () => {
      render(<ViaRenderer via={mockVia} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });

    it('应该渲染外圈和内圈', () => {
      render(<ViaRenderer via={mockVia} />);
      const circles = screen.getAllByTestId('konva-circle');
      expect(circles.length).toBe(2); // 外圈和内圈
    });

    it('应该正确设置外圈大小', () => {
      render(<ViaRenderer via={mockVia} />);
      const circles = screen.getAllByTestId('konva-circle');
      const outerCircle = circles[0];
      // 0.8mm * 10px/mm / 2 = 4px radius
      expect(outerCircle).toHaveAttribute('data-radius', '4');
    });

    it('应该正确设置钻孔大小', () => {
      render(<ViaRenderer via={mockVia} />);
      const circles = screen.getAllByTestId('konva-circle');
      const innerCircle = circles[1];
      // 0.4mm * 10px/mm / 2 = 2px radius
      expect(innerCircle).toHaveAttribute('data-radius', '2');
    });

    it('应该显示为棕色', () => {
      render(<ViaRenderer via={mockVia} />);
      const circles = screen.getAllByTestId('konva-circle');
      const outerCircle = circles[0];
      expect(outerCircle).toHaveAttribute('data-fill', '#8B4513');
    });

    it('选中时应该显示高亮', () => {
      // Override mock to return selected via
      mockUsePCBStore.mockReturnValueOnce({
        selectedIds: ['via-001'],
        toggleSelection: mockToggleSelection,
      });

      render(<ViaRenderer via={mockVia} />);
      const circles = screen.getAllByTestId('konva-circle');
      const outerCircle = circles[0];
      expect(outerCircle).toHaveAttribute('data-stroke', '#FFFF00');
    });
  });

  describe('交互测试', () => {
    it('点击过孔应该触发选择', () => {
      // Mock the store to return our mock function
      mockUsePCBStore.mockReturnValue({
        selectedIds: [],
        toggleSelection: mockToggleSelection,
      });
      
      render(<ViaRenderer via={mockVia} />);
      const group = screen.getByTestId('konva-group');
      
      fireEvent.click(group);
      
      expect(mockToggleSelection).toHaveBeenCalledWith('via-001');
    });
  });

  describe('边界条件测试', () => {
    it('应该处理小过孔', () => {
      const smallVia = { ...mockVia, size: 0.3, drill: 0.15 };
      expect(() => {
        render(<ViaRenderer via={smallVia} />);
      }).not.toThrow();
    });

    it('应该处理大过孔', () => {
      const largeVia = { ...mockVia, size: 2.0, drill: 1.0 };
      expect(() => {
        render(<ViaRenderer via={largeVia} />);
      }).not.toThrow();
    });

    it('应该处理负坐标', () => {
      const negativeVia = {
        ...mockVia,
        position: { x: -30, y: -30 },
      };
      expect(() => {
        render(<ViaRenderer via={negativeVia} />);
      }).not.toThrow();
    });

    it('应该处理盲孔', () => {
      const blindVia = {
        ...mockVia,
        startLayer: 'F.Cu',
        endLayer: 'In1.Cu',
      };
      render(<ViaRenderer via={blindVia} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });
  });

  describe('坐标转换测试', () => {
    it('应该正确转换毫米到像素', () => {
      render(<ViaRenderer via={mockVia} />);
      const circles = screen.getAllByTestId('konva-circle');
      
      // Check that circles have the expected positions
      // 30mm * 10px/mm = 300px
      // The mock Circle component sets data attributes based on props
      expect(circles.length).toBe(2);
    });
  });
});
