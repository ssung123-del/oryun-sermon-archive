const assert=require('node:assert/strict');
const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {chromium,webkit}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),original=JSON.parse(fs.readFileSync(path.join(root,'sermons.json'),'utf8'));
const policyText='제1조 (약관의 목적과 동의) 테스트용 수집 정책 2022년 5월 10일 부터 시행 됩니다.';
const policyHash=crypto.createHash('sha256').update(JSON.stringify(policyText)).digest('hex');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8').replace("const TERMS_HASH='409fb91ce256dab3ea30c0bf2c79cb47ef0ff7efd42029fa7f39636691e8c5e5'",`const TERMS_HASH='${policyHash}'`);
const server=http.createServer((req,res)=>{res.setHeader('Content-Type',req.url.includes('sermons.json')?'application/json':'text/html; charset=utf-8');res.end(req.url.includes('sermons.json')?JSON.stringify(original):html);});
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
function listing(menu,rows,page,pages){return `<div class="PhotoList">${rows.map(r=>`<a href="/tv/?menu=${menu}&amp;mode=view&amp;tid=${r.tid}"><span class="cont tit">${esc(r.title)}</span><span class="cont text">${esc(r.reference_raw)} | ${esc(r.speaker)}</span><span class="cont date">${r.date}</span></a>`).join('')}</div><div class="paging"><span class="m_num"><input class="post_page" value="${page}"> / ${pages}</span></div>`;}
function detail(r){return `<div class="title_Box"><div class="date">[${r.date}]</div><div class="title" data="sns">${esc(r.title)}</div><div class="vname">${esc(r.speaker)} 목사</div></div><div class="list_Box"><div class="title"><span class="sky">본문말씀</span> : ${esc(r.reference_raw)}</div></div>`;}
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));let checks=0;
 try{for(const [name,type] of Object.entries({chromium,webkit})){
  const b=await type.launch({headless:true});try{
   const p=await b.newPage({viewport:{width:name==='webkit'?390:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.clock.install();
   let mode='ok',requests=0;const rows=new Map(Object.keys(original.meta.menus).map(k=>[Number(k),original.sermons.filter(r=>r.menu===Number(k)).map(r=>({...r}))]));
   rows.get(57).unshift({...rows.get(57)[0],tid:'999999999',title:'버튼으로 가져온 새 설교',date:'2026-10-25'});
   rows.get(58)[1].title='공식 제목 수정 테스트';
   await p.route('https://oryun.org/**',async route=>{
    requests++;const u=new URL(route.request().url());
    if(mode==='hold'){await new Promise(r=>setTimeout(r,200));return route.abort();}
    if(mode==='denied')return route.fulfill({status:403,body:'forbidden'});
    if(u.pathname==='/robots.txt')return route.fulfill({body:mode==='robots'?'User-agent: *\nDisallow: /tv/':'User-agent: *'});
    if(u.pathname==='/about/')return route.fulfill({contentType:'text/html',body:`<p>${mode==='terms'?policyText.replace('테스트용','변경된'):policyText}</p>`});
    const menu=Number(u.searchParams.get('menu')),list=rows.get(menu),page=Number(u.searchParams.get('page')||1);
    if(u.searchParams.has('tid'))return route.fulfill({contentType:'text/html',body:detail(list.find(r=>r.tid===u.searchParams.get('tid')))});
    if(mode==='structure')return route.fulfill({contentType:'text/html',body:'<html>점검 중</html>'});
    return route.fulfill({contentType:'text/html',body:listing(menu,list.slice((page-1)*16,page*16),page,mode==='drop'?1:original.meta.menus[String(menu)].total_pages)});
   });
   await p.goto(`http://127.0.0.1:${server.address().port}`);await p.waitForSelector('#rows tr');
   // Speed up intentional rate-limit sleeps in tests only; production default is 1.2 seconds.
   await p.evaluate(()=>{const collect=ArchiveCollector.collect;ArchiveCollector.collect=(data,options)=>collect(data,{...options,wait:async()=>{}});});
   assert.equal(requests,0);await p.clock.runFor(600000);assert.equal(requests,0);checks++;
   await p.locator('#search').fill('버튼으로 가져온');await p.clock.runFor(200);await p.locator('#crawl').click();await p.waitForFunction(()=>document.querySelector('#cancelCrawl').hidden);
   assert.equal(await p.locator('#totalCount').textContent(),'1,371');assert.equal(await p.locator('#rows tr').count(),1);assert.match(await p.locator('#notice').textContent(),/새 항목 1건 · 수정 1건/);checks+=3;
   const cache=await p.evaluate(()=>JSON.parse(localStorage.getItem('oryun-sermon-archive:manual:v1')));assert.equal(cache.meta.total,1459);checks++;
   const python=path.join(root,'.venv/bin/python');const verified=spawnSync(python,['-c','import sys,json;from scraper import validate_archive;validate_archive(json.load(sys.stdin))'],{cwd:root,input:JSON.stringify(cache),encoding:'utf8'});assert.equal(verified.status,0,verified.stderr);checks++;
   await p.reload();await p.waitForSelector('#rows tr');assert.equal(await p.locator('#totalCount').textContent(),'1,371');assert.match(await p.locator('#scopeNote').textContent(),/브라우저에 저장/);checks+=2;
   await p.evaluate(()=>{const collect=ArchiveCollector.collect;ArchiveCollector.collect=(data,options)=>collect(data,{...options,wait:async()=>{}});});
   const before=await p.evaluate(()=>localStorage.getItem('oryun-sermon-archive:manual:v1'));
   for(mode of ['denied','robots','terms','structure','drop']){await p.locator('#crawl').click();await p.waitForFunction(()=>document.querySelector('#cancelCrawl').hidden);assert.match(await p.locator('#notice').textContent(),/기존 목록/);assert.equal(await p.evaluate(()=>localStorage.getItem('oryun-sermon-archive:manual:v1')),before);checks+=2;}
   mode='hold';await p.locator('#crawl').click();await p.locator('#cancelCrawl').click();await p.waitForFunction(()=>document.querySelector('#cancelCrawl').hidden);assert.match(await p.locator('#notice').textContent(),/취소/);assert.equal(await p.evaluate(()=>localStorage.getItem('oryun-sermon-archive:manual:v1')),before);checks+=2;
   mode='ok';await p.locator('#fullScan').check();await p.locator('#crawl').click();await p.waitForFunction(()=>document.querySelector('#cancelCrawl').hidden);
   const full=await p.evaluate(()=>JSON.parse(localStorage.getItem('oryun-sermon-archive:manual:v1')));assert.equal(full.meta.mode,'browser-full');assert.equal(full.meta.menus['58'].checked_pages.length,40);checks+=2;
   const fullBytes=await p.evaluate(()=>localStorage.getItem('oryun-sermon-archive:manual:v1'));await p.locator('#fullScan').uncheck();
   await p.evaluate(()=>Storage.prototype.setItem=function(){throw new DOMException('full','QuotaExceededError');});await p.locator('#crawl').click();await p.waitForFunction(()=>document.querySelector('#cancelCrawl').hidden);
   assert.match(await p.locator('#notice').textContent(),/저장하지 못했습니다/);assert.match(await p.locator('#scopeNote').textContent(),/이번 방문/);assert.equal(await p.evaluate(()=>localStorage.getItem('oryun-sermon-archive:manual:v1')),fullBytes);checks+=3;
   const policies=await p.evaluate(()=>{
    const x=ArchiveCollector.robotsPolicy('User-agent: *\nDisallow: /tv/\nAllow: /tv/?menu=57\nCrawl-delay: 3');
    const y=ArchiveCollector.robotsPolicy('User-agent: *\nDisallow: /tv/*mode=view$');
    return [x.allows('https://oryun.org/tv/?menu=57'),x.allows('https://oryun.org/tv/?menu=58'),x.delay,y.allows('https://oryun.org/tv/?menu=57&mode=view'),y.allows('https://oryun.org/tv/?menu=57&page=1')];
   });assert.deepEqual(policies,[true,false,3,false,true]);checks++;
   for(const menu of [57,58,59,61,62]){
    const fixture=fs.readFileSync(path.join(root,`tests/fixtures/list-${menu}.html`),'utf8');const actual=await p.evaluate(async({fixture,menu})=>ArchiveCollector.parseListing(fixture,menu),{fixture,menu});
    const expected=spawnSync(python,['-c',`import json,sys;from scraper import parse_listing;print(json.dumps(parse_listing(sys.stdin.read(),${menu})[0],ensure_ascii=False))`],{cwd:root,input:fixture,encoding:'utf8'});assert.equal(expected.status,0,expected.stderr);assert.deepEqual(actual.records,JSON.parse(expected.stdout));checks++;
   }
   assert.deepEqual(errors,[]);assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks+=2;
   console.log(`PASS ${name}: manual crawl, cache, cancellation, policies, parse parity, no polling`);
  }finally{await b.close();}
 }
 console.log(`Manual browser checks passed: ${checks}`);
 }finally{server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
