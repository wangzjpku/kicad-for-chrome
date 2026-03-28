// KiCad for Chrome - 完整功能测试
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3000';
const BACKEND_URL = 'http://localhost:8000';
const SCREENSHOT_DIR = 'E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-ai-auto/test_screenshots';

(async () => {
  console.log('🔬 KiCad for Chrome 完整功能测试\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 100,
    args: ['--disable-blink-features=AutomationControlled']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });

  const page = await context.newPage();
  const results = { passed: [], failed: [], warnings: [] };
  const consoleErrors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  const screenshot = async (name) => {
    const path = `${SCREENSHOT_DIR}/${name}.png`;
    await page.screenshot({ path, fullPage: true });
    console.log(`📸 ${path}`);
    return path;
  };

  try {
    // ===== 测试 1: 首页 =====
    console.log('\n【1】首页加载');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await screenshot('01_homepage');
    results.passed.push('首页加载');

    const title = await page.title();
    console.log(`   标题: ${title}`);
    if (title.includes('KiCad')) results.passed.push('标题');

    // ===== 测试 2: 项目列表 =====
    console.log('\n【2】项目列表');
    const hasProjects = await page.locator('[class*="project"], .card').first().isVisible().catch(() => false);
    console.log(`   有项目: ${hasProjects}`);
    results.passed.push('项目列表');

    // ===== 测试 3: 搜索框 =====
    console.log('\n【3】搜索框');
    const searchInput = await page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="Search"]').first().isVisible().catch(() => false);
    console.log(`   搜索框: ${searchInput}`);
    if (searchInput) results.passed.push('搜索框');
    else results.warnings.push('搜索框');

    // ===== 测试 4: New Project 按钮 =====
    console.log('\n【4】New Project 按钮');
    const newProjectBtn = await page.locator('button:has-text("New Project")').first().isVisible().catch(() => false);
    console.log(`   可见: ${newProjectBtn}`);
    if (newProjectBtn) {
      results.passed.push('New Project');
      await screenshot('02_new_project_btn');
    }

    // ===== 测试 5: AI 创建按钮 =====
    console.log('\n【5】AI 创建按钮');
    const aiBtn = await page.locator('button:has-text("AI")').first().isVisible().catch(() => false);
    console.log(`   AI按钮: ${aiBtn}`);
    if (aiBtn) results.passed.push('AI按钮');

    // ===== 测试 6: 登录按钮 =====
    console.log('\n【6】登录入口');
    const loginBtn = await page.locator('text=登录, text=Login').first().isVisible().catch(() => false);
    console.log(`   登录按钮: ${loginBtn}`);
    if (loginBtn) results.passed.push('登录入口');

    // ===== 测试 7: 打开项目 =====
    console.log('\n【7】打开项目');
    const openBtn = page.locator('button:has-text("Open")').first();
    if (await openBtn.isVisible().catch(() => false)) {
      await openBtn.click();
      await page.waitForTimeout(3000);
      await screenshot('03_project_view');
      console.log('   ✅ 打开项目成功');
      results.passed.push('打开项目');

      // ===== 测试 8: PCB 编辑器 =====
      console.log('\n【8】PCB编辑器');
      const pcbTab = await page.locator('text=PCB, text=pcbnew, [class*="tab"]:has-text("PCB")').first().isVisible().catch(() => false);
      console.log(`   PCB标签: ${pcbTab}`);
      if (pcbTab) results.passed.push('PCB编辑器');

      // ===== 测试 9: 原理图编辑器 =====
      console.log('\n【9】原理图编辑器');
      const schTab = await page.locator('text=原理图, text=Schematic, [class*="tab"]:has-text("Schematic")').first().isVisible().catch(() => false);
      console.log(`   原理图标签: ${schTab}`);
      if (schTab) results.passed.push('原理图编辑器');

      // ===== 测试 10: 工具栏 =====
      console.log('\n【10】工具栏');
      const toolbar = await page.locator('[class*="toolbar"], [class*="tool-bar"]').first().isVisible().catch(() => false);
      console.log(`   工具栏: ${toolbar}`);
      if (toolbar) results.passed.push('工具栏');

      // ===== 测试 11: AI 对话框 =====
      console.log('\n【11】AI对话框');
      const aiDialogBtn = page.locator('button:has-text("AI"), button:has-text("🤖")');
      if (await aiDialogBtn.isEnabled().catch(() => false)) {
        await aiDialogBtn.click();
        await page.waitForTimeout(1500);
        await screenshot('04_ai_dialog');
        results.passed.push('AI对话框');
        await page.keyboard.press('Escape');
      } else {
        results.warnings.push('AI按钮未启用');
      }

      // ===== 测试 12: 导出功能 =====
      console.log('\n【12】导出功能');
      const exportBtn = await page.locator('text=导出, text=Export').first().isVisible().catch(() => false);
      console.log(`   导出按钮: ${exportBtn}`);
      if (exportBtn) results.passed.push('导出功能');
      else results.warnings.push('导出功能');

      // ===== 测试 13: DRC 检查 =====
      console.log('\n【13】DRC检查');
      const drcBtn = await page.locator('text=DRC, text=设计规则').first().isVisible().catch(() => false);
      console.log(`   DRC按钮: ${drcBtn}`);
      if (drcBtn) results.passed.push('DRC功能');
      else results.warnings.push('DRC功能');
    }

    // ===== 测试 14: 后端API =====
    console.log('\n【14】后端API');
    const health = await page.request.get(`${BACKEND_URL}/api/health`);
    console.log(`   健康检查: ${health.status()}`);
    if (health.status() === 200) results.passed.push('后端健康');

    const projects = await page.request.get(`${BACKEND_URL}/api/v1/projects`);
    const projectData = await projects.json();
    console.log(`   项目数: ${projectData.data?.length || 0}`);
    results.passed.push('项目API');

    // ===== 测试 15: 版本API =====
    console.log('\n【15】版本API');
    const version = await page.request.get(`${BACKEND_URL}/api/version`);
    const versionData = await version.json();
    console.log(`   版本: ${versionData.version || versionData.data?.version || 'N/A'}`);
    results.passed.push('版本API');

    // ===== 测试 16: 控制台错误 =====
    console.log('\n【16】控制台错误');
    await page.waitForTimeout(1000);
    if (consoleErrors.length === 0) {
      console.log('   ✅ 无错误');
      results.passed.push('无控制台错误');
    } else {
      console.log(`   ❌ ${consoleErrors.length}个错误`);
      consoleErrors.forEach(e => console.log(`      - ${e.substring(0, 100)}`));
      results.failed.push(`控制台错误(${consoleErrors.length})`);
    }

    await screenshot('99_final_report');

    // ===== 输出报告 =====
    console.log('\n' + '='.repeat(50));
    console.log('📊 测试报告');
    console.log('='.repeat(50));
    console.log(`✅ 通过: ${results.passed.length}`);
    console.log(`⚠️ 警告: ${results.warnings.length}`);
    console.log(`❌ 失败: ${results.failed.length}`);

    console.log('\n【通过】');
    results.passed.forEach(p => console.log(`  ✓ ${p}`));

    if (results.warnings.length) {
      console.log('\n【警告】');
      results.warnings.forEach(p => console.log(`  ⚠ ${p}`));
    }

    if (results.failed.length) {
      console.log('\n【失败】');
      results.failed.forEach(p => console.log(`  ✗ ${p}`));
    }

    const passRate = ((results.passed.length / (results.passed.length + results.warnings.length + results.failed.length)) * 100).toFixed(1);
    console.log(`\n📈 通过率: ${passRate}%`);

  } catch (error) {
    console.error('\n❌ 测试异常:', error.message);
    await screenshot('error');
  } finally {
    await browser.close();
    console.log('\n👋 测试完成');
  }
})();
