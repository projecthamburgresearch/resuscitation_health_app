#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = process.cwd();
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const ALGORITHMS_INDEX = path.join(ROOT, 'app', 'algorithms', 'index.json');
const REPORT_DIR = path.join(ROOT, 'appendix', 'guidance', 'warden', 'research', 'reports');
const REPORT_FILE = path.join(REPORT_DIR, 'behavior_report.json');

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
    const wheel = await page.locator('#wheel');
    const knob = await page.locator('#knob');

    // Helper to perform a drag on the knob
    const dragKnob = async (angleDeltaDeg) => {
      const knobBox = await knob.boundingBox();
      const wheelBox = await wheel.boundingBox();
      if (!knobBox || !wheelBox) throw new Error('Could not find knob or wheel box');

      const cx = wheelBox.x + wheelBox.width / 2;
      const cy = wheelBox.y + wheelBox.height / 2;

      // Start drag at knob center
      const startX = knobBox.x + knobBox.width / 2;
      const startY = knobBox.y + knobBox.height / 2;

      await page.mouse.move(startX, startY);
      await page.mouse.down();

      // current angle from center
      let currentAngle = Math.atan2(startY - cy, startX - cx);

      // move angle by delta
      const radDelta = angleDeltaDeg * (Math.PI / 180);
      const targetAngle = currentAngle + radDelta;

      const r = 150; // WHEEL_RADIUS
      const endX = cx + r * Math.cos(targetAngle);
      const endY = cy + r * Math.sin(targetAngle);

      await page.mouse.move(endX, endY, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(100);
    };

    // Forward gesture tests (anticlockwise in default wheel arc -> positive angleDelta? Actually CSS is different, but let's test)
    // We can evaluate state from window variable, but it's not exported. We can check class or id changes.
    // The active card title changes.
    const getActiveCardId = async () => {
      // We can inject a script to read state.currentId if we can reach it, but variables are let/const.
      // Instead we can read the DOM.
      return await page.evaluate(() => document.querySelector('.card-title')?.innerText || document.querySelector('.cover-title')?.innerText);
    };

    const isDecisionMode = async () => {
      return await page.evaluate(() => document.getElementById('zone-top').classList.contains('decision-mode'));
    };

    // Evaluate if history zone has cards
    const getHistoryCount = async () => {
      return await page.evaluate(() => document.querySelectorAll('.history-card').length);
    };

    let startCard = await getActiveCardId();
    console.log('  Start card is:', startCard);
    addStep('Identify start card', !!startCard, startCard);

    // Forward drag
    // Intent is anticlockwise. If we drag from angle -> angle - 30 deg it's anticlockwise math-wise. Let's drag up/left from 330 deg.
    // Negative mathematically is clockwise. Anticlockwise is negative angle delta in screen coords
    await dragKnob(-45); // This simulates an anticlockwise drag (forward)

    let nextCard = await getActiveCardId();
    console.log('  After dragKnob(-45), active card is:', nextCard);

    let movedForward = startCard !== nextCard;
    if (!movedForward) {
      console.log('  Did not move forward, trying +45');
      // let's try pushing it the other way just in case
      await dragKnob(45);
      nextCard = await getActiveCardId();
      console.log('  After dragKnob(+45), active card is:', nextCard);
      movedForward = startCard !== nextCard;
    }
    addStep('Forward intent advances 1 step', movedForward, `Card changed to ${nextCard}`);

    // Reverse drag
    const historyBeforeR = await getHistoryCount();
    await dragKnob(60); // Reverse
    let rewindCard = await getActiveCardId();
    const historyAfterR = await getHistoryCount();
    addStep('Reverse intent rewinds 1 step', rewindCard === startCard, `Card changed to ${rewindCard}`);

    // Advance until decision
    let maxIter = 10;
    let decisionReached = false;
    let forwardDragAmount = -45; // The one that worked

    while (maxIter > 0 && !(await isDecisionMode())) {
      await dragKnob(forwardDragAmount);
      maxIter--;
    }
    decisionReached = await isDecisionMode();
    addStep('Reached decision state', decisionReached);

    if (decisionReached) {
      let decisionCard = await getActiveCardId();

      // Try to forward drag through decision
      await dragKnob(forwardDragAmount);
      let afterDragDecision = await getActiveCardId();
      addStep('Decision state locks forward drag', decisionCard === afterDragDecision);

      // Confirm decision via drag to center
      const optionCardLocator = page.locator('.decision-option-card.selected');
      const ocBox = await optionCardLocator.boundingBox();
      if (ocBox) {
        // Drag to center (down by 100px)
        await page.mouse.move(ocBox.x + ocBox.width / 2, ocBox.y + ocBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(ocBox.x + ocBox.width / 2, ocBox.y + ocBox.height / 2 + 100, { steps: 5 });
        await page.mouse.up();
        await page.waitForTimeout(200);

        let postDecisionCard = await getActiveCardId();
        addStep('Drag-to-center advances decision', postDecisionCard !== decisionCard, `Card changed to ${postDecisionCard}`);

        // Ensure reverse can pass back through decision
        await dragKnob(-forwardDragAmount); // Reverse
        let afterRewindBack = await getActiveCardId();
        addStep('Reverse traversal past decision works', afterRewindBack === decisionCard);
      } else {
        addStep('Drag-to-center advances decision', false, 'Option card not found');
      }
    }

  } catch (err) {
    addStep('Execution error', false, err.message);
  }

  return testResults;
}

async function runBehaviorTests() {
  console.log('🚀 Starting Behavior Contract Validation...');
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
    console.error('❌ Behavior contract validation failed for one or more algorithms.');
    process.exit(1);
  }
}

runBehaviorTests().catch(err => {
  console.error(err);
  process.exit(1);
});
