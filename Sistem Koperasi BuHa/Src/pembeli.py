from database import get_db

def get_semua_barang():
    conn = get_db()
    items = conn.execute("SELECT * FROM produk WHERE stok > 0").fetchall()
    conn.close()
    return items

def proses_transaksi(user_id, keranjang):
    conn = get_db()
    cursor = conn.cursor()
    total_akhir = 0
    list_item = []
