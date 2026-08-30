# Crypto Fibo Agent — OKX + Bybit

Trend bacaklarından Fibonacci (wick + close) ve fib kanalı çizen, hold/fail etiketleyen, parametrelerini evrimleştiren ajan grubu.

Borsalar: **OKX (birincil)** + **Bybit**. Binance yok. Docker yok.

`%80` bir kapıdır, vaat değildir. Canlı emir kilitlidir.

## Kurulum (venv + systemd)

```bash
git clone https://github.com/yzcmrt/fibo-agent.git
cd fibo-agent   # veya klasör adı crypto-fibo-agent ise onu kullan
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Yerel deneme (Mac’te `--loop` worker önermiyoruz):

```bash
.venv/bin/python dashboard/app.py          # http://127.0.0.1:8765
.venv/bin/python scripts/run_phase1.py
.venv/bin/python scripts/train.py
.venv/bin/python -m pytest tests -q
```

## VPS 7/24 (user systemd)

Repo’yu `$HOME/crypto-fibo-agent` altına koy (unit dosyaları `%h/crypto-fibo-agent` bekler) veya `deploy/systemd/*.service` içindeki yolu düzelt.

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/fibo-worker.service deploy/systemd/fibo-dashboard.service ~/.config/systemd/user/
loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now fibo-worker fibo-dashboard
journalctl --user -u fibo-worker -f
```

Nginx örneği: `deploy/nginx/fibo.conf`. Basic auth: `htpasswd -c /etc/nginx/.fibo-htpasswd kullanici`.

## Faz durumu (PROMPT-FINAL.md)

- 0 altyapı + bugfix — bu commit
- 1 correlator kalıcılığı — bu commit
- 2 HTF teyidi — sıradaki
- 2b wick/close + fib kanalı + YAML kalibrasyon
- 3–11 PROMPT-FINAL.md

## Dürüst sınır

Fib “öğrenmesi” derin öğrenme chart-reader değil; evrimleşen kural + etiket döngüsüdür. Demo ≠ testnet. Coinbase Prime yok; vekil premium ileriki faz.
