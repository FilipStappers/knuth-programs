(* outputs the rooted tree that corresponds to D W Matula's bijection *)
(* Reference: SIAM Review 10 (1968) 273; see also OEIS A061775 *)
(* the output is in my rectree format, see MATULA-BIG *)

stream="stdout" (* you can change this *)

startstack:=stack={}; startstack
push[elt_]:=stack={elt,stack}
pop:=With[{elt=First[stack]},stack=Last[stack];elt]

print[string_]:=WriteString[stream,string]
newline:=Write[stream]
writespec[spec_]:=With[{n=spec[[1]],offset=spec[[2]]},
           WriteString[stream,"T",mtl[n],"_",offset]]
printtop:=writespec[First[stack]]

fi=FactorInteger
sm[l_]:=Sum[l[[k]][[2]] mtl[PrimePi[l[[k]][[1]]]],{k,Length[l]}]
mtl[n_] := mtl[n] = 1 + sm[fi[n]]
mtl[0]=0

finish:=While[stack!={},deftree[pop]]

deftree[spec_]:=Block[{n=spec[[1]],offset=spec[[2]],l},l=fi[n];If[n>2,
  writespec[spec];print["="];offset++;
  Do[launch[l[[k]],offset];offset+=l[[k]][[2]]*mtl[PrimePi[l[[k]][[1]]]],
        {k,Length[l]}];
  print[".\n"]]]

launch[spec_,offset_]:=With[{n=PrimePi[spec[[1]]],e=spec[[2]]},
  print["+"<>ToString[e]<>"T"<>ToString[mtl[n]]<>"_"<>ToString[offset]];
  push[{n,offset}]]

matulatree[n_]:=Block[{},startstack;push[{n,0}];
     print["% Rooted tree number "<>ToString[n]<>"\n"];
     printtop;print[".\n"];finish]
