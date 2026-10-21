"""Explicit feature list only. No training/evaluation and no implicit fitting."""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def make_preprocessor(numeric, categorical=(), scale=False):
    forbidden = {'user_key', 'device_key', 'reference_date', 'label_churn_7d',
                 'label_status', 'label_reason', 'split'}
    if forbidden.intersection([*numeric, *categorical]) or any(c.startswith('label_') for c in [*numeric, *categorical]):
        raise ValueError('관리용/정답 컬럼은 입력 변수로 사용할 수 없습니다.')
    if set(numeric).intersection(categorical):
        raise ValueError('숫자/범주형 목록이 겹칩니다.')
    num = [('impute', SimpleImputer(strategy='median', add_indicator=True,
                                   keep_empty_features=True))]
    if scale:
        num.append(('scale', StandardScaler()))
    return ColumnTransformer([
        ('numeric', Pipeline(num), list(numeric)),
        ('categorical', Pipeline([
            ('impute', SimpleImputer(strategy='constant', fill_value='unknown')),
            ('encode', OneHotEncoder(handle_unknown='ignore')),
        ]), list(categorical)),
    ], remainder='drop')


def transform_splits(train, validation, test, numeric, categorical=(), scale=False):
    """Caller supplies agreed temporal splits; fit exclusively on train."""
    if train.empty:
        raise ValueError('학습 표본이 없습니다. 수집 신뢰성/라벨/시간 분할을 확인하세요.')
    transformer = make_preprocessor(numeric, categorical, scale)
    return (transformer, transformer.fit_transform(train),
            transformer.transform(validation), transformer.transform(test))
