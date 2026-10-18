"""B039: each production append must check space before storing its pointer."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import ROOT, FLAGS


class AntislideStackCapacity(unittest.TestCase):
    def test_full_and_exact_fit_production_append_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            for variant in ['base','nocorner']:
                for branch in ['moves','remaining','constraints']:
                    text=(ROOT/'programs/programs/antislide.w').read_text()
                    # Observe every real pointer store independently. On fixed
                    # code the production guard must terminate before this hook.
                    text=text.replace('@<Global variables@>@;', '''@<Global variables@>@;
node **observe_move(node **p) {
 if(p>=move_stack+move_stack_size){fprintf(stderr,"UNGUARDED MOVE\\n");exit(79);}return p;
}
node ***observe_constraint(node ***p) {
 if(p>=constr_stack+constr_stack_size){fprintf(stderr,"UNGUARDED CONSTRAINT\\n");exit(79);}return p;
}''',1)
                    setup='''node **mtop,***ctop,**pp,***cc;
node *test_constraint[2]={&headers[0][0][1],NULL};
node **cbest=test_constraint,**test_clist[1]={test_constraint};
int count=0,seen[108]={0};
'''
                    if branch=='constraints':
                        setup+='count=1; cc=test_clist; ctop=constr_stack+constr_stack_size-(argc>1?count:0);\n'
                        module='@<If constraint |pp=*cc| is not satisfied, put it on the constraint stack@>;'
                    else:
                        if branch=='moves':
                            setup+='for(q=headers[0][0][1].down;q->left;q=q->down)count++;\n'
                            module='@<Put the moves for |cbest| on the move stack@>;'
                        else:
                            setup+='''for(p=&headers[0][0][0];p<(node*)(headers+n1);p++)
 for(q=p->down;q!=p;q=q->down) if(!seen[q->tag-tags])seen[q->tag-tags]=1,count++;
'''
                            module='@<Put all remaining moves on the move stack@>;'
                        setup+='mtop=move_stack+move_stack_size-(argc>1?count:0);\n'
                    text=text.replace('@<Backtrack thru all possibilities@>;',
                        '{'+setup+module+' printf("APPENDED %d\\n",count); return 0;}',1)
                    source=work/(variant+'-'+branch+'.w')
                    source.write_text(text)
                    generated=source.with_suffix('.c')
                    program=source.with_suffix('')
                    change=str(ROOT/'programs/programs/antislide-nocorner.ch') if variant=='nocorner' else '-'
                    subprocess.run(['ctangle',str(source),change,str(generated)],check=True,capture_output=True)
                    code=generated.read_text().replace('*mtop++=','*observe_move(mtop++)=').replace('*ctop++=','*observe_constraint(ctop++)=')
                    generated.write_text(code)
                    subprocess.run(['gcc',*FLAGS,str(generated),'-o',str(program)],check=True,capture_output=True)
                    for exact in [False,True]:
                        with self.subTest(variant=variant,branch=branch,exact=exact):
                            result=subprocess.run([str(program),*(['exact'] if exact else [])],capture_output=True,timeout=5)
                            self.assertNotIn(b'UNGUARDED',result.stderr)
                            if exact:
                                self.assertEqual(result.returncode,0,result.stdout)
                                self.assertRegex(result.stdout,rb'APPENDED [1-9][0-9]*\n')
                            else:
                                self.assertNotEqual(result.returncode,0)
                                self.assertIn(b'stack overflow!',result.stdout)


if __name__=='__main__': unittest.main()
