import argparse, hashlib, json, os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
ABC='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
NETWORK='course-testnet';VERSION=b'\x6f';MAX=2**63-1

def sha(x):return hashlib.sha256(x).digest()
def b58encode(data):
 n=int.from_bytes(data,'big');s=''
 while n:n,r=divmod(n,58);s=ABC[r]+s
 return '1'*(len(data)-len(data.lstrip(b'\x00')))+(s or '')
def b58decode(s):
 n=0
 for c in s:
  if c not in ABC:raise ValueError('non-base58 character')
  n=n*58+ABC.index(c)
 b=n.to_bytes((n.bit_length()+7)//8,'big') if n else b''
 return b'\x00'*(len(s)-len(s.lstrip('1')))+b
def address(pub):
 body=VERSION+hashlib.new('ripemd160',sha(pub)).digest();return b58encode(body+sha(sha(body))[:4])
def decode_address(s):
 raw=b58decode(s)
 if len(raw)!=25 or raw[:1]!=VERSION or raw[-4:]!=sha(sha(raw[:-4]))[:4]:raise ValueError('invalid address or checksum')
 return raw[1:21]
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def validate_tx(tx):
 fields={'version','network_id','sender','recipient','amount_units','nonce','memo_hash'}
 if type(tx)!=dict or set(tx)!=fields:raise ValueError('wrong transaction fields')
 if type(tx['version'])!=int or tx['version']!=1 or tx['network_id']!=NETWORK:raise ValueError('wrong network or version')
 if type(tx['amount_units'])!=int or not 0<tx['amount_units']<=MAX:raise ValueError('invalid amount')
 if type(tx['nonce'])!=int or not 0<=tx['nonce']<=MAX:raise ValueError('invalid nonce')
 for key in ('sender','recipient'):decode_address(tx[key])
 if type(tx['memo_hash'])!=str or len(tx['memo_hash'])!=64 or shahex_valid(tx['memo_hash']) is False:raise ValueError('invalid memo hash')
 return canon(tx)
def shahex_valid(s):
 try:return bytes.fromhex(s).hex()==s
 except ValueError:return False
def save_key(path):
 key=Ed25519PrivateKey.generate()
 data=key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())
 flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
 fd=os.open(path,flags,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data)
 return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
def pub_from_private(path):
 key=Ed25519PrivateKey.from_private_bytes(Path(path).read_bytes())
 return key,key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
def sign(tx,key):return {'tx':tx,'public_key':key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex(),'signature':key.sign(validate_tx(tx)).hex()}
def verify(envelope,used_nonces=None):
 try:
  if set(envelope)!={'tx','public_key','signature'}:return False
  tx=envelope['tx'];pub=bytes.fromhex(envelope['public_key']);sig=bytes.fromhex(envelope['signature'])
  if len(pub)!=32 or len(sig)!=64 or tx['sender']!=address(pub):return False
  b=validate_tx(tx);Ed25519PublicKey.from_public_bytes(pub).verify(sig,b)
  if used_nonces is not None:
   unique=(tx['sender'],tx['nonce'])
   if unique in used_nonces:return False
   used_nonces.add(unique)
  return True
 except Exception:return False

def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
 q=s.add_parser('keygen');q.add_argument('private_file')
 q=s.add_parser('address');q.add_argument('private_file')
 q=s.add_parser('sign');q.add_argument('private_file');q.add_argument('tx_json');q.add_argument('output_json')
 q=s.add_parser('verify');q.add_argument('signed_json')
 a=p.parse_args()
 if a.cmd=='keygen':
  pub=save_key(a.private_file);print('WARNING: DEVELOPMENT KEY ONLY — NEVER USE FOR REAL FUNDS');print(json.dumps({'public_key':pub.hex(),'address':address(pub)}))
 elif a.cmd=='address':
  _,pub=pub_from_private(a.private_file);print(json.dumps({'public_key':pub.hex(),'address':address(pub)}))
 elif a.cmd=='sign':
  key,_=pub_from_private(a.private_file);env=sign(json.loads(Path(a.tx_json).read_text()),key)
  Path(a.output_json).write_text(json.dumps(env,indent=2));print('signed',a.output_json)
 else:print(json.dumps({'valid':verify(json.loads(Path(a.signed_json).read_text()))}))
if __name__=='__main__':main()
