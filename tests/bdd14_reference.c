/* Direct three-variable truth tables; no BDD operation supplies expectations. */
#define main bdd_original_main
#include "bdd-under-test.c"
#undef main

static unsigned evaluate(node *p) {
  unsigned a,t=0;
  for (a=0;a<8;a++) {
    node *q=p;
    while (q>topsink)
      q=node_((a&(1U<<thevar(q)->name))?q->hi:q->lo);
    if (q==topsink) t|=1U<<a;
  }
  return t;
}
static node *construct(unsigned t,int v,unsigned a) {
  node *l,*h,*r;
  if (v==3) { r=(t&(1U<<a))?topsink:botsink; r->xref++; return r; }
  l=construct(t,v+1,a);
  h=construct(t,v+1,a|(1U<<v));
  return unique_find(varhead+v,l,h);
}
static unsigned exists(unsigned t,unsigned mask) {
  unsigned a,b,result=0;
  for (a=0;a<8;a++) for (b=0;b<8;b++)
    if ((b&~mask)==0 && ((t>>((a&~mask)|b))&1)) {
      result|=1U<<a;
      break;
    }
  return result;
}
int main(int argc,char **argv) {
  unsigned t,u,q,a,cube[8],failures=0,cases=0;
  bdd_original_main(2,argv); /* only replace its final normal exit by return */
#ifdef ZDD
  createvars(2);
#endif
  for (a=0;a<3;a++) projection(a);
  for (t=0;t<256;t++) f[t]=construct(t,0,0);
  if (argc>2 && strcmp(argv[2],"cache")==0) {
    unsigned oldmask,slot,trigger_slot;
    int found=0,before,after;
    node *hit;
    collect_garbage(1);
    cache_init();
    oldmask=cachemask;
    trigger_slot=cachehash(f[255],f[255],node_(1));
    for (t=1;t<255&&!found;t++) for (u=1;u<255;u++) {
      slot=cachehash(f[t],f[u],node_(1));
      if ((slot&(oldmask+1)) && ((slot&oldmask)!=(trigger_slot&oldmask))) {
        found=1;
        break;
      }
    }
    t--;
    if (!found) return 2;
    cache_insert(f[t],f[u],node_(1),f[t&u]);
    hit=cache_lookup(f[t],f[u],node_(1)); before=hit!=NULL;
    if (hit) deref(hit);
    cacheinserts=threshold-1;
    cache_insert(f[255],f[255],node_(1),f[255]);
    hit=cache_lookup(f[t],f[u],node_(1)); after=hit!=NULL;
    if (hit) deref(hit);
    sanity_check();
    printf("CACHE before=%d after=%d pages=%d\n",before,after,cachepages);
    return before&&after&&cachepages==2?0:1;
  }
#ifndef ZDD
  if (argc>2 && strcmp(argv[2],"compose")==0) {
    for (t=0;t<=255;t+=255) {
      node *r=f[t];
      int before=r->xref;
      node *result=compose_top(r);
      if (result!=r || r->xref!=before+1) failures++;
      /* Release only a reference that the result actually acquired. */
      if (r->xref==before+1) deref(result);
      if (r->xref!=before) failures++;
    }
    sanity_check();
    printf("COMPOSE failures=%u\n",failures);
    return failures?1:0;
  }
#endif
  for (q=0;q<8;q++) {
    cube[q]=0;
    for (a=0;a<8;a++) if ((a&q)==q) cube[q]|=1U<<a;
  }
  for (t=0;t<256;t++) for (u=0;u<256;u++) {
    node *r=binary_top(1,f[t],f[u]);
    if (evaluate(r)!=(t&u)) failures++;
    deref(r);
    for (q=0;q<8;q++) {
      r=ternary_top(19,f[t],f[u],f[cube[q]]);
      if (evaluate(r)!=exists(t&u,q)) failures++;
      deref(r);
      cases++;
    }
  }
  sanity_check();
  printf("FUSED cases=%u failures=%u\n",cases,failures);
  return failures?1:0;
}
