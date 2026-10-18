"""B057: scripted local updates; no random graph search or RNG calls."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import ROOT, GraphNative


class D4g6Bookkeeping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        native=GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/archives/SATexamples/sources/rand-d4g6.w').read_text()
        start=text.index('  for (e=0;e<2*nn;)')
        end=text.index('\n}\n',start)
        text=text[:start]+'''  insert(0,1);e++;insert(2,3);e++;insert(4,5);e++;
  if(argc>3) {
    time=strtoull(argv[3],NULL,10);advance_time();
    printf("TIME %llu\\n",(unsigned long long)time);return 0;
  }
  if(!strcmp(argv[1],"insert")) {
    p=1;uelig[0]=6;velig[0]=7;
    @<Insert a random eligible edge@>;
    printf("TIME %llu\\n",(unsigned long long)time);return 0;
  }
  if(argc>2) {
    curstamp=strtoull(argv[2],NULL,10);u=0;
    @<Stamp all vertices at distance |<5| from |u|@>;
    printf("STAMP %u",(unsigned)curstamp);
    for(v=0;v<nn;v++)printf(" %u",(unsigned)stamp[v]);puts("");return 0;
  }
  time=20; j=atoi(argv[1]);
  @<Delete a random edge@>;
  e--;
  printf("TIME %llu\\n",(unsigned long long)time);
  for(u=0;u<nn;u++)for(v=0;v<nn;v++) if(wait[u][v])
    printf("WAIT %d %d %llu\\n",u,v,(unsigned long long)wait[u][v]);
  for(j=0;j<e;j++)printf("EDGE %d %d %d %d\\n",ee[j].u,ee[j].v,ee[j].uinx,ee[j].vinx);
  for(v=0;v<nn;v++)for(j=0;j<deg[v];j++)printf("ARC %d %d %d %d\\n",v,j,adj[v][j],adjinx[v][j]);
  return 0;'''+text[end:]
        text=text.replace('@<Process the command line@>;','nn=8;',1)
        text=text.replace('j=gb_unif_rand(e);','/* j was chosen by the fixture */')
        text=text.replace('j=gb_unif_rand(p);','j=0; /* the sole scripted choice */')
        cls.program=native.build('bookkeeping',text)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_deleted_edge_not_replacement_is_embargoed(self):
        original=[(0,1),(2,3),(4,5)]
        for choice in range(3):
            result=subprocess.run([str(self.program),str(choice)],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            lines=[line.split() for line in result.stdout.decode().splitlines()]
            self.assertEqual(next(line for line in lines if line[0]=='TIME'),['TIME','21'])
            u,v=original[choice]
            waits={(int(line[1]),int(line[2])):int(line[3]) for line in lines if line[0]=='WAIT'}
            self.assertEqual(waits,{(u,v):31,(v,u):31})
            edges=[tuple(map(int,line[1:])) for line in lines if line[0]=='EDGE']
            self.assertEqual({tuple(sorted(edge[:2])) for edge in edges},set(original)-{(u,v)})
            arcs={(int(line[1]),int(line[2])):tuple(map(int,line[3:])) for line in lines if line[0]=='ARC'}
            self.assertEqual(len(arcs),4)
            for index,(a,b,ui,vi) in enumerate(edges):
                self.assertEqual(arcs[b,ui],(a,index))
                self.assertEqual(arcs[a,vi],(b,index))

    def test_stamp_high_bit_and_wrap_rejection(self):
        for stamp in [0,2147483647,4294967294,4294967295]:
            result=subprocess.run([str(self.program),'stamp',str(stamp)],capture_output=True,timeout=5)
            if stamp==4294967295:
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'give up',result.stderr)
            else:
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(list(map(int,result.stdout.split()[1:])),[stamp+1,stamp+1,stamp+1,0,0,0,0,0,0])

    def test_update_clock_bounds_and_insertion(self):
        result=subprocess.run([str(self.program),'insert'],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,b'TIME 1\n')
        maximum=(1<<64)-1
        for initial in [2147483647,maximum-11,maximum-10,maximum]:
            result=subprocess.run([str(self.program),'clock','unused',str(initial)],capture_output=True,timeout=5)
            if initial>=maximum-10:
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'Update clock exhausted',result.stderr)
            else:
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout,f'TIME {initial+1}\n'.encode())


if __name__=='__main__': unittest.main()
