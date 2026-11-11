"""Report observed event introductions without changing processed datasets."""
import gzip
import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

import pandas as pd

KST = timezone(timedelta(hours=9))
START, END = date(2025, 10, 8), date(2026, 10, 26)
ROOT = Path(__file__).resolve().parents[2]


def main():
    stats = {}
    seen = set()
    for path in sorted((ROOT / 'export_data/734177').rglob('*.json.gz')):
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():
                    continue
                event = json.loads(line)
                name, timestamp = event.get('event_type'), event.get('event_time')
                if not name or not timestamp or event.get('amplitude_id') is None:
                    continue
                dt = datetime.fromisoformat(timestamp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt = dt.astimezone(KST).replace(tzinfo=None)
                if not START <= dt.date() <= END:
                    continue
                uuid = event.get('uuid')
                if uuid is not None:
                    if uuid in seen:
                        continue
                    seen.add(uuid)
                version = str(event.get('version_name') or '(unknown)')
                platform = str(event.get('platform') or '(unknown)')
                if name not in stats:
                    stats[name] = {'first': dt, 'last': dt, 'count': 0, 'first_day_versions': set(), 'first_day_platforms': set()}
                s = stats[name]
                if dt.date() < s['first'].date():
                    s['first_day_versions'].clear()
                    s['first_day_platforms'].clear()
                s['first'] = min(s['first'], dt)
                s['last'] = max(s['last'], dt)
                s['count'] += 1
                if dt.date() == s['first'].date():
                    s['first_day_versions'].add(version)
                    s['first_day_platforms'].add(platform)
    clean = pd.read_parquet(ROOT / 'processed_kst/clean_events.parquet', columns=['event_type', 'event_time'])
    retained = clean.groupby('event_type').agg(first_retained_kst=('event_time', 'min'), retained_count=('event_time', 'size'))
    observed_start = min(s["first"].date() for s in stats.values())
    rows = []
    for name, s in stats.items():
        rows.append({'first_date_kst': str(s['first'].date()), 'event_type': name,
                     'first_time_kst': s['first'], 'last_time_kst': s['last'],
                     'first_day_app_versions': ', '.join(sorted(s['first_day_versions'])),
                     'first_day_platforms': ', '.join(sorted(s['first_day_platforms'])),
                     'raw_deduplicated_count': s['count'],
                     'observation_status': 'baseline' if s['first'].date() == observed_start else 'first_observed'})
    out = pd.DataFrame(rows).sort_values(['first_date_kst', 'event_type']).merge(retained, left_on='event_type', right_index=True, how='left')
    out['retained_count'] = out.retained_count.fillna(0).astype(int)
    report = ROOT / 'reports'
    report.mkdir(exist_ok=True)
    descriptions_path = report / 'event_descriptions_ko.json'
    descriptions = json.loads(descriptions_path.read_text(encoding='utf-8')) if descriptions_path.exists() else {}
    out['description_ko'] = out.event_type.map(descriptions).fillna('새 이벤트: 한국어 설명 확인 필요')
    out.to_csv(report / 'event_introductions.csv', index=False, encoding='utf-8-sig')
    lines = ['# 이벤트 최초 관측일 (KST)', '',
             '원본 분석 필터: 2025-10-08~2026-10-26. UUID 중복 제거 후 집계. 현재 전처리 파일은 변경하지 않음.',
             f'유효 원본 이벤트의 실제 관측 시작일: {observed_start}. 이 날짜의 이벤트는 초기 관측 목록으로 분류.',
             '날짜는 제공된 원본에서 처음 관측한 날짜이며 기능 출시일·앱 배포일을 확정하지 않음. 이름 변경·오탈자도 별도 이벤트로 표시.',
             '원본 최초 날짜에는 현재 제외한 이상 ID의 로그도 포함. CSV의 first_retained_kst는 현재 정제 데이터에서 처음 남아 있는 시각.',
             '앱 버전은 최초 관측일에 해당 이벤트를 기록한 버전 목록으로, 기능이 도입된 버전을 뜻하지 않음.', '',
             '한국어 설명은 이벤트 이름을 해석한 것으로, 수집 명세로 확정한 정의가 아님.', '']
    for day, group in out.groupby('first_date_kst', sort=True):
        label = day + (' (관측 시작 시 이미 존재)' if day == str(observed_start) else '')
        lines.extend([f'## {label} ({len(group)}개)', '', '| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |', '|---|---|---|'])
        for row in group.itertuples():
            lines.append(f'| `{row.event_type}` | {row.description_ko} | {row.first_day_app_versions} |')
        lines.append('')
    (report / 'event_introductions.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Event types:', len(out), 'first-observed dates:', out.first_date_kst.nunique())
    print(out.groupby('first_date_kst').event_type.agg(list).to_string())


if __name__ == '__main__':
    main()
