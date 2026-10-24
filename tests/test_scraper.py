import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import requests
import scraper as s

FIX = Path(__file__).parent / 'fixtures'


def fixture(n=58):
    return (FIX / f'list-{n}.html').read_text()


def listing(rows, page=1, pages=1):
    items = ''.join(f'<li><a href="/tv/?menu={r["menu"]}&amp;mode=view&amp;tid={r["tid"]}"><span class="cont tit">{r["title"]}</span><span class="cont text">{r["reference_raw"]} | {r["speaker"]}</span><span class="cont date">{r["date"]}</span></a></li>' for r in rows)
    return f'<div class="PhotoList"><ul>{items}</ul></div><div class="paging"><span class="m_num"><input class="post_page" value="{page}"> / {pages}</span></div>'


def detail(r):
    return f'<div class="title_Box"><div class="date">[{r["date"]}] 예배</div><div class="title" data="sns">{r["title"]}</div><div class="vname">{r["speaker"]} 목사</div></div><div class="list_Box"><div class="title"><span class="sky">본문말씀</span> : {r["reference_raw"]}</div></div>'


def row(menu, tid=None):
    return dict(menu=menu, tid=str(tid or menu), date='2026-10-21', title='은혜의 말씀', speaker='홍길동', reference_raw='요한복음 8:1~11')


class FakeClient:
    def __init__(self):
        self.rows = {m: [row(m)] for m in s.MENUS}
        self.pages = {m: 1 for m in s.MENUS}
        self.broken = None
        self.calls = []

    def check_policy(self):
        return {'checked_at': s.now()}

    def get(self, url):
        self.calls.append(url)
        if self.broken and self.broken in url:
            raise requests.Timeout('offline')
        q = s.parse_qs(s.urlparse(url).query)
        menu = int(q['menu'][0])
        if 'tid' in q:
            return detail(next(r for r in self.rows[menu] if r['tid'] == q['tid'][0]))
        p = int(q.get('page', [1])[0])
        return listing(self.rows[menu][(p-1)*16:p*16], p, self.pages[menu])


class ReferenceTests(unittest.TestCase):
    def test_catalog(self):
        self.assertEqual(len(s.BOOKS), 66)
        self.assertEqual(sum(b['testament'] == 'OT' for b in s.BOOKS), 39)
        self.assertEqual(sum(len(b['verses']) for b in s.BOOKS), 1189)

    def test_aliases(self):
        for b in s.BOOKS:
            for alias in b['aliases']:
                if ' ' not in alias:
                    self.assertEqual(s.normalize_reference(alias+' 1:1')['key'], s.normalize_reference(b['name']+' 1:1')['key'])

    def test_multiple_and_discontinuous(self):
        a = s.normalize_reference('요 8:1-3, 5, 7-11; 롬 1:1-2')
        self.assertEqual(a['status'], 'ok')
        self.assertEqual(len(a['ranges']), 4)
        self.assertEqual(a['ranges'][1]['start'], 5)
        self.assertEqual(s.normalize_reference('요한복음 21:15~17, 25')['ranges'][-1]['start'], 25)

    def test_cross_chapter(self):
        a = s.normalize_reference('요 7:52-8:11')
        self.assertEqual(a['ranges'], [{'book':43,'chapter':7,'start':52,'end':53},{'book':43,'chapter':8,'start':1,'end':11}])

    def test_whole_chapter_and_union(self):
        self.assertEqual(s.normalize_reference('요 8')['key'],s.normalize_reference('요 8:1-59')['key'])
        self.assertEqual(s.normalize_reference('요 8:1-3,4-11')['key'],s.normalize_reference('요 8:1-11')['key'])
        self.assertEqual(s.normalize_reference('요 8장 1절-11절')['status'],'ok')

    def test_no_guess(self):
        for v in ['', '요', '요 8:20-1', '요 99:1', '요 8:999', '요 8:0', '요 8:1 이하', '요 8:1; 모르는책 1:1', '요 8:1,', '요 8:1-']:
            with self.subTest(v=v):
                self.assertEqual(s.normalize_reference(v)['status'], 'failed')


class ParserTests(unittest.TestCase):
    def test_real_html_all_menus(self):
        for n in s.MENUS:
            rows, pages = s.parse_listing(fixture(n), n)
            self.assertEqual(len(rows), 16)
            d=s.parse_detail((FIX/f'detail-{n}.html').read_text())
            self.assertTrue(all(rows[0][k]==v for k,v in d.items()))
            self.assertGreater(pages,0)

    def test_structure_change(self):
        for value in ['<html>maintenance</html>', fixture().replace('cont date','changed date'),fixture().replace('post_page','new-page')]:
            with self.assertRaises(s.CollectionError):
                s.parse_listing(value,58)

    def test_missing_reference_requires_detail(self):
        r=row(57)
        html=listing([r]).replace('요한복음 8:1~11 | 홍길동','홍길동')
        d=detail(r).replace('<span class="sky">본문말씀</span> : 요한복음 8:1~11','')
        rows,_=s.parse_listing(html,57,detail_loader=lambda _:d)
        self.assertEqual(rows[0]['reference_raw'],'')
        self.assertEqual(rows[0]['reference']['status'],'failed')
        with self.assertRaises(s.CollectionError):s.parse_listing(html,57)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.client=FakeClient()
        self.old=s.collect(self.client,s.empty_archive(),full=True)

    def test_new_one(self):
        self.client.rows[58].insert(0,row(58,900))
        result=s.collect(self.client,self.old)
        self.assertEqual(result['meta']['total'],6)
        self.assertEqual(result['meta']['stats']['added'],1)

    def test_same_tid_multiple_categories(self):
        self.client.rows[62] = [row(62,57)]
        result=s.collect(self.client,s.empty_archive(),full=True)
        self.assertEqual(result['meta']['total'],5)
        self.assertEqual(result['meta']['unique_total'],4)

    def test_shared_detail_correction_propagates_to_cached_category(self):
        c=FakeClient();c.rows[62]=[row(62,57)];previous=s.collect(c,s.empty_archive(),full=True)
        c.rows[57][0]['title']='확인된 수정';c.rows[62][0]['title']='확인된 수정'
        result=s.collect(c,previous)
        self.assertEqual({r['title'] for r in result['sermons'] if r['tid']=='57'},{'확인된 수정'})

    def test_no_news(self):
        result=s.collect(self.client,self.old)
        self.assertEqual(result['meta']['stats']['added'],0)
        self.assertEqual(result['meta']['stats']['changed'],0)
        self.assertEqual(result['sermons'][0]['updated_at'],self.old['sermons'][0]['updated_at'])

    def test_duplicate(self):
        self.client.rows[58].append(copy.deepcopy(self.client.rows[58][0]))
        self.assertEqual(s.collect(self.client,self.old)['meta']['total'],5)

    def test_conflicting_duplicate(self):
        other=copy.deepcopy(self.client.rows[58][0]);other['title']='충돌'
        self.client.rows[58].append(other)
        with self.assertRaises(s.CollectionError):s.collect(self.client,self.old)

    def test_correction(self):
        self.client.rows[58][0].update(title='수정된 제목', reference_raw='요 8:1-3; 롬 1:1')
        result=s.collect(self.client,self.old)
        r=next(r for r in result['sermons'] if r['menu']==58)
        self.assertEqual(result['meta']['stats']['changed'],1)
        self.assertEqual(r['title'],'수정된 제목')
        self.assertEqual(len(r['reference']['ranges']),2)
        self.assertEqual(r['first_collected_at'],next(r for r in self.old['sermons'] if r['menu']==58)['first_collected_at'])

    def test_failure_preserves_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sermons.json';s.atomic_save(path,self.old);old_bytes=path.read_bytes()
            self.client.broken='menu=59'
            with self.assertRaises(requests.Timeout):s.atomic_save(path,s.collect(self.client,self.old))
            self.assertEqual(old_bytes,path.read_bytes())

    def test_detail_mismatch(self):
        original=self.client.get
        def get(url):
            value=original(url)
            return value.replace('은혜의 말씀','다른 제목') if 'mode=view' in url else value
        self.client.get=get
        with self.assertRaises(s.CollectionError):s.collect(self.client,self.old)

    def test_count_drop(self):
        inflated=copy.deepcopy(self.old);inflated['meta']['menus']['57']['total_pages']=30
        with self.assertRaises(s.CollectionError):s.collect(self.client,inflated)

    def test_full_drop_and_no_auto_deletion(self):
        full_client=FakeClient();full_client.rows[57]=[row(57,i) for i in range(100,116)]
        previous=s.collect(full_client,s.empty_archive(),full=True)
        full_client.rows[57]=[row(57,100)]
        with self.assertRaises(s.CollectionError):s.collect(full_client,previous,full=True)
        result=s.collect(full_client,previous)
        self.assertEqual(result['meta']['total'],20)

    def test_old_pages_audited(self):
        c=FakeClient();c.rows[57]=[row(57,i) for i in range(100,149)];c.pages[57]=4
        previous=s.collect(c,s.empty_archive(),full=True)
        c.rows[57][-1]['title']='오래된 설교 수정'
        for _ in range(4):previous=s.collect(c,previous,audit_pages=1,recent_pages=1)
        self.assertEqual(next(r for r in previous['sermons'] if r['id']=='57:148')['title'],'오래된 설교 수정')

    def test_long_gap_scan(self):
        c=FakeClient();previous=s.collect(c,s.empty_archive(),full=True)
        c.rows[57]=[row(57,i) for i in range(100,164)]+[row(57)];c.pages[57]=5
        result=s.collect(c,previous,audit_pages=1,recent_pages=1)
        self.assertEqual(result['meta']['stats']['added'],64)

    def test_validate_and_atomic(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sermons.json';s.atomic_save(path,self.old)
            old=path.read_bytes();bad=copy.deepcopy(self.old);bad['sermons'][0]['reference']['key']='invalid'
            with self.assertRaises(s.CollectionError):s.atomic_save(path,bad)
            self.assertEqual(old,path.read_bytes())
            s.atomic_save(path,self.old)
            self.assertEqual(Path(str(path)+'.bak').read_bytes(),old)


class NetworkPolicyTests(unittest.TestCase):
    def allowed_client(self):
        c=s.Client();c.robot=s.RobotFileParser();c.robot.parse(['User-agent: *','Disallow:'])
        return c

    @patch('scraper.time.sleep')
    def test_retry_timeout(self,_):
        c=self.allowed_client();r=Mock(status_code=200,text='ok',headers={});c.session.get=Mock(side_effect=[requests.Timeout(),r])
        self.assertEqual(c.get(s.list_url(57)),'ok');self.assertEqual(c.session.get.call_count,2)

    @patch('scraper.time.sleep')
    def test_retry_429_then_success(self,_):
        c=self.allowed_client();c.session.get=Mock(side_effect=[Mock(status_code=429,headers={'Retry-After':'3'}),Mock(status_code=200,text='ok')])
        self.assertEqual(c.get(s.list_url(57)),'ok')

    @patch('scraper.time.sleep')
    def test_access_denied_not_retried(self,_):
        c=self.allowed_client();c.session.get=Mock(return_value=Mock(status_code=403))
        with self.assertRaises(s.CollectionError):c.get(s.list_url(57))
        self.assertEqual(c.session.get.call_count,1)

    def test_robots(self):
        c=s.Client();c.robot=s.RobotFileParser();c.robot.parse(['User-agent: *','Disallow: /tv/']);c.session.get=Mock()
        with self.assertRaises(s.CollectionError):c.get(s.list_url(57))
        c.session.get.assert_not_called()

    def test_changed_terms_stop(self):
        c=s.Client();c.get=Mock(side_effect=['User-agent: *','제1조 (약관의 목적과 동의) 변경됨 2022년 5월 10일 부터 시행 됩니다.'])
        with self.assertRaises(s.CollectionError):c.check_policy()


if __name__=='__main__':unittest.main()
