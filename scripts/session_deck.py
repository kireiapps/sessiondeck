#!/usr/bin/env python3
"""
Session Deck — Hermes WebUI session'larını kart destesi olarak yönet.

Tasarım ilkeleri (önceki sürümlerdeki gerçek hatalardan öğrenilenler):
1. Kanonik kart id'si HER ZAMAN dosya adıdır (uzantısız). Dosya içindeki
   'session_id' alanına asla index anahtarı olarak güvenilmez.
2. HERMES_HOME otomatik tespit edilir: birkaç aday yol denenir, hangisinde
   gerçekten session verisi varsa o kullanılır. Bu, agent'ın script'i farklı
   bir $HOME altında çalıştırdığı (ve sessizce yanlış/boş klasörde işlem
   yaptığı) sandbox senaryolarını engellemek içindir. --hermes-home ile
   elle override edilebilir.
3. Her yazma işlemi atomiktir (tmp dosyaya yaz + rename) — yarım yazılmış
   bozuk JSON riski yok.
4. delete/inspect komutları işlemden SONRA diskte gerçekten ne olduğunu
   tekrar okuyup doğrular; "başarılı" mesajı yalnızca gerçekten doğrulanmış
   bir değişiklik varsa basılır.
"""

import json
import os
import re
import random
import sys
import argparse
import datetime
import tempfile

ID_RE = re.compile(r'^[A-Za-z0-9_-]+$')


# ── HERMES_HOME tespiti ─────────────────────────────────────────────

def _candidate_hermes_homes():
    seen = []
    def add(p):
        if p and p not in seen:
            seen.append(p)
    add(os.environ.get('HERMES_HOME'))
    add(os.path.expanduser('~/.hermes'))
    home_env = os.environ.get('HOME')
    if home_env:
        add(os.path.join(home_env, '.hermes'))
    add(os.path.expanduser('~/.config/hermes'))
    add('/root/.hermes')
    return seen

def detect_hermes_home(explicit=None):
    """Aday yolları dener, webui/sessions içinde en az bir .json dosyası
    olan İLK adayı seçer. Hiçbiri uygun değilse, ilk adayı (varsayılan
    davranış) döndürür ki en azından 'fix'/'init' ile başlanabilsin."""
    candidates = [explicit] if explicit else _candidate_hermes_homes()
    fallback = candidates[0] if candidates else os.path.expanduser('~/.hermes')

    for c in candidates:
        if not c:
            continue
        sdir = os.path.join(c, 'webui', 'sessions')
        if os.path.isdir(sdir):
            try:
                has_files = any(f.endswith('.json') and not f.startswith('_')
                                 for f in os.listdir(sdir))
            except OSError:
                has_files = False
            if has_files:
                return c
    return fallback


# ── path yardımcıları (main() içinde HERMES_HOME belirlendikten sonra set edilir) ──

class Paths:
    def __init__(self, hermes_home):
        self.home = hermes_home
        self.sessions_json = os.path.join(hermes_home, 'webui', '.sessions.json')
        self.sessions_dir = os.path.join(hermes_home, 'webui', 'sessions')
        self.webui_index = os.path.join(self.sessions_dir, '_index.json')
        self.webui_deleted = os.path.join(self.sessions_dir, '_deleted_webui_sessions.json')


# ── atomik dosya işlemleri ──────────────────────────────────────────

def _atomic_write(path, text):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=d, prefix='.tmp_', suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

def _safe_id(sid):
    if not sid or not ID_RE.match(sid) or '..' in sid:
        return None
    return sid


# ── veri katmanı ─────────────────────────────────────────────────────

def get_sessions(P):
    """Deck listesi = WebUI'nin gerçek sidebar kaynağı olan _index.json.
    Script ile WebUI AYNI listeyi görsün ki bir kart discard edilince
    sol panel (REST + cache invalidate ile) anında güncellensin.
    Eski .sessions.json artık kullanılmıyor; _index.json tek otorite."""
    return {e.get('session_id'): (e.get('updated_at') or e.get('created_at') or 0)
            for e in get_webui_index(P) if e.get('session_id')}

def save_sessions(P, sessions_dict):
    """_index.json'u yalnızca sessions_dict'teki anahtarlara göre prune et
    (WebUI ile birebir uyumlu). Fallback olarak eski .sessions.json'u da
    güncelle ki başka bir araç onu okusa bile tutarlı kalsın."""
    idx = [e for e in get_webui_index(P) if e.get('session_id') in sessions_dict]
    save_webui_index(P, idx)
    prefix = '1|'
    if os.path.exists(P.sessions_json):
        with open(P.sessions_json, 'r') as f:
            raw = f.read().strip()
        if '|' in raw:
            prefix = raw.split('|', 1)[0] + '|'
    _atomic_write(P.sessions_json, f"{prefix}{json.dumps(sessions_dict)}")

def get_webui_index(P):
    if not os.path.exists(P.webui_index):
        return []
    try:
        with open(P.webui_index, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_webui_index(P, index_list):
    _atomic_write(P.webui_index, json.dumps(index_list, indent=2))

def get_deleted_ids(P):
    if not os.path.exists(P.webui_deleted):
        return {"version": 1, "ids": []}
    try:
        with open(P.webui_deleted, 'r') as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "ids": []}

def save_deleted_ids(P, data):
    _atomic_write(P.webui_deleted, json.dumps(data))

def get_session_content(P, session_id):
    sid = _safe_id(session_id)
    if not sid:
        return None
    path = os.path.join(P.sessions_dir, f"{sid}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def resolve_id(P, prefix):
    """Tam id ya da (tekilse) dosya-adı öneki çözer. `list` çıktısındaki
    değeri doğrudan yapıştırabilmen için trailing '...' toleranslıdır."""
    prefix = (prefix or '').strip().rstrip('.')
    safe_prefix = re.sub(r'[^A-Za-z0-9_-]', '', prefix)
    if not safe_prefix:
        return None, "Geçersiz id."

    if os.path.exists(os.path.join(P.sessions_dir, f"{safe_prefix}.json")):
        return safe_prefix, None

    try:
        candidates = [
            f[:-5] for f in os.listdir(P.sessions_dir)
            if f.endswith('.json') and not f.startswith('_') and f.startswith(safe_prefix)
        ]
    except FileNotFoundError:
        candidates = []

    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        return None, f"'{prefix}' birden fazla karta uyuyor ({len(candidates)}), tam id ver."
    return None, f"'{prefix}' ile eşleşen kart yok. `list` veya `fix` dene."


# ── görüntüleme yardımcıları ────────────────────────────────────────

def _fmt_ts(ts):
    if ts is None:
        return None
    try:
        if isinstance(ts, str):
            try:
                return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            except ValueError:
                ts = float(ts)
        ts = float(ts)
        if ts > 1e12:
            ts = ts / 1000.0
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return None

def _preview_text(content, limit):
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block['text'] if isinstance(block.get('text'), str) else f"[{block.get('type', 'block')}]")
            else:
                parts.append(str(block))
        text = ' '.join(parts)
    else:
        text = '' if content is None else str(content)
    text = text.replace('\n', ' ')
    return text if len(text) <= limit else text[:limit - 3] + "..."


# ── işlemler ─────────────────────────────────────────────────────────

def fix_index(P):
    """Index'i diskteki dosyalardan yeniden kurar. Anahtar HER ZAMAN dosya
    adıdır — içerideki 'session_id' alanı asla anahtar olarak kullanılmaz."""
    if not os.path.isdir(P.sessions_dir):
        os.makedirs(P.sessions_dir, exist_ok=True)
        return {"fixed": 0, "errors": 0, "total": 0}

    files = [f for f in os.listdir(P.sessions_dir)
             if f.endswith('.json') and not f.startswith('_')]

    new_index_map, new_webui_list = {}, []
    fixed = errors = 0

    for filename in files:
        sid = filename[:-5]
        path = os.path.join(P.sessions_dir, filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            ts = data.get('updated_at') or data.get('created_at') or os.path.getmtime(path)
            new_index_map[sid] = ts
            new_webui_list.append({
                "session_id": sid,
                "title": data.get('title', 'Untitled'),
                "workspace": data.get('workspace', ''),
                "model": data.get('model', ''),
                "model_provider": data.get('model_provider', ''),
                "message_count": len(data.get('messages', [])),
                "created_at": data.get('created_at', ts),
                "updated_at": data.get('updated_at', ts),
                "last_message_at": data.get('last_message_at', ts),
                "pinned": data.get('pinned', False),
                "archived": data.get('archived', False),
                "project_id": data.get('project_id'),
                "profile": data.get('profile', 'default'),
                "input_tokens": data.get('input_tokens', 0),
                "output_tokens": data.get('output_tokens', 0),
                "estimated_cost": data.get('estimated_cost', 0.0),
                "cache_read_tokens": data.get('cache_read_tokens', 0),
                "cache_write_tokens": data.get('cache_write_tokens', 0),
                "is_streaming": data.get('is_streaming', False),
                "read_only": data.get('read_only', False),
                "source_label": data.get('source_label', ''),
                "manual_title": data.get('manual_title', None),
            })
            fixed += 1
        except Exception:
            errors += 1

    save_sessions(P, new_index_map)
    save_webui_index(P, new_webui_list)
    save_deleted_ids(P, {"version": 1, "ids": []})
    return {"fixed": fixed, "errors": errors, "total": len(new_webui_list)}

def get_session_display(P, sid, mode='quick'):
    content = get_session_content(P, sid)
    if not content:
        return None
    msgs = content.get('messages', [])
    date_raw = content.get('updated_at') or content.get('last_message_at') or content.get('created_at')
    display = {
        "id": sid,
        "title": content.get('title', 'Untitled Session'),
        "date": _fmt_ts(date_raw),
        "created": _fmt_ts(content.get('created_at')),
    }
    if mode == 'quick':
        display["preview"] = [f"[{m.get('role','unknown')}] {_preview_text(m.get('content',''), 100)}" for m in msgs[-3:]]
    elif mode == 'deep':
        display["preview"] = [f"[{m.get('role','unknown')}] {_preview_text(m.get('content',''), 300)}" for m in msgs[-10:]]
    elif mode == 'full':
        display["full_content"] = msgs
    return display

def pick_random_session(P, mode='quick'):
    sessions = get_sessions(P)
    if not sessions:
        return None
    ids = list(sessions.keys())
    random.shuffle(ids)
    for sid in ids:
        display = get_session_display(P, sid, mode=mode)
        if display:
            return display
    return None

def _webui_api_base():
    host = os.environ.get('HERMES_WEBUI_HOST', '127.0.0.1')
    port = os.environ.get('HERMES_WEBUI_PORT', '8787')
    return f"http://{host}:{port}"

def notify_webui_delete(sid):
    """Çalışan WebUI'ye silme olayını REST ile bildirir ki sidebar cache'i
    anında invalidate olsun (restart gerektirmesin). Best-effort: API'ye
    ulaşılamaz ya da auth gerektiriyorsa sessizce False döner; disk
    temizliği ayrıca yapıldığı için veri yine de silinir. WebUI kendi
    endpoint'inde zaten dosyayı, index'i, journal'ları ve state.db'yi
    temizliyor + _publish_session_list_changed ile sidebar'ı canlı güncelliyor."""
    import urllib.request as _ur
    import urllib.error as _ue
    url = f"{_webui_api_base()}/api/session/delete"
    data = json.dumps({"session_id": sid}).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    last = None
    for method in ("POST", "DELETE"):
        req = _ur.Request(url, data=data, headers=headers, method=method)
        try:
            with _ur.urlopen(req, timeout=3) as r:
                if r.status in (200, 202, 204):
                    return True, f"api {method} ok"
        except _ue.HTTPError as e:
            last = e.code
            if e.code in (401, 403):
                return False, f"auth {e.code} (elle silindi)"
        except Exception as e:
            last = str(e)[:60]
    return False, f"unreachable ({last})"

def delete_session(P, sid):
    """Siler ve SONRADAN diski tekrar okuyup gerçekten silinip silinmediğini
    doğrular. Sadece doğrulanmış bir değişiklik varsa True döner.
    Ayrıca çalışan WebUI'yi REST ile haberdar eder ki sidebar restart
    beklemeden güncellensin."""
    # ── canlı WebUI'yi haberdar et (best-effort) ──
    webui_ok, webui_detail = False, "atlandı"
    try:
        webui_ok, webui_detail = notify_webui_delete(sid)
    except Exception as e:
        webui_detail = f"notify hata: {e}"

    sessions = get_sessions(P)
    if sid in sessions:
        del sessions[sid]
        save_sessions(P, sessions)

    safe = _safe_id(sid)
    path = os.path.join(P.sessions_dir, f"{safe}.json") if safe else None
    if path and os.path.exists(path):
        os.remove(path)

    try:
        webui_idx = get_webui_index(P)
        new_idx = [e for e in webui_idx if e.get('session_id') != sid]
        if len(new_idx) != len(webui_idx):
            save_webui_index(P, new_idx)
    except Exception:
        pass

    try:
        deleted = get_deleted_ids(P)
        if sid not in deleted['ids']:
            deleted['ids'].append(sid)
            save_deleted_ids(P, deleted)
    except Exception:
        pass

    # ── doğrulama: diski tekrar oku ──
    still_in_index = sid in get_sessions(P)
    still_on_disk = path and os.path.exists(path)
    if still_in_index or still_on_disk:
        reasons = []
        if still_in_index:
            reasons.append("index'te hâlâ mevcut")
        if still_on_disk:
            reasons.append("dosya diskte hâlâ mevcut")
        return False, f"Silme doğrulanamadı ({', '.join(reasons)}). Muhtemelen HERMES_HOME yanlış çözümleniyor veya izin sorunu var — `debug` çalıştır."
    tag = "" if webui_ok else f" · webui: {webui_detail}"
    return True, f"ok{tag}"


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Session Deck - Kart destesi oyunu")
    parser.add_argument("cmd", choices=["pick", "delete", "list", "inspect", "stats", "fix", "debug"])
    parser.add_argument("--id", help="Tam id ya da `list`'ten kopyalanan kısaltılmış önek")
    parser.add_argument("--mode", choices=["quick", "deep", "full"], default="quick")
    parser.add_argument("--hermes-home", help="HERMES_HOME'u elle belirt (otomatik tespiti bypass eder)")
    args = parser.parse_args()

    hh = detect_hermes_home(explicit=args.hermes_home)
    P = Paths(hh)

    if args.cmd == "debug":
        candidates = _candidate_hermes_homes()
        info = {
            "$USER": os.environ.get('USER') or os.environ.get('USERNAME'),
            "$HOME": os.environ.get('HOME'),
            "$HERMES_HOME (env, raw)": os.environ.get('HERMES_HOME'),
            "denenen adaylar": candidates,
            "SEÇİLEN hermes_home": hh,
            "sessions_json": {"path": P.sessions_json, "exists": os.path.exists(P.sessions_json)},
            "sessions_dir": {
                "path": P.sessions_dir,
                "exists": os.path.isdir(P.sessions_dir),
                "writable": os.access(P.sessions_dir, os.W_OK) if os.path.isdir(P.sessions_dir) else None,
                "json_file_count": (len([f for f in os.listdir(P.sessions_dir) if f.endswith('.json')])
                                     if os.path.isdir(P.sessions_dir) else None),
            },
            "index_entry_count": len(get_sessions(P)),
            "cwd": os.getcwd(),
            "script_path": os.path.abspath(__file__),
        }
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return

    if args.cmd == "fix":
        print(json.dumps(fix_index(P)))

    elif args.cmd == "pick":
        res = pick_random_session(P, mode=args.mode)
        print(json.dumps(res) if res else "No sessions found.")

    elif args.cmd == "delete":
        if not args.id:
            print("Error: --id required"); return
        sid, err = resolve_id(P, args.id)
        if not sid:
            print(f"❌ {err}"); return
        ok, detail = delete_session(P, sid)
        print(f"🔥 Discarded: {sid}" if ok else f"❌ Failed to discard {sid}: {detail}")

    elif args.cmd == "list":
        sessions = get_sessions(P)
        if not sessions:
            print("(deste boş)")
        for sid, ts in sorted(sessions.items(), key=lambda x: x[1], reverse=True):
            dt = _fmt_ts(ts) or '????-??-?? ??:??'
            content = get_session_content(P, sid)
            title = content.get('title', 'Untitled') if content else 'BROKEN'
            print(f"  {dt}  {sid}  {title[:40]}")

    elif args.cmd == "stats":
        sessions = get_sessions(P)
        valid = sum(1 for s in sessions if get_session_content(P, s))
        print(f"HERMES_HOME kullanılan: {hh}")
        print(f"Total in deck:         {len(sessions)}")
        print(f"Valid cards:           {valid}")
        print(f"Broken:                {len(sessions) - valid}")
        print(f"WebUI _index entries:  {len(get_webui_index(P))}")

    elif args.cmd == "inspect":
        if not args.id:
            print("Error: --id required"); return
        sid, err = resolve_id(P, args.id)
        if not sid:
            print(f"❌ {err}"); return
        res = get_session_display(P, sid, mode=args.mode)
        print(json.dumps(res, indent=2) if res else "Card not found.")


if __name__ == "__main__":
    main()
