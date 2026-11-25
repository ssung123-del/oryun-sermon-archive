import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('funeral_scraper',ROOT/'funerals/scraper.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)


def listing(items,page=1,pages=1):
    rows=''.join(f'<li class="friendsSub" data="{i}"><a href="#open"><span class="title_notice">{tag}{title}</span><span class="date3">2026-11-25</span></a><div class="Liston">이름, 연락처, 장소는 보관하지 않음</div></li>' for i,tag,title in items)
    return f'<ul>{rows}</ul><div class="paging"><span class="m_num"><input class="post_page" value="{page}"> / {pages}</span></div>'


class FuneralParserTests(unittest.TestCase):
    def test_multiple_and_shared_names(self):
        x=f.district_info('[교회장-하남/교구장-성내2] 가상 이름')
        self.assertEqual(x['districts'],['성내2','하남'])
        self.assertEqual(x['ceremony_types'],['교구장','교회장'])
        self.assertEqual(f.district_info('[교회장-파크리오/교구장-파크리오] 가상')['districts'],['파크리오'])
        self.assertEqual(f.district_info('[교구장-경기남/파크리오] 가상')['districts'],['경기남','파크리오'])

    def test_no_guess_and_partial(self):
        self.assertEqual(f.district_info('[교구장] 가상')['parse_status'],'unclassified')
        self.assertEqual(f.district_info('[교구장] 가상')['ceremony_types'],['교구장'])
        self.assertEqual(f.district_info('[교구장-하남/알수없는표기] 가상')['parse_status'],'partial')
        self.assertEqual(f.district_info('이름 안에 하남이 있어도 추정하지 않음')['districts'],[])
        self.assertEqual(f.district_info('[교구장-거마위] 가상')['districts'],['거마위'])
        self.assertEqual(f.district_info('[교구장-그레이스부] 가상')['districts'],['그레이스부'])

    def test_only_funeral_and_no_personal_fields(self):
        html=listing([(1,'<em>장례</em>','[교구장-오금] 가상 이름 소천'),(2,'<em>결혼</em>','[교구장-하남] 가상 결혼'),(3,'','[교회장-성내1] 가상 소천')])
        rows,pages,ids=f.parse_listing(html)
        self.assertEqual([r['id'] for r in rows],['1','3'])
        self.assertEqual(ids,['1','2','3'])
        self.assertNotIn('가상',json.dumps(rows,ensure_ascii=False))
        self.assertTrue(all(set(r)==f.KEYS for r in rows))
        self.assertTrue(all('&mode=view&bid=' in r['source_url'] for r in rows))

    def test_structure_dates_counts(self):
        for html in ['<html>maintenance</html>',listing([(1,'<em>장례</em>','[교구장-오금] 가상')]).replace('date3','newdate'),listing([(1,'<em>장례</em>','[교구장-오금] 가상')],1,2)]:
            with self.subTest(html=html[:30]),self.assertRaises(ValueError):f.parse_listing(html)
        with self.assertRaises(ValueError):f.parse_listing(listing([(1,'<em>장례</em>','[교구장-오금] 가상')]).replace('2026-11-25','2026-99-99'))

    def test_validate_rejects_private_data(self):
        rows,_,_=f.parse_listing(listing([(1,'<em>장례</em>','[교구장-오금] 가상')]))
        d={'schema_version':1,'meta':{'total':1},'notices':rows};f.validate(d)
        for key,value in [('title','개인 이름'),('phone','연락처')]:
            bad=copy.deepcopy(d);bad['notices'][0][key]=value
            with self.assertRaises(ValueError):f.validate(bad)
        bad=copy.deepcopy(d);bad['notices'][0]['districts']=['개인 이름']
        with self.assertRaises(ValueError):f.validate(bad)

    def test_atomic_invalid_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'notices.json';p.write_bytes(b'previous')
            with self.assertRaises(ValueError):f.save(p,{'schema_version':99})
            self.assertEqual(p.read_bytes(),b'previous')

    def test_checked_archive(self):
        data=json.loads((ROOT/'funerals/notices.json').read_text());f.validate(data)
        self.assertTrue(data['meta']['full_collected_at'])
        self.assertTrue(all(set(r)==f.KEYS for r in data['notices']))


if __name__=='__main__':unittest.main()
