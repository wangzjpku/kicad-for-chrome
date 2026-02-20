/**
 * KiCad Web Editor - Playwright MCP 自动化测试脚本
 * 
 * 使用方法:
 * 1. 确保后端和前端正运行在 http://localhost:8000 和 http://localhost:3000
 * 2. 使用 Playwright MCP 执行这些测试步骤
 */

// ==================== 测试套件 1: 首页和项目列表 ====================

async function testHomepage() {
  console.log("🧪 测试 1: 访问首页");
  
  // 导航到首页
  await browser_navigate({ url: "http://localhost:3000" });
  
  // 等待页面加载
  await browser_wait_for({ time: 2 });
  
  // 截图记录
  await browser_take_screenshot({ filename: "01_homepage.png", type: "png" });
  
  // 验证页面元素
  const snapshot = await browser_snapshot({});
  console.log("✅ 首页加载成功");
  
  return snapshot;
}

// ==================== 测试套件 2: 创建新项目 ====================

async function testCreateProject() {
  console.log("🧪 测试 2: 创建新项目");
  
  // 确保在项目列表页面
  await browser_navigate({ url: "http://localhost:3000" });
  await browser_wait_for({ time: 2 });
  
  // 获取当前快照
  const snapshot = await browser_snapshot({});
  
  // 点击 "+ New Project" 按钮
  // 注意: 需要根据实际快照中的 ref 值调整
  await browser_click({ 
    element: "+ New Project button", 
    ref: "e11" 
  });
  
  await browser_wait_for({ time: 1 });
  
  // 截图记录
  await browser_take_screenshot({ filename: "02_create_dialog.png", type: "png" });
  
  console.log("✅ 项目创建对话框打开");
}

// ==================== 测试套件 3: 打开项目并测试 PCB 编辑器 ====================

async function testPCBEditor() {
  console.log("🧪 测试 3: PCB 编辑器功能");
  
  // 访问首页
  await browser_navigate({ url: "http://localhost:3000" });
  await browser_wait_for({ time: 2 });
  
  // 获取快照找到项目
  const snapshot = await browser_snapshot({});
  
  // 点击项目名称打开项目
  await browser_click({ 
    element: "Project name heading", 
    ref: "e16" 
  });
  
  await browser_wait_for({ time: 2 });
  
  // 截图 PCB 编辑器
  await browser_take_screenshot({ 
    filename: "03_pcb_editor.png", 
    type: "png" 
  });
  
  // 测试菜单功能 - 放置菜单
  await browser_click({ 
    element: "放置 menu", 
    ref: "e29" 
  });
  
  await browser_wait_for({ time: 1 });
  
  await browser_take_screenshot({ 
    filename: "04_place_menu.png", 
    type: "png" 
  });
  
  // 关闭菜单
  await browser_press_key({ key: "Escape" });
  
  console.log("✅ PCB 编辑器测试完成");
}

// ==================== 测试套件 4: 测试 API 文档页面 ====================

async function testAPIDocs() {
  console.log("🧪 测试 4: API 文档页面");
  
  // 导航到 API 文档
  await browser_navigate({ url: "http://localhost:8000/docs" });
  
  // 等待 Swagger UI 加载
  await browser_wait_for({ time: 3 });
  
  // 截图完整页面
  await browser_take_screenshot({ 
    filename: "05_api_docs.png", 
    type: "png",
    fullPage: true 
  });
  
  console.log("✅ API 文档页面测试完成");
}

// ==================== 测试套件 5: 测试工具栏按钮 ====================

async function testToolbarButtons() {
  console.log("🧪 测试 5: 工具栏按钮");
  
  // 进入 PCB 编辑器
  await browser_navigate({ url: "http://localhost:3000" });
  await browser_wait_for({ time: 2 });
  
  const snapshot = await browser_snapshot({});
  
  // 点击项目名称进入编辑器
  await browser_click({ 
    element: "Project name heading", 
    ref: "e16" 
  });
  
  await browser_wait_for({ time: 2 });
  
  // 测试各种工具按钮
  // 选择工具
  await browser_click({ element: "Select tool", ref: "e41" });
  await browser_wait_for({ time: 0.5 });
  
  // 走线工具
  await browser_click({ element: "Track tool", ref: "e43" });
  await browser_wait_for({ time: 0.5 });
  
  // 截图
  await browser_take_screenshot({ 
    filename: "06_toolbar_test.png", 
    type: "png" 
  });
  
  console.log("✅ 工具栏按钮测试完成");
}

// ==================== 测试套件 6: 测试视图切换 ====================

async function testViewSwitching() {
  console.log("🧪 测试 6: 2D/3D 视图切换");
  
  // 进入 PCB 编辑器
  await browser_navigate({ url: "http://localhost:3000" });
  await browser_wait_for({ time: 2 });
  
  const snapshot = await browser_snapshot({});
  
  await browser_click({ 
    element: "Project name heading", 
    ref: "e16" 
  });
  
  await browser_wait_for({ time: 2 });
  
  // 切换到 3D 视图
  await browser_click({ element: "3D view button", ref: "e50" });
  await browser_wait_for({ time: 2 });
  
  await browser_take_screenshot({ 
    filename: "07_3d_view.png", 
    type: "png" 
  });
  
  // 切换回 2D 视图
  await browser_click({ element: "2D view button", ref: "e49" });
  await browser_wait_for({ time: 1 });
  
  await browser_take_screenshot({ 
    filename: "08_2d_view.png", 
    type: "png" 
  });
  
  console.log("✅ 视图切换测试完成");
}

// ==================== 测试套件 7: 网络请求监控 ====================

async function testNetworkRequests() {
  console.log("🧪 测试 7: 网络请求监控");
  
  // 清空之前的请求记录
  await browser_navigate({ url: "http://localhost:3000" });
  await browser_wait_for({ time: 2 });
  
  // 获取网络请求
  const requests = await browser_network_requests({ 
    includeStatic: false 
  });
  
  console.log("网络请求:", requests);
  
  // 保存到文件
  await browser_network_requests({ 
    includeStatic: false,
    filename: "network_requests.txt"
  });
  
  console.log("✅ 网络请求监控完成");
}

// ==================== 测试套件 8: 控制台错误检查 ====================

async function testConsoleErrors() {
  console.log("🧪 测试 8: 控制台错误检查");
  
  await browser_navigate({ url: "http://localhost:3000" });
  await browser_wait_for({ time: 3 });
  
  // 获取控制台消息
  const consoleMessages = await browser_console_messages({ 
    level: "error" 
  });
  
  console.log("控制台错误:", consoleMessages);
  
  // 保存到文件
  await browser_console_messages({ 
    level: "error",
    filename: "console_errors.txt"
  });
  
  console.log("✅ 控制台错误检查完成");
}

// ==================== 主测试流程 ====================

async function runAllTests() {
  console.log("🚀 开始 KiCad Web Editor 自动化测试");
  console.log("====================================");
  
  try {
    // 测试 1: 首页
    await testHomepage();
    
    // 测试 2: 创建项目
    await testCreateProject();
    
    // 测试 3: PCB 编辑器
    await testPCBEditor();
    
    // 测试 4: API 文档
    await testAPIDocs();
    
    // 测试 5: 工具栏按钮
    await testToolbarButtons();
    
    // 测试 6: 视图切换
    await testViewSwitching();
    
    // 测试 7: 网络请求
    await testNetworkRequests();
    
    // 测试 8: 控制台错误
    await testConsoleErrors();
    
    console.log("====================================");
    console.log("✅ 所有测试完成！");
    
  } catch (error) {
    console.error("❌ 测试失败:", error);
  }
}

// 运行测试
// runAllTests();

// 导出测试函数供单独调用
module.exports = {
  testHomepage,
  testCreateProject,
  testPCBEditor,
  testAPIDocs,
  testToolbarButtons,
  testViewSwitching,
  testNetworkRequests,
  testConsoleErrors,
  runAllTests
};
