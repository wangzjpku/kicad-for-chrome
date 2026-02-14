import { useState, useEffect } from 'react'
import { useKiCadStore, LogEntry } from '../stores/kicadStore'
import { kicadApi, DRCReport, DRCItem } from '../services/api'

interface OutputPanelProps {
  dataTestId?: string
}

export default function OutputPanel({ dataTestId = 'output-panel' }: OutputPanelProps) {
  const { logs, errors, activeOutputTab, setActiveOutputTab, clearErrors } =
    useKiCadStore()
  const [drcReport, setDrcReport] = useState<DRCReport | null>(null)
  const [isLoadingDRC, setIsLoadingDRC] = useState(false)

  // 获取 DRC 报告
  const fetchDRCReport = async () => {
    setIsLoadingDRC(true)
    try {
      const report = await kicadApi.getDRCReport()
      setDrcReport(report)
    } catch (error) {
      console.error('获取 DRC 报告失败:', error)
    } finally {
      setIsLoadingDRC(false)
    }
  }

  // 当切换到 DRC 标签时获取报告
  useEffect(() => {
    if (activeOutputTab === 'drc') {
      fetchDRCReport()
    }
  }, [activeOutputTab])

  const tabs = [
    { id: 'logs', label: '日志', count: logs.length },
    { id: 'errors', label: '错误', count: errors.length },
    { id: 'drc', label: 'DRC', count: drcReport?.error_count || 0 },
  ]

  return (
    <div className="output-panel h-full flex flex-col" data-testid={dataTestId}>
      {/* 标签页 */}
      <div className="flex items-center border-b border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`output-tab ${activeOutputTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveOutputTab(tab.id)}
            data-testid={`tab-${tab.id}`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span
                className={`ml-2 px-1.5 py-0.5 rounded text-xs ${
                  tab.id === 'errors' || tab.id === 'drc' ? 'bg-red-600' : 'bg-gray-600'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}

        <div className="flex-1" />

        {activeOutputTab === 'errors' && errors.length > 0 && (
          <button
            className="px-3 py-1 text-xs text-gray-400 hover:text-white"
            onClick={clearErrors}
            data-testid="btn-clear-errors"
          >
            清除
          </button>
        )}

        {activeOutputTab === 'drc' && (
          <button
            className="px-3 py-1 text-xs text-gray-400 hover:text-white"
            onClick={fetchDRCReport}
            disabled={isLoadingDRC}
          >
            {isLoadingDRC ? '刷新中...' : '刷新'}
          </button>
        )}
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto p-2 font-mono text-sm">
        {activeOutputTab === 'logs' && <LogView logs={logs} />}
        {activeOutputTab === 'errors' && <ErrorList errors={errors} />}
        {activeOutputTab === 'drc' && (
          <DRCReportView report={drcReport} isLoading={isLoadingDRC} />
        )}
      </div>
    </div>
  )
}

interface LogViewProps {
  logs: LogEntry[]
}

function LogView({ logs }: LogViewProps) {
  if (logs.length === 0) {
    return (
      <div className="text-gray-500 text-center py-4">
        暂无日志
      </div>
    )
  }

  return (
    <div className="space-y-1" data-testid="log-content">
      {logs.map((log) => (
        <div key={log.id} className={`log-entry ${log.level}`}>
          <span className="text-gray-500 mr-2">
            {log.timestamp.toLocaleTimeString()}
          </span>
          <span>{log.message}</span>
        </div>
      ))}
    </div>
  )
}

interface ErrorListProps {
  errors: string[]
}

function ErrorList({ errors }: ErrorListProps) {
  if (errors.length === 0) {
    return (
      <div className="text-gray-500 text-center py-4" data-testid="no-errors">
        ✓ 没有错误
      </div>
    )
  }

  return (
    <div className="space-y-2" data-testid="error-list">
      {errors.map((error, index) => (
        <div
          key={index}
          className="p-2 bg-red-900/30 border border-red-800 rounded text-red-300"
        >
          <div className="flex items-start gap-2">
            <span className="text-red-500">⚠</span>
            <div>{error}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

interface DRCReportViewProps {
  report: DRCReport | null
  isLoading: boolean
}

function DRCReportView({ report, isLoading }: DRCReportViewProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-6 h-6 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mr-2" />
        加载中...
      </div>
    )
  }

  if (!report) {
    return (
      <div className="text-gray-500 text-center py-4" data-testid="drc-report">
        点击"刷新"获取 DRC 报告
      </div>
    )
  }

  return (
    <div className="space-y-4" data-testid="drc-report">
      {/* 统计信息 */}
      <div className="flex items-center gap-4 pb-2 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">错误:</span>
          <span className={report.error_count > 0 ? 'text-red-400 font-bold' : 'text-green-400'}>
            {report.error_count}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400">警告:</span>
          <span className={report.warning_count > 0 ? 'text-yellow-400 font-bold' : 'text-green-400'}>
            {report.warning_count}
          </span>
        </div>
      </div>

      {/* DRC 详细结果 */}
      {report.error_count === 0 && report.warning_count === 0 ? (
        <div className="text-green-400 text-center py-4">
          ✓ DRC 检查通过，没有发现问题
        </div>
      ) : (
        <div className="space-y-2">
          {/* 错误列表 */}
          {report.errors?.length > 0 && (
            <div>
              <h4 className="text-red-400 font-semibold mb-2">错误</h4>
              <div className="space-y-1">
                {report.errors.map((error, index) => (
                  <DRCItemView key={`error-${index}`} item={error} type="error" />
                ))}
              </div>
            </div>
          )}

          {/* 警告列表 */}
          {report.warnings?.length > 0 && (
            <div className="mt-4">
              <h4 className="text-yellow-400 font-semibold mb-2">警告</h4>
              <div className="space-y-1">
                {report.warnings.map((warning, index) => (
                  <DRCItemView key={`warning-${index}`} item={warning} type="warning" />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface DRCItemViewProps {
  item: DRCItem
  type: 'error' | 'warning'
}

function DRCItemView({ item, type }: DRCItemViewProps) {
  const bgColor = type === 'error' ? 'bg-red-900/20' : 'bg-yellow-900/20'
  const borderColor = type === 'error' ? 'border-red-800' : 'border-yellow-800'
  const textColor = type === 'error' ? 'text-red-300' : 'text-yellow-300'

  return (
    <div className={`p-2 ${bgColor} border ${borderColor} rounded ${textColor}`}>
      <div className="flex items-start gap-2">
        <span>{type === 'error' ? '⚠' : '⚡'}</span>
        <div className="flex-1">
          <div>{item.description}</div>
          {item.position && (
            <div className="text-xs text-gray-400 mt-1">
              位置: ({item.position.x.toFixed(3)}, {item.position.y.toFixed(3)})
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
