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

    try:
        for item_id, qty in keranjang.items():
            barang = cursor.execute("SELECT * FROM produk WHERE id = ?", (item_id,)).fetchone()
            if barang and barang['stok'] >= qty:
                subtotal = barang['harga'] * qty
                total_akhir += subtotal
                cursor.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (qty, item_id))
                list_item.append(f"🔹 {barang['nama']} x{qty} (Rp{subtotal:,.0f})")