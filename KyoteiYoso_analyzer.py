import os
import re
import math
import pandas as pd
from bs4 import BeautifulSoup

# ==========================================
# 競艇場別ローカルルール・水面特性マスタ
# ==========================================
VENUE_MASTERS = {
    "01": {"name": "桐生", "water": "淡水", "type": "ナイター", "in_rate": "標準", "desc": "標高が高く気圧が低い。淡水でモーターパワー（出足・伸び）が重要。"},
    "02": {"name": "戸田", "water": "淡水", "type": "デイドリーム", "in_rate": "低い", "desc": "【戸田のカドまくり】1M幅が狭く1コース逃げ率低。3・4コースのダッシュまくり・まくり差しが炸裂。"},
    "03": {"name": "江戸川", "water": "淡水/河川", "type": "難水面", "in_rate": "波乱", "desc": "【難水面・潮と風】上げ潮・追い風は1コース流れて差し(2,3コース)有利。Fタッチ展示艇はスタート信頼◎。"},
    "04": {"name": "平和島", "water": "海水/汽水", "type": "難水面", "in_rate": "極低(前半35%)", "desc": "【平和島のバック水面】前半1~4Rはイン弱い。まくり艇抵抗で『来そうな選手の一つ外(5コース差し)』が高配当。"},
    "05": {"name": "多摩川", "water": "淡水", "type": "静水面", "in_rate": "標準", "desc": "【淡水は硬く重い選手に厳しい】浮力が小さく水質が硬い。体重55kg以上の選手や出足不足艇は2M跳ねやすい。"},
    "06": {"name": "浜名湖", "water": "汽水", "type": "デイドリーム", "in_rate": "標準", "desc": "広大な静水面でスピード戦。機力差が素直に着順に出やすい。"},
    "07": {"name": "蒲郡", "water": "海水", "type": "ナイター", "in_rate": "高め", "feature": "ナイターのイン強勢。静水面で実力上位艇が安定。"},
    "08": {"name": "常滑", "water": "海水", "type": "デイドリーム", "in_rate": "高め", "desc": "伊勢湾の潮風。風向きで差し・まくりの優位変化。"},
    "09": {"name": "津", "water": "海水", "type": "デイドリーム", "in_rate": "高め", "desc": "鈴鹿おろし強風時は水面荒れて波乱含み。"},
    "10": {"name": "三国", "water": "淡水", "type": "モーニング", "in_rate": "高め", "desc": "モーニング場。風の影響を受けやすい。"},
    "11": {"name": "びわこ", "water": "淡水", "type": "難水面", "in_rate": "低い", "desc": "標高高く淡水でうねり発生。1M旋回困難で1コース飛ぶ可能性高。"},
    "12": {"name": "住之江", "water": "淡水", "type": "ナイター", "in_rate": "高め", "desc": "【競艇の聖地】淡水ナイター。2M引き波で硬い水面が引き起こす跳ねに注意。"},
    "13": {"name": "尼崎", "water": "淡水", "type": "デイドリーム", "in_rate": "高め", "desc": "静水面でイン強い。機力の素直な反映。"},
    "14": {"name": "鳴門", "water": "海水", "type": "モーニング", "in_rate": "標準", "desc": "1M狭くまくり決まりやすい。"},
    "15": {"name": "丸亀", "water": "海水", "type": "ナイター", "in_rate": "高め", "desc": "潮位差あり。満潮はイン有利、干潮はまくり。"},
    "16": {"name": "児島", "water": "海水", "type": "デイドリーム", "in_rate": "高め", "desc": "【干潮のインは握って回れる】干満差3m。干潮時は水面落ち着きイン逃げ圧倒的。"},
    "17": {"name": "宮島", "water": "海水", "type": "デイドリーム", "in_rate": "標準", "desc": "潮位差大。満潮時のうねりでまくり流される。"},
    "18": {"name": "徳山", "water": "海水", "type": "モーニング", "in_rate": "極高(1-4R)", "desc": "【1R~4R本命マン領域】1-2占有率23.9%で本命堅固。5R・9R企画戦は中穴マンの2-4-1特異点(153%)・1-3岩郷バイアス。"},
    "19": {"name": "下関", "water": "海水", "type": "ナイター", "in_rate": "極高", "desc": "ナイター化でイン超強勢。"},
    "20": {"name": "若松", "water": "海水", "type": "ナイター", "in_rate": "高め", "desc": "海水で浮力あり。潮の満ち引きで傾向変化。"},
    "21": {"name": "芦屋", "water": "淡水", "type": "モーニング", "in_rate": "極高", "desc": "モーニング企画戦でイン超強勢。1R~4Rは1強5弱構造。"},
    "22": {"name": "福岡", "water": "汽水", "type": "難水面", "in_rate": "低い", "desc": "1M独特のうねり（うねり発生でイン流れる）。2・3コース差し抜け多発。"},
    "23": {"name": "唐津", "water": "淡水", "type": "モーニング", "in_rate": "高め", "desc": "モーニング「朝1戦」は本命マンの1強5弱アンカリング構造。"},
    "24": {"name": "大村", "water": "海水", "type": "イン最強", "in_rate": "最高(約60%)", "desc": "【全国No.1イン最強水面】1コース勝率60%超。イン信頼度絶大（ただし1号艇飛べば超高配当万舟）。"}
}


class FanDataLoader:
    """
    fan2604.txt (モーターボートファン手帳データ) 自動解析クラス
    """
    def __init__(self, file_path="fan2604.txt"):
        self.file_path = file_path
        self.racer_db = {}
        self.pattern = re.compile(
            r'([A-B][1-2])([SHR])(\d{6})(\d)(\d{2})(\d{3})(\d{2})([ A-BO]{2})\s*(\d{4})(\d{4})'
        )
        if os.path.exists(file_path):
            self.load_data()

    def load_data(self):
        try:
            with open(self.file_path, "r", encoding="cp932", errors="replace") as f:
                for line in f:
                    self._parse_line(line)
        except Exception:
            try:
                with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        self._parse_line(line)
            except Exception as e:
                print(f"ファン手帳データ読み込みエラー: {e}")

    def _parse_line(self, line: str):
        if len(line) < 100:
            return
        
        toban = line[:4].strip()
        if not toban.isdigit():
            return
        
        match = self.pattern.search(line)
        if not match:
            return
        
        try:
            kyu = match.group(1)
            shouritsu = int(match.group(9)) / 100.0
            fukushouritsu = int(match.group(10)) / 10.0
            
            idx = match.end(10)
            avg_st = int(line[idx+13:idx+16]) / 100.0
            
            c_idx = idx + 16
            course_data = {}
            for c in range(1, 7):
                entry_cnt = int(line[c_idx:c_idx+3])
                c_fukushou = int(line[c_idx+3:c_idx+7]) / 10.0
                c_st = int(line[c_idx+7:c_idx+10]) / 100.0
                c_st_rank = int(line[c_idx+10:c_idx+13]) / 100.0
                
                course_data[c] = {
                    "entry_count": entry_cnt,
                    "fukushouritsu": c_fukushou,
                    "avg_st": c_st,
                    "avg_st_rank": c_st_rank
                }
                c_idx += 13
                
            konki_noshi = int(line[c_idx+10:c_idx+14]) / 100.0
            
            self.racer_db[toban] = {
                "toban": toban,
                "kyu": kyu,
                "shouritsu": shouritsu,
                "fukushouritsu": fukushouritsu,
                "avg_st": avg_st,
                "courses": course_data,
                "konki_noshi": konki_noshi
            }
        except Exception:
            pass

    def get_racer(self, toban: str):
        """登番から選手データを取得"""
        return self.racer_db.get(str(toban).zfill(4))

    def calculate_score_bonus(self, toban: str, course_no: int):
        """
        指定した登番・枠番（コース）における合算ボーナススコアを算出
        """
        racer = self.get_racer(toban)
        if not racer:
            return 0.0, "データなし"
        
        c_info = racer["courses"].get(course_no, {})
        c_fukushou = c_info.get("fukushouritsu", 0.0)
        noshi = racer.get("konki_noshi", 50.0)
        
        bonus = (noshi * 0.5) + (c_fukushou * 0.4)
        detail = f"能力指数:{noshi:.1f} pts / {course_no}コース複勝率:{c_fukushou:.1f}%"
        return bonus, detail


def detect_hidden_a(toban, kyu, shouritsu, local_winrate=0.0):
    """
    登番3000〜4000番台のベテラン・『隠れA級』の検出
    B1/B2級に降格していても、実力を保持しているベテラン選手を判定
    """
    try:
        tb_num = int(toban)
        if 3000 <= tb_num <= 4000 and kyu in ["B1", "B2"]:
            if shouritsu >= 5.0 or local_winrate >= 5.0:
                return True, f"登番{toban}(ベテラン実力派/隠れA級)"
    except Exception:
        pass
    return False, ""


def generate_exact_boatrace_odds_order():
    """
    boatrace.jp 3連単オッズ (odds3t) HTML DOM (120点) 正しいRow-by-Row出現順
    Table 1 (左側: 1着 1, 2, 3) 20行 x 3列 = 60点
    Table 2 (右側: 1着 4, 5, 6) 20行 x 3列 = 60点
    """
    combinations = []
    # Table 1: 1着 1, 2, 3
    for r in range(20):
        for a in [1, 2, 3]:
            b_list = [x for x in range(1, 7) if x != a]
            b = b_list[r // 4]
            c_list = [y for y in range(1, 7) if y != a and y != b]
            c = c_list[r % 4]
            combinations.append(f"{a}-{b}-{c}")
            
    # Table 2: 1着 4, 5, 6
    for r in range(20):
        for a in [4, 5, 6]:
            b_list = [x for x in range(1, 7) if x != a]
            b = b_list[r // 4]
            c_list = [y for y in range(1, 7) if y != a and y != b]
            c = c_list[r % 4]
            combinations.append(f"{a}-{b}-{c}")
            
    return combinations


def parse_odds3t(soup):
    """
    3連単オッズHTMLから全120通りのオッズ辞書 {"1-2-3": 16.8, ...} を抽出
    td.oddsPoint のみを取得し、span要素による240点重複を自動排除する
    """
    odds_dict = {}
    if not soup:
        return odds_dict
    
    td_cells = [
        td for td in soup.find_all("td")
        if td.get("class") and any("oddsPoint" in c for c in td.get("class"))
    ]
    
    val_list = []
    for cell in td_cells:
        txt = cell.get_text().strip()
        try:
            val = float(txt)
            val_list.append(val)
        except ValueError:
            pass
            
    if len(val_list) == 240:
        val_list = val_list[::2]
        
    combos = generate_exact_boatrace_odds_order()
    
    if len(val_list) >= 120:
        for idx, combo in enumerate(combos):
            odds_dict[combo] = val_list[idx]
    else:
        for cell in td_cells:
            txt = cell.get_text().strip()
            parent = cell.parent
            if parent:
                p_txt = parent.get_text().strip()
                m = re.search(r'([1-6])[-ー—]([1-6])[-ー—]([1-6])', p_txt)
                if m:
                    combo = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                    try:
                        odds_dict[combo] = float(txt)
                    except ValueError:
                        pass
    return odds_dict


def calculate_capital_allocation(odds_list, total_budget=10000):
    """
    傾斜資金分配計算（合成オッズ・払戻金均等化・100円単位）
    """
    valid_odds = [o for o in odds_list if o > 0]
    if not valid_odds:
        return {
            "synthetic_odds": 0.0,
            "allocations": [],
            "total_allocated": 0,
            "target_payout": 0
        }
    
    inv_sum = sum(1.0 / o for o in valid_odds)
    synthetic_odds = 1.0 / inv_sum if inv_sum > 0 else 0.0
    
    target_payout = total_budget * synthetic_odds
    
    raw_stakes = [target_payout / o for o in valid_odds]
    rounded_stakes = [max(100, int(round(s / 100.0) * 100)) for s in raw_stakes]
    
    total_allocated = sum(rounded_stakes)
    
    allocations = []
    for o, stake in zip(valid_odds, rounded_stakes):
        payout = stake * o
        return_rate = (payout / total_allocated * 100.0) if total_allocated > 0 else 0.0
        allocations.append({
            "odds": o,
            "stake": stake,
            "expected_payout": payout,
            "return_rate": return_rate
        })
        
    return {
        "synthetic_odds": synthetic_odds,
        "allocations": allocations,
        "total_allocated": total_allocated,
        "target_payout": target_payout
    }


def generate_suji_recommendations(r1, r2, r3, r4, r5, r6, jcd, rno):
    """
    格言集のスジ買い法則および番組マンのクセに基づくスジ買いの買い目生成
    - まくり（3,4コース頭）➔ 内外スジ (4-5, 4-6, 4-1 / 3-4, 3-5, 3-1)
    - 差し（2,3コース頭） ➔ 内内スジ (2-1, 3-1)
    - まくり差し ➔ 3-1, 5-1, 5-4
    - 平和島特有 ➔ まくり艇の1つ外の差し (4まくりなら5-1, 5-2)
    - 徳山・大村岩郷バイアス ➔ 1-3本線
    """
    suji_lines = []
    explanations = []
    
    # 1. 軸が1号艇の場合（イン逃げ）
    if r1 == 1:
        if jcd in ["18", "24"]:  # 徳山・大村
            suji_lines.extend([f"1-3-{r2}", f"1-3-{r3}", f"1-3-{r4}", f"1-2-{r3}", f"1-2-{r4}"])
            explanations.append("【岩郷バイアス・イン本命】1号艇強勢時の1-3軸（市場人気1-2を超える高出現率スジ）")
        else:
            suji_lines.extend([f"1-2-{r3}", f"1-2-{r4}", f"1-3-{r2}", f"1-3-{r4}", f"1-4-{r2}"])
            explanations.append("【王道イン逃げスジ】1コース頭からの本線・対抗ライン")
            
    # 2. 軸が2号艇の場合（差し中心）
    elif r1 == 2:
        suji_lines.extend([f"2-1-{r3}", f"2-1-{r4}", f"2-3-{r1}", f"2-4-{r1}"])
        explanations.append("【格言：差しは内（内内スジ）】2コース差し成功時は1号艇が残る2-1展開")
        if jcd == "18" and (r2 == 4 or r3 == 4):
            suji_lines.append("2-4-1")
            explanations.append("【番組マン特異点】徳山2-4-1座標（期待値153%のバグ発生ポイント）")

    # 3. 軸が3号艇の場合（まくり・まくり差し）
    elif r1 == 3:
        suji_lines.extend([f"3-1-{r2}", f"3-1-{r4}", f"3-4-{r1}", f"3-5-{r1}"])
        explanations.append("【格言：まくりは内外 / まくり差しは総合力】3コース攻めによる内外連動＆3-1スジ")

    # 4. 軸が4号艇の場合（カドまくり）
    elif r1 == 4:
        suji_lines.extend([f"4-5-{r1}", f"4-5-{r6}", f"4-6-{r1}", f"4-1-{r5}"])
        explanations.append("【格言：まくりは内外（カドまくりスジ）】4コースまくりで内失速、外枠5・6号艇が連動")
        if jcd == "04":  # 平和島
            suji_lines.extend(["5-1-2", "5-2-1"])
            explanations.append("【平和島格言：来そうな選手の一つ外は返しておけ】4まくり抵抗時の5コース差し抜け高配当")
            
    # 5. 5・6号艇軸の場合
    else:
        suji_lines.extend([f"{r1}-1-{r2}", f"{r1}-4-{r2}", f"{r1}-{r2}-1"])
        explanations.append("【展開波乱・大穴スジ】アウトコースまくり差し・差し抜けの波乱決着")
        
    return list(dict.fromkeys(suji_lines)), explanations


def generate_venue_and_maxim_alerts(jcd: str, rno: int, racers_map: dict, before_info: dict, fan_loader, ranked_boats: list):
    """
    格言集および番組マンのクセに基づくリアルタイム注意・アラート生成
    """
    alerts = []
    v_data = VENUE_MASTERS.get(jcd, {})
    v_name = v_data.get("name", "該当場")
    water_type = v_data.get("water", "淡水")
    
    # 1. 競艇場固有の格言アラート
    if jcd == "02": # 戸田
        alerts.append("💡 【戸田格言：戸田のカドまくり】1コース逃げ率低め。3・4コースのカドまくり・まくり差し展開を要警戒！")
    elif jcd == "03": # 江戸川
        alerts.append("💡 【江戸川格言：難水面・潮と風】上げ潮・追い風時は1コース流れて2・3コースの差し抜けが急増！")
    elif jcd == "04": # 平和島
        if rno <= 4:
            alerts.append("💡 【平和島格言：前半は3、4の差し（1コース約35%）】前半戦は1コース着率が低くイン飛び警戒！")
        alerts.append("💡 【平和島格言：来そうな選手の一つ外は返しておけ】4まくり狙い時は内抵抗で5コースの差し抜け高配当をマーク！")
    elif jcd == "16": # 児島
        alerts.append("💡 【児島格言：干潮のインは握って回れる】干潮時間帯は水面落ち着きイン逃げが圧倒的優位！")
    elif jcd == "18": # 徳山
        if rno <= 4:
            alerts.append("💡 【徳山格言：本命マンのモーニングアンカリング(1R~4R)】1強5弱構造で1-2（占有率23.9%）が本命軸！")
        elif rno in [5, 9]:
            alerts.append("💡 【徳山格言：中穴マンの企画戦(5R/9R)】2・4号艇の実力派隠れA級と2-4-1特異点(期待値153%)に注意！")
    elif jcd == "24": # 大村
        alerts.append("💡 【大村格言：大村はイン最強水面】1コース1着率約60%。ただし1号艇崩れた場合のオッズ崩壊万舟を頭の隅に！")

    # 2. 水質（淡水 vs 海水）と体重アラート
    if "淡水" in water_type:
        alerts.append(f"💧 【淡水場アラート（{v_name}）】塩分がなく水質が硬い。体重重い選手や出足不足艇は2Mで引き波に弾かれ跳ねやすい！")
        
    # 3. 隠れA級（ベテラン実力派）検出アラート
    hidden_a_list = []
    if racers_map and fan_loader:
        for b_no, toban in racers_map.items():
            if toban:
                racer = fan_loader.get_racer(toban)
                if racer:
                    kyu = racer.get("kyu", "B1")
                    sr = racer.get("shouritsu", 0.0)
                    is_hidden, h_desc = detect_hidden_a(toban, kyu, sr)
                    if is_hidden:
                        hidden_a_list.append(f"{b_no}号艇:{h_desc}")
    if hidden_a_list:
        alerts.append(f"👤 【中穴マンの刺客：隠れA級検出】" + ", ".join(hidden_a_list) + " ➔ 記号的B級だが本番の捌き・気合で波乱を起こす要注意艇！")

    # 4. チルト跳ね上げアラート
    for b_no, tilt_val in before_info.get("tilts", {}).items():
        if tilt_val >= 2.0:
            alerts.append(f"⚠️ 【チルト注意】{b_no}号艇のチルト角度が {tilt_val}° に跳ね上げ。伸び足重視のまくり波乱の可能性高！")

    return alerts
