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
    # 보안의 이유로 데이터 공유 불가
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
    # 보안의 이유로 데이터 공유 불가
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
    # 보안의 이유로 데이터 공유 불가
}

transaction_persona_template = {
    # 보안의 이유로 데이터 공유 불가
}

# =========================
# 4. 페르소나
# =========================
call_persona_template = {
    # 보안의 이유로 데이터 공유 불가
}

# =========================
# 5. 수신자 선택
# =========================
chain_handover_done = set()

spam_targets = [
    u for u in users
    # 보안의 이유로 데이터 공유 불가
]

chain_map = {
    # 보안의 이유로 데이터 공유 불가
}

def choose_receiver(caller, timestamp):
    p_type = users[caller]["type"]

    # 스팸 발신자는 전화는 걸 수 있지만, 수신자는 절대 스팸이면 안 됨
    if p_type == "스팸":
        candidates = [
            u for u in users
            if u != caller
            and users[u]["type"] != "스팸"
            # 보안의 이유로 데이터 공유 불가
        ]

        if not candidates:
            candidates = [
                u for u in users
                # 보안의 이유로 데이터 공유 불가
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
            # 보안의 이유로 데이터 공유 불가
        ):
            chain_handover_done.add(caller)
            # 보안의 이유로 데이터 공유 불가

    # 관계 기반 후보
    candidates = [
        u for u in relations.get(caller, set())
        if u in users
        and u != caller
        # 보안의 이유로 데이터 공유 불가
    ]

    # fallback 후보
    if not candidates:
        candidates = [
            u for u in users
            if u != caller
            # 보안의 이유로 데이터 공유 불가
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
     # 보안의 이유로 데이터 공유 불가
]

spam_users_list = [
    row["name"] for _, row in scenario_df.iterrows()
    if row["type"] == "스팸"
]

for spam_name in spam_users_list:
    ueS.append({
     # 보안의 이유로 데이터 공유 불가
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
            # 보안의 이유로 데이터 공유 불가
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

                ##보안으로 인해 데이터 공유 불가

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
        # 보안의 이유로 데이터 공유 불가
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