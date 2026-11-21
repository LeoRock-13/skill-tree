# claude-manager

Inventario in sola lettura della configurazione di Claude Code: skill, plugin, MCP server, hook, CLAUDE.md/AGENTS.md.

    python3 -I scan.py          # genera index.html (contiene i TUOI dati: e' ignorato da git)
    CLAUDE_MANAGER_SKIP=Android,snap python3 -I scan.py   # cartelle extra da escludere

Schede: **Mappa** (stile floorplan: dove vivono skill, plugin, MCP e i collegamenti tra loro), **Albero** (cartelle del PC con CLAUDE.md, AGENTS.md, .claude, skill), Panoramica, Skill, Plugin, MCP, Hook, CLAUDE.md.

Gestione: `python3 -I server.py` → http://127.0.0.1:8765. Cambi lo stato delle skill (on / off / solo manuale) e abiliti/disabiliti i plugin; scrive solo in `~/.claude/settings.json` con backup in `backups/`.

Legge solo percorsi standard sotto $HOME. Non scrive fuori da questa cartella e non stampa valori di env/token.
