"""Complete graceful-labeling families compared with direct permutations."""
from itertools import combinations, permutations
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))


def labelings(n, edges, preset=None, canonical_rule='back'):
    m = len(edges)
    result = set()
    for labels in permutations(range(m+1), n):
        if preset and any(labels[v] != value for v, value in preset.items()):
            continue
        if sorted(abs(labels[u]-labels[v]) for u, v in edges) != list(range(1, m+1)):
            continue
        if not preset and canonical_rule == 'back':
            if m >= 2 and not any({labels[u], labels[v]} == {1, m} for u, v in edges):
                continue
            if m == 1 and labels[0] != 0:
                continue
        if canonical_rule == 'dlx' and m and not any(labels[u] == 0 and labels[v] == m
                                                    for u, v in edges):
            continue
        result.add(labels)
    return result


@unittest.skipUnless((GRAPHBASE/'gb_types.w').exists(), 'GraphBase sources required')
class GracefulLabelings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-w',
                            '-I'+str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')),
                            '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        generated = cls.work/'graceful.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/back-graceful.w'),
                        '-', str(generated)], cwd=GRAPHBASE, check=True, capture_output=True)
        cls.program = cls.work/'graceful'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(generated), *objects, '-o', str(cls.program)],
                       check=True, capture_output=True)
        fixture = cls.work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),i,u,v;char name[16];Graph *g=gb_new_graph(n);
  if(!g)return 1;
  for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  while(scanf("%d %d",&u,&v)==2)gb_new_edge(g->vertices+u,g->vertices+v,1);
  return save_graph(g,argv[2]);
}
''')
        cls.writer = cls.work/'fixture'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(fixture), *objects, '-o', str(cls.writer)],
                       check=True, capture_output=True)
        cls.encoders = {}
        for mode in ['graceful-dlx', 'graceful-dlx-domains', 'graceful-dlx-presets']:
            generated = cls.work/(mode+'.c')
            base = 'graceful-dlx' if mode.endswith('-domains') else mode
            change = str(ROOT/'programs/programs'/(mode+'.ch')) if mode.endswith('-domains') else '-'
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(base+'.w')),
                            change, str(generated)], cwd=GRAPHBASE,
                           check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon',
                            '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                            '-I'+str(GRAPHBASE), str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.encoders[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_family(self, n, edges, preset=None):
        saved = self.work/'input.gb'
        subprocess.run([str(self.writer), str(n), str(saved)],
                       input=''.join(f'{u} {v}\n' for u, v in edges), text=True,
                       check=True, capture_output=True)
        result = subprocess.run([str(self.program), str(saved)]+
                                [f'v{v}={value}' for v, value in (preset or {}).items()],
                                capture_output=True, text=True, timeout=10)
        # Historical void main has no defined success status; check its complete output.
        self.assertIn('Altogether ', result.stderr)
        actual = []
        for line in result.stdout.splitlines():
            assignments = {int(v): int(value) for v, value in re.findall(r'v(\d+)=(\d+)', line)}
            self.assertEqual(set(assignments), set(range(n)), 'incomplete labeling: '+line)
            actual.append(tuple(assignments[v] for v in range(n)))
        self.assertEqual(len(actual), len(set(actual)), 'duplicate labelings')
        self.assertEqual(set(actual), labelings(n, edges, preset))
        self.assertRegex(result.stderr, rf'Altogether {len(actual)} (?:canonical )?graceful labeling')

    def test_forced_complement_and_empty_boundaries(self):
        for n, edges in [(3, [(0, 1), (0, 2)]), (2, [(0, 1)]),
                         (1, []), (2, []), (3, [])]:
            with self.subTest(n=n, edges=edges):
                self.check_family(n, edges)

    def test_all_small_simple_graphs_and_presets(self):
        for n in range(1, 5):
            pairs = list(combinations(range(n), 2))
            for mask in range(1 << len(pairs)):
                edges = [e for k, e in enumerate(pairs) if mask & (1 << k)]
                for preset in [None, {0: 0}]+([{0: 1}] if edges else []):
                    with self.subTest(n=n, edges=edges, preset=preset):
                        self.check_family(n, edges, preset)

    def test_isolated_vertices_receive_all_unused_labels(self):
        for edges in [[(0, 1), (1, 2), (2, 3), (3, 0)],
                      list(combinations(range(4), 2))[:-1],
                      list(combinations(range(4), 2))]:
            for preset in [None, {0: 0}, {4: 1}]:
                with self.subTest(edges=edges, preset=preset):
                    self.check_family(5, edges, preset)

    def check_encoder(self, mode, n, edges, preset=None):
        saved = self.work/'cover.gb'
        subprocess.run([str(self.writer), str(n), str(saved)],
                       input=''.join(f'{u} {v}\n' for u, v in edges), text=True,
                       check=True, capture_output=True)
        result = subprocess.run([str(self.encoders[mode]), str(saved)]+
                                [f'v{v}={value}' for v, value in (preset or {}).items()],
                                capture_output=True, text=True, timeout=10)
        lines = result.stdout.splitlines()
        self.assertGreaterEqual(len(lines), 2, result.stderr)
        header = lines[1].split()
        primary = set(header[:header.index('|')])
        options = []
        for line in lines[2:]:
            items, colors = set(), {}
            for word in line.split():
                if ':' in word:
                    item, color = word.split(':')
                    colors[item] = color
                else:
                    items.add(word)
            self.assertTrue(items <= primary)
            options.append((items, colors))
        answers = []
        def visit(left, colors):
            if not left:
                self.assertTrue(all(f'.v{v}' in colors for v in range(n)),
                                'an exact cover omits a vertex label')
                answers.append(tuple(int(colors[f'.v{v}']) for v in range(n)))
                return
            compatible = [(items, extra) for items, extra in options if items <= left and
                          all(key not in colors or colors[key] == value for key, value in extra.items())]
            item = min(left, key=lambda item: sum(item in items for items, _ in compatible))
            for items, extra in compatible:
                if item in items:
                    visit(left-items, colors | extra)
        visit(primary, {})
        expected = labelings(n, edges, preset, None if mode.endswith('-presets') else 'dlx')
        self.assertEqual(len(answers), len(set(answers)))
        self.assertEqual(set(answers), expected)

    def test_encoder_isolated_vertex_regression(self):
        for mode in self.encoders:
            for n, edges in [(1, []), (2, []), (3, [(0, 1)]),
                             (5, list(combinations(range(4), 2))[:-1])]:
                for preset in ([None, {n-1: 0}] if mode.endswith('-presets') else [None]):
                    with self.subTest(mode=mode, n=n, edges=edges, preset=preset):
                        self.check_encoder(mode, n, edges, preset)

    def test_encoder_all_small_families(self):
        for n in range(1, 5):
            pairs = list(combinations(range(n), 2))
            for mask in range(1 << len(pairs)):
                edges = [e for k, e in enumerate(pairs) if mask & (1 << k)]
                for mode in self.encoders:
                    presets = ([None, {0: 0}]+([{0: 1}] if edges else [])) if mode.endswith('-presets') else [None]
                    for preset in presets:
                        with self.subTest(n=n, edges=edges, mode=mode, preset=preset):
                            self.check_encoder(mode, n, edges, preset)


if __name__ == '__main__':
    unittest.main()
