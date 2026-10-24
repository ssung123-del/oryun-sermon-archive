// Optional end-to-end suite: npm install --no-save playwright && npx playwright install chromium webkit
const assert=require('node:assert/strict');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,webkit}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{
 const name=new URL(req.url,'http://localhost').pathname.endsWith('sermons.json')?'sermons.json':'index.html';
 res.setHeader('Content-Type',name.endsWith('.json')?'application/json; charset=utf-8':'text/html; charset=utf-8');res.end(fs.readFileSync(path.join(root,name)));
});
const artifacts=path.join(__dirname,'artifacts');fs.mkdirSync(artifacts,{recursive:true});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const url=`http://127.0.0.1:${server.address().port}`;let checks=0;
 try{for(const [name,type] of Object.entries({chromium,webkit})){
  const browser=await type.launch({headless:true});
  try{for(const width of [1440,390,320]){
   const context=await browser.newContext({viewport:{width,height:1000},acceptDownloads:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.clock.install();await page.goto(url);await page.waitForFunction(()=>document.querySelector('#rows').children.length>0);
   assert.equal(await page.locator('#rows tr').count(),30);checks++;
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`${name} ${width}px horizontal overflow`);checks++;
   if(width!==320)await page.screenshot({path:path.join(artifacts,`${name}-${width}.png`),fullPage:true});
   await page.locator('#search').fill('요 8:1-11');await page.clock.runFor(200);await page.waitForFunction(()=>document.querySelector('#search').value&&document.querySelector('#resultCount').textContent!=='—');
   assert.ok(await page.locator('#rows tr').count()>0);checks++;
   await page.locator('#testament').selectOption('NT');await page.locator('#book').selectOption('43');await page.locator('#chapter').fill('8');
   assert.ok(await page.locator('#rows tr').count()>0);checks++;
   await page.locator('#rows [data-compare]').first().click();await page.waitForSelector('dialog[open]');await page.locator('[name=compareMode][value=overlap]').check();assert.ok((await page.locator('#compareCount').textContent()).includes('겹치는'));await page.locator('#closeDialog').click();checks++;
   const downloadEvent=page.waitForEvent('download');await page.locator('#csv').click();const download=await downloadEvent;const csv=fs.readFileSync(await download.path());assert.deepEqual([...csv.subarray(0,3)],[239,187,191]);checks++;
   await page.locator('#dateFrom').fill('2026-10-23');await page.locator('#dateTo').fill('2020-01-01');assert.equal(await page.locator('#rangeError').isVisible(),true);checks++;
   await page.locator('#reset').click();await page.locator('#services button[data-service="수요예배"]').click();assert.ok(await page.locator('#rows tr').count()>0);checks++;
   await page.locator('#sort').selectOption('asc');await page.locator('#reset').click();await page.locator('#search').fill('아무결과도없어야합니다xyz');await page.clock.runFor(200);assert.equal(await page.locator('#rows tr').count(),0);assert.equal(await page.locator('#state').isVisible(),true);checks++;
   await page.locator('#reset').click();await page.locator('#next').click();assert.ok((await page.locator('#pageLabel').textContent()).startsWith('2 /'));checks++;
   const initialTotal=await page.locator('#totalCount').textContent();const original=JSON.parse(fs.readFileSync(path.join(root,'sermons.json'),'utf8'));
   const first=original.sermons.find(r=>r.reference.status==='ok');const added={...first,id:`${first.menu}:999999999`,tid:'999999999',title:'목록 다시 열기 테스트',source_url:`https://oryun.org/tv/?menu=${first.menu}&mode=view&tid=999999999`};
   original.sermons.unshift(added);original.meta.total++;original.meta.content_version='poll-test';original.meta.last_success_at='2026-10-25T12:00:00Z';
   await page.route('**/sermons.json?*',route=>route.fulfill({json:original}));await page.clock.runFor(300000);assert.equal(await page.locator('#totalCount').textContent(),initialTotal);checks++;await page.locator('#refresh').click();await page.waitForFunction(n=>document.querySelector('#totalCount').textContent!==n,initialTotal);
   assert.ok((await page.locator('#pageLabel').textContent()).startsWith('2 /'));checks++;
   await page.route('**/sermons.json?*',route=>route.fulfill({json:{schema_version:1,meta:{total:0},sermons:[{bad:true}]}}));await page.locator('#refresh').click();await page.waitForFunction(()=>document.querySelector('#notice').classList.contains('error'));assert.equal(await page.locator('#rows tr').count(),30);checks++;
   assert.deepEqual(errors,[]);checks++;await context.close();console.log(`PASS ${name} ${width}px`);
  }}finally{await browser.close();}
 }
 console.log(`Browser checks passed: ${checks}`);
 }finally{server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
