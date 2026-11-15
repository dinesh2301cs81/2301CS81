import copy,pytest
from ledger import *
@pytest.fixture
def state():
 a=Ed25519PrivateKey.generate();b=Ed25519PrivateKey.generate();l=Ledger();l.mint_for_demo(address(pub_bytes(a)),40,'a');l.mint_for_demo(address(pub_bytes(a)),70,'b');return l,a,b

def test_expected(state):
 l,a,b=state;t=build_payment(l,a,address(pub_bytes(b)),85,2)
 assert l.apply(t)['fee']==2
 assert sorted(x['value'] for x in l.utxos.values())==[23,85]
 with pytest.raises(ValueError,match='missing or already spent'):l.apply(t)
@pytest.mark.parametrize('mutation',[
 lambda t:t['outputs'][0].update(value=111),
 lambda t:t['outputs'][0].update(value=-1),
 lambda t:t['outputs'][0].update(value=0),
 lambda t:t['outputs'][0].update(value=2**63),
 lambda t:t['inputs'][0].update(signature='00'*64),
 lambda t:t['inputs'][0].update(public_key='00'*32),
 lambda t:t['inputs'][0].update(txid='0'*64),
 lambda t:t['inputs'][0].update(index=4),
 lambda t:t['inputs'].append(copy.deepcopy(t['inputs'][0])),
 lambda t:t['outputs'].append({'value':100,'address':t['outputs'][0]['address']}),
 lambda t:t['outputs'][0].update(address='bad'),
 lambda t:t.update(version=2),
 lambda t:t.update(outputs=[]),
 lambda t:t.update(inputs=[]),
 lambda t:t['inputs'][0].update(txid='nothex'),
 lambda t:t['inputs'][0].update(signature='garbage'),
 lambda t:t['outputs'][0].update(value=True),
 lambda t:t['outputs'][0].update(value=2**64),
 lambda t:t['outputs'][0].update(value='85'),
 lambda t:t['inputs'][0].update(index=-1),
])
def test_invalid_atomic(state,mutation):
 l,a,b=state;t=build_payment(l,a,address(pub_bytes(b)),85,2);before=l.snapshot();mutation(t)
 with pytest.raises(ValueError):l.apply(t)
 assert before==l.snapshot()
def test_persistence(state,tmp_path):
 l,a,b=state;p=tmp_path/'snapshot.json';l.save(p);assert Ledger.load(p).snapshot()==l.snapshot()
def test_insufficient(state):
 l,a,b=state
 with pytest.raises(ValueError,match='insufficient'):build_payment(l,a,address(pub_bytes(b)),111,0)
