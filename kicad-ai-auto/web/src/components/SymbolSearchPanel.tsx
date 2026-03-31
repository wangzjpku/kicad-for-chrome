/**
 * Symbol Search Panel - Phase 6
 * 符号搜索面板 - 支持模糊匹配、类别过滤、分页
 */

import { useState, useEffect, useCallback } from 'react';
import { phase6Api, SymbolInfo, SymbolSearchFilters } from '../services/api';

interface SymbolSearchPanelProps {
  onClose: () => void;
  onSymbolSelect: (symbol: SymbolInfo) => void;
}

// 类别颜色映射
const CATEGORY_COLORS: Record<string, string> = {
  resistor: '#e57373',
  capacitor: '#64b5f6',
  inductor: '#81c784',
  connector: '#ffb74d',
  ic: '#ba68c8',
  power: '#f44336',
  ground: '#795548',
  transistor: '#4db6ac',
  mosfet: '#26a69a',
  diode: '#ff7043',
  led: '#ff5722',
  switch: '#90a4ae',
  sensor: '#42a5f5',
  mcu: '#7e57c2',
  interface: '#5c6bc0',
  crystal: '#26c6da',
  relay: '#8d6e63',
  fuse: '#d4e157',
  other: '#78909c',
};

export default function SymbolSearchPanel({ onClose, onSymbolSelect }: SymbolSearchPanelProps) {
  const [query, setQuery] = useState('');
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categories, setCategories] = useState<string[]>([]);

  // 加载类别列表
  useEffect(() => {
    phase6Api.getSymbolCategories().then((res) => {
      if (res.success) {
        setCategories(res.categories);
      }
    }).catch(console.error);
  }, []);

  // 搜索函数
  const searchSymbols = useCallback(async () => {
    setLoading(true);
    try {
      const filters: SymbolSearchFilters = {};
      if (selectedCategory) {
        filters.category = selectedCategory;
      }

      const result = await phase6Api.searchSymbols(query, filters, page, pageSize);
      if (result.success) {
        setSymbols(result.symbols);
        setTotal(result.total);
      }
    } catch (error) {
      console.error('Symbol search failed:', error);
    } finally {
      setLoading(false);
    }
  }, [query, selectedCategory, page, pageSize]);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      searchSymbols();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchSymbols]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#323232',
          borderRadius: 8,
          width: 800,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #4a4a4a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <h3 style={{ margin: 0, color: '#e0e0e0', fontSize: 16 }}>
            符号搜索
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#a0a0a0',
              cursor: 'pointer',
              fontSize: 20,
              padding: 4,
            }}
          >
            x
          </button>
        </div>

        {/* Search Input */}
        <div style={{ padding: 16, borderBottom: '1px solid #4a4a4a' }}>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
            placeholder="搜索符号名称、描述或关键词..."
            style={{
              width: '100%',
              padding: '10px 14px',
              backgroundColor: '#2d2d2d',
              border: '1px solid #4a4a4a',
              borderRadius: 4,
              color: '#e0e0e0',
              fontSize: 14,
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />

          {/* Category Filters */}
          <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            <button
              onClick={() => {
                setSelectedCategory(null);
                setPage(1);
              }}
              style={{
                padding: '4px 10px',
                backgroundColor: selectedCategory === null ? '#4a9eff' : '#3d3d3d',
                border: '1px solid #4a4a4a',
                borderRadius: 4,
                color: selectedCategory === null ? '#fff' : '#a0a0a0',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              全部
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  setSelectedCategory(cat);
                  setPage(1);
                }}
                style={{
                  padding: '4px 10px',
                  backgroundColor: selectedCategory === cat ? '#4a9eff' : '#3d3d3d',
                  border: '1px solid #4a4a4a',
                  borderRadius: 4,
                  color: selectedCategory === cat ? '#fff' : CATEGORY_COLORS[cat] || '#a0a0a0',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Results */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: 8,
          }}
        >
          {loading ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: 200,
                color: '#a0a0a0',
              }}
            >
              搜索中...
            </div>
          ) : symbols.length === 0 ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: 200,
                color: '#a0a0a0',
              }}
            >
              {query ? '未找到匹配的符号' : '请输入搜索关键词'}
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 8,
              }}
            >
              {symbols.map((symbol) => (
                <div
                  key={`${symbol.library}:${symbol.name}`}
                  onClick={() => onSymbolSelect(symbol)}
                  style={{
                    padding: 12,
                    backgroundColor: '#3d3d3d',
                    borderRadius: 6,
                    cursor: 'pointer',
                    border: '1px solid transparent',
                    transition: 'border-color 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#4a9eff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'transparent';
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 6,
                    }}
                  >
                    <span
                      style={{
                        padding: '2px 8px',
                        backgroundColor: CATEGORY_COLORS[symbol.category] || '#78909c',
                        borderRadius: 3,
                        fontSize: 10,
                        color: '#fff',
                      }}
                    >
                      {symbol.category}
                    </span>
                    <span style={{ color: '#e0e0e0', fontWeight: 500, fontSize: 14 }}>
                      {symbol.name}
                    </span>
                  </div>
                  <div style={{ color: '#a0a0a0', fontSize: 12 }}>
                    {symbol.description}
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      gap: 12,
                      marginTop: 6,
                      fontSize: 11,
                      color: '#707070',
                    }}
                  >
                    <span>库: {symbol.library}</span>
                    <span>封装: {symbol.package}</span>
                    <span>引脚: {symbol.pin_count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid #4a4a4a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span style={{ color: '#a0a0a0', fontSize: 12 }}>
            共 {total} 个结果
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{
                padding: '6px 12px',
                backgroundColor: '#3d3d3d',
                border: '1px solid #4a4a4a',
                borderRadius: 4,
                color: page <= 1 ? '#707070' : '#e0e0e0',
                cursor: page <= 1 ? 'not-allowed' : 'pointer',
                fontSize: 12,
              }}
            >
              上一页
            </button>
            <span style={{ color: '#e0e0e0', fontSize: 12, padding: '6px 8px' }}>
              {page} / {totalPages || 1}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              style={{
                padding: '6px 12px',
                backgroundColor: '#3d3d3d',
                border: '1px solid #4a4a4a',
                borderRadius: 4,
                color: page >= totalPages ? '#707070' : '#e0e0e0',
                cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                fontSize: 12,
              }}
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
