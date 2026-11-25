#!/usr/bin/env python3
"""Collect aggregate-safe funeral notice metadata; never persist names or bodies."""
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('oryun_source',ROOT/'scraper.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
URL='https://oryun.org/life/?menu=247'
DISTRICTS='방이 송파 잠실 강남 파크리오 강동1 강동2 강동3 포레온 경기북 하남 올림픽 오금 가락 거여마천위례 경기남 성내1 성내2 풍납 광진 강북 거마위 위례 거여 마천 성내 강동 성남 분당 천호'.split()
ALLOWED_TYPES=['교회장','교구장','가족장','기타']
KEYS={'id','published_at','districts','ceremony_types','parse_status','unmapped_groups','source_url'}


def district_info(title):
    """Use only explicit bracket headings. Unknown labels are not retained."""
    districts=[];types=[];unknown=set()
    blocks=re.findall(r'\[([^\[\]]+)\]',title)
    for block in blocks:
        plain=source.clean(block)
        if plain in ALLOWED_TYPES[:3] and plain not in types:types.append(plain)
    headers=[b for b in blocks if re.search(r'(?:교회장|교구장|가족장)\s*[-:：]',b)]
    for block in headers:
        current=None
        for segment in re.split(r'[/,ㆍ·&+]',block):
            token=re.sub(r'\s+','',segment)
            m=re.match(r'^(교회장|교구장|가족장)[-:：](.*)$',token)
            if m:
                current=m[1];token=m[2]
                if current not in types:types.append(current)
            elif current is None:
                unknown.add(token or '?');continue
            token=re.sub(r'교구$','',token) if not re.fullmatch(r'[1-9]\d?교구',token) else token
            if token in DISTRICTS or re.fullmatch(r'청년(?:[1-9]|1[01])부|그레이스(?:[12])?부|그레이스|엘피스부|쀼부|[1-9]\d?교구',token):
                if token not in districts:districts.append(token)
            else:unknown.add(token or '?')
    unmapped=len(unknown) if headers else 1
    return {'districts':sorted(districts),'ceremony_types':sorted(types) or ['기타'],
            'parse_status':'partial' if districts and unmapped else 'ok' if districts else 'unclassified',
            'unmapped_groups':unmapped}


def parse_listing(html,page=1):
    s=BeautifulSoup(html,'html.parser')
    first=s.select_one('li.friendsSub[data]');rows=[r for r in first.parent.find_all('li',recursive=False) if 'friendsSub' in r.get('class',[]) and r.has_attr('data')] if first else [];paging=s.select_one('.paging .m_num');active=s.select_one('.paging .post_page')
    if not rows or not paging or not active:raise ValueError('교우소식 HTML 구조가 변경되었습니다')
    m=re.search(r'/\s*(\d+)\s*$',paging.get_text(' ',strip=True))
    if not m or active.get('value')!=str(page):raise ValueError('페이지 번호 확인 실패')
    pages=int(m.group(1))
    if not 1<=page<=pages<=3000 or len(rows)>16 or page<pages and len(rows)!=16:raise ValueError('비정상적인 목록/페이지 건수')
    notices=[];ids=[]
    for row in rows:
        identity=row.get('data','');title=row.select_one('a .title_notice');day=row.select_one('a .date3')
        if not identity.isdigit() or not title or not day:raise ValueError('공지 필수 필드 누락')
        ids.append(identity)
        category=title.select_one('em');title_text=source.clean(title.get_text(' ',strip=True))
        if category is not None:
            if source.clean(category.get_text())!='장례':continue
            category.decompose();title_text=source.clean(title.get_text(' ',strip=True))
        elif not (re.search(r'\[\s*(?:교회장|교구장|가족장)\s*(?:[-:：]|\])',title_text) and re.search(r'소천|별세|장례',title_text)):continue
        published=source.clean(day.get_text())
        if source.date.fromisoformat(published).isoformat()!=published:raise ValueError('게시일 형식 오류')
        info=district_info(title_text)
        notices.append({'id':identity,'published_at':published,**info,'source_url':URL+'&mode=view&bid='+identity})
    if len(set(ids))!=len(ids):raise ValueError('같은 페이지에 중복된 공지 식별자')
    return notices,pages,ids


def validate(data):
    if data.get('schema_version')!=1 or not isinstance(data.get('meta'),dict) or not isinstance(data.get('notices'),list):raise ValueError('데이터 스키마 오류')
    seen=set()
    for r in data['notices']:
        if set(r)!=KEYS:raise ValueError('허용하지 않은 필드: 개인 정보 저장 금지')
        if not re.fullmatch(r'\d+',r['id']) or r['id'] in seen:raise ValueError('식별자 오류/중복')
        seen.add(r['id'])
        if source.date.fromisoformat(r['published_at']).isoformat()!=r['published_at']:raise ValueError('게시일 오류')
        if r['source_url']!=URL+'&mode=view&bid='+r['id']:raise ValueError('출처 주소 오류')
        if not isinstance(r['unmapped_groups'],int) or not 0<=r['unmapped_groups']<=20:raise ValueError('미분류 수 오류')
        if r['districts']!=sorted(set(r['districts'])):raise ValueError('중복 교구')
        for d in r['districts']:
            if d not in DISTRICTS and not re.fullmatch(r'청년(?:[1-9]|1[01])부|그레이스(?:[12])?부|그레이스|엘피스부|쀼부|[1-9]\d?교구',d):raise ValueError('확인되지 않은 교구/개인 정보')
        if not r['ceremony_types'] or any(t not in ALLOWED_TYPES for t in r['ceremony_types']):raise ValueError('장례 구분 오류')
        state='partial' if r['districts'] and r['unmapped_groups'] else 'ok' if r['districts'] else 'unclassified'
        if r['parse_status']!=state or not r['districts'] and not r['unmapped_groups']:raise ValueError('분석 상태 오류')
    if data['meta'].get('total')!=len(seen):raise ValueError('건수 불일치')
    return data


def collect(client,previous=None,full=True,state_path=None):
    previous=previous or {'schema_version':1,'meta':{'total':0},'notices':[]};validate(previous)
    policy=client.check_policy();existing={r['id']:r for r in previous['notices']};merged=dict(existing)
    first,pages,latest_ids=parse_listing(client.get(URL+'&page=1'))
    if previous['meta'].get('source_pages',0)>pages+max(1,int(previous['meta'].get('source_pages',0)*.1)):raise ValueError('원본 페이지 수 급감')
    cached={}
    if state_path and Path(state_path).exists():
        saved=json.loads(Path(state_path).read_text())
        age=(source.datetime.now(source.timezone.utc)-source.datetime.fromisoformat(saved['created_at'])).total_seconds() if saved.get('created_at') else 3601
        if 0<=age<3600 and saved.get('pages')==pages and saved.get('latest_ids')==latest_ids:cached=saved.get('cache',{})
    known=set(existing)|set(previous['meta'].get('latest_ids',[]));observed={};signatures=set();queue=list(range(1,pages+1)) if full else [1]
    for page in queue:
        records,total,ids=(first,pages,latest_ids) if page==1 else cached[str(page)] if str(page) in cached else parse_listing(client.get(URL+f'&page={page}'),page)
        validate({'schema_version':1,'meta':{'total':len(records)},'notices':records})
        cached[str(page)]=[records,total,ids]
        if state_path:
            checkpoint=Path(str(state_path)+'.tmp')
            checkpoint.write_text(json.dumps({'created_at':source.now(),'pages':pages,'latest_ids':latest_ids,'cache':cached},ensure_ascii=False),encoding='utf-8')
            os.replace(checkpoint,state_path)
        if total!=pages:raise ValueError('수집 도중 페이지 수 변경')
        signature=tuple(ids)
        if signature in signatures:raise ValueError('서로 다른 페이지가 같은 목록 반환')
        signatures.add(signature)
        for r in records:
            if r['id'] in observed and observed[r['id']]!=r:raise ValueError('상충하는 공지 식별자')
            observed[r['id']]=r
        if not full and not any(i in known for i in ids) and page<pages:queue.append(page+1)
        print(f'page={page}/{pages} funeral_notices={len(observed)}',flush=True)
    if full and existing and len(observed)<len(existing)*.9:raise ValueError('장례 공지 건수 급감')
    merged.update(observed);records=sorted(merged.values(),key=lambda r:(r['published_at'],int(r['id'])),reverse=True)
    stamp=source.now();data={'schema_version':1,'meta':{'total':len(records),'last_success_at':stamp,
        'full_collected_at':stamp if full else previous['meta'].get('full_collected_at'),
        'source':URL,'source_pages':pages,'latest_ids':latest_ids,'checked_pages':queue,
        'coverage_start':min((r['published_at'] for r in records),default=None),
        'coverage_end':max((r['published_at'] for r in records),default=None),
        'policy':policy,'basis':'publication_date','unit':'funeral_notice','personal_data_stored':False},'notices':records}
    validate(data)
    if state_path and Path(state_path).exists():Path(state_path).unlink()
    return data


def save(path,data):
    validate(data);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--incremental',action='store_true');p.add_argument('--output',type=Path,default=Path(__file__).with_name('notices.json'));args=p.parse_args()
    previous=json.loads(args.output.read_text()) if args.output.exists() else None
    save(args.output,collect(source.Client(),previous,full=not args.incremental,state_path=Path(__file__).with_name('.crawl-state.json')))
