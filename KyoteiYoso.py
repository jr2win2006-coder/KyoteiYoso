import datetime
import time
import re
import os
import sys
from io import StringIO
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st

# アナライザーモジュールの安全なインポート
try:
    from KyoteiYoso_analyzer import FanDataLoader, parse_odds3t, calculate_capital_allocation
    fan_loader = FanDataLoader("fan2604.txt")
except Exception:
    try:
        import importlib.util
        script_dir = os.path.dirname(os.path.abspath(__file__))
        analyzer_path = os.path.join(script_dir, "KyoteiYoso_analyzer.py")
        if os.path.exists(analyzer_path):
            spec = importlib.util.spec_from_file_location("KyoteiYoso_analyzer", analyzer_path)
            analyzer_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(analyzer_mod)
            FanDataLoader = analyzer_mod.FanDataLoader
            parse_odds3t = analyzer_mod.parse_odds3t
            calculate_capital_allocation = analyzer_mod.calculate_capital_allocation
            fan_loader = FanDataLoader("fan2604.txt")
        else:
            fan_loader = None
            parse_odds3t = None
            calculate_capital_allocation = None
    except Exception:
        fan_loader = None
        parse_odds3t = None
        calculate_capital_allocation = None

# ==========================================
# 【初期値設定】デフォルトで選択する競艇場コード
# ==========================================
DEFAULT_STADIUM_CODE = "01"  # 桐生

# 全国の競艇場24か所のコードマスタ
STADIUMS = {
    "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島",
    "05": "多摩川", "06": "浜名湖", "07": "蒲郡", "08": "常滑",
    "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
    "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島",
    "17": "宮島", "18": "徳山", "19": "下関", "20": "若松",
    "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
}

# キャッスル式V6 コース別基本点数マスタ (全24競艇場 x 1~6コース)
CASTLE_COURSE_POINTS = {
    "01": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 桐生
    "02": {1: 8.5, 2: 8.0, 3: 7.5, 4: 7.0, 5: 5.5, 6: 5.0}, # 戸田
    "03": {1: 8.0, 2: 7.5, 3: 7.5, 4: 7.0, 5: 5.5, 6: 5.0}, # 江戸川
    "04": {1: 8.5, 2: 7.5, 3: 7.5, 4: 7.0, 5: 6.0, 6: 5.0}, # 平和島
    "05": {1: 9.0, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 多摩川
    "06": {1: 9.0, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 浜名湖
    "07": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 蒲郡
    "08": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 常滑
    "09": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 津
    "10": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 三国
    "11": {1: 9.0, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # びわこ
    "12": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 住之江
    "13": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 尼崎
    "14": {1: 9.0, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 鳴門
    "15": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 丸亀
    "16": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 児島
    "17": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 宮島
    "18": {1: 10.0, 2: 7.5, 3: 7.0, 4: 6.0, 5: 5.0, 6: 4.5},# 徳山
    "19": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 下関
    "20": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 若松
    "21": {1: 10.0, 2: 7.5, 3: 7.0, 4: 6.0, 5: 5.0, 6: 4.5},# 芦屋
    "22": {1: 9.0, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 福岡
    "23": {1: 9.5, 2: 7.5, 3: 7.0, 4: 6.5, 5: 5.5, 6: 5.0}, # 唐津
    "24": {1: 10.0, 2: 7.5, 3: 7.0, 4: 6.0, 5: 5.0, 6: 4.5} # 大村
}

PAGE_TYPES = {
    "🏰 キャッスル式V6予想": "castle_v6",
    "🎯 スコア買い目予想": "predict",
    "出走表（番組）": "racelist",
    "オッズ（3連単）": "odds3t",
    "直前情報": "beforeinfo",
    "レース結果": "raceresult",
    "【一括取得】すべての情報": "all"
}

def fetch_boatrace_data(page_type: str, jcd: str, rno: int, date_str: str):
    domain = "www" + "." + "boatrace" + "." + "jp"
    base_url = f"https://{domain}/owpc/pc/race/{page_type}"
    params = {"rno": rno, "jcd": jcd, "hd": date_str}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    }
    timeout_config = (5, 25)
    for attempt in range(2):
        try:
            time.sleep(1.0)
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout_config)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                time.sleep(1.5)
                continue
            else:
                st.error(f"通信エラーが発生しました ({page_type}): {e}")
                return None

def parse_racelist_info(soup):
    racers = {}
    if not soup:
        return racers
    links = soup.find_all("a", href=re.compile(r"toban=\d{4}"))
    toban_list = []
    for a in links:
        m = re.search(r"toban=(\d{4})", a["href"])
        if m:
            t = m.group(1)
            if t not in toban_list:
                toban_list.append(t)
    for i in range(1, 7):
        if i - 1 < len(toban_list):
            racers[i] = toban_list[i - 1]
        else:
            racers[i] = None
    return racers

def parse_beforeinfo_details(soup):
    details = {}
    if not soup:
        return details
    
    tds = soup.find_all(["td", "div"])
    tilts = {}
    tilt_list = []
    for td in tds:
        txt = td.get_text().strip()
        if re.match(r"^[-+]?[0-3]\.[05]$", txt):
            try:
                tilt_list.append(float(txt))
            except ValueError:
                pass
    if len(tilt_list) >= 6:
        for i in range(1, 7):
            tilts[i] = tilt_list[i - 1]
            
    ex_times = []
    for td in tds:
        txt = td.get_text().strip()
        if re.match(r"^[67]\.\d{2}$", txt):
            try:
                fval = float(txt)
                if 6.00 <= fval <= 7.80:
                    ex_times.append(fval)
            except ValueError:
                pass
    times = {}
    if len(ex_times) >= 6:
        for i in range(1, 7):
            times[i] = ex_times[i - 1]
            
    return {"tilts": tilts, "ex_times": times}

def calculate_castle_v6_prediction(jcd: str, rno: int, date_str: str):
    racelist_soup = fetch_boatrace_data("racelist", jcd, rno, date_str)
    before_soup = fetch_boatrace_data("beforeinfo", jcd, rno, date_str)
    odds_soup = fetch_boatrace_data("odds3t", jcd, rno, date_str)
    
    racers_map = parse_racelist_info(racelist_soup)
    before_info = parse_beforeinfo_details(before_soup)
    odds_dict = parse_odds3t(odds_soup) if parse_odds3t else {}
    
    c_pts = CASTLE_COURSE_POINTS.get(jcd, CASTLE_COURSE_POINTS["01"])
    
    warnings = []
    
    for b_no, tilt_val in before_info.get("tilts", {}).items():
        if tilt_val >= 2.0:
            warnings.append(f"⚠️ 【チルト注意】{b_no}号艇のチルト角度が {tilt_val}° に跳ね上げられています（波乱の可能性高）。")
            
    scores = {}
    details = {}
    
    for boat_no in range(1, 7):
        p1 = c_pts.get(boat_no, 5.0)
        toban = racers_map.get(boat_no)
        p2, p3, p4, p5, p6 = 3.0, 3.0, 3.0, 3.0, 0.0
        
        if toban and fan_loader:
            racer = fan_loader.get_racer(toban)
            if racer:
                c_fukushou = racer["courses"].get(boat_no, {}).get("fukushouritsu", 30.0)
                if c_fukushou >= 50.0: p2 = 5.0
                elif c_fukushou >= 35.0: p2 = 4.0
                elif c_fukushou >= 20.0: p2 = 3.0
                else: p2 = 2.0
                
                st_val = racer["courses"].get(boat_no, {}).get("avg_st", 0.17)
                if st_val <= 0.13: p3 = 5.0
                elif st_val <= 0.16: p3 = 4.0
                elif st_val <= 0.19: p3 = 3.0
                else: p3 = 2.0
                
                sr = racer.get("shouritsu", 5.0)
                if sr >= 6.5: p5 = 5.0
                elif sr >= 5.5: p5 = 4.0
                elif sr >= 4.5: p5 = 3.0
                else: p5 = 2.0
                
        total_p = p1 + p2 + p3 + p4 + p5 + p6
        scores[boat_no] = total_p
        
        details[boat_no] = {
            "toban": toban if toban else "未検出",
            "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6,
            "total": total_p
        }
        
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rank_boats = [b for b, s in ranked]
    top_score = ranked[0][1]
    
    top3_scores = [s for b, s in ranked[:3]]
    if len(top3_scores) >= 3 and (top3_scores[0] == top3_scores[1] == top3_scores[2]):
        warnings.append("⚠️ 【見送り推奨】合計点数のトップ（1位）に3名が同点で並んでいます（超難解混戦レース）。")
        
    r1, r2, r3, r4, r5, r6 = rank_boats
    
    va_lines = [f"{r1}-{r2}-{r3}", f"{r1}-{r2}-{r4}", f"{r1}-{r2}-{r5}", f"{r1}-{r2}-{r6}", f"{r1}-{r3}-{r2}", f"{r1}-{r3}-{r4}"]
    vb_lines = [f"{r2}-{r1}-{r3}", f"{r2}-{r1}-{r4}", f"{r2}-{r3}-{r1}", f"{r2}-{r3}-{r4}"]
    
    va_odds = [odds_dict.get(combo, 0.0) for combo in va_lines]
    vb_odds = [odds_dict.get(combo, 0.0) for combo in vb_lines]
    
    return {
        "ranked_boats": rank_boats,
        "details": details,
        "warnings": warnings,
        "va_lines": va_lines,
        "va_odds": va_odds,
        "vb_lines": vb_lines,
        "vb_odds": vb_odds,
        "parsed_racers": bool(racers_map),
        "total_odds_count": len(odds_dict)
    }

def calculate_score_prediction(jcd: str, rno: int, date_str: str):
    racelist_soup = fetch_boatrace_data("racelist", jcd, rno, date_str)
    before_soup = fetch_boatrace_data("beforeinfo", jcd, rno, date_str)
    odds_soup = fetch_boatrace_data("odds3t", jcd, rno, date_str)
    
    racers_map = parse_racelist_info(racelist_soup)
    before_info = parse_beforeinfo_details(before_soup)
    times_map = before_info.get("ex_times", {})
    odds_dict = parse_odds3t(odds_soup) if parse_odds3t else {}
    
    base_scores = {1: 100.0, 2: 75.0, 3: 60.0, 4: 50.0, 5: 40.0, 6: 30.0}
    time_bonuses = {i: 0.0 for i in range(1, 7)}
    if len(times_map) == 6:
        sorted_times = sorted(times_map.items(), key=lambda x: x[1])
        time_bonuses[sorted_times[0][0]] = 20.0
        time_bonuses[sorted_times[1][0]] = 10.0
        time_bonuses[sorted_times[2][0]] = 5.0

    scores = {}
    details = {}
    
    for boat_no in range(1, 7):
        b_score = base_scores[boat_no]
        t_bonus = time_bonuses[boat_no]
        toban = racers_map.get(boat_no)
        
        fan_bonus = 0.0
        fan_detail = "登番検出なし"
        
        if toban and fan_loader:
            fan_bonus, fan_detail = fan_loader.calculate_score_bonus(toban, boat_no)
            
        total_score = b_score + t_bonus + fan_bonus
        scores[boat_no] = total_score
        
        ex_time_str = f"{times_map[boat_no]:.2f}s" if boat_no in times_map else "データなし"
        toban_str = toban if toban else "未検出"
        details[boat_no] = {
            "toban": toban_str,
            "base_score": b_score,
            "fan_bonus": fan_bonus,
            "fan_detail": fan_detail,
            "ex_time": ex_time_str,
            "time_bonus": t_bonus,
            "total_score": total_score
        }
        
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rank_boats = [b for b, s in ranked]
    r1, r2, r3, r4, r5, r6 = rank_boats
    
    honmei = [f"{r1}-{r2}-{r3}", f"{r1}-{r2}-{r4}", f"{r1}-{r3}-{r2}", f"{r1}-{r3}-{r4}"]
    taikou = [f"{r2}-{r1}-{r3}", f"{r2}-{r1}-{r4}", f"{r2}-{r3}-{r1}", f"{r2}-{r3}-{r4}"]
    oana   = [f"{r3}-{r1}-{r2}", f"{r3}-{r1}-{r4}", f"{r4}-{r1}-{r2}", f"{r4}-{r1}-{r3}"]
    
    honmei_odds = [odds_dict.get(combo, 0.0) for combo in honmei]
    
    return {
        "ranked_boats": rank_boats,
        "details": details,
        "honmei": honmei,
        "honmei_odds": honmei_odds,
        "taikou": taikou,
        "oana": oana,
        "parsed_racers": bool(racers_map),
        "total_odds_count": len(odds_dict)
    }

def parse_and_display_tables(soup, title_label: str):
    if not soup:
        return
    try:
        html_str = str(soup)
        try:
            tables = pd.read_html(StringIO(html_str), flavor='lxml')
        except Exception:
            try:
                tables = pd.read_html(StringIO(html_str), flavor='html5lib')
            except Exception:
                tables = pd.read_html(StringIO(html_str))
        
        if tables:
            st.success(f"{title_label} データ取得成功（検出テーブル数: {len(tables)}）")
            for idx, df in enumerate(tables):
                st.subheader(f"■ {title_label} - テーブル {idx + 1}")
                st.dataframe(df, use_container_width=True)
        else:
            st.warning(f"{title_label}: 該当ページのテーブルデータが存在しません（未開催・未更新の可能性があります）。")
    except ValueError:
        st.warning(f"{title_label}: ページ内に解析可能なテーブル構造が見つかりませんでした。")
    except Exception as e:
        st.error(f"{title_label}: データ解析中にエラーが発生しました: {e}")

# Streamlit 画面構成
st.set_page_config(page_title="KyoteiYoso - 競艇予想システム", layout="wide")
st.title("🚤 KyoteiYoso 競艇スクレイピング＆予想システム")

col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 2])

with col1:
    selected_date = st.date_input(
        "① 年月日を選択",
        value=datetime.date(2026, 10, 11)
    )
    date_str = selected_date.strftime("%Y%m%d")

with col2:
    stadium_options = [f"{code} : {name}" for code, name in STADIUMS.items()]
    default_index = 0
    for idx, (code, name) in enumerate(STADIUMS.items()):
        if code == DEFAULT_STADIUM_CODE:
            default_index = idx
            break
            
    selected_stadium = st.selectbox("② 競艇場を選択", stadium_options, index=default_index)
    jcd_code = selected_stadium.split(" : ")[0]

with col3:
    race_options = [f"{r}R" for r in range(1, 13)]
    selected_race = st.selectbox("③ レース番号を選択", race_options)
    rno = int(selected_race.replace("R", ""))

with col4:
    selected_info_label = st.selectbox("④ 取得情報を選択", list(PAGE_TYPES.keys()))
    selected_info_type = PAGE_TYPES[selected_info_label]

with col5:
    total_budget = st.number_input("⑤ 資金配分予算（円）", min_value=1000, max_value=1000000, value=10000, step=1000)

if "cached_data" not in st.session_state:
    st.session_state["cached_data"] = None
if "cached_params" not in st.session_state:
    st.session_state["cached_params"] = None

if st.button("データを取得", type="primary"):
    with st.spinner("データを処理・取得中..."):
        if selected_info_type == "castle_v6":
            res = calculate_castle_v6_prediction(jcd_code, rno, date_str)
            st.session_state["cached_data"] = res
            st.session_state["cached_params"] = (jcd_code, rno, date_str, selected_info_type, selected_info_label)
        elif selected_info_type == "predict":
            res = calculate_score_prediction(jcd_code, rno, date_str)
            st.session_state["cached_data"] = res
            st.session_state["cached_params"] = (jcd_code, rno, date_str, selected_info_type, selected_info_label)
        elif selected_info_type == "all":
            tab_soups = {
                "castle": calculate_castle_v6_prediction(jcd_code, rno, date_str),
                "racelist": fetch_boatrace_data("racelist", jcd_code, rno, date_str),
                "odds3t": fetch_boatrace_data("odds3t", jcd_code, rno, date_str),
                "beforeinfo": fetch_boatrace_data("beforeinfo", jcd_code, rno, date_str),
                "raceresult": fetch_boatrace_data("raceresult", jcd_code, rno, date_str)
            }
            st.session_state["cached_data"] = tab_soups
            st.session_state["cached_params"] = (jcd_code, rno, date_str, selected_info_type, selected_info_label)
        else:
            soup = fetch_boatrace_data(selected_info_type, jcd_code, rno, date_str)
            st.session_state["cached_data"] = soup
            st.session_state["cached_params"] = (jcd_code, rno, date_str, selected_info_type, selected_info_label)

if st.session_state.get("cached_data") is not None:
    c_jcd, c_rno, c_date_str, c_type, c_label = st.session_state["cached_params"]
    date_display = f"{c_date_str[:4]}/{c_date_str[4:6]}/{c_date_str[6:]}"
    st.markdown("---")
    st.write(f"【表示中データ】 日付: **{date_display}** | 競艇場: **{STADIUMS.get(c_jcd, c_jcd)} ({c_jcd})** | レース: **{c_rno}R** | モード: **{c_label}**")
    
    res = st.session_state["cached_data"]
    
    if c_type == "castle_v6":
        st.subheader("🏰 【キャッスル式V6作戦】 予想＆オッズ資金分配")
        st.caption(f"オッズ解析状態: 取得総件数 {res.get('total_odds_count', 0)} / 120点")
        
        if res.get("warnings"):
            for w in res["warnings"]:
                st.warning(w)
                
        col_va, col_vb = st.columns(2)
        with col_va:
            st.success("■ VA線（本命ライン・6点）")
            for c, o in zip(res["va_lines"], res["va_odds"]):
                o_str = f"{o:.1f}倍" if o > 0 else "--- 倍"
                st.write(f"👉 **{c}** (オッズ: **{o_str}**)")
                
        with col_vb:
            st.info("■ VB線（穴目ライン・4点）")
            for c, o in zip(res["vb_lines"], res["vb_odds"]):
                o_str = f"{o:.1f}倍" if o > 0 else "--- 倍"
                st.write(f"👉 **{c}** (オッズ: **{o_str}**)")
                
        st.markdown("---")
        st.subheader("💰 資金分配（払戻均等化計算）")
        
        if calculate_capital_allocation and res.get("va_odds"):
            alloc_res = calculate_capital_allocation(res["va_odds"], total_budget=total_budget)
            st.write(f"📊 **VA線 合成オッズ**: **{alloc_res['synthetic_odds']:.2f}倍** | **目標払戻額**: **約 {int(alloc_res['target_payout']):,} 円** (設定予算: **{total_budget:,} 円**)")
            
            table_alloc = []
            for combo, o, a in zip(res["va_lines"], res["va_odds"], alloc_res["allocations"]):
                table_alloc.append({
                    "買い目": combo,
                    "現在オッズ": f"{o:.1f}倍" if o > 0 else "---",
                    "推奨購入金額": f"{a['stake']:,} 円",
                    "的中時払戻金": f"{int(a['expected_payout']):,} 円",
                    "回収率": f"{a['return_rate']:.1f}%"
                })
            st.dataframe(pd.DataFrame(table_alloc), use_container_width=True)
            
        st.markdown("---")
        st.subheader("📊 キャッスルV6 6大要素採点明細")
        
        table_score = []
        symbols = ["◎ (1位)", "○ (2位)", "▲ (3位)", "△ (4位)", "☆ (5位)", "消 (6位)"]
        for rank_idx, b_no in enumerate(res["ranked_boats"]):
            d = res["details"][b_no]
            table_score.append({
                "評価": symbols[rank_idx],
                "艇番": f"{b_no}号艇",
                "登番": d["toban"],
                "合計点数": f"{d['total']:.1f} pt",
                "①コース基本": f"{d['p1']:.1f}",
                "②コース複勝率": f"{d['p2']:.1f}",
                "③平均ST": f"{d['p3']:.1f}",
                "④当地複勝": f"{d['p4']:.1f}",
                "⑤最近勝率": f"{d['p5']:.1f}",
                "⑥体重補正": f"{d['p6']:.1f}"
            })
        st.dataframe(pd.DataFrame(table_score), use_container_width=True)
        
    elif c_type == "predict":
        st.subheader("🎯 【データ＆理論】3連単買い目予想")
        st.caption(f"オッズ解析状態: 取得総件数 {res.get('total_odds_count', 0)} / 120点")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.success("■ 本命（堅調・4点）")
            for item, o in zip(res["honmei"], res["honmei_odds"]):
                o_str = f"({o:.1f}倍)" if o > 0 else "(---)"
                st.write(f"👉 **{item}** {o_str}")
        with col_b:
            st.info("■ 対抗・抑え（4点）")
            for item in res["taikou"]:
                st.write(f"👉 **{item}**")
        with col_c:
            st.warning("■ 大穴・高配当（4点）")
            for item in res["oana"]:
                st.write(f"👉 **{item}**")
                
        st.markdown("---")
        st.subheader("💰 本命買い目 資金分配（払戻均等化計算）")
        
        if calculate_capital_allocation and res.get("honmei_odds"):
            alloc_res = calculate_capital_allocation(res["honmei_odds"], total_budget=total_budget)
            st.write(f"📊 **本命合成オッズ**: **{alloc_res['synthetic_odds']:.2f}倍** | **目標払戻額**: **約 {int(alloc_res['target_payout']):,} 円** (設定予算: **{total_budget:,} 円**)")
            
            table_alloc = []
            for combo, o, a in zip(res["honmei"], res["honmei_odds"], alloc_res["allocations"]):
                table_alloc.append({
                    "買い目": combo,
                    "現在オッズ": f"{o:.1f}倍" if o > 0 else "---",
                    "推奨購入金額": f"{a['stake']:,} 円",
                    "的中時払戻金": f"{int(a['expected_payout']):,} 円",
                    "回収率": f"{a['return_rate']:.1f}%"
                })
            st.dataframe(pd.DataFrame(table_alloc), use_container_width=True)
            
        st.markdown("---")
        st.subheader("📊 6艇別 予想評価スコア明細")
        
        table_data = []
        symbols = ["◎ (軸)", "○ (対抗)", "▲ (単穴)", "△ (連下)", "☆ (注意)", "消"]
        for rank_idx, b_no in enumerate(res["ranked_boats"]):
            d = res["details"][b_no]
            table_data.append({
                "評価": symbols[rank_idx],
                "艇番": f"{b_no}号艇",
                "登番": d["toban"],
                "総合スコア": f"{d['total_score']:.1f} pts",
                "枠番基礎点": f"{d['base_score']:.1f}",
                "ファン手帳加点": f"+{d['fan_bonus']:.1f}",
                "ファン手帳詳細": d["fan_detail"],
                "展示タイム": d["ex_time"],
                "展示加点": f"+{d['time_bonus']:.1f}"
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
        
        if not res["parsed_racers"]:
            st.info("💡 出走表から登番が検出できなかったため、枠番ベース点中心の評価となっています（未開催またはWebページ形式変更の可能性）。")

    elif c_type == "all":
        tab0, tab1, tab2, tab3, tab4 = st.tabs(["🏰 キャッスルV6予想", "出走表（番組）", "オッズ（3連単）", "直前情報", "レース結果"])
        
        with tab0:
            c_res = res["castle"]
            st.subheader("🏰【キャッスル式V6作戦】 予想＆オッズ")
            col_va, col_vb = st.columns(2)
            with col_va:
                st.success("■ VA線（本命・6点）")
                for c, o in zip(c_res["va_lines"], c_res["va_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "---"
                    st.write(f"👉 **{c}** ({o_str})")
            with col_vb:
                st.info("■ VB線（穴目・4点）")
                for c, o in zip(c_res["vb_lines"], c_res["vb_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "---"
                    st.write(f"👉 **{c}** ({o_str})")
                    
            if calculate_capital_allocation and c_res.get("va_odds"):
                alloc_res = calculate_capital_allocation(c_res["va_odds"], total_budget=total_budget)
                st.write(f"📊 **VA線 合成オッズ**: **{alloc_res['synthetic_odds']:.2f}倍** | **目標払戻額**: **約 {int(alloc_res['target_payout']):,} 円** (設定予算: **{total_budget:,} 円**)")
                table_alloc = []
                for combo, o, a in zip(c_res["va_lines"], c_res["va_odds"], alloc_res["allocations"]):
                    table_alloc.append({
                        "買い目": combo,
                        "現在オッズ": f"{o:.1f}倍" if o > 0 else "---",
                        "推奨購入金額": f"{a['stake']:,} 円",
                        "的中時払戻金": f"{int(a['expected_payout']):,} 円",
                        "回収率": f"{a['return_rate']:.1f}%"
                    })
                st.dataframe(pd.DataFrame(table_alloc), use_container_width=True)
        
        with tab1:
            parse_and_display_tables(res["racelist"], "出走表")
        with tab2:
            parse_and_display_tables(res["odds3t"], "オッズ")
        with tab3:
            parse_and_display_tables(res["beforeinfo"], "直前情報")
        with tab4:
            parse_and_display_tables(res["raceresult"], "レース結果")
            
    else:
        parse_and_display_tables(res, c_label)
