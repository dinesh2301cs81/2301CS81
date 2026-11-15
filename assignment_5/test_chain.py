from chain import *
from wallet import Ed25519PrivateKey,address
from ledger import pub_bytes
import copy,pytest
@pytest.fixture
def owner():return address(pub_bytes(Ed25519PrivateKey.generate()))
def test_fork(owner):
 c=Chain();easy=(1<<252)-1;hard=(1<<250)-1
 a,_=mine(ZERO,[coinbase(owner,50,1)],easy);aa=c.add(a)
 b,_=mine(aa['hash'],[coinbase(owner,50,2)],easy);bb=c.add(b)
 d,_=mine(ZERO,[coinbase(owner,50,1)],hard);dd=c.add(d)
 assert c.active_tip==dd['hash'] and dd['reorg'] and len(c.active.utxos)==1
 assert c.score[dd['hash']]>c.score[bb['hash']]
def test_invalid_pow(owner):
 c=Chain();b,_=mine(ZERO,[coinbase(owner,50,1)],(1<<250)-1)
 b['nonce']+=1
 if int(block_hash(b),16)<=b['target']:b['target']=1
 before=c.active.snapshot()
 with pytest.raises(ValueError):c.add(b)
 assert c.active.snapshot()==before
def test_bad_root(owner):
 c=Chain();b,_=mine(ZERO,[coinbase(owner,50,1)],(1<<254)-1);b['root']='0'*64
 with pytest.raises(ValueError):c.add(b)
def test_coinbase(owner):
 c=Chain();b,_=mine(ZERO,[coinbase(owner,51,1)],(1<<254)-1)
 with pytest.raises(ValueError,match='excess'):c.add(b)
