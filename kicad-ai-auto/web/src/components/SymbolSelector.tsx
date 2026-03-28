import { useState } from 'react'
import { kicadApi } from '../services/api'
import { useKiCadStore } from '../stores/kicadStore'

interface Symbol {
  name: string
  library: string
  description: string
  footprint?: string
  footprintSource?: 'builtin' | 'library' | 'default_mapping' | 'fallback'  // 封装来源
  pins?: Array<{ number: string; name: string; type: string }>
}

interface SymbolSelectorProps {
  onClose: () => void
  onSymbolSelect: (symbol: Symbol) => void
}

// 内置符号库 - 扩展版
const BUILTIN_SYMBOLS: Symbol[] = [
  // 电阻类
  { name: 'R', library: 'Device', description: '电阻', footprint: 'Resistor_SMD:R_0603_1608Metric' },
  { name: 'R_Potentiometer', library: 'Device', description: '电位器', footprint: 'Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical' },
  { name: 'R_Photo', library: 'Device', description: '光敏电阻', footprint: 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal' },
  { name: 'Thermistor', library: 'Device', description: '热敏电阻', footprint: 'Resistor_SMD:R_0603_1608Metric' },
  { name: 'Varistor', library: 'Device', description: '压敏电阻', footprint: 'Varistor_THT:Varistor_Disc_D7mm' },
  
  // 电容类
  { name: 'C', library: 'Device', description: '电容', footprint: 'Capacitor_SMD:C_0603_1608Metric' },
  { name: 'C_Polarized', library: 'Device', description: '电解电容', footprint: 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm' },
  { name: 'C_Variable', library: 'Device', description: '可变电容', footprint: 'Capacitor_THT:C_Trimmer_Suntan_TLC-07' },
  { name: 'CP', library: 'Device', description: '极性电容', footprint: 'Capacitor_SMD:CP_Elec_4x5.4' },
  
  // 电感类
  { name: 'L', library: 'Device', description: '电感', footprint: 'Inductor_SMD:L_0603_1608Metric' },
  { name: 'L_Ferrite', library: 'Device', description: '铁氧体磁珠', footprint: 'Inductor_SMD:L_0603_1608Metric' },
  { name: 'Transformer', library: 'Device', description: '变压器', footprint: 'Transformer_THT:Transformer_Breve_TEZ-22x24' },
  
  // 二极管类
  { name: 'D', library: 'Device', description: '二极管', footprint: 'Diode_SMD:D_SOD-123' },
  { name: 'LED', library: 'Device', description: 'LED', footprint: 'LED_SMD:LED_0603_1608Metric' },
  { name: 'D_Zener', library: 'Device', description: '稳压二极管', footprint: 'Diode_SMD:D_SOD-123' },
  { name: 'D_Schottky', library: 'Device', description: '肖特基二极管', footprint: 'Diode_SMD:D_SOD-123' },
  { name: 'D_Bridge', library: 'Device', description: '整流桥', footprint: 'Package_SO:SOIC-4_4.55x3.7mm_P2.54mm' },
  { name: 'PhotoDiode', library: 'Device', description: '光电二极管', footprint: 'Diode_THT:D_DO-41_SOD81_P7.62mm_Vertical_AnodeUp' },
  
  // 晶体管类
  { name: 'Q_NPN', library: 'Device', description: 'NPN 三极管', footprint: 'Package_TO_SOT_SMD:SOT-23' },
  { name: 'Q_PNP', library: 'Device', description: 'PNP 三极管', footprint: 'Package_TO_SOT_SMD:SOT-23' },
  { name: 'Q_NMOS', library: 'Device', description: 'N沟道 MOSFET', footprint: 'Package_TO_SOT_SMD:SOT-23' },
  { name: 'Q_PMOS', library: 'Device', description: 'P沟道 MOSFET', footprint: 'Package_TO_SOT_SMD:SOT-23' },
  { name: 'Q_NJFET', library: 'Device', description: 'N沟道 JFET', footprint: 'Package_TO_SOT_SMD:SOT-23' },
  
  // 集成电路类
  { name: 'U', library: 'Device', description: '集成电路', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm' },
  { name: 'Opamp', library: 'Amplifier_Operational', description: '运算放大器', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm' },
  { name: 'Regulator', library: 'Regulator_Linear', description: '稳压器', footprint: 'Package_TO_SOT_SMD:SOT-223-3' },
  { name: 'Timer', library: 'Timer', description: '定时器(555)', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm' },
  
  // 连接器类
  { name: 'J', library: 'Connector', description: '连接器', footprint: 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical' },
  { name: 'USB', library: 'Connector', description: 'USB接口', footprint: 'Connector_USB:USB_Micro-B_Molex-105017-0001' },
  { name: 'Audio', library: 'Connector', description: '音频接口', footprint: 'Connector_Audio:Jack_3.5mm_CUI_SJ-3523-SMT_Horizontal' },
  { name: 'DCJack', library: 'Connector', description: 'DC电源接口', footprint: 'Connector_BarrelJack:BarrelJack_Horizontal' },
  { name: 'HDMI', library: 'Connector', description: 'HDMI接口', footprint: 'Connector_HDMI:HDMI_A_Molex_208658-1001_Horizontal' },
  
  // 开关类
  { name: 'SW', library: 'Switch', description: '开关', footprint: 'Button_Switch_SMD:SW_SPST_B3U-3000' },
  { name: 'SW_Push', library: 'Switch', description: '按键开关', footprint: 'Button_Switch_THT:SW_PUSH_6mm' },
  { name: 'SW_DIP', library: 'Switch', description: 'DIP开关', footprint: 'Button_Switch_SMD:SW_DIP_SPSTx04_Slide_Omron_A6S' },
  { name: 'RotaryEncoder', library: 'Device', description: '旋转编码器', footprint: 'Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm' },
  
  // 晶振类
  { name: 'Y', library: 'Device', description: '晶振', footprint: 'Crystal_SMD:Crystal_SMD_3225-4Pin_3.2x2.5mm' },
  { name: 'Crystal', library: 'Device', description: '晶体振荡器', footprint: 'Crystal_SMD:Crystal_SMD_5032-2Pin_5.0x3.2mm' },
  { name: 'Oscillator', library: 'Oscillator', description: '有源晶振', footprint: 'Oscillator:Oscillator_DIP-8' },
  
  // 电源类
  { name: 'BT', library: 'Device', description: '电池', footprint: 'Battery:BatteryHolder_Keystone_3000_1x12mm' },
  { name: 'F', library: 'Device', description: '保险丝', footprint: 'Fuse:Fuse_1206_3216Metric' },
  { name: 'Power', library: 'power', description: '电源符号', footprint: '' },
  
  // 音频类
  { name: 'MIC', library: 'Device', description: '麦克风', footprint: 'Microphone:Microphone_CUI_CMI-9745J-10-A_Trumpet' },
  { name: 'Speaker', library: 'Device', description: '扬声器', footprint: 'Buzzer_Beeper:Buzzer_12x9.5RM7.6' },
  { name: 'Buzzer', library: 'Device', description: '蜂鸣器', footprint: 'Buzzer_Beeper:Buzzer_12x9.5RM7.6' },
  
  // 显示类
  { name: 'Display', library: 'Display', description: '显示器', footprint: 'Display:LCD_16x2' },
  { name: 'OLED', library: 'Display', description: 'OLED屏幕', footprint: 'Display_OLED:OLED_0.96inch_128x64' },
  
  // 传感器类
  { name: 'Sensor_Temp', library: 'Sensor_Temperature', description: '温度传感器', footprint: 'Sensor_Temperature:Temperature_TO-92_3Pin_Horizontal' },
  { name: 'Sensor_Humidity', library: 'Sensor', description: '湿度传感器', footprint: 'Sensor_Humidity:Digital_Humidity_Temperature_Sensortech_DHT11' },
  { name: 'Sensor_PIR', library: 'Sensor_Motion', description: 'PIR传感器', footprint: 'Sensor_Motion:PIR_HC-SR501' },
  { name: 'Sensor_Ultrasonic', library: 'Sensor_Distance', description: '超声波传感器', footprint: 'Sensor_Distance:HC-SR04' },
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
      symbol.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      symbol.library.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (selectedCategory === 'all') return matchesSearch
    if (selectedCategory === 'passive') {
      return matchesSearch && ['R', 'C', 'L', 'R_Potentiometer', 'R_Photo', 'Thermistor', 'Varistor', 'C_Polarized', 'C_Variable', 'CP', 'L_Ferrite', 'Transformer'].includes(symbol.name)
    }
    if (selectedCategory === 'active') {
      return matchesSearch && ['D', 'LED', 'D_Zener', 'D_Schottky', 'D_Bridge', 'PhotoDiode', 'Q_NPN', 'Q_PNP', 'Q_NMOS', 'Q_PMOS', 'Q_NJFET', 'U', 'Opamp', 'Regulator', 'Timer'].includes(symbol.name)
    }
    if (selectedCategory === 'mech') {
      return matchesSearch && ['J', 'USB', 'Audio', 'DCJack', 'HDMI', 'SW', 'SW_Push', 'SW_DIP', 'RotaryEncoder'].includes(symbol.name)
    }
    if (selectedCategory === 'crystal') {
      return matchesSearch && ['Y', 'Crystal', 'Oscillator'].includes(symbol.name)
    }
    if (selectedCategory === 'power') {
      return matchesSearch && ['BT', 'F', 'Power'].includes(symbol.name)
    }
    if (selectedCategory === 'audio') {
      return matchesSearch && ['MIC', 'Speaker', 'Buzzer'].includes(symbol.name)
    }
    if (selectedCategory === 'display') {
      return matchesSearch && ['Display', 'OLED'].includes(symbol.name)
    }
    if (selectedCategory === 'sensor') {
      return matchesSearch && ['Sensor_Temp', 'Sensor_Humidity', 'Sensor_PIR', 'Sensor_Ultrasonic'].includes(symbol.name)
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
