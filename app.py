"""
Garmin 跑步準備度儀表板
類似「雷蒙三十」學員作品的 AI 跑步教練 dashboard。

使用方式：
1. 到 https://connect.garmin.com/app/settings/personalApiToken 取得 Personal API Key
2. 在側邊欄貼上 Key（或設環境變數 GARMIN_PERSONAL_API_KEY）
3. streamlit run app.py
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import os
from garmin_client import GarminPersonalClient

st.set_page_config(page_title="跑步儀表板", layout="wide", initial_sidebar_state="expanded")

# Custom CSS to mimic the beige / clean look
st.markdown("""
<style>
    .main { background-color: #faf8f5; }
    .stApp { background-color: #faf8f5; }
    h1, h2, h3 { color: #2c3e50; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 12px;
    }
    .readiness-score {
        font-size: 48px;
        font-weight: bold;
        color: #2ecc71;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏃 跑步準備度分析")
st.caption("整合 Garmin 手錶資料 · 隨時查看身體狀況與訓練建議")

# Sidebar for API key
with st.sidebar:
    st.header("設定")
    api_key = st.text_input(
        "Garmin Personal API Key",
        type="password",
        value=os.getenv("GARMIN_PERSONAL_API_KEY", ""),
        help="從 https://connect.garmin.com/app/settings/personalApiToken 取得",
    )
    if st.button("同步 Garmin"):
        st.session_state["force_refresh"] = True
    st.markdown("---")
    st.markdown("**如何取得 API Key？**")
    st.markdown("1. 登入 [Garmin Connect](https://connect.garmin.com)")
    st.markdown("2. 前往 [Personal API Token](https://connect.garmin.com/app/settings/personalApiToken)")
    st.markdown("3. 建立 Key 並複製貼上")
    st.info("此為官方 Personal API（2026/10 新開放），僅讀取你自己的資料，安全且免費。")

if not api_key:
    st.warning("請先在左側輸入 Garmin Personal API Key，即可開始同步真實資料。")
    st.info("目前顯示的是示範畫面，輸入 Key 後會自動換成你的數據。")
    # Show mock data for demo
    readiness = 84
    tsb = 7.2
    ctl = 14.0
    atl = 6.8
    hrv_status = "平衡"
    sleep_score = 78
    resting_hr = 52
    today_str = date.today().isoformat()
else:
    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Fetch data
        with st.spinner("正在從 Garmin 同步資料..."):
            hrv_data = client.get_daily_hrv(today) or client.get_daily_hrv(yesterday)
            sleep_data = client.get_daily_sleep(today) or client.get_daily_sleep(yesterday)
            summaries = client.get_daily_summaries(today - timedelta(days=7), today)
            activities = client.search_activities(limit=30, start_date=(today - timedelta(days=90)).isoformat(), end_date=today.isoformat())

        # Extract useful fields (structure may vary; handle gracefully)
        def safe_get(d, *keys, default=None):
            for k in keys:
                if isinstance(d, dict) and k in d:
                    d = d[k]
                else:
                    return default
            return d

        def to_number(val, default=70):
            """Safely convert API value to a number."""
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, dict):
                # Common patterns: {"value": 78} or nested
                for k in ("value", "score", "overall"):
                    if k in val and isinstance(val[k], (int, float)):
                        return float(val[k])
            return default

        # HRV
        hrv_raw = safe_get(hrv_data, "lastNightAvg") or safe_get(hrv_data, "weeklyAvg")
        hrv_last_night = to_number(hrv_raw, 0)
        hrv_status = safe_get(hrv_data, "status") or "未知"
        if isinstance(hrv_status, dict):
            hrv_status = hrv_status.get("status") or str(hrv_status)

        # Sleep
        sleep_raw = (
            safe_get(sleep_data, "dailySleepDTO", "sleepScores", "overall", "value")
            or safe_get(sleep_data, "dailySleepDTO", "sleepScores", "overall")
            or safe_get(sleep_data, "sleepScores", "overall")
        )
        sleep_score = to_number(sleep_raw, 70)

        # Resting HR from summaries
        resting_hr = 55
        if summaries and isinstance(summaries, dict) and "data" in summaries:
            for s in summaries.get("data", []):
                if isinstance(s, dict) and (
                    s.get("calendarDate") == today.isoformat()
                    or s.get("calendarDate") == yesterday.isoformat()
                ):
                    rhr = s.get("restingHeartRate")
                    if isinstance(rhr, (int, float)):
                        resting_hr = rhr
                    break

        # Simple readiness approximation (0-100)
        hrv_factor = min(100, max(40, (hrv_last_night / 50) * 70)) if hrv_last_night else 70
        sleep_factor = sleep_score
        readiness = int(0.45 * hrv_factor + 0.35 * sleep_factor + 0.2 * 75)
        readiness = max(1, min(100, readiness))

        # Simple load metrics (placeholder; real TSB needs full load history)
        tsb = 5.0 + (readiness - 70) * 0.3
        ctl = 20.0
        atl = ctl - tsb

        today_str = today.isoformat()

    except Exception as e:
        st.error(f"連線或資料取得失敗：{e}")
        st.info("請確認 API Key 正確，且已在 Garmin Connect 建立。若持續失敗，可改用非官方庫或匯出 CSV。")
        readiness = 70
        tsb = 0.0
        ctl = 15.0
        atl = 15.0
        hrv_status = "未知"
        sleep_score = 65
        resting_hr = 58
        today_str = date.today().isoformat()

# Main layout
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("今日準備度")
    color = "#2ecc71" if readiness >= 75 else "#f39c12" if readiness >= 50 else "#e74c3c"
    st.markdown(f'<div class="readiness-score" style="color:{color}">{readiness}<span style="font-size:20px">/100</span></div>', unsafe_allow_html=True)
    status_text = "良好・可執行高強度" if readiness >= 75 else "中等・建議中低強度" if readiness >= 50 else "偏低・建議休息或恢復"
    st.markdown(f"**狀態：** {status_text}")
    st.caption(f"HRV 狀態：{hrv_status}　睡眠分數：{sleep_score}　靜息心率：{resting_hr} bpm")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("負荷平衡")
    st.metric("TSB (訓練壓力平衡)", f"{tsb:+.1f}", help="正值表示恢復良好，負值表示疲勞累積")
    st.caption(f"CTL ≈ {ctl:.1f}　ATL ≈ {atl:.1f}")
    if tsb > 5:
        st.success("負荷平衡良好，還有空間穩定增量。")
    elif tsb > -5:
        st.info("負荷適中。")
    else:
        st.warning("近期負荷偏高，建議安排恢復日。")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("準備度雷達")
    categories = ["速度", "耐力", "比賽適能", "訓練負荷", "恢復"]
    # Approximate values (in real app, compute from history)
    values = [
        min(100, 60 + (readiness - 70) * 0.5),
        min(100, 55 + tsb * 2),
        min(100, 50 + ctl),
        min(100, 100 - abs(tsb) * 3),
        readiness,
    ]
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        line_color="#3498db",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        height=320,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Bottom cards
st.markdown("### 關鍵指標")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("速度評分", f"{int(values[0])}/100")
with c2:
    st.metric("耐力評分", f"{int(values[1])}/100")
with c3:
    st.metric("比賽適能", f"{int(values[2])}/100")
with c4:
    st.metric("訓練負荷", f"{int(values[3])}/100")

st.markdown("---")
st.subheader("AI 今日建議")
if readiness >= 75 and tsb > 0:
    st.success("今天適合照課表或進行高強度／比賽配速跑。身體恢復良好。")
elif readiness >= 50:
    st.info("可進行中等強度訓練，或安排輕鬆跑。注意身體感覺。")
else:
    st.warning("建議以恢復跑或休息為主，讓身體充分恢復。")

st.caption(f"資料日期參考：{today_str}　此儀表板使用 Garmin 官方 Personal API，數據僅供個人參考。")

# Optional: show raw activity list if available
if api_key and "activities" in locals() and activities:
    with st.expander("近期活動（最近 30 筆）"):
        try:
            acts = activities if isinstance(activities, list) else activities.get("activities", activities.get("data", []))
            if acts:
                df = pd.DataFrame(acts)[["activityName", "startTimeLocal", "distance", "duration", "activityType"]].head(10)
                st.dataframe(df, use_container_width=True)
        except Exception:
            st.write("活動資料格式解析中…")
