import base64
import datetime
import io
import os
import re
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SISTEM AUDIT EKSA", page_icon="📝", layout="wide")

# PAUTAN GOOGLE SHEETS ANDA
URL_GSHEETS = "https://docs.google.com/spreadsheets/d/1VZzjHycnRV_vOKNld5YSumf9rpOB3FOInjWlpF5qgZA/edit?usp=sharing"

# --- 2. PENGURUSAN PANGKALAN DATA (SESSION & GOOGLE SHEETS) ---
if "pangkalan_data" not in st.session_state:
    st.session_state.pangkalan_data = {}

if "data_disegerakkan" not in st.session_state:
    st.session_state.data_disegerakkan = False

# Panggilan Sambungan GSheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
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


# --- 3. FUNGSI BACAAN EXCEL DUKUNGAN PENUH EXCEL ---
@st.cache_data
def muat_data_eksa(file_path):
    xls = pd.ExcelFile(file_path)
    data_komponen = {}

    valid_sheets = [
        s for s in xls.sheet_names if str(s).upper().startswith("KOMPONEN")
    ]

    for sheet in valid_sheets:
        df = pd.read_excel(file_path, sheet_name=sheet)
        item_list = []
        current_subtopic = "KRITERIA UMUM"

        for index, row in df.iterrows():
            for col_idx in range(len(row)):
                val = row.iloc[col_idx]
                if pd.notna(val) and isinstance(val, str) and re.match(r"^[A-Z]\d+\)", str(val).strip()):
                    current_subtopic = str(val).strip()
                    break

            no_item = None
            perkara = None
            rubrik = {}

            for col_idx in range(len(row) - 1):
                val = row.iloc[col_idx]
                if pd.notna(val) and len(str(val).strip()) > 0:
                    val_str = str(val).strip()
                    if re.match(r"^\d+$", val_str) and int(val_str) < 100:
                        next_val = row.iloc[col_idx + 1]
                        if (
                            pd.notna(next_val)
                            and isinstance(next_val, str)
                            and len(next_val.strip()) > 3
                            and "ZON" not in next_val.upper()
                            and "MARKAH" not in next_val.upper()
                        ):
                            no_item = val_str
                            perkara = str(next_val).strip()

                            for i in range(1, 6):
                                rub_col = col_idx + 1 + i
                                if rub_col < len(row):
                                    r_val = row.iloc[rub_col]
                                    if pd.notna(r_val):
                                        r_str = str(r_val).strip()
                                        rubrik[i] = r_str if r_str.lower() != "nan" else ""
                                    else:
                                        rubrik[i] = ""
                                else:
                                    rubrik[i] = ""
                            break

            if no_item and perkara:
                item_list.append(
                    {
                        "Subtopik": current_subtopic,
                        "No": str(no_item),
                        "Perkara": perkara,
                        "Rubrik": rubrik,
                    }
                )

        if item_list:
            data_komponen[sheet] = item_list

    return data_komponen


fail_excel = "MARKAH AUDIT EKSA.xlsx"
try:
    data_eksa = muat_data_eksa(fail_excel)
except Exception:
    st.error(
        f"Gagal membaca fail Excel. Pastikan fail '{fail_excel}' wujud di dalam folder ini."
    )
    st.stop()


# Fungsi Membaca Data Sedia Ada Dari Google Sheets
def senkron_data_dari_gsheets():
    if conn is not None:
        try:
            df_existing = conn.read(spreadsheet=URL_GSHEETS, ttl=0)
            if not df_existing.empty:
                st.session_state.pangkalan_data = {}  # Bersihkan data tempatan sebelum muat semula
                for _, row in df_existing.iterrows():
                    z = str(row["Zon"]).strip().upper()
                    j = str(row["Juruaudit"]).strip()
                    
                    k_raw = str(row["Komponen"]).strip().upper()
                    k = k_raw
                    for main_k in data_eksa.keys():
                        prefix_main = main_k.split(":")[0].strip().upper() if ":" in main_k else main_k.strip().upper()
                        if k_raw in main_k.upper() or main_k.upper() in k_raw or k_raw == prefix_main:
                            k = main_k
                            break

                    no_i = "".join(filter(str.isdigit, str(row["No_Item"])))

                    if z not in st.session_state.pangkalan_data:
                        st.session_state.pangkalan_data[z] = {}
                    if j not in st.session_state.pangkalan_data[z]:
                        st.session_state.pangkalan_data[z][j] = {}

                    st.session_state.pangkalan_data[z][j]["_lokasi_khusus"] = (
                        str(row["Lokasi"]) if pd.notna(row["Lokasi"]) else ""
                    )

                    if k not in st.session_state.pangkalan_data[z][j]:
                        st.session_state.pangkalan_data[z][j][k] = {}

                    senarai_gbr = []
                    for idx_g in range(1, 6):
                        col_name = f"Gambar_{idx_g}"
                        if col_name in row and pd.notna(row[col_name]):
                            senarai_gbr.append(str(row[col_name]))

                    raw_markah = row["Markah"]
                    if pd.notna(raw_markah) and str(raw_markah).isdigit():
                        markah_val = int(raw_markah)
                    else:
                        markah_val = None

                    st.session_state.pangkalan_data[z][j][k][no_i] = {
                        "Markah": markah_val,
                        "Ulasan": (
                            str(row["Ulasan"]) if pd.notna(row["Ulasan"]) else ""
                        ),
                        "Senarai_Gambar": senarai_gbr,
                        "Ulasan_Susulan": "",
                        "Gambar_Susulan": None,
                        "Tarikh_Susulan": datetime.date.today(),
                    }
                st.session_state.data_disegerakkan = True
                return True
        except Exception:
            pass
    return False


# Laksanakan segerak automatik pada kemasukan pertama
if not st.session_state.data_disegerakkan:
    senkron_data_dari_gsheets()

# --- CSS KHAS ---
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)


# --- FUNGSI PENAPISAN ITEM MENGIKUT ZON ---
def dapatkan_item_tapis(komponen, zon):
    komponen_upper = str(komponen).upper()
    zon_upper = str(zon).upper()
    item_dikecualikan = []

    if "KOMPONEN B" in komponen_upper:
        if "ZON EFEKTIF" in zon_upper:
            item_dikecualikan = ["39", "40", "41", "42", "43", "44", "45", "46", "49", "50", "51"]
        elif "ZON KOMITED" in zon_upper:
            item_dikecualikan = ["32", "33", "34", "35", "36", "37", "38", "47", "48", "52", "53"]
        elif "ZON SEPAKAT" in zon_upper:
            item_dikecualikan = ["32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53"]
        elif "ZON AKTIF" in zon_upper:
            item_dikecualikan = ["32", "33", "34", "35", "36", "37", "38", "45", "46", "47", "48", "49", "50", "51", "52", "53"]

    elif "KOMPONEN C" in komponen_upper:
        if "ZON EFEKTIF" in zon_upper:
            item_dikecualikan = ["14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]
        elif "ZON KOMITED" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "16", "17", "18", "19", "20", "21", "22", "23"]
        elif "ZON SEPAKAT" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "14", "15", "24", "25"]
        elif "ZON AKTIF" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]

    elif "KOMPONEN D" in komponen_upper:
        if "ZON EFEKTIF" in zon_upper:
            item_dikecualikan = ["5", "6", "7", "8", "9", "10"]
        elif "ZON KOMITED" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "4", "5", "6", "9", "10", "11", "12"]
        elif "ZON SEPAKAT" in zon_upper:
            item_dikecualikan = ["1", "2", "9", "10", "11", "12"]
        elif "ZON AKTIF" in zon_upper:
            item_dikecualikan = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

    items_asal = data_eksa.get(komponen, [])
    filtered_items = []

    for item in items_asal:
        num_only = "".join(filter(str.isdigit, str(item["No"])))
        if num_only not in item_dikecualikan:
            filtered_items.append(item)

    return filtered_items


# --- FUNGSI KIRA PRESTASI ---
def kira_prestasi(data_individu, zon, filter_komp="Semua Komponen"):
    ringkasan_markah = {}
    total_markah_semua = 0
    total_penuh_semua = 0

    komponen_dipilih = (
        data_eksa.keys() if filter_komp == "Semua Komponen" else [filter_komp]
    )

    for komp in komponen_dipilih:
        rekod_komponen = {}
        komp_code = komp.split(":")[0].strip().upper() if ":" in komp else komp.strip().upper()
        
        for k_entry, v_entry in data_individu.items():
            k_entry_code = k_entry.split(":")[0].strip().upper() if ":" in k_entry else k_entry.strip().upper()
            if komp_code == k_entry_code:
                rekod_komponen = v_entry
                break

        items_komp = dapatkan_item_tapis(komp, zon)

        jumlah_markah = 0
        jumlah_item_dinilai = 0

        if rekod_komponen:
            for item in items_komp:
                no_dig = "".join(filter(str.isdigit, str(item["No"])))
                match_key = None
                for k_i in rekod_komponen.keys():
                    if "".join(filter(str.isdigit, str(k_i))) == no_dig:
                        match_key = k_i
                        break

                if match_key:
                    val = rekod_komponen[match_key]
                    if isinstance(val, dict):
                        m_val = val.get("Markah")
                        if m_val is not None and str(m_val).isdigit():
                            jumlah_markah += int(m_val)
                            jumlah_item_dinilai += 1

        markah_penuh = jumlah_item_dinilai * 5

        peratusan = (
            (jumlah_markah / markah_penuh) * 100 if markah_penuh > 0 else 0
        )
        if markah_penuh > 0:
            ringkasan_markah[komp] = peratusan

        total_markah_semua += jumlah_markah
        total_penuh_semua += markah_penuh

    peratusan_keseluruhan = (
        (total_markah_semua / total_penuh_semua) * 100
        if total_penuh_semua > 0
        else 0
    )
    return (
        ringkasan_markah,
        total_markah_semua,
        total_penuh_semua,
        peratusan_keseluruhan,
    )

# --- 4. SIDEBAR LOGO & KAWALAN ---
fail_logo = None
for nm in ["logo.png", "Logo.png", "LOGO.PNG", "logo.PNG", "logo.jpeg", "logo.jpg"]:
    if os.path.exists(nm):
        fail_logo = nm
        break

if fail_logo:
    st.sidebar.image(fail_logo, use_container_width=True)

st.sidebar.title("SISTEM AUDIT EKSA")

# Butang Muat Semula Data Manual
if st.sidebar.button("🔄 Muat Semula Data dari GSheets"):
    if senkron_data_dari_gsheets():
        st.sidebar.success("Data berjaya dikemas kini!")
        st.rerun()
    else:
        st.sidebar.error("Gagal menyemak data dari GSheets.")

st.sidebar.markdown("---")
st.sidebar.header("Navigasi Sistem")
menu_paparan = st.sidebar.radio(
    "Sila pilih menu paparan:",
    [
        "📋 Modul Kerja (Borang)",
        "📊 Markah Audit",
        "📈 Rumusan Markah Terperinci",
        "🖨️ Laporan Penuh & Cetakan",
    ],
)

# [Bahagian selebihnya kekal sama seperti kod asal anda...]
