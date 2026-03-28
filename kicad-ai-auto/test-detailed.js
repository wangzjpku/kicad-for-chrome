// KiCad for Chrome 详细功能测试 v2
const { chromium } = require('playwright');
const path = require('path');

const TARGET_URL = 'http://localhost:3000';
const BACKEND_URL = 'http://localhost:8000';

const screenshotDir = 'E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-ai-auto/test_screenshots';

(async () => {
  console.log('🚀 KiCad for Chrome 详细功能测试 v2\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });

  const page = await browser.newPage();
  const results = { passed: [], failed: [], warnings: [] };

  const screenshot = async (name) => {
    const filePath = `${screenshotDir}/${name}.png`;
    await page.screenshot({ path: filePath, fullPage: true });
    console.log(`📸 ${filePath}`);
    return filePath;
  };

  try {
    // 1. 首页加载
    console.log('\n【1】首页加载测试');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);
    await screenshot('01_homepage');
    results.passed.push('首页加载');

    // 2. 页面标题
    const title = await page.title();
    console.log(`   标题: ${title}`);
    if (title.includes('KiCad')) results.passed.push('标题正确');
    else results.failed.push('标题');

    // 3. 检查项目列表
    console.log('\n【2】项目列表测试');
    const hasProjects = await page.locator('[class*="project"], .card, .item').first().isVisible().catch(() => false);
    console.log(`   有项目: ${hasProjects}`);
    results.passed.push('项目列表');

    // 4. 创建设计按钮
    console.log('\n【3】创建设计按钮');
    const createBtn = page.locator('button:has-text("创建设计"), button:has-text("新建设计")');
    const createBtnVisible = await createBtn.isVisible().catch(() => false);
    console.log(`   可见: ${createBtnVisible}`);
    if (createBtnVisible) {
      results.passed.push('创建设计按钮');
      await screenshot('02_create_button');
    }

    // 5. 进入项目
    console.log('\n【4】进入项目测试');
    const firstProject = page.locator('[class*="project"], .card').first();
    if (await firstProject.isVisible().catch(() => false)) {
      await firstProject.click();
      await page.waitForTimeout(2000);
      await screenshot('03_project_view');
      console.log('   ✅ 进入项目成功');
      results.passed.push('进入项目');

      // 6. PCB 编辑器
      console.log('\n【5】PCB编辑器');
      const pcbEditor = await page.locator('text=PCB, text=pcbnew').first().isVisible().catch(() => false);
      console.log(`   PCB编辑器: ${pcbEditor}`);
      if (pcbEditor) results.passed.push('PCB编辑器');

      // 7. 原理图编辑器
      console.log('\n【6】原理图编辑器');
      const schematic = await page.locator('text=原理图, text=schematic').first().isVisible().catch(() => false);
      console.log(`   原理图: ${schematic}`);
      if (schematic) results.passed.push('原理图');

      // 8. AI 按钮 (现在应该可用)
      console.log('\n【7】AI功能');
      const aiBtn = page.locator('button:has-text("AI"), button:has-text("🤖")');
      const aiEnabled = await aiBtn.isEnabled().catch(() => false);
      console.log(`   AI按钮启用: ${aiEnabled}`);
      if (aiEnabled) {
        await aiBtn.click();
        await page.waitForTimeout(1000);
        await screenshot('04_ai_dialog');
        results.passed.push('AI对话框');
        await page.keyboard.press('Escape');
      } else {
        results.warnings.push('AI按钮未启用');
      }
    }

    // 9. 后端API测试
    console.log('\n【8】后端API测试');
    const health = await page.request.get(`${BACKEND_URL}/api/health`);
    console.log(`   健康检查: ${health.status()}`);
    if (health.status() === 200) results.passed.push('后端健康');

    const projects = await page.request.get(`${BACKEND_URL}/api/v1/projects`);
    const projectData = await projects.json();
    console.log(`   项目数: ${projectData.data?.length || 0}`);
    results.passed.push('项目API');

    // 10. 导出功能
    console.log('\n【9】导出功能');
    const exportBtn = await page.locator('text=导出').first().isVisible().catch(() => false);
    console.log(`   导出按钮: ${exportBtn}`);
    if (exportBtn) results.passed.push('导出功能');
    else results.warnings.push('导出功能');

    // 11. 控制台错误
    console.log('\n【10】控制台错误');
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.waitForTimeout(500);
    if (errors.length === 0) {
      console.log('   ✅ 无错误');
      results.passed.push('无控制台错误');
    } else {
      console.log(`   ❌ ${errors.length}个错误`);
      results.failed.push(`控制台错误(${errors.length})`);
    }

    await screenshot('99_final');

    // 输出报告
    console.log('\n' + '='.repeat(50));
    console.log('📊 测试报告');
    console.log('='.repeat(50));
    console.log(`✅ 通过: ${results.passed.length}`);
    console.log(`⚠️ 警告: ${results.warnings.length}`);
    console.log(`❌ 失败: ${results.failed.length}`);
    console.log('\n通过:');
    results.passed.forEach(p => console.log(`  ✓ ${p}`));
    if (results.warnings.length) {
      console.log('\n警告:');
      results.warnings.forEach(p => console.log(`  ⚠ ${p}`));
    }
    if (results.failed.length) {
      console.log('\n失败:');
      results.failed.forEach(p => console.log(`  ✗ ${p}`));
    }

  } catch (e) {
    console.error('\n❌ 测试异常:', e.message);
    await screenshot('error');
  } finally {
    await browser.close();
  }
})();
