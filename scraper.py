#!/usr/bin/env python3
"""Oryun public sermon metadata collector. Fail closed; never fetch media."""
from __future__ import annotations
import argparse
import copy
from datetime import date, datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE = 'https://oryun.org'
TERMS_URL = BASE + '/about/?menu=312'
AGENT = 'OryunSermonArchive/1.0 (+metadata-only; public noncommercial archive)'
MENUS = {57: '주일예배', 58: '수요예배', 59: '금요기도회', 61: '주일예배(부목사)', 62: '외부강사'}
LOG = logging.getLogger('oryun')
BOOKS = [{'id': 1, 'name': '창세기', 'aliases': ['창세기', '창'], 'testament': 'OT', 'verses': [31, 25, 24, 26, 32, 22, 24, 22, 29, 32, 32, 20, 18, 24, 21, 16, 27, 33, 38, 18, 34, 24, 20, 67, 34, 35, 46, 22, 35, 43, 55, 32, 20, 31, 29, 43, 36, 30, 23, 23, 57, 38, 34, 34, 28, 34, 31, 22, 33, 26]}, {'id': 2, 'name': '출애굽기', 'aliases': ['출애굽기', '출'], 'testament': 'OT', 'verses': [22, 25, 22, 31, 23, 30, 25, 32, 35, 29, 10, 51, 22, 31, 27, 36, 16, 27, 25, 26, 36, 31, 33, 18, 40, 37, 21, 43, 46, 38, 18, 35, 23, 35, 35, 38, 29, 31, 43, 38]}, {'id': 3, 'name': '레위기', 'aliases': ['레위기', '레'], 'testament': 'OT', 'verses': [17, 16, 17, 35, 19, 30, 38, 36, 24, 20, 47, 8, 59, 57, 33, 34, 16, 30, 37, 27, 24, 33, 44, 23, 55, 46, 34]}, {'id': 4, 'name': '민수기', 'aliases': ['민수기', '민'], 'testament': 'OT', 'verses': [54, 34, 51, 49, 31, 27, 89, 26, 23, 36, 35, 16, 33, 45, 41, 50, 13, 32, 22, 29, 35, 41, 30, 25, 18, 65, 23, 31, 40, 16, 54, 42, 56, 29, 34, 13]}, {'id': 5, 'name': '신명기', 'aliases': ['신명기', '신'], 'testament': 'OT', 'verses': [46, 37, 29, 49, 33, 25, 26, 20, 29, 22, 32, 32, 18, 29, 23, 22, 20, 22, 21, 20, 23, 30, 25, 22, 19, 19, 26, 68, 29, 20, 30, 52, 29, 12]}, {'id': 6, 'name': '여호수아', 'aliases': ['여호수아', '수'], 'testament': 'OT', 'verses': [18, 24, 17, 24, 15, 27, 26, 35, 27, 43, 23, 24, 33, 15, 63, 10, 18, 28, 51, 9, 45, 34, 16, 33]}, {'id': 7, 'name': '사사기', 'aliases': ['사사기', '삿'], 'testament': 'OT', 'verses': [36, 23, 31, 24, 31, 40, 25, 35, 57, 18, 40, 15, 25, 20, 20, 31, 13, 31, 30, 48, 25]}, {'id': 8, 'name': '룻기', 'aliases': ['룻기', '룻'], 'testament': 'OT', 'verses': [22, 23, 18, 22]}, {'id': 9, 'name': '사무엘상', 'aliases': ['사무엘상', '삼상'], 'testament': 'OT', 'verses': [28, 36, 21, 22, 12, 21, 17, 22, 27, 27, 15, 25, 23, 52, 35, 23, 58, 30, 24, 42, 15, 23, 29, 22, 44, 25, 12, 25, 11, 31, 13]}, {'id': 10, 'name': '사무엘하', 'aliases': ['사무엘하', '삼하'], 'testament': 'OT', 'verses': [27, 32, 39, 12, 25, 23, 29, 18, 13, 19, 27, 31, 39, 33, 37, 23, 29, 33, 43, 26, 22, 51, 39, 25]}, {'id': 11, 'name': '열왕기상', 'aliases': ['열왕기상', '왕상'], 'testament': 'OT', 'verses': [53, 46, 28, 34, 18, 38, 51, 66, 28, 29, 43, 33, 34, 31, 34, 34, 24, 46, 21, 43, 29, 53]}, {'id': 12, 'name': '열왕기하', 'aliases': ['열왕기하', '왕하'], 'testament': 'OT', 'verses': [18, 25, 27, 44, 27, 33, 20, 29, 37, 36, 21, 21, 25, 29, 38, 20, 41, 37, 37, 21, 26, 20, 37, 20, 30]}, {'id': 13, 'name': '역대상', 'aliases': ['역대상', '대상'], 'testament': 'OT', 'verses': [54, 55, 24, 43, 26, 81, 40, 40, 44, 14, 47, 40, 14, 17, 29, 43, 27, 17, 19, 8, 30, 19, 32, 31, 31, 32, 34, 21, 30]}, {'id': 14, 'name': '역대하', 'aliases': ['역대하', '대하'], 'testament': 'OT', 'verses': [17, 18, 17, 22, 14, 42, 22, 18, 31, 19, 23, 16, 22, 15, 19, 14, 19, 34, 11, 37, 20, 12, 21, 27, 28, 23, 9, 27, 36, 27, 21, 33, 25, 33, 27, 23]}, {'id': 15, 'name': '에스라', 'aliases': ['에스라', '스'], 'testament': 'OT', 'verses': [11, 70, 13, 24, 17, 22, 28, 36, 15, 44]}, {'id': 16, 'name': '느헤미야', 'aliases': ['느헤미야', '느'], 'testament': 'OT', 'verses': [11, 20, 32, 23, 19, 19, 73, 18, 38, 39, 36, 47, 31]}, {'id': 17, 'name': '에스더', 'aliases': ['에스더', '에'], 'testament': 'OT', 'verses': [22, 23, 15, 17, 14, 14, 10, 17, 32, 3]}, {'id': 18, 'name': '욥기', 'aliases': ['욥기', '욥'], 'testament': 'OT', 'verses': [22, 13, 26, 21, 27, 30, 21, 22, 35, 22, 20, 25, 28, 22, 35, 22, 16, 21, 29, 29, 34, 30, 17, 25, 6, 14, 23, 28, 25, 31, 40, 22, 33, 37, 16, 33, 24, 41, 30, 24, 34, 17]}, {'id': 19, 'name': '시편', 'aliases': ['시편', '시'], 'testament': 'OT', 'verses': [6, 12, 8, 8, 12, 10, 17, 9, 20, 18, 7, 8, 6, 7, 5, 11, 15, 50, 14, 9, 13, 31, 6, 10, 22, 12, 14, 9, 11, 12, 24, 11, 22, 22, 28, 12, 40, 22, 13, 17, 13, 11, 5, 26, 17, 11, 9, 14, 20, 23, 19, 9, 6, 7, 23, 13, 11, 11, 17, 12, 8, 12, 11, 10, 13, 20, 7, 35, 36, 5, 24, 20, 28, 23, 10, 12, 20, 72, 13, 19, 16, 8, 18, 12, 13, 17, 7, 18, 52, 17, 16, 15, 5, 23, 11, 13, 12, 9, 9, 5, 8, 28, 22, 35, 45, 48, 43, 13, 31, 7, 10, 10, 9, 8, 18, 19, 2, 29, 176, 7, 8, 9, 4, 8, 5, 6, 5, 6, 8, 8, 3, 18, 3, 3, 21, 26, 9, 8, 24, 13, 10, 7, 12, 15, 21, 10, 20, 14, 9, 6]}, {'id': 20, 'name': '잠언', 'aliases': ['잠언', '잠'], 'testament': 'OT', 'verses': [33, 22, 35, 27, 23, 35, 27, 36, 18, 32, 31, 28, 25, 35, 33, 33, 28, 24, 29, 30, 31, 29, 35, 34, 28, 28, 27, 28, 27, 33, 31]}, {'id': 21, 'name': '전도서', 'aliases': ['전도서', '전'], 'testament': 'OT', 'verses': [18, 26, 22, 16, 20, 12, 29, 17, 18, 20, 10, 14]}, {'id': 22, 'name': '아가', 'aliases': ['아가', '아', '아가서'], 'testament': 'OT', 'verses': [17, 17, 11, 16, 16, 13, 13, 14]}, {'id': 23, 'name': '이사야', 'aliases': ['이사야', '사'], 'testament': 'OT', 'verses': [31, 22, 26, 6, 30, 13, 25, 22, 21, 34, 16, 6, 22, 32, 9, 14, 14, 7, 25, 6, 17, 25, 18, 23, 12, 21, 13, 29, 24, 33, 9, 20, 24, 17, 10, 22, 38, 22, 8, 31, 29, 25, 28, 28, 25, 13, 15, 22, 26, 11, 23, 15, 12, 17, 13, 12, 21, 14, 21, 22, 11, 12, 19, 12, 25, 24]}, {'id': 24, 'name': '예레미야', 'aliases': ['예레미야', '렘'], 'testament': 'OT', 'verses': [19, 37, 25, 31, 31, 30, 34, 22, 26, 25, 23, 17, 27, 22, 21, 21, 27, 23, 15, 18, 14, 30, 40, 10, 38, 24, 22, 17, 32, 24, 40, 44, 26, 22, 19, 32, 21, 28, 18, 16, 18, 22, 13, 30, 5, 28, 7, 47, 39, 46, 64, 34]}, {'id': 25, 'name': '예레미야애가', 'aliases': ['예레미야애가', '애', '예레미야 애가'], 'testament': 'OT', 'verses': [22, 22, 66, 22, 22]}, {'id': 26, 'name': '에스겔', 'aliases': ['에스겔', '겔'], 'testament': 'OT', 'verses': [28, 10, 27, 17, 17, 14, 27, 18, 11, 22, 25, 28, 23, 23, 8, 63, 24, 32, 14, 49, 32, 31, 49, 27, 17, 21, 36, 26, 21, 26, 18, 32, 33, 31, 15, 38, 28, 23, 29, 49, 26, 20, 27, 31, 25, 24, 23, 35]}, {'id': 27, 'name': '다니엘', 'aliases': ['다니엘', '단'], 'testament': 'OT', 'verses': [21, 49, 30, 37, 31, 28, 28, 27, 27, 21, 45, 13]}, {'id': 28, 'name': '호세아', 'aliases': ['호세아', '호'], 'testament': 'OT', 'verses': [11, 23, 5, 19, 15, 11, 16, 14, 17, 15, 12, 14, 16, 9]}, {'id': 29, 'name': '요엘', 'aliases': ['요엘', '욜'], 'testament': 'OT', 'verses': [20, 32, 21]}, {'id': 30, 'name': '아모스', 'aliases': ['아모스', '암'], 'testament': 'OT', 'verses': [15, 16, 15, 13, 27, 14, 17, 14, 15]}, {'id': 31, 'name': '오바댜', 'aliases': ['오바댜', '옵'], 'testament': 'OT', 'verses': [21]}, {'id': 32, 'name': '요나', 'aliases': ['요나', '욘'], 'testament': 'OT', 'verses': [17, 10, 10, 11]}, {'id': 33, 'name': '미가', 'aliases': ['미가', '미'], 'testament': 'OT', 'verses': [16, 13, 12, 13, 15, 16, 20]}, {'id': 34, 'name': '나훔', 'aliases': ['나훔', '나'], 'testament': 'OT', 'verses': [15, 13, 19]}, {'id': 35, 'name': '하박국', 'aliases': ['하박국', '합'], 'testament': 'OT', 'verses': [17, 20, 19]}, {'id': 36, 'name': '스바냐', 'aliases': ['스바냐', '습'], 'testament': 'OT', 'verses': [18, 15, 20]}, {'id': 37, 'name': '학개', 'aliases': ['학개', '학'], 'testament': 'OT', 'verses': [15, 23]}, {'id': 38, 'name': '스가랴', 'aliases': ['스가랴', '슥'], 'testament': 'OT', 'verses': [21, 13, 10, 14, 11, 15, 14, 23, 17, 12, 17, 14, 9, 21]}, {'id': 39, 'name': '말라기', 'aliases': ['말라기', '말'], 'testament': 'OT', 'verses': [14, 17, 18, 6]}, {'id': 40, 'name': '마태복음', 'aliases': ['마태복음', '마'], 'testament': 'NT', 'verses': [25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34, 46, 46, 39, 51, 46, 75, 66, 20]}, {'id': 41, 'name': '마가복음', 'aliases': ['마가복음', '막'], 'testament': 'NT', 'verses': [45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20]}, {'id': 42, 'name': '누가복음', 'aliases': ['누가복음', '눅'], 'testament': 'NT', 'verses': [80, 52, 38, 44, 39, 49, 50, 56, 62, 42, 54, 59, 35, 35, 32, 31, 37, 43, 48, 47, 38, 71, 56, 53]}, {'id': 43, 'name': '요한복음', 'aliases': ['요한복음', '요'], 'testament': 'NT', 'verses': [51, 25, 36, 54, 47, 71, 53, 59, 41, 42, 57, 50, 38, 31, 27, 33, 26, 40, 42, 31, 25]}, {'id': 44, 'name': '사도행전', 'aliases': ['사도행전', '행'], 'testament': 'NT', 'verses': [26, 47, 26, 37, 42, 15, 60, 40, 43, 48, 30, 25, 52, 28, 41, 40, 34, 28, 41, 38, 40, 30, 35, 27, 27, 32, 44, 31]}, {'id': 45, 'name': '로마서', 'aliases': ['로마서', '롬'], 'testament': 'NT', 'verses': [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27]}, {'id': 46, 'name': '고린도전서', 'aliases': ['고린도전서', '고전'], 'testament': 'NT', 'verses': [31, 16, 23, 21, 13, 20, 40, 13, 27, 33, 34, 31, 13, 40, 58, 24]}, {'id': 47, 'name': '고린도후서', 'aliases': ['고린도후서', '고후'], 'testament': 'NT', 'verses': [24, 17, 18, 18, 21, 18, 16, 24, 15, 18, 33, 21, 14]}, {'id': 48, 'name': '갈라디아서', 'aliases': ['갈라디아서', '갈'], 'testament': 'NT', 'verses': [24, 21, 29, 31, 26, 18]}, {'id': 49, 'name': '에베소서', 'aliases': ['에베소서', '엡'], 'testament': 'NT', 'verses': [23, 22, 21, 32, 33, 24]}, {'id': 50, 'name': '빌립보서', 'aliases': ['빌립보서', '빌'], 'testament': 'NT', 'verses': [30, 30, 21, 23]}, {'id': 51, 'name': '골로새서', 'aliases': ['골로새서', '골'], 'testament': 'NT', 'verses': [29, 23, 25, 18]}, {'id': 52, 'name': '데살로니가전서', 'aliases': ['데살로니가전서', '살전'], 'testament': 'NT', 'verses': [10, 20, 13, 18, 28]}, {'id': 53, 'name': '데살로니가후서', 'aliases': ['데살로니가후서', '살후'], 'testament': 'NT', 'verses': [12, 17, 18]}, {'id': 54, 'name': '디모데전서', 'aliases': ['디모데전서', '딤전'], 'testament': 'NT', 'verses': [20, 15, 16, 16, 25, 21]}, {'id': 55, 'name': '디모데후서', 'aliases': ['디모데후서', '딤후'], 'testament': 'NT', 'verses': [18, 26, 17, 22]}, {'id': 56, 'name': '디도서', 'aliases': ['디도서', '딛'], 'testament': 'NT', 'verses': [16, 15, 15]}, {'id': 57, 'name': '빌레몬서', 'aliases': ['빌레몬서', '몬'], 'testament': 'NT', 'verses': [25]}, {'id': 58, 'name': '히브리서', 'aliases': ['히브리서', '히'], 'testament': 'NT', 'verses': [14, 18, 19, 16, 14, 20, 28, 13, 28, 39, 40, 29, 25]}, {'id': 59, 'name': '야고보서', 'aliases': ['야고보서', '약'], 'testament': 'NT', 'verses': [27, 26, 18, 17, 20]}, {'id': 60, 'name': '베드로전서', 'aliases': ['베드로전서', '벧전'], 'testament': 'NT', 'verses': [25, 25, 22, 19, 14]}, {'id': 61, 'name': '베드로후서', 'aliases': ['베드로후서', '벧후'], 'testament': 'NT', 'verses': [21, 22, 18]}, {'id': 62, 'name': '요한일서', 'aliases': ['요한일서', '요일', '요한1서'], 'testament': 'NT', 'verses': [10, 29, 24, 21, 21]}, {'id': 63, 'name': '요한이서', 'aliases': ['요한이서', '요이', '요한2서'], 'testament': 'NT', 'verses': [13]}, {'id': 64, 'name': '요한삼서', 'aliases': ['요한삼서', '요삼', '요한3서'], 'testament': 'NT', 'verses': [14]}, {'id': 65, 'name': '유다서', 'aliases': ['유다서', '유'], 'testament': 'NT', 'verses': [25]}, {'id': 66, 'name': '요한계시록', 'aliases': ['요한계시록', '계'], 'testament': 'NT', 'verses': [20, 29, 22, 11, 14, 17, 17, 13, 21, 11, 19, 17, 18, 20, 8, 21, 18, 24, 21, 15, 27, 21]}]

class CollectionError(RuntimeError):
    pass


def clean(value):
    return re.sub(r'\s+', ' ', value).strip()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def normalize_reference(raw):
    """Return an all-or-nothing union of chapter-local closed verse intervals."""
    failure = {'status': 'failed', 'ranges': [], 'key': None, 'error': '지원하지 않거나 유효하지 않은 성경 본문 표기'}
    value = re.sub(r'\s+', '', raw).replace('：', ':')
    value = re.sub(r'[~～〜–—−]', '-', value).replace('，', ',').replace('；', ';')
    aliases = {re.sub(r'\s+', '', a): b for b in BOOKS for a in b['aliases']}
    pattern = re.compile('|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)))
    matches = list(pattern.finditer(value))
    if not matches or matches[0].start() != 0:
        return failure
    intervals = []
    try:
        for i, match in enumerate(matches):
            b = aliases[match.group()]
            tail = value[match.end():matches[i+1].start() if i+1 < len(matches) else len(value)]
            if i+1 < len(matches):
                tail = re.sub(r'(?:[;,/·]|및)+$', '', tail)
            tail = tail.replace('장', ':').replace('절', '')
            tail = re.sub(r':(?=[,;-]|$)', '', tail)
            # Only unambiguous comma/semicolon-separated ranges are accepted.
            pieces = re.split('[,;]', tail)
            chapter = None
            verse_context = False
            for piece in pieces:
                if not piece:
                    raise ValueError()
                m = re.fullmatch(r'(\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?', piece)
                if not m:
                    raise ValueError()
                a, v, end, ev = (int(x) if x else None for x in m.groups())
                if v is not None:
                    sc, sv = a, v
                    ec, ve = (end, ev) if ev is not None else (a, end or v)
                    chapter, verse_context = ec, True
                elif verse_context:
                    if ev is not None:
                        raise ValueError()
                    sc = ec = chapter
                    sv, ve = a, end or a
                else:
                    if ev is not None:
                        raise ValueError()
                    sc, ec = a, end or a
                    sv, ve = 1, b['verses'][ec-1] if 1 <= ec <= len(b['verses']) else 0
                    chapter = ec
                if not (1 <= sc <= ec <= len(b['verses'])):
                    raise ValueError()
                if not (1 <= sv <= b['verses'][sc-1] and 1 <= ve <= b['verses'][ec-1]):
                    raise ValueError()
                if sc == ec and sv > ve:
                    raise ValueError()
                for ch in range(sc, ec+1):
                    intervals.append({'book': b['id'], 'chapter': ch, 'start': sv if ch == sc else 1,
                                      'end': ve if ch == ec else b['verses'][ch-1]})
        merged = []
        for r in sorted(intervals, key=lambda r: (r['book'], r['chapter'], r['start'], r['end'])):
            if merged and (r['book'], r['chapter']) == (merged[-1]['book'], merged[-1]['chapter']) and r['start'] <= merged[-1]['end']+1:
                merged[-1]['end'] = max(merged[-1]['end'], r['end'])
            else:
                merged.append(r.copy())
        if not merged:
            return failure
        key = ';'.join(f"{r['book']}:{r['chapter']}:{r['start']}-{r['end']}" for r in merged)
        return {'status': 'ok', 'ranges': merged, 'key': key, 'error': None}
    except (ValueError, IndexError):
        return failure


def list_url(menu, page=1):
    return BASE + '/tv/?' + urlencode({'menu': menu, 'page': page, 'tv_type': 'photo'})


def source_url(menu, tid):
    return BASE + '/tv/?' + urlencode({'menu': menu, 'mode': 'view', 'tid': tid})


def parse_listing(html, menu, page=1, detail_loader=None):
    s = BeautifulSoup(html, 'html.parser')
    container = s.select_one('.PhotoList')
    paging = s.select_one('.paging .m_num')
    active = s.select_one('.paging .post_page')
    if container is None or paging is None or active is None:
        raise CollectionError(f'menu={menu} page={page}: 목록/페이지 구조 변경')
    m = re.search(r'/\s*(\d+)\s*$', paging.get_text(' ', strip=True))
    if not m or active.get('value') != str(page):
        raise CollectionError('페이지 번호 검증 실패')
    total_pages = int(m.group(1))
    if not 1 <= page <= total_pages <= 2000:
        raise CollectionError('비정상적인 페이지 수')
    records = []
    for a in container.select('a[href*="tid="]'):
        q = parse_qs(urlparse(urljoin(BASE, a['href'])).query)
        fields = [a.select_one(x) for x in ['.cont.tit', '.cont.text', '.cont.date']]
        if any(x is None for x in fields) or q.get('menu') != [str(menu)] or not re.fullmatch(r'\d+', q.get('tid', [''])[0]):
            raise CollectionError('설교 필드/식별자 구조 변경')
        title, text, day = [clean(x.get_text(' ', strip=True)) for x in fields]
        if text.count('|') == 1:
            reference, speaker = map(clean, text.split('|'))
        elif '|' not in text and detail_loader:
            detail = parse_detail(detail_loader(source_url(menu, q['tid'][0])), allow_missing_reference=True)
            if detail['title'] != title or detail['date'] != day or detail['speaker'] != text:
                raise CollectionError('본문 누락 목록과 상세 메타데이터 불일치')
            reference, speaker = detail['reference_raw'], detail['speaker']
        else:
            raise CollectionError('본문/설교자 구분자 구조 변경')
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError()
        except ValueError as e:
            raise CollectionError(f'유효하지 않은 날짜 {day}') from e
        if not title or not speaker:
            raise CollectionError('필수 메타데이터 누락')
        tid = q['tid'][0]
        record = {'id': f'{menu}:{tid}', 'menu': menu, 'tid': tid, 'date': day, 'title': title,
                  'speaker': speaker, 'reference_raw': reference, 'service': MENUS[menu],
                  'source_url': source_url(menu, tid), 'reference': normalize_reference(reference)}
        record['content_hash'] = digest({k: record[k] for k in ['date', 'title', 'speaker', 'reference_raw', 'service']})
        records.append(record)
    if not records or len(records) > 16 or (page < total_pages and len(records) != 16):
        raise CollectionError(f'비정상 목록 건수: menu={menu} page={page} count={len(records)}')
    return records, total_pages


def parse_detail(html, *, allow_missing_reference=False):
    s = BeautifulSoup(html, 'html.parser')
    title = s.select_one('.title_Box .title[data="sns"]')
    day = s.select_one('.title_Box .date')
    speaker = s.select_one('.title_Box .vname')
    refs = [x for x in s.select('.list_Box > .title') if x.select_one('.sky') and clean(x.select_one('.sky').get_text()) == '본문말씀']
    # Fixture keeps only the metadata title to avoid redistributing Bible text.
    if not refs:
        refs = [x for x in s.select('div.title') if x.select_one('.sky') and clean(x.select_one('.sky').get_text()) == '본문말씀']
    if not refs:
        blank = s.select('.list_Box > .title')
        if len(blank) == 1 and not clean(blank[0].get_text()):
            refs = blank
    if title is None or day is None or speaker is None or (len(refs) != 1 and not (allow_missing_reference and not refs)):
        raise CollectionError('상세 페이지 메타데이터 구조 변경')
    match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', day.get_text())
    if not match:
        raise CollectionError('상세 날짜 구조 변경')
    return {'title': clean(title.get_text()), 'date': match.group(1),
            'speaker': re.sub(r'\s+(목사|집사|장로|전도사|선교사|교수|강도사|권사|성도)$', '', clean(speaker.get_text())),
            'reference_raw': re.sub(r'^본문말씀\s*:\s*', '', clean(refs[0].get_text(' ', strip=True))) if refs else ''}


def terms_text(html):
    s = BeautifulSoup(html, 'html.parser')
    text = clean(s.get_text(' ', strip=True))
    start, end = text.find('제1조 (약관의 목적과 동의)'), text.find('2022년 5월 10일 부터 시행 됩니다.')
    if start < 0 or end < start:
        raise CollectionError('이용약관 구조/시행일 변경: 수동 검토 필요')
    return text[start:end+len('2022년 5월 10일 부터 시행 됩니다.')]

REVIEWED_TERMS_HASH = '409fb91ce256dab3ea30c0bf2c79cb47ef0ff7efd42029fa7f39636691e8c5e5'

class Client:
    def __init__(self, delay=1.2):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = AGENT
        self.delay = max(delay, 1.2)
        self.last_request = 0.0
        self.robot = None
        self.requests = 0

    def get(self, url, *, policy=False):
        if urlparse(url).netloc != 'oryun.org' or urlparse(url).scheme != 'https':
            raise CollectionError('공식 HTTPS 호스트 이외 요청 금지')
        if not policy and (self.robot is None or not self.robot.can_fetch(AGENT, url)):
            raise CollectionError(f'robots.txt에 의해 수집 중단: {url}')
        for attempt in range(4):
            time.sleep(max(0, self.last_request + self.delay - time.monotonic()))
            self.last_request = time.monotonic()
            self.requests += 1
            try:
                r = self.session.get(url, timeout=(10, 40), allow_redirects=False)
                if r.status_code in (401, 403) or 300 <= r.status_code < 400:
                    raise CollectionError(f'접근 제한/리디렉션: {url} HTTP {r.status_code}')
                if r.status_code == 429 or 500 <= r.status_code < 600:
                    if attempt == 3:
                        r.raise_for_status()
                    retry = r.headers.get('Retry-After', '')
                    wait = max(2 ** (attempt+1), int(retry) if retry.isdigit() else 0)
                    if wait > 120:
                        raise CollectionError('긴 Retry-After: 다음 실행까지 수집 중단')
                    LOG.warning('HTTP %s 재시도 %ss: %s', r.status_code, wait, url)
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                r.encoding = 'utf-8'
                return r.text
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt == 3:
                    raise CollectionError(f'요청 실패: {url}: {e}') from e
                LOG.warning('연결 실패 재시도: %s', url)
                time.sleep(2 ** (attempt+1))
        raise CollectionError('요청 재시도 소진')

    def check_policy(self):
        robots = self.get(BASE + '/robots.txt', policy=True)
        if not robots.lstrip().lower().startswith(('user-agent:', '#')) or 'user-agent:' not in robots.lower():
            raise CollectionError('유효한 robots.txt를 확인할 수 없음')
        self.robot = RobotFileParser()
        self.robot.parse(robots.splitlines())
        self.delay = max(self.delay, self.robot.crawl_delay(AGENT) or self.robot.crawl_delay('*') or 0)
        rate = self.robot.request_rate(AGENT) or self.robot.request_rate('*')
        if rate:
            self.delay = max(self.delay, rate.seconds / rate.requests)
        terms = terms_text(self.get(TERMS_URL))
        h = digest(terms)
        if h != REVIEWED_TERMS_HASH:
            raise CollectionError('이용약관이 검토된 내용과 다릅니다. 운영자가 정책 재검토 후 코드의 해시를 갱신해야 합니다.')
        return {'checked_at': now(), 'robots_url': BASE+'/robots.txt', 'robots_hash': digest(robots),
                'terms_url': TERMS_URL, 'terms_hash': h}


def empty_archive():
    return {'schema_version': 1, 'meta': {'last_success_at': None, 'full_collected_at': None,
            'total': 0, 'menus': {}}, 'sermons': []}


def validate_archive(data):
    if data.get('schema_version') != 1 or not isinstance(data.get('meta'), dict) or not isinstance(data.get('sermons'), list):
        raise CollectionError('지원하지 않는 JSON 스키마')
    seen = set()
    logical = {}
    for r in data['sermons']:
        try:
            if r['id'] != f"{r['menu']}:{r['tid']}" or r['id'] in seen or r['menu'] not in MENUS or not re.fullmatch(r'\d+', r['tid']):
                raise ValueError('중복/식별자')
            if r['service'] != MENUS[r['menu']]:
                raise ValueError('예배 분류')
            if r['source_url'] != source_url(r['menu'], r['tid']):
                raise ValueError('출처 URL')
            if date.fromisoformat(r['date']).isoformat() != r['date']:
                raise ValueError('날짜')
            if not all(isinstance(r[k], str) and r[k] for k in ['title', 'speaker', 'first_collected_at', 'updated_at', 'last_seen_at']) or not isinstance(r['reference_raw'], str):
                raise ValueError('필수 값')
            if r['reference'] != normalize_reference(r['reference_raw']):
                raise ValueError('정규화 불일치')
            if r['content_hash'] != digest({k: r[k] for k in ['date', 'title', 'speaker', 'reference_raw', 'service']}):
                raise ValueError('내용 해시 불일치')
        except (KeyError, TypeError, ValueError) as e:
            raise CollectionError(f'데이터 검증 실패: {r.get("id")}: {e}') from e
        seen.add(r['id'])
        core = tuple(r[k] for k in ['date', 'title', 'speaker', 'reference_raw'])
        if r['tid'] in logical and logical[r['tid']] != core:
            raise CollectionError(f'같은 tid의 메타데이터 충돌: {r["tid"]}')
        logical[r['tid']] = core
    if data['meta'].get('total') != len(seen):
        raise CollectionError('전체 건수 불일치')
    if 'unique_total' in data['meta'] and data['meta']['unique_total'] != len(logical):
        raise CollectionError('고유 설교 건수 불일치')
    return data


def collect(client, previous, *, full=False, audit_pages=2, recent_pages=2):
    validate_archive(previous)
    full = full or not previous['meta'].get('full_collected_at')
    policy = client.check_policy()
    stamp = now()
    old = {r['id']: r for r in previous['sermons']}
    merged = copy.deepcopy(old)
    menu_meta = {}
    stats = {'added': 0, 'changed': 0, 'observed': 0, 'normalization_failed': 0}
    observed_logical = {}
    for menu in MENUS:
        first, total_pages = parse_listing(client.get(list_url(menu)), menu, detail_loader=client.get)
        before = previous['meta'].get('menus', {}).get(str(menu), {})
        old_pages = before.get('total_pages', 0)
        if old_pages and total_pages < old_pages - max(1, int(old_pages * .1)):
            raise CollectionError(f'menu={menu}: 목록 페이지 수 급감 {old_pages} → {total_pages}')
        target = set(range(1, total_pages+1)) if full else set(range(1, min(total_pages, recent_pages)+1))
        cursor = min(max(1, before.get('audit_cursor', recent_pages+1)), total_pages)
        if not full:
            for _ in range(min(audit_pages, total_pages)):
                target.add(cursor)
                cursor = cursor % total_pages + 1
        # Follow new records past recent window, even after a long outage.
        queue = sorted(target)
        frontier = min(total_pages, recent_pages)
        signatures, observed = set(), {}
        for page in queue:
            rows, n = (first, total_pages) if page == 1 else parse_listing(client.get(list_url(menu, page)), menu, page, detail_loader=client.get)
            if n != total_pages:
                raise CollectionError('수집 도중 페이지 수 변경: 다음 실행에서 재시도')
            signature = tuple(r['id'] for r in rows)
            if signature in signatures:
                raise CollectionError('서로 다른 페이지에서 동일 목록 반환')
            signatures.add(signature)
            if not full and page == frontier and not any(r['id'] in old for r in rows) and page < total_pages:
                frontier += 1
                if frontier not in queue:
                    queue.append(frontier)
            for r in rows:
                if r['id'] in observed and observed[r['id']]['content_hash'] != r['content_hash']:
                    raise CollectionError('중복 식별자의 메타데이터 충돌')
                observed[r['id']] = r
            LOG.info('menu=%s page=%s/%s rows=%s', menu, page, total_pages, len(rows))
        # One detail sentinel per category verifies that listing fields match detail HTML.
        detail = parse_detail(client.get(first[0]['source_url']), allow_missing_reference=not first[0]['reference_raw'])
        if any(detail[k] != first[0][k] for k in detail):
            raise CollectionError(f'menu={menu}: 목록/상세 메타데이터 불일치')
        old_count = sum(r['menu'] == menu for r in old.values())
        if full and old_count and len(observed) < old_count * .9:
            raise CollectionError(f'menu={menu}: 전체 수집 건수 급감 {old_count} → {len(observed)}')
        for key, r in observed.items():
            core = {k: r[k] for k in ['date', 'title', 'speaker', 'reference_raw', 'reference']}
            if r['tid'] in observed_logical and observed_logical[r['tid']] != core:
                raise CollectionError(f'여러 분류의 같은 tid 메타데이터 충돌: {r["tid"]}')
            observed_logical[r['tid']] = core
            existing = old.get(key)
            changed = existing is not None and existing['content_hash'] != r['content_hash']
            r.update(first_collected_at=existing['first_collected_at'] if existing else stamp,
                     updated_at=stamp if changed or not existing else existing['updated_at'], last_seen_at=stamp)
            merged[key] = r
            stats['added'] += existing is None
            stats['changed'] += changed
            stats['observed'] += 1
        menu_meta[str(menu)] = {'total_pages': total_pages, 'audit_cursor': 1 if full else cursor,
                                'observed_count': len(observed), 'checked_pages': sorted(queue), 'checked_at': stamp}
    # tid identifies a shared detail page. Propagate confirmed corrections to its
    # cached category appearances without claiming those lists were re-fetched.
    for r in merged.values():
        if r['tid'] in observed_logical:
            r.update(observed_logical[r['tid']])
            new_hash = digest({k: r[k] for k in ['date', 'title', 'speaker', 'reference_raw', 'service']})
            if new_hash != r['content_hash']:
                r['content_hash'], r['updated_at'] = new_hash, stamp
    records = sorted(merged.values(), key=lambda r: (r['date'], int(r['tid']), r['menu']), reverse=True)
    stats['normalization_failed'] = sum(r['reference']['status'] != 'ok' for r in records)
    completed = now()
    result = {'schema_version': 1, 'meta': {'last_success_at': completed,
              'full_collected_at': completed if full else previous['meta']['full_collected_at'],
              'total': len(records), 'unique_total': len({r['tid'] for r in records}),
              'content_version': digest([(r['id'], r['content_hash']) for r in records]),
              'mode': 'full' if full else 'incremental', 'menus': menu_meta, 'policy': policy,
              'stats': stats, 'source': BASE, 'normalizer_version': 1}, 'sermons': records}
    validate_archive(result)
    return result


def atomic_save(path, data):
    validate_archive(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Previous bytes remain untouched on any crawl/validation error.
    if path.exists():
        previous = path.read_bytes()
        Path(str(path)+'.bak').write_bytes(previous)
    fd, tmp = tempfile.mkstemp(prefix=path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full', action='store_true', help='전체 목록 재검사; 기존 설교 자동 삭제 없음')
    p.add_argument('--output', type=Path, default=Path('sermons.json'))
    p.add_argument('--audit-pages', type=int, default=2)
    p.add_argument('--recent-pages', type=int, default=2)
    p.add_argument('--validate-only', action='store_true')
    args = p.parse_args()
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler('logs/scraper.log', encoding='utf-8')])
    try:
        if args.audit_pages < 1 or args.recent_pages < 1:
            raise CollectionError('점검 페이지 수는 1 이상이어야 합니다')
        previous = json.loads(args.output.read_text()) if args.output.exists() else empty_archive()
        if args.validate_only:
            validate_archive(previous)
            LOG.info('검증 성공: %s건', previous['meta']['total'])
            return 0
        client = Client()
        data = collect(client, previous, full=args.full, audit_pages=args.audit_pages, recent_pages=args.recent_pages)
        atomic_save(args.output, data)
        LOG.info('SUCCESS total=%s requests=%s stats=%s', data['meta']['total'], client.requests, data['meta']['stats'])
        return 0
    except Exception:
        LOG.exception('FAILED: 기존 JSON을 보존합니다')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
