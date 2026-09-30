"""Explicit opt-in only: one real search, announcement page and PDF download."""
from datetime import date, timedelta
import os

import pytest

from engine.bse_client import BSEClient
from engine.fetcher import ANN_URL, download_filing
from engine.models import Filing
from engine.resolver import resolve


@pytest.mark.skipif(os.environ.get('FF_LIVE') != '1', reason='live BSE test; set FF_LIVE=1 to run')
def test_live_heg_resolve_announcements_and_pdf():
    client = BSEClient()
    try:
        candidates = resolve('HEG', client)
        assert any(candidate.scrip_code == '509631' for candidate in candidates)
        today = date.today()
        rows = client.get_json(ANN_URL, {
            'strCat': '-1', 'subcategory': '-1', 'strSearch': 'P', 'strType': 'C',
            'strScrip': '509631', 'strPrevDate': (today - timedelta(days=365)).strftime('%Y%m%d'),
            'strToDate': today.strftime('%Y%m%d'), 'pageno': '1',
        })['Table']
        assert rows, 'HEG should have announcements within the last year'
        row = next(row for row in rows if row.get('ATTACHMENTNAME'))
        filing = Filing(news_id=str(row['NEWSID']), date=row['DissemDT'][:10],
                        headline=row.get('HEADLINE') or row.get('NEWSSUB') or 'HEG filing',
                        attachment=row['ATTACHMENTNAME'], folder='announcements', category='Announcements')
        pdf = download_filing(filing, client)
        assert pdf.startswith(b'%PDF-')
        print(f'HEG 509631 resolved; announcements page 1: {len(rows)} rows; PDF: {len(pdf):,} bytes, %PDF- verified')
    finally:
        client.close()
