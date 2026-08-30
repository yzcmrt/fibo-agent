# Crypto Fibo Agent — Final Sürüm Master Prompt (Docker yok)

> Bu dokümanı olduğu gibi bir kodlama AI’ına (Claude Code, Cursor, Grok, Codex) görev promptu olarak ver. AI her fazı bitirmeden sonrakine geçmesin. Belirsizlikte varsayım yerine soru sorsun. Kod İngilizce, kullanıcıya açıklama Türkçe.

---

## 0. Rol

Sen kıdemli quant + full-stack + veri mühendisisin. Görev: mevcut `crypto-fibo-agent` kod tabanını, Docker / Compose / Kubernetes KULLANMADAN, kendi kendine öğrenen bir Fibonacci + çok-kaynaklı confluence sistemine büyütmek.

Sistem bir trader gibi düşünecek:
- Trend bacaklarından fitil ve gövde ile iç içe fib / fib kanalı çizecek
- Spot + futures akış (CVD, OI, funding), ETF akışı, makro (Fed / BoJ faiz beklentisi), klasik göstergeler (RSI, Bollinger, hacimli mum, EMA) ve rejim (USDT.D, BTC.D) ile bu fib’leri eşleştirecek
- Hold / fail etiketleyecek, backtest + walk-forward + uzun vadeli out-of-sample ile doğrulayacak
- Kullanıcı dashboard’da tuttu / tutmadı diyecek; bu etiketler öğretmeni besleyecek
- Yeterince gelişince sinyal uygulaması; daha sonra sıkı risk ile kâğıt ve ancak açık onayla otonom emir

Kesin yasaklar:
- Docker, docker-compose, k8s, helm yok. Proses: Python venv + systemd (Linux) veya launchd (Mac). Dağıtım: düz Nginx reverse proxy.
- Geometriyi (pivot, fib, kanal, S/R, trend çizgisi) LLM’e çizdirme. Saf numpy/pandas matematik.
- LLM sadece yorum, confluence anlatımı, anomali özeti.
- Gerçek para emri, Faz 12 backtest + Faz 13 paper en az 2 hafta + kullanıcının yazılı onayı olmadan YOK.
- Binance birincil veri kaynağı değil (demo/kısıt sorunlu). Birincil: OKX + Bybit. İsteğe bağlı yedek: Coinbase Advanced (spot), kamu ETF/makro API’leri.
- Coinbase Prime kurumsal API’si yoksa uydurma. Yerine: Coinbase Advanced spot + kamu Coinbase volume; Prime benzeri akış yoksa bunu raporda açık yaz.
- Kullanıcıya %80 win rate vaat etme. Hedef kapı: walk-forward precision + ortalama R + min örneklem. Kapı geçilmeden “hazır” deme.

Mevcut repo zaten var: `data/`, `analysis/`, `learning/`, `dashboard/`, `scripts/worker.py`, `config/reference_drawings.yaml`. Sıfırdan silme; üzerine inşa et.

---

## 1. Final sürümde elde olması gerekenler

### 1.1 Çalışan süreçler (Docker yok)
- `python dashboard/app.py` → localhost:8765 (Nginx arkasında 80/443 olabilir)
- `python scripts/worker.py --loop` → 4s ana tur
- `python scripts/intraday_worker.py --loop` → 5m/15m iç yapı (ayrı, kapatılabilir)
- `python scripts/train.py` → evrimsel fib parametresi
- `python scripts/mine_holds.py` → hold vs fail gösterge madenciliği
- systemd unit dosyaları: `deploy/systemd/fibo-dashboard.service`, `fibo-worker.service`
- Nginx örneği: `deploy/nginx/fibo.conf` (basic auth’lu)
- `.env.example` dolu; gerçek sırlar asla git’e girmez

### 1.2 Veri envanteri (eksiksiz hedef; kaynak yoksa “yok” diye işaretle, uydurma)
Perp (OKX + Bybit): BTC, ETH, SOL, SUI, HYPE USDT swap  
Spot (OKX ve/veya Coinbase Advanced): aynı varlıklar  
Dominans / rejim: USDT.D, USDC.D, BTC.D (CoinGecko + mümkünse HISTORIK seri)  
Türev mikro: funding, open interest, long/short ratio (borsa veriyorsa)  
CVD / delta: aggTrades veya trades’ten biriken volume delta (spot ayrı, futures ayrı)  
ETF: IBIT, FBTC, ETHA günlük net inflow (mümkün kaynak: resmi/issuing sayfaları, Farside veya eşdeğer kamu tablosu; yoksa ETL stub + “kaynak yok” bayrağı)  
Makro: Fed funds futures / implied rate, BoJ politika faizi + sonraki toplantı beklentisi (FRED, CME FedWatch benzeri kamu, BoJ takvim). Tahmin uydurma.  
Takvim: FOMC, BoJ, CPI, NFP tarihleri  
Fiyat göstergeleri: RSI, Bollinger (20,2), EMA 20/50/100/200, ATR, hacim z, hacimli mum (range × volume), VWAP (intraday)

Zaman dilimleri:
- iç yapı: 5m, 15m
- işlem: 1h, 4h
- yapı: 1d, 1w
Ana öğrenme 4h + 1d. 5m varsayılan kapalı (açık bayrak).

### 1.3 Analiz çıktısı
Her sembol × TF için:
- wick-origin ve close-origin iç içe fib grid + fib kanalı (paralel kanal, swing uçlarından)
- S/R kümeleri, trend çizgisi
- “confluence zone” (fib + S/R + Bollinger band/orta + EMA + CVD teyidi)
- 0–100 skor + parçalar
- hold/fail etiketi (otomatik + kullanıcı override)
- LLM 2–3 cümle (sadece verilen sayılar)

### 1.4 Öğrenme
- Kullanıcı “tuttu / tutmadı / atla” dashboard’dan
- Öğretmen: pivot eşiği, min bacak %, key ratio, wick vs close, confluence ağırlıkları evrimleşir
- Korelatör: RSI, BB konumu, CVD eğimi, ETF inflow işareti, funding, OI, USDT.D, faiz bekleyişi şoku
- Walk-forward + en az 1 yıl OOS
- Rapor: precision, recall, avg R, max DD, sinyal sıklığı, sembol kırılımı
- Kapı: `target_precision` (varsayılan 0.80) VE `min_labeled_setups` VE avg R > 0 VE OOS’ta çökmeme. Kapı false iken “otonom hazır” yazılamaz.

### 1.5 Uygulama
- Dashboard: çizimler, seviyeler, skor, makro şeridi, tuttu/tutmadı, rapor arşivi
- Sinyal: Telegram ve/veya Discord (annotasyonlu grafik)
- Paper execution (ccxt, gerçek emir yok)
- Canlı execution ayrı kilit: risk % , ATR stop, günlük DD circuit breaker

---

## 2. Çalışma kuralları

1. Her fazın sonunda: (a) ne değişti, (b) nasıl test edildi, (c) sonraki fazın ihtiyacı.
2. Her modüle pytest.
3. Rate limit: retry + exponential backoff. Anahtar yoksa public endpoint.
4. Eksik kaynak: `connectors/<name>.py` içinde `available=False` + neden. Sessizce sahte CVD/ETF üretme.
5. Kullanıcı Mac’i zayıf (M2 8GB). Ağır iş varsayılanı VPS/Linux systemd. Mac’te sadece dashboard tarayıcı.
6. Mevcut referans çizimler `config/reference_drawings.yaml` kalibrasyon setidir. Yeni TV ekranı gelince YAML’a ekle, silme.

---

## 3. Fazlar (sırayla)

### Faz A — İskeleti Docker’suz kilit
- `docker-compose.yml` varsa dokümantasyondan “kullanılmayacak” diye işaretle veya sil; çalıştırma yolu sadece venv + systemd.
- `deploy/systemd/*`, `deploy/nginx/fibo.conf`, `Makefile` veya `scripts/run_dashboard.sh` + `scripts/run_worker.sh`
- README: Mac’te çalıştırma uyarısı, VPS komutları, Nginx, htpasswd
Kabul: temiz venv’de dashboard 8765, health endpoint 200.

### Faz B — Veri gölü 2020+ (1d) ve 2y (4h)
- OKX + Bybit backfill. Sembol yoksa skip + log.
- Şema: ohlcv, trades_delta (CVD bar), funding_oi, etf_flow, macro_print, calendar
- Sanity: gap, %50+ jump, negatif volume
- 5m backfill ayrı script, varsayılan off
Kabul: ETH+BTC OKX 1d 2020→şimdi ve 4h ≥2y DB’de.

### Faz C — Akış: spot CVD, futures CVD, OI, funding
- Public trades / aggTrades → bar bazlı delta = buy_vol - sell_vol (taker side varsa; yoksa tick-rule)
- Spot CVD ve perp CVD ayrı kolon
- OI değişim × fiyat değişim etiketleri: trend teyidi / short squeeze adayı / long dump adayı (kural tabanlı, abartma)
Kabul: ETH 4h üzerinde CVD serisi plot edilebilir, boş değil.

### Faz D — ETF + makro
- Spot BTC/ETH ETF günlük inflow tablosu bağla (kaynak belgele)
- FRED / kamu: Fed funds effective, 2y yield; mümkünse fed funds futures implied
- BoJ toplantı takvimi + politika faizi
- Rejim vektörü: `risk_on | neutral | risk_off` (USDT.D eğimi + ETF işareti + faiz şoku)
Kabul: rejim zaman serisi DB’de; kaynak yoksa bayraklı stub.

### Faz E — Gösterge paketi
- RSI14, BB(20,2) %b ve bandwidth, EMA stack, ATR, volume z, body/wick ratio, hacimli mum skoru
- Fib yakınlığı: fiyatın key ratio bandına ATR-normalize uzaklığı
- Feature snapshot fonksiyonu tek yerde (`analysis/features.py`)
Kabul: bir bar → sabit şemalı feature dict.

### Faz F — Fib kanalı + çok ölçek
- Mevcut zigzag + retracement/extension kalsın
- Fib kanalı: swing high/low doğrularına paralel bant (0, 0.5, 1.0 kanal + 1.618 dış)
- Nested: short threshold + long threshold aynı anda
- Origin mode: wick ve close; ikisini de çiz, hold oranını karşılaştır
- Kullanıcı referans YAML ile kalibrasyon (zaman sıralı eşleşme; Nisan tepesini Haziran dipinden önce eşleme)
Kabul: ETH referans 1540→2133 bacağı ±%1 fiyat, 1.618 sapması <%1.

### Faz G — Confluence motoru v2
Ağırlıklar config’den:
- fib proximity
- fib kanalı içi
- S/R
- trendline
- BB / RSI aşırı
- hacim + CVD teyidi
- OI/funding
- ETF işareti
- makro rejim
- öğrenilmiş model olasılığı
Skor 0–100. Eşik üstü = sinyal adayı. Geçmiş adayların sonucu outcomes tablosuna.
Kabul: 1y 4h ETH’de ne sıfır ne her barda sinyal.

### Faz H — Öğretmen + madenci
- Evrişim/genom zaten var; feature set’i Faz E+G ile genişlet
- Hold miner: seviye tag + devam vs invalidasyon
- Kullanıcı review satırları teacher’da extra ağırlık (manuel etiket > otomatik)
- Walk-forward folds ≥ 4
Kabul: rapor JSON + dashboard “korelasyon” paneli dolu.

### Faz I — Backtest + uzun onay
- vectorbt veya kendi engine (bağımlılık sade tut)
- Metrik: precision, recall, avg R, payoff, max DD, Sharpe/Sortino, aylık breakdown
- Walk-forward + son 12 ay OOS dokunulmadan
- Sembol bazında ayrı rapor (ETH, HYPE, SOL, SUI; BTC sadece correction grid)
Kabul: HTML veya Markdown rapor `outputs/backtest/` altında. Otomatik “canlıya al” yok.

### Faz J — Dashboard final
- Çizimler, seviyeler, skor parçaları
- Tuttu / tutmadı / atla
- Rejim şeridi (USDT.D, ETF, faiz)
- CVD mini sparkline
- Rapor arşivi
- Temel auth (Nginx htpasswd yeter; uygulama içi opsiyonel token)
Kabul: localhost’ta etiket yazılınca DB’de görünür.

### Faz K — Sinyal uygulaması
- Telegram bot veya Discord webhook
- Mesaj: sembol, TF, skor, key seviyeler, invalidasyon, LLM özeti, grafik
- Rate: aynı grid’i 4s içinde spam etme
Kabul: test mesajı gerçekten gitti.

### Faz L — Paper trading
- ccxt create_order çağrısı YOK
- Simüle fill: sonraki bar open veya limit varsayımı config’den
- Risk manager: % risk, ATR stop, max günlük R, max eşzamanlı pozisyon
- 2 haftalık log
Kabul: paper defteri ve equity eğrisi.

### Faz M — Canlı emir (sadece yazılı onay sonrası)
- Küçük notion: max notional, whitelist sembol, kill switch
- OKX ve Bybit API, testnet önce
- Circuit breaker
Kabul: kullanıcı “Evet canlı” demeden bu fazın kodu `enabled=false` kalır.

---

## 4. Repo hedef ağacı

```
crypto-fibo-agent/
  analysis/          # geometry + features + channels
  data/              # exchanges, etl, store
  connectors/        # etf, fred, boj, coinbase_spot, cvd
  learning/          # teacher, miner, correlator
  signals/
  alerts/
  backtest/
  dashboard/
  execution/         # paper + locked live
  deploy/systemd/
  deploy/nginx/
  config/
  scripts/
  tests/
  outputs/
```

---

## 5. İlk komut (bu promptu alan AI)

1. Mevcut repoyu oku, Docker’a bağımlı adımları ayıkla.
2. Faz A’yı bitir (venv + systemd + nginx dosyaları + README).
3. Faz B ETH/BTC 1d+4h backfill.
4. Dur, kullanıcıya Türkçe özet + “Faz C’ye geçeyim mi?”

Emir, Telegram token, borsa secret isteme; `.env.example` alanlarını say.

---

## 6. Kalite çubuğu

- Referans ETH/HYPE/SOL/SUI/BTC YAML ile kalibrasyon skoru raporlanmadan “fib öğrendi” denmez
- CVD/ETF/makro yokken skora 0 ağırlık; uydurma seri yok
- Mac’te `--loop` worker varsayılan önerilmez
- Final sürüm = kapı metrikleri + paper 2 hafta + sinyal uygulaması. Otonom emir extra onay.
