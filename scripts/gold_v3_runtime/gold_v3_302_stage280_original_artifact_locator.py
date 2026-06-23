#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess
from pathlib import Path

FORBIDDEN=("gold_v2","old_gold","disc8","stage41","legacy_gold")
TARGETS={
 "gold_v3_stage280_oos_predictions.pkl":"frozen_matrix",
 "gold_v3_stage280_feature_importance.csv":"feature_importance",
 "stage280_rev_long_2026_model.txt":"model_text",
 "stage280_rev_long_2026_model.txt.gz.b64":"model_b64",
 "stage280_rev_long_2026_contract.json":"contract",
}
MAX_BYTES=256*1024*1024

def run(cmd,cwd):
 return subprocess.run(cmd,cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
def blocked(text):
 s=text.lower().replace("\\","/"); return any(x in s for x in FORBIDDEN)
def root_from_git(start):
 r=run(["git","rev-parse","--show-toplevel"],start)
 if r.returncode: raise RuntimeError(r.stderr.decode("utf-8",errors="replace"))
 return Path(r.stdout.decode().strip()).resolve()
def size_of(root,sha):
 r=run(["git","cat-file","-s",sha],root)
 try:return int(r.stdout.strip()) if r.returncode==0 else None
 except ValueError:return None
def blob(root,sha,size):
 if size is None or size>MAX_BYTES:return b""
 r=run(["git","cat-file","blob",sha],root); return r.stdout if r.returncode==0 else b""
def signatures(data,name=""):
 out=[]; n=name.lower(); stripped=data.lstrip()
 if data.startswith(b"\x80") and all(x in data for x in (b"target_rev",b"subtype",b"h4_align")):out.append("frozen_matrix_signature")
 if (data.startswith(b"tree\n") or b"Tree=0\n" in data[:200000]) and b"feature_names=" in data and b"m1_ret5_atr" in data:out.append("model_text_signature")
 if stripped.startswith(b"{") and b"STAGE280_REV_LONG_2026" in data and b"score_threshold" in data and b"features" in data:out.append("contract_signature")
 first=data.splitlines()[0].lower() if data.splitlines() else b""
 if (b"feature" in first or "feature_importance" in n) and b"m1_ret5_atr" in data and b"countermove_60" in data:out.append("feature_importance_signature")
 return out
def sha256(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def roots(values):
 out=[]; seen=set()
 for value in values:
  p=Path(value).expanduser().resolve(); k=str(p).lower()
  if p.exists() and k not in seen and not blocked(str(p)):seen.add(k);out.append(p)
 return out
def scan_files(scan_roots):
 exact=[]; sig=[]; seen=set(); count=0
 for base in scan_roots:
  for dp,dns,fns in os.walk(base):
   cur=Path(dp); low=str(cur).lower().replace("\\","/")
   dns[:]=[d for d in dns if d not in {".git","__pycache__",".venv","venv"} and not blocked(low+"/"+d)]
   for fn in fns:
    p=(cur/fn)
    if blocked(str(p)):continue
    try:p=p.resolve(); st=p.stat()
    except OSError:continue
    k=str(p).lower()
    if k in seen:continue
    seen.add(k);count+=1
    kind=TARGETS.get(fn.lower())
    if kind:
     try:digest=sha256(p)
     except OSError:digest=""
     exact.append({"source":"filesystem_exact","kind":kind,"path":str(p),"size":int(st.st_size),"mtime":int(st.st_mtime),"sha256":digest})
    if st.st_size<=MAX_BYTES and (kind or any(x in fn.lower() for x in ("stage280","oos_predictions","feature_importance","rev_long"))):
     try:data=p.read_bytes()
     except OSError:data=b""
     kinds=signatures(data,fn) if data else []
     if kinds:sig.append({"source":"filesystem_signature","kinds":kinds,"path":str(p),"size":int(st.st_size)})
 return exact,sig,count
def parse_objects(raw):
 for line in raw.decode("utf-8",errors="replace").splitlines():
  if not line.strip():continue
  parts=line.split(" ",1); sha=parts[0]; path=parts[1] if len(parts)>1 else ""
  if not blocked(path):yield sha,path
def scan_git(root):
 exact=[]; sig=[]; unreachable=[]
 rev=run(["git","rev-list","--objects","--all"],root)
 if rev.returncode==0:
  for sha,path in parse_objects(rev.stdout):
   fn=Path(path).name.lower(); kind=TARGETS.get(fn); interesting=kind or any(x in path.lower() for x in ("stage280","oos_predictions","feature_importance","rev_long"))
   if not interesting:continue
   size=size_of(root,sha)
   if kind:exact.append({"source":"git_reachable_exact","kind":kind,"blob_sha":sha,"path":path,"size":size})
   data=blob(root,sha,size); kinds=signatures(data,fn) if data else []
   if kinds:sig.append({"source":"git_reachable_signature","kinds":kinds,"blob_sha":sha,"path":path,"size":size})
 fsck=run(["git","fsck","--full","--no-reflogs","--unreachable"],root)
 for line in fsck.stdout.decode("utf-8",errors="replace").splitlines():
  parts=line.split()
  if len(parts)<3 or parts[1]!="blob":continue
  sha=parts[2]; size=size_of(root,sha); data=blob(root,sha,size); kinds=signatures(data) if data else []
  if kinds:unreachable.append({"source":"git_unreachable_signature","kinds":kinds,"blob_sha":sha,"size":size})
 return exact,sig,unreachable
def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",required=True);p.add_argument("--scan-root",action="append",default=[]);p.add_argument("--output",required=True);a=p.parse_args()
 repo=root_from_git(Path(a.repo_root).resolve()); scan_roots=roots([repo,*a.scan_root])
 fe,fs,count=scan_files(scan_roots);ge,gs,gu=scan_git(repo);rows=fe+fs+ge+gs+gu
 present={r.get("kind") for r in rows if r.get("kind")}
 for r in rows:present.update(r.get("kinds",[]))
 matrix=bool({"frozen_matrix","frozen_matrix_signature"}&present);model=bool({"model_text","model_b64","model_text_signature"}&present);feature=bool({"feature_importance","feature_importance_signature","contract","contract_signature"}&present)
 decision="EXACT_MODEL_CANDIDATE_FOUND" if model else "FROZEN_MATRIX_CANDIDATE_FOUND" if matrix else "FEATURE_OR_CONTRACT_ONLY_FOUND" if feature else "ORIGINAL_ARTIFACT_NOT_FOUND"
 report={"status":"GOLD_V3_302_STAGE280_ORIGINAL_ARTIFACT_LOCATOR_READY","repo_root":str(repo),"scanned_roots":[str(x) for x in scan_roots],"forbidden_paths_skipped":list(FORBIDDEN),"recovered_runtime_source":{"blob_sha":"ac45e29c1b575ccfef8caf151b4112863380e81a","required_inputs":["gold_v3_stage280_oos_predictions.pkl","gold_v3_stage280_feature_importance.csv"]},"summary":{"files_seen":count,"filesystem_exact":len(fe),"filesystem_signature":len(fs),"git_reachable_exact":len(ge),"git_reachable_signature":len(gs),"git_unreachable_signature":len(gu),"matrix_candidate_found":matrix,"model_candidate_found":model,"feature_or_contract_found":feature},"decision":decision,"filesystem_exact_matches":fe,"filesystem_signature_matches":fs,"git_reachable_exact_matches":ge,"git_reachable_signature_matches":gs,"git_unreachable_signature_matches":gu,"note":"Audit-only. No expected value, tolerance, model, threshold, signal, order, Discord, or partial-close state is changed."}
 out=Path(a.output).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(report,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
