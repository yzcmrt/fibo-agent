# Crypto Fibo Agent — Tek Prompt (şu andan final sürüme)

Nasıl kullanılır: Bu belge uygulama promptudur. Her oturumu şöyle aç:

«Şu an Faz N’deyiz. Repo crypto-fibo-agent. Önceki fazların kabul kriteri geçti. Bu fazın hedefi: [ilgili bölüm]. Kabul kriterini geçmeden sonraki faza geçme. Kod İngilizce, bana açıklama Türkçe.»

Fazlar sırayla bağlıdır. Kabul kriteri geçilmeden “öğrendi / hazır / otonom” denmez. Tüm fazları tek turda kodlama.

---

## Rol ve kapsam

Kıdemli quant + veri + uygulama mühendisisin. Mevcut repoyu silmeden, Docker/Compose/K8s/container KULLANMADAN sistemi final sürüme götür.

Süreç: Python venv + systemd (user veya system) + cron (günde 1 makro) + Nginx (opsiyonel, düz reverse proxy). Mac M2 8GB üzerinde `--loop` worker önerme; 7/24 iş VPS/Linux.

Sistem bir trader gibi:
- Fitil (wick) ve gövde (close) çapalı, iç içe Fibonacci + Fibonacci KANALI çizer
- 5m/15m iç yapı (varsayılan kapalı), 1h/4h işlem, 1d/1w yapı
- Spot CVD ve futures CVD ayrı; OI, funding; hacimli mum; Bollinger; RSI; EMA
- ETF net akış, Coinbase premium (Prime değil), Fed / BoJ vekilleri, USDT.D / BTC.D
- Hold/fail etiketler, kullanıcı dashboard’da tuttu/tutmadı der
- Öğrenilen ağırlıklar restart’ta kaybolmaz
- Backtest (masraflı) + walk-forward + haftalarca canlı-pasif forward test
- Kapı geçince: sinyal → demo execution → kademeli küçük canlı

---

## Sert kurallar

1. Geometri (pivot, fib, kanal, S/R, trend) saf numpy/pandas. LLM çizmez. LLM yalnızca verilen sayılardan 2–3 cümle yorum.
2. Sahte seri yok. Kaynak yoksa `available=False` + neden. Worker scrape hatasında çökmez; son bilinen değer.
3. Binance birincil veri değil. OKX + Bybit. Spot takviye: Coinbase Exchange public (Prime API yok; uydurma).
4. BTC sadece düzeltme (correction) fibi; extension chase yok.
5. Coinbase Prime bireysel key ile alınamaz. Vekil: Coinbase BTC-USD − OKX/Bybit BTC-USDT = premium.
6. CVD OHLCV’den türetilmez. Geçmiş OKX’te kısmen; Bybit’te çoğu ileriye birikir.
7. %80 vaat edilmez. Kapı: precision hedefi + n≥80 tamamlanmış setup + net avg R>0 + forward’ın walk-forward’dan kopmaması. Kapı false iken execution.enabled=false.
8. Gerçek para: Faz 8 kapısı art arda en az 3 forward dönemde geçmeden ve kullanıcı “canlı boyut artır” demeden yok.
9. Bybit testnet ≠ demo. Demo kullan (`api-demo.bybit.com`). OKX demo: `x-simulated-trading: 1`.
10. Secret git’e girmez. `.env` + systemd `EnvironmentFile=`.
11. `reference_drawings.yaml` kalibrasyon setidir; silinmez. Yeni TV grid’i buraya eklenir.
12. Path’leri `/home/mert` diye sabitleme. `WorkingDirectory=` repo kökü; kullanıcıyı placeholder bırak.

---

## Final kontrol listesi

- [ ] Docker yok; reboot sonrası worker + dashboard systemd ile kalkıyor; `.env` okunuyor
- [ ] Correlator/model restart’ta kaybolmuyor
- [ ] HTF 1d/1w teyidi; ters yönde skor en az 15–20 puan düşük (test)
- [ ] Wick ve close origin ayrı; hold oranları ayrı rapor
- [ ] Fib kanalı (0 / 0.5 / 1.0 / 1.618 paralel)
- [ ] Referans YAML kalibrasyonu (ETH 1540→2133 1.618 sapması <%1 hedef; HYPE/SOL/SUI/BTC mevcut kayıtlar)
- [ ] BB, hacimli mum, RSI, EMA stack feature şemasında
- [ ] Spot+perp CVD birikiyor; anlamsızsa ağırlık düşük, veri durmuyor
- [ ] ETF + Coinbase premium + Fed vekili + BoJ vekili (JGB10y + USDJPY); rejim filtresi
- [ ] feature_delta ile ölçülmüş ağırlıklar; anlamsız faktör düşürülmüş
- [ ] Backtest: net precision, net avg R, komisyon+slippage+funding, equity DD
- [ ] 4–8 hafta forward test kartı dashboard’da; çoklu sembol train
- [ ] 15m/5m worker varsayılan kapalı; HTF+4h oturunca açılır
- [ ] Dashboard: fib overlay, tuttu/tutmadı, rejim, CVD, genom geçmişi, kill switch
- [ ] Telegram/Discord sinyal (spam yok)
- [ ] OKX+Bybit DEMO, risk limit, reconciliation, kill switch
- [ ] Sinyal → yarı otonom demo → kademeli canlı (her artış yeni forward kanıtı)
- [ ] BTC correction-only kodda kural

---

## Faz 0 — Docker’sız altyapı + mevcut buglar (1–3 gün)

Hedef: Container olmadan 7/24; bilinen kırıklar kapalı.

Yapılacaklar:
1. `requirements.txt`: `mplfinance>=0.12.10` satırını kaldır (PyPI’de bu pin patlar). Mum varsa matplotlib veya pinsiz `mplfinance`.
2. `.env` yüklensin:
   - `config/__init__.py` başına `from dotenv import load_dotenv; load_dotenv()`
   - systemd `EnvironmentFile=%h/crypto-fibo-agent/.env` (kök yolu kullanıcıya göre)
3. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
4. `deploy/systemd/fibo-worker.service` ve `fibo-dashboard.service` (Type=simple, Restart=on-failure, After=network-online, ExecStart venv python, WorkingDirectory repo kökü). User systemd ise `loginctl enable-linger $USER`.
5. `docker-compose.yml` sil veya “kullanılmayacak” notu. README yalnızca venv+systemd+Nginx+htpasswd.
6. `os.getenv` ile OKX/Bybit anahtarlarının gerçekten geldiğini doğrula (değerleri loglama).

Kabul: Reboot veya `systemctl --user restart` sonrası worker+dashboard ayağa kalkar; health `200`; `.env` okunur.

---

## Faz 1 — Öğrenilen modelin kalıcılığı (2–3 gün)

Hedef: `trainer` / correlator restart’ta sıfırlanmasın.

- `learning/memory.py`: `load_correlations()` → weights + success/fail mean
- `FeatureCorrelator.load_state(...)` (scaler yoksa ağırlıklı skor moduna düş; varsa scaler’ı da DB’ye yaz)
- `AgentOrchestra.__init__` model varsa yüklüyor
- Test: train → süreç öldür → aç → `analyze()` içinde `model_prob` sayı ve son ağırlıklarla tutarlı

Kabul: restart sonrası `raw["model_prob"] is not None`.

---

## Faz 2 — HTF trend teyidi (3–5 gün) — en yüksek öncelik

Hedef: 4h sinyal 1d/1w ile çelişiyorsa cezalı.

- `analysis/trend_confirmation.py`: 1d ve 1w EMA20/50 eğimi + HH/HL vs LH/LL → `htf_bias` ∈ [-1,1]
- `score_setup(..., htf_bias)`; grid yönü tersse tavan ~%60 veya ≥15–20 puan ceza
- `settings.yaml` `confluence.weights.htf_alignment: 0.15`, toplam 1.0
- `analyze()` 1d/1w çeker
- BTC: correction grid dışında extension adayı üretilmez

Kabul: sentetik iki senaryolu birim test; ters HTF skor farkı ≥15 puan.

---

## Faz 2b — Kullanıcı çizim dili (2–4 gün) — HTF ile aynı öncelik bloğu

Hedef: Senin TV yöntemine oturt.

- Origin: her swing için `wick` ve `close` grid; hold oranı ayrı
- Fib kanalı: swing uçlarından paralel 0 / 0.5 / 1.0 + 1.618 dış bant
- Nested: kısa + uzun eşik aynı anda; kalabalık cezası mevcut evrime bağlı kalsın
- `scripts/calibrate.py` + `config/reference_drawings.yaml` zaman sıralı eşleşme (Nisan tepesi Haziran dibine yapışmasın)
- Hedef sapma: kayıtlı ETH 1540→2133 bacağı fiyat ±%1, 1.618 <%1

Kabul: kalibrasyon raporu YAML’deki ETH/HYPE/SOL/SUI/BTC satırlarını sayı ile döner.

---

## Faz 3 — Bollinger + hacimli mum (2–3 gün)

- `bb_mid/upper/lower`, `bb_width`, `bb_pct` (20,2)
- Conviction candle: `vol_z>2` + gövde/fitil kuralı (ML yok)
- Confluence: bant dışı mean-reversion / dar bant sıkışma — kuralı yaz, sonra Faz 6 ölçecek
- `snapshot_features` tek şema (`analysis/features.py` varsa orada topla)

Kabul: snapshot’ta `bb_pct`, `bb_width`; hold_miner bu alanların hold/fail ortalamasını hesaplar.

---

## Faz 4 — CVD spot + futures (1–2 hafta, biriktirme süresi var)

- `data/cvd.py`: WS trades (ccxt `watch_trades` veya borsa WS). Taker side yoksa tick-rule. Spot ve perp ayrı.
- Tablo: `exchange, symbol, timeframe, ts, buy_vol, sell_vol, delta, cumulative_delta`
- Feature: `cvd_slope`, `cvd_divergence` (fiyat HH, CVD değilse)
- Geçmiş yoksa ileriye biriktir; 2–3 hafta dolmadan “CVD işe yaramıyor” diye silme, ağırlığı düşük tut

Kabul: tablo doluyor; worker WS kopunca yeniden bağlanır; hold_miner delta raporu üretir (anlamlı olmasa bile).

---

## Faz 5 — Makro / kurumsal vekiller (2–3 hafta, cron günlük)

| Veri | Kaynak | Not |
|---|---|---|
| BTC/ETH ETF net akış | Farside veya SoSoValue, günde 1 scrape | Resmi API yok |
| Coinbase Prime | YOK | Vekil: Coinbase Exchange BTC-USD vs OKX/Bybit BTC-USDT premium |
| Fed beklenti | CME FedWatch sayfa veya `cme-fedwatch` benzeri kamu paket | Resmi realtime API alma |
| BoJ | FRED JGB 10y + USDJPY | Seyrek, best-effort |
| Rejim | USDT.D, BTC.D + yukarıdakiler | `risk_on/neutral/risk_off` |

- `data/macro.py` + `scripts/fetch_macro.py`
- Tablo `macro_snapshot(ts, etf_net_flow_usd, coinbase_premium_pct, fed_hold_prob, fed_cut_prob, jgb_10y, usdjpy, usdt_d, btc_d)`
- Cron: `0 8 * * * /path/.venv/bin/python scripts/fetch_macro.py`
- Scrape fail worker’ı öldürmez

Kabul: ≥14 günlük satır; bir kaynak kırıkken diğerleri yazılmaya devam.

---

## Faz 6 — Confluence v2 + ayırt edicilik (1–2 hafta)

- HOLD_FEATURES’a ekle: `htf_alignment`, `bb_position`, `cvd_bias`, `macro_bias`, `origin_mode`, `channel_position`
- Her faktör `feature_delta` (hold mean − fail mean). |delta| küçükse ağırlık düşür/sıfırla. Sezgiyle şişirme.
- `weights` toplamı 1.0 test
- Rapor `reports` tablosuna

Kabul: ≥3 yeni faktör ölçülmüş; en az biri anlamlıysa ağırlığı artmış, anlamsızlar düşmüş.

---

## Faz 7 — Masraflı backtest (1 hafta)

- `r_multiple`, MFE, MAE ile gerçek equity
- Taker/maker (OKX/Bybit fee), slippage ≈ spread/2, funding = açık süre × ortalama rate
- DD equity’den
- Sembol kırılımı: ETH HYPE SOL SUI; BTC yalnızca correction seti

Kabul: raporda brüt vs net precision ve net avg_r; en az bir koşuda fark görünür.

---

## Faz 8 — Walk-forward + canlı-pasif forward (4–8 hafta, kısayol yok)

- Fold 6–8; `scripts/train.py` `symbols.perps` listesinin tamamını gezer (BTC kuralı hariç extension)
- Forward-sinyal: her yeni 4h mumda üretilen `live_drawings` / setup emir YOK; `label_fib_hold` ile sonuç `outcomes`’a
- Dashboard kartı: üretilen / tamamlanan / anlık precision
- Walk-forward %78, forward %55 ise overfitting: Faz 6’ya dön, sadeleştir, tekrar bekle
- 5m/15m worker ancak bu fazın 4h/1d’i istikrarlıysa açılır (ayrı servis, varsayılan disabled)

Kabul: ≥4 hafta forward birikimi; precision WF’ye yakın; n hedefe doğru sayaç görünür.

---

## Faz 9 — Risk + DEMO execution (yalnızca Faz 8 kapısı geçtiyse)

- RiskManager: UTC midnight `realized_r_today=0`, max eşzamanlı pozisyon, sembol notional tavanı, ATR stop
- OrderExecutor: OKX demo header; Bybit demo host. Testnet yok.
- Emir öncesi/sonrası `get_order` reconciliation
- Dashboard kill switch → `execution.enabled=false` anında
- Paper/simülasyon kodu durur; demo ayrı bayrak

Kabul: demo’da aç-kapa; limit ihlali testte engellenir; kill switch yeni emri keser.

---

## Faz 10 — Dashboard v2 (1–2 hafta)

- lightweight-charts (tek JS, container yok) mum + fib + kanal overlay
- OKX / Bybit paneli: pozisyon, açık emir, günlük PnL, son log
- Genom şampiyon geçmişi
- Tuttu / tutmadı / atla mevcut kalsın
- stdlib `http.server` yeter; gerekirse token header. Yeni framework zorlama.
- Nginx örneği + htpasswd `deploy/nginx/`

Kabul: tek sayfada iki borsa, 24s çizimler, genom, kill switch, review.

---

## Faz 11 — Sinyal → kademeli otonomi (sürekli)

1. Sinyal: Telegram/Discord + grafik + invalidasyon; sen emri elle alırsın. Aynı grid 4s spam yok.
2. Yarı otonom: yalnızca DEMO kendi emrini atar; canlı kapalı.
3. Canlı: Faz 8 kapısı art arda ≥3 forward dönemde (ör. 3×4 hafta) geçtiyse min notional. Her boyut artışı yeni dönem kanıtı ister. Tek “onaylıyorum” yetmez.

Kabul: aşama 1 üretimde; 2 demo’da; 3 kodda `enabled=false` ve kapı fonksiyonu açıkça false döner.

---

## İlk oturum emri

Repo oku. Faz 0’ı bitir (mplfinance, dotenv, systemd unit, docker-compose temizliği, README). Faz 0 kabulünü kanıtla. Dur. «Faz 1’e geçeyim mi?» diye sor.

Secret isteme. `.env.example` alanlarını listele.
