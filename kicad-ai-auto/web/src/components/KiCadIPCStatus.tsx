/**
 * KiCad IPC Status Component
 * 显示 KiCad 连接状态和板子信息
 */

import React, { useState } from 'react';
import { useKiCadIPC } from '../hooks/useKiCadIPC';

export const KiCadIPCStatus: React.FC = () => {
  const {
    connected,
    wsConnected,
    kicadState,
    error,
    startKiCad,
    stopKiCad,
    createFootprint,
    refreshStatus,
  } = useKiCadIPC();

  const [pcbFile, setPcbFile] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleStart = async () => {
    setIsLoading(true);
    try {
      await startKiCad(pcbFile || undefined);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      await stopKiCad();
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateFootprint = () => {
    createFootprint('R_0603_1608Metric', { x: 50, y: 50 }, 'F.Cu');
  };

  return (
    <div className="kicad-ipc-status p-4 bg-gray-900 text-white rounded-lg">
      <h2 className="text-xl font-bold mb-4">KiCad IPC 控制面板</h2>

      {/* 连接状态 */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm text-gray-400">WebSocket:</span>
          <span className={`px-2 py-1 rounded text-sm ${
            wsConnected ? 'bg-green-600' : 'bg-red-600'
          }`}>
            {wsConnected ? '已连接' : '未连接'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">KiCad IPC:</span>
          <span className={`px-2 py-1 rounded text-sm ${
            connected ? 'bg-green-600' : 'bg-yellow-600'
          }`}>
            {connected ? '已连接' : '未连接'}
          </span>
        </div>
      </div>

      {/* 错误显示 */}
      {error && (
        <div className="mb-4 p-2 bg-red-900 rounded text-sm">
          错误: {error}
        </div>
      )}

      {/* 控制按钮 */}
      <div className="mb-4 space-y-2">
        {!connected ? (
          <>
            <input
              type="text"
              placeholder="PCB 文件路径 (可选)"
              value={pcbFile}
              onChange={(e) => setPcbFile(e.target.value)}
              className="w-full p-2 bg-gray-800 rounded text-sm"
            />
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
            >
              {isLoading ? '启动中...' : '启动 KiCad'}
            </button>
          </>
        ) : (
          <>
            <button
              onClick={handleStop}
              disabled={isLoading}
              className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded disabled:opacity-50"
            >
              {isLoading ? '关闭中...' : '关闭 KiCad'}
            </button>
            <button
              onClick={handleCreateFootprint}
              className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 rounded"
            >
              测试: 放置电阻
            </button>
            <button
              onClick={refreshStatus}
              className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
            >
              刷新状态
            </button>
          </>
        )}
      </div>

      {/* 板子信息 */}
      {kicadState && kicadState.connected && (
        <div className="border-t border-gray-700 pt-4">
          <h3 className="font-semibold mb-2">板子信息</h3>

          {kicadState.board_path && (
            <div className="text-sm text-gray-400 mb-2">
              文件: {kicadState.board_path}
            </div>
          )}

          {kicadState.item_count !== undefined && (
            <div className="text-sm text-gray-400 mb-2">
              项目数: {kicadState.item_count}
            </div>
          )}

          {kicadState.selection && kicadState.selection.length > 0 && (
            <div className="text-sm text-gray-400 mb-2">
              已选中: {kicadState.selection.length} 项
            </div>
          )}

          {/* 项目列表 */}
          {kicadState.items && kicadState.items.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-semibold mb-2">项目列表 (前20)</h4>
              <div className="max-h-48 overflow-y-auto bg-gray-800 rounded p-2">
                {kicadState.items.slice(0, 20).map((item, idx) => (
                  <div key={idx} className="text-xs text-gray-400 py-1 border-b border-gray-700 last:border-0">
                    <span className="text-blue-400">{item.type}</span>
                    <span className="mx-2">|</span>
                    <span className="text-gray-500">{item.id.substring(0, 8)}...</span>
                    {item.layer && (
                      <>
                        <span className="mx-2">|</span>
                        <span className="text-green-400">{item.layer}</span>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 说明 */}
      <div className="mt-4 text-xs text-gray-500 border-t border-gray-700 pt-4">
        <p>💡 提示:</p>
        <ul className="list-disc list-inside mt-1 space-y-1">
          <li>需要先安装 KiCad 9.0+</li>
          <li>Windows: 确保 pywin32 已安装</li>
          <li>首次使用需在 KiCad 中启用 API: Tools → Plugins → Start Server</li>
        </ul>
      </div>
    </div>
  );
};

export default KiCadIPCStatus;
