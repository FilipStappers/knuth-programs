"""BUG-038: declared UTF-16 capacity covers key/dead-state output families.

This checks the layout state machine, not the native macOS keyboard compiler.
"""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'programs/programs'


def layout(name):
    text = (ROOT / (name + '.keylayout')).read_text(encoding='utf-8')
    # XML 1.0 parsers reject the historical control-key character references.
    # Replace only those references by one-unit private-use placeholders.
    def control(match):
        value = int(match[1][1:], 16) if match[1].startswith('x') else int(match[1])
        return chr(0xe000 + value) if value < 32 and value not in (9, 10, 13) else match[0]
    return ET.fromstring(re.sub(r'&#(x[0-9a-fA-F]+|[0-9]+);', control, text))


def cases(root):
    actions = {a.attrib['id']: {w.attrib['state']: w.attrib for w in a}
               for a in root.findall('./actions/action')}
    terms = {w.attrib['state']: w.attrib['output'] for w in root.findall('./terminators/when')}
    maps = {(s.attrib['id'], m.attrib['index']): m
            for s in root.findall('keyMapSet') for m in s.findall('keyMap')}

    def keys(identifier):
        mapping = maps[identifier]
        result = keys((mapping.attrib['baseMapSet'], mapping.attrib['baseIndex'])) \
            if 'baseMapSet' in mapping.attrib else {}
        result.update({k.attrib['code']: k.attrib for k in mapping.findall('key')})
        return result

    def transition(key, state):
        if 'output' in key:
            return terms.get(state, '') + key['output'], 'none'
        action = actions[key['action']]
        prefix = ''
        if state not in action:
            prefix = terms[state]
            state = 'none'
        step = action[state]
        return prefix + step.get('output', ''), step.get('next', 'none')

    allkeys = [(identifier, code, key) for identifier in maps
               for code, key in keys(identifier).items()]
    reachable = {'none'}
    while True:
        more = {transition(key, state)[1] for _, _, key in allkeys for state in reachable}
        if more <= reachable:
            break
        reachable |= more
    return [(identifier, code, state, transition(key, state)[0])
            for identifier, code, key in allkeys for state in sorted(reachable)]


class KeyboardCapacity(unittest.TestCase):
    def test_declared_capacity_covers_reachable_outputs(self):
        for name in ['DonKeys', 'DonKeysExtended']:
            root = layout(name)
            outputs = cases(root)
            maximum = max(len(output.encode('utf-16-le')) // 2 for *_, output in outputs)
            if 'maxout' in root.attrib:
                declared = int(root.attrib['maxout'])
                self.assertGreaterEqual(declared, maximum, (name, declared, maximum))
            else:
                self.assertEqual(maximum, 2)
            if name == 'DonKeysExtended':
                self.assertEqual(len(outputs), 45136)
                self.assertEqual(maximum, 4)
                self.assertTrue(any(state == 'macron' and output == 'L\u0323\u0304'
                                    for _, _, state, output in outputs))
                self.assertTrue(any(state == 'tildebelow' and output == '\u00a0\u0330SS'
                                    for _, _, state, output in outputs))


if __name__ == '__main__':
    unittest.main()
