import { useState } from 'react'
import { kicadApi } from '../services/api'
import { useKiCadStore } from '../stores/kicadStore'

interface Symbol {
  name: string
  library: string
  description: string
  footprint?: string
}

interface SymbolSelectorProps {
  onClose: () => void
  onSymbolSelect: (symbol: Symbol) => void
}

// 内置符号库
const BUILTIN_SYMBOLS: Symbol[] = [
  { name: 'R', library: 'Device', description: '电阻', footprint: 'R_0603_1608Metric' },
  { name: 'C', library: 'Device', description: '电容', footprint: 'C_0603_1608Metric' },
  { name: 'L', library: 'Device', description: '电感', footprint: 'L_0603_1608Metric' },
  { name: 'D', library: 'Device', description: '二极管', footprint: 'D_0603_1608Metric' },
  { name: 'LED', library: 'Device', description: 'LED', footprint: 'LED_0603_1608Metric' },
  { name: 'Q_NPN', library: 'Device', description: 'NPN 三极管', footprint: 'SOT-23' },
  { name: 'Q_PNP', library: 'Device', description: 'PNP 三极管', footprint: 'SOT-23' },
  { name: 'U', library: 'Device', description: '集成电路', footprint: 'SOIC-8' },
  { name: 'J', library: 'Connector', description: '连接器', footprint: 'PinHeader_1x02_P2.54mm_Vertical' },
  { name: 'SW', library: 'Switch', description: '开关', footprint: 'SW_Push_1P1T_NO_6x6mm_H9.5mm' },
  { name: 'Y', library: 'Device', description: '晶振', footprint: 'Crystal_SMD_3225-4Pin_3.2x2.5mm' },
  { name: 'BT', library: 'Device', description: '电池', footprint: 'BatteryHolder_Keystone_3000_1x12mm' },
  { name: 'F', library: 'Device', description: '保险丝', footprint: 'Fuse_1206_3216Metric' },
  { name: 'LMP', library: 'Device', description: '灯座', footprint: 'LED_5mm_Radial' },
  { name: 'MIC', library: 'Device', description: '麦克风', footprint: 'MIC_CMA-4544PF-W' },
  { name: 'SP', library: 'Device', description: '扬声器', footprint: 'Buzzer_12x9.5RM7.6' },
  { name: 'Xtal', library: 'Device', description: '晶体', footprint: 'Crystal_SMD_5032-2Pin_5.0x3.2mm' },
  { name: 'Varistor', library: 'Device', description: '压敏电阻', footprint: 'Varistor_Disc_D7mm' },
  { name: 'Thermistor', library: 'Device', description: '热敏电阻', footprint: 'R_0603_1608Metric' },
  { name: 'Pot', library: 'Device', description: '电位器', footprint: 'Potentiometer_Bourns_3386P_Vertical' },
]

export default function SymbolSelector({ onClose, onSymbolSelect }: SymbolSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [isLoading, setIsLoading] = useState(false)
  const { addLog, addError } = useKiCadStore()

  // 过滤符号
  const filteredSymbols = BUILTIN_SYMBOLS.filter((symbol) => {
    const matchesSearch = 
      symbol.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      symbol.description.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (selectedCategory === 'all') return matchesSearch
    if (selectedCategory === 'passive') {
      return matchesSearch && ['R', 'C', 'L'].includes(symbol.name)
    }
    if (selectedCategory === 'active') {
      return matchesSearch && ['D', 'LED', 'Q_NPN', 'Q_PNP', 'U'].includes(symbol.name)
    }
    if (selectedCategory === 'mech') {
      return matchesSearch && ['J', 'SW', 'BT'].includes(symbol.name)
    }
    return matchesSearch
  })

  const handleSymbolClick = async (symbol: Symbol) => {
    setIsLoading(true)
    try {
      // 激活放置符号工具
      await kicadApi.activateTool('place_symbol', { symbol: symbol.name })
      
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'success',
        message: `已选择符号: ${symbol.name} (${symbol.description})`,
      })
      
      onSymbolSelect(symbol)
      onClose()
    } catch (error) {
      const message = error instanceof Error ? error.message : '选择符号失败'
      addError(message)
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'error',
        message,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const categories = [
    { id: 'all', label: '全部' },
    { id: 'passive', label: '被动器件' },
    { id: 'active', label: '主动器件' },
    { id: 'mech', label: '机械/接口' },
  ]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-[600px] max-h-[80vh] flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">选择符号</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-xl"
            disabled={isLoading}
          >
            ×
          </button>
        </div>

        {/* 搜索和分类 */}
        <div className="p-4 border-b border-gray-700 space-y-3">
          <input
            type="text"
            placeholder="搜索符号..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm"
            disabled={isLoading}
          />
          
          <div className="flex gap-2">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1 rounded text-sm ${
                  selectedCategory === cat.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                disabled={isLoading}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* 符号列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {filteredSymbols.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              没有找到匹配的符号
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {filteredSymbols.map((symbol) => (
                <button
                  key={symbol.name}
                  onClick={() => handleSymbolClick(symbol)}
                  className="flex items-center gap-3 p-3 bg-gray-700 hover:bg-gray-600 rounded text-left transition-colors"
                  disabled={isLoading}
                >
                  <div className="w-10 h-10 bg-gray-600 rounded flex items-center justify-center text-lg">
                    {symbol.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{symbol.name}</div>
                    <div className="text-sm text-gray-400 truncate">
                      {symbol.description}
                    </div>
                    {symbol.footprint && (
                      <div className="text-xs text-gray-500 truncate">
                        {symbol.footprint}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 底部信息 */}
        <div className="p-4 border-t border-gray-700 text-sm text-gray-400">
          共 {filteredSymbols.length} 个符号
          {isLoading && (
            <span className="ml-2">处理中...</span>
          )}
        </div>
      </div>
    </div>
  )
}
