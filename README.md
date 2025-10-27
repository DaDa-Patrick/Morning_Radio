# MorningCast 🎙️

MorningCast 是一套自動化的個人化早晨播客產製流程。系統會在每天早晨彙整郵件摘要、天氣資料、行事曆事件與本地歌單，透過多階段 LLM 規劃並產生 SSML 播報稿，再接上 TTS 與自動混音，輸出具有淡入淡出、Crossfade 與 Sidechain Ducking 的完整播客音檔。

## 功能概覽

- 📬 **資料擷取**：讀取預先整理的郵件摘要 JSON、呼叫 Open-Meteo 取得天氣、讀取 Google Calendar、載入本地 songs.csv。
- 🧠 **三階段 LLM 管線**：
  - **LLM-A** 將原始資訊轉換成貼近日常的口語敘事。
  - **LLM-B** 規劃節目段落與情緒流程、挑選歌曲。
  - **LLM-C** 依節目規劃與 Persona 產生 SSML 完整稿。
- 🔊 **多引擎 TTS**：優先使用 Azure Speech，退回 ElevenLabs，最終使用 Edge-TTS。
- 🎚️ **音訊處理**：librosa 找出歌曲 Hook、FFmpeg 擷取副歌、Acrossfade 淡入淡出、Sidechain 壓縮 Ducking。
- 🗂️ **產出**：
  - `out/podcast_YYYYMMDD.mp3`：完成的播客。
  - `out/podcast_YYYYMMDD.md`：SSML 逐字稿。
  - `out/podcast_YYYYMMDD.json`：節目段落時間軸資料。

## 安裝與環境

1. 建議使用 Python 3.11。
2. 安裝系統依賴

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. 建立 `.env`（不要提交到 Git）：

   ```env
   OPENAI_API_KEY=...
   AZURE_SPEECH_KEY=...
   AZURE_SPEECH_REGION=...
   ELEVENLABS_API_KEY=...
   ELEVENLABS_VOICE_ID=...
   ```

   若沒有 Azure 或 ElevenLabs 金鑰，程式會自動退回免費的 Edge-TTS。

## 準備資料

- `email_summary.json`：郵件摘要陣列。
- `songs.csv`：包含歌曲標題、BPM、能量值與檔案路徑（範例指向 `media/` 目錄，可自行替換為實際檔案）。
- `media/`：請放入實際授權的音樂檔案，檔名需與 `songs.csv` 對應。
- `persona.json`：主持人角色設定（可用範例檔）。
- `email_summary.json`、`songs.csv` 與 `persona.json` 皆提供簡易示範，可依需求替換。
- Google Calendar 需要 `credentials.json` 與 `token.json`，請依 Google 官方指引設定。

## 執行流程

```bash
python main.py --date today --city "Taipei" --emails email_summary.json --songs songs.csv
```

更多選項：

- `--persona` 指定 persona 檔案。
- `--output` 指定輸出資料夾。
- `--calendar-credentials` 與 `--calendar-token` 指向 Google Calendar OAuth 憑證與 token。
- `--llm-key` 覆寫 OpenAI API Key（或直接使用環境變數）。
- `--model-*` 可替換各階段模型。

## Cron 自動化

每日 06:45 自動生成：

```
0 6 * * * cd ~/Projects/morningcast && /usr/bin/python3 main.py --date today --city Taipei
```

## 專案結構

```
morningcast/
  data/            # 資料擷取模組
  llm/             # 三階段 LLM 模組
  tts/             # TTS 引擎介面
  audio/           # 混音、Sidechain、跨淡入淡出
  pipeline/        # 高階流程 Orchestrator
  utils/           # 日誌、時間等工具
main.py            # CLI 進入點
```

## 注意事項

- 本專案預設輸出 wav/mp3 需要系統安裝 FFmpeg。
- 請確認歌曲音檔具有使用授權。
- 若需商業用途，請依各 TTS 服務授權規範升級方案。

Enjoy your personalised MorningCast! ☀️
