"""Read emitted frontier diagrams independently of native frontier state code."""
import re


def diagram(output):
    arcs,nodes={},{}
    vertex,level=None,0
    for line in output.decode().splitlines():
        match=re.match(r'^(\d+)\(v(\d+)\)',line)
        if match:
            vertex=int(match[2])
        match=re.match(r'^\s+(->|<-)\s+(?:\d+\(v(\d+)(?:,[^)]*)?\)|dummy,0)\s+#(\d+)',line)
        if match:
            tip=int(match[2]) if match[2] is not None else None
            arcs[int(match[3])]=(vertex,tip) if match[1]=='->' else (tip,vertex)
        match=re.fullmatch(r'#(\d+):',line)
        if match:
            level=int(match[1])
        match=re.fullmatch(r'([0-9a-f]+):([0-9a-f]+),([0-9a-f]+)',line)
        if match:
            node,lo,hi=map(lambda s:int(s,16),match.groups())
            nodes[node]=(level,lo,hi)
    cache={0:set(),1:{frozenset()}}
    def visit(node):
        if node not in cache:
            var,lo,hi=nodes[node]
            cache[node]=visit(lo)|{family|{var} for family in visit(hi)}
        return cache[node]
    return arcs,visit(2)
