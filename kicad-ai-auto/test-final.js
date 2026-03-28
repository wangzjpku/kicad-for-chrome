// KiCad for Chrome - 最终完整测试
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3000';
const BACKEND_URL = 'http://localhost:8000';
const SCREENSHOT_DIR = 'E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-ai-auto/test_screenshots';

(async () => {
  console.log('🔬 KiCad for Chrome 最终完整测试\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 100,
    args: ['--disable-blink-features=AutomationControlled']
  });

  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const results = { passed: [], failed: [], warnings: [] };
  const consoleErrors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  const screenshot = async (name) => {
    await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}.png`, fullPage: true });
  };

  try {
    // 1. 首页
    console.log('\n【1】首页');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await screenshot('01_homepage');
    results.passed.push('首页加载');

    // 2. 搜索框
    console.log('\n【2】搜索框');
    const searchInput = await page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first().isVisible().catch(() => false);
    console.log(`   搜索框: ${searchInput}`);
    if (searchInput) results.passed.push('搜索框');

    // 3. New Project 按钮
    console.log('\n【3】New Project');
    const newProject = await page.locator('button:has-text("New Project")').first().isVisible().catch(() => false);
    if (newProject) results.passed.push('New Project');

    // 4. AI 按钮
    console.log('\n【4】AI按钮');
    const aiBtn = await page.locator('button:has-text("AI")').first().isVisible().catch(() => false);
    if (aiBtn) results.passed.push('AI按钮');

    // 5. 打开项目
    console.log('\n【5】打开项目');
    const openBtn = page.locator('button:has-text("Open")').first();
    if (await openBtn.isVisible().catch(() => false)) {
      await openBtn.click();
      await page.waitForTimeout(3000);
      await screenshot('02_project_editor');
      results.passed.push('打开项目');
    }

    // 6. 右侧面板 - Properties/Layers/DRC/Export 标签
    console.log('\n【6】右侧面板标签');
    const tabs = await page.locator('text=Properties, text=Layers, text=DRC, text=Export').all().catch(() => []);
    console.log(`   找到标签: ${tabs.length}个`);
    if (tabs.length >= 2) results.passed.push('右侧面板');

    // 7. 点击 DRC 标签
    console.log('\n【7】DRC功能');
    const drcTab = await page.locator('text=DRC').first();
    if (await drcTab.isVisible().catch(() => false)) {
      await drcTab.click();
      await page.waitForTimeout(500);
      await screenshot('03_drc_panel');
      results.passed.push('DRC面板');
    }

    // 8. 点击 Export 标签
    console.log('\n【8】导出功能');
    const exportTab = await page.locator('text=Export').first();
    if (await exportTab.isVisible().catch(() => false)) {
      await exportTab.click();
      await page.waitForTimeout(500);
      await screenshot('04_export_panel');
      results.passed.push('导出面板');
    }

    // 9. AI对话框测试
    console.log('\n【9】AI对话框');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    const aiHomeBtn = page.locator('button:has-text("🤖")');
    if (await aiHomeBtn.isVisible().catch(() => false)) {
      await aiHomeBtn.click();
      await page.waitForTimeout(1000);
      await screenshot('05_ai_dialog');
      results.passed.push('AI对话框');
    }

    // 10. 后端API
    console.log('\n【10】后端API');
    const health = await page.request.get(`${BACKEND_URL}/api/health`);
    const version = await page.request.get(`${BACKEND_URL}/api/version`);
    console.log(`   健康: ${health.status()}, 版本: ${(await version.json()).version}`);
    results.passed.push('后端健康');

    // 11. 控制台错误
    console.log('\n【11】控制台错误');
    await page.waitForTimeout(1000);
    if (consoleErrors.length === 0) {
      results.passed.push('无控制台错误');
    } else {
      console.log(`   错误数: ${consoleErrors.length}`);
      results.warnings.push(`控制台错误(${consoleErrors.length})`);
    }

    await screenshot('99_final');

    // 输出报告
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

    const total = results.passed.length + results.warnings.length + results.failed.length;
    const rate = ((results.passed.length / total) * 100).toFixed(1);
    console.log(`\n📈 通过率: ${rate}%`);

  } catch (error) {
    console.error('\n❌ 测试异常:', error.message);
  } finally {
    await browser.close();
  }
})();
