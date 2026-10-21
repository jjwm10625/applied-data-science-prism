"""Export one wide, uncompressed CSV for the modeling teammate; no feature recalculation."""
import argparse
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from layout import artifact
from run import sha, dump


def export(run_dir):
    roles = json.loads(artifact(run_dir, 'feature_roles.json').read_text())
    target = roles.get('modeling_target', 'label_churn_7d')
    model_names = roles['numeric_candidates'] + roles['categorical_candidates']
    assert not any(c.startswith('label_') for c in model_names)
    shared = ['user_key', 'reference_date', target, 'split']
    parts = []
    inputs = {}
    by_window = {}
    quality_by_window = {}
    checks = {}
    dictionaries = []
    dictionary = pd.read_csv(artifact(run_dir, 'column_dictionary.csv'))
    descriptions = dictionary[dictionary.table.eq('features')].set_index('column').description.to_dict()
    base = None
    for w in [7, 14, 21, 28]:
        source = artifact(run_dir, f'features_{w}d_labeled.csv.gz')
        inputs[str(source.relative_to(run_dir))] = sha(source)
        frame = pd.read_csv(source, float_precision='round_trip')
        if frame.duplicated(['user_key', 'reference_date']).any():
            raise ValueError('Duplicate user/reference-date rows')
        if frame[target].isna().any() or not frame[target].isin([0, 1]).all():
            raise ValueError('Modeling export requires nonmissing binary target')
        assert frame.window_days.eq(w).all()
        if base is None:
            base = frame[shared].copy()
            parts.append(base)
            for c in shared:
                dictionaries.append({'column': c, 'role': 'target' if c == target else 'management',
                                     'window_days': '', 'description': descriptions.get(c, c)})
        else:
            pd.testing.assert_frame_equal(base, frame[shared], check_exact=True)
        t = pd.to_datetime(frame.reference_date).dt.tz_localize('Asia/Seoul')
        max_time = pd.to_datetime(frame.feature_max_event_time_utc, utc=True, format='mixed')
        assert (max_time.isna() | (max_time < t)).all()
        quality = ['unconfirmed_record_days', 'no_record_days', 'collection_verified_days', 'collection_unverified_days']
        quality += [c for c in frame if c.endswith('_coverage_verified')]
        for names, prefix, role in [(model_names, f'w{w}__', 'model_candidate'),
                                    (quality, f'q{w}__', 'quality_not_default_model_input')]:
            rename = {c: prefix + c for c in names}
            parts.append(frame[names].rename(columns=rename))
            for c in names:
                dictionaries.append({'column': rename[c], 'role': role, 'window_days': w,
                                     'description': descriptions.get(c, c)})
            if role == 'model_candidate':
                by_window[str(w)] = list(rename.values())
            else:
                quality_by_window[str(w)] = list(rename.values())
        checks[str(w)] = {'rows': len(frame), 'candidate_features': len(model_names),
                           'quality_columns': len(quality), 'feature_max_time_before_T': True}
    wide = pd.concat(parts, axis=1)
    assert not wide.columns.duplicated().any()
    assert len(wide) == len(base)
    assert not np.isinf(wide.select_dtypes(include='number').to_numpy()).any()
    destination = run_dir / 'handoff'
    destination.mkdir(exist_ok=True)
    path = destination / 'modeling_dataset.csv'
    wide.to_csv(path, index=False, encoding='utf-8-sig')
    reloaded = pd.read_csv(path, float_precision='round_trip')
    pd.testing.assert_frame_equal(wide, reloaded, check_exact=True)
    pd.DataFrame(dictionaries).to_csv(destination / 'column_dictionary.csv', index=False, encoding='utf-8-sig')
    export_roles = {'target': target, 'management': [c for c in shared if c != target],
                    'model_columns_by_window': by_window, 'quality_columns_by_window': quality_by_window,
                    'definition': roles.get('target_definition', ''),
                    'missing_values': 'Do not fill missing feature counts with zero without modeling justification.'}
    dump(destination / 'feature_roles.json', export_roles)
    zero, one = int(wide[target].eq(0).sum()), int(wide[target].eq(1).sum())
    readme = f'''# 모델링 담당자 전달 파일

주 데이터는 **modeling_dataset.csv 한 파일**입니다. UTF-8 BOM CSV이고 pandas에서 바로 읽을 수 있습니다.

- {len(wide):,}행 × {len(wide.columns)}열. 한 행 = 가명 사용자 키 하나 × KST 00:00 기준일 하나.
- 정답: `{target}`. 0={zero:,}행, 1={one:,}행. 미확정 라벨과 분할 경계 제외 대상은 원본 전체 테이블에 보존하고 이 파일에서는 제외했습니다.
- `w7__`, `w14__`, `w21__`, `w28__`: 각 관찰 기간의 모델 입력 후보 {len(model_names)}개씩.
- `q7__`, `q14__`, `q21__`, `q28__`: 관측 품질 정보. 기본 모델 입력에서 제외합니다.
- `user_key`, `reference_date`, `split`: 관리 정보이며 모델 입력에서 제외합니다.
- 기능별 결측은 수집 여부가 확인되지 않은 0 등을 포함합니다. 실제 미사용 0으로 일괄 바꾸지 마세요.

{roles.get('target_definition', '')}

기간 비교 시 같은 행과 같은 시간 분할을 사용하고, **해당 기간의 w 접두사 컬럼만** 선택하세요. 120개 후보를 한꺼번에 사용한 모델은 7·14·21·28일별 비교 실험이 아닙니다. recency는 T 이전 전체 이력의 마지막 접속 확인을 사용하므로 기간별 값이 같을 수 있습니다.

```python
import json
import pandas as pd

df = pd.read_csv("modeling_dataset.csv")
with open("feature_roles.json", encoding="utf-8") as f:
    roles = json.load(f)

window = "7"  # "14", "21", "28"로 바꾸어 같은 표본을 비교
X = df[roles["model_columns_by_window"][window]]
y = df[roles["target"]]
# 날짜 합의 후 시간순 train/validation/test 분할 및 라벨 구간 겹침 제외.
# imputer/encoder/scaler는 train에만 fit. 이 예시는 학습하지 않습니다.
```

현재 `split=not_configured`이면 최종 분할 전입니다. reference_date를 기준으로 팀이 합의한 날짜에 분할하고, 앞 구간의 T+7일이 다음 구간 시작을 넘는 행은 제외하세요. 무작위 행 분할을 기본값으로 쓰지 마세요.

Feature는 기존 retrospective_snapshot 기준입니다. 서버에 T 이후 도착한 과거 행동이 포함될 수 있으므로 당시 가용성 평가와 구분해야 합니다. 실제 미접속이 확인된 정답으로 성능을 주장하지 마세요.

feature_roles.json은 입력 변수 선택에, column_dictionary.csv는 컬럼 의미 확인에 사용합니다. 정제 이벤트는 ../data/, 전체 표본과 기간별 원래 파일은 ../features/, 검증·라벨 근거는 ../reports/에 있습니다.
'''
    (destination / 'README.md').write_text(readme, encoding='utf-8')
    shutil.copy2(__file__, artifact(run_dir, 'export_modeling_csv.py'))
    report = {'rows': len(wide), 'columns': len(wide.columns), 'model_columns_per_window': len(model_names),
              'users': int(wide.user_key.nunique()), 'reference_dates': int(wide.reference_date.nunique()),
              'reference_start': wide.reference_date.min(), 'reference_end': wide.reference_date.max(),
              'target': target, 'label_counts': {'0': zero, '1': one},
              'input_sha256': inputs, 'output_sha256': sha(path), 'csv_bytes': path.stat().st_size,
              'window_checks': checks, 'shared_keys_labels_splits_equal': True,
              'csv_round_trip_values_equal': True, 'recomputed_features': False}
    dump(artifact(run_dir, 'handoff_report.json'), report)
    # Refresh the final run manifest to include the new handoff, without changing source data.
    manifest = artifact(run_dir, 'audit_manifest.json')
    old = json.loads(manifest.read_text())
    for name, digest in old['sha256'].items():
        if name.startswith('handoff/') or name in {str(artifact(run_dir, 'handoff_report.json').relative_to(run_dir)), 'provenance/code/export_modeling_csv.py'}:
            continue
        assert sha(run_dir / name) == digest, name
    old['sha256'] = {str(p.relative_to(run_dir)): sha(p) for p in run_dir.rglob('*')
                     if p.is_file() and p.name != 'audit_manifest.json'}
    dump(manifest, old)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return path

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_directory', type=Path)
    args = p.parse_args()
    print('단일 CSV:', export(args.run_directory.resolve()))
