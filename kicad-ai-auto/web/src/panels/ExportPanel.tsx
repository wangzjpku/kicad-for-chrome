/**
 * 导出面板 (Phase 5.4)
 */

import React, { useState } from 'react';
import { usePCBStore } from '../stores/pcbStore';
import { exportApi, ApiResponse, ExportResultData } from '../services/api';

interface ExportPanelProps {
  onClose?: () => void;
}

const ExportPanel: React.FC<ExportPanelProps> = ({ onClose }) => {
  const { projectId } = usePCBStore();
  const [exporting, setExporting] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const handleExport = async (type: string, exportFn: () => Promise<ApiResponse<ExportResultData>>) => {
    if (!projectId) {
      setResults(prev => ({
        ...prev,
        [type]: { success: false, message: 'No project loaded' }
      }));
      return;
    }

    setExporting(type);
    try {
      const response = await exportFn();
      if (response.success) {
        setResults(prev => ({
          ...prev,
          [type]: { success: true, message: 'Export successful' }
        }));
      } else {
        setResults(prev => ({
          ...prev,
          [type]: { success: false, message: response.error || 'Export failed' }
        }));
      }
    } catch (_error) {
      setResults(prev => ({
        ...prev,
        [type]: { success: false, message: 'Network error' }
      }));
    } finally {
      setExporting(null);
    }
  };

  const exportFormats = [
    {
      id: 'gerber',
      name: 'Gerber Files',
      description: 'Standard PCB manufacturing format',
      icon: '📄',
      action: () => handleExport('gerber', () => exportApi.exportGerber(projectId!))
    },
    {
      id: 'drill',
      name: 'Drill Files',
      description: 'NC drill and route files',
      icon: '🔩',
      action: () => handleExport('drill', () => exportApi.exportDrill(projectId!))
    },
    {
      id: 'bom',
      name: 'Bill of Materials',
      description: 'CSV format component list',
      icon: '📋',
      action: () => handleExport('bom', () => exportApi.exportBOM(projectId!))
    },
    {
      id: 'step',
      name: '3D Model (STEP)',
      description: '3D mechanical model',
      icon: '🧊',
      action: () => handleExport('step', () => exportApi.exportSTEP(projectId!))
    }
  ];

  return (
    <div style={{ padding: '20px', maxWidth: '500px' }}>
      <h2 style={{ color: '#ffffff', margin: '0 0 20px 0', fontSize: '18px' }}>
        Export Project
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {exportFormats.map(format => (
          <div
            key={format.id}
            style={{
              padding: '16px',
              backgroundColor: '#2d2d2d',
              borderRadius: '8px',
              border: '1px solid #3d3d3d',
              display: 'flex',
              alignItems: 'center',
              gap: '16px'
            }}
          >
            <div style={{ fontSize: '24px' }}>{format.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ color: '#ffffff', fontSize: '14px', fontWeight: 'bold' }}>
                {format.name}
              </div>
              <div style={{ color: '#888888', fontSize: '12px' }}>
                {format.description}
              </div>
              {results[format.id] && (
                <div
                  style={{
                    color: results[format.id].success ? '#4caf50' : '#ff4444',
                    fontSize: '11px',
                    marginTop: '4px'
                  }}
                >
                  {results[format.id].message}
                </div>
              )}
            </div>
            <button
              onClick={format.action}
              disabled={exporting === format.id || !projectId}
              style={{
                padding: '8px 16px',
                backgroundColor: exporting === format.id ? '#3d3d3d' : '#4a9eff',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                cursor: exporting === format.id || !projectId ? 'not-allowed' : 'pointer',
                fontSize: '12px',
                minWidth: '80px'
              }}
            >
              {exporting === format.id ? '...' : 'Export'}
            </button>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: '20px',
          padding: '12px',
          backgroundColor: '#1a1a1a',
          borderRadius: '4px',
          color: '#666666',
          fontSize: '11px'
        }}
      >
        💡 Exported files will be saved to C:\KiCadWebEditor\output\
      </div>

      {onClose && (
        <button
          onClick={onClose}
          style={{
            marginTop: '20px',
            width: '100%',
            padding: '10px',
            backgroundColor: '#3d3d3d',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Close
        </button>
      )}
    </div>
  );
};

export default ExportPanel;
