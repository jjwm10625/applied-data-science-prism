"""Stable artifact layout shared by generation, validation and folder migration."""
from pathlib import Path


def artifact(run_dir, name):
    """Resolve an artifact name without creating directories during reads."""
    name = str(name)
    if name == 'README.md':
        folder = ''
    elif name in {'events_clean.csv.gz', 'user_daily_activity.csv.gz'}:
        folder = 'data'
    elif name.startswith('features_') or name == 'feature_roles.json':
        folder = 'features'
    elif name == 'personalization_profiles.csv.gz':
        folder = 'personalization'
    elif name.endswith('.py'):
        folder = 'provenance/code'
    elif name in {'config.json', 'requirements.txt', 'requirements-tested.txt',
                  'legacy_policy.json', 'audit_manifest.json', 'enrichment.sqlite'}:
        folder = 'provenance'
    elif name in {'DATA_QUALITY.md', 'PREPROCESSING_REPORT.md'}:
        folder = 'reports'
    elif name in {'column_dictionary.csv', 'event_mapping.csv'}:
        folder = 'reports/schema'
    elif name.endswith(('.csv', '.csv.gz')):
        folder = 'reports/quality'
    else:
        folder = 'reports/validation'
    return Path(run_dir) / folder / name


def prepare_run(run_dir):
    for folder in ['data', 'features', 'personalization', 'reports', 'reports/schema', 'reports/quality', 'reports/validation', 'provenance/code']:
        (Path(run_dir) / folder).mkdir(parents=True, exist_ok=True)
