import gzip, json, glob
import pandas as pd

# 1. export_data 폴더 내 모든 json.gz 파일 로드
records = []
file_list = glob.glob("./export_data/734177/**/*.json.gz", recursive=True)
print(f"[*] 총 {len(file_list)}개의 압축 파일을 불러옵니다...")

if not file_list:
    print("[경고] ./export_data/734177/ 폴더에 .json.gz 파일이 없습니다. 경로를 확인해 주세요.")
    exit()

for filepath in file_list:
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))

df = pd.DataFrame(records)
print(f"[*] 총 {len(df):,}건의 이벤트가 성공적으로 로드되었습니다.\n")

# 2. 날짜 컬럼 생성 (event_time 기준)
df['event_dt'] = pd.to_datetime(df['event_time']).dt.date

# 3. 2026-08-25 ~ 2026-10-10 일자별 이벤트 수 및 유저 수 집계
daily_check = df[(df['event_dt'] >= pd.to_datetime('2026-08-25').date()) & 
                 (df['event_dt'] <= pd.to_datetime('2026-10-10').date())]

summary = daily_check.groupby('event_dt').agg(
    total_events=('event_type', 'count'),
    unique_users=('amplitude_id', 'nunique'),
    unique_user_ids=('user_id', 'nunique')
)

# 4. 결과 출력
print("=== 일자별 데이터 점검 결과 ===")
print(summary.to_string())
