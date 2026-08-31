# Fibo Agent — kapatılacak açıklar (nihai plan)

Repo silinmez. Her adım bitince test çıktısı + 3–5 cümle Türkçe özet + “sonrakine geçeyim mi?”
Canlı emir bu listenin hiçbir maddesinde açılmaz.

## Blok A — ölçüm dürüstlüğü (önce bunlar)

### A1 Forward = backtest dili
- `learning/forward.py` `resolve_open` `label_fib_hold` + gerçek `r_multiple` kullansın.
- Forward setup’ta swing/grid saklansın (levels JSON veya swing_low/high + key_ratio).
- Kapı karşılaştırması aynı etiketi konuşsun.
- Kabul: birim test; kaba last-close kuralı yok.

### A2 ETF sessiz yanlış sayı olmasın
- Farside “Total” (günlük net) satırı; ilk `Xm` regex’i kalksın.
- Parse fail → `available=False`, value=None, son değeri “gerçek bugün” diye yazma.
- Kabul: sahte HTML’de Total yakalanır; bozuk sayfada available=False.

### A3 Fed: çek veya açıkça yok
- Ya kamu FedWatch/eşdeğer + `available=True`, ya `fed_hold_prob/fed_cut_prob` kalıcı None + flag `fed:unavailable`.
- `prev.get` ile boş kolon doldurma bitsin.
- Kabul: snapshot’ta fed ya sayı+kaynak, ya available=False.

### A4 Telegram/Discord dedup
- Anahtar: symbol+tf+direction+key_price (yuvarlanmış) + skor bandı.
- Aynı anahtar N saat (varsayılan 8s / 2 mum 4h) tekrar gitmez.
- Kabul: iki çağrıda ikinci send edilmez.

### A5 Miner tüm perp’ler
- Worker’da `ETH` if’i kalksın; liste `settings.symbols.perps`.
- BTC’de extension miner’a sokulmasın.
- Kabul: kodda ETH-only yok.

## Blok B — veri sözleşmesi

### B1 `connectors/` + `ConnectorResult`
- Ortak dataclass: available, value, source, fetched_at, error.
- Sarmala: cvd, etf, premium, fed, boj, calendar.
- Worker connector exception ile ölmez.
- Kabul: en az bir connector kasıtlı kırıkken cycle devam.

### B2 Confluence `available` normalize
- False faktör ağırlığı 0, kalanlar toplam 1.0.
- Kabul: cvd yokken skor 0–100 aralığında, cvd_bias devre dışı.

### B3 `build_feature_row` tek kapı
- `indicators.snapshot` + miner `_extra` + kanal/HTF/CVD/macro bir fonksiyon.
- hold_miner, trainer, analyze aynı fonksiyon.
- Kabul: grep ile dağınık kopya kalmasın (makul istisna: test).

### B4 CVD: poll deliği + O(n²)
- Mümkünse WS; yoksa `since` ile artımlı REST, kaçan aralık `available` notu.
- `attach_cvd_features` merge/asof, bar başına full tablo tarama yok.
- `rebase_cumulative` ölü kod silinsin.
- Kabul: join O(n log n) veya daha iyi; birim test.

### B5 OI kuralı + funding ROC
- `analysis/oi_rules.py`: fiyat↑ OI↑ yeni long, fiyat↓ OI↑ yeni short, vb.
- Funding seviye değil değişim feature.
- Kabul: feature_delta tablosunda isimler görünür (anlamlı olmak zorunda değil).

### B6 Ekonomik takvim
- FOMC / BoJ / ABD CPI tarihleri, tahmin yok. `calendar_flag`.
- Kabul: olay günü bayrak 1, diğer gün 0 veya None.

## Blok C — öğrenme ve rapor

### C1 İnsan etiketi > otomatik
- `drawing_reviews` fail/hold, sonraki `train`/`mine` etiketinde insan kazanır.
- Kabul: dashboard fail → all_labels’da izlenir.

### C2 OOS + çıktı dosyası
- ≥12 ay OOS pencere (veri yetmezse “OOS kısa” diye yaz, uydurma uzatma).
- `outputs/backtest/` sembol kırılımı, brüt/net, WF vs OOS.
- Kabul: dosya + net_avg_r alanı.

### C3 `macro_bias` gerçek feature
- Premium+ETF+takvim tek sayı; tuner eşlemesi tetiklensin.
- Kabul: HOLD_FEATURES’ta dolu kolon.

### C4 `docs/progress.md`
- Her adım satırı: tarih, adım, sonuç, açık risk.

## Blok D — arayüz (kapı sonrası incelir)

### D1 Dashboard
- Mum + fib/kanal overlay (varsa OHLCV).
- Skor parçaları, CVD spark.
- OKX/Bybit panel (paper fill varsa).
- Kill switch zaten var.

### D2 Demo endpoint (yalnızca forward kapısı + senin “Evet demo”)
- OKX `x-simulated-trading`, Bybit `api-demo.bybit.com`.
- Reconciliation + kill gerçek `place` yolunda.
- Testnet yok.

### D3 Kademeli canlı
- 3 forward dönem kapı + yazılı “Evet canlı”.
- Şimdi kod iskeleti, `enabled=false`.

## Bilerek sonra / yapma

- Repo silmek, Faz 1’den sıfır ajan.
- %80 vaadi.
- Binance birincil.
- Mac’te 7/24 `--loop`.
- Üç noktalı adaptive fib kanalı (A–C bitmeden).
- Canlı mainnet emir.

## Sıra

A1 → A2 → A3 → A4 → A5 → B1 → B2 → B3 → B4 → B5 → B6 → C1 → C2 → C3 → C4 → D1 → (onay) D2 → D3
