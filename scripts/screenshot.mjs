import { chromium } from 'playwright';

const url = process.argv[2] || 'http://localhost:4000';
const output = process.argv[3] || 'docs/images/dashboard-hero.png';

async function captureScreenshot() {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1280, height: 800 }
  });

  await page.goto(url, { waitUntil: 'networkidle' });

  // Wait for content to load
  await page.waitForTimeout(2000);

  await page.screenshot({
    path: output,
    fullPage: false
  });

  console.log(`Screenshot saved to ${output}`);
  await browser.close();
}

captureScreenshot().catch(console.error);
