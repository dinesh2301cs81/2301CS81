from wallet import *

def test_sign_and_tamper():
 k=Ed25519PrivateKey.generate();pub=k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
 tx={'version':1,'network_id':NETWORK,'sender':address(pub),'recipient':address(pub),'amount_units':1250000,'nonce':7,'memo_hash':'0'*64}
 e=sign(tx,k);assert verify(e)
 assert not verify({**e,'tx':{**tx,'amount_units':1}})
 assert not verify({**e,'tx':{**tx,'network_id':'mainnet'}})
 seen=set();assert verify(e,seen);assert not verify(e,seen)
 assert validate_tx(tx)==validate_tx(dict(reversed(list(tx.items()))))
 assert decode_address(address(pub))
 bad=address(pub)[:-1]+'0';assert not verify({**e,'tx':{**tx,'recipient':bad}})
