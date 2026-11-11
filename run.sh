#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -c 'import sys; sys.exit("Python 3.9 이상이 필요합니다.") if sys.version_info < (3, 9) else None'
python3 - <<'PY'
from pathlib import Path
if next(Path("export_data/734177").rglob("*.json.gz"), None) is None:
    raise SystemExit("export_data/734177/에 원본 *.json.gz 파일을 배치하세요.")
PY

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt

for step in \
    preprocess \
    build_churn_features \
    build_notification_features \
    add_weekday_hours \
    validate_features \
    validate_behavior_union; do
    printf '\n>>> %s\n' "$step"
    .venv/bin/python "src/preprocessing/${step}.py"
done

printf '\n완료: processed_kst/에서 결과를 확인하세요.\n'
