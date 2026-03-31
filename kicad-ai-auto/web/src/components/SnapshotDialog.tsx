/**
 * SnapshotDialog - 项目快照管理对话框组件
 *
 * 功能:
 * - 查看项目快照列表
 * - 创建新快照
 * - 恢复到指定快照
 * - 删除快照
 */

import React, { useState, useEffect } from 'react';
import { snapshotApi, Snapshot } from '../services/api';
import './SnapshotDialog.css';

interface SnapshotDialogProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onSnapshotRestored?: (snapshot: Snapshot) => void;
}

type TabType = 'list' | 'create';

export const SnapshotDialog: React.FC<SnapshotDialogProps> = ({
  isOpen,
  onClose,
  projectId,
  onSnapshotRestored,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('list');
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);

  // Create form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [includeSchematic, setIncludeSchematic] = useState(true);
  const [includePcb, setIncludePcb] = useState(true);
  const [creating, setCreating] = useState(false);

  // Restore state
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    if (isOpen && projectId) {
      loadSnapshots();
    }
  }, [isOpen, projectId]);

  const loadSnapshots = async () => {
    setLoading(true);
    try {
      const response = await snapshotApi.list(projectId);
      if (response.success && response.data?.snapshots) {
        setSnapshots(response.data.snapshots);
      }
    } catch (error) {
      console.error('加载快照失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSnapshot = async () => {
    if (!title.trim()) {
      alert('请输入快照标题');
      return;
    }

    setCreating(true);
    try {
      const response = await snapshotApi.create(projectId, {
        title: title.trim(),
        description: description.trim(),
        include_schematic: includeSchematic,
        include_pcb: includePcb,
      });

      if (response.success) {
        alert('快照创建成功');
        setTitle('');
        setDescription('');
        setActiveTab('list');
        loadSnapshots();
      }
    } catch (error) {
      console.error('创建快照失败:', error);
      alert('创建快照失败');
    } finally {
      setCreating(false);
    }
  };

  const handleRestoreSnapshot = async (snapshot: Snapshot) => {
    if (!confirm(`确定要恢复到版本 ${snapshot.version} 吗？当前未保存的更改将会丢失。`)) {
      return;
    }

    setRestoring(true);
    try {
      const response = await snapshotApi.restore(projectId, snapshot.id);
      if (response.success) {
        alert(`已恢复到版本 ${snapshot.version}`);
        onSnapshotRestored?.(snapshot);
        onClose();
      }
    } catch (error) {
      console.error('恢复快照失败:', error);
      alert('恢复快照失败');
    } finally {
      setRestoring(false);
    }
  };

  const handleDeleteSnapshot = async (snapshot: Snapshot) => {
    if (!confirm(`确定要删除快照 "${snapshot.title}" 吗？此操作不可恢复。`)) {
      return;
    }

    try {
      const response = await snapshotApi.delete(projectId, snapshot.id);
      if (response.success) {
        setSnapshots(snapshots.filter(s => s.id !== snapshot.id));
        if (selectedSnapshot?.id === snapshot.id) {
          setSelectedSnapshot(null);
        }
      }
    } catch (error) {
      console.error('删除快照失败:', error);
      alert('删除快照失败');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="snapshot-dialog" onClick={onClose}>
      <div className="snapshot-dialog-content" onClick={e => e.stopPropagation()}>
        <div className="snapshot-dialog-header">
          <h3>项目快照</h3>
          <button className="snapshot-dialog-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="snapshot-dialog-body">
          {/* Tabs */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button
              className={`snapshot-btn ${activeTab === 'list' ? 'snapshot-btn-primary' : 'snapshot-btn-secondary'}`}
              onClick={() => setActiveTab('list')}
            >
              快照列表
            </button>
            <button
              className={`snapshot-btn ${activeTab === 'create' ? 'snapshot-btn-primary' : 'snapshot-btn-secondary'}`}
              onClick={() => setActiveTab('create')}
            >
              创建快照
            </button>
          </div>

          {/* List Tab */}
          {activeTab === 'list' && (
            <div className="snapshot-list">
              {loading ? (
                <div className="snapshot-loading">加载中...</div>
              ) : snapshots.length === 0 ? (
                <div className="snapshot-empty">
                  <div className="snapshot-empty-icon">📸</div>
                  <p>暂无快照</p>
                  <p style={{ fontSize: '12px' }}>创建第一个快照来保存当前工作进度</p>
                </div>
              ) : (
                snapshots.map(snapshot => (
                  <div
                    key={snapshot.id}
                    className={`snapshot-item ${selectedSnapshot?.id === snapshot.id ? 'selected' : ''}`}
                    onClick={() => setSelectedSnapshot(snapshot)}
                  >
                    <div className="snapshot-item-header">
                      <span className="snapshot-item-title">{snapshot.title}</span>
                      <span className="snapshot-item-version">v{snapshot.version}</span>
                    </div>
                    <div className="snapshot-item-date">
                      {new Date(snapshot.created_at).toLocaleString('zh-CN')}
                    </div>
                    {snapshot.description && (
                      <div className="snapshot-item-description">{snapshot.description}</div>
                    )}
                    <div className="snapshot-item-badges">
                      {snapshot.has_schematic && (
                        <span className="snapshot-badge schematic">原理图</span>
                      )}
                      {snapshot.has_pcb && <span className="snapshot-badge pcb">PCB</span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Create Tab */}
          {activeTab === 'create' && (
            <div className="snapshot-form">
              <div className="snapshot-form-group">
                <label>快照标题 *</label>
                <input
                  type="text"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="例如：完成电源部分设计"
                />
              </div>
              <div className="snapshot-form-group">
                <label>描述</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="可选：描述此快照包含的内容"
                  rows={3}
                />
              </div>
              <div className="snapshot-form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={includeSchematic}
                    onChange={e => setIncludeSchematic(e.target.checked)}
                  />{' '}
                  包含原理图数据
                </label>
              </div>
              <div className="snapshot-form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={includePcb}
                    onChange={e => setIncludePcb(e.target.checked)}
                  />{' '}
                  包含 PCB 数据
                </label>
              </div>
            </div>
          )}
        </div>

        <div className="snapshot-dialog-footer">
          {activeTab === 'list' && selectedSnapshot && (
            <>
              <button
                className="snapshot-btn snapshot-btn-danger"
                onClick={() => handleDeleteSnapshot(selectedSnapshot)}
              >
                删除
              </button>
              <button
                className="snapshot-btn snapshot-btn-primary"
                onClick={() => handleRestoreSnapshot(selectedSnapshot)}
                disabled={restoring}
              >
                {restoring ? '恢复中...' : '恢复到该版本'}
              </button>
            </>
          )}
          {activeTab === 'create' && (
            <>
              <button
                className="snapshot-btn snapshot-btn-secondary"
                onClick={() => setActiveTab('list')}
              >
                取消
              </button>
              <button
                className="snapshot-btn snapshot-btn-primary"
                onClick={handleCreateSnapshot}
                disabled={creating || !title.trim()}
              >
                {creating ? '创建中...' : '创建快照'}
              </button>
            </>
          )}
          {activeTab === 'list' && !selectedSnapshot && (
            <button className="snapshot-btn snapshot-btn-secondary" onClick={onClose}>
              关闭
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SnapshotDialog;
