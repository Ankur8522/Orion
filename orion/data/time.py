from datetime import datetime, timezone

def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    try:
        dt=datetime.fromisoformat(value[:-1]+'+00:00')
    except ValueError as e:
        raise ValueError('INVALID_TIMESTAMP') from e
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    return dt
