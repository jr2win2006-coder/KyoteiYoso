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
    from KyoteiYoso_analyzer import (
        FanDataLoader, parse_odds3t, calculate_capital_allocation,
        VENUE_MASTERS, generate_suji_recommendations, generate_venue_and_maxim_alerts,
        detect_hidden_a
    )
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
            VENUE_MASTERS = getattr(analyzer_mod, "VENUE_MASTERS", {})
            generate_suji_recommendations = getattr(analyzer_mod, "generate_suji_recommendations", None)
            generate_venue_and_maxim_alerts = getattr(analyzer_mod, "generate_venue_and_maxim_alerts", None)
            detect_hidden_a = getattr(analyzer_mod, "detect_hidden_a", None)
            fan_loader = FanDataLoader("fan2604.txt")
        else:
            fan_loader = None
            parse_odds3t = None
            calculate_capital_allocation = None
            VENUE_MASTERS = {}
            generate_suji_recommendations = None
            generate_venue_and_maxim_alerts = None
            detect_hidden_a = None
    except Exception:
        fan_loader = None
        parse_odds3t = None
        calculate_capital_allocation = None
        VENUE_MASTERS = {}
        generate_suji_recommendations = None
        generate_venue_and_maxim_alerts = None
        detect_hidden_a = None

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

# ==========================================
# 【スマートキャッシュ付き データ取得関数】
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boatrace_html(page_type: str, jcd: str, rno: int, date_str: str) -> str:
    """
    boatrace.jpからHTML文字列を取得し、30分間メモリキャッシュする関数
    同じレース情報であれば相手サーバーへアクセスせずキャッシュから即返却します
    """
    domain = "www.boatrace.jp"
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
            return response.text
        except requests.exceptions.RequestException:
            if attempt == 0:
                time.sleep(1.5)
                continue
            else:
                return ""

def fetch_boatrace_data(page_type: str, jcd: str, rno: int, date_str: str):
    """
    キャッシュされたHTML文字列をBeautifulSoupオブジェクトに変換して返却
    """
    html_text = fetch_boatrace_html(page_type, jcd, rno, date_str)
    if html_text:
        return BeautifulSoup(html_text, "html.parser")
    else:
        st.error(f"通信エラーが発生しました ({page_type})")
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

def calculate_castle_v6_prediction(jcd: str, rno: int, date_str: str, params: dict = None):
    if params is None:
        params = {"ex_top_bonus": 15.0, "in_weak_winrate": 4.5, "in_weak_penalty": -3.0, "hidden_a_bonus": 5.0, "suji_outer_ext": True}
        
    racelist_soup = fetch_boatrace_data("racelist", jcd, rno, date_str)
    before_soup = fetch_boatrace_data("beforeinfo", jcd, rno, date_str)
    odds_soup = fetch_boatrace_data("odds3t", jcd, rno, date_str)
    
    racers_map = parse_racelist_info(racelist_soup)
    before_info = parse_beforeinfo_details(before_soup)
    odds_dict = parse_odds3t(odds_soup) if parse_odds3t else {}
    
    c_pts = CASTLE_COURSE_POINTS.get(jcd, CASTLE_COURSE_POINTS["01"])
    
    scores = {}
    details = {}
    
    # パラメータ抽出
    ex_top_bonus = params.get("ex_top_bonus", 15.0)
    in_weak_winrate = params.get("in_weak_winrate", 4.5)
    in_weak_penalty = params.get("in_weak_penalty", -3.0)
    hidden_a_bonus = params.get("hidden_a_bonus", 5.0)
    
    # 展示タイム解析
    ex_times = before_info.get("ex_times", {})
    valid_ex = {b: t for b, t in ex_times.items() if t > 0}
    ex_top_boat = min(valid_ex, key=valid_ex.get) if valid_ex else None
    
    for boat_no in range(1, 7):
        p1 = c_pts.get(boat_no, 5.0)
        toban = racers_map.get(boat_no)
        p2, p3, p4, p5, p6 = 3.0, 3.0, 3.0, 3.0, 0.0
        
        p_ex = 0.0
        p_in_pen = 0.0
        p_hidden = 0.0
        
        # 展示最速艇ボーナス
        if ex_top_boat and boat_no == ex_top_boat:
            p_ex = ex_top_bonus
            
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
                
                # イン飛び減点判定 (1号艇)
                if boat_no == 1:
                    if sr < in_weak_winrate:
                        p_in_pen = in_weak_penalty
                        
                # 隠れA級判定
                kyu = racer.get("kyu", "B1")
                if detect_hidden_a and boat_no in [2, 3, 4]:
                    is_h, _ = detect_hidden_a(toban, kyu, sr)
                    if is_h:
                        p_hidden = hidden_a_bonus
                
        total_p = p1 + p2 + p3 + p4 + p5 + p6 + p_ex + p_in_pen + p_hidden
        scores[boat_no] = total_p
        
        details[boat_no] = {
            "toban": toban if toban else "未検出",
            "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6,
            "p_ex": p_ex, "p_in_pen": p_in_pen, "p_hidden": p_hidden,
            "total": total_p
        }
        
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rank_boats = [b for b, s in ranked]
    r1, r2, r3, r4, r5, r6 = rank_boats
    
    va_lines = [f"{r1}-{r2}-{r3}", f"{r1}-{r2}-{r4}", f"{r1}-{r2}-{r5}", f"{r1}-{r2}-{r6}", f"{r1}-{r3}-{r2}", f"{r1}-{r3}-{r4}"]
    vb_lines = [f"{r2}-{r1}-{r3}", f"{r2}-{r1}-{r4}", f"{r2}-{r3}-{r1}", f"{r2}-{r3}-{r4}"]
    
    suji_lines, suji_expl = generate_suji_recommendations(r1, r2, r3, r4, r5, r6, jcd, rno, suji_outer_ext=params.get("suji_outer_ext", True)) if generate_suji_recommendations else ([], [])
    alerts = generate_venue_and_maxim_alerts(jcd, rno, racers_map, before_info, fan_loader, rank_boats) if generate_venue_and_maxim_alerts else []
    
    top3_scores = [s for b, s in ranked[:3]]
    if len(top3_scores) >= 3 and (top3_scores[0] == top3_scores[1] == top3_scores[2]):
        alerts.insert(0, "⚠️ 【見送り推奨】合計点数のトップ（1位）に3名が同点で並んでいます（超難解混戦レース）。")
        
    return {
        "mode": "castle_v6",
        "ranked_boats": rank_boats,
        "details": details,
        "alerts": alerts,
        "va_lines": va_lines,
        "va_odds": [odds_dict.get(c, 0.0) for c in va_lines],
        "vb_lines": vb_lines,
        "vb_odds": [odds_dict.get(c, 0.0) for c in vb_lines],
        "suji_lines": suji_lines,
        "suji_odds": [odds_dict.get(c, 0.0) for c in suji_lines],
        "suji_expl": suji_expl,
        "parsed_racers": bool(racers_map),
        "total_odds_count": len(odds_dict)
    }

def calculate_score_prediction(jcd: str, rno: int, date_str: str, params: dict = None):
    if params is None:
        params = {"ex_top_bonus": 15.0, "in_weak_winrate": 4.5, "in_weak_penalty": -3.0, "hidden_a_bonus": 5.0, "suji_outer_ext": True}

    racelist_soup = fetch_boatrace_data("racelist", jcd, rno, date_str)
    before_soup = fetch_boatrace_data("beforeinfo", jcd, rno, date_str)
    odds_soup = fetch_boatrace_data("odds3t", jcd, rno, date_str)
    
    racers_map = parse_racelist_info(racelist_soup)
    before_info = parse_beforeinfo_details(before_soup)
    odds_dict = parse_odds3t(odds_soup) if parse_odds3t else {}
    
    c_pts = CASTLE_COURSE_POINTS.get(jcd, CASTLE_COURSE_POINTS["01"])
    
    scores = {}
    details = {}
    
    ex_top_bonus = params.get("ex_top_bonus", 15.0)
    in_weak_winrate = params.get("in_weak_winrate", 4.5)
    in_weak_penalty = params.get("in_weak_penalty", -3.0)
    hidden_a_bonus = params.get("hidden_a_bonus", 5.0)

    ex_times = before_info.get("ex_times", {})
    valid_ex = {b: t for b, t in ex_times.items() if t > 0}
    ex_top_boat = min(valid_ex, key=valid_ex.get) if valid_ex else None
    
    for boat_no in range(1, 7):
        p1 = c_pts.get(boat_no, 5.0)
        toban = racers_map.get(boat_no)
        p2, p3, p4, p5, p6 = 3.0, 3.0, 3.0, 3.0, 0.0
        
        p_ex = 0.0
        p_in_pen = 0.0
        p_hidden = 0.0

        if ex_top_boat and boat_no == ex_top_boat:
            p_ex = ex_top_bonus
            
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

                if boat_no == 1:
                    if sr < in_weak_winrate:
                        p_in_pen = in_weak_penalty
                        
                kyu = racer.get("kyu", "B1")
                if detect_hidden_a and boat_no in [2, 3, 4]:
                    is_h, _ = detect_hidden_a(toban, kyu, sr)
                    if is_h:
                        p_hidden = hidden_a_bonus
                
        total_p = p1 + p2 + p3 + p4 + p5 + p6 + p_ex + p_in_pen + p_hidden
        scores[boat_no] = total_p
        
        details[boat_no] = {
            "toban": toban if toban else "未検出",
            "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6,
            "p_ex": p_ex, "p_in_pen": p_in_pen, "p_hidden": p_hidden,
            "total": total_p
        }
        
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rank_boats = [b for b, s in ranked]
    r1, r2, r3, r4, r5, r6 = rank_boats
    
    honmei_lines = [f"{r1}-{r2}-{r3}", f"{r1}-{r2}-{r4}", f"{r1}-{r3}-{r2}", f"{r1}-{r3}-{r4}"]
    taikou_lines = [f"{r2}-{r1}-{r3}", f"{r2}-{r1}-{r4}", f"{r2}-{r3}-{r1}", f"{r2}-{r3}-{r4}"]
    oana_lines = [f"{r3}-{r1}-{r2}", f"{r3}-{r2}-{r1}", f"{r4}-{r1}-{r2}", f"{r4}-{r2}-{r1}"]
    
    suji_lines, suji_expl = generate_suji_recommendations(r1, r2, r3, r4, r5, r6, jcd, rno, suji_outer_ext=params.get("suji_outer_ext", True)) if generate_suji_recommendations else ([], [])
    alerts = generate_venue_and_maxim_alerts(jcd, rno, racers_map, before_info, fan_loader, rank_boats) if generate_venue_and_maxim_alerts else []
    
    return {
        "mode": "predict",
        "ranked_boats": rank_boats,
        "details": details,
        "alerts": alerts,
        "honmei_lines": honmei_lines,
        "honmei_odds": [odds_dict.get(c, 0.0) for c in honmei_lines],
        "taikou_lines": taikou_lines,
        "taikou_odds": [odds_dict.get(c, 0.0) for c in taikou_lines],
        "oana_lines": oana_lines,
        "oana_odds": [odds_dict.get(c, 0.0) for c in oana_lines],
        "suji_lines": suji_lines,
        "suji_odds": [odds_dict.get(c, 0.0) for c in suji_lines],
        "suji_expl": suji_expl,
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
st.set_page_config(page_title="KyoteiYoso 10/14版 - 競艇キャリブレーション済予想システム", layout="wide")
st.title("🚤 KyoteiYoso 競艇スクレイピング＆予想・格言スジ買いシステム")
st.caption("✨ 10/12・10/13キャリブレーション完了 ＆ 10/14最新番組・fan2604.txt完全対応版")

st.write("条件を入力して「データを取得」ボタンを押してください。データ取得後も予算金額はリアルタイムで自由に変更可能です。")

# 5列構成のトップフォーム（⑤資金配分予算の事前設定）
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    selected_date = st.date_input("① 年月日を選択", value=datetime.date(2026, 10, 14))
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
    total_budget = st.number_input("⑤ 資金配分予算（円）", min_value=1000, max_value=500000, value=10000, step=1000)

# ⚙️ 調整パラメータ設定フォーム（アコーディオン形式）
with st.expander("⚙️ 予想調整パラメータ設定（10/12・10/13 キャリブレーション最適化済み）", expanded=False):
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        ex_top_bonus = st.number_input(
            "① 展示最速艇 加点ボーナス (pt)",
            min_value=0.0, max_value=30.0, value=15.0, step=1.0,
            help="直前展示タイムが一番時計（最速）の艇に与える加点スコアです。値を大きくすると、直線伸び足が良いセンター・カド艇の直撃まくり・まくり差しを狙う買い目が優先されます。"
        )
    with col_p2:
        in_weak_winrate = st.number_input(
            "② 1号艇イン飛び判定 (当地勝率)",
            min_value=0.0, max_value=8.0, value=4.5, step=0.1,
            help="1号艇の当地勝率がこの閾値を下回る場合、イン逃げ不発（イン飛び）の波乱レースと判定します。"
        )
        in_weak_penalty = st.number_input(
            "   1号艇弱体化 減点 (pt)",
            min_value=-15.0, max_value=0.0, value=-3.0, step=0.5,
            help="イン飛び判定時に1号艇に適用する減点スコアです。マイナス幅を大きくすると、本命（1頭）から穴目（2〜4頭のVB線・格言スジ）へ買い目がシフトします。"
        )
    with col_p3:
        hidden_a_bonus = st.number_input(
            "③ 隠れA級ベテラン ボーナス (pt)",
            min_value=0.0, max_value=15.0, value=5.0, step=1.0,
            help="登録番号3000〜4000番台でB1/B2級に降格しているが実力を保持しているベテラン選手（隠れA級）への加点スコアです。2〜4コース配置時の差し抜け中穴を拾い上げます。"
        )
    with col_p4:
        suji_outer_ext = st.checkbox(
            "④ 外枠連動（5・6コース）スジ買い拡張",
            value=True,
            help="カドまくり（3・4コース頭）発生時に、展開に恵まれて外枠5・6号艇が雪崩れ込む高配当スジ買い目（4-5, 4-6等）を追加生成するか選択します。"
        )

params_dict = {
    "ex_top_bonus": ex_top_bonus,
    "in_weak_winrate": in_weak_winrate,
    "in_weak_penalty": in_weak_penalty,
    "hidden_a_bonus": hidden_a_bonus,
    "suji_outer_ext": suji_outer_ext
}

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    btn_fetch = st.button("データを取得 / パラメータ適用再計算", type="primary", use_container_width=True)
with col_btn2:
    if st.button("🔄 キャッシュクリア", use_container_width=True):
        st.cache_data.clear()
        st.success("キャッシュをクリアしました！次回は最新WEBデータを取得します。")

if btn_fetch:
    date_display = selected_date.strftime('%Y/%m/%d')
    st.session_state['fetch_params'] = {
        "date_display": date_display,
        "stadium_name": STADIUMS[jcd_code],
        "jcd_code": jcd_code,
        "rno": rno,
        "info_label": selected_info_label,
        "info_type": selected_info_type,
        "date_str": date_str,
        "params": params_dict
    }
    
    with st.spinner("データを処理・計算中..."):
        if selected_info_type == "castle_v6":
            st.session_state['race_result'] = calculate_castle_v6_prediction(jcd_code, rno, date_str, params=params_dict)
        elif selected_info_type == "predict":
            st.session_state['race_result'] = calculate_score_prediction(jcd_code, rno, date_str, params=params_dict)
        elif selected_info_type == "all":
            st.session_state['race_result'] = {"mode": "all"}
        else:
            soup = fetch_boatrace_data(selected_info_type, jcd_code, rno, date_str)
            st.session_state['race_result'] = {"mode": "single_table", "soup": soup}

# 結果のレンダリング（セッション状態から読み出し）
if 'fetch_params' in st.session_state and 'race_result' in st.session_state:
    st.markdown("---")
    fp = st.session_state['fetch_params']
    res = st.session_state['race_result']
    
    st.write(f"【検索条件】 日付: **{fp['date_display']}** | 競艇場: **{fp['stadium_name']} ({fp['jcd_code']})** | レース: **{fp['rno']}R** | モード: **{fp['info_label']}**")
    
    mode = res.get("mode")
    
    if mode in ["castle_v6", "predict"]:
        # 1. 競艇格言・場別ローカルルール・番組マン注意アラート
        alerts = res.get("alerts", [])
        if alerts:
            st.subheader("💡 競艇格言・場別ローカルルール・番組マン注意アラート")
            for a in alerts:
                if "⚠️" in a:
                    st.warning(a)
                else:
                    st.info(a)
                    
        # 2. 予想買い目表示
        if mode == "castle_v6":
            st.subheader("🏰 【キャッスル式V6作戦】 予想買い目")
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
            target_odds = res["va_odds"]
            target_lines = res["va_lines"]
            
        else: # predict
            st.subheader("🎯 【スコア買い目予想】 本命・対抗・大穴")
            col1_p, col2_p, col3_p = st.columns(3)
            with col1_p:
                st.success("■ 本命買い目（4点）")
                for c, o in zip(res["honmei_lines"], res["honmei_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "--- 倍"
                    st.write(f"👉 **{c}** ({o_str})")
            with col2_p:
                st.info("■ 対抗買い目（4点）")
                for c, o in zip(res["taikou_lines"], res["taikou_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "--- 倍"
                    st.write(f"👉 **{c}** ({o_str})")
            with col3_p:
                st.warning("■ 大穴買い目（4点）")
                for c, o in zip(res["oana_lines"], res["oana_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "--- 倍"
                    st.write(f"👉 **{c}** ({o_str})")
            target_odds = res["honmei_odds"]
            target_lines = res["honmei_lines"]

        # 3. 格言集スジ買い法則に基づく推奨目
        suji_lines = res.get("suji_lines", [])
        suji_odds = res.get("suji_odds", [])
        suji_expl = res.get("suji_expl", [])
        if suji_lines:
            st.markdown("---")
            st.subheader("📜 【格言集スジ買い法則】 展開スジ買い推奨目")
            if suji_expl:
                for exp in suji_expl:
                    st.caption(f"・{exp}")
            cols_s = st.columns(min(len(suji_lines), 6))
            for idx_s, (c, o) in enumerate(zip(suji_lines, suji_odds)):
                with cols_s[idx_s % len(cols_s)]:
                    o_str = f"{o:.1f}倍" if o > 0 else "---"
                    st.metric(label=f"スジ買い {c}", value=o_str)

        # 4. 資金分配表（最上部の設定金額に即時連動）
        st.markdown("---")
        st.subheader(f"💰 傾斜資金分配（設定予算: {total_budget:,} 円）")
        if calculate_capital_allocation and target_odds:
            alloc_res = calculate_capital_allocation(target_odds, total_budget=total_budget)
            st.write(f"📊 **合成オッズ**: **{alloc_res['synthetic_odds']:.2f}倍** | **目標払戻額**: **約 {int(alloc_res['target_payout']):,} 円**")
            
            table_alloc = []
            for combo, o, a in zip(target_lines, target_odds, alloc_res["allocations"]):
                table_alloc.append({
                    "買い目": combo,
                    "現在オッズ": f"{o:.1f}倍" if o > 0 else "---",
                    "推奨購入金額": f"{a['stake']:,} 円",
                    "的中時払戻金": f"{int(a['expected_payout']):,} 円",
                    "回収率": f"{a['return_rate']:.1f}%"
                })
            st.dataframe(pd.DataFrame(table_alloc), use_container_width=True)

        # 5. 艇別評価明細表
        st.markdown("---")
        st.subheader("📊 艇別評価 6大要素採点明細")
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
                "⑥体重補正": f"{d['p6']:.1f}",
                "展示ボーナス": f"{d.get('p_ex', 0.0):.1f}",
                "イン減点": f"{d.get('p_in_pen', 0.0):.1f}",
                "隠れA級加点": f"{d.get('p_hidden', 0.0):.1f}"
            })
        st.dataframe(pd.DataFrame(table_score), use_container_width=True)

    elif mode == "all":
        tab0, tab1, tab2, tab3, tab4 = st.tabs(["🏰 キャッスルV6予想", "出走表（番組）", "オッズ（3連単）", "直前情報", "レース結果"])
        jcd = fp['jcd_code']
        rno_val = fp['rno']
        d_str = fp['date_str']
        
        with tab0:
            res_v6 = calculate_castle_v6_prediction(jcd, rno_val, d_str, params=fp.get("params"))
            st.subheader("🏰【キャッスル式V6作戦】 予想＆オッズ")
            alerts = res_v6.get("alerts", [])
            if alerts:
                for a in alerts:
                    st.info(a)
            col_va, col_vb = st.columns(2)
            with col_va:
                st.success("■ VA線（本命・6点）")
                for c, o in zip(res_v6["va_lines"], res_v6["va_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "---"
                    st.write(f"👉 **{c}** ({o_str})")
            with col_vb:
                st.info("■ VB線（穴目・4点）")
                for c, o in zip(res_v6["vb_lines"], res_v6["vb_odds"]):
                    o_str = f"{o:.1f}倍" if o > 0 else "---"
                    st.write(f"👉 **{c}** ({o_str})")
        
        with tab1:
            soup = fetch_boatrace_data("racelist", jcd, rno_val, d_str)
            parse_and_display_tables(soup, "出走表")
        
        with tab2:
            soup = fetch_boatrace_data("odds3t", jcd, rno_val, d_str)
            parse_and_display_tables(soup, "オッズ")
        
        with tab3:
            soup = fetch_boatrace_data("beforeinfo", jcd, rno_val, d_str)
            parse_and_display_tables(soup, "直前情報")
        
        with tab4:
            soup = fetch_boatrace_data("raceresult", jcd, rno_val, d_str)
            parse_and_display_tables(soup, "レース結果")
