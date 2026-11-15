import argparse, hashlib, json, time
from pathlib import Path
H=lambda b:hashlib.sha256(b).digest()
def leaf(data):return H(b'\x00'+data)
def node(a,b):return H(b'\x01'+a+b)
def levels(items):
    layer=[leaf(x) for x in items] or [H(b'\x02')]
    out=[layer]
    while len(layer)>1:
        layer=[node(layer[i],layer[i+1] if i+1<len(layer) else layer[i]) for i in range(0,len(layer),2)]
        out.append(layer)
    return out
def root(items):return levels(items)[-1][0].hex()
def prove(items,index):
    if not 0<=index<len(items):raise ValueError('bad index')
    ls=levels(items);siblings=[];pos=index
    for layer in ls[:-1]:
        other=pos^1
        if other>=len(layer):other=pos
        siblings.append({'side':'left' if pos&1 else 'right','hash':layer[other].hex()})
        pos//=2
    return {'leaf_index':index,'tree_size':len(items),'siblings':siblings}
def verify(data,proof,expected):
    try:
        if set(proof)!={'leaf_index','tree_size','siblings'}:return False
        i=proof['leaf_index']; n=proof['tree_size']; siblings=proof['siblings']
        if type(i)!=int or type(n)!=int or n<1 or not 0<=i<n or type(siblings)!=list:return False
        height=(n-1).bit_length()
        if len(siblings)!=height:return False
        if not isinstance(expected,str) or len(expected)!=64 or bytes.fromhex(expected).hex()!=expected.lower():return False
        h=leaf(data)
        for s in siblings:
            if set(s)!={'side','hash'} or s['side'] not in ('left','right') or type(s['hash'])!=str or len(s['hash'])!=64:return False
            other=bytes.fromhex(s['hash']);side='left' if i&1 else 'right'
            if side!=s['side']:return False
            # odd final leaf is duplicated; direction must still be right
            if i^1>=n and other!=h:return False
            h=node(other,h) if side=='left' else node(h,other)
            i//=2;n=(n+1)//2
        return h.hex()==expected.lower()
    except (ValueError,TypeError,KeyError,AttributeError):return False

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    for a in ('root','prove'):
        q=sub.add_parser(a);q.add_argument('file',help='one UTF-8 transaction per line')
        if a=='prove':q.add_argument('index',type=int)
    q=sub.add_parser('verify');q.add_argument('leaf');q.add_argument('proof');q.add_argument('root')
    q=sub.add_parser('bench')
    a=p.parse_args()
    if a.action in ('root','prove'):
        items=Path(a.file).read_bytes().splitlines();ans={'root':root(items)} if a.action=='root' else prove(items,a.index)
    elif a.action=='verify':ans={'valid':verify(a.leaf.encode(),json.loads(Path(a.proof).read_text()),a.root)}
    else:
        ans=[]
        for count in (8,1024,100000):
            data=[str(i).encode() for i in range(count)];start=time.perf_counter();r=root(data);elapsed=time.perf_counter()-start
            proof=prove(data,count//2);ans.append({'leaves':count,'seconds':round(elapsed,4),'proof_json_bytes':len(json.dumps(proof).encode()),'verified':verify(data[count//2],proof,r)})
    print(json.dumps(ans,indent=2))
if __name__=='__main__':main()
