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
            # Cari tajuk subtopik (contoh: A1) DASAR EKSA, B1) LANTAI, dll.)
            for col_idx in range(len(row)):
                val = row.iloc[col_idx]
                if pd.notna(val) and isinstance(val, str) and re.match(r"^[A-Z]\d+\)", str(val).strip()):
                    current_subtopic = str(val).strip()
                    break

            no_item = None
            perkara = None
            rubrik = {}

            # Cari nombor item dan perkara
            for col_idx in range(len(row) - 1):
                val = row.iloc[col_idx]
                if pd.notna(val) and len(str(val).strip()) > 0:
                    val_str = str(val).strip()
                    # Pastikan nombor item nombor bulat dan elakkan baris tajuk 'ZON' / 'MARKAH'
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

                            # Ekstrak Rubrik 1 hingga 5
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
                        markah_val = "-"

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
        except Exception:
            pass


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


# --- FUNGSI PENAPISAN ITEM MENGIKUT ZON (BERDASARKAN EXCEL SEBENAR) ---
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
                        if str(m_val).isdigit():
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

# --- 4. SIDEBAR LOGO ---
fail_logo = None
for nm in ["logo.png", "Logo.png", "LOGO.PNG", "logo.PNG", "logo.jpeg", "logo.jpg"]:
    if os.path.exists(nm):
        fail_logo = nm
        break

if fail_logo:
    st.sidebar.image(fail_logo, use_container_width=True)

st.sidebar.title("SISTEM AUDIT EKSA")
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


# ==========================================
# PAPARAN 1: BORANG PENILAIAN (MODUL KERJA)
# ==========================================
if menu_paparan == "📋 Modul Kerja (Borang)":

    st.title("Borang Penilaian EKSA")
    st.write(
        "Sila lengkapkan maklumat audit dan pilih komponen yang ingin dinilai."
    )

    col_info1, col_info2, col_info3, col_info4 = st.columns([1, 1, 1.2, 1])
    with col_info1:
        komponen_pilihan = st.selectbox(
            "1. Pilih Komponen:", list(data_eksa.keys())
        )
    with col_info2:
        komponen_upper = str(komponen_pilihan).upper()
        if "KOMPONEN A" in komponen_upper or "KOMPONEN E" in komponen_upper:
            pilihan_zon_rasmi = ["ZON INDUK", "ZON LAIN-LAIN..."]
        else:
            pilihan_zon_rasmi = [
                "ZON EFEKTIF",
                "ZON KOMITED",
                "ZON SEPAKAT",
                "ZON AKTIF",
                "ZON LAIN-LAIN...",
            ]

        lokasi_audit_sel = st.selectbox("2. Pilih Zon:", pilihan_zon_rasmi)

        if lokasi_audit_sel == "ZON LAIN-LAIN...":
            zon_audit = st.text_input("Nama Zon Manual:").strip().upper()
        else:
            zon_audit = lokasi_audit_sel
    with col_info3:
        lokasi_khusus = st.text_input(
            "3. Lokasi Di-Audit (Manual):", "Bilik Mesyuarat Utama / Aras 2"
        ).strip()
    with col_info4:
        nama_juruaudit = st.text_input("4. Nama Juruaudit:", "Juruaudit 1").strip()

    st.markdown("---")

    if zon_audit and nama_juruaudit:
        if zon_audit not in st.session_state.pangkalan_data:
            st.session_state.pangkalan_data[zon_audit] = {}
        if nama_juruaudit not in st.session_state.pangkalan_data[zon_audit]:
            st.session_state.pangkalan_data[zon_audit][nama_juruaudit] = {}

        data_semasa = st.session_state.pangkalan_data[zon_audit][nama_juruaudit]
        data_semasa["_lokasi_khusus"] = lokasi_khusus

        st.subheader(f"Menilai: {komponen_pilihan}")
        st.caption(
            f"**Zon:** {zon_audit} | **Lokasi:** {lokasi_khusus} | **Juruaudit:** {nama_juruaudit}"
        )

        items = dapatkan_item_tapis(komponen_pilihan, zon_audit)

        if komponen_pilihan not in data_semasa:
            data_semasa[komponen_pilihan] = {}

        if not items:
            st.info("Tiada item dijumpai bagi komponen ini pada zon yang dipilih.")
        else:
            with st.form(key=f"form_{komponen_pilihan}_{zon_audit}_{nama_juruaudit}"):
                current_displayed_subtopic = ""

                for item in items:
                    item_no_str = str(item["No"]).strip()
                    item_dig = "".join(filter(str.isdigit, item_no_str))

                    if item["Subtopik"] != current_displayed_subtopic:
                        st.markdown(
                            f"<h3 style='color: #007BFF; margin-top: 30px;'>📑 {item['Subtopik']}</h3>",
                            unsafe_allow_html=True,
                        )
                        current_displayed_subtopic = item["Subtopik"]

                    st.markdown(f"**Item {item_no_str}: {item['Perkara']}**")

                    with st.expander(
                        f"Lihat Rubrik Pemarkahan untuk Item {item_no_str}"
                    ):
                        for skor, deskripsi in item["Rubrik"].items():
                            if deskripsi and deskripsi != "nan":
                                st.write(f"**Skor {skor}:** {deskripsi}")

                    rekod_lama = data_semasa[komponen_pilihan].get(
                        item_no_str,
                        data_semasa[komponen_pilihan].get(
                            item_dig,
                            {
                                "Markah": 5,
                                "Ulasan": "",
                                "Senarai_Gambar": [],
                                "Ulasan_Susulan": "",
                                "Gambar_Susulan": None,
                                "Tarikh_Susulan": datetime.date.today(),
                            },
                        ),
                    )

                    col1, col2, col3 = st.columns([1.2, 1.4, 1.4])
                    with col1:
                        pilihan_markah = [1, 2, 3, 4, 5]
                        val_lama = rekod_lama["Markah"]
                        if str(val_lama).isdigit():
                            val_lama = int(val_lama)
                        idx_default = pilihan_markah.index(val_lama) if val_lama in pilihan_markah else 4

                        markah = st.radio(
                            "Markah",
                            options=pilihan_markah,
                            index=idx_default,
                            horizontal=True,
                            key=f"mark_{zon_audit}_{komponen_pilihan}_{item_no_str}",
                        )
                    with col2:
                        ulasan = st.text_input(
                            "Ulasan/Komen Asal",
                            value=rekod_lama["Ulasan"],
                            key=f"ulasan_{zon_audit}_{komponen_pilihan}_{item_no_str}",
                        )
                    with col3:
                        gambar_muat_naik_list = st.file_uploader(
                            "Muat Naik Bukti (Maksima 5 Gambar)",
                            type=["png", "jpg", "jpeg"],
                            accept_multiple_files=True,
                            key=f"gambar_{zon_audit}_{komponen_pilihan}_{item_no_str}",
                        )

                        gambar_disimpan_list = rekod_lama.get("Senarai_Gambar", [])

                        if gambar_muat_naik_list:
                            if len(gambar_muat_naik_list) > 5:
                                st.warning("⚠️ Hanya 5 gambar pertama akan disimpan.")
                                gambar_muat_naik_list = gambar_muat_naik_list[:5]

                            gambar_disimpan_list = []
                            for g_file in gambar_muat_naik_list:
                                b64_res = gambar_ke_base64(g_file)
                                if b64_res:
                                    gambar_disimpan_list.append(b64_res)

                        if gambar_disimpan_list:
                            st.write("Gambar Dimuat Naik:")
                            cols_g = st.columns(min(len(gambar_disimpan_list), 5))
                            for idx_img, img_b64 in enumerate(gambar_disimpan_list):
                                with cols_g[idx_img]:
                                    st.image(img_b64, use_container_width=True)

                    data_semasa[komponen_pilihan][item_no_str] = {
                        "Markah": markah,
                        "Ulasan": ulasan,
                        "Senarai_Gambar": gambar_disimpan_list,
                        "Ulasan_Susulan": rekod_lama.get("Ulasan_Susulan", ""),
                        "Gambar_Susulan": rekod_lama.get("Gambar_Susulan", None),
                        "Tarikh_Susulan": rekod_lama.get(
                            "Tarikh_Susulan", datetime.date.today()
                        ),
                    }
                    st.markdown("---")

                hantar = st.form_submit_button("Simpan Markah & Gambar")

                if hantar:
                    st.session_state.pangkalan_data[zon_audit][
                        nama_juruaudit
                    ] = data_semasa

                    if conn is not None:
                        try:
                            baris_baru = []
                            tarikh_sekarang = datetime.date.today().strftime(
                                "%Y-%m-%d"
                            )

                            for no_i, d_item in data_semasa[
                                komponen_pilihan
                            ].items():
                                padanan = [
                                    orig
                                    for orig in data_eksa.get(
                                        komponen_pilihan, []
                                    )
                                    if str(orig["No"]).strip()
                                    == str(no_i).strip()
                                ]
                                subtopik_val = (
                                    padanan[0]["Subtopik"]
                                    if padanan
                                    else "KRITERIA UMUM"
                                )

                                g_list = d_item.get("Senarai_Gambar", [])
                                g1 = g_list[0] if len(g_list) > 0 else ""
                                g2 = g_list[1] if len(g_list) > 1 else ""
                                g3 = g_list[2] if len(g_list) > 2 else ""
                                g4 = g_list[3] if len(g_list) > 3 else ""
                                g5 = g_list[4] if len(g_list) > 4 else ""

                                baris_baru.append(
                                    {
                                        "Tarikh": tarikh_sekarang,
                                        "Zon": zon_audit,
                                        "Lokasi": lokasi_khusus,
                                        "Juruaudit": nama_juruaudit,
                                        "Komponen": komponen_pilihan,
                                        "Subtopik": subtopik_val,
                                        "No_Item": str(no_i),
                                        "Markah": str(d_item["Markah"]),
                                        "Ulasan": d_item["Ulasan"],
                                        "Gambar_1": g1,
                                        "Gambar_2": g2,
                                        "Gambar_3": g3,
                                        "Gambar_4": g4,
                                        "Gambar_5": g5,
                                    }
                                )

                            df_baru = pd.DataFrame(baris_baru)
                            try:
                                df_lama = conn.read(
                                    spreadsheet=URL_GSHEETS, ttl=0
                                )
                                df_gabung = pd.concat(
                                    [df_lama, df_baru], ignore_index=True
                                )
                            except Exception:
                                df_gabung = df_baru

                            conn.update(
                                spreadsheet=URL_GSHEETS, data=df_gabung
                            )
                            st.success(
                                "✅ Data dan gambar berjaya disimpan ke Google Sheets!"
                            )
                        except Exception as err:
                            st.error(f"Gagal berhubung ke Google Sheets: {err}")
                    else:
                        st.warning(
                            "Sambungan Google Sheets gagal dibuka. Pastikan secrets.toml telah dikonfigurasi."
                        )
    else:
        st.warning(
            "Sila pastikan Zon dan Nama Juruaudit telah diisi untuk memulakan penilaian."
        )

# ==========================================
# PAPARAN 2: MARKAH AUDIT (DENGAN EDIT & DELETE)
# ==========================================
elif menu_paparan == "📊 Markah Audit":

    st.title("📊 Papan Markah Audit EKSA")
    st.write(
        "Paparan analisis interaktif berdasarkan Komponen, Zon, Lokasi, dan Juruaudit."
    )
    st.markdown("---")

    senarai_zon = list(st.session_state.pangkalan_data.keys())

    if not senarai_zon:
        st.warning("Belum ada sebarang data audit yang direkodkan dalam sistem ini.")
    else:
        col_m1, col_m2, col_m3 = st.columns(3)

        with col_m1:
            pilih_komponen = st.selectbox(
                "1. Pilih Komponen:",
                ["Semua Komponen"] + list(data_eksa.keys()),
                key="m_komp",
            )

        with col_m2:
            pilih_zon = st.selectbox(
                "2. Pilih Zon:", ["Semua Zon"] + senarai_zon, key="m_zon"
            )

        if pilih_zon == "Semua Zon":
            senarai_auditor_raw = []
            for z in senarai_zon:
                senarai_auditor_raw.extend(
                    list(st.session_state.pangkalan_data[z].keys())
                )
            senarai_auditor = list(set(senarai_auditor_raw))
        else:
            senarai_auditor = list(
                st.session_state.pangkalan_data[pilih_zon].keys()
            )

        with col_m3:
            pilih_auditor = st.selectbox(
                "3. Pilih Juruaudit:",
                ["Semua Juruaudit"] + senarai_auditor,
                key="m_auditor",
            )

        st.markdown("---")

        zon_sasaran = senarai_zon if pilih_zon == "Semua Zon" else [pilih_zon]

        st.subheader("📊 Prestasi Pencapaian Markah")

        data_graf = []
        for zon in zon_sasaran:
            dict_zon = st.session_state.pangkalan_data[zon]
            auditor_sasaran = (
                list(dict_zon.keys())
                if pilih_auditor == "Semua Juruaudit"
                else ([pilih_auditor] if pilih_auditor in dict_zon else [])
            )

            for nm_auditor in auditor_sasaran:
                ringkasan, jum_markah, jum_penuh, peratus = kira_prestasi(
                    dict_zon[nm_auditor], zon, pilih_komponen
                )
                lok_khusus = dict_zon[nm_auditor].get("_lokasi_khusus", "Biasa")
                if jum_penuh > 0:
                    data_graf.append(
                        {
                            "Zon": zon,
                            "Lokasi": lok_khusus,
                            "Nama Juruaudit": nm_auditor,
                            "Markah Dinilai": jum_markah,
                            "Markah Penuh": jum_penuh,
                            "Peratusan (%)": round(peratus, 2),
                        }
                    )

        if (
            len(data_graf) > 1
            or pilih_zon == "Semua Zon"
            or pilih_auditor == "Semua Juruaudit"
        ):
            df_graf = pd.DataFrame(data_graf)
            if not df_graf.empty:
                fig = px.bar(
                    df_graf,
                    x="Zon",
                    y="Markah Dinilai",
                    color="Nama Juruaudit",
                    barmode="group",
                    hover_data={
                        "Lokasi": True,
                        "Peratusan (%)": True,
                        "Markah Penuh": True,
                    },
                    text="Peratusan (%)",
                )
                fig.update_traces(
                    texttemplate="%{text}%", textposition="outside"
                )
                fig.update_layout(
                    xaxis_title="Zon Audit", yaxis_title="Markah Dinilai"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Tiada data markah direkodkan untuk tapisan ini.")

        elif len(data_graf) == 1:
            st.metric(
                f"Markah Diberikan oleh {data_graf[0]['Nama Juruaudit']} bagi {data_graf[0]['Zon']} ({data_graf[0]['Lokasi']})",
                f"{data_graf[0]['Markah Dinilai']} / {data_graf[0]['Markah Penuh']} ({data_graf[0]['Peratusan (%)']}%)",
            )

        st.markdown("---")

        senarai_komp_laporan = (
            list(data_eksa.keys())
            if pilih_komponen == "Semua Komponen"
            else [pilih_komponen]
        )

        st.subheader("📝 Pengurusan & Suntingan Rekod Audit")

        ada_rekod = False
        for zon in zon_sasaran:
            dict_zon_terpilih = st.session_state.pangkalan_data[zon]
            senarai_auditor_laporan = (
                list(dict_zon_terpilih.keys())
                if pilih_auditor == "Semua Juruaudit"
                else (
                    [pilih_auditor] if pilih_auditor in dict_zon_terpilih else []
                )
            )

            for nm_auditor in senarai_auditor_laporan:
                rekod_auditor = dict_zon_terpilih[nm_auditor]
                lok_khusus = rekod_auditor.get("_lokasi_khusus", "Biasa")

                for komp in senarai_komp_laporan:
                    rekod_komp = {}
                    komp_code = komp.split(":")[0].strip().upper() if ":" in komp else komp.strip().upper()
                    
                    for k_entry, v_entry in rekod_auditor.items():
                        k_entry_code = k_entry.split(":")[0].strip().upper() if ":" in k_entry else k_entry.strip().upper()
                        if komp_code == k_entry_code:
                            rekod_komp = v_entry
                            break

                    item_sah_zon = dapatkan_item_tapis(komp, zon)
                    no_item_sah_zon = [
                        "".join(filter(str.isdigit, str(x["No"])))
                        for x in item_sah_zon
                    ]

                    for no_item, data in list(rekod_komp.items()):
                        no_item_str = str(no_item).strip()
                        no_item_dig = "".join(filter(str.isdigit, no_item_str))
                        if no_item_dig not in no_item_sah_zon:
                            continue

                        if isinstance(data, dict):
                            ada_rekod = True
                            padanan_item = [
                                orig
                                for orig in data_eksa.get(komp, [])
                                if "".join(filter(str.isdigit, str(orig["No"])))
                                == no_item_dig
                            ]
                            perkara_txt = (
                                padanan_item[0]["Perkara"]
                                if padanan_item
                                else f"Item {no_item_str}"
                            )

                            with st.expander(
                                f"📌 [{zon} - {lok_khusus}] {komp} - Item {no_item_str}: {perkara_txt} (Markah: {data['Markah']}/5)"
                            ):
                                c_info, c_edit, c_del = st.columns([3, 1, 1])

                                with c_info:
                                    st.write(f"**Juruaudit:** {nm_auditor}")
                                    st.write(
                                        f"**Ulasan:** {data['Ulasan'] if data['Ulasan'] else '*Tiada*'}"
                                    )
                                    gbr_list_view = data.get("Senarai_Gambar", [])
                                    if gbr_list_view:
                                        cols_view = st.columns(min(len(gbr_list_view), 5))
                                        for idx_v, img_v in enumerate(gbr_list_view):
                                            with cols_view[idx_v]:
                                                st.image(
                                                    img_v,
                                                    caption=f"Gambar {idx_v+1}",
                                                    use_container_width=True,
                                                )

                                # BUTANG SUNTING (EDIT)
                                with c_edit:
                                    with st.popover("✏️ Edit"):
                                        st.markdown(f"**Edit Item {no_item_str}**")

                                        pilihan_edit = [1, 2, 3, 4, 5]
                                        val_m = data.get("Markah", 5)
                                        if str(val_m).isdigit():
                                            val_m = int(val_m)
                                        idx_m = pilihan_edit.index(val_m) if val_m in pilihan_edit else 4

                                        markah_baru = st.radio(
                                            "Markah Baharu",
                                            pilihan_edit,
                                            index=idx_m,
                                            horizontal=True,
                                            key=f"edit_m_{zon}_{nm_auditor}_{komp}_{no_item_str}",
                                        )
                                        ulasan_baru = st.text_input(
                                            "Ulasan Baharu",
                                            value=data["Ulasan"],
                                            key=f"edit_u_{zon}_{nm_auditor}_{komp}_{no_item_str}",
                                        )
                                        gambar_baru_list = st.file_uploader(
                                            "Tukar Gambar (Max 5)",
                                            type=["png", "jpg", "jpeg"],
                                            accept_multiple_files=True,
                                            key=f"edit_g_{zon}_{nm_auditor}_{komp}_{no_item_str}",
                                        )

                                        if st.button(
                                            "💾 Simpan Kemas Kini",
                                            key=f"btn_save_{zon}_{nm_auditor}_{komp}_{no_item_str}",
                                        ):
                                            st.session_state.pangkalan_data[zon][
                                                nm_auditor
                                            ][komp][no_item_str][
                                                "Markah"
                                            ] = markah_baru
                                            st.session_state.pangkalan_data[zon][
                                                nm_auditor
                                            ][komp][no_item_str][
                                                "Ulasan"
                                            ] = ulasan_baru

                                            gbr_updated_list = data.get("Senarai_Gambar", [])
                                            if gambar_baru_list:
                                                if len(gambar_baru_list) > 5:
                                                    gambar_baru_list = gambar_baru_list[:5]
                                                gbr_updated_list = []
                                                for g_f in gambar_baru_list:
                                                    b64_str = gambar_ke_base64(g_f)
                                                    if b64_str:
                                                        gbr_updated_list.append(b64_str)

                                            st.session_state.pangkalan_data[zon][
                                                nm_auditor
                                            ][komp][no_item_str][
                                                "Senarai_Gambar"
                                            ] = gbr_updated_list

                                            if conn is not None:
                                                try:
                                                    df_g = conn.read(
                                                        spreadsheet=URL_GSHEETS,
                                                        ttl=0,
                                                    )
                                                    mask = (
                                                        (df_g["Zon"] == zon)
                                                        & (
                                                            df_g["Juruaudit"]
                                                            == nm_auditor
                                                        )
                                                        & (
                                                            df_g["Komponen"]
                                                            == komp
                                                        )
                                                        & (
                                                            df_g[
                                                                "No_Item"
                                                            ].astype(str)
                                                            == no_item_str
                                                        )
                                                    )
                                                    df_g.loc[
                                                        mask, "Markah"
                                                    ] = markah_baru
                                                    df_g.loc[
                                                        mask, "Ulasan"
                                                    ] = ulasan_baru

                                                    if gambar_baru_list:
                                                        for idx_up in range(1, 6):
                                                            col_n = f"Gambar_{idx_up}"
                                                            val_up = (
                                                                gbr_updated_list[idx_up - 1]
                                                                if len(gbr_updated_list) >= idx_up
                                                                else ""
                                                            )
                                                            df_g.loc[mask, col_n] = val_up

                                                    conn.update(
                                                        spreadsheet=URL_GSHEETS,
                                                        data=df_g,
                                                    )
                                                except Exception:
                                                    pass

                                            st.success(
                                                "✅ Rekod berjaya dikemas kini!"
                                            )
                                            st.rerun()

                                # BUTANG PADAM (DELETE)
                                with c_del:
                                    if st.button(
                                        "🗑️ Padam",
                                        key=f"del_{zon}_{nm_auditor}_{komp}_{no_item_str}",
                                        type="primary",
                                    ):
                                        del st.session_state.pangkalan_data[
                                            zon
                                        ][nm_auditor][komp][no_item_str]

                                        if conn is not None:
                                            try:
                                                df_g = conn.read(
                                                    spreadsheet=URL_GSHEETS,
                                                    ttl=0,
                                                )
                                                df_filtered = df_g[
                                                    ~(
                                                        (df_g["Zon"] == zon)
                                                        & (
                                                            df_g["Juruaudit"]
                                                            == nm_auditor
                                                        )
                                                        & (
                                                            df_g["Komponen"]
                                                            == komp
                                                        )
                                                        & (
                                                            df_g[
                                                                "No_Item"
                                                            ].astype(str)
                                                            == no_item_str
                                                        )
                                                    )
                                                ]
                                                conn.update(
                                                    spreadsheet=URL_GSHEETS,
                                                    data=df_filtered,
                                                )
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
            senarai_auditor_laporan = (
                list(dict_zon_terpilih.keys())
                if pilih_auditor == "Semua Juruaudit"
                else (
                    [pilih_auditor] if pilih_auditor in dict_zon_terpilih else []
                )
            )

            for nm_auditor in senarai_auditor_laporan:
                rekod_auditor = dict_zon_terpilih[nm_auditor]
                lok_khusus = rekod_auditor.get("_lokasi_khusus", "Biasa")

                for komp in senarai_komp_laporan:
                    rekod_komp = {}
                    komp_code = komp.split(":")[0].strip().upper() if ":" in komp else komp.strip().upper()
                    for k_entry, v_entry in rekod_auditor.items():
                        k_entry_code = k_entry.split(":")[0].strip().upper() if ":" in k_entry else k_entry.strip().upper()
                        if komp_code == k_entry_code:
                            rekod_komp = v_entry
                            break

                    item_sah_zon = dapatkan_item_tapis(komp, zon)
                    no_item_sah_zon = [
                        "".join(filter(str.isdigit, str(x["No"])))
                        for x in item_sah_zon
                    ]

                    for no_item, data in rekod_komp.items():
                        no_item_str = str(no_item).strip()
                        no_item_dig = "".join(filter(str.isdigit, no_item_str))
                        m_val = data.get("Markah") if isinstance(data, dict) else None

                        if (
                            no_item_dig in no_item_sah_zon
                            and str(m_val).isdigit()
                            and int(m_val) == 5
                        ):
                            ada_cemerlang = True
                            padanan_item = [
                                orig
                                for orig in data_eksa.get(komp, [])
                                if "".join(filter(str.isdigit, str(orig["No"])))
                                == no_item_dig
                            ]
                            subtopik_item = (
                                padanan_item[0]["Subtopik"]
                                if padanan_item
                                else "KRITERIA UMUM"
                            )
                            perkara_item = (
                                padanan_item[0]["Perkara"]
                                if padanan_item
                                else f"Item {no_item_str}"
                            )

                            st.success(
                                f"**[{zon} - {lok_khusus}] {subtopik_item} - Item {no_item_str}** \n{perkara_item} \n*(Oleh: {nm_auditor}) | Ulasan: {data['Ulasan'] if data['Ulasan'] else 'Memuaskan'}*"
                            )

        if not ada_cemerlang:
            st.info(
                "Tiada rekod item cemerlang (Markah 5) dijumpai untuk kriteria yang dipilih."
            )

        st.markdown("---")

        st.subheader(
            "⚠️ Pencapaian Rendah & Tindakan Susulan (Markah 1 & 2)"
        )
        ada_kelemahan = False

        for zon in zon_sasaran:
            dict_zon_terpilih = st.session_state.pangkalan_data[zon]
            senarai_auditor_laporan = (
                list(dict_zon_terpilih.keys())
                if pilih_auditor == "Semua Juruaudit"
                else (
                    [pilih_auditor] if pilih_auditor in dict_zon_terpilih else []
                )
            )

            for nm_auditor in senarai_auditor_laporan:
                rekod_auditor = dict_zon_terpilih[nm_auditor]
                lok_khusus = rekod_auditor.get("_lokasi_khusus", "Biasa")

                for komp in senarai_komp_laporan:
                    rekod_komp = {}
                    komp_code = komp.split(":")[0].strip().upper() if ":" in komp else komp.strip().upper()
                    for k_entry, v_entry in rekod_auditor.items():
                        k_entry_code = k_entry.split(":")[0].strip().upper() if ":" in k_entry else k_entry.strip().upper()
                        if komp_code == k_entry_code:
                            rekod_komp = v_entry
                            break

                    item_sah_zon = dapatkan_item_tapis(komp, zon)
                    no_item_sah_zon = [
                        "".join(filter(str.isdigit, str(x["No"])))
                        for x in item_sah_zon
                    ]

                    for no_item, data in rekod_komp.items():
                        no_item_str = str(no_item).strip()
                        no_item_dig = "".join(filter(str.isdigit, no_item_str))
                        m_val = data.get("Markah") if isinstance(data, dict) else None

                        if (
                            no_item_dig in no_item_sah_zon
                            and isinstance(data, dict)
                            and str(m_val).isdigit()
                            and int(m_val) <= 2
                        ):
                            ada_kelemahan = True
                            padanan_item = [
                                orig
                                for orig in data_eksa.get(komp, [])
                                if "".join(filter(str.isdigit, str(orig["No"])))
                                == no_item_dig
                            ]
                            subtopik_item = (
                                padanan_item[0]["Subtopik"]
                                if padanan_item
                                else "KRITERIA UMUM"
                            )
                            perkara_item = (
                                padanan_item[0]["Perkara"]
                                if padanan_item
                                else f"Item {no_item_str}"
                            )

                            st.error(
                                f"**[{zon} - {lok_khusus}] {subtopik_item} - Item {no_item_str}** \n{perkara_item} *(Dinilai oleh: {nm_auditor})*"
                            )
                            col_sebelum, col_selepas = st.columns(2)

                            with col_sebelum:
                                st.markdown("#### 🔴 Penemuan Asal")
                                st.write(
                                    f"**Skor Diberikan:** {data['Markah']} / 5"
                                )
                                st.write(
                                    f"**Komen Juruaudit:** {data['Ulasan'] if data['Ulasan'] else '*Tiada ulasan ditinggalkan.*'}"
                                )
                                gbr_asal_list = data.get("Senarai_Gambar", [])
                                if gbr_asal_list:
                                    cols_g_asal = st.columns(min(len(gbr_asal_list), 5))
                                    for idx_g_a, img_g_a in enumerate(gbr_asal_list):
                                        with cols_g_asal[idx_g_a]:
                                            st.image(
                                                img_g_a,
                                                caption=f"Gambar {idx_g_a+1}",
                                                use_container_width=True,
                                            )
                                else:
                                    st.info("Tiada bukti gambar asal.")

                            with col_selepas:
                                st.markdown("#### 🟢 Tindakan Penambahbaikan")
                                with st.form(
                                    key=f"susulan_m_{zon}_{nm_auditor}_{komp}_{no_item_str}"
                                ):
                                    tarikh_baru = st.date_input(
                                        "Tarikh Tindakan:",
                                        value=data.get(
                                            "Tarikh_Susulan",
                                            datetime.date.today(),
                                        ),
                                    )
                                    ulasan_baru = st.text_area(
                                        "Tindakan yang telah diambil:",
                                        value=data["Ulasan_Susulan"],
                                        height=80,
                                    )
                                    gambar_baru_muat_naik = st.file_uploader(
                                        "Muat Naik Gambar (Selepas)",
                                        type=["png", "jpg", "jpeg"],
                                        key=f"gambar_susulan_m_{zon}_{nm_auditor}_{komp}_{no_item_str}",
                                    )
                                    simpan_susulan = st.form_submit_button(
                                        "Simpan & Kemas Kini Susulan"
                                    )

                                    gambar_susulan_disimpan = data[
                                        "Gambar_Susulan"
                                    ]
                                    if gambar_baru_muat_naik is not None:
                                        gambar_susulan_disimpan = (
                                            gambar_ke_base64(
                                                gambar_baru_muat_naik
                                            )
                                        )

                                    if simpan_susulan:
                                        st.session_state.pangkalan_data[zon][
                                            nm_auditor
                                        ][komp][no_item_str][
                                            "Tarikh_Susulan"
                                        ] = tarikh_baru
                                        st.session_state.pangkalan_data[zon][
                                            nm_auditor
                                        ][komp][no_item_str][
                                            "Ulasan_Susulan"
                                        ] = ulasan_baru
                                        st.session_state.pangkalan_data[zon][
                                            nm_auditor
                                        ][komp][no_item_str][
                                            "Gambar_Susulan"
                                        ] = gambar_susulan_disimpan
                                        st.success(
                                            "Tindakan susulan dikemas kini!"
                                        )
                                        st.rerun()

                                if data["Ulasan_Susulan"]:
                                    st.write(
                                        f"**Tarikh Selesai:** {data['Tarikh_Susulan'].strftime('%d/%m/%Y')}"
                                    )
                                    st.write(
                                        f"**Tindakan Ambilan:** {data['Ulasan_Susulan']}"
                                    )
                                else:
                                    st.write(
                                        "*(Belum ada tindakan direkodkan)*"
                                    )

                                if data["Gambar_Susulan"]:
                                    st.image(
                                        data["Gambar_Susulan"],
                                        caption="Bukti Selepas Penambahbaikan",
                                        use_container_width=True,
                                    )
                            st.markdown("---")

        if not ada_kelemahan:
            st.success(
                "Tahniah! Tiada item dengan markah rendah (1 atau 2) yang memerlukan tindakan susulan bagi tetapan yang dipilih."
            )

# ==========================================
# PAPARAN 3: RUMUSAN MARKAH TERPERINCI
# ==========================================
elif menu_paparan == "📈 Rumusan Markah Terperinci":

    st.title("📈 Rumusan Markah Terperinci")
    st.write(
        "Paparan terperinci rubrik dan markah mengikut komponen dan zon seperti jadual rasmi."
    )

    pilih_komp = st.selectbox("Sila Pilih Komponen:", list(data_eksa.keys()))

    komponen_upper = str(pilih_komp).upper()
    if "KOMPONEN A" in komponen_upper or "KOMPONEN E" in komponen_upper:
        zon_rasmi_list = ["ZON INDUK"]
    else:
        zon_rasmi_list = [
            "ZON EFEKTIF",
            "ZON KOMITED",
            "ZON SEPAKAT",
            "ZON AKTIF",
        ]

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
    
    # Ambil kod awalan komponen pilih (Contoh: "KOMPONEN A")
    target_komp_code = pilih_komp.split(":")[0].strip().upper() if ":" in pilih_komp else pilih_komp.strip().upper()

    for item in data_eksa[pilih_komp]:
        item_no_str = str(item["No"]).strip()
        item_dig = "".join(filter(str.isdigit, item_no_str))

        if item["Subtopik"] != current_sub:
            total_colspan = 7 + colspan_markah
            html_jadual_rumusan += f"<tr class='subtopik-row'><td colspan='{total_colspan}'>{item['Subtopik']}</td></tr>"
            current_sub = item["Subtopik"]

        skor_dicatat = {}
        for z in zon_rasmi_list:
            item_sebenar_zon = dapatkan_item_tapis(pilih_komp, z)
            item_nums_zon = [
                "".join(filter(str.isdigit, str(x["No"])))
                for x in item_sebenar_zon
            ]

            if item_dig not in item_nums_zon:
                skor_dicatat[z] = "-"
            else:
                skor_semasa = ""

                # Cari zon berpadanan
                zon_key_match = None
                for z_k in st.session_state.pangkalan_data.keys():
                    if str(z_k).strip().upper() == str(z).strip().upper():
                        zon_key_match = z_k
                        break

                if zon_key_match:
                    dict_zon = st.session_state.pangkalan_data[zon_key_match]
                    for aud_name, data_auditor in dict_zon.items():
                        
                        # Padankan komponen berasaskan Awalan (Contoh: "KOMPONEN A")
                        komp_key_match = None
                        for k_k in data_auditor.keys():
                            k_code = k_k.split(":")[0].strip().upper() if ":" in k_k else k_k.strip().upper()
                            if target_komp_code == k_code:
                                komp_key_match = k_k
                                break

                        if komp_key_match:
                            dict_item = data_auditor[komp_key_match]
                            for i_k, i_v in dict_item.items():
                                if "".join(filter(str.isdigit, str(i_k))) == item_dig:
                                    if isinstance(i_v, dict):
                                        skor_val = i_v.get("Markah", "")
                                        skor_semasa = skor_val

                                        if str(skor_val).isdigit():
                                            jumlah_skor_zon[z] += int(skor_val)
                                    break
                            if skor_semasa != "":
                                break

                skor_dicatat[z] = skor_semasa if skor_semasa != "" else "-"

        kolum_markah_html = ""
        for z in zon_rasmi_list:
            kolum_markah_html += (
                f'<td class="center-text"><b>{skor_dicatat[z]}</b></td>\n'
            )

        html_jadual_rumusan += f"""<tr>
<td class="center-text"><b>{item_no_str}</b></td>
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
            [
                "1. Markah Audit (Format Ringkas)",
                "2. Laporan Penilaian Audit (Format Penuh)",
            ],
            horizontal=True,
        )

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        nama_agensi = st.text_input(
            "Nama Agensi / Kolej:", "KOLEJ KOMUNITI HULU LANGAT"
        )
    with col_i2:
        tarikh_audit_cetak = st.date_input("Tarikh Audit:", datetime.date.today())

    zon_rasmi_list = [
        "ZON INDUK",
        "ZON EFEKTIF",
        "ZON KOMITED",
        "ZON SEPAKAT",
        "ZON AKTIF",
    ]

    # Pemetaan item yang tidak berkenaan mengikut Komponen & Zon
    def is_na_zone(komp_key, zon_nama):
        k_upper = str(komp_key).upper()
        z_upper = str(zon_nama).upper()
        if "KOMPONEN A" in k_upper or "KOMPONEN E" in k_upper:
            return "ZON INDUK" not in z_upper
        elif "KOMPONEN B" in k_upper or "KOMPONEN C" in k_upper or "KOMPONEN D" in k_upper:
            return "ZON INDUK" in z_upper
        return False

    # Fungsi kumpul markah diperolehi & markah penuh
    def kumpul_markah_zon(zon_nama, komp_nama):
        if is_na_zone(komp_nama, zon_nama):
            return None, None  # Penanda tidak berkenaan (-)

        items_tapis = dapatkan_item_tapis(komp_nama, zon_nama)
        m_penuh_standard = len(items_tapis) * 5

        total_m = 0
        count_item = 0

        zon_match = None
        for z_k in st.session_state.pangkalan_data.keys():
            if str(z_k).strip().upper() == str(zon_nama).strip().upper():
                zon_match = z_k
                break

        if zon_match:
            dict_zon = st.session_state.pangkalan_data[zon_match]
            target_code = komp_nama.split(":")[0].strip().upper() if ":" in komp_nama else komp_nama.strip().upper()

            for nm_aud, data_aud in dict_zon.items():
                komp_match = None
                for k_k in data_aud.keys():
                    k_code = k_k.split(":")[0].strip().upper() if ":" in k_k else k_k.strip().upper()
                    if target_code == k_code:
                        komp_match = k_k
                        break

                if komp_match:
                    for no_i, d_item in data_aud[komp_match].items():
                        if isinstance(d_item, dict) and "Markah" in d_item:
                            m_val = d_item["Markah"]
                            if str(m_val).isdigit():
                                total_m += int(m_val)
                                count_item += 1

        total_p = (count_item * 5) if count_item > 0 else m_penuh_standard
        return total_m, total_p

    # Dapatkan Gambar Logo jika wujud
    logo_base64_str = ""
    if fail_logo and os.path.exists(fail_logo):
        try:
            with open(fail_logo, "rb") as img_f:
                logo_base64_str = f"data:image/png;base64,{base64.b64encode(img_f.read()).decode()}"
        except Exception:
            logo_base64_str = ""

    html_logo_tag = f'<img src="{logo_base64_str}" style="max-height: 80px; width: auto;">' if logo_base64_str else ""

    html_kandungan = ""
    senarai_komp_keys = ["KOMPONEN A", "KOMPONEN B", "KOMPONEN C", "KOMPONEN D", "KOMPONEN E"]
    kod_huruf = ["A.", "B.", "C.", "D.", "E."]

    # FORMAT 1: MARKAH AUDIT (FORMAT RINGKAS)
    if pilihan_jenis_cetakan == "1. Markah Audit (Format Ringkas)":
        html_kandungan = f"""
        <div style="display: flex; align-items: center; justify-content: center; position: relative; margin-bottom: 20px; background-color: #ffffff; color: #000000; padding: 10px; border: 1.5px solid #000000;">
            <div style="position: absolute; left: 15px;">{html_logo_tag}</div>
            <div style="text-align: center; width: 100%;">
                <h3 style="margin: 0; font-family: Arial, sans-serif; color: #000000; font-weight: bold; font-size: 18px;">
                    MARKAH AUDIT DALAM EKSA {tarikh_audit_cetak.year}<br>{nama_agensi}
                </h3>
            </div>
        </div>
        <table class="jadual-laporan">
            <thead>
                <tr>
                    <th class="header-kelabu" style="width: 5%;">BIL.</th>
                    <th class="header-kelabu" style="width: 35%;">KOMPONEN</th>
                    <th style="background-color: #ffff00 !important; color: #000000; width: 12%;">% MARKAH ZON<br>INDUK</th>
                    <th style="background-color: #fef3c7 !important; color: #000000; width: 12%;">% MARKAH ZON<br>EFEKTIF</th>
                    <th style="background-color: #bfdbfe !important; color: #000000; width: 12%;">% MARKAH ZON<br>KOMITED</th>
                    <th style="background-color: #fca5a5 !important; color: #000000; width: 12%;">% MARKAH ZON<br>SEPAKAT</th>
                    <th style="background-color: #bbf7d0 !important; color: #000000; width: 12%;">% MARKAH ZON<br>AKTIF</th>
                </tr>
            </thead>
            <tbody>
        """

        zon_total_m = {z: 0 for z in zon_rasmi_list}
        zon_total_p = {z: 0 for z in zon_rasmi_list}

        for idx, k_key in enumerate(senarai_komp_keys):
            nam_komp = [k for k in data_eksa.keys() if k_key in str(k).upper()]
            nam_komp_full = nam_komp[0] if nam_komp else k_key
            tajuk_bersih = (
                nam_komp_full.replace("KOMPONEN A", "KEPERLUAN UTAMA PELAKSANAAN")
                .replace("KOMPONEN B", "RUANG TEMPAT KERJA / PEJABAT")
                .replace("KOMPONEN C", "TEMPAT UMUM")
                .replace("KOMPONEN D", "BILIK PEMBELAJARAN & PENGAJARAN")
                .replace("KOMPONEN E", "KESELAMATAN PERSEKITARAN")
            )

            html_kandungan += f"<tr><td><b>{kod_huruf[idx]}</b></td><td style='text-align: left;'><b>{tajuk_bersih}</b></td>"
            for z_nam in zon_rasmi_list:
                m_dapat, m_penuh = kumpul_markah_zon(z_nam, nam_komp_full)
                if m_dapat is None:
                    # Tukar N/A kepada -
                    html_kandungan += "<td style='background-color: #ffffff; color: #000000;'><b>-</b></td>"
                else:
                    zon_total_m[z_nam] += m_dapat
                    zon_total_p[z_nam] += m_penuh
                    pct_str = f"{(m_dapat / m_penuh * 100):.2f}%" if m_penuh > 0 else ""
                    html_kandungan += f"<td><b>{pct_str}</b></td>"
            html_kandungan += "</tr>"

        html_kandungan += "<tr><td colspan='2' class='header-kelabu'><b>PERATUS MARKAH ZON</b></td>"
        grand_m = 0
        grand_p = 0
        for z_nam in zon_rasmi_list:
            if zon_total_p[z_nam] > 0:
                z_pct = (zon_total_m[z_nam] / zon_total_p[z_nam]) * 100
                html_kandungan += f"<td><b>{z_pct:.2f}%</b></td>"
            else:
                html_kandungan += f"<td><b></b></td>"
            grand_m += zon_total_m[z_nam]
            grand_p += zon_total_p[z_nam]
        html_kandungan += "</tr>"

        grand_pct_str = f"{(grand_m / grand_p * 100):.2f}%" if grand_p > 0 else ""
        html_kandungan += f"""
            <tr>
                <td colspan='2' class='header-kelabu'><b>PERATUS MARKAH KESELURUHAN</b></td>
                <td colspan='5' style='font-size: 16px; text-align: center;'><b>{grand_pct_str}</b></td>
            </tr>
            </tbody>
        </table>
        """

    # FORMAT 2: LAPORAN PENILAIAN AUDIT (FORMAT PENUH)
    elif pilihan_jenis_cetakan == "2. Laporan Penilaian Audit (Format Penuh)":
        html_kandungan = f"""
        <div style="display: flex; align-items: center; justify-content: center; position: relative; margin-bottom: 10px; background-color: #ffffff; color: #000000; padding: 10px; border: 1.5px solid #000000;">
            <div style="position: absolute; left: 15px;">{html_logo_tag}</div>
            <div style="text-align: center; width: 100%;">
                <h3 style="margin: 0; font-family: Arial, sans-serif; color: #000000; font-weight: bold; font-size: 16px;">
                    LAPORAN PENILAIAN AUDIT EKSA {tarikh_audit_cetak.year}<br>{nama_agensi}
                </h3>
            </div>
        </div>
        <p style="font-family: Arial, sans-serif; color: #000000; margin-bottom: 8px;"><b>TARIKH AUDIT: {tarikh_audit_cetak.strftime('%d %B %Y').upper()}</b></p>
        <table class="jadual-laporan">
            <thead>
                <tr>
                    <th rowspan="2" class="header-kelabu" style="width: 3%;">BIL.</th>
                    <th rowspan="2" class="header-kelabu" style="width: 25%;">KOMPONEN</th>
                    <th colspan="2" style="background-color: #e9d5ff !important; color: #000000;">ZON INDUK</th>
                    <th colspan="2" style="background-color: #fef3c7 !important; color: #000000;">ZON EFEKTIF</th>
                    <th colspan="2" style="background-color: #bfdbfe !important; color: #000000;">ZON KOMITED</th>
                    <th colspan="2" style="background-color: #fca5a5 !important; color: #000000;">ZON SEPAKAT</th>
                    <th colspan="2" style="background-color: #bbf7d0 !important; color: #000000;">ZON AKTIF</th>
                </tr>
                <tr>
                    <th style="background-color: #e9d5ff !important; color: #000000; font-size: 11px;">MARKAH PENUH ZON INDUK</th>
                    <th style="background-color: #e9d5ff !important; color: #000000; font-size: 11px;">MARKAH YANG DIPEROLEH ZON INDUK</th>
                    <th style="background-color: #fef3c7 !important; color: #000000; font-size: 11px;">MARKAH PENUH ZON EFEKTIF</th>
                    <th style="background-color: #fef3c7 !important; color: #000000; font-size: 11px;">MARKAH YANG DIPEROLEH ZON EFEKTIF</th>
                    <th style="background-color: #bfdbfe !important; color: #000000; font-size: 11px;">MARKAH PENUH ZON KOMITED</th>
                    <th style="background-color: #bfdbfe !important; color: #000000; font-size: 11px;">MARKAH YANG DIPEROLEH ZON KOMITED</th>
                    <th style="background-color: #fca5a5 !important; color: #000000; font-size: 11px;">MARKAH PENUH ZON SEPAKAT</th>
                    <th style="background-color: #fca5a5 !important; color: #000000; font-size: 11px;">MARKAH YANG DIPEROLEH ZON SEPAKAT</th>
                    <th style="background-color: #bbf7d0 !important; color: #000000; font-size: 11px;">MARKAH PENUH ZON AKTIF</th>
                    <th style="background-color: #bbf7d0 !important; color: #000000; font-size: 11px;">MARKAH YANG DIPEROLEH ZON AKTIF</th>
                </tr>
            </thead>
            <tbody>
        """

        zon_total_m = {z: 0 for z in zon_rasmi_list}
        zon_total_p = {z: 0 for z in zon_rasmi_list}

        for idx, k_key in enumerate(senarai_komp_keys):
            nam_komp = [k for k in data_eksa.keys() if k_key in str(k).upper()]
            nam_komp_full = nam_komp[0] if nam_komp else k_key
            tajuk_bersih = (
                nam_komp_full.replace("KOMPONEN A", "KEPERLUAN UTAMA PELAKSANAAN")
                .replace("KOMPONEN B", "RUANG TEMPAT KERJA / PEJABAT")
                .replace("KOMPONEN C", "TEMPAT UMUM")
                .replace("KOMPONEN D", "BILIK PEMBELAJARAN & PENGAJARAN")
                .replace("KOMPONEN E", "KESELAMATAN PERSEKITARAN")
            )

            html_kandungan += f"<tr><td><b>{kod_huruf[idx]}</b></td><td style='text-align: left;'><b>{tajuk_bersih}</b></td>"
            for z_nam in zon_rasmi_list:
                m_dapat, m_penuh = kumpul_markah_zon(z_nam, nam_komp_full)
                if m_dapat is None:
                    # Tukar N/A kepada -
                    html_kandungan += "<td style='color: #ff0000; font-weight: bold;'>-</td><td></td>"
                else:
                    zon_total_m[z_nam] += m_dapat
                    zon_total_p[z_nam] += m_penuh
                    txt_p = str(m_penuh)
                    txt_m = str(m_dapat) if m_dapat > 0 else ""

                    color_style = "color: #ff0000; font-weight: bold;" if z_nam != "ZON INDUK" else "font-weight: bold;"
                    html_kandungan += f"<td style='{color_style}'>{txt_p}</td><td><b>{txt_m}</b></td>"
            html_kandungan += "</tr>"

        html_kandungan += "<tr><td colspan='2' class='header-kelabu'><b>JUMLAH MARKAH</b></td>"
        grand_m = 0
        grand_p = 0
        for z_nam in zon_rasmi_list:
            txt_jp = str(zon_total_p[z_nam]) if zon_total_p[z_nam] > 0 else ""
            txt_jm = str(zon_total_m[z_nam]) if zon_total_m[z_nam] > 0 else "0"
            color_style = "color: #ff0000; font-weight: bold;" if z_nam != "ZON INDUK" else "font-weight: bold;"

            html_kandungan += f"<td style='{color_style}'>{txt_jp}</td><td style='{color_style}'>{txt_jm}</td>"
            grand_m += zon_total_m[z_nam]
            grand_p += zon_total_p[z_nam]
        html_kandungan += "</tr>"

        html_kandungan += "<tr><td colspan='2' class='header-kelabu'><b>PERATUS MARKAH ZON</b></td>"
        for z_nam in zon_rasmi_list:
            if zon_total_p[z_nam] > 0:
                z_pct = (zon_total_m[z_nam] / zon_total_p[z_nam]) * 100
                html_kandungan += f"<td colspan='2'><b>{z_pct:.2f}%</b></td>"
            else:
                html_kandungan += f"<td colspan='2'><b>0.00%</b></td>"
        html_kandungan += "</tr>"

        grand_pct_str = f"{(grand_m / grand_p * 100):.2f}%" if grand_p > 0 else "0.00%"
        html_kandungan += f"""
            <tr>
                <td colspan='2' class='header-kelabu'><b>PERATUS MARKAH KESELURUHAN</b></td>
                <td colspan='10' style='font-size: 16px; text-align: center;'><b>{grand_pct_str}</b></td>
            </tr>
            </tbody>
        </table>
        <br><br>
        <div style="display: flex; justify-content: space-between; font-family: Arial, sans-serif; color: #000000; background-color: #ffffff; padding: 0 20px;">
            <div>
                <b>PENGESAHAN<br>KETUA JURUAUDIT</b><br><br><br><br>
                TANDATANGAN: ___________________________<br>
                NAMA : MAZWINA HANIM BINTI ABU BAKAR<br>
                TARIKH: ________________________________
            </div>
            <div>
                <b>PENGESAHAN<br>WAKIL PENGURUSAN</b><br><br><br><br>
                TANDATANGAN: ___________________________<br>
                NAMA : _________________________________<br>
                TARIKH: ________________________________
            </div>
        </div>
        """

    # Komponen Cetakan JS & HTML View
    components.html(
        f"""
        <script>
        function cetakLaporanIsolasi() {{
            var kandungan = `{html_kandungan}`;
            var mywindow = window.open('', 'PRINT', 'height=800,width=1100');
            mywindow.document.write('<html><head><title>Laporan Audit EKSA</title>');
            mywindow.document.write('<style>');
            mywindow.document.write('@page {{ size: landscape; margin: 10mm; }}');
            mywindow.document.write('body {{ background-color: #ffffff !important; color: #000000 !important; font-family: Arial, sans-serif; padding: 10px; }}');
            mywindow.document.write('.jadual-laporan {{ width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 12px; text-align: center; margin-top: 5px; background-color: #ffffff !important; color: #000000 !important; }}');
            mywindow.document.write('.jadual-laporan th, .jadual-laporan td {{ border: 1.5px solid #000000 !important; padding: 5px; color: #000000 !important; background-color: #ffffff; }}');
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
        height=65,
    )
    st.markdown("---")
    st.markdown(
        f"<div class='jadual-laporan-wrapper'>{html_kandungan}</div>",
        unsafe_allow_html=True,
    )
