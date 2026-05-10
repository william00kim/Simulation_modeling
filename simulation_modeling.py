import pandas as pd
import numpy as np
import random
import re
from datetime import datetime, timedelta
import osmnx as ox

# =========================
# 1. 사용자 로드
# =========================
scenario_df = pd.read_csv("scenario_final.csv")

# 공백/타입 정리
scenario_df["name"] = scenario_df["name"].astype(str).str.strip()
scenario_df["type"] = scenario_df["type"].astype(str).str.strip()
scenario_df["phone"] = scenario_df["phone"].astype(str).str.strip()

users = {
    row["name"]: {
        "type": row["type"],
        "phone": row["phone"]
    }
    for _, row in scenario_df.iterrows()
}

# 스팸 전화번호/이름 집합
spam_names = set(
    scenario_df.loc[scenario_df["type"] == "스팸", "name"]
)
spam_phones = set(
    scenario_df.loc[scenario_df["type"] == "스팸", "phone"]
)

# =========================
# 2. 활성 기간
# =========================
user_active_period = {
    "김누구":         (datetime(2026, 1, 1), datetime(2026, 1, 31)),
    "김누구_대포폰1": (datetime(2026, 2, 1), datetime(2026, 2, 28)),
    "김누구_대포폰2": (datetime(2026, 3, 1), datetime(2026, 6, 30)),
}

def is_active(user, timestamp):
    if user not in user_active_period:
        return True
    start, end = user_active_period[user]
    return start <= timestamp <= end

# =========================
# 3. 관계 정의 (단방향 원본)
# =========================
_relations_raw = {
    "김누구":         {"김누구_부", "김누구_모", "김대아", "김소아", "이아내", "박운전"},
    "김누구_대포폰1": {"김누구_부", "김누구_모", "김대아", "김소아", "이아내", "박운전"},
    "김누구_대포폰2": {"김누구_부", "김누구_모", "김대아", "김소아", "이아내", "박운전"},

    "김대아": {"김누구", "이아내", "김소아",
               "김대아_친구1","김대아_친구2","김대아_친구3","김대아_친구4",
               "김대아_친구5","김대아_친구6","김대아_친구7","김대아_친구8"},
    "김대아_친구1": {"김대아","김대아_친구2","김대아_친구3","김대아_친구4","김대아_친구5","김대아_친구6","김대아_친구7","김대아_친구8"},
    "김대아_친구2": {"김대아","김대아_친구1","김대아_친구3","김대아_친구4","김대아_친구5","김대아_친구6","김대아_친구7","김대아_친구8"},
    "김대아_친구3": {"김대아","김대아_친구1","김대아_친구2","김대아_친구4","김대아_친구5","김대아_친구6","김대아_친구7","김대아_친구8"},
    "김대아_친구4": {"김대아","김대아_친구1","김대아_친구2","김대아_친구3","김대아_친구5","김대아_친구6","김대아_친구7","김대아_친구8"},
    "김대아_친구5": {"김대아","김대아_친구1","김대아_친구2","김대아_친구3","김대아_친구4","김대아_친구6","김대아_친구7","김대아_친구8"},
    "김대아_친구6": {"김대아","김대아_친구1","김대아_친구2","김대아_친구3","김대아_친구4","김대아_친구5","김대아_친구7","김대아_친구8"},
    "김대아_친구7": {"김대아","김대아_친구1","김대아_친구2","김대아_친구3","김대아_친구4","김대아_친구5","김대아_친구6","김대아_친구8"},
    "김대아_친구8": {"김대아","김대아_친구1","김대아_친구2","김대아_친구3","김대아_친구4","김대아_친구5","김대아_친구6","김대아_친구7"},

    "김소아": {"김누구", "이아내", "김대아",
               "김소아_친구1","김소아_친구2","김소아_친구3","김소아_친구4",
               "김소아_친구5","김소아_친구6","김소아_친구7","김소아_친구8"},
    "김소아_친구1": {"김소아","김소아_친구2","김소아_친구3","김소아_친구4","김소아_친구5","김소아_친구6","김소아_친구7","김소아_친구8"},
    "김소아_친구2": {"김소아","김소아_친구1","김소아_친구3","김소아_친구4","김소아_친구5","김소아_친구6","김소아_친구7","김소아_친구8"},
    "김소아_친구3": {"김소아","김소아_친구1","김소아_친구2","김소아_친구4","김소아_친구5","김소아_친구6","김소아_친구7","김소아_친구8"},
    "김소아_친구4": {"김소아","김소아_친구1","김소아_친구2","김소아_친구3","김소아_친구5","김소아_친구6","김소아_친구7","김소아_친구8"},
    "김소아_친구5": {"김소아","김소아_친구1","김소아_친구2","김소아_친구3","김소아_친구4","김소아_친구6","김소아_친구7","김소아_친구8"},
    "김소아_친구6": {"김소아","김소아_친구1","김소아_친구2","김소아_친구3","김소아_친구4","김소아_친구5","김소아_친구7","김소아_친구8"},
    "김소아_친구7": {"김소아","김소아_친구1","김소아_친구2","김소아_친구3","김소아_친구4","김소아_친구5","김소아_친구6","김소아_친구8"},
    "김소아_친구8": {"김소아","김소아_친구1","김소아_친구2","김소아_친구3","김소아_친구4","김소아_친구5","김소아_친구6","김소아_친구7"},

    "이아내": {"김대아", "김소아", "이아내_부", "이아내_모",
               "이아내_친구1","이아내_친구2","이아내_친구3","이아내_친구4",
               "이아내_친구5","이아내_친구6","이아내_친구7","이아내_친구8"},
    "이아내_친구1": {"이아내","이아내_친구2","이아내_친구3","이아내_친구4","이아내_친구5","이아내_친구6","이아내_친구7","이아내_친구8"},
    "이아내_친구2": {"이아내","이아내_친구1","이아내_친구3","이아내_친구4","이아내_친구5","이아내_친구6","이아내_친구7","이아내_친구8"},
    "이아내_친구3": {"이아내","이아내_친구1","이아내_친구2","이아내_친구4","이아내_친구5","이아내_친구6","이아내_친구7","이아내_친구8"},
    "이아내_친구4": {"이아내","이아내_친구1","이아내_친구2","이아내_친구3","이아내_친구5","이아내_친구6","이아내_친구7","이아내_친구8"},
    "이아내_친구5": {"이아내","이아내_친구1","이아내_친구2","이아내_친구3","이아내_친구4","이아내_친구6","이아내_친구7","이아내_친구8"},
    "이아내_친구6": {"이아내","이아내_친구1","이아내_친구2","이아내_친구3","이아내_친구4","이아내_친구5","이아내_친구7","이아내_친구8"},
    "이아내_친구7": {"이아내","이아내_친구1","이아내_친구2","이아내_친구3","이아내_친구4","이아내_친구5","이아내_친구6","이아내_친구8"},
    "이아내_친구8": {"이아내","이아내_친구1","이아내_친구2","이아내_친구3","이아내_친구4","이아내_친구5","이아내_친구6","이아내_친구7"},

    "박운전": {"박운전_부", "박운전_모",
               "박운전_친구1","박운전_친구2","박운전_친구3","박운전_친구4",
               "박운전_친구5","박운전_친구6","박운전_친구7","박운전_친구8"},
    "박운전_친구1": {"박운전","박운전_친구2","박운전_친구3","박운전_친구4","박운전_친구5","박운전_친구6","박운전_친구7","박운전_친구8"},
    "박운전_친구2": {"박운전","박운전_친구1","박운전_친구3","박운전_친구4","박운전_친구5","박운전_친구6","박운전_친구7","박운전_친구8"},
    "박운전_친구3": {"박운전","박운전_친구1","박운전_친구2","박운전_친구4","박운전_친구5","박운전_친구6","박운전_친구7","박운전_친구8"},
    "박운전_친구4": {"박운전","박운전_친구1","박운전_친구2","박운전_친구3","박운전_친구5","박운전_친구6","박운전_친구7","박운전_친구8"},
    "박운전_친구5": {"박운전","박운전_친구1","박운전_친구2","박운전_친구3","박운전_친구4","박운전_친구6","박운전_친구7","박운전_친구8"},
    "박운전_친구6": {"박운전","박운전_친구1","박운전_친구2","박운전_친구3","박운전_친구4","박운전_친구5","박운전_친구7","박운전_친구8"},
    "박운전_친구7": {"박운전","박운전_친구1","박운전_친구2","박운전_친구3","박운전_친구4","박운전_친구5","박운전_친구6","박운전_친구8"},
    "박운전_친구8": {"박운전","박운전_친구1","박운전_친구2","박운전_친구3","박운전_친구4","박운전_친구5","박운전_친구6","박운전_친구7"},

    "스팸": set()
}

# 양방향 확장
relations = {}
for caller, contacts in _relations_raw.items():
    relations.setdefault(caller, set()).update(contacts)
    for contact in contacts:
        relations.setdefault(contact, set()).add(caller)

# =========================
# 트랜잭션 발생 대상 & 페르소나
# =========================
TRANSACTION_USERS = {
    "김누구", "김누구_대포폰1", "김누구_대포폰2",
    "이아내", "박운전", "김소아", "김대아"
}

transaction_persona_template = {
    "김누구":         {"mean_interval_min": 10, "active_hours": (9, 22)},
    "김누구_대포폰1": {"mean_interval_min": 10, "active_hours": (9, 22)},
    "김누구_대포폰2": {"mean_interval_min": 10, "active_hours": (9, 22)},
    "박운전":         {"mean_interval_min": 10, "active_hours": (9, 22)},
    "이아내":         {"mean_interval_min": 10, "active_hours": (9, 21)},
    "김대아":         {"mean_interval_min": 10, "active_hours": (9, 21)},
    "김소아":         {"mean_interval_min": 10, "active_hours": (9, 21)},
}

# =========================
# 4. 페르소나
# =========================
call_persona_template = {
    "용의자": {
        "lambda": 2,
        "daily_call_count": (0, 5),
        "call_duration": (2, 10),
        "active_hours": (9, 22),
    },
    "공범": {
        "lambda": 2,
        "daily_call_count": (0, 5),
        "call_duration": (1, 10),
        "active_hours": (9, 22),
    },
    "김누구_가족": {
        "lambda": 2,
        "daily_call_count": (0, 4),
        "call_duration": (4, 30),
        "active_hours": (9, 22)
    },
    "이아내_가족": {
        "lambda": 2,
        "daily_call_count": (0, 4),
        "call_duration": (4, 30),
        "active_hours": (9, 22)
    },
    "이아내_친구": {
        "lambda": 2,
        "daily_call_count": (0, 4),
        "call_duration": (10, 40),
        "active_hours": (9, 22)
    },
    "김대아_친구": {
        "lambda": 2,
        "daily_call_count": (0, 4),
        "call_duration": (15, 30),
        "active_hours": (9, 22)
    },
    "김소아_친구": {
        "lambda": 2,
        "daily_call_count": (0, 4),
        "call_duration": (20, 30),
        "active_hours": (9, 22)
    },
    "박운전_가족": {
        "lambda": 2,
        "daily_call_count": (0, 10),
        "call_duration": (1, 10),
        "active_hours": (9, 22)
    },
    "박운전_친구": {
        "lambda": 2,
        "daily_call_count": (0, 10),
        "call_duration": (1, 10),
        "active_hours": (9, 22)
    },
    "스팸": {
        "lambda": 3,
        "daily_call_count": (0, 1),
        "call_duration": (1, 2),
        "active_hours": (9, 16)
    }
}

# =========================
# 5. 수신자 선택
# =========================
chain_handover_done = set()

spam_targets = [
    u for u in users
    if users[u]["type"] != "스팸"
    and users[u]["phone"] not in spam_phones
    and not u.startswith("김누구_대포폰")
]

chain_map = {
    "김누구":         ("김누구_대포폰1", datetime(2026, 1, 31)),
    "김누구_대포폰1": ("김누구_대포폰2", datetime(2026, 2, 28)),
}

def choose_receiver(caller, timestamp):
    p_type = users[caller]["type"]

    # 스팸 발신자는 전화는 걸 수 있지만, 수신자는 절대 스팸이면 안 됨
    if p_type == "스팸":
        candidates = [
            u for u in users
            if u != caller
            and users[u]["type"] != "스팸"
            and users[u]["phone"] not in spam_phones
            and not u.startswith("김누구_대포폰")
        ]

        if not candidates:
            candidates = [
                u for u in users
                if u != caller
                and users[u]["type"] != "스팸"
                and users[u]["phone"] not in spam_phones
            ]

        if not candidates:
            raise ValueError(f"{caller}에게 배정 가능한 비스팸 수신자가 없습니다.")

        receiver = random.choice(candidates)
        return receiver, "SPAM"

    # 일반 발신자가 스팸에게 전화하는 로직은 제거
    # if np.random.random() < 0.05: ...  <- 삭제됨

    # 대포폰 체인 인계
    if caller in chain_map:
        next_phone, handover_date = chain_map[caller]
        if (
            timestamp.date() == handover_date.date()
            and caller not in chain_handover_done
            and users[next_phone]["type"] != "스팸"
            and users[next_phone]["phone"] not in spam_phones
        ):
            chain_handover_done.add(caller)
            return next_phone, "SUSPICIOUS"

    # 관계 기반 후보
    candidates = [
        u for u in relations.get(caller, set())
        if u in users
        and u != caller
        and users[u]["type"] != "스팸"
        and users[u]["phone"] not in spam_phones
    ]

    # fallback 후보
    if not candidates:
        candidates = [
            u for u in users
            if u != caller
            and users[u]["type"] != "스팸"
            and users[u]["phone"] not in spam_phones
        ]

    if not candidates:
        raise ValueError(f"{caller}에게 배정 가능한 비스팸 수신자가 없습니다.")

    receiver = random.choice(candidates)

    if (
        p_type in ["용의자", "공범"]
        and users[receiver]["type"] in ["용의자", "공범"]
    ):
        call_type = "SUSPICIOUS"
    else:
        call_type = "NORMAL"

    return receiver, call_type

# =========================
# 6. 기지국 데이터 로드
# =========================
def dms_to_decimal(dms):
    if pd.isna(dms):
        return None
    text = str(dms)
    nums = re.findall(r"[0-9]+\.?[0-9]*", text)
    if len(nums) >= 3:
        degree, minute, second = map(float, nums[:3])
        return degree + minute / 60 + second / 3600
    try:
        return float(text)
    except ValueError:
        return None

bs = pd.read_csv("merged_result.csv")
bs["lat"] = bs["위도"].apply(dms_to_decimal)
bs["lon"] = bs["경도"].apply(dms_to_decimal)
bs = bs.dropna(subset=["lat", "lon"])

bs_lat = bs["lat"].values
bs_lon = bs["lon"].values

# =========================
# 7. 거리 / RSSI 함수
# =========================
EARTH_RADIUS_M = 6371000

def haversine(lon1, lat1, lon2, lat2):
    lat1, lat2 = np.radians(lat1), np.radians(lat2)
    lon1, lon2 = np.radians(lon1), np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

RSSI_D0_DBM = -50
PATH_LOSS_N = 2
bs_rssi0 = RSSI_D0_DBM + np.random.randn(len(bs)) * 3

def get_base_station(lat, lon):
    dist = haversine(lon, lat, bs_lon, bs_lat)
    dists_safe = np.maximum(dist, 1.0)
    rssi = bs_rssi0 - 10 * PATH_LOSS_N * np.log10(dists_safe)
    return int(np.argmax(rssi))

# =========================
# 8. 이동 경로 생성
# =========================
print("OSMnx 그래프 로드 중...")
X = ox.load_graphml("gangwon_drive.graphml")

ueS = [
    {"name": "김누구",         "start": (37.353002479591744,127.95765675540923),  "end": (37.89368892796336, 127.74942819301279)},
    {"name": "김누구_대포폰1", "start": (37.353002479591744,127.95765675540923),  "end": (37.89368892796336, 127.74942819301279)},
    {"name": "김누구_대포폰2", "start": (37.353002479591744,127.95765675540923),  "end": (37.89368892796336, 127.74942819301279)},
    {"name": "이아내",         "start": (37.328665544164956, 127.95443679000853),"end": (37.35144625421606,127.94980434594856)},
    {"name": "김대아",         "start": (37.328665544164956, 127.95443679000853),"end": (37.34957263098421, 127.94496728318722)},
    {"name": "김소아",         "start": (37.328665544164956, 127.95443679000853),"end": (37.36313055480327, 127.93502324636087)},
    {"name": "박운전",         "start": (37.86675474853952,127.75626382827372), "end": (37.76458014665824,128.83050162838398)},
    {"name": "김누구_부",      "start": (37.76790104794838, 128.93333479824776), "end": (37.76068486898025, 128.88837754538184)},
    {"name": "김누구_모",      "start": (37.76790104794838, 128.93333479824776), "end": (37.77340614020734, 128.91313535097134)},
    {"name": "이아내_부",      "start": (37.79055286720136, 128.91345549609343), "end": (37.75840141276585, 128.93979325877882)},
    {"name": "이아내_모",      "start": (37.79055286720136, 128.91345549609343), "end": (37.748348230009775, 128.89494470042382)},
    {"name": "박운전_부",      "start": (37.75352138794892, 128.88328263383022), "end": (37.7706935424776, 128.92274566942012)},
    {"name": "박운전_모",      "start": (37.75352138794892, 128.88328263383022), "end": (37.7706935424776, 128.92274566942012)},
    {"name": "이아내_친구1", "start": (37.33, 127.95), "end": (37.34, 127.96)},
    {"name": "이아내_친구2", "start": (37.32, 127.96), "end": (37.33, 127.97)},
    {"name": "이아내_친구3", "start": (37.34, 127.94), "end": (37.35, 127.95)},
    {"name": "이아내_친구4", "start": (37.31, 127.95), "end": (37.32, 127.96)},
    {"name": "이아내_친구5", "start": (37.33, 127.93), "end": (37.34, 127.94)},
    {"name": "이아내_친구6", "start": (37.32, 127.92), "end": (37.33, 127.93)},
    {"name": "이아내_친구7", "start": (37.34, 127.96), "end": (37.35, 127.97)},
    {"name": "이아내_친구8", "start": (37.31, 127.94), "end": (37.32, 127.95)},
    {"name": "김대아_친구1", "start": (37.34, 127.94), "end": (37.36, 127.93)},
    {"name": "김대아_친구2", "start": (37.35, 127.95), "end": (37.37, 127.94)},
    {"name": "김대아_친구3", "start": (37.33, 127.96), "end": (37.35, 127.95)},
    {"name": "김대아_친구4", "start": (37.36, 127.93), "end": (37.38, 127.92)},
    {"name": "김대아_친구5", "start": (37.34, 127.97), "end": (37.36, 127.96)},
    {"name": "김대아_친구6", "start": (37.32, 127.94), "end": (37.34, 127.93)},
    {"name": "김대아_친구7", "start": (37.35, 127.92), "end": (37.37, 127.91)},
    {"name": "김대아_친구8", "start": (37.33, 127.93), "end": (37.35, 127.92)},
    {"name": "김소아_친구1", "start": (37.36, 127.93), "end": (37.37, 127.92)},
    {"name": "김소아_친구2", "start": (37.37, 127.94), "end": (37.38, 127.93)},
    {"name": "김소아_친구3", "start": (37.35, 127.92), "end": (37.36, 127.91)},
    {"name": "김소아_친구4", "start": (37.38, 127.95), "end": (37.39, 127.94)},
    {"name": "김소아_친구5", "start": (37.36, 127.96), "end": (37.37, 127.95)},
    {"name": "김소아_친구6", "start": (37.34, 127.94), "end": (37.35, 127.93)},
    {"name": "김소아_친구7", "start": (37.37, 127.92), "end": (37.38, 127.91)},
    {"name": "김소아_친구8", "start": (37.35, 127.91), "end": (37.36, 127.90)},
    {"name": "박운전_친구1", "start": (37.86, 127.75), "end": (37.88, 127.74)},
    {"name": "박운전_친구2", "start": (37.87, 127.76), "end": (37.89, 127.75)},
    {"name": "박운전_친구3", "start": (37.85, 127.74), "end": (37.87, 127.73)},
    {"name": "박운전_친구4", "start": (37.88, 127.75), "end": (37.90, 127.74)},
    {"name": "박운전_친구5", "start": (37.86, 127.77), "end": (37.88, 127.76)},
    {"name": "박운전_친구6", "start": (37.84, 127.75), "end": (37.86, 127.74)},
    {"name": "박운전_친구7", "start": (37.87, 127.73), "end": (37.89, 127.72)},
    {"name": "박운전_친구8", "start": (37.85, 127.76), "end": (37.87, 127.75)},
]

spam_users_list = [
    row["name"] for _, row in scenario_df.iterrows()
    if row["type"] == "스팸"
]

for spam_name in spam_users_list:
    ueS.append({
        "name": spam_name,
        "start": (37.55, 127.05),
        "end":   (37.55, 127.05),
    })

route_coords = []
ue_positions = []

start_time = datetime(2026, 1, 1, 8, 0, 0)
SPEED_MPS = 10 * 1000 / 3600

print("경로 생성 중...")
for ue in ueS:
    orig = ox.nearest_nodes(X, ue["start"][1], ue["start"][0])
    dest = ox.nearest_nodes(X, ue["end"][1], ue["end"][0])
    route = ox.shortest_path(X, orig, dest, weight="length")

    detailed_route = []
    for u, v in zip(route[:-1], route[1:]):
        edge_data = X.get_edge_data(u, v)[0]
        if "geometry" in edge_data:
            detailed_route.extend([(lat, lon) for lon, lat in edge_data["geometry"].coords])
        else:
            detailed_route.append((X.nodes[u]["y"], X.nodes[u]["x"]))
    detailed_route.append((X.nodes[route[-1]]["y"], X.nodes[route[-1]]["x"]))
    route_coords.append(detailed_route)

    current_time = start_time
    prev = None
    for step_idx, (lat, lon) in enumerate(detailed_route):
        if prev:
            dist = haversine(prev[1], prev[0], lon, lat)
            dt = dist / SPEED_MPS
            current_time += timedelta(seconds=dt)
        ue_positions.append({
            "ue": ue["name"],
            "lat": lat,
            "lon": lon,
            "timestamp": current_time
        })
        prev = (lat, lon)

# =========================
# 9. 위치 조회
# =========================
ue_positions_dict = {}
for p in ue_positions:
    ue_positions_dict.setdefault(p["ue"], []).append(p)

# =========================
# 10. 통합 로그 생성
# =========================
logs = []
HOLD_RADIUS = 500

start_date = datetime(2026, 1, 1)
end_date   = datetime(2026, 6, 30)

def get_position_at_time(name, timestamp):
    positions = ue_positions_dict.get(name, [])
    if not positions:
        return None, None
    closest = min(positions, key=lambda p: abs((p["timestamp"] - timestamp).total_seconds()))
    return closest["lat"], closest["lon"]

# ── 통화 로그 ─────────────────────────────────────────────────
print("통화 로그 생성 중...")
current_day = start_date
while current_day < end_date:
    for name in users:
        if not is_active(name, current_day):
            continue

        route = ue_positions_dict.get(name, [])
        if not route:
            continue

        p_type = users[name]["type"]
        persona = call_persona_template.get(p_type, call_persona_template["용의자"])
        
        min_count, max_count = persona["daily_call_count"]

        while True:
            count = np.random.poisson(lam=persona["lambda"])
            if min_count <= count <= max_count:
                break

        if len(route) == 0 or count <= 0:
            continue

        call_steps = set(random.sample(range(len(route)), min(count, len(route))))

        prev_bs = None
        for step_idx, step in enumerate(route):
            if step_idx not in call_steps:
                continue

            lat, lon = step["lat"], step["lon"]

            t = step["timestamp"].replace(
                year=current_day.year,
                month=current_day.month,
                day=current_day.day
            )

            best_bs = get_base_station(lat, lon)

            if prev_bs is None:
                selected_bs = best_bs
            else:
                dist = haversine(lon, lat, bs_lon[prev_bs], bs_lat[prev_bs])
                selected_bs = best_bs if dist > HOLD_RADIUS else prev_bs
            prev_bs = selected_bs

            bs_lat_val = bs_lat[selected_bs]
            bs_lon_val = bs_lon[selected_bs]

            receiver, call_type = choose_receiver(name, t)
            receiver_phone = users[receiver]["phone"]

            # 최종 방어선: receiver_phone에 스팸 번호가 들어가면 즉시 중단
            if receiver_phone in spam_phones:
                raise ValueError(
                    f"receiver_phone에 스팸 번호가 들어갔습니다. "
                    f"caller_phone={users[name]['phone']}, "
                    f"receiver_phone={receiver_phone}, "
                    f"timestamp={t}"
                )

            duration = random.randint(*persona["call_duration"])

            logs.append({
                "timestamp":      t,
                "caller":         None,
                "caller_phone":   users[name]["phone"],
                "receiver":       None,
                "receiver_phone": receiver_phone,
                "lat":            bs_lat_val,
                "lon":            bs_lon_val,
                "station_id":     selected_bs,
                "call_type":      "NORMAL",
                "duration":       duration,
            })

    current_day += timedelta(days=1)

# ── 트랜잭션 로그 ─────────────────────────────────────────────
print("트랜잭션 로그 생성 중...")
current_day = start_date
while current_day < end_date:
    for name in TRANSACTION_USERS:
        if not is_active(name, current_day):
            continue

        route = ue_positions_dict.get(name, [])
        if not route:
            continue

        tx_persona = transaction_persona_template.get(name, {"mean_interval_min": 3, "active_hours": (9, 21)})
        mean_interval = tx_persona["mean_interval_min"] * 60

        prev_bs = None
        next_tx_after_sec = np.random.exponential(scale=mean_interval)
        elapsed_sec = 0.0

        for step_idx, step in enumerate(route):
            t = step["timestamp"].replace(
                year=current_day.year,
                month=current_day.month,
                day=current_day.day
            )

            if step_idx > 0:
                prev_t = route[step_idx - 1]["timestamp"].replace(
                    year=current_day.year,
                    month=current_day.month,
                    day=current_day.day
                )
                elapsed_sec += (t - prev_t).total_seconds()

            if elapsed_sec >= next_tx_after_sec:
                lat, lon = step["lat"], step["lon"]
                best_bs = get_base_station(lat, lon)

                if prev_bs is None:
                    selected_bs = best_bs
                else:
                    dist = haversine(lon, lat, bs_lon[prev_bs], bs_lat[prev_bs])
                    selected_bs = best_bs if dist > HOLD_RADIUS else prev_bs
                prev_bs = selected_bs

                logs.append({
                    "timestamp":      t,
                    "caller":         None,
                    "caller_phone":   users[name]["phone"],
                    "receiver":       None,
                    "receiver_phone": None,
                    "lat":            bs_lat[selected_bs],
                    "lon":            bs_lon[selected_bs],
                    "station_id":     selected_bs,
                    "call_type":      "TRANSACTION",
                    "duration":       None,
                })

                next_tx_after_sec = elapsed_sec + np.random.exponential(scale=mean_interval)

    current_day += timedelta(days=1)

# =========================
# 11. 저장 전 검증
# =========================
df = pd.DataFrame(logs)
df = df.sort_values("timestamp").reset_index(drop=True)

bad_rows = df[
    df["receiver_phone"].notna()
    & df["receiver_phone"].isin(spam_phones)
]

print("\n[검증] receiver_phone에 스팸 번호가 들어간 행 수:", len(bad_rows))

if len(bad_rows) > 0:
    print(bad_rows[[
        "timestamp",
        "caller_phone",
        "receiver_phone",
        "call_type"
    ]].head(30))
    raise ValueError("receiver_phone에 스팸 번호가 들어간 로그가 있습니다.")
else:
    print("OK: receiver_phone에 스팸 번호가 없습니다.")

# =========================
# 12. 저장
# =========================
df.to_csv("call_logs_final_third.csv", index=False)

print(f"\n완료: {len(df):,}건 저장 → call_logs_final_third.csv")
print(df["call_type"].value_counts())