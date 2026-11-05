// Visual smoke test for the generated, self-contained report.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('path');
const fs = require('fs');
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file:///'+path.resolve('reports/retail_observatory.html').replaceAll('\\','/'));
  await page.waitForFunction(()=>document.querySelectorAll('.js-plotly-plot').length>=10);
  await page.screenshot({path:'reports/report-preview.png',fullPage:false});
  const charts=await page.locator('.js-plotly-plot').count();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'artifacts/report-mobile.png',fullPage:false});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  const result={charts,javascript_errors:errors,mobile_page_overflow:overflow};
  fs.writeFileSync('reports/visual_qa.json',JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
  await browser.close();
  if(errors.length||overflow)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
