#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = process.cwd();
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const ALGORITHMS_INDEX = path.join(ROOT, 'app', 'algorithms', 'index.json');
const REPORT_DIR = path.join(ROOT, 'appendix', 'guidance', 'warden', 'research', 'reports');
const REPORT_FILE = path.join(REPORT_DIR, 'keyboard_report.json');

async function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function testAlgorithm(page, algoFile, algoId) {
  console.log(`\nTesting algorithm: ${algoId} (${algoFile})`);
  const url = `${BASE_URL}/?algo=${encodeURIComponent(algoFile)}`;
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);

  const testResults = {
    id: algoId,
    file: algoFile,
    success: true,
    steps: []
  };

  const addStep = (name, result, message = '') => {
    testResults.steps.push({ name, result, message });
    if (!result) testResults.success = false;
    console.log(`  [${result ? 'PASS' : 'FAIL'}] ${name} ${message ? '- ' + message : ''}`);
  };

  try {
    const knob = await page.locator('#knob');
    // Focus the knob
    await knob.focus();

    const pressRight = async () => {
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(100);
    };

    const pressLeft = async () => {
        await page.keyboard.press('ArrowLeft');
        await page.waitForTimeout(100);
    };

    const getActiveCardId = async () => {
      return await page.evaluate(() => document.querySelector('.card-title')?.innerText || document.querySelector('.cover-title')?.innerText);
    };

    const isDecisionMode = async () => {
      return await page.evaluate(() => document.getElementById('zone-top').classList.contains('decision-mode'));
    };

    let startCard = await getActiveCardId();
    console.log('  Start card is:', startCard);
    addStep('Identify start card', !!startCard, startCard);

    // Forward (ArrowRight)
    await pressRight();

    let nextCard = await getActiveCardId();
    console.log('  After ArrowRight, active card is:', nextCard);

    let movedForward = startCard !== nextCard;
    addStep('Keyboard Forward advances 1 step', movedForward, `Card changed to ${nextCard}`);

    // Reverse (ArrowLeft)
    await pressLeft();
    let rewindCard = await getActiveCardId();
    addStep('Keyboard Reverse rewinds 1 step', rewindCard === startCard, `Card changed to ${rewindCard}`);

    // Advance until decision
    let maxIter = 10;
    let decisionReached = false;

    // Reset to forward state if we rewound
    if (rewindCard === startCard) {
         await pressRight();
    }

    while (maxIter > 0 && !(await isDecisionMode())) {
      await pressRight();
      maxIter--;
    }
    decisionReached = await isDecisionMode();
    addStep('Reached decision state', decisionReached);

    if (decisionReached) {
      let decisionCard = await getActiveCardId();

      // In decision mode, first ArrowRight should SELECT the first option (if not selected)
      // It should NOT advance yet.

      await pressRight(); // This should select Option 1
      let afterSelectDecision = await getActiveCardId();
      addStep('First ArrowRight selects option but stays on decision', decisionCard === afterSelectDecision);

      // Verify selection visual
      const isSelected = await page.locator('.decision-option-card.selected').count() > 0;
      addStep('Option is selected visually', isSelected);

      // Next ArrowRight should CONFIRM and ADVANCE
      await pressRight();
      let postDecisionCard = await getActiveCardId();
      addStep('Second ArrowRight confirms and advances', postDecisionCard !== decisionCard, `Card changed to ${postDecisionCard}`);

      // Reverse traversal
      await pressLeft();
      let afterRewindBack = await getActiveCardId();
      addStep('Reverse traversal past decision works', afterRewindBack === decisionCard);
    }

  } catch (err) {
    addStep('Execution error', false, err.message);
  }

  return testResults;
}

async function runBehaviorTests() {
  console.log('🚀 Starting Keyboard Navigation Validation...');
  let indexData;
  try {
    indexData = JSON.parse(fs.readFileSync(ALGORITHMS_INDEX, 'utf-8'));
  } catch (err) {
    console.error('Failed to read algorithms index:', err.message);
    process.exit(1);
  }

  const algorithms = indexData.algorithms || [];
  if (algorithms.length === 0) {
    console.error('No algorithms found to test.');
    process.exit(1);
  }

  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();

  const report = {
    timestamp: new Date().toISOString(),
    totalAlgorithms: algorithms.length,
    passedAlgorithms: 0,
    failedAlgorithms: 0,
    results: []
  };

  let allPass = true;

  for (const algo of algorithms) {
    const res = await testAlgorithm(page, algo.file, algo.id);
    report.results.push(res);
    if (res.success) {
      report.passedAlgorithms++;
    } else {
      report.failedAlgorithms++;
      allPass = false;
    }
  }

  await browser.close();

  await ensureDir(REPORT_DIR);
  fs.writeFileSync(REPORT_FILE, JSON.stringify(report, null, 2));

  console.log(`\n✅ Tests completed. Passed: ${report.passedAlgorithms}, Failed: ${report.failedAlgorithms}`);
  console.log(`Report written to ${REPORT_FILE}`);

  if (!allPass) {
    console.error('❌ Keyboard validation failed for one or more algorithms.');
    process.exit(1);
  }
}

runBehaviorTests().catch(err => {
  console.error(err);
  process.exit(1);
});
