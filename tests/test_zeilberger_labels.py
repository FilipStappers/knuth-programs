"""Inverse labels from reconstructed links, plus independent pruning families."""
from math import comb
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/zeilberger.w'

AUDIT = '''
@ @<Sub...@>=
int audit_q[n+1],audit_s[n+1];
void audit_labels(int v) {
  int p,right;
  if (!v) return;
  audit_labels(lll[v]);
  audit_labels(rrr[v]);
  p=audit_q[lll[v]]+(audit_s[lll[v]]>1);
  right=audit_q[rrr[v]];
  audit_q[v]=(p>right? p:right);
  audit_s[v]=(p>right? 1:audit_s[rrr[v]]+(p==right));
  if(q[v]!=audit_q[v] || s[v]!=audit_s[v]) {
    fprintf(stderr,"LABEL_MISMATCH node %d: %d,%d expected %d,%d\\n",
            v,q[v],s[v],audit_q[v],audit_s[v]);
    exit(1);
  }
}
'''


def binary_shape(links, root=1):
    visited = set()
    def visit(v):
        if not v:
            return None
        assert 1 <= v <= len(links) and v not in visited
        visited.add(v)
        return tuple(visit(w) for w in links[v-1])
    result = visit(root)
    assert len(visited) == len(links)
    return result


def strahler(tree):
    if tree is None:
        return 0
    left, right = map(strahler, tree)
    return max(left, right)+(left == right)


def pruning_order(links):
    children = {}
    for v, (child, _) in enumerate(links, 1):
        children[v] = []
        while child:
            children[v].append(child)
            child = links[child-1][1]
    live, rounds = set(children), 0
    while live:
        def filament(v):
            remaining = [w for w in children[v] if w in live]
            return not remaining or (len(remaining) == 1 and filament(remaining[0]))
        removed = {v for v in live if filament(v)}
        assert removed
        live -= removed
        rounds += 1
    return rounds


class ZeilbergerLabels(unittest.TestCase):
    def test_complete_inverse_labels_and_small_bijections(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for degree in range(2, 16):
                text = SOURCE.read_text().replace('@d n 17 ', f'@d n {degree} ')
                needle = 'unzeil(1); /* attempt to recreate the original forest */'
                self.assertEqual(text.count(needle), 1)
                text = text.replace(needle, needle+'''
audit_s[0]=1000000;
audit_labels(1);
if (n<=8) {
  printf("@@@@ ");
  for(k=1;k<=n;k++) printf("%d,%d;",l[k],r[k]);
  printf("|");
  for(k=1;k<=n;k++) printf("%d,%d;",ll[k],rr[k]);
  printf("\\n");
}
''')
                self.assertEqual(text.count('@* Index.'), 1)
                text = text.replace('@* Index.', AUDIT+'\n@* Index.')
                source, generated, program = [work/(f'zeil{degree}'+suffix) for suffix in ['.w', '.c', '']]
                source.write_text(text)
                subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
                compiled = subprocess.run(['gcc', '-std=gnu99', '-O2', '-Wno-implicit-int',
                                '-include', 'stdlib.h', str(generated), '-o', str(program)],
                               text=True, capture_output=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                result = subprocess.run([str(program)], text=True, capture_output=True, timeout=45)
                with self.subTest(degree=degree):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, '')
                    totals = re.findall(r'Altogether (\d+) cases with pruning order', result.stdout)
                    expected = comb(2*degree, degree)//(degree+1)
                    self.assertEqual(sum(map(int, totals)), expected)
                    if degree > 8:
                        continue
                    forests, binaries = set(), set()
                    for line in result.stdout.splitlines():
                        if not line.startswith('@@ '):
                            continue
                        source_links, binary_links = [
                            [tuple(map(int, pair.split(','))) for pair in part.split(';') if pair]
                            for part in line[3:].split('|')]
                        forest = binary_shape(source_links)
                        binary = binary_shape(binary_links)
                        self.assertNotIn(forest, forests)
                        self.assertNotIn(binary, binaries)
                        forests.add(forest)
                        binaries.add(binary)
                        self.assertEqual(pruning_order(source_links), strahler(binary))
                    self.assertEqual(len(forests), expected)
                    self.assertEqual(len(binaries), expected)


if __name__ == '__main__':
    unittest.main()
