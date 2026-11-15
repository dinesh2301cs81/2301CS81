import hashlib,json,time,copy,argparse
from dataclasses import dataclass
from ledger import Ledger,txid,outkey,MAX
ZERO='00'*32;SUBSIDY=50
sha=lambda x:hashlib.sha256(x).hexdigest()
def merkle(txs):
 h=[hashlib.sha256(b'\x00'+bytes.fromhex(txid(t))).digest() for t in txs]
 if not h:return hashlib.sha256(b'\x02').hexdigest()
 while len(h)>1:h=[hashlib.sha256(b'\x01'+h[i]+h[i+1 if i+1<len(h) else i]).digest() for i in range(0,len(h),2)]
 return h[0].hex()
def header(block):return {'version':block['version'],'previous':block['previous'],'root':block['root'],'timestamp':block['timestamp'],'target':block['target'],'nonce':block['nonce']}
def header_bytes(b):
 h=header(b)
 return (h['version'].to_bytes(4,'big')+bytes.fromhex(h['previous'])+bytes.fromhex(h['root'])+h['timestamp'].to_bytes(8,'big')+h['target'].to_bytes(32,'big')+h['nonce'].to_bytes(8,'big'))
def block_hash(b):return sha(header_bytes(b))
def work(target):return (1<<256)//(target+1)
def mine(previous,txs,target,timestamp=None):
 b={'version':1,'previous':previous,'root':merkle(txs),'timestamp':int(time.time()) if timestamp is None else timestamp,'target':target,'nonce':0,'txs':txs}
 start=time.perf_counter();count=0
 while True:
  count+=1
  if int(block_hash(b),16)<=target:break
  b['nonce']+=1
  if b['nonce']>=2**64:raise RuntimeError('nonce exhausted')
 return b,{'attempts':count,'seconds':time.perf_counter()-start}
def coinbase(owner,value,height):return {'coinbase':True,'height':height,'outputs':[{'value':value,'address':owner}]}
class Chain:
 def __init__(self,genesis_utxos=None):
  self.genesis=copy.deepcopy(genesis_utxos or {});self.blocks={};self.active_tip=ZERO;self.active=Ledger(self.genesis);self.score={ZERO:0};self.states={ZERO:copy.deepcopy(self.genesis)};self.heights={ZERO:0}
 def add(self,b):
  try:
   if set(b)!={'version','previous','root','timestamp','target','nonce','txs'}:raise ValueError('block fields')
   if b['version']!=1 or not isinstance(b['timestamp'],int) or b['timestamp']<0 or type(b['nonce'])!=int or not 0<=b['nonce']<2**64:raise ValueError('bad header')
   if type(b['target'])!=int or not 0<b['target']<(1<<256):raise ValueError('bad target')
   parent=b['previous'];bid=block_hash(b)
   if parent not in self.score:raise ValueError('unknown parent')
   if bid in self.blocks:raise ValueError('duplicate block')
   if int(bid,16)>b['target']:raise ValueError('invalid proof of work')
   if merkle(b['txs'])!=b['root']:raise ValueError('wrong Merkle root')
   if not b['txs'] or b['txs'][0].get('coinbase') is not True or any(t.get('coinbase') for t in b['txs'][1:]):raise ValueError('coinbase placement')
   height=self.heights[parent]+1;cb=b['txs'][0]
   if set(cb)!={'coinbase','height','outputs'} or cb['height']!=height or len(cb['outputs'])!=1:raise ValueError('invalid coinbase')
   out=cb['outputs'][0]
   from wallet import decode_address
   if set(out)!={'address','value'} or type(out['value'])!=int or not 0<out['value']<=MAX:raise ValueError('invalid coinbase output')
   decode_address(out['address'])
   state=Ledger(self.states[parent]);fee=0
   for tx in b['txs'][1:]:fee+=state.apply(tx)['fee']
   if out['value']>SUBSIDY+fee:raise ValueError('excess coinbase reward')
   reward_id=txid(cb);rk=outkey(reward_id,0)
   if rk in state.utxos:raise ValueError('duplicate coinbase')
   state.utxos[rk]=dict(out)
   self.blocks[bid]=copy.deepcopy(b);self.states[bid]=state.snapshot();self.score[bid]=self.score[parent]+work(b['target']);self.heights[bid]=height
   reorg=False
   if self.score[bid]>self.score[self.active_tip]:
    reorg=(self.active_tip!=ZERO and parent!=self.active_tip)
    self.active_tip=bid;self.active=Ledger(state.snapshot())
   return {'hash':bid,'height':height,'cumulative_work':self.score[bid],'active':bid==self.active_tip,'reorg':reorg}
  except (KeyError,OverflowError,TypeError,AttributeError) as e:raise ValueError(f'malformed block: {e}') from e
 def path(self,tip):
  p=[]
  while tip!=ZERO:p.append(tip);tip=self.blocks[tip]['previous']
  return p[::-1]
def fork_demo(owner):
 easy=(1<<252)-1;hard=(1<<250)-1;c=Chain()
 a1,_=mine(ZERO,[coinbase(owner,50,1)],easy);ra1=c.add(a1)
 a2,_=mine(ra1['hash'],[coinbase(owner,50,2)],easy);ra2=c.add(a2)
 b1,_=mine(ZERO,[coinbase(owner,50,1)],hard);rb1=c.add(b1)
 print(json.dumps({'easy_branch':[ra1,ra2],'hard_branch':rb1,'winner':c.active_tip,'active_utxos':c.active.snapshot()},indent=2));return c

def benchmark(owner):
 out=[]
 for bits in (4,6,8):
  target=(1<<(256-bits))-1
  b,m=mine(ZERO,[coinbase(owner,50,1)],target)
  out.append({'leading_zero_bits':bits,'expected_attempts':2**bits,'observed_attempts':m['attempts'],'hashes_per_second':round(m['attempts']/max(m['seconds'],1e-9)),'header_hex':header_bytes(b).hex()})
 return out
if __name__=='__main__':
 from wallet import Ed25519PrivateKey,address
 from ledger import pub_bytes
 p=argparse.ArgumentParser();p.add_argument('command',choices=['fork','bench']);a=p.parse_args()
 owner=address(pub_bytes(Ed25519PrivateKey.generate()))
 if a.command=='fork':fork_demo(owner)
 else:print(json.dumps(benchmark(owner),indent=2))
