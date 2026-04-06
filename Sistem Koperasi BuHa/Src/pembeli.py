from database import get_db

def get_semua_barang():
    conn = get_db()
    items = conn.execute("SELECT * FROM produk WHERE stok > 0").fetchall()
    conn.close()
    return items
