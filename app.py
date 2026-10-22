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

st.set_page_config(page_title="跑步儀表板", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS — cleaner modern style
st.markdown("""
<style>
    .main { background-color: #f7f5f2; }
    .stApp { background-color: #f7f5f2; }
    h1, h2, h3 { color: #1a1a1a; font-weight: 600; }
    .metric-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 16px;
        border: 1px solid #eee;
    }
    .readiness-score {
        font-size: 52px;
        font-weight: 700;
        line-height: 1;
    }
    .stMetric { background: #fff; border-radius: 12px; padding: 12px; }
    div[data-testid="stSidebar"] { background-color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation + API key
with st.sidebar:
    st.markdown("### 跑步儀表板")
    st.caption(f"{date.today().isoformat()} · HRV")

    # Full navigation (still available when sidebar is opened)
    page_options = [
        "總覽 Overview",
        "訓練狀態",
        "訓練紀錄",
        "準備度分析",
        "長期趨勢",
        "訓練負荷",
        "心率與配速",
        "數據關係分析",
        "本週訓練",
        "計劃總覽",
        "訓練工具箱",
        "AI 教練",
        "設定",
    ]
    page = st.radio(
        "功能選單",
        page_options,
        index=page_options.index(st.session_state.get("page", "訓練狀態")),
        label_visibility="collapsed",
        key="sidebar_page",
    )
    st.session_state["page"] = page

    st.markdown("---")
    st.subheader("Garmin 連線")
    api_key = st.text_input(
        "Personal API Key",
        type="password",
        value=os.getenv("GARMIN_PERSONAL_API_KEY", ""),
        help="從 Garmin Connect → Personal API Token 取得",
    )
    if st.button("同步 Garmin", use_container_width=True):
        st.session_state["force_refresh"] = True
        st.rerun()

    st.markdown("---")
    with st.expander("如何取得 API Key？"):
        st.markdown("1. 登入 [Garmin Connect](https://connect.garmin.com)")
        st.markdown("2. 前往 [Personal API Token](https://connect.garmin.com/app/settings/personalApiToken)")
        st.markdown("3. 建立 Key 並複製貼上")
    st.caption("官方 Personal API · 僅讀取你自己的資料")

# ========== Top quick navigation (mobile friendly) ==========
quick_pages = ["訓練狀態", "本週訓練", "訓練紀錄", "準備度分析", "訓練負荷", "訓練工具箱"]
if "page" not in st.session_state:
    st.session_state["page"] = "訓練狀態"

st.markdown("""
<style>
.quick-nav button {
    margin-right: 6px;
    margin-bottom: 6px;
    border-radius: 20px !important;
    font-size: 14px !important;
    padding: 6px 14px !important;
}
</style>
""", unsafe_allow_html=True)

cols = st.columns(len(quick_pages))
for i, qp in enumerate(quick_pages):
    with cols[i]:
        if st.button(qp, key=f"quick_{qp}", use_container_width=True,
                     type="primary" if st.session_state["page"] == qp else "secondary"):
            st.session_state["page"] = qp
            st.rerun()

page = st.session_state["page"]
st.markdown("---")

# ========== Page routing ==========
if page == "訓練狀態":
    st.title("訓練狀態")
    st.caption("今日身體狀況與訓練負荷總覽")

    if not api_key:
        st.warning("請先在左側輸入 Garmin Personal API Key。")
        # Demo values
        readiness = 84
        tsb = 7.2
        status = "良好"
        advice = "今天適合照課表或進行高強度／比賽配速跑。"
    else:
        try:
            client = GarminPersonalClient(api_key)
            today = date.today()
            yesterday = today - timedelta(days=1)
            with st.spinner("正在同步訓練狀態..."):
                hrv_data = client.get_daily_hrv(today) or client.get_daily_hrv(yesterday)
                sleep_data = client.get_daily_sleep(today) or client.get_daily_sleep(yesterday)
                activities = client.search_activities(limit=30, start_date=(today - timedelta(days=30)).isoformat(), end_date=today.isoformat())

            # Reuse simple readiness logic
            def to_number(val, default=70):
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, dict):
                    for k in ("value", "score", "overall"):
                        if k in val and isinstance(val[k], (int, float)):
                            return float(val[k])
                return default

            hrv_raw = (hrv_data or {}).get("lastNightAvg") or (hrv_data or {}).get("weeklyAvg")
            hrv_val = to_number(hrv_raw, 0)
            sleep_raw = None
            if sleep_data:
                sleep_raw = (
                    sleep_data.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value")
                    or sleep_data.get("sleepScores", {}).get("overall")
                )
            sleep_val = to_number(sleep_raw, 70)
            hrv_factor = min(100, max(40, (hrv_val / 50) * 70)) if hrv_val else 70
            readiness = int(0.45 * hrv_factor + 0.35 * sleep_val + 0.2 * 75)
            readiness = max(1, min(100, readiness))
            tsb = 5.0 + (readiness - 70) * 0.3

            if readiness >= 75 and tsb > 0:
                status = "良好"
                advice = "今天適合照課表或進行高強度／比賽配速跑。身體恢復良好。"
            elif readiness >= 50:
                status = "中等"
                advice = "建議進行中低強度訓練或輕鬆跑。"
            else:
                status = "偏低"
                advice = "建議休息或安排恢復日。"

        except Exception as e:
            st.error(f"無法取得資料：{e}")
            readiness = 70
            tsb = 0.0
            status = "未知"
            advice = "請確認 API Key 或稍後再試。"

    # Display
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("今日準備度")
        color = "#2ecc71" if readiness >= 75 else "#f39c12" if readiness >= 50 else "#e74c3c"
        st.markdown(f'<div class="readiness-score" style="color:{color}">{readiness}<span style="font-size:20px">/100</span></div>', unsafe_allow_html=True)
        st.markdown(f"**狀態：** {status}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("訓練壓力平衡 (TSB)")
        st.metric("TSB", f"{tsb:+.1f}")
        if tsb > 5:
            st.success("負荷平衡良好")
        elif tsb > -5:
            st.info("負荷適中")
        else:
            st.warning("近期負荷偏高")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 今日建議")
    if readiness >= 75:
        st.success(advice)
    elif readiness >= 50:
        st.info(advice)
    else:
        st.warning(advice)

    st.caption("數據僅供個人參考。完整細節請至「準備度分析」與「訓練負荷」頁面查看。")
    st.stop()

elif page == "準備度分析":
    st.title("🏃 跑步準備度分析")
    st.caption("整合 Garmin 手錶資料 · 隨時查看身體狀況與訓練建議")
    # (existing readiness logic continues below)
elif page == "總覽 Overview":
    st.title("總覽 Overview")
    st.caption("本週重點與今日狀態")

    if not api_key:
        st.warning("請先輸入 API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        with st.spinner("載入總覽..."):
            activities = client.search_activities(limit=20, start_date=(today - timedelta(days=7)).isoformat(), end_date=today.isoformat())
        act_list = activities if isinstance(activities, list) else (activities or {}).get("activities") or []
        week_distance = sum((a.get("distance") or 0) / 1000 for a in act_list if isinstance(a, dict))
        week_time = sum((a.get("duration") or 0) / 60 for a in act_list if isinstance(a, dict))

        c1, c2, c3 = st.columns(3)
        c1.metric("本週距離", f"{week_distance:.1f} km")
        c2.metric("本週時間", f"{int(week_time)} 分")
        c3.metric("活動次數", len(act_list))

        st.markdown("### 最近活動")
        if act_list:
            for a in act_list[:5]:
                if isinstance(a, dict):
                    name = a.get("activityName") or "活動"
                    dist = (a.get("distance") or 0) / 1000
                    st.write(f"- **{name}** · {dist:.2f} km")
        else:
            st.info("本週尚無活動。")
    except Exception as e:
        st.error(f"載入失敗：{e}")
    st.stop()
elif page == "訓練紀錄":
    st.title("訓練紀錄")
    st.caption("最近的跑步與活動紀錄")

    if not api_key:
        st.warning("請先在左側輸入 Garmin Personal API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        with st.spinner("正在載入訓練紀錄..."):
            activities = client.search_activities(
                limit=20,
                start_date=(today - timedelta(days=90)).isoformat(),
                end_date=today.isoformat(),
            )

        # Normalize response (API may return list or dict with list)
        if isinstance(activities, dict):
            activity_list = activities.get("activities") or activities.get("data") or []
        elif isinstance(activities, list):
            activity_list = activities
        else:
            activity_list = []

        if not activity_list:
            st.info("目前沒有找到活動紀錄。請確認手錶已同步到 Garmin Connect。")
            st.stop()

        # Build a clean table
        rows = []
        for act in activity_list:
            if not isinstance(act, dict):
                continue
            start = act.get("startTimeLocal") or act.get("startTimeGMT") or ""
            date_str = start[:10] if start else ""
            name = act.get("activityName") or act.get("activityType", {}).get("typeKey") or "活動"
            distance_m = act.get("distance") or 0
            distance_km = round(distance_m / 1000, 2) if distance_m else 0
            duration_s = act.get("duration") or act.get("elapsedDuration") or 0
            minutes = int(duration_s // 60) if duration_s else 0
            avg_hr = act.get("averageHR") or act.get("averageHeartRate") or ""
            avg_speed = act.get("averageSpeed")  # m/s
            pace = ""
            if avg_speed and avg_speed > 0:
                pace_min_per_km = 1000 / (avg_speed * 60)
                pace = f"{int(pace_min_per_km)}:{int((pace_min_per_km % 1) * 60):02d}"
            rows.append({
                "日期": date_str,
                "活動": name,
                "距離 (km)": distance_km,
                "時間 (分)": minutes,
                "配速": pace or "—",
                "平均心率": avg_hr or "—",
            })

        if not rows:
            st.info("無法解析活動資料。")
            st.stop()

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "距離 (km)": st.column_config.NumberColumn(format="%.2f"),
                "時間 (分)": st.column_config.NumberColumn(format="%d"),
            },
        )

        # Summary metrics
        total_distance = df["距離 (km)"].sum()
        total_time = df["時間 (分)"].sum()
        run_count = len(df)
        col1, col2, col3 = st.columns(3)
        col1.metric("活動次數", run_count)
        col2.metric("總距離", f"{total_distance:.1f} km")
        col3.metric("總時間", f"{total_time} 分")

        st.success(f"已載入最近 {run_count} 筆活動（最多 180 天）。")

    except Exception as e:
        st.error(f"載入訓練紀錄失敗：{e}")
        st.info("請確認 API Key 正確，或稍後再試。")
    st.stop()
elif page == "長期趨勢":
    st.title("長期趨勢")
    st.caption("近 30 日活動距離趨勢")

    if not api_key:
        st.warning("請先輸入 API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        with st.spinner("載入趨勢..."):
            activities = client.search_activities(limit=30, start_date=(today - timedelta(days=21)).isoformat(), end_date=today.isoformat())
        act_list = activities if isinstance(activities, list) else (activities or {}).get("activities") or []
        daily = {}
        for a in act_list:
            if isinstance(a, dict):
                d = (a.get("startTimeLocal") or "")[:10]
                if d:
                    daily[d] = daily.get(d, 0) + (a.get("distance") or 0) / 1000
        if daily:
            df = pd.DataFrame(list(daily.items()), columns=["日期", "距離 (km)"]).sort_values("日期")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["日期"], y=df["距離 (km)"], mode="lines+markers", name="每日距離", line=dict(color="#3498db", width=2)))
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="日期", yaxis_title="距離 (km)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("近 30 日尚無足夠資料。")
    except Exception as e:
        st.error(f"載入失敗：{e}")
    st.stop()
elif page == "訓練負荷":
    st.title("訓練負荷")
    st.caption("CTL（長期負荷）· ATL（短期負荷）· TSB（訓練壓力平衡）")

    if not api_key:
        st.warning("請先在左側輸入 Garmin Personal API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        with st.spinner("正在計算訓練負荷..."):
            activities = client.search_activities(
                limit=30,
                start_date=(today - timedelta(days=60)).isoformat(),
                end_date=today.isoformat(),
            )

        # Normalize list
        if isinstance(activities, dict):
            activity_list = activities.get("activities") or activities.get("data") or []
        elif isinstance(activities, list):
            activity_list = activities
        else:
            activity_list = []

        # Build daily load (simple TRIMP-like: duration_min * avg_hr_factor)
        daily_load = {}
        for act in activity_list:
            if not isinstance(act, dict):
                continue
            start = act.get("startTimeLocal") or ""
            d = start[:10]
            if not d:
                continue
            duration_min = (act.get("duration") or 0) / 60
            avg_hr = act.get("averageHR") or act.get("averageHeartRate") or 140
            # Simple load proxy (higher HR & longer = higher load)
            load = duration_min * (avg_hr / 150)
            daily_load[d] = daily_load.get(d, 0) + load

        if not daily_load:
            st.info("目前沒有足夠的活動資料來計算訓練負荷。請確認手錶已同步。")
            st.stop()

        # Create full date range and fill zeros
        dates = pd.date_range(start=today - timedelta(days=90), end=today, freq="D")
        load_series = pd.Series(0.0, index=dates)
        for d_str, load in daily_load.items():
            try:
                dt = pd.to_datetime(d_str)
                if dt in load_series.index:
                    load_series[dt] = load
            except Exception:
                continue

        # CTL (42-day exponential), ATL (7-day exponential)
        # Using simple rolling mean as approximation (good enough for personal use)
        ctl = load_series.rolling(window=42, min_periods=7).mean().fillna(0)
        atl = load_series.rolling(window=7, min_periods=3).mean().fillna(0)
        tsb = ctl - atl

        current_ctl = float(ctl.iloc[-1])
        current_atl = float(atl.iloc[-1])
        current_tsb = float(tsb.iloc[-1])

        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("CTL（長期負荷）", f"{current_ctl:.1f}", help="約 42 日平均負荷，代表體能基礎")
        c2.metric("ATL（短期負荷）", f"{current_atl:.1f}", help="約 7 日平均負荷，代表近期疲勞")
        c3.metric("TSB（訓練壓力平衡）", f"{current_tsb:+.1f}", help="CTL - ATL，正值表示恢復良好")

        # Status message
        if current_tsb > 5:
            st.success("負荷平衡良好，還有空間穩定增量。")
        elif current_tsb > -5:
            st.info("負荷適中，可維持目前訓練節奏。")
        else:
            st.warning("近期負荷偏高，建議安排恢復或輕鬆日。")

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ctl.index, y=ctl, name="CTL（長期）", line=dict(color="#3498db", width=2)))
        fig.add_trace(go.Scatter(x=atl.index, y=atl, name="ATL（短期）", line=dict(color="#e74c3c", width=2)))
        fig.add_trace(go.Scatter(x=tsb.index, y=tsb, name="TSB", line=dict(color="#2ecc71", width=2, dash="dot")))
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="日期",
            yaxis_title="負荷指數",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption("負荷指數為根據活動時間與平均心率估算的相對值（非官方 TSS）。數值僅供個人參考與趨勢觀察。")

    except Exception as e:
        st.error(f"計算訓練負荷失敗：{e}")
        st.info("請確認 API Key 正確，或稍後再試。")
    st.stop()
elif page == "心率與配速":
    st.title("心率與配速")
    st.caption("近期活動的心率與配速")

    if not api_key:
        st.warning("請先輸入 API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        with st.spinner("載入資料..."):
            activities = client.search_activities(limit=30, start_date=(today - timedelta(days=60)).isoformat(), end_date=today.isoformat())
        act_list = activities if isinstance(activities, list) else (activities or {}).get("activities") or []
        rows = []
        for a in act_list:
            if not isinstance(a, dict):
                continue
            avg_hr = a.get("averageHR") or a.get("averageHeartRate")
            avg_speed = a.get("averageSpeed")
            pace = "—"
            if avg_speed and avg_speed > 0:
                p = 1000 / (avg_speed * 60)
                pace = f"{int(p)}:{int((p % 1)*60):02d}"
            rows.append({
                "日期": (a.get("startTimeLocal") or "")[:10],
                "活動": a.get("activityName") or "活動",
                "平均心率": avg_hr or "—",
                "配速": pace,
                "距離 (km)": round((a.get("distance") or 0)/1000, 2),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("尚無足夠活動資料。")
    except Exception as e:
        st.error(f"載入失敗：{e}")
    st.stop()
elif page == "數據關係分析":
    st.title("數據關係分析")
    st.caption("觀察心率、配速與距離的關係")

    if not api_key:
        st.warning("請先輸入 API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        with st.spinner("載入活動資料..."):
            activities = client.search_activities(limit=30, start_date=(today - timedelta(days=60)).isoformat(), end_date=today.isoformat())
        act_list = activities if isinstance(activities, list) else (activities or {}).get("activities") or []

        rows = []
        for a in act_list:
            if not isinstance(a, dict):
                continue
            dist = (a.get("distance") or 0) / 1000
            if dist < 1:
                continue
            avg_hr = a.get("averageHR") or a.get("averageHeartRate")
            avg_speed = a.get("averageSpeed")
            pace = None
            if avg_speed and avg_speed > 0:
                pace = 1000 / (avg_speed * 60)
            if avg_hr and pace:
                rows.append({
                    "距離 (km)": round(dist, 2),
                    "平均心率": avg_hr,
                    "配速 (分/km)": round(pace, 2),
                    "日期": (a.get("startTimeLocal") or "")[:10],
                })

        if not rows:
            st.info("尚無足夠的心率與配速資料可供分析。")
            st.stop()

        df = pd.DataFrame(rows)
        st.markdown("### 心率 vs 配速")
        fig = go.Figure(go.Scatter(
            x=df["配速 (分/km)"],
            y=df["平均心率"],
            mode="markers",
            marker=dict(size=10, color=df["距離 (km)"], colorscale="Blues", showscale=True, colorbar=dict(title="距離")),
            text=df["日期"],
            hovertemplate="配速: %{x:.2f}<br>心率: %{y}<br>%{text}<extra></extra>"
        ))
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="配速 (分/km)", yaxis_title="平均心率")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 活動摘要表")
        st.dataframe(df.sort_values("日期", ascending=False), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"載入失敗：{e}")
    st.stop()

elif page == "本週訓練":
    st.title("本週訓練")
    st.caption("本週活動與跑量趨勢")

    if not api_key:
        st.warning("請先輸入 API Key。")
        st.stop()

    try:
        client = GarminPersonalClient(api_key)
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        with st.spinner("載入本週資料..."):
            activities = client.search_activities(limit=20, start_date=monday.isoformat(), end_date=today.isoformat())
        act_list = activities if isinstance(activities, list) else (activities or {}).get("activities") or []

        # Daily volume this week
        daily_km = {}
        for a in act_list:
            if isinstance(a, dict):
                d = (a.get("startTimeLocal") or "")[:10]
                if d:
                    daily_km[d] = daily_km.get(d, 0) + (a.get("distance") or 0) / 1000

        total_km = sum(daily_km.values())
        st.metric("本週總距離", f"{total_km:.1f} km")

        if daily_km:
            df = pd.DataFrame(list(daily_km.items()), columns=["日期", "距離 (km)"]).sort_values("日期")
            # Use short date labels to avoid Plotly datetime parsing issues
            df["顯示日期"] = df["日期"].str[5:]  # MM-DD
            fig = go.Figure(go.Bar(
                x=df["顯示日期"],
                y=df["距離 (km)"],
                marker_color="#3498db",
                text=df["距離 (km)"].round(1),
                textposition="outside"
            ))
            fig.update_layout(
                height=340,
                margin=dict(l=20, r=20, t=30, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="日期",
                yaxis_title="距離 (km)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 活動明細")
        for a in act_list:
            if isinstance(a, dict):
                st.write(f"**{(a.get('startTimeLocal') or '')[:10]}** · {a.get('activityName') or '活動'} · {(a.get('distance') or 0)/1000:.2f} km")
        if not act_list:
            st.info("本週尚無活動紀錄。")
    except Exception as e:
        st.error(f"載入失敗：{e}")
    st.stop()

elif page == "計劃總覽":
    st.title("計劃總覽")
    st.info("訓練計劃功能開發中。之後可在此查看與管理週期計劃。")
    st.stop()

elif page == "訓練工具箱":
    st.title("訓練工具箱")

    st.markdown("### 配速計算器")
    distance = st.number_input("距離 (公里)", min_value=1.0, value=5.0, step=0.5)
    time_min = st.number_input("目標時間 (分鐘)", min_value=1.0, value=25.0, step=1.0)
    if distance > 0 and time_min > 0:
        pace = time_min / distance
        st.success(f"配速：{int(pace)}:{int((pace % 1)*60):02d} / 公里")

    st.markdown("---")
    st.markdown("### VDOT 估算（簡易版）")
    st.caption("根據近期最佳成績估算跑步能力（Jack Daniels 公式近似）")
    race_dist = st.selectbox("比賽距離", ["5 km", "10 km", "半程馬拉松", "全馬"])
    race_time = st.number_input("完賽時間 (分鐘)", min_value=10.0, value=25.0, step=1.0)
    dist_map = {"5 km": 5, "10 km": 10, "半程馬拉松": 21.0975, "全馬": 42.195}
    d = dist_map.get(race_dist, 5)
    if race_time > 0 and d > 0:
        # Velocity in meters per minute
        v = (d * 1000) / race_time
        # Jack Daniels VDOT approximation
        vdot = -4.60 + 0.182258 * v + 0.000104 * (v ** 2)
        vdot = max(20, min(85, vdot))
        st.metric("估算 VDOT", f"{vdot:.1f}")
        st.info("數值越高代表跑步能力越好。僅供個人參考，非官方精確計算。")

    st.markdown("---")
    st.markdown("### 心率區間建議（依年齡）")
    age = st.number_input("年齡", min_value=15, max_value=80, value=35, step=1)
    max_hr = 220 - age
    st.write(f"估計最大心率：{max_hr} bpm")
    zones = {
        "恢復 (50-60%)": (0.5, 0.6),
        "輕鬆 (60-70%)": (0.6, 0.7),
        "有氧 (70-80%)": (0.7, 0.8),
        "閾值 (80-90%)": (0.8, 0.9),
        "無氧 (90-100%)": (0.9, 1.0),
    }
    for name, (lo, hi) in zones.items():
        st.write(f"**{name}**：{int(max_hr*lo)} – {int(max_hr*hi)} bpm")
    st.stop()

elif page == "AI 教練":
    st.title("AI 教練")
    st.info("AI 教練功能開發中。之後將根據你的準備度與負荷提供個人化建議。")
    if st.button("取得今日建議（簡易版）"):
        st.success("建議維持穩定訓練，注意恢復。完整 AI 分析即將上線。")
    st.stop()

elif page == "設定":
    st.title("設定")
    st.markdown("### 目前設定")
    st.write(f"API Key：{'已設定' if api_key else '未設定'}")
    st.info("更多設定選項（顯示偏好、單位等）開發中。")
    st.stop()

# ========== Original readiness page logic continues ==========

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
