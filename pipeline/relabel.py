"""Reuse an audited run with preserved strict labels; create a separate proxy-label run without raw reprocessing."""
import argparse, json, platform, shutil
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from layout import artifact
from proxy_labels import apply_to_run
from run import ROOT, dump, sha
from validate_outputs import audit


def check_reuse_config(old, new):
    keys = ['analysis_start', 'analysis_end_exclusive', 'reference_start', 'reference_end_inclusive',
            'reference_interval_days', 'windows_days', 'minimum_observed_history_days',
            'eligibility_recent_active_days', 'verified_collection_intervals', 'suspect_intervals',
            'feature_verified_intervals', 'late_upload_policy', 'label_upload_deadline_utc',
            'split_dates', 'personalization_min_active_days']
    changed = [k for k in keys if old.get(k) != new.get(k)]
    if changed:
        raise ValueError('Label-only reuse cannot change these settings; run full pipeline: ' + ', '.join(changed))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source_run', type=Path)
    p.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    args = p.parse_args()
    source = args.source_run.resolve()
    cfg = json.loads(args.config.read_text())
    source_cfg = json.loads(artifact(source, 'config.json').read_text())
    check_reuse_config(source_cfg, cfg)
    manifest = json.loads(artifact(source, 'audit_manifest.json').read_text())['sha256']
    for name, digest in manifest.items():
        if sha(source / name) != digest:
            raise ValueError('Source artifact changed: ' + name)
    out = ROOT / 'outputs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_proxy')
    shutil.copytree(source, out)
    # Rebuilt labels may invalidate a previous wide export or narrative report.
    shutil.rmtree(out / 'handoff', ignore_errors=True)
    for name in ['PREPROCESSING_REPORT.md', 'handoff_report.json']:
        artifact(out, name).unlink(missing_ok=True)
    print('기존 정제·Feature 재사용:', source.name, flush=True)
    # The parent run retains its historical code and config. This run records current stage code.
    shutil.rmtree(out / 'provenance' / 'code')
    (out / 'provenance' / 'code').mkdir()
    for script in Path(__file__).parent.glob('*.py'):
        shutil.copy2(script, artifact(out, script.name))
    for name in ['README.md', 'requirements.txt', 'requirements-tested.txt']:
        shutil.copy2(Path(__file__).with_name(name), artifact(out, name))
    dump(artifact(out, 'config.json'), cfg)
    lineage = {'stage': 'proxy_label_only', 'parent_run': str(source.relative_to(ROOT)),
               'parent_audit_manifest_sha256': sha(artifact(source, 'audit_manifest.json')),
               'parent_config_sha256': sha(artifact(source, 'config.json')),
               'parent_artifact_sha256': manifest,
               'packages': {'python': platform.python_version(), 'pandas': pd.__version__,
                            'numpy': np.__version__, 'scikit_learn': sklearn.__version__},
               'raw_reprocessing': False, 'feature_recalculation': False}
    dump(out / 'provenance' / 'lineage.json', lineage)
    report = apply_to_run(out, cfg)
    # Parent data and personalization artifacts are byte-for-byte unchanged.
    for name, digest in manifest.items():
        if name.startswith(('data/', 'personalization/')):
            assert sha(out / name) == digest
    audit(out)
    print(json.dumps(report['proxy_label_counts'], ensure_ascii=False), flush=True)
    print('완료:', out, flush=True)

if __name__ == '__main__':
    main()
