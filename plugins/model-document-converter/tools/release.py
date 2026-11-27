#!/usr/bin/env python3
"""Strict PRIVATE Agent Plugins 1.0 preflight and deterministic packaging.

Public-directory submission requirements are intentionally a separate gate;
this validator cannot certify public submission or publisher identity.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import yaml

sys.dont_write_bytecode=True
SKIP_DIRS={".git","__pycache__",".pytest_cache","dist"}
ROOT_SCHEMA="https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def require(value,message):
    if not value:raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))


def members(root):
    result=[]
    for path in sorted(root.rglob("*")):
        rel=path.relative_to(root)
        if set(rel.parts)&SKIP_DIRS:continue
        require(not path.is_symlink(),"Symlink: "+str(rel))
        if path.is_dir():continue
        require(path.is_file(),"Not regular file: "+str(rel))
        require(path.suffix not in {".pyc",".tmp"} and path.name not in {".DS_Store","Thumbs.db"},"Transient file: "+str(rel))
        require(path.name not in {".env","credentials.json","token.json","id_rsa"},"Secret-shaped file: "+str(rel))
        require(len(rel.as_posix())<=1024 and "\\" not in rel.as_posix() and all(ord(c)>=32 for c in rel.as_posix()),"Unsafe path: "+str(rel))
        require(path.stat().st_size<=20_000_000,"Oversized package member: "+str(rel))
        result.append(path)
    keys=[unicodedata.normalize("NFC",p.relative_to(root).as_posix()).casefold() for p in result]
    require(len(keys)==len(set(keys)),"Case/normalization collision")
    return result


def relative_asset(root,value):
    require(isinstance(value,str) and value==value.strip() and value.startswith("./"),"Asset must be ./ relative path")
    p=PurePosixPath(value)
    require(not p.is_absolute() and ".." not in p.parts and "\\" not in value,"Unsafe asset path")
    resolved=root/value
    require(resolved.is_file() and not resolved.is_symlink(),"Missing asset: "+value)
    return resolved


def validate(root):
    root=Path(root).resolve()
    files=members(root)
    manifest=read_json(root/"plugin.json")
    require(manifest.get("$schema")==ROOT_SCHEMA,"Wrong portable manifest schema")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",manifest.get("name","")) and len(manifest["name"])<=64,"Invalid plugin name")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?",manifest.get("version","")),"Invalid version")
    require(not {"skills","mcpServers","apps","interface"}&set(manifest),"Legacy fields at portable manifest root")
    require(isinstance(manifest.get("description"),str) and bool(manifest["description"]),"Description missing")
    ext=manifest.get("extensions",{}).get("com.openai")
    require(isinstance(ext,dict),"OpenAI extension must be an object")
    interface=ext["interface"]
    for key,limit in (("displayName",30),("shortDescription",30),("developerName",80),("longDescription",4000)):
        value=interface.get(key)
        require(isinstance(value,str) and bool(value.strip()) and len(value)<=limit,"Bad interface "+key)
    require(interface.get("category")=="Productivity","Wrong category")
    require(isinstance(interface.get("capabilities"),list) and all(isinstance(x,str) for x in interface["capabilities"]),"Bad capabilities")
    prompts=interface.get("defaultPrompt",[])
    if isinstance(prompts,str):prompts=[prompts]
    require(len(prompts)<=3 and all(isinstance(x,str) and 0<len(x)<=128 for x in prompts),"Bad starter prompts")
    for key in ("logo","composerIcon"):
        asset=relative_asset(root,interface[key])
        svg=ET.fromstring(asset.read_bytes())
        require(svg.tag=="{http://www.w3.org/2000/svg}svg","Invalid SVG root")
        w,h=float(svg.get("width","0")),float(svg.get("height","0"))
        require(w==h and w>=48,"Icon must be square, at least 48px")
        require(not re.search(rb"<(?:script|foreignObject)|(?:href|src)=",asset.read_bytes(),re.I),"SVG must be self-contained")
    compat=read_json(root/".codex-plugin/plugin.json")
    require({p.name for p in (root/".codex-plugin").iterdir()}=={"plugin.json"},"Misplaced compatibility files")
    for key in ("name","version","description","author"):
        require(compat.get(key)==manifest.get(key),"Compatibility identity mismatch: "+key)
    require(compat.get("interface")==interface and compat.get("apps")==ext.get("apps"),"Compatibility settings differ")
    require(ext.get("apps")=="./.app.json","Google Drive app declaration missing")
    apps=read_json(root/".app.json")
    require(set(apps)=={"apps"} and set(apps["apps"])=={"google-drive"},"Unexpected app declarations")
    drive=apps["apps"]["google-drive"]
    require(drive.get("id")=="connector_5f3c8c41a1e54ad7a76272c89e2554fa" and drive.get("required") is True and "optional" not in drive,
            "Verified required Google Drive binding differs")
    require(not (root/"mcp.json").exists() and not (root/".mcp.json").exists(),"Unexpected server configuration")
    skills=list((root/"skills").iterdir())
    require(len(skills)==1 and skills[0].is_dir() and skills[0].name=="model-ocr","Exactly one intended Skill required")
    skill=skills[0]
    text=(skill/"SKILL.md").read_text(encoding="utf-8")
    require(text.startswith("---\n"),"Skill frontmatter missing")
    parts=text.split("---",2)
    meta=yaml.safe_load(parts[1])
    require(set(meta)=={"name","description"} and meta["name"]=="model-ocr" and isinstance(meta["description"],str),"Invalid Skill metadata")
    require(bool(parts[2].strip()) and len(text.splitlines())<=500,"Skill body missing/oversized")
    agent=yaml.safe_load((skill/"agents/openai.yaml").read_text(encoding="utf-8"))
    require(isinstance(agent.get("interface"),dict),"Agent interface missing")
    for key in ("display_name","short_description","default_prompt"):
        require(isinstance(agent["interface"].get(key),str) and bool(agent["interface"][key]),"Bad agent metadata")
    require(agent.get("policy",{}).get("allow_implicit_invocation") is True,"Invocation policy mismatch")
    require("dependencies" not in agent,"Do not invent host Python/shell tool dependencies")
    for file in files:
        if file.suffix==".json":read_json(file)
        elif file.suffix==".py":ast.parse(file.read_text(encoding="utf-8"),filename=file.name)
        elif file.suffix==".md":
            content=file.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)",content):
                if "://" in target or target.startswith("#"):continue
                target=target.split("#")[0]
                require((file.parent/target).exists(),f"Broken link in {file.relative_to(root)}: {target}")
    require((skill/"assets/DejaVuSans.ttf").is_file(),"Unicode font missing")
    require((root/"docs/SELF_EVALUATION.md").is_file(),"Source self-evaluation missing")
    return {"ok":True,"scope":"private","format":"Agent Plugins 1.0","name":manifest["name"],"version":manifest["version"],"skills":1,
            "app_bindings":1,"files":len(files),"bytes":sum(x.stat().st_size for x in files),"public_submission":"not_requested_not_certified"}


def package(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    result=validate(root)
    require(not output.is_relative_to(root),"Archive must be outside plugin root")
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in members(root):
            info=zipfile.ZipInfo(path.relative_to(root).as_posix(),(1980,1,1,0,0,0))
            info.create_system=3;info.external_attr=0o100644<<16
            z.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(output) as z:require(z.testzip() is None,"ZIP CRC failed")
    return {**result,"archive":str(output),"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"zip_bytes":output.stat().st_size}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("root");p.add_argument("--zip")
    args=p.parse_args()
    try:
        result=package(args.root,args.zip) if args.zip else validate(args.root)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
