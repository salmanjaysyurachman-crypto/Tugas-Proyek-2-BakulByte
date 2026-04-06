import pandas as pd
from database import get_db
from datetime import datetime
import 

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