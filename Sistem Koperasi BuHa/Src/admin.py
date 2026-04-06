import pandas as pd
from database import get_db
from datetime import datetime
import os

def tambah_barang(nama, harga, stok):
    conn = get_db()
    conn.execute("INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)", (nama, harga, stok))
    conn.commit()
    conn.close()

def hapus_barang(id_barang):
    conn = get_db()
    conn.execute("DELETE FROM produk WHERE id = ?", (id_barang,))
    conn.commit()
    conn.close()

def edit_stok(id_barang, stok_baru):
    conn = get_db()
    conn.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (stok_baru, id_barang))
    conn.commit()
    conn.close()

def export_laporan(mode='harian'):
    conn = get_db()
    query = "SELECT * FROM transaksi"
    if mode == 'harian':
        query += " WHERE tanggal = CURRENT_DATE"

    # Membaca data ke DataFrame Pandas
    df = pd.read_sql_query(query, conn)
    
    # Nama file unik berdasarkan waktu
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"laporan_{mode}_{timestamp}.xlsx"
    
    # Export ke Excel
    df.to_excel(filename, index=False)
    conn.close()
    return filename