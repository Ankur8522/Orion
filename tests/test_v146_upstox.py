import hashlib, pytest
from orion.providers.upstox import UpstoxRequestBuilder, UpstoxNormalizer, RawEnvelope
from orion.data.pit_corpus import PITRecord, CorpusState, CorpusManifest

def test_upstox_historical_request_is_v3_and_encoded():
    url,_=UpstoxRequestBuilder().historical_candle('NSE_EQ|INE002A01018','days',1,'2026-09-25','2026-09-01')
    assert '/v3/historical-candle/NSE_EQ%7CINE002A01018/days/1/' in url

def test_quote_batch_limit_and_validation():
    with pytest.raises(ValueError): UpstoxRequestBuilder().full_quotes([])
    with pytest.raises(ValueError): UpstoxRequestBuilder().full_quotes(['BAD'])

def test_raw_envelope_hash():
    e=RawEnvelope.create('ohlcv','NSE_EQ|X',b'abc','2026-09-25T10:00:00Z','2026-09-25T10:01:00Z')
    assert e.payload_sha256==hashlib.sha256(b'abc').hexdigest()

def test_normalizer_preserves_available_time():
    rows=UpstoxNormalizer.candles({'data':{'candles':[['2026-09-25T10:00:00+05:30',1,2,0.5,1.5,100]]}},'NSE_EQ|X','2026-09-25T10:01:00Z')
    assert rows[0]['volume']==100 and rows[0]['available_time'].endswith('Z')

def test_pit_blocks_future_and_synthetic():
    r=PITRecord('X','ohlcv','2026-09-25T10:00:00Z','2026-09-25T10:01:00Z','2026-09-25T10:02:00Z','upstox',CorpusState.HISTORICAL_PIT,'a'*64)
    with pytest.raises(ValueError): r.validate('2026-09-25T10:00:30Z')
    s=PITRecord('X','ohlcv','2026-09-25T10:00:00Z','2026-09-25T10:00:00Z','2026-09-25T10:02:00Z','fixture',CorpusState.SYNTHETIC,'a'*64)
    with pytest.raises(ValueError): s.validate('2026-09-25T10:03:00Z')

def test_manifest_is_deterministic():
    r=PITRecord('X','ohlcv','2026-09-25T10:00:00Z','2026-09-25T10:00:00Z','2026-09-25T10:01:00Z','upstox',CorpusState.HISTORICAL_PIT,'a'*64)
    m=CorpusManifest('m1','2026-09-25T11:00:00Z',(r,))
    assert m.digest()==m.digest() and len(m.digest())==64
