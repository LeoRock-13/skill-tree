#!/usr/bin/env python3
"""claude-manager: inventario in sola lettura di skill, plugin, MCP, hook e file CLAUDE.md.

Uso: python3 -I scan.py   ->  scrive index.html accanto allo script.
Non modifica nulla fuori da questa cartella. Non legge ne' stampa valori di env/token degli MCP.
"""
import json, os, re, glob, html
from pathlib import Path

HOME = Path.home()
HERE = Path(__file__).resolve().parent
SKIP = {"node_modules", ".cache", ".git", ".venv", "venv", "__pycache__", ".npm", ".cargo", ".rustup", "target", "dist", "build", ".next"}

SKIP |= set(filter(None, os.environ.get("CLAUDE_MANAGER_SKIP", "").split(",")))  # cartelle extra da ignorare, es. Android,snap


def rj(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return {}


def frontmatter(p):
    try:
        t = Path(p).read_text(errors="ignore")
    except Exception:
        return {}
    m = re.match(r"^---\n(.*?)\n---", t, re.S)
    out = {}
    if m:
        cur = None
        for line in m.group(1).splitlines():
            k = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
            if k:
                cur = k.group(1)
                out[cur] = k.group(2).strip().strip("'\"")
                if out[cur] in (">", "|", ">-", "|-"):
                    out[cur] = ""
            elif cur and line.startswith(" "):
                out[cur] = (out[cur] + " " + line.strip()).strip()
    return out


settings = rj(HOME / ".claude/settings.json")
overrides = settings.get("skillOverrides", {})
enabled_plugins = settings.get("enabledPlugins", {})

# ---------- skills ----------
skills = []


def add_skill(name, path, source, group):
    fm = frontmatter(Path(path) / "SKILL.md")
    real = os.path.realpath(path)
    skills.append({
        "name": name,
        "desc": fm.get("description", "")[:300],
        "source": source,
        "group": group,
        "path": str(path).replace(str(HOME), "~"),
        "link": real.replace(str(HOME), "~") if real != str(path) else "",
        "state": overrides.get(name, "on"),
    })


for d in sorted(glob.glob(str(HOME / ".claude/skills/*"))):
    add_skill(os.path.basename(d), d, "utente", "~/.claude/skills")
for d in sorted(glob.glob(str(HOME / ".agents/skills/*"))):
    add_skill(os.path.basename(d), d, "agents", "~/.agents/skills")

# ---------- plugin ----------
plugins = []
inst = rj(HOME / ".claude/plugins/installed_plugins.json").get("plugins", {})
for key, versions in inst.items():
    v = versions[0] if versions else {}
    ip = Path(v.get("installPath", ""))
    pskills = sorted(glob.glob(str(ip / "skills/*/SKILL.md")))
    cmds = sorted(glob.glob(str(ip / "commands/*.md")))
    agents = sorted(glob.glob(str(ip / "agents/*.md")))
    hooks = (ip / "hooks").exists()
    mcp = (ip / ".mcp.json").exists()
    plugins.append({
        "id": key, "version": v.get("version", ""), "scope": v.get("scope", ""),
        "enabled": enabled_plugins.get(key, False),
        "skills": [Path(p).parent.name for p in pskills],
        "commands": [Path(p).stem for p in cmds],
        "agents": [Path(p).stem for p in agents],
        "hooks": hooks, "mcp": mcp,
        "path": str(ip).replace(str(HOME), "~"),
    })
    for p in pskills:
        n = Path(p).parent.name
        fm = frontmatter(p)
        skills.append({
            "name": f"{key.split('@')[0]}:{n}", "desc": fm.get("description", "")[:300],
            "source": "plugin", "group": key, "path": str(Path(p).parent).replace(str(HOME), "~"),
            "link": "", "state": overrides.get(f"{key.split('@')[0]}:{n}", overrides.get(n, "on")),
        })

# ---------- MCP ----------
mcp = []


def add_mcp(name, cfg, scope, where):
    mcp.append({
        "name": name, "scope": scope, "where": where.replace(str(HOME), "~"),
        "type": cfg.get("type") or ("stdio" if cfg.get("command") else "?"),
        "target": cfg.get("url") or " ".join([cfg.get("command", "")] + [a for a in cfg.get("args", []) if not re.search(r"(key|token|secret|pass)", a, re.I)])[:120],
        "env_keys": sorted(cfg.get("env", {}).keys()) if isinstance(cfg.get("env"), dict) else [],
    })


cj = rj(HOME / ".claude.json")
for n, c in cj.get("mcpServers", {}).items():
    add_mcp(n, c, "globale (utente)", "~/.claude.json")
for proj, v in cj.get("projects", {}).items():
    for n, c in v.get("mcpServers", {}).items():
        add_mcp(n, c, "progetto", proj)
for n, c in settings.get("mcpServers", {}).items():
    add_mcp(n, c, "settings.json", "~/.claude/settings.json")
for f in glob.glob(str(HOME / "**/.mcp.json"), recursive=True)[:200]:
    if any(s in f.split(os.sep) for s in SKIP) or "/.claude/plugins/" in f:
        continue
    for n, c in rj(f).get("mcpServers", {}).items():
        add_mcp(n, c, "progetto (.mcp.json)", f)

# ---------- hook ----------
hooks = []
for ev, entries in settings.get("hooks", {}).items():
    for e in entries:
        for h in e.get("hooks", []):
            hooks.append({"event": ev, "matcher": e.get("matcher", ""), "cmd": (h.get("command") or h.get("type", ""))[:140]})

# ---------- CLAUDE.md / AGENTS.md ----------
memfiles = []
dotdirs = []
for root, dirs, files in os.walk(HOME):
    dirs[:] = [d for d in dirs if d not in SKIP and (not d.startswith(".") or d in (".claude", ".agents"))]
    for d in dirs:
        if d in (".claude", ".agents"):
            dp = Path(root) / d
            info = {"path": str(dp).replace(str(HOME), "~"), "kind": d}
            for sub in ("skills", "commands", "agents"):
                sp = dp / sub
                info[sub] = len([x for x in sp.iterdir()]) if sp.is_dir() else 0
            info["files"] = sorted(x for x in ("settings.json", "settings.local.json", "CLAUDE.md", ".mcp.json") if (dp / x).exists())
            dotdirs.append(info)
    if root.count(os.sep) - str(HOME).count(os.sep) > 6:
        dirs[:] = []
    if "/.claude/plugins" in root or "/.claude/projects" in root or "/.local/" in root:
        dirs[:] = []
        continue
    for f in files:
        if f in ("CLAUDE.md", "AGENTS.md", "CLAUDE.local.md"):
            p = Path(root) / f
            try:
                size = p.stat().st_size
            except OSError:
                continue
            memfiles.append({"path": str(p).replace(str(HOME), "~"), "dir": root.replace(str(HOME), "~") or "~",
                             "file": f, "size": size, "symlink": p.is_symlink()})
memfiles.sort(key=lambda m: m["path"])

data = {"skills": skills, "plugins": plugins, "mcp": mcp, "hooks": hooks, "memfiles": memfiles, "dotdirs": dotdirs,
        "settings": {"overrides": len(overrides), "plugins": len(enabled_plugins), "hooks": len(hooks)}}

if __name__ == "__main__":
    tpl = (HERE / "template.html").read_text()
    out = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    (HERE / "index.html").write_text(out)
    print(f"dotdirs={len(dotdirs)} skills={len(skills)} plugins={len(plugins)} mcp={len(mcp)} hooks={len(hooks)} memfiles={len(memfiles)} -> {HERE/'index.html'}")
