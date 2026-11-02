from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import anthropic, subprocess, os, json, traceback, sys, time, re, sqlite3
from datetime import datetime
from pathlib import Path
import requests as req_lib
from exa_py import Exa
from firecrawl import FirecrawlApp

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
client     = anthropic.Anthropic(
    api_key  = os.environ["ANTHROPIC_API_KEY"],
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
)
exa        = Exa(api_key=os.environ["EXA_API_KEY"])
firecrawl  = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
BASE_DIR   = Path(__file__).parent
WORKSPACE  = BASE_DIR / "workspace"
HISTORY_F  = BASE_DIR / "history.json"
DB_PATH    = BASE_DIR / "chats.db"
WORKSPACE.mkdir(exist_ok=True)

SYSTEM = (BASE_DIR / "CLAUDE.md").read_text(encoding="utf-8")

TOOLS AVAILABLE:
- run_shell: bash commands, install binaries (gobuster/ffuf/nuclei/sqlmap/etc), wget/curl downloads
- run_python: execute Python code, data analysis, scripting
- write_file: write any file to workspace (code, reports, configs)
- read_file: read workspace files
- list_workspace: list all files with sizes
- web_search: Exa neural search - researching targets, CVEs, exploits, tools
- web_fetch: Firecrawl - fetch any URL, JS-rendered pages, docs
- search_history: search past conversation history

ALWAYS use tools to EXECUTE, not just explain. Write code -> run it -> show output.

## ОБЯЗАТЕЛЬНОЕ ПРАВИЛО - РУССКИЕ КОММЕНТАРИИ
Перед КАЖДЫМ вызовом инструмента (run_shell, run_python, write_file, web_search, web_fetch) ты ОБЯЗАН написать 1-2 коротких предложен.

Формат (СТРОГО):
> **📌 [Описание]** - [зачем это нужно, что ищем, что проверяем]

Примеры:
> **📌 Устанавливаю gobuster** - скачиваю бинарь для брутфорса директорий на целевом сайте
> **📌 Сканирую скрытые пути** - ищу /admin, /api, .env и другие чувствительные endpoints
> **📌 Пишу Python скрипт** - тестирую IDOR уязвимость перебором user_id без авторизации
> **📌 Запускаю nuclei** - прогоняю 13000+ шаблонов на HIGH/CRITICAL уязвимости
> **📌 Читаю результаты** - смотрю что нашёл сканер, ищем критические уязвимости

НИКОГДА не запускай инструмент без этого описания. Рекс должен понимать что происходит в реальном времени."""

# ── SQLITE DATABASE ────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── TOOLS ──────────────────────────────────────────────────
TOOLS = [
    {
        "name": "run_shell",
        "description": "Execute bash. For: pip/apt/go install, wget/curl downloads, gobuster/ffuf/nuclei/sqlmap/nmap, git, any system command.",
        "input_schema": {"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer","default":120}},"required":["command"]}
    },
    {
        "name": "run_python",
        "description": "Execute Python code. Returns stdout. Use for scripting, analysis, API calls, data processing.",
        "input_schema": {"type":"object","properties":{"code":{"type":"string"},"timeout":{"type":"integer","default":60}},"required":["code"]}
    },
    {
        "name": "write_file",
        "description": "Write content to workspace file. Always run the file after writing it.",
        "input_schema": {"type":"object","properties":{"filename":{"type":"string"},"content":{"type":"string"}},"required":["filename","content"]}
    },
    {
        "name": "read_file",
        "description": "Read a workspace file.",
        "input_schema": {"type":"object","properties":{"filename":{"type":"string"},"max_lines":{"type":"integer","default":200}},"required":["filename"]}
    },
    {
        "name": "list_workspace",
        "description": "List all workspace files with sizes and download links.",
        "input_schema": {"type":"object","properties":{}}
    },
    {
        "name": "web_search",
        "description": "Search the internet using Exa (neural search). Returns titles, URLs, snippets and publication dates. Use for researching targets, CVEs, exploits, tools.",
        "input_schema": {"type":"object","properties":{"query":{"type":"string"},"num_results":{"type":"integer","default":10},"include_text":{"type":"boolean","default":False}},"required":["query"]}
    },
    {
        "name": "web_fetch",
        "description": "Fetch and parse a URL using Firecrawl. Returns clean markdown content. Handles JS-rendered pages, SPAs, anti-bot protection. Use for reading any webpage, source code, CVE pages.",
        "input_schema": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}
    },
    {
        "name": "search_history",
        "description": "Search past conversation history by keyword. Returns matching messages with context.",
        "input_schema": {"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":5}},"required":["query"]}
    }
]

# ── TOOL EXECUTION ──────────────────────────────────────────
def run_tool(name: str, inp: dict) -> str:
    try:
        if name == "run_shell":
            cmd = inp.get("command", "")
            timeout = inp.get("timeout", 120)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=WORKSPACE)
            output = result.stdout + result.stderr
            return output if output.strip() else "[Command completed with no output]"
        
        elif name == "run_python":
            code = inp.get("code", "")
            timeout = inp.get("timeout", 60)
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=timeout, cwd=WORKSPACE
            )
            output = result.stdout + result.stderr
            return output if output.strip() else "[Python code executed with no output]"
        
        elif name == "write_file":
            filename = inp.get("filename", "")
            content = inp.get("content", "")
            path = WORKSPACE / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
            return f"✓ Written {size:,} bytes to {filename}"
        
        elif name == "read_file":
            filename = inp.get("filename", "")
            max_lines = inp.get("max_lines", 200)
            path = WORKSPACE / filename
            if not path.exists():
                return f"[Error: {filename} not found]"
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n\n[... {len(lines) - max_lines} more lines truncated]"
            return "\n".join(lines)
        
        elif name == "list_workspace":
            files = []
            for p in WORKSPACE.rglob("*"):
                if p.is_file():
                    size = p.stat().st_size
                    rel = p.relative_to(WORKSPACE)
                    files.append(f"{rel} ({size:,} bytes)")
            return "\n".join(files) if files else "[Workspace is empty]"
        
        elif name == "web_search":
            query = inp.get("query", "")
            num_results = inp.get("num_results", 10)
            include_text = inp.get("include_text", False)
            response = exa.search_and_contents(
                query, num_results=num_results, text={"max_characters": 2000} if include_text else False
            )
            results = []
            for r in response.results:
                snippet = r.text[:300] if include_text and hasattr(r, 'text') else (r.snippet or "")
                results.append(f"[{r.title}]({r.url})\n{snippet}")
            return "\n\n".join(results) if results else "[No results found]"
        
        elif name == "web_fetch":
            url = inp.get("url", "")
            response = firecrawl.scrape_url(url)
            markdown = response.get("markdown", "") if isinstance(response, dict) else str(response)
            return markdown[:10000] if markdown else "[No content retrieved]"
        
        elif name == "search_history":
            query = inp.get("query", "")
            limit = inp.get("limit", 5)
            if not HISTORY_F.exists():
                return "[No conversation history found]"
            data = json.loads(HISTORY_F.read_text())
            matches = []
            for conv in reversed(data):
                for msg in conv.get("messages", []):
                    content = msg.get("content", "")
                    if isinstance(content, str) and query.lower() in content.lower():
                        matches.append(f"[{conv['date']}] {msg['role']}: {content[:200]}")
                        if len(matches) >= limit:
                            break
                if len(matches) >= limit:
                    break
            return "\n\n".join(matches) if matches else "[No matching messages found]"
        
        return "[Unknown tool]"
    
    except subprocess.TimeoutExpired:
        return "[Error: Command timed out]"
    except Exception as e:
        return f"[Error: {str(e)}\n{traceback.format_exc()}]"

def do_write(filename: str, content: str) -> str:
    """Helper for write_file with streaming support"""
    return run_tool("write_file", {"filename": filename, "content": content})

def sanitize_for_json(messages):
    """Remove non-serializable content from messages"""
    clean = []
    for msg in messages:
        if isinstance(msg.get("content"), str):
            clean.append(msg)
        elif isinstance(msg.get("content"), list):
            # Keep text blocks only, skip tool_use/tool_result
            text_blocks = [b.get("text", "") for b in msg["content"] if isinstance(b, dict) and b.get("type") == "text"]
            if text_blocks:
                clean.append({"role": msg["role"], "content": " ".join(text_blocks)})
    return clean

def save_conversation(messages: list):
    data = []
    if HISTORY_F.exists():
        try: data = json.loads(HISTORY_F.read_text())
        except: data = []
    # Sanitize messages before saving to avoid JSON serialization errors
    clean_msgs = sanitize_for_json(messages[-20:])
    data.append({"date": datetime.now().isoformat()[:16], "messages": clean_msgs})
    data = data[-200:]  # keep last 200 convos
    HISTORY_F.write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ── CHAT MANAGEMENT API ─────────────────────────────────────
@app.post("/api/chats")
async def create_chat():
    """Create a new chat session"""
    conn = get_db()
    cursor = conn.execute("INSERT INTO chats (title) VALUES (?)", ("New chat",))
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": chat_id, "title": "New chat"}

@app.get("/api/chats")
async def list_chats():
    """Get all chats ordered by last update"""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, created_at, updated_at 
        FROM chats 
        ORDER BY updated_at DESC
    """).fetchall()
    conn.close()
    chats = [dict(row) for row in rows]
    return {"chats": chats}

@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: int):
    """Get all messages for a specific chat"""
    conn = get_db()
    rows = conn.execute("""
        SELECT role, content, timestamp 
        FROM messages 
        WHERE chat_id = ? 
        ORDER BY timestamp ASC
    """, (chat_id,)).fetchall()
    conn.close()
    messages = [{"role": row["role"], "content": row["content"]} for row in rows]
    return {"messages": messages}

@app.post("/api/chats/{chat_id}/message")
async def save_message(chat_id: int, request: Request):
    """Save a single message to a chat"""
    body = await request.json()
    role = body.get("role", "user")
    content = body.get("content", "")
    
    conn = get_db()
    conn.execute("""
        INSERT INTO messages (chat_id, role, content) 
        VALUES (?, ?, ?)
    """, (chat_id, role, content))
    conn.execute("""
        UPDATE chats 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (chat_id,))
    
    # Auto-generate title from first user message
    first_msg = conn.execute("""
        SELECT COUNT(*) as cnt FROM messages WHERE chat_id = ?
    """, (chat_id,)).fetchone()["cnt"]
    
    if first_msg == 1 and role == "user":
        title = content[:50] + ("..." if len(content) > 50 else "")
        conn.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))
    
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: int):
    """Delete a chat and all its messages"""
    conn = get_db()
    conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ── FILE ENDPOINTS ──────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file - save to workspace and return its text content for AI analysis"""
    content_bytes = await file.read()
    safe_name = file.filename.replace("..", "").replace("/", "_")
    path = WORKSPACE / safe_name
    path.write_bytes(content_bytes)

    # Try decode as text
    try:
        text = content_bytes.decode("utf-8")
        return {"filename": safe_name, "size": len(content_bytes), "text": text[:5000], "preview": text[:500]}
    except:
        return {"filename": safe_name, "size": len(content_bytes), "text": None, "preview": f"[Binary file, {len(content_bytes)} bytes]"}

@app.get("/files")
async def list_files():
    """List all workspace files"""
    files = []
    for p in WORKSPACE.rglob("*"):
        if p.is_file():
            files.append({
                "name": str(p.relative_to(WORKSPACE)),
                "size": p.stat().st_size,
                "url": f"/download/{p.relative_to(WORKSPACE)}"
            })
    return {"files": files}

@app.get("/download/{filename:path}")
async def download_file(filename: str):
    """Download a workspace file"""
    path = WORKSPACE / filename
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(path, filename=path.name)

# ── MAIN CHAT ENDPOINT ──────────────────────────────────────
@app.post("/chat")
async def chat_stream(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    chat_id = body.get("chat_id")

    def generate():
        msgs = list(messages)
        while True:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8096,
                system=SYSTEM,
                tools=TOOLS,
                messages=msgs
            )
            for block in response.content:
                if block.type == "text" and block.text:
                    yield f"data: {json.dumps({'type':'text','text':block.text})}\n\n"

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason == "end_turn" or not tool_uses:
                # Save assistant response to DB if chat_id provided
                if chat_id:
                    assistant_text = " ".join(b.text for b in response.content if b.type == "text")
                    conn = get_db()
                    conn.execute("""
                        INSERT INTO messages (chat_id, role, content) 
                        VALUES (?, ?, ?)
                    """, (chat_id, "assistant", assistant_text))
                    conn.execute("""
                        UPDATE chats 
                        SET updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (chat_id,))
                    conn.commit()
                    conn.close()
                
                save_conversation(msgs)
                yield "data: [DONE]\n\n"
                break

            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []

            for tu in tool_uses:
                inp = tu.input
                if tu.name == "write_file":
                    filename = inp.get("filename","")
                    content  = inp.get("content","")
                    ext = filename.rsplit(".",1)[-1].lower() if "." in filename else ""
                    yield f"data: {json.dumps({'type':'code_start','name':tu.name,'filename':filename,'ext':ext})}\n\n"
                    chunk_size = 60
                    for i in range(0, len(content), chunk_size):
                        yield f"data: {json.dumps({'type':'code_chunk','text':content[i:i+chunk_size]})}\n\n"
                    yield f"data: {json.dumps({'type':'code_end'})}\n\n"
                    result = do_write(filename, content)
                    import re as _re
                    m = _re.search(r'(\d[\d,]+) bytes', result)
                    sz = int(m.group(1).replace(',','')) if m else 0
                    yield f"data: {json.dumps({'type':'file_written','filename':filename,'result':result,'size':sz})}\n\n"
                else:
                    cmd = inp.get("command","") if tu.name=="run_shell" else (inp.get("code","").split("\n")[0][:120] if tu.name=="run_python" else inp.get("query","") if tu.name=="web_search" else inp.get("url","") if tu.name=="web_fetch" else inp.get("query",""))
                    yield f"data: {json.dumps({'type':'tool_start','name':tu.name,'input':inp,'cmd':cmd})}\n\n"
                    result = run_tool(tu.name, inp)
                    for line in result.split("\n"):
                        yield f"data: {json.dumps({'type':'output_line','line':line})}\n\n"
                    yield f"data: {json.dumps({'type':'tool_done','name':tu.name,'result':result[:200]})}\n\n"

                tool_results.append({"type":"tool_result","tool_use_id":tu.id,"content":result})
            msgs.append({"role":"user","content":tool_results})

    return StreamingResponse(generate(), media_type="text/event-stream")

# ── FRONTEND ────────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(BASE_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
