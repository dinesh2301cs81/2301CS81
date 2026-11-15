import argparse, base64, hashlib, json, unicodedata
from pathlib import Path

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(data):
    h=hashlib.sha256(data).digest()
    return {'bytes':len(data),'sha256':h.hex(),'base64':base64.b64encode(h).decode()}

def hash_file(path):
    h=hashlib.sha256(); n=0
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            n+=len(chunk);h.update(chunk)
    d=h.digest()
    return {'bytes':n,'sha256':d.hex(),'base64':base64.b64encode(d).decode()}

def avalanche(data, bit):
    if bit<0 or bit>=len(data)*8: raise ValueError('bit outside input')
    changed=bytearray(data);changed[bit//8]^=1<<(bit%8)
    x=hashlib.sha256(data).digest();y=hashlib.sha256(changed).digest()
    return {'original_sha256':x.hex(),'modified_sha256':y.hex(),'changed_bits_in_digest':sum((a^b).bit_count() for a,b in zip(x,y))}

def main():
    p=argparse.ArgumentParser(prog='hashlab'); sub=p.add_subparsers(dest='mode',required=True)
    for mode in ['text','hex','file','canonical-json']:
        sub.add_parser(mode).add_argument('value')
    a=sub.add_parser('avalanche');a.add_argument('--text',required=True);a.add_argument('--bit',type=int,required=True)
    a=sub.add_parser('demo')
    args=p.parse_args()
    if args.mode=='text': ans=digest(args.value.encode('utf-8'))
    elif args.mode=='hex':
        if len(args.value)%2: p.error('hex string length must be even')
        try: value=bytes.fromhex(args.value)
        except ValueError: p.error('malformed hex')
        ans=digest(value)
    elif args.mode=='file': ans=hash_file(args.value)
    elif args.mode=='canonical-json':
        obj=json.loads(Path(args.value).read_text(encoding='utf-8'))
        if not isinstance(obj,dict):p.error('root must be a JSON object')
        b=canonical(obj);ans={'canonical_utf8_hex':b.hex(),**digest(b)}
    elif args.mode=='avalanche':ans=avalanche(args.text.encode(),args.bit)
    else:
        cases={'LF':'hello\n','CRLF':'hello\r\n','é NFC':unicodedata.normalize('NFC','é'),'é NFD':unicodedata.normalize('NFD','é'), 'integer':canonical({'x':1}).decode(),'string':canonical({'x':'1'}).decode(),'keys AB':canonical({'a':1,'b':2}).decode(),'keys BA':canonical({'b':2,'a':1}).decode()}
        ans={k:digest(v.encode())['sha256'] for k,v in cases.items()}
    print(json.dumps(ans,indent=2))
if __name__=='__main__':main()
