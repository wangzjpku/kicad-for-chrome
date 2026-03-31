/**
 * Template Selector - Phase 6
 * 模板选择器 - 选择项目模板
 */

import { useState, useEffect, useCallback } from 'react';
import { phase6Api, TemplateInfo, TemplateDetail } from '../services/api';

interface TemplateSelectorProps {
  onClose: () => void;
  onSelect: (templateId: string, projectName: string) => void;
  onUseTemplate?: (templateId: string, projectName: string) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  mcu_board: '#ba68c8',
  power: '#f44336',
  sensor: '#42a5f5',
  interface: '#5c6bc0',
  wireless: '#26c6da',
  display: '#ff7043',
  motor: '#8d6e63',
  custom: '#78909c',
};

export default function TemplateSelector({ onClose, onSelect }: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [categories, setCategories] = useState<Array<{ value: string; label: string }>>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null);
  const [projectName, setProjectName] = useState('');
  const [creating, setCreating] = useState(false);

  // 加载模板列表
  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const result = await phase6Api.getTemplates(
        selectedCategory || undefined,
        searchKeyword || undefined
      );
      if (result.success) {
        setTemplates(result.templates);
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, searchKeyword]);

  // 加载类别
  useEffect(() => {
    phase6Api.getTemplateCategories().then((res) => {
      if (res.success) {
        setCategories(res.categories);
      }
    }).catch(console.error);
  }, []);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      loadTemplates();
    }, 300);
    return () => clearTimeout(timer);
  }, [loadTemplates]);

  // 加载选中模板详情
  const handleTemplateClick = async (template: TemplateInfo) => {
    try {
      const result = await phase6Api.getTemplate(template.template_id);
      if (result.success) {
        setSelectedTemplate(result.template);
        setProjectName(`${template.name_cn || template.name} 项目`);
      }
    } catch (error) {
      console.error('Failed to load template detail:', error);
    }
  };

  // 创建项目
  const handleCreate = async () => {
    if (!selectedTemplate || !projectName.trim()) return;

    setCreating(true);
    try {
      const result = await phase6Api.createProjectFromTemplate(
        selectedTemplate.template_id,
        projectName.trim()
      );
      if (result.success) {
        onSelect(result.project_id, result.project_name);
      }
    } catch (error) {
      console.error('Failed to create project from template:', error);
    } finally {
      setCreating(false);
    }
  };

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
          width: 950,
          maxHeight: '85vh',
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
            选择项目模板
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

        {/* Content */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
          {/* Left: Template List */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid #4a4a4a' }}>
            {/* Filters */}
            <div style={{ padding: 12, borderBottom: '1px solid #4a4a4a' }}>
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                placeholder="搜索模板..."
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: '#2d2d2d',
                  border: '1px solid #4a4a4a',
                  borderRadius: 4,
                  color: '#e0e0e0',
                  fontSize: 13,
                  boxSizing: 'border-box',
                  marginBottom: 10,
                }}
              />

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                <button
                  onClick={() => setSelectedCategory(null)}
                  style={{
                    padding: '4px 10px',
                    backgroundColor: selectedCategory === null ? '#4a9eff' : '#3d3d3d',
                    border: '1px solid #4a4a4a',
                    borderRadius: 4,
                    color: '#fff',
                    fontSize: 11,
                    cursor: 'pointer',
                  }}
                >
                  全部
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.value}
                    onClick={() => setSelectedCategory(cat.value)}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: selectedCategory === cat.value ? '#4a9eff' : '#3d3d3d',
                      border: '1px solid #4a4a4a',
                      borderRadius: 4,
                      color: selectedCategory === cat.value ? '#fff' : CATEGORY_COLORS[cat.value] || '#a0a0a0',
                      fontSize: 11,
                      cursor: 'pointer',
                    }}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Template Grid */}
            <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: '#707070' }}>
                  加载中...
                </div>
              ) : templates.length === 0 ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: '#707070' }}>
                  未找到模板
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
                  {templates.map((template) => (
                    <div
                      key={template.template_id}
                      onClick={() => handleTemplateClick(template)}
                      style={{
                        padding: 12,
                        backgroundColor: selectedTemplate?.template_id === template.template_id ? '#4a4a4a' : '#3d3d3d',
                        borderRadius: 6,
                        cursor: 'pointer',
                        border: `2px solid ${selectedTemplate?.template_id === template.template_id ? '#4a9eff' : 'transparent'}`,
                        transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <span
                          style={{
                            padding: '2px 8px',
                            backgroundColor: CATEGORY_COLORS[template.category] || '#78909c',
                            borderRadius: 3,
                            fontSize: 10,
                            color: '#fff',
                          }}
                        >
                          {template.category}
                        </span>
                        {template.is_predefined && (
                          <span style={{ fontSize: 10, color: '#4a9eff' }}>预定义</span>
                        )}
                      </div>
                      <div style={{ color: '#e0e0e0', fontWeight: 500, fontSize: 13, marginBottom: 4 }}>
                        {template.name}
                      </div>
                      <div style={{ color: '#a0a0a0', fontSize: 11 }}>
                        {template.name_cn}
                      </div>
                      <div style={{ color: '#707070', fontSize: 10, marginTop: 6 }}>
                        {template.description?.substring(0, 60)}
                        {template.description && template.description.length > 60 ? '...' : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Template Detail */}
          <div style={{ width: 320, display: 'flex', flexDirection: 'column' }}>
            {selectedTemplate ? (
              <>
                <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
                  <h4 style={{ margin: '0 0 12px 0', color: '#e0e0e0', fontSize: 14 }}>
                    {selectedTemplate.name}
                  </h4>
                  <p style={{ margin: '0 0 12px 0', color: '#a0a0a0', fontSize: 12 }}>
                    {selectedTemplate.description}
                  </p>

                  <div style={{ marginBottom: 12 }}>
                    <div style={{ color: '#707070', fontSize: 11, marginBottom: 4 }}>标签</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {selectedTemplate.tags.map((tag) => (
                        <span
                          key={tag}
                          style={{
                            padding: '2px 8px',
                            backgroundColor: '#3d3d3d',
                            borderRadius: 3,
                            fontSize: 10,
                            color: '#a0a0a0',
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginBottom: 12 }}>
                    <div style={{ color: '#707070', fontSize: 11, marginBottom: 4 }}>作者</div>
                    <div style={{ color: '#e0e0e0', fontSize: 12 }}>{selectedTemplate.author}</div>
                  </div>

                  {selectedTemplate.schematic && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ color: '#707070', fontSize: 11, marginBottom: 4 }}>原理图元件</div>
                      <div style={{ color: '#e0e0e0', fontSize: 12 }}>
                        {(selectedTemplate.schematic.components as any[])?.length || 0} 个
                      </div>
                    </div>
                  )}

                  {selectedTemplate.pcb && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ color: '#707070', fontSize: 11, marginBottom: 4 }}>PCB 层数</div>
                      <div style={{ color: '#e0e0e0', fontSize: 12 }}>
                        {(selectedTemplate.pcb as any).layers || 2} 层
                      </div>
                    </div>
                  )}
                </div>

                {/* Project Name Input */}
                <div style={{ padding: 16, borderTop: '1px solid #4a4a4a' }}>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 6 }}>
                    项目名称
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="输入项目名称"
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      backgroundColor: '#2d2d2d',
                      border: '1px solid #4a4a4a',
                      borderRadius: 4,
                      color: '#e0e0e0',
                      fontSize: 13,
                      boxSizing: 'border-box',
                      marginBottom: 12,
                    }}
                  />
                  <button
                    onClick={handleCreate}
                    disabled={!projectName.trim() || creating}
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: projectName.trim() && !creating ? '#4a9eff' : '#3d3d3d',
                      border: 'none',
                      borderRadius: 4,
                      color: '#fff',
                      fontSize: 13,
                      cursor: projectName.trim() && !creating ? 'pointer' : 'not-allowed',
                      opacity: creating ? 0.6 : 1,
                    }}
                  >
                    {creating ? '创建中...' : '使用此模板创建项目'}
                  </button>
                </div>
              </>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#707070', fontSize: 12 }}>
                选择一个模板查看详情
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
