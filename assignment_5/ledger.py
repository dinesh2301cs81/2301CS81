"""Toy UTXO ledger. All values are unsigned 63-bit units. For classroom use."""
import hashlib, json, argparse
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from wallet import address,decode_address,canon,Ed25519PrivateKey,serialization
MAX=2**63-1
sha=lambda x:hashlib.sha256(x).hexdigest()
def signable(tx,index):
 return canon({'version':tx['version'],'inputs':[{'txid':x['txid'],'index':x['index'],'public_key':x['public_key']} for x in tx['inputs']],'outputs':tx['outputs'],'signing_input':index})
def txid(tx):return sha(canon(tx))
def outkey(txid,index):return f'{txid}:{index}'
class Ledger:
 def __init__(self,utxos=None):self.utxos=dict(utxos or {})
 def snapshot(self):return json.loads(json.dumps(self.utxos,sort_keys=True))
 def mint_for_demo(self,owner,value,seed):
  decode_address(owner)
  if type(value)!=int or not 0<value<=MAX:raise ValueError('bad mint')
  k=outkey(sha(f'demo genesis {seed}'.encode()),0)
  if k in self.utxos:raise ValueError('duplicate genesis')
  self.utxos[k]={'value':value,'address':owner};return k
 def validate(self,tx):
  if type(tx)!=dict or set(tx)!={'version','inputs','outputs'} or tx['version']!=1:raise ValueError('invalid transaction format')
  if not isinstance(tx['inputs'],list) or not tx['inputs'] or not isinstance(tx['outputs'],list) or not tx['outputs']:raise ValueError('empty inputs/outputs')
  seen=set();incoming=0;outgoing=0
  for ix,item in enumerate(tx['inputs']):
   if type(item)!=dict or set(item)!={'txid','index','public_key','signature'}:raise ValueError('bad input')
   tid=item['txid'];j=item['index']
   if type(tid)!=str or len(tid)!=64 or type(j)!=int or j<0:raise ValueError('bad outpoint')
   try:bytes.fromhex(tid)
   except ValueError:raise ValueError('bad outpoint')
   k=outkey(tid,j)
   if k in seen:raise ValueError('duplicate input')
   seen.add(k)
   if k not in self.utxos:raise ValueError('missing or already spent input')
   old=self.utxos[k]
   try:
    pub=bytes.fromhex(item['public_key']);sig=bytes.fromhex(item['signature'])
    if len(pub)!=32 or len(sig)!=64 or address(pub)!=old['address']:raise ValueError('wrong signer')
    Ed25519PublicKey.from_public_bytes(pub).verify(sig,signable(tx,ix))
   except Exception:raise ValueError('bad signature or wrong signer')
   incoming+=old['value']
   if incoming>MAX:raise ValueError('input arithmetic overflow')
  for o in tx['outputs']:
   if type(o)!=dict or set(o)!={'value','address'} or type(o['value'])!=int or not 0<o['value']<=MAX:raise ValueError('invalid output')
   decode_address(o['address']);outgoing+=o['value']
   if outgoing>MAX:raise ValueError('output arithmetic overflow')
  if incoming<outgoing:raise ValueError('outputs exceed inputs')
  return incoming-outgoing
 def apply(self,tx):
  fee=self.validate(tx);t=txid(tx)
  updates=self.utxos.copy()
  for i in tx['inputs']:del updates[outkey(i['txid'],i['index'])]
  for j,o in enumerate(tx['outputs']):updates[outkey(t,j)]=dict(o)
  self.utxos=updates
  return {'txid':t,'fee':fee}
 def save(self,path):Path(path).write_text(json.dumps(self.utxos,sort_keys=True,indent=2))
 @classmethod
 def load(cls,path):
  obj=json.loads(Path(path).read_text())
  if not isinstance(obj,dict):raise ValueError('invalid snapshot')
  for k,v in obj.items():
   if type(k)!=str or ':' not in k or type(v)!=dict or set(v)!={'value','address'} or type(v['value'])!=int or not 0<v['value']<=MAX:raise ValueError('invalid snapshot record')
   decode_address(v['address'])
  return cls(obj)
def pub_bytes(key):return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
def build_payment(ledger,key,recipient,amount,fee):
 if type(amount)!=int or type(fee)!=int or amount<=0 or fee<0 or amount+fee>MAX:raise ValueError('bad amount/fee')
 decode_address(recipient);own=address(pub_bytes(key));selected=[];total=0
 # deterministic largest-first, tie-break by outpoint string
 for k,v in sorted(ledger.utxos.items(),key=lambda kv:(-kv[1]['value'],kv[0])):
  if v['address']!=own:continue
  selected.append(k);total+=v['value']
  if total>=amount+fee:break
 if total<amount+fee:raise ValueError('insufficient funds')
 ins=[]
 for k in selected:
  tid,idx=k.rsplit(':',1);ins.append({'txid':tid,'index':int(idx),'public_key':pub_bytes(key).hex(),'signature':''})
 outs=[{'value':amount,'address':recipient}]
 if total>amount+fee:outs.append({'value':total-amount-fee,'address':own})
 tx={'version':1,'inputs':ins,'outputs':outs}
 for ix in range(len(ins)):ins[ix]['signature']=key.sign(signable(tx,ix)).hex()
 return tx

def demo():
 alice=Ed25519PrivateKey.generate();bob=Ed25519PrivateKey.generate();ledger=Ledger()
 ledger.mint_for_demo(address(pub_bytes(alice)),40,'a');ledger.mint_for_demo(address(pub_bytes(alice)),70,'b')
 tx=build_payment(ledger,alice,address(pub_bytes(bob)),85,2)
 print('BEFORE',json.dumps(ledger.snapshot(),indent=2));print('ACCEPT',ledger.apply(tx))
 print('AFTER',json.dumps(ledger.snapshot(),indent=2))
 try:ledger.apply(tx)
 except ValueError as e:print('REJECT duplicate spend:',str(e))
 return ledger
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot');a=p.parse_args();ledger=demo()
 if a.snapshot:ledger.save(a.snapshot)
