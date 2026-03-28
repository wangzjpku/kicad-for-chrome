// KiCad for Chrome 完整功能测试
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3000';
const BACKEND_URL = 'http://localhost:8000';

(async () => {
  console.log('🚀 开始 KiCad for Chrome 完整功能测试\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 100,
    defaultViewport: { width: 1920, height: 1080 }
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // 收集控制台错误
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  const results = {
    passed: [],
    failed: []
  };

  const takeScreenshot = async (name) => {
    const path = `/tmp/kicad-test-${name}-${Date.now()}.png`;
    await page.screenshot({ path, fullPage: true });
    console.log(`📸 截图: ${path}`);
    return path;
  };

  try {
    // ===== 测试 1: 首页加载 =====
    console.log('\n📋 测试 1: 首页加载');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot('01-homepage');
    console.log('✅ 首页加载成功');

    // ===== 测试 2: 检查页面标题 =====
    console.log('\n📋 测试 2: 页面标题');
    const title = await page.title();
    console.log(`   标题: ${title}`);
    results.passed.push('页面标题');

    // ===== 测试 3: 项目列表存在 =====
    console.log('\n📋 测试 3: 项目列表');
    const projectList = await page.locator('text=项目').first().isVisible().catch(() => false);
    console.log(`   项目列表可见: ${projectList}`);
    if (projectList) results.passed.push('项目列表');
    else results.failed.push('项目列表');

    // ===== 测试 4: 创建设计按钮 =====
    console.log('\n📋 测试 4: 创建设计按钮');
    const createBtn = await page.locator('text=创建设计').first().isVisible().catch(() => false);
    console.log(`   创建设计按钮可见: ${createBtn}`);
    if (createBtn) {
      results.passed.push('创建设计按钮');
      await takeScreenshot('02-create-button');
    } else {
      results.failed.push('创建设计按钮');
    }

    // ===== 测试 5: AI 对话框 =====
    console.log('\n📋 测试 5: AI 对话框功能');
    const aiDialogBtn = await page.locator('text=AI').first().isVisible().catch(() => false);
    if (aiDialogBtn) {
      await page.locator('text=AI').first().click();
      await page.waitForTimeout(1000);
      await takeScreenshot('03-ai-dialog');
      console.log('✅ AI 对话框打开成功');
      results.passed.push('AI 对话框');

      // 关闭对话框
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    } else {
      console.log('⚠️ AI 按钮未找到');
      results.failed.push('AI 对话框');
    }

    // ===== 测试 6: PCB 编辑器入口 =====
    console.log('\n📋 测试 6: PCB 编辑器入口');
    // 点击第一个项目进入
    const projectItems = await page.locator('[class*="card"], [class*="project"]').all();
    if (projectItems.length > 0) {
      await projectItems[0].click();
      await page.waitForTimeout(2000);
      await takeScreenshot('04-pcb-editor');
      console.log('✅ 进入项目/PCB编辑器');
      results.passed.push('PCB编辑器入口');
    } else {
      console.log('⚠️ 没有项目可点击');
      results.failed.push('PCB编辑器入口');
    }

    // ===== 测试 7: 工具栏 =====
    console.log('\n📋 测试 7: 工具栏');
    const toolbar = await page.locator('[class*="tool"], [class*="bar"]').first().isVisible().catch(() => false);
    console.log(`   工具栏可见: ${toolbar}`);
    if (toolbar) results.passed.push('工具栏');
    else results.failed.push('工具栏');

    // ===== 测试 8: 后端健康检查 =====
    console.log('\n📋 测试 8: 后端 API 健康检查');
    const healthResponse = await page.request.get(`${BACKEND_URL}/api/health`);
    console.log(`   健康检查状态: ${healthResponse.status()}`);
    if (healthResponse.status() === 200) {
      results.passed.push('后端健康检查');
    } else {
      results.failed.push('后端健康检查');
    }

    // ===== 测试 9: 项目列表 API =====
    console.log('\n📋 测试 9: 项目列表 API');
    const projectsResponse = await page.request.get(`${BACKEND_URL}/api/v1/projects`);
    const projectsData = await projectsResponse.json();
    console.log(`   项目数量: ${projectsData.data?.length || 0}`);
    if (projectsResponse.status() === 200) {
      results.passed.push('项目列表API');
    } else {
      results.failed.push('项目列表API');
    }

    // ===== 测试 10: 导出功能入口 =====
    console.log('\n📋 测试 10: 导出功能');
    // 尝试找到导出菜单
    const exportMenu = await page.locator('text=导出').first().isVisible().catch(() => false);
    console.log(`   导出菜单可见: ${exportMenu}`);
    if (exportMenu) results.passed.push('导出功能');
    else results.failed.push('导出功能');

    // ===== 测试 11: 控制台错误检查 =====
    console.log('\n📋 测试 11: 控制台错误');
    if (consoleErrors.length > 0) {
      console.log(`   ❌ 发现 ${consoleErrors.length} 个错误:`);
      consoleErrors.forEach(err => console.log(`      - ${err}`));
      results.failed.push(`控制台错误(${consoleErrors.length}个)`);
    } else {
      console.log('   ✅ 无控制台错误');
      results.passed.push('无控制台错误');
    }

    // ===== 最终报告 =====
    console.log('\n' + '='.repeat(50));
    console.log('📊 测试结果汇总');
    console.log('='.repeat(50));
    console.log(`✅ 通过: ${results.passed.length}`);
    console.log(`❌ 失败: ${results.failed.length}`);
    console.log('\n通过的项目:');
    results.passed.forEach(p => console.log(`  ✓ ${p}`));
    if (results.failed.length > 0) {
      console.log('\n失败的项目:');
      results.failed.forEach(p => console.log(`  ✗ ${p}`));
    }

    await takeScreenshot('99-final');

  } catch (error) {
    console.error('\n❌ 测试过程出错:', error.message);
    await takeScreenshot('error');
  } finally {
    await browser.close();
    console.log('\n👋 浏览器已关闭');
  }
})();
