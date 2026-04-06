import sqlite3

def get_db():
    conn = sqlite3.connect('koperasi.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Tabel Produk
    cursor.execute('''CREATE TABLE IF NOT EXISTS produk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        harga REAL NOT NULL,
        stok INTEGER NOT NULL
    )''')
    # Tabel Transaksi
    cursor.execute('''CREATE TABLE IF NOT EXISTS transaksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        total_harga REAL,
        items TEXT,
        tanggal DATE DEFAULT CURRENT_DATE
    )''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()