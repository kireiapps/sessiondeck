---
name: session-deck
description: Hermes WebUI session'larını bir kart destesine dönüştürür. Çek, incele, yok et, skill yap veya memory'e kazı.
author: KIREI (https://kirei.com.tr)
license: MIT
---

# Session Deck

> Geçmiş oturumların bir dijital kart destesine dönüşsün. Her kart bir anı, bir karar, bir ders.
> **[KIREI](https://kirei.com.tr)**

## 🃏 Mekanik Nedir?

Hermes WebUI'da zamanla biriken ve sistemin zihnini bulandıran eski sohbet oturumları (session'lar), senin için karıştırılmış bir dijital kart destesine dönüşür. Her kart; başlık, son güncellenme tarihi ve önizleme ile gelir. Desteden her kart çektiğinde geçmiş bir oturumla yüzleşirsin. Karar senin:

- **🔥 Discard / Burn (Desteden At / Yok Et)** — Artık yük olan bir debug çöplüğünü, başarısız bir testi veya eskimiş bir bağlamı kalıcı olarak sil ve desteyi hafiflet.
- **✨ Distill (Damıt / Skill Yap)** — Kartın içindeki karmaşayı süz; içinden tekrar kullanılabilir saf bir iş akışı (skill) çıkar ve Hermes'e kazandır.
- **🧠 Imprint (Zihne Kazı / Memory)** — Gelecekteki kararları etkileyecek kritik bir tercihi, kuralı veya notu Hermes'in kalıcı hafızasına mühürle.
- **👁️ Inspect (Derinlemesine İncele)** — Karar vermeden önce kartın katmanlarına in; son mesajlarını veya tüm geçmişini gör.
- **⏭️ Pass (Destenin Altına Koy / Geç)** — Bu oturumu şimdilik yaşat, destenin en altına gönder ve sıradaki karta geç.

## 📦 Kurulum

```bash
cp -r session-deck ~/.hermes/skills/automation/session-deck
```

Klasöre kopyalamak yeterlidir; Hermes skill'i oradan otomatik okur.
**Not:** `hermes skills sync` diye bir komut YOKTUR (bu sürümde `hermes skills`
alt komutları: browse/search/install/inspect/list/check/update/... — `sync` yok).
Kurulumu doğrula: `hermes skills list | grep session-deck` → `enabled` görmelisin.
Kurduktan sonra `scripts/session_deck.py debug` çalıştırıp `sessions_dir.exists/writable: true`
olduğunu teyit et.

## 🚀 Kullanım

```bash
python3 ~/.hermes/skills/automation/session-deck/scripts/session_deck.py pick
```

### Komutlar

| Komut | Açıklama | Örnek |
| :--- | :--- | :--- |
| `pick` | Rastgele bir kart çeker. `--mode quick/deep/full` destekler. | `./session_deck.py pick --mode deep` |
| `inspect --id <ID>` | Belirtilen kartı incele. Tam id ya da `list`'teki kısaltılmış önek kabul eder. | `./session_deck.py inspect --id abc123` |
| `delete --id <ID>` | Kartı kalıcı olarak sil (Burn). Silme sonrası diski tekrar okuyup **gerçekten** silindiğini doğrular. | `./session_deck.py delete --id abc123` |
| `list` | Destedeki tüm kartları listele. | `./session_deck.py list` |
| `stats` | Deste istatistikleri + hangi `HERMES_HOME`'un kullanıldığı. | `./session_deck.py stats` |
| `fix` | Index'i diskteki kartlardan yeniden inşa et. | `./session_deck.py fix` |
| `debug` | Hangi ortamda, hangi yolda çalıştığını gösterir. **Bir şey çalışmıyor gibi görünüyorsa önce bunu çalıştır.** | `./session_deck.py debug` |

Her komut `--hermes-home /özel/yol` ile de çağrılabilir (otomatik tespiti bypass eder).

### Oyun Döngüsü (Agent ile)

```
Session Deck oyunu başlat. Rastgele bir kart çek ve bana göster.
Kararımı bekle: Discard, Distill, Imprint, Inspect, Pass.
İşlem biter bitmez hemen bir sonraki kartı çek.
```

## 🧭 HERMES_HOME Otomatik Tespiti (bu sürümün asıl farkı)

Önceki sürümlerde script sadece `$HERMES_HOME` ortam değişkenine (yoksa `~/.hermes`'e) körü körüne güveniyordu. Bir agent script'i farklı bir `$HOME` altında / izole bir ortamda çalıştırırsa, script sessizce **yanlış veya boş bir klasörde** işlem yapıyor, "başarılı" mesajı basıyor ama senin gerçek verilerine hiç dokunmuyordu — özellikle `delete`'in "çalışmıyormuş gibi görünmesinin" en sık nedeni buydu.

Bu sürüm sırayla şu adayları dener ve **içinde gerçekten `.json` session dosyası olan ilk adayı** seçer:

1. `$HERMES_HOME` (env var)
2. `~/.hermes`
3. `$HOME/.hermes`
4. `~/.config/hermes`
5. `/root/.hermes`

Hiçbiri veri içermiyorsa ilk adaya (`$HERMES_HOME` ya da `~/.hermes`) düşer ki en azından açık bir hata/`debug` çıktısı alınabilsin. `debug` komutu hangi adayın seçildiğini ve neden seçildiğini gösterir.

**Hâlâ silme çalışmıyorsa:** `debug` çıktısındaki `SEÇİLEN hermes_home` ve `sessions_dir.exists/writable` alanlarına bak. Doğru yolu görüyorsan ama yine de silmiyorsa, `delete` artık işlemden sonra diski tekrar okuyup doğruluyor — başarısızsa nedenini (`index'te hâlâ mevcut` / `dosya diskte hâlâ mevcut`) açıkça yazıyor, sessiz kalmıyor.

## 🔄 Sidebar Canlı Senkronizasyon (restart gerektirmez)

**Kök sorun (çözüldü):** WebUI sol paneli `webui/sessions/_index.json` +
bellek cache'inden okur. Eski script ise `webui/.sessions.json`'u okuyup
yazıyordu → **iki farklı liste**. Script bir kartı silse bile WebUI'nin
kaynağına dokunmadığı için kart sol panelde kalıyor, kullanıcı her silmede
restart etmek zorunda kalıyordu.

**Çözüm (bu sürümde):**
1. `get_sessions()`/`save_sessions()` artık **`_index.json`'u tek otorite**
   olarak kullanır → deck ile WebUI birebir aynı listeyi görür.
2. `delete`, silme sonrası çalışan WebUI'ye best-effort REST bildirimi
   gönderir: `POST/DELETE http://HOST:PORT/api/session/delete` body
   `{session_id: sid}`. WebUI bu endpoint'te dosyayı/index'i/journal'ları/
   state.db'yi temizler + `_publish_session_list_changed` ile sidebar'ı
   **canlı** günceller. Host/port `HERMES_WEBUI_HOST`/`HERMES_WEBUI_PORT`
   (varsayılan `127.0.0.1:8787`).
3. REST 401/403 (auth açık) veya ulaşılamaz olsa bile disk+`_index.json`
   prune'i zaten yapıldığı için veri her durumda silinir; sidebar en geç
   WebUI'nin stale-cache background rebuild'iyle tazelenir.

Detay ve reprodüksiyon: `references/webui_sidebar_sync.md`.

## ⚙️ Teknik Detaylar

- Saf Python 3, sıfır bağımlılık.
- **Kanonik kart id'si dosya adıdır** (uzantısız). İçerideki `session_id` alanı hiçbir yerde anahtar olarak kullanılmaz — eski sürümdeki `fix` sonrası kartların "BROKEN" görünmesi ve `delete`'in sessizce hiçbir şey silmemesi buradan kaynaklanıyordu.
- **Deck listesi `_index.json`'dan gelir**, `.sessions.json`'dan değil (WebUI ile ortak kaynak; yukarı bkz).
- Tüm yazmalar atomiktir (tmp dosya + `os.replace`) — yarım yazılmış bozuk JSON riski yok.
- `delete` işlem sonrası diski tekrar okuyup doğrular; doğrulanamayan silme `❌` ile raporlanır, asla sessizce "başarılı" denmez.
- `--id`, tam eşleşme yoksa (tekilse) dosya-adı öneki olarak çözülür; path traversal karakterleri (`/`, `..` vb.) filtrelenir.
- Mesaj `content` alanı düz metin ya da blok listesi (tool_use/tool_result) olabilir, önizleme ikisini de güvenle işler.
- **Tüm silme işlemleri geri alınamaz.**

## 📜 Lisans

MIT — al, kullan, değiştir, paylaş. Bir satırda **KIREI**'yi anarsan sevinirim. 😄

---

> *"Geçmişi temizlemek de bir sanattır."* — Komutan Yoldaş
