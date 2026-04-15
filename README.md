# 🛒 Bakul Byte

<p align="center">
  <img src="assets/banner.png" alt="Bakul Byte Banner" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/salmanjaysyurachman-crypto/Bakul-Byte?style=for-the-badge">
  <img src="https://img.shields.io/github/forks/salmanjaysyurachman-crypto/Bakul-Byte?style=for-the-badge">
  <img src="https://img.shields.io/github/license/salmanjaysyurachman-crypto/Bakul-Byte?style=for-the-badge">
</p>

---

## ✨ Overview

**Bakul Byte** adalah sistem manajemen UMKM berbasis **Telegram Bot** untuk membantu:

* 📦 Manajemen stok barang
* 🛒 Transaksi penjualan
* 📊 Laporan harian

> 💡 Menghubungkan pedagang tradisional dengan solusi digital modern.

---

## 🚀 Features

* 📦 Kelola stok barang
* 🛒 Sistem pembelian
* 📊 Laporan penjualan
* 🤖 Telegram Bot interaktif
* 👤 Role Admin & Pembeli

---

## 🏗️ Project Structure

```bash
Bakul-Byte/
│
├── docs/
│   ├── Laporan-Observasi.pdf
│   ├── Laporan-Wawancara.pdf
│   ├── Laporan-Kebutuhan-Sistem.pdf
│
├── src/
│   ├── database.py
│   ├── admin.py
│   ├── pembeli.py
│   ├── bot.py
│
├── assets/
│   ├── banner.png
│   ├── preview-bot.png
│
└── README.md
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/salmanjaysyurachman-crypto/Bakul-Byte.git
cd Bakul-Byte
```

### 2. Install Dependencies

```bash
pip install python-telegram-bot
```

---

## 🔑 Setup Telegram Bot

1. Buka Telegram
2. Cari **@BotFather**
3. Ketik `/newbot`
4. Salin TOKEN
5. Masukkan ke:

```bash
src/pembeli.py
```

```python
TOKEN = "YOUR_BOT_TOKEN"
```

---

## ▶️ Running the App

```bash
python src/bot.py
```

✅ Bot akan aktif dan siap digunakan

---

## 📸 Preview

<p align="center">
  <img src="assets/preview-bot.png" width="300">
</p>

---

## 🤖 Demo Command

### 👤 User (Pembeli)

```
/start
/menu
/produk
/beli
/keranjang
/help
```

### 👨‍💼 Admin

```
/admin
/tambah
/hapus
/stok
/laporan
```

---

## 💻 Run on Another Device

```bash
git clone https://github.com/salmanjaysyurachman-crypto/Bakul-Byte.git
cd Bakul-Byte
pip install python-telegram-bot
python src/bot.py
```

📌 Jangan lupa isi TOKEN di `src/pembeli.py`

---

## 🧠 Tech Stack

* Python
* SQLite
* python-telegram-bot

---

## 🚀 Future Plans

* 🌐 Web Dashboard
* 📊 Grafik Penjualan
* 🧾 Export PDF
* ☁️ Cloud Database

---

## 👥 Team

* Salman
* Hasyim
* Furqon

---

## 📬 Contact

* Salman → https://instagram.com/isalmanjay
* Hasyim → https://instagram.com/muhhsyim
* Furqon → https://instagram.com/furqon.thoriq

---

## 📜 License

Project ini dibuat untuk pembelajaran dan pengembangan UMKM.

---

<p align="center">
  ⭐ Jangan lupa kasih star jika bermanfaat!
</p>
