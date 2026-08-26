import streamlit as st
import pandas as pd
from PIL import Image
import datetime
import plotly.express as px
import re
import os
import io
import base64
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SISTEM AUDIT EKSA", page_icon="📝", layout="wide")

# PAUTAN GOOGLE SHEETS ANDA
URL_GSHEETS = "https://docs.google.com/spreadsheets/d/1VZzjHycnRV_vOKNld5YSumf9rpOB3FOInjWlpF5qgZA/edit?usp=sharing"

# --- 2. PENGURUSAN PANGKALAN DATA (SESSION & GOOGLE SHEETS) ---
if 'pangkalan_data' not in st.session_state:
    st.session_state.pangkalan_data = {}

# Panggilan Sambungan GSheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    conn = None

# Fungsi Penukaran Gambar ke Base64 dengan Pemampatan
def gambar_ke_base64(file_obj, max_size=(300, 300), quality=50):
    if file_obj is None:
        return None
    try:
        img = Image.open(file_obj)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail(max_size)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        
        b64_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        st.error(f"Gagal memampatkan gambar: {e}")
        return None

# Fungsi Membaca Data Sedia Ada Dari Google Sheets
def senkron_data_dari_gsheets():
    if conn is not None:
        try:
            # ttl=0 untuk memastikan tiada cache yang disimpan
            df_existing = conn.read(spreadsheet=URL_GSHEETS, ttl=0)
            
            # 1. KOSONGKAN memori data sementara untuk elak data 'Ghost' (yang dah di-delete) muncul kembali
            data_terkini = {}
            
            if not df_existing.empty:
                for _, row in df_existing.iterrows():
                    # 2. Langkah Keselamatan (Bypass ralat jika terjumpa baris kosong di GSheets)
                    if pd.isna(row.get('Zon')) or pd.isna(row.get('Juruaudit')) or pd.isna(row.get('Komponen')):
                        continue

                    z = str(row['Zon']).strip()
                    j = str(row['Juruaudit']).strip()
                    k = str(row['Komponen']).strip()
                    no_i = str(row.get('No_Item', '')).strip()

                    if z not in data_terkini:
                        data_terkini[z] = {}
                    if j not in data_terkini[z]:
                        data_terkini[z][j] = {}

                    data_terkini[z][j]['_lokasi_khusus'] = str(row.get('Lokasi', ''))

                    if k not in data_terkini[z][j]:
                        data_terkini[z][j][k] = {}

                    # Baiki ralat gambar "nan" (kosong)
                    gbr_val = str(row.get('Gambar_Base64', ''))
                    if pd.isna(row.get('Gambar_Base64')) or gbr_val.lower() == 'nan' or gbr_val == '':
                        gbr_val = None

                    # 3. Baiki Ralat Markah yang buat data hilang masa refresh
                    try:
                        markah_val = int(float(row.get('Markah', 0)))
                    except (ValueError, TypeError):
                        markah_val = 0

                    # 4. Ambil kira Tindakan Susulan sekiranya wujud di Gsheets
                    ulasan_susulan = str(row.get('Ulasan_Susulan', ''))
                    if pd.isna(row.get('Ulasan_Susulan')) or ulasan_susulan.lower() == 'nan':
                        ulasan_susulan = ''
                        
                    gbr_susulan = str(row.get('Gambar_Susulan', ''))
                    if pd.isna(row.get('Gambar_Susulan')) or gbr_susulan.lower() == 'nan' or gbr_susulan == '':
                        gbr_susulan = None

                    tarikh_s = row.get('Tarikh_Susulan', datetime.date.today())
                    if pd.isna(tarikh_s):
                        tarikh_s = datetime.date.today()

                    data_terkini[z][j][k][no_i] = {
                        'Markah': markah_val,
                        'Ulasan': str(row.get('Ulasan', '')) if pd.notna(row.get('Ulasan')) else '',
                        'Gambar': gbr_val,
                        'Ulasan_Susulan': ulasan_susulan,
                        'Gambar_Susulan': gbr_susulan,
                        'Tarikh_Susulan': tarikh_s
                    }
            
            # Gantikan session_state lama dengan data baru yang 100% sama dengan GSheets
            st.session_state.pangkalan_data = data_terkini

        except Exception as e:
            # Outputkan log ralat sekiranya Gsheets rosak atau tidak dapat dibaca
            st.error(f"Ralat sistem menyegerak data GSheets: {e}")

senkron_data_dari_gsheets()

# --- CSS KHAS ---
st.markdown("""
    <style>
    @media print {
        header[data-testid="stHeader"],
        section[data-testid="stSidebar"],
        footer,
        .sembunyi-semasa-cetak {
            display: none !important;
        }
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin: 0 !important;
            width: 100% !important;
            max-width: none !important;
            background-color: #ffffff !important;
            color: #000000 !important;
        }
    }
    .jadual-laporan-wrapper {
        background-color: #ffffff !important;
        color: #000000 !important;
        padding: 15px;
        border-radius: 8px;
    }
    .jadual-laporan {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 13px;
        text-align: center;
        margin-top: 10px;
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    .jadual-laporan th, .jadual-laporan td {
        border: 1.5px solid #000000 !important;
        padding: 6px 8px;
        color: #000000 !important;
        background-color: #ffffff;
    }
    .jadual-laporan th {
        font-weight: bold;
        color: #000000 !important;
    }
    .header-efektif { background-color: #fef3c7 !important; color: #000000 !important; }
    .header-komited { background-color: #bfdbfe !important; color: #000000 !important; }
    .header-sepakat { background-color: #fca5a5 !important; color: #000000 !important; }
    .header-aktif { background-color: #bbf7d0 !important; color: #000000 !important; }
    .header-kelabu { background-color: #e5e7eb !important; color: #000000 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNGSI BACAAN EXCEL ---
@st.cache_data
def muat_data_eksa(file_path):
    xls = pd.ExcelFile(file_path)
    data_komponen = {}
    
    valid_sheets = [s for s in xls.sheet_names if str(s).upper().startswith('KOMPONEN')]
    
    for sheet in valid_sheets:
        df = pd.read_excel(file_path, sheet_name=sheet)
        item_list = []
        current_subtopic = "KRITERIA UMUM"
        
        for index, row in df.iterrows():
            for col_idx in [0, 1]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if isinstance(val, str) and re.match(r'^[A-Z]\d+\)', str(val).strip()):
                        current_subtopic = str(val).strip()
                        break 
            
            no_item = None
            perkara = None
            rubrik = {}
            
            for col_idx in [0, 1]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    
                    if str(val).strip().isdigit():
                        next_val = row.iloc[col_idx + 1]
                        
                        if pd.notna(next_val) and isinstance(next_val, str) and len(next_val.strip()) > 5:
                            no_item = str(val).strip()
                            perkara = str(next_val).strip()
                            
                            for i in range(1, 6):
                                rub_idx = col_idx + 1 + i
                                if rub_idx < len(row):
                                    rub_val = str(row.iloc[rub_idx]).strip()
                                    rubrik[i] = rub_val if rub_val != 'nan' else ""
                                else:
                                    rubrik[i] = ""
                            break 
            
            if no_item:
                item_list.append({
                    'Subtopik': current_subtopic,
                    'No': no_item,
                    'Perkara': perkara,
                    'Rubrik': rubrik
                })
                
        if item_list:
            data_komponen[sheet] = item_list
            
    return data_komponen

fail_excel = '8. MARKAH AUDIT EKSA.xlsx'
try:
    data_eksa = muat_data_eksa(fail_excel)
except Exception as e:
    st.error(f"Gagal membaca fail Excel. Pastikan fail '{fail_excel}' wujud di dalam folder ini.")
    st.stop()

# --- FUNGSI BARU: PENAPISAN ITEM MENGIKUT ZON (VERSI KEBAL) ---
def dapatkan_item_tapis(komponen, zon):
    # .strip() memastikan tiada 'space' kosong yang mengganggu bacaan
    komponen_upper = str(komponen).upper().strip()
    zon_upper = str(zon).upper().strip()
    item_dikecualikan = []
    
    # Logik pengecualian mengikut zon
    if "KOMPONEN B" in komponen_upper:
        if "EFEKTIF" in zon_upper:
            item_dikecualikan = ["12", "13", "15"]
        elif "KOMITED" in zon_upper:
            item_dikecualikan = ["11", "14", "16"]
        elif "SEPAKAT" in zon_upper:
            item_dikecualikan = ["11", "12", "13", "14", "15", "16"]
        elif "AKTIF" in zon_upper:
            item_dikecualikan = ["11", "13", "14", "15", "16"]
            
    elif "KOMPONEN C" in komponen_upper:
        if "EFEKTIF" in zon_upper:
            item_dikecualikan = ["5", "6", "7", "8"]
        elif "KOMITED" in zon_upper:
            item_dikecualikan = ["1", "6", "7"]
        elif "SEPAKAT" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "5", "8"]
        elif "AKTIF" in zon_upper:
            item_dikecualikan = ["1", "5", "6", "7", "8"]
            
    elif "KOMPONEN D" in komponen_upper:
        if "EFEKTIF" in zon_upper:
            item_dikecualikan = ["3", "4", "5"]
        elif "KOMITED" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "5", "6"]
        elif "SEPAKAT" in zon_upper:
            item_dikecualikan = ["1", "5", "6"]
        elif "AKTIF" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "4", "6"]
            
    items_asal = data_eksa.get(komponen, [])
    filtered_items = []
    
    for item in items_asal:
        # Menarik keluar sebarang nombor bulat. 
        # Jika dalam Excel ditulis "B12" atau " 12 ", ia tetap diekstrak menjadi "12".
        num_only = ''.join(filter(str.isdigit, str(item['No'])))
        
        # Tambah ke dalam senarai borang jika nombor item BUKAN dalam senarai dikecualikan
        if num_only and num_only not in item_dikecualikan:
            filtered_items.append(item)
            
    return filtered_items

# --- FUNGSI KIRA PRESTASI (DIKEMAS KINI: HANYA KIRA ITEM SAH) ---
def kira_prestasi(data_individu, zon, filter_komp="Semua Komponen"):
    ringkasan_markah = {}
    total_markah_semua = 0
    total_penuh_semua = 0
    
    komponen_dipilih = data_eksa.keys() if filter_komp == "Semua Komponen" else [filter_komp]
    
    for komp in komponen_dipilih:
        rekod_komponen = data_individu.get(komp, {})
        
        # Dapatkan item yang HANYA SAH untuk zon ini
        item_sah = dapatkan_item_tapis(komp, zon)
        no_item_sah = [str(x['No']) for x in item_sah]
        
        jumlah_markah = 0
        if rekod_komponen:
            for no_i, val in rekod_komponen.items():
                # HANYA campur markah jika item tidak dibuang
                if str(no_i) in no_item_sah and isinstance(val, dict):
                    jumlah_markah += val['Markah']
        
        jumlah_item = len(item_sah)
        markah_penuh = jumlah_item * 5
        
        peratusan = (jumlah_markah / markah_penuh) * 100 if markah_penuh > 0 else 0
        if jumlah_item > 0:
            ringkasan_markah[komp] = peratusan
            
        total_markah_semua += jumlah_markah
        total_penuh_semua += markah_penuh
        
    peratusan_keseluruhan = (total_markah_semua / total_penuh_semua) * 100 if total_penuh_semua > 0 else 0
    return ringkasan_markah, total_markah_semua, total_penuh_semua, peratusan_keseluruhan

# --- 4. SIDEBAR LOGO ---
fail_logo = None
for nm in ['logo.png', 'Logo.png', 'LOGO.PNG', 'logo.PNG', 'logo.jpeg', 'logo.jpg']:
    if os.path.exists(nm):
        fail_logo = nm
        break

if fail_logo:
    st.sidebar.image(fail_logo, use_container_width=True)

st.sidebar.title("SISTEM AUDIT EKSA")
st.sidebar.markdown("---")
st.sidebar.header("Navigasi Sistem")
menu_paparan = st.sidebar.radio("Sila pilih menu paparan:", [
    "📋 Modul Kerja (Borang)", 
    "📊 Markah Audit", 
    "📈 Rumusan Markah Terperinci",
    "🖨️ Laporan Penuh & Cetakan",
])


# ==========================================
# PAPARAN 1: BORANG PENILAIAN (MODUL KERJA)
# ==========================================
# ==========================================
# PAPARAN 1: BORANG PENILAIAN (MODUL KERJA)
# ==========================================
if menu_paparan == "📋 Modul Kerja (Borang)":

    st.title("Borang Penilaian EKSA")
    st.write("Sila lengkapkan maklumat audit dan pilih komponen yang ingin dinilai.")

    col_info1, col_info2, col_info3, col_info4 = st.columns([1, 1, 1.2, 1])
    with col_info1:
        komponen_pilihan = st.selectbox("1. Pilih Komponen:", list(data_eksa.keys()))
    with col_info2:
        komponen_upper = str(komponen_pilihan).upper()
        if "KOMPONEN A" in komponen_upper or "KOMPONEN E" in komponen_upper:
            pilihan_zon_rasmi = ["ZON INDUK", "ZON LAIN-LAIN..."]
        else:
            pilihan_zon_rasmi = ["ZON EFEKTIF", "ZON KOMITED", "ZON SEPAKAT", "ZON AKTIF", "ZON LAIN-LAIN..."]

        lokasi_audit_sel = st.selectbox("2. Pilih Zon:", pilihan_zon_rasmi)

        if lokasi_audit_sel == "ZON LAIN-LAIN...":
            zon_audit = st.text_input("Nama Zon Manual:").strip().upper()
        else:
            zon_audit = lokasi_audit_sel
    with col_info3:
        lokasi_khusus = st.text_input("3. Lokasi Di-Audit (Manual):", "Bilik Mesyuarat Utama / Aras 2").strip()
    with col_info4:
        nama_juruaudit = st.text_input("4. Nama Juruaudit:", "Juruaudit 1").strip()

    st.markdown("---")

    if zon_audit and nama_juruaudit:
        if zon_audit not in st.session_state.pangkalan_data:
            st.session_state.pangkalan_data[zon_audit] = {}
        if nama_juruaudit not in st.session_state.pangkalan_data[zon_audit]:
            st.session_state.pangkalan_data[zon_audit][nama_juruaudit] = {}

        data_semasa = st.session_state.pangkalan_data[zon_audit][nama_juruaudit]
        data_semasa['_lokasi_khusus'] = lokasi_khusus

        st.subheader(f"Menilai: {komponen_pilihan}")
        st.caption(f"**Zon:** {zon_audit} | **Lokasi:** {lokasi_khusus} | **Juruaudit:** {nama_juruaudit}")

        # MENGGUNAKAN ITEM YANG TELAH DITAPIS MENGIKUT ZON
        items = dapatkan_item_tapis(komponen_pilihan, zon_audit)

        if komponen_pilihan not in data_semasa:
            data_semasa[komponen_pilihan] = {}

        # Semak jika komponen ini pernah dinilai sebelumnya
        komponen_pernah_dinilai = len(data_semasa[komponen_pilihan]) > 0

        if not items:
            st.info("Tiada item untuk dinilai bagi komponen dan zon yang dipilih berdasarkan kriteria pengecualian.")
        else:
            with st.form(key=f"form_{komponen_pilihan}"):
                current_displayed_subtopic = ""
                temp_data_komponen = {} # Simpanan sementara semasa merender borang

                for item in items:
                    if item['Subtopik'] != current_displayed_subtopic:
                        st.markdown(f"<h3 style='color: #007BFF; margin-top: 30px;'>📑 {item['Subtopik']}</h3>", unsafe_allow_html=True)
                        current_displayed_subtopic = item['Subtopik']

                    st.markdown(f"**Item {item['No']}: {item['Perkara']}**")

                    with st.expander(f"Lihat Rubrik Pemarkahan untuk Item {item['No']}"):
                        for skor, deskripsi in item['Rubrik'].items():
                            if deskripsi and deskripsi != 'nan':
                                st.write(f"**Skor {skor}:** {deskripsi}")

                    rekod_lama = data_semasa[komponen_pilihan].get(item['No'], None)
                    
                    if rekod_lama is None:
                        # Jika tiada rekod lama bagi item ini, set 'N/A' jika komponen pernah dihantar (bermaksud item dipadam)
                        # Jika ia adalah borang komponen baharu, set default kepada 3
                        default_markah = "N/A" if komponen_pernah_dinilai else 3
                        default_ulasan = ""
                        default_gambar = None
                        default_ulasan_susulan = ""
                        default_gambar_susulan = None
                        default_tarikh_susulan = datetime.date.today()
                    else:
                        default_markah = rekod_lama['Markah']
                        default_ulasan = rekod_lama['Ulasan']
                        default_gambar = rekod_lama['Gambar']
                        default_ulasan_susulan = rekod_lama.get('Ulasan_Susulan', '')
                        default_gambar_susulan = rekod_lama.get('Gambar_Susulan', None)
                        default_tarikh_susulan = rekod_lama.get('Tarikh_Susulan', datetime.date.today())

                    col1, col2, col3 = st.columns([1.2, 1.3, 1.5])
                    with col1:
                        markah = st.radio("Skor Penilaian", options=[1, 2, 3, 4, 5, "N/A"], 
                                          index=[1, 2, 3, 4, 5, "N/A"].index(default_markah), 
                                          horizontal=True, key=f"mark_{komponen_pilihan}_{item['No']}")
                    with col2:
                        ulasan = st.text_input("Ulasan/Komen", value=default_ulasan, 
                                               key=f"ulasan_{komponen_pilihan}_{item['No']}")
                    with col3:
                        gambar_muat_naik = st.file_uploader("Muat Naik Bukti", type=['png', 'jpg', 'jpeg'], 
                                                            key=f"gambar_{komponen_pilihan}_{item['No']}")
                        gambar_disimpan = default_gambar

                        if gambar_muat_naik is not None:
                            gambar_disimpan = gambar_ke_base64(gambar_muat_naik)

                        if gambar_disimpan:
                            st.image(gambar_disimpan, width=120, caption="Gambar dimuat naik")

                    # Simpan dalam dict sementara HANYA jika pengguna tidak memilih "N/A"
                    if markah != "N/A":
                        temp_data_komponen[item['No']] = {
                            'Markah': markah, 
                            'Ulasan': ulasan,
                            'Gambar': gambar_disimpan,
                            'Ulasan_Susulan': default_ulasan_susulan,
                            'Gambar_Susulan': default_gambar_susulan,
                            'Tarikh_Susulan': default_tarikh_susulan
                        }
                    
                    st.markdown("---")

                hantar = st.form_submit_button("Simpan Markah & Gambar")

                if hantar:
                    # Kemas kini state dengan data yang sah (N/A diabaikan sepenuhnya)
                    data_semasa[komponen_pilihan] = temp_data_komponen
                    st.session_state.pangkalan_data[zon_audit][nama_juruaudit] = data_semasa

                    if conn is not None:
                        try:
                            baris_baru = []
                            tarikh_sekarang = datetime.date.today().strftime('%Y-%m-%d')

                            for no_i, d_item in temp_data_komponen.items():
                                padanan = [orig for orig in data_eksa.get(komponen_pilihan, []) if str(orig['No']).strip() == str(no_i).strip()]
                                subtopik_val = padanan[0]['Subtopik'] if padanan else "KRITERIA UMUM"

                                baris_baru.append({
                                    'Tarikh': tarikh_sekarang,
                                    'Zon': zon_audit,
                                    'Lokasi': lokasi_khusus,
                                    'Juruaudit': nama_juruaudit,
                                    'Komponen': komponen_pilihan,
                                    'Subtopik': subtopik_val,
                                    'No_Item': str(no_i),
                                    'Markah': d_item['Markah'],
                                    'Ulasan': d_item['Ulasan'],
                                    'Gambar_Base64': d_item['Gambar'] if d_item['Gambar'] else ''
                                })

                            df_baru = pd.DataFrame(baris_baru)

                            # Baca dan tapis data lama GSheets (Padam rekod lama Zon & Komponen ini)
                            df_lama = conn.read(spreadsheet=URL_GSHEETS, ttl=0)
                            if not df_lama.empty:
                                mask = ~((df_lama['Zon'] == zon_audit) & 
                                         (df_lama['Juruaudit'] == nama_juruaudit) & 
                                         (df_lama['Komponen'] == komponen_pilihan))
                                df_filtered = df_lama[mask]
                            else:
                                df_filtered = pd.DataFrame()

                            if not df_baru.empty:
                                df_gabung = pd.concat([df_filtered, df_baru], ignore_index=True)
                            else:
                                df_gabung = df_filtered

                            conn.update(spreadsheet=URL_GSHEETS, data=df_gabung)
                            st.success("✅ Data dan gambar berjaya disimpan secara KEKAL ke Google Sheets!")
                        except Exception as err:
                            st.error(f"Gagal berhubung ke Google Sheets: {err}")
                    else:
                        st.warning("Sambungan Google Sheets gagal dibuka. Pastikan secrets.toml telah dikonfigurasi.")
    else:
        st.warning("Sila pastikan Zon dan Nama Juruaudit telah diisi untuk memulakan penilaian.")

# ==========================================
# PAPARAN 2: MARKAH AUDIT (DENGAN EDIT & DELETE)
# ==========================================
elif menu_paparan == "📊 Markah Audit":
        
    st.title("📊 Papan Markah Audit EKSA")
    st.write("Paparan analisis interaktif berdasarkan Komponen, Zon, Lokasi, dan Juruaudit.")
    st.markdown("---")
    
    senarai_zon = list(st.session_state.pangkalan_data.keys())
    
    if not senarai_zon:
        st.warning("Belum ada sebarang data audit yang direkodkan dalam sistem ini.")
    else:
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            pilih_komponen = st.selectbox("1. Pilih Komponen:", ["Semua Komponen"] + list(data_eksa.keys()), key="m_komp")
            
        with col_m2:
            pilih_zon = st.selectbox("2. Pilih Zon:", ["Semua Zon"] + senarai_zon, key="m_zon")
            
        if pilih_zon == "Semua Zon":
            senarai_auditor_raw = []
            for z in senarai_zon:
                senarai_auditor_raw.extend(list(st.session_state.pangkalan_data[z].keys()))
            senarai_auditor = list(set(senarai_auditor_raw))
        else:
            senarai_auditor = list(st.session_state.pangkalan_data[pilih_zon].keys())
            
        with col_m3:
            pilih_auditor = st.selectbox("3. Pilih Juruaudit:", ["Semua Juruaudit"] + senarai_auditor, key="m_auditor")
            
        st.markdown("---")

        zon_sasaran = senarai_zon if pilih_zon == "Semua Zon" else [pilih_zon]
        
        st.subheader("📊 Prestasi Pencapaian Markah")
        
        data_graf = []
        for zon in zon_sasaran:
            dict_zon = st.session_state.pangkalan_data[zon]
            auditor_sasaran = list(dict_zon.keys()) if pilih_auditor == "Semua Juruaudit" else ([pilih_auditor] if pilih_auditor in dict_zon else [])
            
            for nm_auditor in auditor_sasaran:
                ringkasan, jum_markah, jum_penuh, peratus = kira_prestasi(dict_zon[nm_auditor], zon, pilih_komponen)
                lok_khusus = dict_zon[nm_auditor].get('_lokasi_khusus', 'Biasa')
                if jum_penuh > 0:
                    data_graf.append({
                        "Zon": zon,
                        "Lokasi": lok_khusus,
                        "Nama Juruaudit": nm_auditor,
                        "Markah Dinilai": jum_markah,
                        "Markah Penuh": jum_penuh,
                        "Peratusan (%)": round(peratus, 2)
                    })
        
        if len(data_graf) > 1 or pilih_zon == "Semua Zon" or pilih_auditor == "Semua Juruaudit":
            df_graf = pd.DataFrame(data_graf)
            if not df_graf.empty:
                fig = px.bar(
                    df_graf, 
                    x="Zon", 
                    y="Markah Dinilai", 
                    color="Nama Juruaudit", 
                    barmode="group", 
                    hover_data={"Lokasi": True, "Peratusan (%)": True, "Markah Penuh": True}, 
                    text="Peratusan (%)"
                )
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                fig.update_layout(xaxis_title="Zon Audit", yaxis_title="Markah Dinilai")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Tiada data markah direkodkan untuk tapisan ini.")
                
        elif len(data_graf) == 1:
            st.metric(f"Markah Diberikan oleh {data_graf[0]['Nama Juruaudit']} bagi {data_graf[0]['Zon']} ({data_graf[0]['Lokasi']})", 
                      f"{data_graf[0]['Markah Dinilai']} / {data_graf[0]['Markah Penuh']} ({data_graf[0]['Peratusan (%)']}%)")

        st.markdown("---")

        senarai_komp_laporan = list(data_eksa.keys()) if pilih_komponen == "Semua Komponen" else [pilih_komponen]

        # ==========================================
        # SENARAI REKOD AUDIT (DENGAN EDIT & DELETE)
        # ==========================================
        st.subheader("📝 Pengurusan & Suntingan Rekod Audit")
        
        ada_rekod = False
        for zon in zon_sasaran:
            dict_zon_terpilih = st.session_state.pangkalan_data[zon]
            senarai_auditor_laporan = list(dict_zon_terpilih.keys()) if pilih_auditor == "Semua Juruaudit" else ([pilih_auditor] if pilih_auditor in dict_zon_terpilih else [])
            
            for nm_auditor in senarai_auditor_laporan:
                rekod_auditor = dict_zon_terpilih[nm_auditor]
                lok_khusus = rekod_auditor.get('_lokasi_khusus', 'Biasa')
                
                for komp in senarai_komp_laporan:
                    rekod_komp = rekod_auditor.get(komp, {})
                    
                    item_sah_zon = dapatkan_item_tapis(komp, zon)
                    no_item_sah_zon = [str(x['No']) for x in item_sah_zon]
                    
                    for no_item, data in list(rekod_komp.items()):
                        # Sembunyikan item yang dibuang agar markah tidak terpapar/diedit
                        if str(no_item) not in no_item_sah_zon:
                            continue
                            
                        if isinstance(data, dict):
                            ada_rekod = True
                            padanan_item = [orig for orig in data_eksa.get(komp, []) if str(orig['No']).strip() == str(no_item).strip()]
                            perkara_txt = padanan_item[0]['Perkara'] if padanan_item else f"Item {no_item}"
                            
                            with st.expander(f"📌 [{zon} - {lok_khusus}] {komp} - Item {no_item}: {perkara_txt} (Markah: {data['Markah']}/5)"):
                                c_info, c_edit, c_del = st.columns([3, 1, 1])
                                
                                with c_info:
                                    st.write(f"**Juruaudit:** {nm_auditor}")
                                    st.write(f"**Ulasan:** {data['Ulasan'] if data['Ulasan'] else '*Tiada*'}")
                                    if data.get('Gambar'):
                                        st.image(data['Gambar'], width=150, caption="Bukti Gambar")
                                
                                # --- BUTANG SUNTING (EDIT) ---
                                with c_edit:
                                    with st.popover("✏️ Edit"):
                                        st.markdown(f"**Edit Item {no_item}**")
                                        
                                        markah_baru = st.radio(
                                            "Markah Baharu", 
                                            [1, 2, 3, 4, 5], 
                                            index=[1, 2, 3, 4, 5].index(data['Markah']), 
                                            horizontal=True,
                                            key=f"edit_m_{zon}_{nm_auditor}_{komp}_{no_item}"
                                        )
                                        ulasan_baru = st.text_input(
                                            "Ulasan Baharu", 
                                            value=data['Ulasan'],
                                            key=f"edit_u_{zon}_{nm_auditor}_{komp}_{no_item}"
                                        )
                                        gambar_baru = st.file_uploader(
                                            "Tukar Gambar", 
                                            type=['png', 'jpg', 'jpeg'],
                                            key=f"edit_g_{zon}_{nm_auditor}_{komp}_{no_item}"
                                        )
                                        
                                        if st.button("💾 Simpan Kemas Kini", key=f"btn_save_{zon}_{nm_auditor}_{komp}_{no_item}"):
                                            st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]['Markah'] = markah_baru
                                            st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]['Ulasan'] = ulasan_baru
                                            
                                            gbr_base64_baru = data['Gambar']
                                            if gambar_baru is not None:
                                                gbr_base64_baru = gambar_ke_base64(gambar_baru)
                                                st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]['Gambar'] = gbr_base64_baru
                                            
                                            if conn is not None:
                                                try:
                                                    df_g = conn.read(spreadsheet=URL_GSHEETS, ttl=0)
                                                    mask = (df_g['Zon'] == zon) & (df_g['Juruaudit'] == nm_auditor) & (df_g['Komponen'] == komp) & (df_g['No_Item'].astype(str) == str(no_item))
                                                    df_g.loc[mask, 'Markah'] = markah_baru
                                                    df_g.loc[mask, 'Ulasan'] = ulasan_baru
                                                    if gambar_baru is not None:
                                                        df_g.loc[mask, 'Gambar_Base64'] = gbr_base64_baru
                                                    conn.update(spreadsheet=URL_GSHEETS, data=df_g)
                                                except Exception:
                                                    pass
                                            
                                            st.success("✅ Rekod berjaya dikemas kini!")
                                            st.rerun()

                                # --- BUTANG PADAM (DELETE) ---
                                with c_del:
                                    if st.button("🗑️ Padam", key=f"del_{zon}_{nm_auditor}_{komp}_{no_item}", type="primary"):
                                        del st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]
                                        
                                        if conn is not None:
                                            try:
                                                df_g = conn.read(spreadsheet=URL_GSHEETS, ttl=0)
                                                df_filtered = df_g[~((df_g['Zon'] == zon) & (df_g['Juruaudit'] == nm_auditor) & (df_g['Komponen'] == komp) & (df_g['No_Item'].astype(str) == str(no_item)))]
                                                conn.update(spreadsheet=URL_GSHEETS, data=df_filtered)
                                            except Exception:
                                                pass
                                        
                                        st.warning("🗑️ Rekod telah dipadam.")
                                        st.rerun()

        if not ada_rekod:
            st.info("Tiada rekod penilaian dijumpai bagi tapisan yang dipilih.")

        st.markdown("---")

        st.subheader("🌟 Pencapaian Cemerlang (Markah 5)")
        ada_cemerlang = False
        
        for zon in zon_sasaran:
            dict_zon_terpilih = st.session_state.pangkalan_data[zon]
            senarai_auditor_laporan = list(dict_zon_terpilih.keys()) if pilih_auditor == "Semua Juruaudit" else ([pilih_auditor] if pilih_auditor in dict_zon_terpilih else [])
            
            for nm_auditor in senarai_auditor_laporan:
                rekod_auditor = dict_zon_terpilih[nm_auditor]
                lok_khusus = rekod_auditor.get('_lokasi_khusus', 'Biasa')
                
                for komp in senarai_komp_laporan:
                    rekod_komp = rekod_auditor.get(komp, {})
                    item_sah_zon = dapatkan_item_tapis(komp, zon)
                    no_item_sah_zon = [str(x['No']) for x in item_sah_zon]
                    
                    for no_item, data in rekod_komp.items():
                        if str(no_item) in no_item_sah_zon and isinstance(data, dict) and data.get('Markah') == 5:
                            ada_cemerlang = True
                            padanan_item = [orig for orig in data_eksa.get(komp, []) if str(orig['No']).strip() == str(no_item).strip()]
                            subtopik_item = padanan_item[0]['Subtopik'] if padanan_item else "KRITERIA UMUM"
                            perkara_item = padanan_item[0]['Perkara'] if padanan_item else f"Item {no_item}"
                            
                            st.success(f"**[{zon} - {lok_khusus}] {subtopik_item} - Item {no_item}** \n{perkara_item} \n*(Oleh: {nm_auditor}) | Ulasan: {data['Ulasan'] if data['Ulasan'] else 'Memuaskan'}*")
        
        if not ada_cemerlang:
            st.info("Tiada rekod item cemerlang (Markah 5) dijumpai untuk kriteria yang dipilih.")

        st.markdown("---")

        st.subheader("⚠️ Pencapaian Rendah & Tindakan Susulan (Markah 1 & 2)")
        ada_kelemahan = False
        
        for zon in zon_sasaran:
            dict_zon_terpilih = st.session_state.pangkalan_data[zon]
            senarai_auditor_laporan = list(dict_zon_terpilih.keys()) if pilih_auditor == "Semua Juruaudit" else ([pilih_auditor] if pilih_auditor in dict_zon_terpilih else [])
            
            for nm_auditor in senarai_auditor_laporan:
                rekod_auditor = dict_zon_terpilih[nm_auditor]
                lok_khusus = rekod_auditor.get('_lokasi_khusus', 'Biasa')
                
                for komp in senarai_komp_laporan:
                    rekod_komp = rekod_auditor.get(komp, {})
                    item_sah_zon = dapatkan_item_tapis(komp, zon)
                    no_item_sah_zon = [str(x['No']) for x in item_sah_zon]
                    
                    for no_item, data in rekod_komp.items():
                        if str(no_item) in no_item_sah_zon and isinstance(data, dict) and data.get('Markah', 5) <= 2:
                            ada_kelemahan = True
                            padanan_item = [orig for orig in data_eksa.get(komp, []) if str(orig['No']).strip() == str(no_item).strip()]
                            subtopik_item = padanan_item[0]['Subtopik'] if padanan_item else "KRITERIA UMUM"
                            perkara_item = padanan_item[0]['Perkara'] if padanan_item else f"Item {no_item}"
                            
                            st.error(f"**[{zon} - {lok_khusus}] {subtopik_item} - Item {no_item}** \n{perkara_item} *(Dinilai oleh: {nm_auditor})*")
                            col_sebelum, col_selepas = st.columns(2)
                            
                            with col_sebelum:
                                st.markdown("#### 🔴 Penemuan Asal")
                                st.write(f"**Skor Diberikan:** {data['Markah']} / 5")
                                st.write(f"**Komen Juruaudit:** {data['Ulasan'] if data['Ulasan'] else '*Tiada ulasan ditinggalkan.*'}")
                                if data.get('Gambar'):
                                    st.image(data['Gambar'], caption="Bukti Semasa Audit", use_container_width=True)
                                else:
                                    st.info("Tiada bukti gambar asal.")
                            
                            with col_selepas:
                                st.markdown("#### 🟢 Tindakan Penambahbaikan")
                                with st.form(key=f"susulan_m_{zon}_{nm_auditor}_{komp}_{no_item}"):
                                    tarikh_baru = st.date_input("Tarikh Tindakan:", value=data.get('Tarikh_Susulan', datetime.date.today()))
                                    ulasan_baru = st.text_area("Tindakan yang telah diambil:", value=data['Ulasan_Susulan'], height=80)
                                    gambar_baru_muat_naik = st.file_uploader("Muat Naik Gambar (Selepas)", type=['png', 'jpg', 'jpeg'], key=f"gambar_susulan_m_{zon}_{nm_auditor}_{komp}_{no_item}")
                                    simpan_susulan = st.form_submit_button("Simpan & Kemas Kini Susulan")
                                    
                                    gambar_susulan_disimpan = data['Gambar_Susulan']
                                    if gambar_baru_muat_naik is not None:
                                        gambar_susulan_disimpan = gambar_ke_base64(gambar_baru_muat_naik)
                                        
                                    if simpan_susulan:
                                        st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]['Tarikh_Susulan'] = tarikh_baru
                                        st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]['Ulasan_Susulan'] = ulasan_baru
                                        st.session_state.pangkalan_data[zon][nm_auditor][komp][no_item]['Gambar_Susulan'] = gambar_susulan_disimpan
                                        st.success("Tindakan susulan dikemas kini!")
                                        st.rerun()

                                if data['Ulasan_Susulan']:
                                    st.write(f"**Tarikh Selesai:** {data['Tarikh_Susulan'].strftime('%d/%m/%Y')}")
                                    st.write(f"**Tindakan Ambilan:** {data['Ulasan_Susulan']}")
                                else:
                                    st.write("*(Belum ada tindakan direkodkan)*")

                                if data['Gambar_Susulan']:
                                    st.image(data['Gambar_Susulan'], caption="Bukti Selepas Penambahbaikan", use_container_width=True)
                            st.markdown("---")

        if not ada_kelemahan:
            st.success("Tahniah! Tiada item dengan markah rendah (1 atau 2) yang memerlukan tindakan susulan bagi tetapan yang dipilih.")

# ==========================================
# PAPARAN 3: RUMUSAN MARKAH TERPERINCI (BARU)
# ==========================================
elif menu_paparan == "📈 Rumusan Markah Terperinci":
        
    st.title("📈 Rumusan Markah Terperinci")
    st.write("Paparan terperinci rubrik dan markah mengikut komponen dan zon seperti jadual rasmi.")
    
    pilih_komp = st.selectbox("Sila Pilih Komponen:", list(data_eksa.keys()))
    
    komponen_upper = str(pilih_komp).upper()
    if "KOMPONEN A" in komponen_upper or "KOMPONEN E" in komponen_upper:
        zon_rasmi_list = ["ZON INDUK"]
    else:
        zon_rasmi_list = ["ZON EFEKTIF", "ZON KOMITED", "ZON SEPAKAT", "ZON AKTIF"]
    
    st.markdown("---")
    
    colspan_markah = len(zon_rasmi_list)
    header_zon_html = ""
    for z in zon_rasmi_list:
        nama_zon_br = z.replace("ZON ", "ZON<br>")
        header_zon_html += f'<th class="markah-column">{nama_zon_br}</th>\n'
    
    html_jadual_rumusan = f"""<style>
.tabel-rumusan {{ 
    width: 100%; 
    border-collapse: collapse; 
    font-size: 12px; 
    font-family: Arial, sans-serif; 
    background-color: white;
    color: black;
}}
.tabel-rumusan th, .tabel-rumusan td {{ 
    border: 2px solid #e67e22;
    padding: 6px; 
    text-align: left; 
    vertical-align: top; 
}}
.tabel-rumusan th {{ 
    text-align: center; 
    background-color: #fdebd0;
    font-weight: bold; 
}}
.subtopik-row {{ 
    background-color: #fae5d3; 
    font-weight: bold; 
    text-transform: uppercase;
}}
.center-text {{ 
    text-align: center; 
}}
.markah-column {{
    width: 6%;
    text-align: center;
}}
</style>

<div style='overflow-x:auto;'>
<table class="tabel-rumusan">
<thead>
<tr>
<th colspan="7" style="font-size: 16px;">{pilih_komp.upper()}</th>
<th colspan="{colspan_markah}" style="font-size: 14px;">MARKAH</th>
</tr>
<tr>
<th colspan="2" style="width: 25%;">KEPERLUAN UTAMA PELAKSANAAN</th>
<th style="width: 11%;">1</th>
<th style="width: 11%;">2</th>
<th style="width: 11%;">3</th>
<th style="width: 11%;">4</th>
<th style="width: 11%;">5</th>
{header_zon_html}
</tr>
</thead>
<tbody>
"""
    
    current_sub = ""
    jumlah_skor_zon = {z: 0 for z in zon_rasmi_list}
    
    for item in data_eksa[pilih_komp]:
        if item['Subtopik'] != current_sub:
            total_colspan = 7 + colspan_markah
            html_jadual_rumusan += f"<tr class='subtopik-row'><td colspan='{total_colspan}'>{item['Subtopik']}</td></tr>"
            current_sub = item['Subtopik']
            
        skor_dicatat = {}
        for z in zon_rasmi_list:
            # SEMAK JIKA ITEM INI DIKECUALIKAN UNTUK ZON BERKENAAN
            item_sebenar_zon = dapatkan_item_tapis(pilih_komp, z)
            item_nums_zon = [str(x['No']) for x in item_sebenar_zon]
            
            if str(item['No']) not in item_nums_zon:
                skor_dicatat[z] = "N/A"
            else:
                skor_semasa = ""
                if z in st.session_state.pangkalan_data:
                    for aud_name, data_auditor in st.session_state.pangkalan_data[z].items():
                        if pilih_komp in data_auditor and item['No'] in data_auditor[pilih_komp]:
                            skor_val = data_auditor[pilih_komp][item['No']]['Markah']
                            skor_semasa = skor_val
                            jumlah_skor_zon[z] += skor_val
                            break
                skor_dicatat[z] = skor_semasa
            
        kolum_markah_html = ""
        for z in zon_rasmi_list:
            kolum_markah_html += f'<td class="center-text"><b>{skor_dicatat[z]}</b></td>\n'
            
        html_jadual_rumusan += f"""<tr>
<td class="center-text"><b>{item['No']}</b></td>
<td>{item['Perkara']}</td>
<td>{item['Rubrik'].get(1, '')}</td>
<td>{item['Rubrik'].get(2, '')}</td>
<td>{item['Rubrik'].get(3, '')}</td>
<td>{item['Rubrik'].get(4, '')}</td>
<td>{item['Rubrik'].get(5, '')}</td>
{kolum_markah_html}
</tr>"""
        
    kolum_jumlah_html = ""
    for z in zon_rasmi_list:
        kolum_jumlah_html += f'<td class="center-text" style="font-weight: bold; font-size: 14px;">{jumlah_skor_zon[z]}</td>\n'
        
    html_jadual_rumusan += f"""<tr>
<td colspan="7" style="text-align: right; font-weight: bold; font-size: 14px;">JUMLAH</td>
{kolum_jumlah_html}
</tr>"""
    
    html_jadual_rumusan += "</tbody></table></div>"
    
    st.markdown(html_jadual_rumusan, unsafe_allow_html=True)

# ==========================================
# PAPARAN 4: LAPORAN PENUH & CETAKAN
# ==========================================
elif menu_paparan == "🖨️ Laporan Penuh & Cetakan":
        
    st.title("🖨️ Pusat Pelaporan & Cetakan")
    st.write("Sila pilih jenis cetakan laporan yang dikehendaki:")
    
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        pilihan_jenis_cetakan = st.radio(
            "Pilih Format Laporan Cetakan:",
            ["1. Markah Audit (Format Ringkas)", "2. Laporan Penilaian Audit (Format Penuh)"],
            horizontal=True
        )
    
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        nama_agensi = st.text_input("Nama Agensi / Kolej:", "KOLEJ KOMUNITI HULU LANGAT")
    with col_i2:
        tarikh_audit_cetak = st.date_input("Tarikh Audit:", datetime.date.today())
    
    zon_rasmi_list = ["ZON INDUK", "ZON EFEKTIF", "ZON KOMITED", "ZON SEPAKAT", "ZON AKTIF"]
    
    # DIKEMAS KINI: HANYA CAMPUR ITEM SAH SUPAYA KIRAAN TEPAT PER-100
    def kumpul_markah_zon(zon_nama, komp_nama):
        komp_upper = str(komp_nama).upper()
        is_komp_a_or_e = "KOMPONEN A" in komp_upper or "KOMPONEN E" in komp_upper
        
        if zon_nama == "ZON INDUK" and not is_komp_a_or_e:
            return 0, 0
            
        if zon_nama != "ZON INDUK" and is_komp_a_or_e:
            return 0, 0

        # Dapatkan item yang HANYA sah untuk zon ini
        item_sah = dapatkan_item_tapis(komp_nama, zon_nama)
        no_item_sah = [str(x['No']) for x in item_sah]

        total_m = 0
        if zon_nama in st.session_state.pangkalan_data:
            dict_zon = st.session_state.pangkalan_data[zon_nama]
            for nm_aud, data_aud in dict_zon.items():
                if komp_nama in data_aud:
                    for no_i, d_item in data_aud[komp_nama].items():
                        # HANYA kumpul markah sekiranya item tersebut belum di buang/dikecualikan
                        if str(no_i) in no_item_sah and isinstance(d_item, dict) and 'Markah' in d_item:
                            total_m += d_item['Markah']
        
        total_p = len(item_sah) * 5
        return total_m, total_p

    html_kandungan = ""
    css_tambahan = """
    <style>
    .header-induk { background-color: #e9d5ff !important; color: #000000 !important; }
    </style>
    """
    st.markdown(css_tambahan, unsafe_allow_html=True)

    if pilihan_jenis_cetakan == "1. Markah Audit (Format Ringkas)":
        html_kandungan = f"""
        <div style="text-align: center; margin-bottom: 20px; background-color: #ffffff; color: #000000;">
            <h3 style="margin: 0; font-family: Arial, sans-serif; color: #000000;">MARKAH AUDIT DALAM EKSA {tarikh_audit_cetak.year} {nama_agensi}</h3>
        </div>
        <table class="jadual-laporan">
            <thead>
                <tr>
                    <th class="header-kelabu" style="width: 5%;">BIL.</th>
                    <th class="header-kelabu" style="width: 40%;">KOMPONEN</th>
                    <th class="header-induk" style="width: 11%;">% MARKAH<br>ZON INDUK</th>
                    <th class="header-efektif" style="width: 11%;">% MARKAH<br>ZON EFEKTIF</th>
                    <th class="header-komited" style="width: 11%;">% MARKAH<br>ZON KOMITED</th>
                    <th class="header-sepakat" style="width: 11%;">% MARKAH<br>ZON SEPAKAT</th>
                    <th class="header-aktif" style="width: 11%;">% MARKAH<br>ZON AKTIF</th>
                </tr>
            </thead>
            <tbody>
        """
        senarai_komp_keys = ['KOMPONEN A', 'KOMPONEN B', 'KOMPONEN C', 'KOMPONEN D', 'KOMPONEN E']
        kod_huruf = ['A.', 'B.', 'C.', 'D.', 'E.']
        zon_total_m = {z: 0 for z in zon_rasmi_list}
        zon_total_p = {z: 0 for z in zon_rasmi_list}
        
        for idx, k_key in enumerate(senarai_komp_keys):
            nam_komp = [k for k in data_eksa.keys() if k_key in str(k).upper()]
            nam_komp_full = nam_komp[0] if nam_komp else k_key
            tajuk_bersih = nam_komp_full.replace("KOMPONEN A", "KEPERLUAN UTAMA PELAKSANAAN")\
                                       .replace("KOMPONEN B", "RUANG TEMPAT KERJA / PEJABAT")\
                                       .replace("KOMPONEN C", "TEMPAT UMUM")\
                                       .replace("KOMPONEN D", "BILIK PEMBELAJARAN & PENGAJARAN")\
                                       .replace("KOMPONEN E", "KESELAMATAN PERSEKITARAN")
            
            html_kandungan += f"<tr><td><b>{kod_huruf[idx]}</b></td><td style='text-align: left;'><b>{tajuk_bersih}</b></td>"
            for z_nam in zon_rasmi_list:
                m_dapat, m_penuh = kumpul_markah_zon(z_nam, nam_komp_full)
                zon_total_m[z_nam] += m_dapat
                zon_total_p[z_nam] += m_penuh
                if m_penuh > 0:
                    pct = (m_dapat / m_penuh) * 100
                    html_kandungan += f"<td><b>{pct:.2f}%</b></td>"
                else:
                    html_kandungan += f"<td><span style='color:#aaaaaa'>-</span></td>"
            html_kandungan += "</tr>"
            
        html_kandungan += "<tr><td colspan='2' class='header-kelabu'><b>PERATUS MARKAH ZON</b></td>"
        grand_m = 0
        grand_p = 0
        for z_nam in zon_rasmi_list:
            if zon_total_p[z_nam] > 0:
                z_pct = (zon_total_m[z_nam] / zon_total_p[z_nam]) * 100
                html_kandungan += f"<td><b>{z_pct:.2f}%</b></td>"
            else:
                html_kandungan += f"<td><b>-</b></td>"
            grand_m += zon_total_m[z_nam]
            grand_p += zon_total_p[z_nam]
        html_kandungan += "</tr>"
        
        grand_pct = (grand_m / grand_p * 100) if grand_p > 0 else 0.0
        html_kandungan += f"""
            <tr>
                <td colspan='2' class='header-kelabu'><b>PERATUS MARKAH KESELURUHAN</b></td>
                <td colspan='5' style='font-size: 16px;'><b>{grand_pct:.2f}%</b></td>
            </tr>
            </tbody>
        </table>
        """

    elif pilihan_jenis_cetakan == "2. Laporan Penilaian Audit (Format Penuh)":
        html_kandungan = f"""
        <div style="text-align: center; margin-bottom: 10px; background-color: #ffffff; color: #000000;">
            <h3 style="margin: 0; font-family: Arial, sans-serif; color: #000000;">LAPORAN PENILAIAN AUDIT EKSA {tarikh_audit_cetak.year} {nama_agensi}</h3>
        </div>
        <p style="font-family: Arial, sans-serif; color: #000000;"><b>TARIKH AUDIT:</b> {tarikh_audit_cetak.strftime('%d %B %Y').upper()}</p>
        <table class="jadual-laporan">
            <thead>
                <tr>
                    <th rowspan="2" class="header-kelabu" style="width: 4%;">BIL.</th>
                    <th rowspan="2" class="header-kelabu" style="width: 26%;">KOMPONEN</th>
                    <th colspan="2" class="header-induk">ZON INDUK</th>
                    <th colspan="2" class="header-efektif">ZON EFEKTIF</th>
                    <th colspan="2" class="header-komited">ZON KOMITED</th>
                    <th colspan="2" class="header-sepakat">ZON SEPAKAT</th>
                    <th colspan="2" class="header-aktif">ZON AKTIF</th>
                </tr>
                <tr>
                    <th class="header-induk">PENUH</th>
                    <th class="header-induk">MARKAH</th>
                    <th class="header-efektif">PENUH</th>
                    <th class="header-efektif">MARKAH</th>
                    <th class="header-komited">PENUH</th>
                    <th class="header-komited">MARKAH</th>
                    <th class="header-sepakat">PENUH</th>
                    <th class="header-sepakat">MARKAH</th>
                    <th class="header-aktif">PENUH</th>
                    <th class="header-aktif">MARKAH</th>
                </tr>
            </thead>
            <tbody>
        """
        senarai_komp_keys = ['KOMPONEN A', 'KOMPONEN B', 'KOMPONEN C', 'KOMPONEN D', 'KOMPONEN E']
        kod_huruf = ['A.', 'B.', 'C.', 'D.', 'E.']
        zon_total_m = {z: 0 for z in zon_rasmi_list}
        zon_total_p = {z: 0 for z in zon_rasmi_list}
        
        for idx, k_key in enumerate(senarai_komp_keys):
            nam_komp = [k for k in data_eksa.keys() if k_key in str(k).upper()]
            nam_komp_full = nam_komp[0] if nam_komp else k_key
            tajuk_bersih = nam_komp_full.replace("KOMPONEN A", "KEPERLUAN UTAMA PELAKSANAAN")\
                                       .replace("KOMPONEN B", "RUANG TEMPAT KERJA / PEJABAT")\
                                       .replace("KOMPONEN C", "TEMPAT UMUM")\
                                       .replace("KOMPONEN D", "BILIK PEMBELAJARAN & PENGAJARAN")\
                                       .replace("KOMPONEN E", "KESELAMATAN PERSEKITARAN")
            
            html_kandungan += f"<tr><td><b>{kod_huruf[idx]}</b></td><td style='text-align: left;'><b>{tajuk_bersih}</b></td>"
            for z_nam in zon_rasmi_list:
                m_dapat, m_penuh = kumpul_markah_zon(z_nam, nam_komp_full)
                zon_total_m[z_nam] += m_dapat
                zon_total_p[z_nam] += m_penuh
                
                txt_p = str(m_penuh) if m_penuh > 0 else "<span style='color:#aaaaaa'>-</span>"
                txt_m = f"<b>{m_dapat}</b>" if m_penuh > 0 else "<span style='color:#aaaaaa'>-</span>"
                html_kandungan += f"<td>{txt_p}</td><td>{txt_m}</td>"
            html_kandungan += "</tr>"
            
        html_kandungan += "<tr><td colspan='2' class='header-kelabu'><b>JUMLAH MARKAH</b></td>"
        grand_m = 0
        grand_p = 0
        for z_nam in zon_rasmi_list:
            txt_jp = f"<b>{zon_total_p[z_nam]}</b>" if zon_total_p[z_nam] > 0 else "-"
            txt_jm = f"<b>{zon_total_m[z_nam]}</b>" if zon_total_p[z_nam] > 0 else "-"
            html_kandungan += f"<td>{txt_jp}</td><td>{txt_jm}</td>"
            grand_m += zon_total_m[z_nam]
            grand_p += zon_total_p[z_nam]
        html_kandungan += "</tr>"
        
        html_kandungan += "<tr><td colspan='2' class='header-kelabu'><b>PERATUS MARKAH ZON</b></td>"
        for z_nam in zon_rasmi_list:
            if zon_total_p[z_nam] > 0:
                z_pct = (zon_total_m[z_nam] / zon_total_p[z_nam]) * 100
                html_kandungan += f"<td colspan='2'><b>{z_pct:.2f}%</b></td>"
            else:
                html_kandungan += f"<td colspan='2'><b>-</b></td>"
        html_kandungan += "</tr>"
        
        grand_pct = (grand_m / grand_p * 100) if grand_p > 0 else 0.0
        html_kandungan += f"""
            <tr>
                <td colspan='2' class='header-kelabu'><b>PERATUS MARKAH KESELURUHAN</b></td>
                <td colspan='10' style='font-size: 16px;'><b>{grand_pct:.2f}%</b></td>
            </tr>
            </tbody>
        </table>
        <br><br>
        <div style="display: flex; justify-content: space-between; font-family: Arial, sans-serif; color: #000000; background-color: #ffffff;">
            <div>
                <b>PENGESAHAN KETUA JURUAUDIT</b><br><br><br>
                TANDATANGAN: ___________________________<br>
                NAMA : MAZWINA HANIM BINTI ABU BAKAR<br>
                TARIKH: ________________________________
            </div>
            <div>
                <b>PENGESAHAN WAKIL PENGURUSAN</b><br><br><br>
                TANDATANGAN: ___________________________<br>
                NAMA : _________________________________<br>
                TARIKH: ________________________________
            </div>
        </div>
        """

    components.html(
        f"""
        <script>
        function cetakLaporanIsolasi() {{
            var kandungan = `{html_kandungan}`;
            var mywindow = window.open('', 'PRINT', 'height=800,width=1000');
            mywindow.document.write('<html><head><title>Laporan Audit EKSA</title>');
            mywindow.document.write('<style>');
            mywindow.document.write('body {{ background-color: #ffffff !important; color: #000000 !important; font-family: Arial, sans-serif; padding: 20px; }}');
            mywindow.document.write('.jadual-laporan {{ width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 13px; text-align: center; margin-top: 10px; background-color: #ffffff !important; color: #000000 !important; }}');
            mywindow.document.write('.jadual-laporan th, .jadual-laporan td {{ border: 1.5px solid #000000 !important; padding: 6px 8px; color: #000000 !important; background-color: #ffffff; }}');
            mywindow.document.write('.header-induk {{ background-color: #e9d5ff !important; color: #000000 !important; }}');
            mywindow.document.write('.header-efektif {{ background-color: #fef3c7 !important; color: #000000 !important; }}');
            mywindow.document.write('.header-komited {{ background-color: #bfdbfe !important; color: #000000 !important; }}');
            mywindow.document.write('.header-sepakat {{ background-color: #fca5a5 !important; color: #000000 !important; }}');
            mywindow.document.write('.header-aktif {{ background-color: #bbf7d0 !important; color: #000000 !important; }}');
            mywindow.document.write('.header-kelabu {{ background-color: #e5e7eb !important; color: #000000 !important; }}');
            mywindow.document.write('</style></head><body>');
            mywindow.document.write(kandungan);
            mywindow.document.write('</body></html>');
            mywindow.document.close();
            mywindow.focus();
            setTimeout(function() {{
                mywindow.print();
                mywindow.close();
            }}, 500);
            return true;
        }}
        </script>
        <button onclick="cetakLaporanIsolasi()" style="
            background-color: #007BFF;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        ">
            🖨️ Cetak / Simpan Laporan Sebagai PDF
        </button>
        """,
        height=65
    ) 
    st.markdown("---")
    st.markdown(f"<div class='jadual-laporan-wrapper'>{html_kandungan}</div>", unsafe_allow_html=True)
