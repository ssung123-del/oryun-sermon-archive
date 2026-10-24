const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const root=path.join(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
vm.runInThisContext(html.match(/<script id="archive-core">([\s\S]*?)<\/script>/)[1]);
const A=globalThis.Archive;
function row(id,raw='요 8:1-11',extra={}){return {id:`58:${id}`,menu:58,tid:String(id),date:'2026-10-21',title:'은혜의 말씀',speaker:'홍길동',service:'수요예배',reference_raw:raw,reference:A.normalize(raw),source_url:`https://oryun.org/tv/?menu=58&mode=view&tid=${id}`,first_collected_at:'2026-10-21T00:00:00Z',updated_at:'2026-10-21T00:00:00Z',...extra};}
const records=A.index([row(1),row(2,'요한복음 8:1-20',{date:'2026-10-22',speaker:'김목사'}),row(3,'요 8:1-3,5-11'),row(4,'창 1:1-5',{service:'주일예배',date:'2020-01-01'}),row(5,'미상')]);

test('66 books, aliases, chapter boundaries',()=>{
 assert.equal(A.BOOKS.length,66);assert.equal(A.BOOKS.filter(b=>b.testament==='NT').length,27);
 for(const b of A.BOOKS)for(const a of b.aliases)assert.equal(A.normalize(`${a}1:1`).key,A.normalize(`${b.name} 1:1`).key);
 assert.equal(A.normalize('요 8장-9장').status,'ok');
 for(const ref of ['요8:1,','요8:0','요99:1','요8:100','요8:3-1','요8:1 이하','요8:1; 모름1:1'])assert.equal(A.normalize(ref).status,'failed',ref);
});
test('same union differs from overlap, holes remain holes',()=>{
 assert.equal(A.normalize('요한복음8:1~11').key,A.normalize('요8:1-3,4-11').key);
 assert.notEqual(records[0].reference.key,records[1].reference.key);assert.ok(A.overlaps(records[0].reference,records[1].reference));
 assert.equal(A.overlaps(records[2].reference,A.normalize('요8:4')),false);
 assert.equal(A.normalize('요8').key,A.normalize('요8:1-59').key);
 assert.equal(A.normalize('요 7:52-8:11; 롬1:1').ranges.length,3);
});
test('combined filters, date inclusivity, ascending and default order',()=>{
 assert.equal(A.filter(records,{query:'홍길동',book:'43',chapter:'8',testament:'NT',service:'수요예배',from:'2026-10-21',to:'2026-10-21'}).length,2);
 assert.equal(A.filter(records,{query:'요 8:4'}).length,2);
 assert.equal(A.filter(records,{query:'미상'}).length,1);
 assert.equal(A.filter(records,{testament:'OT'}).length,1);
 assert.equal(A.filter(records,{query:'요한복음'}).length,3);
 assert.equal(A.filter(records,{from:'2026-12-01',to:'2020-01-01'}).length,0);
 assert.equal(A.filter(records,{})[0].tid,'2');
 assert.equal(A.filter(records,{sort:'asc'})[0].tid,'4');
 assert.equal(A.filter(records,{query:'홍길동 말씀'}).length,4);
});
test('CSV Excel UTF-8 BOM, CRLF, escaping and formula neutralization',()=>{
 const csv=A.csv([row(1,'요 8:1-11',{title:'=HYPERLINK("bad")',speaker:'홍,길동'})]);
 assert.deepEqual([...Buffer.from(csv).subarray(0,3)],[239,187,191]);
 assert.ok(csv.includes('"\'=HYPERLINK(""bad"")"'));assert.ok(csv.includes('"홍,길동"'));assert.ok(csv.endsWith('\r\n'));
});
test('invalid data is rejected before replacing the UI',()=>{
 const d={schema_version:1,meta:{total:1,last_success_at:'2026-10-21T00:00:00Z'},sermons:[row(1)]};assert.equal(A.validate(d),d);
 for(const bad of [{...d,meta:{...d.meta,total:2}},{...d,sermons:[{...row(1),source_url:'javascript:alert(1)'}]},{...d,sermons:[{...row(1),reference:{status:'ok',key:'bad',ranges:[]}}]}])assert.throws(()=>A.validate(bad));
});
test('Python and JavaScript normalize all archived and edge references identically',()=>{
 const archive=JSON.parse(fs.readFileSync(path.join(root,'sermons.json'),'utf8'));
 const refs=[...new Set([...archive.sermons.map(r=>r.reference_raw),'요8:1,','요8장-9장','요 8장 1절-11절','요8:1-3,5,7-11;롬1:1','요7:52-8:11','아무개1:1',...A.BOOKS.flatMap(b=>b.aliases.map(a=>a+' 1:1'))])];
 const python=process.env.PYTHON||(fs.existsSync(path.join(root,'.venv/bin/python'))?path.join(root,'.venv/bin/python'):'python');
 const p=spawnSync(python,['-c','import json,sys;from scraper import normalize_reference;print(json.dumps([normalize_reference(x) for x in json.load(sys.stdin)],ensure_ascii=False))'],{cwd:root,input:JSON.stringify(refs),encoding:'utf8'});
 assert.equal(p.status,0,p.stderr);const expected=JSON.parse(p.stdout);
 refs.forEach((raw,i)=>assert.deepEqual(A.normalize(raw),expected[i],raw));
 A.validate(archive);
});
test('50,000 records use precomputed index and bounded result rendering',()=>{
 const many=A.index(Array.from({length:50000},(_,i)=>row(i,i%2?'요8:1-11':'롬1:1')));
 const start=performance.now();const found=A.filter(many,{query:'요8:4',service:'수요예배'});const elapsed=performance.now()-start;
 assert.equal(found.length,25000);assert.ok(elapsed<3000,`search took ${elapsed.toFixed(1)}ms`);
 console.log(`50,000-record filter: ${elapsed.toFixed(1)}ms`);
});
test('shared tid is one sermon with all category filters and one CSV row',()=>{
 const shared=A.index([row(1),row(1,'요 8:1-11',{id:'62:1',menu:62,service:'외부강사',source_url:'https://oryun.org/tv/?menu=62&mode=view&tid=1'})]);
 assert.equal(shared.length,1);assert.equal(shared[0].services.length,2);
 assert.equal(A.filter(shared,{service:'외부강사'}).length,1);
 assert.equal(A.csv(shared).split('\r\n').length,3);
 assert.throws(()=>A.index([row(1),row(1,'요 8:1-20',{id:'62:1',menu:62,service:'외부강사'})]));
});
