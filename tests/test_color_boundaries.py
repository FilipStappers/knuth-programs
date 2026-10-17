"""B057: coloring decisions and projections against direct vertex colorings.

Set GRAPHBASE to the Stanford GraphBase source directory. Its real graph
writer/reader exercise the file interface; dependency objects are uninstrumented.
"""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
MODES = ['log', 'log2', 'log3', 'order']


def graph_family():
    for n in range(1, 5):
        pairs = list(itertools.combinations(range(n), 2))
        for mask in range(1 << len(pairs)):
            yield n, mask, [edge for bit, edge in enumerate(pairs) if mask >> bit & 1]


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').is_file(), 'requires GRAPHBASE sources')
class ColorBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                            '-I', str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')),
                            '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        cls.programs = {}
        flags = ['-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                 '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                 '-I', str(GRAPHBASE)]
        for mode in MODES:
            generated = cls.work/(mode+'.c')
            subprocess.run(['ctangle', str(SOURCES/f'sat-color-{mode}.w'), '-', str(generated)],
                           cwd=GRAPHBASE, check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', *flags, str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program
        # Keep only the first two LOG3 edge clauses. Correct its shared bit-width
        # shift in this probe to isolate the separate doubled-color arithmetic.
        text = (SOURCES/'sat-color-log3.w').read_text().replace('1<<t', '1u<<t')
        text = text.replace('main(int argc, char*argv[]) {',
                            'main(int argc, char*argv[]) {\n  unsigned emitted=0;')
        text = text.replace('    printf("\\n");',
                            '    printf("\\n");\n    if (++emitted==2) break;')
        probe_source = cls.work/'log3-prefix.w'
        probe_source.write_text(text)
        generated = cls.work/'log3-prefix.c'
        subprocess.run(['ctangle', str(probe_source), '-', str(generated)], cwd=GRAPHBASE,
                       check=True, capture_output=True)
        cls.log3_prefix = cls.work/'log3-prefix'
        subprocess.run(['gcc', *flags, str(generated), *objects, '-o', str(cls.log3_prefix)],
                       check=True, capture_output=True)
        fixture = cls.work/'fixture.c'
        fixture.write_text(r'''
#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc, char **argv) {
  int n=atoi(argv[1]), mask=atoi(argv[2]), i,j,bit=0;
  char name[2]={0,0};
  Graph *g=gb_new_graph(n);
  if (!g) return 1;
  for (i=0;i<n;i++) {
    name[0]='a'+i;
    g->vertices[i].name=gb_save_string(name);
  }
  for (i=0;i<n;i++) for (j=i+1;j<n;j++,bit++)
    if (mask&(1<<bit)) gb_new_edge(g->vertices+i,g->vertices+j,1);
  return save_graph(g,argv[3]);
}
''')
        writer = cls.work/'fixture'
        subprocess.run(['gcc', *flags, str(fixture), *objects, '-o', str(writer)],
                       check=True, capture_output=True)
        for n, mask, _ in graph_family():
            subprocess.run([str(writer), str(n), str(mask), str(cls.work/f'{n}-{mask}.gb')],
                           check=True, capture_output=True,
                           env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, mode, n, mask, colors):
        result = subprocess.run([str(self.programs[mode]), str(self.work/f'{n}-{mask}.gb'),
                                 str(colors)], capture_output=True, timeout=5,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        return [line.split() for line in result.stdout.decode().splitlines()
                if line.strip() and not line.startswith('~ ')]

    def test_one_color_for_every_small_simple_graph(self):
        for n, mask, edges in graph_family():
            for mode in MODES:
                with self.subTest(n=n, mask=mask, mode=mode):
                    self.assertEqual(satisfiable(self.encode(mode, n, mask, 1)), not edges)

    def test_large_color_counts_on_edgeless_graph(self):
        for colors in [1073741823, 1073741824, 1073741825, 2147483647]:
            for mode in ['log', 'log2', 'log3']:
                with self.subTest(colors=colors, mode=mode):
                    formula = self.encode(mode, 1, 0, colors)
                    self.assertTrue(satisfiable(formula))

    def test_log3_large_leaf_prefix_arithmetic(self):
        for colors in [1073741824, 1073741825, 2147483647]:
            result = subprocess.run([str(self.log3_prefix), str(self.work/'2-1.gb'), str(colors)],
                                    capture_output=True, timeout=5,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            clauses = [line.split() for line in result.stdout.decode().splitlines()
                       if line.strip() and not line.startswith('~ ')]
            t = (colors-1).bit_length()
            expected = []
            for leaf in [colors, colors+1]:
                width = t if leaf >= 1 << t else t-1
                expected.append([('~' if leaf >> bit & 1 else '')+f'{name}.{width-bit}'
                                 for bit in range(width) for name in ['a', 'b']])
            self.assertEqual(clauses, expected)

    def test_invalid_binary_color_counts_reject(self):
        for colors in ['0', '-1', '2x', '4294967297', '9'*100]:
            for mode in ['log', 'log2', 'log3']:
                result = subprocess.run([str(self.programs[mode]), str(self.work/'1-0.gb'), colors],
                                        capture_output=True, timeout=5,
                                        env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(result.stdout)
                self.assertNotIn(b'runtime error', result.stderr)

    def test_neighboring_color_counts_and_small_assignment_projections(self):
        for n, mask, edges in graph_family():
            for colors in range(2, 5):
                assignments = list(itertools.product(range(colors), repeat=n))
                expected = any(all(word[u] != word[v] for u, v in edges) for word in assignments)
                for mode in MODES:
                    formula = self.encode(mode, n, mask, colors)
                    self.assertEqual(satisfiable(formula), expected, (n, mask, colors, mode))
                    if n > 3:
                        continue
                    t = (colors-1).bit_length()
                    # LOG3 represents colors by leaves c..2c-1 of a binary tree.
                    codes = [k & ((1 << t)-1) if k >= 1 << t else
                             (k & ((1 << (t-1))-1)) << 1 for k in range(colors, 2*colors)]
                    for word in assignments:
                        fixed = []
                        for vertex, color in enumerate(word):
                            name = chr(ord('a')+vertex)
                            if mode == 'order':
                                values = [(f'{name}<{k}', color < k) for k in range(1, colors)]
                            else:
                                code = codes[color] if mode == 'log3' else color
                                values = [(f'{name}.{k}', bool(code & (1 << (t-k))))
                                          for k in range(1, t+1)]
                            fixed.extend([('' if value else '~')+variable] for variable, value in values)
                        proper = all(word[u] != word[v] for u, v in edges)
                        self.assertEqual(satisfiable(formula+fixed), proper,
                                         (n, mask, colors, mode, word))


if __name__ == '__main__':
    unittest.main()
