import numpy as np
import pandas as pd

def topsis(data, user_input, weights, impacts):
    extended_data = np.vstack([data, user_input])
    norm = extended_data / np.linalg.norm(extended_data, axis=0)
    weighted = norm * weights
    
    data_weighted = weighted[:-1]
    user_weighted = weighted[-1]
    
    ideal_best = []
    ideal_worst = []
    for i in range(len(impacts)):
        if impacts[i] == 1:  # Benefit criterion
            ideal_best.append(np.max(data_weighted[:, i]))
            ideal_worst.append(np.min(data_weighted[:, i]))
        else:  # Cost criterion
            ideal_best.append(np.min(data_weighted[:, i]))
            ideal_worst.append(np.max(data_weighted[:, i]))
    
    d_best = np.sqrt(np.sum((user_weighted - ideal_best) ** 2))
    d_worst = np.sqrt(np.sum((user_weighted - ideal_worst) ** 2))
    
    scores = []
    for row in data_weighted:
        d_b = np.sqrt(np.sum((row - ideal_best) ** 2))
        d_w = np.sqrt(np.sum((row - ideal_worst) ** 2))
        scores.append(d_w / (d_b + d_w))
    
    return np.array(scores)

def calculate_topsis(user_input):
    df = pd.read_excel('data_smartphone.xlsx')
    
    criteria = [
        'Harga (Rp)',
        'Kapasitas Baterai (mAh)',
        'RAM (GB)',
        'Penyimpanan (GB)',
        'Kamera Belakang (MP)',
        'Kamera Depan (MP)',
        'Ukuran Layar (inci)'
    ]
    
    data = df[criteria].to_numpy()
    
    weights = np.array([0.4, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    impacts = np.array([-1, 1, 1, 1, 1, 1, 1])
    
    if len(weights) != len(criteria) or len(impacts) != len(criteria):
        raise ValueError("Jumlah bobot/impact tidak sesuai dengan jumlah kriteria")
    if abs(weights.sum() - 1.0) > 0.0001:
        raise ValueError("Total bobot harus 1.0")
    
    user_input_array = np.array(user_input)
    
    scores = topsis(data, user_input_array, weights, impacts)
    
    df['Skor TOPSIS'] = scores
    df['Ranking'] = df['Skor TOPSIS'].rank(ascending=False).astype(int)
    
    filtered_df = df[df['Skor TOPSIS'] > 0.5].sort_values('Ranking').reset_index(drop=True)
    return filtered_df

# Contoh input dari pengguna
user_preferences = [2500000, 5000, 6, 128, 48, 16, 6.5]  # Harga, Baterai, RAM, dll.
result = calculate_topsis(user_preferences)
print(result)