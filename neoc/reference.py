"""Independent, bounded reference semantics for the safe pure language.

No LLVM, optimization pass, constant folder or range-analysis implementation is
used here. This is a correctness oracle and a development tool, not a runtime.
"""
import copy
import math
from . import syntax as S

MIN=-(1<<63);MAX=(1<<63)-1

class Fault(Exception):pass

def integer(value):
    if not MIN<=value<=MAX:raise Fault('integer overflow')
    return value

def wrapping(value):return (value+(1<<63))%(1<<64)-(1<<63)

class Reference:
    def __init__(self,program,budget=1000000):self.functions={f.name:f for f in program.fns};self.budget=budget
    def call(self,name,args):
        f=self.functions[name]
        if f.effect or f.external:raise Fault('effects are outside the pure reference evaluator')
        env={p.name:copy.deepcopy(a) for p,a in zip(f.params,args)}
        for p,a in zip(f.params,args):
            if isinstance(p.ty,S.TArr):
                size=p.ty.size
                if isinstance(size,str) and size!='_':env[size]=len(a)
        for name,carrier in getattr(f,'size_binders',[]):env[name]=len(env[carrier])
        return self.evaluate(f.body,env)
    def evaluate(self,node,env):
        self.budget-=1
        if self.budget<0:raise Fault('reference step budget')
        if isinstance(node,(S.Num,S.Flt,S.BoolLit,S.Byte)):return node.value
        if isinstance(node,S.Str):return list(node.value)
        if isinstance(node,S.Var):return env[node.name]
        if isinstance(node,S.Bin):
            a=self.evaluate(node.left,env)
            if node.op=='&&':return a and self.evaluate(node.right,env)
            if node.op=='||':return a or self.evaluate(node.right,env)
            b=self.evaluate(node.right,env);floating=isinstance(a,float) or isinstance(b,float)
            if node.op=='+':return a+b if floating else integer(a+b)
            if node.op=='-':return a-b if floating else integer(a-b)
            if node.op=='*':return a*b if floating else integer(a*b)
            if node.op in ('/','%'):
                if not b:raise Fault('division by zero')
                if floating:return a/b
                if a==MIN and b==-1:raise Fault('integer division overflow')
                quotient=(abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1)
                return quotient if node.op=='/' else a-quotient*b
            return {'==':a==b,'!=':a!=b,'<':a<b,'<=':a<=b,'>':a>b,'>=':a>=b}[node.op]
        if isinstance(node,S.Un):
            value=self.evaluate(node.expr,env)
            return not value if node.op=='!' else -value if isinstance(value,float) else integer(-value)
        if isinstance(node,S.Let):
            child=dict(env);child[node.name]=self.evaluate(node.value,env);return self.evaluate(node.body,child)
        if isinstance(node,S.If):return self.evaluate(node.then if self.evaluate(node.cond,env) else node.els,env)
        if isinstance(node,S.Len):return len(self.evaluate(node.expr,env))
        if isinstance(node,S.Index):
            value=self.evaluate(node.arr,env);index=self.evaluate(node.idx,env)
            if not 0<=index<len(value):raise Fault('array index out of range')
            return copy.deepcopy(value[index])
        if isinstance(node,S.Cast):
            value=self.evaluate(node.expr,env)
            if node.to==S.F64:return float(value)
            if node.to==S.U8:return int(value)%256
            if node.to==S.U16:return int(value)%65536
            if node.to==S.I32:return (int(value)+(1<<31))%(1<<32)-(1<<31)
            if isinstance(value,float) and (not math.isfinite(value) or not MIN<=value<(1<<63)):raise Fault('invalid float cast')
            return integer(int(value))
        if isinstance(node,(S.Sum,S.ArrC)):
            lo=self.evaluate(node.lo,env);hi=self.evaluate(node.hi,env)
            if lo>hi:raise Fault('invalid array range')
            integer(hi-lo);values=[]
            for i in range(lo,hi):
                child=dict(env);child[node.var]=i;values.append(self.evaluate(node.body,child))
            if isinstance(node,S.ArrC):return values
            result=0
            for value in values:
                if isinstance(value,dict):result=value if result==0 else {k:integer(result[k]+v) if isinstance(v,int) else result[k]+v for k,v in value.items()}
                else:result=result+value if isinstance(value,float) else integer(result+value)
            return result
        if isinstance(node,S.Loop):
            values=[self.evaluate(x,env) for x in node.inits]
            while True:
                child={**env,**dict(zip(node.names,values))}
                if not self.evaluate(node.cond,child):return self.evaluate(node.yld,child)
                values=[self.evaluate(x,child) for x in node.nexts]
        if isinstance(node,S.RecLit):return {name:self.evaluate(value,env) for name,value in node.fields}
        if isinstance(node,S.Field):return copy.deepcopy(self.evaluate(node.expr,env)[node.name])
        if isinstance(node,S.With):
            value=copy.deepcopy(self.evaluate(node.expr,env));value.update({name:self.evaluate(v,env) for name,v in node.fields});return value
        if isinstance(node,S.Check):
            if not self.evaluate(node.pred,env):raise Fault('failed check')
            return self.evaluate(node.body,env)
        if isinstance(node,S.Call):
            if node.name=='function':return node.args[0].name
            if node.name=='function_null':return None
            if node.name in env:return self.call(env[node.name],[self.evaluate(x,env) for x in node.args])
            args=[self.evaluate(x,env) for x in node.args]
            if node.name=='noop':return None
            if node.name=='byte_equal':return args[0]==args[1]
            if node.name in ('bit_and','bit_or','bit_xor'):
                a,b=args
                return wrapping(a&b if node.name=='bit_and' else a|b if node.name=='bit_or' else a^b)
            if node.name=='count_trailing_zeros':
                value=args[0]%(1<<64);count=0
                if value==0:return 64
                while value%2==0:count+=1;value//=2
                return count
            if node.name=='byte_swap64':
                value=args[0]%(1<<64);out=0
                for _ in range(8):out=(out<<8)|(value&255);value>>=8
                return wrapping(out)
            if node.name=='mul_high':
                return wrapping(((args[0]%(1<<64))*(args[1]%(1<<64)))>>64)
            if node.name in ('shift_left','shift_right','arithmetic_shift_right'):
                a,b=args
                return wrapping(a<<(b&63) if node.name=='shift_left' else ((a%(1<<64)) if node.name=='shift_right' else a)>>(b&63))
            if node.name=='concat':return [byte for part in args for byte in part]
            if node.name=='byte_read_le':
                value,offset,width=args
                if width not in (1,2,4,8):raise Fault('byte read width')
                if not 0<=offset<=len(value) or width>len(value)-offset:raise Fault('byte read bounds')
                return wrapping(int.from_bytes(bytes(value[offset:offset+width]),'little'))
            if node.name in ('byte_copy','byte_write_le'):
                operands=args
                value,offset=operands[:2]
                if node.name=='byte_copy':data=operands[2]
                else:
                    number,width=operands[2:]
                    if not 0<=width<=8:raise Fault('byte write bounds')
                    data=[(number>>(8*i))&255 for i in range(width)]
                if not 0<=offset<=len(value) or len(data)>len(value)-offset:raise Fault('byte write bounds')
                out=list(value);out[offset:offset+len(data)]=data;return out
            if node.name=='byte_slice':
                value,start,end=args
                if not 0<=start<=end<=len(value):raise Fault('byte slice bounds')
                return value[start:end]
            if node.name=='push':return copy.deepcopy(args[0])+[copy.deepcopy(args[1])]
            if node.name in ('float_bits','bits_float'):
                import struct
                return struct.unpack('<q',struct.pack('<d',args[0]))[0] if node.name=='float_bits' else struct.unpack('<d',struct.pack('<q',wrapping(args[0])))[0]
            if node.name=='sqrt':return math.sqrt(args[0])
            if node.name=='set':
                out=copy.deepcopy(args[0]);index=args[1]
                if not 0<=index<len(out):raise Fault('set index out of range')
                out[index]=args[2];return out
            if node.name.startswith('wrapping_'):
                a,b=args;return wrapping(a+b if node.name=='wrapping_add' else a-b if node.name=='wrapping_sub' else a*b)
            return self.call(node.name,args)
        raise Fault('unsupported reference node '+type(node).__name__)
