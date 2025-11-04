# generate_music_csv.py
import os
import librosa
import pandas as pd
from mutagen.easyid3 import EasyID3

# 指定相對路徑：當前資料夾下的 media/
music_dir = os.path.join(os.path.dirname(__file__), "media")

data = []

# 遞迴搜尋 media/ 內的所有 mp3 檔案
for root, dirs, files in os.walk(music_dir):
    for filename in files:
        print(f"Processing file: {filename}")
        if filename.endswith(".mp3"):
            path = os.path.join(root, filename)
            rel_path = os.path.relpath(path, os.path.dirname(__file__))  # 讓路徑像 "media/xxx.mp3"

            # 預設標籤
            title = os.path.splitext(filename)[0]
            artist = "Unknown Artist"

            # 嘗試讀取 MP3 metadata
            try:
                audiofile = EasyID3(path)
                title = audiofile.get("title", [title])[0]
                artist = audiofile.get("artist", [artist])[0]
            except Exception:
                pass

            # 用 librosa 取 BPM 與能量值
            try:
                y, sr = librosa.load(path, mono=True)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                if hasattr(tempo, "__len__"):
                    tempo = float(tempo[0])
                energy = float((y ** 2).mean()) ** 0.5  # 能量估計（RMS）
                energy = round(energy, 2)
            except Exception:
                tempo = 0
                energy = 0

            data.append({
                "title": title,
                "artist": artist,
                "path": rel_path.replace("\\", "/"),  # 統一成 / 路徑格式
                "bpm": round(tempo),
                "energy": energy
            })

# 匯出 CSV 到與 .py 同一層的路徑
output_path = os.path.join(os.path.dirname(__file__), "songs.csv")
df = pd.DataFrame(data)
df.to_csv(output_path, index=False, encoding="utf-8")

print(f"✅ 已生成 {output_path}")