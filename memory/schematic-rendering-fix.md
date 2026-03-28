# 原理图渲染空白问题修复日志

## 问题描述
用户打开原理图标签页后，画布显示灰色空白，没有显示任何元件。

## 根本原因

### 1. Stage 变换影响所有子元素
**问题**：`Stage` 组件的 `scaleX/scaleY/x/y` 属性会应用到所有子元素，包括背景
- 背景 Layer 使用了这些变换，导致网格和背景位置错乱

**修复**：将变换移到内容 Layer 上，背景 Layer 保持固定
```tsx
// 修复前：Stage 上有变换
<Stage scaleX={zoom} scaleY={zoom} x={pan.x} y={pan.y}>
  <Layer>
    <Rect fill="#1a1a1a" />
    {generateGridLines()}
    {components}
  </Layer>
</Stage>

// 修复后：两层分离
<Stage>
  <Layer>
    <Rect fill="#1a1a1a" />
    {generateGridLines()}
  </Layer>
  <Layer x={pan.x} y={pan.y} scaleX={zoom} scaleY={zoom}>
    {components}
  </Layer>
</Stage>
```

### 2. React useEffect 循环依赖错误
**问题**：`handleAutoView` 在定义之前被 useEffect 引用，导致 "Cannot access 'handleAutoView' before initialization" 错误

**修复**：直接在 useEffect 内部计算视图，避免循环依赖
```tsx
// 修复前
useEffect(() => {
  handleAutoView(); // 循环依赖！
}, [handleAutoView]);

// 修复后
useEffect(() => {
  // 直接计算，不调用 handleAutoView
  const newPan = { x: width/2 - centerX, y: height/2 - centerY };
  setPan(newPan);
  setZoom(1);
}, [schematicData?.components?.length, width, height]);
```

### 3. 默认 props 可能为 undefined
**问题**：组件的默认宽高参数可能未生效，导致 Stage 尺寸为 0

**修复**：添加 defaultProps 并使用 Math.max 确保最小尺寸
```tsx
SchematicEditor.defaultProps = {
  width: 800,
  height: 500
};

// 在 updateSize 中
let newWidth = Math.max(rect.width, DEFAULT_WIDTH);
let newHeight = Math.max(rect.height, DEFAULT_HEIGHT);
```

## 测试结果
- ✅ 4 个项目全部测试通过
- ✅ 无 JavaScript 错误
- ✅ 元件正常显示（LED、电阻、IC、电容）
- ✅ 背景网格正常显示

## 关键文件修改
- `kicad-ai-auto/web/src/editors/SchematicEditor.tsx`
- `kicad-ai-auto/web/src/stores/schematicStore.ts`

## 经验总结
1. React Konva 的变换应该放在 Layer 上，而非 Stage
2. useEffect 依赖中避免使用刚定义的回调函数
3. 使用 Playwright 进行自动化测试验证修复
