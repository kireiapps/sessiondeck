# WebUI Sidebar Senkronizasyonu — Kök Sebep ve Çözüm

## Belirti
Script `delete` ile bir kartı sildikten sonra kart **WebUI sol panelinde
kalmaya devam ediyordu**. Kullanıcı her silmede WebUI'yi restart etmek
zorunda kalıyordu ("her seferinde restart mı edeceğiz?").

## Kök Sebep (iki katmanlı)
1. **Farklı veri kaynakları.** WebUI sol paneli
   `~/.hermes/webui/sessions/_index.json` (liste, `list[dict]`) +
   in-process cache'ten okur. Eski script ise
   `~/.hermes/webui/.sessions.json` (`{id: ts}` map) üzerinde çalışıyordu.
   İki dosya senkron değildi → script silince WebUI'nin gördüğü liste hiç
   değişmiyordu. (Teşhis anında: `.sessions.json` 1 kayıt, `_index.json`
   162 kayıt.)
2. **Canlı cache.** WebUI çalışırken sidebar listesini bellekte cache'ler
   (`_SESSIONS_CACHE`, TTL + stale-rebuild). Dosya *dışarıdan* silinse bile
   cache invalidate olmaz; yalnızca WebUI'nin kendi mutasyon yolları
   (`_publish_session_list_changed`) cache'i tazeler.

## Çözüm
`scripts/session_deck.py` içinde:
- `get_sessions()` / `save_sessions()` **`_index.json`'u tek otorite** yaptı
  (`.sessions.json` yalnızca geriye-uyumluluk için ayrıca güncellenir).
- `notify_webui_delete(sid)` eklendi: silme sonrası çalışan WebUI'ye
  best-effort REST çağrısı. WebUI kendi endpoint'inde tüm temizliği +
  canlı sidebar güncellemesini yapar.

## WebUI delete endpoint sözleşmesi (routes.py ~13791)
```
POST veya DELETE  /api/session/delete
Content-Type: application/json
Body: {"session_id": "<id>"}
→ 200 {"ok": true}
```
Endpoint kendi başına: SESSIONS.pop, sidecar `.json` + `.json.bak` unlink,
`prune_session_from_index`, tombstone, attachment dir, turn/run journal,
state.db (`delete_cli_session`), ve `_publish_session_list_changed(
"session_delete")` yapar. Yani elle disk temizliğiyle **fonksiyonel
eşdeğer**, artı sidebar'ı canlı günceller.

Reddedilen id türleri: read-only import, subagent view-only, messaging
session (bunlarda 400 döner — script yine diskten kendi prune'unu yapar).

## Host/Port
`HERMES_WEBUI_HOST` / `HERMES_WEBUI_PORT` (varsayılan `127.0.0.1:8787`;
kaynak: `api/config.py` PORT, `bootstrap.py` DEFAULT_PORT).

## Auth notu
Auth açıksa REST 401/403 döner → script sessizce atlar, disk+index prune
zaten yapıldığı için veri silinir; sidebar en geç WebUI'nin stale-cache
background rebuild'iyle (birkaç saniye) tazelenir. Yani restart yine gerekmez.

## Doğrulama reçetesi
```bash
SID=<kısa_id>
ls ~/.hermes/webui/sessions/$SID.json            # önce: VAR
grep -q "\"$SID\"" ~/.hermes/webui/sessions/_index.json  # önce: eşleşir
python3 scripts/session_deck.py delete --id "$SID"
ls ~/.hermes/webui/sessions/$SID.json            # sonra: YOK
grep -q "\"$SID\"" ~/.hermes/webui/sessions/_index.json  # sonra: eşleşmez
python3 scripts/session_deck.py stats            # Total 1 azalmış
```

## Genel ders (WebUI state'i dışarıdan değiştirirken)
Çalışan bir WebUI'nin dosyalarını script'le değiştirirken **daima onun REST
API'sini de tetikle**; yoksa in-process cache eski kalır ve kullanıcı
restart'a zorlanır. Doğru kaynak dosyayı da teyit et — WebUI'nin okuduğu
dosya (`_index.json`) ile eski/yan dosya (`.sessions.json`) karışabilir.
