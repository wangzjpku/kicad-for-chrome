/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * TrackRenderer 组件测试
 * 测试走线渲染和选择功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TrackRenderer from '../canvas/TrackRenderer';
import { Track } from '../types';

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
  Line: ({ points, stroke, strokeWidth, onClick }: any) => (
    <div
      data-testid="konva-line"
      data-points={JSON.stringify(points)}
      data-stroke={stroke}
      data-stroke-width={strokeWidth}
      onClick={onClick}
      style={{ 
        border: `${strokeWidth}px solid ${stroke}`,
        width: '100px',
        height: '2px'
      }}
    />
  ),
}));

describe('TrackRenderer', () => {
  const mockTrack: Track = {
    id: 'track-001',
    type: 'track',
    layer: 'F.Cu',
    width: 0.25,
    points: [
      { x: 10, y: 10 },
      { x: 50, y: 10 },
    ],
    netId: 'net-001',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset default mock return value
    mockUsePCBStore.mockReturnValue({
      selectedIds: [],
      toggleSelection: mockToggleSelection,
    });
  });

  describe('渲染测试', () => {
    it('应该渲染走线', () => {
      render(<TrackRenderer track={mockTrack} />);
      expect(screen.getByTestId('konva-line')).toBeInTheDocument();
    });

    it('应该正确设置走线宽度', () => {
      render(<TrackRenderer track={mockTrack} />);
      const line = screen.getByTestId('konva-line');
      // 0.25mm * 10px/mm = 2.5px
      expect(line).toHaveAttribute('data-stroke-width', '2.5');
    });

    it('F.Cu层应该显示为红色', () => {
      render(<TrackRenderer track={mockTrack} />);
      const line = screen.getByTestId('konva-line');
      expect(line).toHaveAttribute('data-stroke', '#FF0000');
    });

    it('B.Cu层应该显示为绿色', () => {
      const bCuTrack = { ...mockTrack, layer: 'B.Cu' };
      render(<TrackRenderer track={bCuTrack} />);
      const line = screen.getByTestId('konva-line');
      expect(line).toHaveAttribute('data-stroke', '#00FF00');
    });

    it('选中时应该显示高亮颜色', () => {
      // Override mock to return selected track
      mockUsePCBStore.mockReturnValueOnce({
        selectedIds: ['track-001'],
        toggleSelection: mockToggleSelection,
      });

      render(<TrackRenderer track={mockTrack} />);
      const line = screen.getByTestId('konva-line');
      expect(line).toHaveAttribute('data-stroke', '#FFFF00');
    });
  });

  describe('交互测试', () => {
    it('点击走线应该触发选择', () => {
      render(<TrackRenderer track={mockTrack} />);
      const line = screen.getByTestId('konva-line');
      
      fireEvent.click(line);
      
      expect(mockToggleSelection).toHaveBeenCalledWith('track-001');
    });

    it('点击走线应该阻止事件冒泡', () => {
      const parentClick = vi.fn();
      render(
        <div onClick={parentClick}>
          <TrackRenderer track={mockTrack} />
        </div>
      );
      
      const line = screen.getByTestId('konva-line');
      fireEvent.click(line);
      
      // 检查cancelBubble是否被设置
      expect(mockToggleSelection).toHaveBeenCalled();
    });
  });

  describe('边界条件测试', () => {
    it('应该处理单点走线', () => {
      const singlePointTrack = { ...mockTrack, points: [{ x: 10, y: 10 }] };
      expect(() => {
        render(<TrackRenderer track={singlePointTrack} />);
      }).not.toThrow();
    });

    it('应该处理多点走线', () => {
      const multiPointTrack = {
        ...mockTrack,
        points: [
          { x: 0, y: 0 },
          { x: 10, y: 0 },
          { x: 10, y: 10 },
          { x: 20, y: 10 },
        ],
      };
      render(<TrackRenderer track={multiPointTrack} />);
      const line = screen.getByTestId('konva-line');
      const points = JSON.parse(line.getAttribute('data-points') || '[]');
      expect(points.length).toBe(8); // 4 points * 2 coordinates
    });

    it('应该处理负坐标', () => {
      const negativeTrack = {
        ...mockTrack,
        points: [
          { x: -10, y: -10 },
          { x: -50, y: -10 },
        ],
      };
      expect(() => {
        render(<TrackRenderer track={negativeTrack} />);
      }).not.toThrow();
    });

    it('应该处理超细走线', () => {
      const thinTrack = { ...mockTrack, width: 0.05 };
      render(<TrackRenderer track={thinTrack} />);
      const line = screen.getByTestId('konva-line');
      expect(line).toBeInTheDocument();
    });

    it('应该处理超粗走线', () => {
      const thickTrack = { ...mockTrack, width: 2.0 };
      render(<TrackRenderer track={thickTrack} />);
      const line = screen.getByTestId('konva-line');
      expect(line).toBeInTheDocument();
    });
  });

  describe('坐标转换测试', () => {
    it('应该正确转换毫米到像素', () => {
      render(<TrackRenderer track={mockTrack} />);
      const line = screen.getByTestId('konva-line');
      const points = JSON.parse(line.getAttribute('data-points') || '[]');
      
      // 10mm * 10px/mm = 100px
      expect(points[0]).toBe(100);
      expect(points[1]).toBe(100);
      // 50mm * 10px/mm = 500px
      expect(points[2]).toBe(500);
      expect(points[3]).toBe(100);
    });
  });
});
