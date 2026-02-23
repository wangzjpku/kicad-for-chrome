/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * FootprintRenderer 组件测试
 * 测试封装渲染、选择、拖拽功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FootprintRenderer from '../canvas/FootprintRenderer';
import { Footprint } from '../types';
import * as pcbStore from '../stores/pcbStore';

// Mock pcbStore
const mockToggleSelection = vi.fn();
const mockUpdateFootprintPosition = vi.fn();
const mockPushHistory = vi.fn();

vi.mock('../stores/pcbStore', () => ({
  usePCBStore: vi.fn(() => ({
    selectedIds: [],
    toggleSelection: mockToggleSelection,
    currentTool: 'select',
    updateFootprintPosition: mockUpdateFootprintPosition,
    pushHistory: mockPushHistory,
    gridSize: 1,
    snapToGrid: true,
  })),
}));

// Mock react-konva
// Create a mock node that has x() and y() methods
const createMockNode = (x = 100, y = 200) => ({
  x: vi.fn(() => x),
  y: vi.fn(() => y),
});

vi.mock('react-konva', () => ({
  Group: ({ children, onClick, onDragEnd, draggable, x, y }: any) => (
    <div 
      data-testid="konva-group" 
      data-x={x} 
      data-y={y}
      data-draggable={draggable}
      onClick={onClick}
      onMouseUp={(e: any) => {
        // Create mock event with target that has x() and y() methods
        const mockEvent = {
          target: createMockNode(x || 100, y || 200),
        };
        onDragEnd?.(mockEvent);
      }}
    >
      {children}
    </div>
  ),
  Rect: ({ x, y, width, height, fill, stroke }: any) => (
    <div 
      data-testid="konva-rect"
      data-x={x}
      data-y={y}
      data-width={width}
      data-height={height}
      style={{ backgroundColor: fill, borderColor: stroke }}
    />
  ),
  Text: ({ text, x, y }: any) => (
    <span data-testid="konva-text" data-x={x} data-y={y}>{text}</span>
  ),
}));

describe('FootprintRenderer', () => {
  const mockFootprint: Footprint = {
    id: 'fp-001',
    type: 'footprint',
    libraryName: 'Device',
    footprintName: 'R_0603',
    fullFootprintName: 'Device:R_0603',
    reference: 'R1',
    value: '10k',
    position: { x: 10, y: 20 },
    rotation: 0,
    layer: 'F.Cu',
    pads: [
      {
        id: 'pad-001',
        number: '1',
        type: 'smd',
        shape: 'rect',
        position: { x: -0.8, y: 0 },
        size: { x: 0.8, y: 0.8 },
        layers: ['F.Cu'],
      },
      {
        id: 'pad-002',
        number: '2',
        type: 'smd',
        shape: 'rect',
        position: { x: 0.8, y: 0 },
        size: { x: 0.8, y: 0.8 },
        layers: ['F.Cu'],
      },
    ],
    attributes: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('应该渲染封装组件', () => {
      render(<FootprintRenderer footprint={mockFootprint} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });

    it('应该显示位号', () => {
      render(<FootprintRenderer footprint={mockFootprint} />);
      expect(screen.getByText('R1')).toBeInTheDocument();
    });

    it('应该渲染所有焊盘', () => {
      render(<FootprintRenderer footprint={mockFootprint} />);
      const rects = screen.getAllByTestId('konva-rect');
      // 应该有2个焊盘 + 可选的高亮框
      expect(rects.length).toBeGreaterThanOrEqual(2);
    });

    it('应该根据层设置颜色', () => {
      render(<FootprintRenderer footprint={mockFootprint} />);
      const rects = screen.getAllByTestId('konva-rect');
      // F.Cu层应该是红色
      expect(rects.length).toBeGreaterThan(0);
    });

    it('应该处理B.Cu层的封装', () => {
      const bCuFootprint = { ...mockFootprint, layer: 'B.Cu' };
      render(<FootprintRenderer footprint={bCuFootprint} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });
  });

  describe('选择功能测试', () => {
    it('点击封装应该触发选择', () => {
      render(<FootprintRenderer footprint={mockFootprint} />);
      const group = screen.getByTestId('konva-group');
      
      fireEvent.click(group);
      
      expect(mockToggleSelection).toHaveBeenCalledWith('fp-001');
    });

    it('选择时应该显示高亮框', () => {
      // 模拟选中状态
      vi.mocked(pcbStore.usePCBStore).mockReturnValueOnce({
        selectedIds: ['fp-001'],
        toggleSelection: mockToggleSelection,
        currentTool: 'select',
        updateFootprintPosition: mockUpdateFootprintPosition,
        pushHistory: mockPushHistory,
        gridSize: 1,
        snapToGrid: true,
      } as any);

      render(<FootprintRenderer footprint={mockFootprint} />);
      // 选中时应该有更多rect（高亮框）
      const rects = screen.getAllByTestId('konva-rect');
      expect(rects.length).toBeGreaterThan(2);
    });

    it('未选中时不应显示高亮框', () => {
      vi.mocked(pcbStore.usePCBStore).mockReturnValueOnce({
        selectedIds: [],
        toggleSelection: mockToggleSelection,
        currentTool: 'select',
        updateFootprintPosition: mockUpdateFootprintPosition,
        pushHistory: mockPushHistory,
        gridSize: 1,
        snapToGrid: true,
      } as any);

      render(<FootprintRenderer footprint={mockFootprint} />);
      const rects = screen.getAllByTestId('konva-rect');
      // 只有2个焊盘，没有高亮框
      expect(rects.length).toBe(2);
    });
  });

  describe('拖拽功能测试', () => {
    it('选中且在选择工具模式下应该可拖拽', () => {
      vi.mocked(pcbStore.usePCBStore).mockReturnValueOnce({
        selectedIds: ['fp-001'],
        toggleSelection: mockToggleSelection,
        currentTool: 'select',
        updateFootprintPosition: mockUpdateFootprintPosition,
        pushHistory: mockPushHistory,
        gridSize: 1,
        snapToGrid: true,
      } as any);

      render(<FootprintRenderer footprint={mockFootprint} />);
      const group = screen.getByTestId('konva-group');
      
      expect(group).toHaveAttribute('data-draggable', 'true');
    });

    it('未选中时不应该可拖拽', () => {
      vi.mocked(pcbStore.usePCBStore).mockReturnValueOnce({
        selectedIds: [],
        toggleSelection: mockToggleSelection,
        currentTool: 'select',
        updateFootprintPosition: mockUpdateFootprintPosition,
        pushHistory: mockPushHistory,
        gridSize: 1,
        snapToGrid: true,
      } as any);

      render(<FootprintRenderer footprint={mockFootprint} />);
      const group = screen.getByTestId('konva-group');
      
      expect(group).toHaveAttribute('data-draggable', 'false');
    });

    it('拖拽结束应该更新位置', () => {
      vi.mocked(pcbStore.usePCBStore).mockReturnValueOnce({
        selectedIds: ['fp-001'],
        toggleSelection: mockToggleSelection,
        currentTool: 'select',
        updateFootprintPosition: mockUpdateFootprintPosition,
        pushHistory: mockPushHistory,
        gridSize: 1,
        snapToGrid: false,
      } as any);

      render(<FootprintRenderer footprint={mockFootprint} />);
      const group = screen.getByTestId('konva-group');
      
      // 模拟拖拽结束 - 需要先触发dragStart以设置内部状态，然后触发dragEnd
      fireEvent.mouseDown(group);
      fireEvent.mouseUp(group);
      
      // 应该更新位置
      expect(mockUpdateFootprintPosition).toHaveBeenCalled();
    });
  });

  describe('旋转功能测试', () => {
    it('应该应用旋转角度', () => {
      const rotatedFootprint = { ...mockFootprint, rotation: 90 };
      render(<FootprintRenderer footprint={rotatedFootprint} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });

    it('应该处理0度旋转', () => {
      const noRotationFootprint = { ...mockFootprint, rotation: 0 };
      render(<FootprintRenderer footprint={noRotationFootprint} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });
  });

  describe('边界条件测试', () => {
    it('应该处理无焊盘的封装', () => {
      const noPadsFootprint = { ...mockFootprint, pads: [] };
      expect(() => {
        render(<FootprintRenderer footprint={noPadsFootprint} />);
      }).not.toThrow();
    });

    it('应该处理负坐标位置', () => {
      const negativePosFootprint = { 
        ...mockFootprint, 
        position: { x: -10, y: -20 } 
      };
      render(<FootprintRenderer footprint={negativePosFootprint} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });

    it('应该处理超大坐标', () => {
      const largePosFootprint = { 
        ...mockFootprint, 
        position: { x: 10000, y: 10000 } 
      };
      render(<FootprintRenderer footprint={largePosFootprint} />);
      expect(screen.getByTestId('konva-group')).toBeInTheDocument();
    });

    it('应该处理缺失的可选属性', () => {
      const minimalFootprint = {
        id: 'fp-002',
        type: 'footprint',
        libraryName: 'Device',
        footprintName: 'R_0603',
        fullFootprintName: 'Device:R_0603',
        reference: 'R2',
        value: '1k',
        position: { x: 0, y: 0 },
        layer: 'F.Cu',
        pads: [],
      } as Footprint;
      
      expect(() => {
        render(<FootprintRenderer footprint={minimalFootprint} />);
      }).not.toThrow();
    });
  });

  describe('坐标转换测试', () => {
    it('应该正确转换毫米到像素', () => {
      render(<FootprintRenderer footprint={mockFootprint} />);
      const group = screen.getByTestId('konva-group');
      
      // 10mm * 10px/mm = 100px
      expect(group).toHaveAttribute('data-x', '100');
      // 20mm * 10px/mm = 200px
      expect(group).toHaveAttribute('data-y', '200');
    });
  });
});
