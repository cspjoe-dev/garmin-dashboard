# Garmin 跑步準備度儀表板

類似「雷蒙三十 - 生活黑客社群」學員作品的個人化 AI 跑步教練 dashboard。

使用 Garmin 官方 **Personal API**（2026 年 10 月新開放），可安全讀取你自己的手錶資料（HRV、睡眠、心率、活動、Body Battery 等），無需輸入密碼。

## 快速開始

1. **取得 API Key**（只需幾秒）  
   登入 [Garmin Connect](https://connect.garmin.com) → 前往  
   [https://connect.garmin.com/app/settings/personalApiToken](https://connect.garmin.com/app/settings/personalApiToken)  
   建立 Key，複製保存（只顯示一次）。

2. **安裝依賴**（建議 Python 3.12+，若較舊也可試）  
   ```bash
   pip install -r requirements.txt
   ```
   若官方套件因 Python 版本無法安裝，app.py 已內建簡易 client，只需 `requests` + `streamlit` 即可。

3. **執行**  
   ```bash
   streamlit run app.py
   ```
   在側邊欄貼上 API Key，即可同步真實資料。

## 功能

- 今日準備度分數（綜合 HRV、睡眠等）
- 負荷平衡參考（TSB / CTL / ATL 近似）
- 準備度雷達圖
- 關鍵指標卡片
- AI 風格今日訓練建議
- 近期活動列表

## 注意

- 資料結構可能隨 Garmin API 調整，若某欄位顯示異常，歡迎回報。
- 官方 Personal API 目前為 pull 模式，歷史資料範圍以 Garmin 提供為準。
- 僅供個人健康與訓練參考，非醫療建議。

享受你的個人化跑步儀表板！
