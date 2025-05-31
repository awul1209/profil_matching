from flask import Flask, render_template, request, jsonify
import pymysql.cursors # Import pymysql

app = Flask(__name__)

# --- Konfigurasi Database ---
DB_CONFIG = {
    'host': 'localhost',      # Ganti jika database ada di server lain
    'user': 'root',           # User database Anda (biasanya root untuk lokal)
    'password': '',           # Password database Anda (kosong jika tidak ada)
    'database': 'db_profil', # Nama database yang sudah dibuat
    'cursorclass': pymysql.cursors.DictCursor # Mengembalikan hasil sebagai dictionary
}

# Fungsi untuk mendapatkan koneksi database
def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

# Variabel global untuk menyimpan profil ideal dan bobot (akan di-load saat aplikasi mulai)
PROFIL_IDEAL = {}
BOBOT_KRITERIA = {}

# Toleransi untuk gaji (misal: +/- 10% dari gaji ideal)
TOLERANSI_GAJI_PERSEN = 0.10

# Fungsi untuk memuat data dari database
def load_data_from_db():
    global PROFIL_IDEAL, BOBOT_KRITERIA
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Ambil Profil Ideal
            cursor.execute("SELECT kriteria, nilai FROM profil_ideal")
            for row in cursor.fetchall():
                # Konversi nilai ke int jika kriteria bukan gaji_harapan
                if row['kriteria'] == 'gaji_harapan':
                    PROFIL_IDEAL[row['kriteria']] = row['nilai']
                else:
                    PROFIL_IDEAL[row['kriteria']] = int(row['nilai'])

            # Ambil Bobot Kriteria
            cursor.execute("SELECT kriteria, bobot FROM bobot_kriteria")
            for row in cursor.fetchall():
                BOBOT_KRITERIA[row['kriteria']] = float(row['bobot'])
        
        print("Data Profil Ideal dan Bobot Kriteria berhasil dimuat dari database.")
        print("Profil Ideal:", PROFIL_IDEAL)
        print("Bobot Kriteria:", BOBOT_KRITERIA)

    except Exception as e:
        print(f"Error saat memuat data dari database: {e}")
        # Atur nilai default jika gagal memuat dari DB (opsional, untuk mencegah error crash)
        PROFIL_IDEAL = {
            'pendidikan': 4,
            'pengalaman_kerja': 5,
            'keterampilan_komunikasi': 5,
            'problem_solving': 4,
            'gaji_harapan': 7000000
        }
        BOBOT_KRITERIA = {
            'pendidikan': 0.25,
            'pengalaman_kerja': 0.25,
            'keterampilan_komunikasi': 0.15,
            'problem_solving': 0.15,
            'gaji_harapan': 0.20
        }
    finally:
        if conn:
            conn.close()

# Panggil fungsi untuk memuat data saat aplikasi pertama kali dijalankan
with app.app_context():
    load_data_from_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match_profile():
    # Pastikan data profil ideal dan bobot sudah terload
    if not PROFIL_IDEAL or not BOBOT_KRITERIA:
        return jsonify({"error": "Data profil ideal atau bobot belum dimuat. Coba restart aplikasi."}), 500

    data = request.json
    
    # Ambil data dari input pengguna
    pendidikan_kandidat = int(data.get('pendidikan'))
    pengalaman_kandidat = int(data.get('pengalaman_kerja'))
    komunikasi_kandidat = int(data.get('keterampilan_komunikasi'))
    problem_solving_kandidat = int(data.get('problem_solving'))
    gaji_kandidat = int(data.get('gaji_harapan'))

    skor_total = 0
    penjelasan_skor = []

    # --- Perhitungan Skor untuk Kriteria Numerik (semakin kecil selisih, semakin baik) ---
    
    # Pendidikan
    selisih_pendidikan = abs(PROFIL_IDEAL['pendidikan'] - pendidikan_kandidat)
    if selisih_pendidikan == 0:
        skor_pendidikan = 1.0 # Sangat cocok
    elif selisih_pendidikan == 1:
        skor_pendidikan = 0.8
    elif selisih_pendidikan == 2:
        skor_pendidikan = 0.5
    else:
        skor_pendidikan = 0.2
    
    skor_total += skor_pendidikan * BOBOT_KRITERIA['pendidikan']
    penjelasan_skor.append(f"Pendidikan: Skor {skor_pendidikan:.2f} (Ideal: {PROFIL_IDEAL['pendidikan']}, Kandidat: {pendidikan_kandidat})")

    # Pengalaman Kerja
    if pengalaman_kandidat >= PROFIL_IDEAL['pengalaman_kerja']:
        skor_pengalaman = 1.0
    else:
        skor_pengalaman = max(0.1, pengalaman_kandidat / PROFIL_IDEAL['pengalaman_kerja'])
    
    skor_total += skor_pengalaman * BOBOT_KRITERIA['pengalaman_kerja']
    penjelasan_skor.append(f"Pengalaman Kerja: Skor {skor_pengalaman:.2f} (Ideal: {PROFIL_IDEAL['pengalaman_kerja']}, Kandidat: {pengalaman_kandidat})")

    # Keterampilan Komunikasi & Problem Solving
    skor_komunikasi = 1 - (abs(PROFIL_IDEAL['keterampilan_komunikasi'] - komunikasi_kandidat) / 4)
    skor_problem_solving = 1 - (abs(PROFIL_IDEAL['problem_solving'] - problem_solving_kandidat) / 4)

    skor_total += skor_komunikasi * BOBOT_KRITERIA['keterampilan_komunikasi']
    skor_total += skor_problem_solving * BOBOT_KRITERIA['problem_solving']
    penjelasan_skor.append(f"Keterampilan Komunikasi: Skor {skor_komunikasi:.2f} (Ideal: {PROFIL_IDEAL['keterampilan_komunikasi']}, Kandidat: {komunikasi_kandidat})")
    penjelasan_skor.append(f"Problem Solving: Skor {skor_problem_solving:.2f} (Ideal: {PROFIL_IDEAL['problem_solving']}, Kandidat: {problem_solving_kandidat})")

    # Gaji Harapan
    skor_gaji = 0
    lower_bound_gaji = PROFIL_IDEAL['gaji_harapan'] * (1 - TOLERANSI_GAJI_PERSEN)
    upper_bound_gaji = PROFIL_IDEAL['gaji_harapan'] * (1 + TOLERANSI_GAJI_PERSEN)

    if lower_bound_gaji <= gaji_kandidat <= upper_bound_gaji:
        skor_gaji = 1.0
        penjelasan_skor.append(f"Gaji Harapan: Dalam rentang ideal. Skor {skor_gaji:.2f} (Ideal: {PROFIL_IDEAL['gaji_harapan']:,}, Kandidat: {gaji_kandidat:,})")
    elif gaji_kandidat < lower_bound_gaji:
        skor_gaji = 0.5
        penjelasan_skor.append(f"Gaji Harapan: Sedikit di bawah rentang ideal. Skor {skor_gaji:.2f} (Ideal: {PROFIL_IDEAL['gaji_harapan']:,}, Kandidat: {gaji_kandidat:,})")
    else:
        skor_gaji = 0.2
        penjelasan_skor.append(f"Gaji Harapan: Di atas rentang ideal. Skor {skor_gaji:.2f} (Ideal: {PROFIL_IDEAL['gaji_harapan']:,}, Kandidat: {gaji_kandidat:,})")
    
    skor_total += skor_gaji * BOBOT_KRITERIA['gaji_harapan']

    return jsonify({
        'skor_kecocokan': round(skor_total * 100, 2),
        'penjelasan': penjelasan_skor
    })

if __name__ == '__main__':
    # Untuk memastikan data terload sebelum server mulai melayani permintaan
    # Ini sudah dihandle di atas dengan app.app_context()
    app.run(debug=True)