import os
import re
import math
import pandas as pd
from bs4 import BeautifulSoup

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


def generate_exact_boatrace_odds_order():
    """
    boatrace.jp 3連単オッズ (odds3t) HTML DOM (120点) 正しいRow-by-Row出現順
    Table 1&2 横並び全6ブロック: 行 0..19
    1行あたり: 1着 1, 2, 3, 4, 5, 6 号艇
    """
    combinations = []
    for r in range(20):
        for a in range(1, 7):
            b_list = [x for x in range(1, 7) if x != a]
            b = b_list[r // 4]
            c_list = [y for y in range(1, 7) if y != a and y != b]
            c = c_list[r % 4]
            combinations.append(f"{a}-{b}-{c}")
    return combinations


def parse_odds3t(soup):
    """
    3連単オッズHTMLから全120通りのオッズ辞書 {"1-2-3": 16.8, ...} を抽出
    td.oddsPoint のみを取得し、span重複を自動排除する
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
