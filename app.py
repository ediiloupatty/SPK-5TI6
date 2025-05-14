from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import numpy as np
import os
import logging
from urllib.parse import unquote_plus

app = Flask(__name__)
app.secret_key = 'supersecretkeycomplex123'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 300  # 5 menit

# Setup logging
logging.basicConfig(level=logging.DEBUG)

DATA_FILE = 'data_smartphone.xlsx'
CRITERIA = [
    'Harga (Rp)', 'Kapasitas Baterai (mAh)', 'RAM (GB)',
    'Penyimpanan (GB)', 'Kamera Belakang (MP)', 'Kamera Depan (MP)', 
    'Ukuran Layar (inci)'
]
WEIGHTS = np.array([0.2, 0.15, 0.15, 0.1, 0.1, 0.1, 0.2])
IMPACTS = np.array([-1, 1, 1, 1, 1, 1, 1])

def improved_topsis(data, user_input, weights, impacts):
    try:
        combined_data = np.vstack([data, user_input])
        norm_data = combined_data / np.sqrt((combined_data**2).sum(axis=0))
        weighted_data = norm_data * weights
        user_point = weighted_data[-1]
        distances = np.sqrt(((weighted_data[:-1] - user_point)**2).sum(axis=1))
        scores = 1 / (1 + distances)
        return scores
    except Exception as e:
        logging.error(f"Improved TOPSIS error: {str(e)}")
        return None

@app.route('/')
def index():
    criteria_mapping = {
        'harga': 'Harga (Rp)',
        'baterai': 'Kapasitas Baterai (mAh)',
        'ram': 'RAM (GB)',
        'penyimpanan': 'Penyimpanan (GB)',
        'kamera_belakang': 'Kamera Belakang (MP)',
        'kamera_depan': 'Kamera Depan (MP)',
        'layar': 'Ukuran Layar (inci)',
        'os': 'Sistem Operasi',
        'prosesor': 'Prosesor',
        'resolusi': 'Resolusi Layar'
    }
    criteria_options = {key: [] for key in criteria_mapping.keys()}

    try:
        if os.path.exists(DATA_FILE):
            df = pd.read_excel(DATA_FILE, engine='openpyxl')
            for form_field, df_column in criteria_mapping.items():
                if df_column in df.columns:
                    if form_field in ['harga', 'baterai', 'ram', 'penyimpanan', 'kamera_belakang', 'kamera_depan', 'layar']:
                        df[df_column] = pd.to_numeric(df[df_column], errors='coerce')
                        options = df[df_column].dropna().unique().tolist()
                        options = sorted(options, reverse=(form_field == 'harga'))
                    else:
                        df[df_column] = df[df_column].astype(str).str.strip()
                        options = df[df_column].unique().tolist()
                        options.sort()
                    criteria_options[form_field] = options
    except Exception as e:
        logging.error(f"Database error: {str(e)}")
        flash('Terjadi kesalahan dalam membaca database', 'error')

    return render_template('index.html', criteria_options=criteria_options)

@app.route('/submit', methods=['POST'])
def submit():
    session.permanent = True
    form_data = request.form.copy()
    session['form_data'] = form_data

    try:
        categorical_filters = {
            'Sistem Operasi': form_data.get('os', '').lower().strip(),
            'Prosesor': form_data.get('prosesor', '').lower().strip(),
            'Resolusi Layar': form_data.get('resolusi', '').lower().strip()
        }

        original_df = pd.read_excel(DATA_FILE, engine='openpyxl')
        filtered_dfs = []
        for i in range(3):
            temp_df = original_df.copy()
            if i == 1:
                categorical_filters['Resolusi Layar'] = ''
            elif i == 2:
                categorical_filters['Prosesor'] = ''
                categorical_filters['Resolusi Layar'] = ''

            for col, value in categorical_filters.items():
                if value and value not in ['', 'pilih...'] and col in temp_df.columns:
                    temp_df = temp_df[temp_df[col].astype(str).str.lower().str.strip() == value]

            if not temp_df.empty:
                filtered_dfs.append(temp_df)
                break

        if not filtered_dfs:
            df = original_df
        else:
            df = pd.concat(filtered_dfs).drop_duplicates()

        df = df.reset_index(drop=True)
        data = df[CRITERIA].apply(pd.to_numeric, errors='coerce').dropna()
        valid_indices = data.index
        df = df.loc[valid_indices].copy()

        user_input = np.array([
            float(form_data.get('harga', 0)),
            float(form_data.get('baterai', 0)),
            float(form_data.get('ram', 0)),
            float(form_data.get('penyimpanan', 0)),
            float(form_data.get('kamera_belakang', 0)),
            float(form_data.get('kamera_depan', 0)),
            float(form_data.get('layar', 0))
        ])

        scores = improved_topsis(data.to_numpy(), user_input, WEIGHTS, IMPACTS)

        if scores is None or len(scores) == 0:
            flash('Gagal menghitung rekomendasi', 'error')
            return redirect(url_for('index'))

        df['Skor TOPSIS'] = scores
        df['Ranking'] = df['Skor TOPSIS'].rank(ascending=False, method='dense').astype(int)
        results = df.sort_values('Ranking').head(20).to_dict('records')

        if not results:
            flash('Tidak ada hasil yang ditemukan', 'error')
            return redirect(url_for('index'))

        session['results'] = results
        return redirect(url_for('hasil'))

    except Exception as e:
        logging.error(f"[CRITICAL ERROR] {str(e)}", exc_info=True)
        flash(f'🔥 Kesalahan Sistem: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/hasil')
def hasil():
    results = session.get('results', [])
    form_data = session.get('form_data', {})
    return render_template('hasil.html', results=results, form_data=form_data)

# Pindahkan route spesifikasi ke atas sebelum blok main
@app.route('/spesifikasi/<model>')
def spesifikasi(model):
    try:
        model = unquote_plus(model)  # Decode URL encoding
        df = pd.read_excel(DATA_FILE, engine='openpyxl')
        df['Model'] = df['Model'].astype(str).str.strip().str.lower()
        
        # Cari model yang cocok (case-insensitive)
        selected = df[df['Model'] == model.lower().strip()]
        
        if selected.empty:
            flash('Smartphone tidak ditemukan.', 'error')
            return redirect(url_for('hasil'))

        detail = selected.iloc[0].to_dict()
        return render_template('spesifikasi.html', detail=detail)

    except Exception as e:
        logging.error(f"Error di halaman spesifikasi: {str(e)}", exc_info=True)
        flash('Terjadi kesalahan saat membuka halaman spesifikasi.', 'error')
        return redirect(url_for('hasil'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)