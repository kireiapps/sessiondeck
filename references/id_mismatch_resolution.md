# Bilinen Geçmiş Hatalar ve Çözümleri

Bu dosya, önceki sürümlerde yaşanan ve bu sürümde kalıcı olarak düzeltilen
sorunları belgeler (arşiv amaçlı).

## 1. ID mismatch (fix komutu index'i bozuyordu)
Eski `fix_index()`, index anahtarı olarak dosya İÇİNDEKİ `session_id`
alanını kullanıyordu (12 karakter). Ama `pick`/`delete`/`inspect` dosyayı
her zaman dosya ADINA göre (`{key}.json`) arıyordu. `fix` çalıştırıldıktan
sonra bu iki değer artık eşleşmiyor, kartlar "BROKEN" görünüyor, `delete`
hiçbir şey silmeden "başarılı" mesajı basıyordu.

**Çözüm:** İndex anahtarı artık her zaman dosya adı. `session_id` alanı
hiçbir yerde anahtar olarak kullanılmıyor.

## 2. delete_session() her zaman True dönüyordu
Dosya gerçekten silinmese bile fonksiyon `True` döndürüyor, CLI de
"🔥 Discarded" yazıyordu — sessiz başarısızlık.

**Çözüm:** `delete_session()` işlem sonrası diski tekrar okuyup gerçekten
silinip silinmediğini doğruluyor, doğrulanamazsa açık hata mesajı veriyor.

## 3. HERMES_HOME yanlış ortamda çözümleniyordu (agent/sandbox senaryosu)
Script bir agent (Hermes) tarafından çalıştırıldığında, agent'ın shell
ortamı kullanıcının gerçek `$HOME`'undan farklı olabiliyor. Bu durumda
script sessizce yanlış/boş bir klasörde işlem yapıyor, kullanıcı "silme
çalışmıyor" diye şikayet ediyor ama aslında script hiç yanlış yapmıyor —
sadece hiç var olmayan bir veri kümesi üzerinde "başarıyla" çalışıyordu.

**Çözüm:** `detect_hermes_home()` birden fazla aday yolu dener ve içinde
gerçekten session verisi olan ilk adayı seçer. `debug` komutu hangi yolun
seçildiğini ve neden seçildiğini açıkça gösterir. `--hermes-home` ile elle
override de mümkün.

## Hızlı Teşhis
```bash
python3 session_deck.py debug
python3 session_deck.py stats
python3 session_deck.py fix
```
`debug` çıktısında `sessions_dir.exists: true` ve `writable: true`
görmüyorsan, sorun script'te değil, script'in çalıştığı ortamdadır.
