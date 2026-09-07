#!/usr/bin/env python3
"""极简 MS-NRBF (.NET BinaryFormatter) 解析器 —— 只求够读懂存档。

用来读游戏的 Save*Short.dat 和 OfflineProfiles.dat：这两个是 .NET 的
BinaryFormatter 序列化流，好处是**字段名就写在流里**，不用猜结构。
undo_move.py 里 savedDataSize 的偏移就是靠它定出来的；游戏更新后字段
位移了，也用它重新对一遍。

Save*Full.dat 不是这个格式，是自定义二进制，见 undo_move.py。

用法:  python3 nrbf.py <文件>        输出 JSON

只实现了读到这些存档所需的记录类型，不求完整；遇到没实现的会直接报错
而不是猜，免得给出看似合理实则错位的结果。
"""
import struct, sys, json, datetime

class R:
    def __init__(s, b): s.b, s.p = b, 0
    def u8(s):  v=s.b[s.p]; s.p+=1; return v
    def i32(s): v,=struct.unpack_from("<i",s.b,s.p); s.p+=4; return v
    def u32(s): v,=struct.unpack_from("<I",s.b,s.p); s.p+=4; return v
    def i64(s): v,=struct.unpack_from("<q",s.b,s.p); s.p+=8; return v
    def u64(s): v,=struct.unpack_from("<Q",s.b,s.p); s.p+=8; return v
    def i16(s): v,=struct.unpack_from("<h",s.b,s.p); s.p+=2; return v
    def u16(s): v,=struct.unpack_from("<H",s.b,s.p); s.p+=2; return v
    def f32(s): v,=struct.unpack_from("<f",s.b,s.p); s.p+=4; return v
    def f64(s): v,=struct.unpack_from("<d",s.b,s.p); s.p+=8; return v
    def s7(s):
        n=sh=0
        while True:
            c=s.u8(); n|=(c&0x7f)<<sh; sh+=7
            if not c&0x80: break
        v=s.b[s.p:s.p+n].decode("utf-8","replace"); s.p+=n; return v

# MS-NRBF PrimitiveTypeEnumeration（注意没有 4）
PRIM={1:"bool",2:"byte",3:"char",5:"decimal",6:"double",7:"i16",8:"i32",9:"i64",
      10:"sbyte",11:"single",12:"timespan",13:"datetime",14:"u16",15:"u32",16:"u64",
      17:"null",18:"string"}

def prim(r,t):
    if t==1:  return r.u8()!=0
    if t==2:  return r.u8()
    if t==3:
        st=r.p
        for n in (1,2,3,4):
            try:
                v=r.b[st:st+n].decode("utf-8"); r.p=st+n; return v
            except Exception: pass
        r.p=st+1; return "?"
    if t==5:  return r.s7()
    if t==6:  return r.f64()
    if t==7:  return r.i16()
    if t==8:  return r.i32()
    if t==9:  return r.i64()
    if t==10:
        v=struct.unpack_from("<b",r.b,r.p)[0]; r.p+=1; return v
    if t==11: return r.f32()
    if t==12: return r.i64()
    if t==13:
        v=r.u64(); ticks=v&0x3FFFFFFFFFFFFFFF
        try: return str(datetime.datetime(1,1,1)+datetime.timedelta(microseconds=ticks//10))
        except Exception: return ticks
    if t==14: return r.u16()
    if t==15: return r.u32()
    if t==16: return r.u64()
    if t==18: return r.s7()
    raise ValueError(f"未知基元类型 {t}")

class Parser:
    def __init__(s,data): s.r=R(data); s.objs={}; s.classes={}; s.pending=[]
    def run(s):
        """解析全部内容。文件可能由多条流首尾相接（如 OfflineProfiles.dat），
        所以遇到 MessageEnd 后若还有剩余字节，就当作下一条流继续读。"""
        r=s.r; roots=[]
        while r.p < len(r.b):
            rt=r.u8()
            if rt==11:                            # MessageEnd
                if r.p >= len(r.b): break
                continue                          # 还有字节 -> 下一条流
            v=s.record(rt)
            if v is not None: roots.append(v)
        return roots, s.objs

    def read_type_info(s,n,system):
        r=s.r; bts=[r.u8() for _ in range(n)]; extra=[]
        for bt in bts:
            if bt==0:   extra.append(r.u8())            # Primitive -> prim type
            elif bt==3: extra.append(r.s7())            # SystemClass -> name
            elif bt==4: extra.append((r.s7(), r.i32())) # Class -> name+libid
            elif bt==7: extra.append(r.u8())            # PrimitiveArray
            else:       extra.append(None)
        return list(zip(bts,extra))

    def read_value(s,bt,ex):
        r=s.r
        if bt==0: return prim(r,ex)
        return s.record(r.u8())

    def record(s,rt):
        r=s.r
        if rt==0:                                  # SerializedStreamHeader
            r.i32(); r.i32(); r.i32(); r.i32(); return None
        if rt==12:                                 # BinaryLibrary
            r.i32(); r.s7(); return None
        if rt in (4,5):                            # SystemClassWithMembersAndTypes / ClassWithMembersAndTypes
            oid=r.i32(); name=r.s7(); cnt=r.i32()
            members=[r.s7() for _ in range(cnt)]
            ti=s.read_type_info(cnt, rt==4)
            if rt==5: r.i32()                      # library id
            s.classes[oid]=(name,members,ti)
            obj={"__type":name}; s.objs[oid]=obj
            for m,(bt,ex) in zip(members,ti): obj[m]=s.read_value(bt,ex)
            return obj
        if rt==1:                                  # ClassWithId
            oid=r.i32(); mid=r.i32()
            name,members,ti=s.classes[mid]
            obj={"__type":name}; s.objs[oid]=obj
            for m,(bt,ex) in zip(members,ti): obj[m]=s.read_value(bt,ex)
            return obj
        if rt==6:                                  # BinaryObjectString
            oid=r.i32(); v=r.s7(); s.objs[oid]=v; return v
        if rt==8:                                  # MemberPrimitiveTyped
            return prim(r,r.u8())
        if rt==9:                                  # MemberReference
            return {"__ref":r.i32()}
        if rt==10: return None                     # ObjectNull
        if rt==13: return [None]*r.u8()            # ObjectNullMultiple256
        if rt==14: return [None]*r.i32()
        if rt==15:                                 # ArraySinglePrimitive
            oid=r.i32(); n=r.i32(); pt=r.u8()
            if pt==2: v=bytes(r.b[r.p:r.p+n]); r.p+=n
            else: v=[prim(r,pt) for _ in range(n)]
            s.objs[oid]=v; return v
        if rt==16:                                 # ArraySingleObject
            oid=r.i32(); n=r.i32(); out=[]; s.objs[oid]=out
            while len(out)<n:
                v=s.record(r.u8())
                if isinstance(v,list) and v and all(x is None for x in v): out.extend(v)
                else: out.append(v)
            return out
        if rt==17:                                 # ArraySingleString
            oid=r.i32(); n=r.i32(); out=[]; s.objs[oid]=out
            while len(out)<n:
                v=s.record(r.u8())
                if isinstance(v,list): out.extend(v)
                else: out.append(v)
            return out
        if rt==7:                                  # BinaryArray
            oid=r.i32(); at=r.u8(); rank=r.i32()
            lens=[r.i32() for _ in range(rank)]
            if at in (3,4,5): [r.i32() for _ in range(rank)]
            bt=r.u8()
            ex=None
            if bt==0: ex=r.u8()
            elif bt==3: ex=r.s7()
            elif bt==4: ex=(r.s7(),r.i32())
            elif bt==7: ex=r.u8()
            total=1
            for l in lens: total*=l
            out=[]; s.objs[oid]=out
            while len(out)<total:
                v=s.read_value(bt,ex)
                if bt!=0 and isinstance(v,list) and v and all(x is None for x in v): out.extend(v)
                else: out.append(v)
            return out
        raise ValueError(f"未知记录类型 {rt} @ {r.p-1}")

def resolve(v,objs,seen=None):
    seen=seen or set()
    if isinstance(v,dict):
        if "__ref" in v:
            t=objs.get(v["__ref"])
            if id(t) in seen: return f"<循环 #{v['__ref']}>"
            return resolve(t,objs,seen|{id(t)})
        return {k:resolve(x,objs,seen) for k,x in v.items()}
    if isinstance(v,list): return [resolve(x,objs,seen) for x in v]
    if isinstance(v,bytes): return f"<{len(v)} 字节>"
    return v

if __name__=="__main__":
    data=open(sys.argv[1],"rb").read()
    roots,objs=Parser(data).run()
    print(json.dumps([resolve(x,objs) for x in roots],ensure_ascii=False,indent=1,default=str))
