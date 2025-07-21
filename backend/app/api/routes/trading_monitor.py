from fastapi import APIRouter
import sys

import os
from datetime import datetime, timedelta 
from collections import deque, defaultdict 
from app.core.deps import kis

from pykis import KisRealtimePrice, KisSubscriptionEventArgs, KisWebsocketClient
import pandas as pd 

router = APIRouter()
background_tasks = {}

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
sys.path.insert(0, backend_dir)


log_buffer = defaultdict(list)

def log(ticker: str, message: str):
    """
    프론트 서버로 뿌릴 티커별 로그를 저장하는 함수
    """
    log_buffer[ticker].append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# 상태 관리
tick_data = defaultdict(lambda: deque(maxlen=3000))  # 약 5분치 데이터 저장
positions = {} # 티커의 매수 기록용 dictionary
initial = {} # 티커의 최초 틱 수신 기록용 dictionary
last_logged_time = defaultdict(lambda: datetime.min)  # 티커별 로그 출력 시간 기록용
tickets = [] # 티커별 웹소켓 구독 티켓 관리

tick_data2 = defaultdict(lambda: deque(maxlen=3000))  # 약 5분치 데이터 저장
positions2 = {} # 티커의 매수 기록용 dictionary
initial2 = {} # 티커의 최초 틱 수신 기록용 dictionary
last_logged_time2 = defaultdict(lambda: datetime.min)  # 티커별 로그 출력 시간 기록용
tickets2 = [] # 티커별 웹소켓 구독 티켓 관리

tick_data3 = defaultdict(lambda: deque(maxlen=3000))  # 약 5분치 데이터 저장
positions3 = {} # 티커의 매수 기록용 dictionary
initial3 = {} # 티커의 최초 틱 수신 기록용 dictionary
last_logged_time3 = defaultdict(lambda: datetime.min)  # 티커별 로그 출력 시간 기록용
tickets3 = [] # 티커별 웹소켓 구독 티켓 관리


def ema(series, span):
    return pd.Series(series).ewm(span=span, adjust=False).mean().tolist()

def check_buy_signal(ticker: str, latest_price: float, latest_volume: int) -> tuple[bool, list]:
    now = datetime.now()

    # ✅ 22:30:00 ± 1분 동안은 판단 자체 skip
    if now.hour == 22 and 29 <= now.minute <= 31:
        return False, []

    three_min_ago = now - timedelta(minutes=3) # 지금으로부터 3분전 시간 기록

    # 최소 3분 이상 데이터 있어야 함
    if len(tick_data[ticker]) == 0 or (now - tick_data[ticker][0][0]).total_seconds() < 180:
        return False, []

    recent_ticks = [(ts, float(p), float(v)) for ts, p, v in tick_data[ticker] if ts >= three_min_ago] # 최근 3분 틱
    if len(recent_ticks) < 30:
        return False, [] # 최근 3분간 틱 갯수가 30개 미만이면 매수 트리거 false 반환

    df = pd.DataFrame(recent_ticks, columns=["ts", "price", "volume"])
    df["amount"] = df["price"] * df["volume"]
    df["ema_3"] = df["price"].ewm(span=3).mean()
    df["vwap"] = (df["amount"].cumsum() / df["volume"].cumsum()).fillna(0)
    df["returns"] = df["price"].pct_change()
    df["std_20"] = df["price"].rolling(20).std()
    df["bb_upper"] = df["price"].rolling(20).mean() + 2 * df["std_20"]
    df["bb_std_prev"] = df["std_20"].shift(20)

    price_now = df["price"].iloc[-1]
    ema3 = df["ema_3"].iloc[-1]
    vwap_now = df["vwap"].iloc[-1]
    highest_price = df["price"].max()
    bb_upper = df["bb_upper"].iloc[-1]
    bb_std_now = df["std_20"].iloc[-1]
    bb_std_prev = df["bb_std_prev"].iloc[-1] if len(df) >= 40 else 0
    volume_now = df["volume"].iloc[-1]
    mean_volume = df["volume"].mean()

    # ✅ VPI (Volume Pressure Index)
    if len(df) >= 100:
        vpi = df["volume"].iloc[-30:].mean() / (df["volume"].iloc[-100:-30].mean() + 1e-6)
    else:
        vpi = 1.0

    # ✅ 체결강도
    price_diff = df["price"].diff()
    uptick_ratio = (price_diff > 0).sum() / len(price_diff)

    # ✅ 3틱 연속 거래량 증가
    volume_growth = (
        df["volume"].iloc[-3] < df["volume"].iloc[-2] < df["volume"].iloc[-1]
    )

    # ✅ shadow 없는 캔들 3개
    candles = df["price"].iloc[-3:]
    shadows_ok = all(abs(candles.diff().iloc[i]) < candles.iloc[i] * 0.001 for i in range(1, 3))

    # ✅ Micro Pullback 패턴
    micro_pullback = (
        price_now >= highest_price * 0.997
        and df["price"].iloc[-3] < highest_price * 0.995
    )

    # ✅ BB squeeze breakout
    bb_squeeze = bb_std_prev < bb_std_now * 0.7 and bb_std_now > 0.15

    ### ✳️ 트리거 조건 수집
    reasons = []
    mand = 0
    opt = 0

    # 🔒 필수 조건
    if micro_pullback:
        reasons.append("🟢 Micro Pullback 후 고점 근접 재돌파")
        mand += 1
    if ema3 > vwap_now:
        reasons.append("🟢 EMA_3 > VWAP: 매수세 유입")
        mand += 1
    if volume_growth:
        reasons.append("🟢 최근 3틱 연속 거래량 증가")
        mand += 1

    # 🟡 보조 조건
    if shadows_ok:
        reasons.append("🟡 최근 3틱 shadow 없음 (강한 바디)")
        opt += 1
    if uptick_ratio > 0.3:
        reasons.append(f"🟡 체결강도 (Uptick ratio: {uptick_ratio:.2f})")
        opt += 1
    if price_now > vwap_now:
        reasons.append("🟡 VWAP 상단 위치")
        opt += 1
    if bb_squeeze:
        reasons.append("🟡 BB squeeze 이후 변동성 확장 감지")
        opt += 1

    if mand >= 2 and opt >= 1:
        return True, reasons
    else:
        return False, []

def check_buy_signal2(ticker: str, tick_data: dict) -> tuple[bool, list]:
    now = datetime.now()

    # ✅ 22:30:00 ± 1분 동안은 판단 자체 skip
    if now.hour == 22 and 29 <= now.minute <= 31:
        return False, []

    three_min_ago = now - timedelta(minutes=3) # 지금으로부터 3분전 시간 기록

    # 최소 3분 이상 데이터 있어야 함
    if len(tick_data[ticker]) == 0 or (now - tick_data[ticker][0][0]).total_seconds() < 180:
        return False, []

    recent_ticks = [(ts, float(p), float(v)) for ts, p, v in tick_data[ticker] if ts >= three_min_ago] # 최근 3분 틱
    if len(recent_ticks) < 30:
        return False, [] # 최근 3분간 틱 갯수가 30개 미만이면 매수 트리거 false 반환

    df = pd.DataFrame(recent_ticks, columns=["ts", "price", "volume"])
    df["amount"] = df["price"] * df["volume"]
    df["ema_fast"] = df["price"].ewm(span=3).mean()
    df["ema_slow"] = df["price"].ewm(span=6).mean()
    df["vwap"] = (df["amount"].cumsum() / df["volume"].cumsum()).fillna(0)
    df["returns"] = df["price"].pct_change()

    price_now = df["price"].iloc[-1]
    ema_fast = df["ema_fast"].iloc[-1]
    ema_slow = df["ema_slow"].iloc[-1]
    vwap_now = df["vwap"].iloc[-1]
    volume_now = df["volume"].iloc[-1]
    mean_volume = df["volume"].mean()
    highest_price = df["price"].max()

    price_diff = df["price"].diff()
    uptick_ratio = (price_diff > 0).iloc[-3:].mean()

    reasons = []
    score = 0

    if ema_fast > ema_slow:
        reasons.append("🟢 EMA short-term crossover detected")
        score += 1
    if price_now > vwap_now:
        reasons.append("🟢 Price above VWAP")
        score += 1
    if uptick_ratio > 0.4:
        reasons.append(f"🟢 Recent buying pressure ({uptick_ratio:.2f})")
        score += 1
    if price_now >= highest_price * 0.995:
        reasons.append("🟢 Near recent high")
        score += 1
    if volume_now > mean_volume * 1.1:
        reasons.append("🟢 Volume spike detected")
        score += 1

    return (score >= 3), reasons

def check_buy_signal3(ticker: str, tick_data: dict) -> tuple[bool, list]:
    now = datetime.now()
    five_min_ago = now - timedelta(minutes=5)

    # ✅ 22:30:00 ± 1분 동안은 판단 자체 skip
    if now.hour == 22 and 29 <= now.minute <= 31:
        return False, []

    # 충분한 히스토리 확보
    if len(tick_data[ticker]) == 0 or (now - tick_data[ticker][0][0]).total_seconds() < 300:
        return False, []

    recent_ticks = [(ts, float(p), float(v)) for ts, p, v in tick_data[ticker] if ts >= five_min_ago]
    if len(recent_ticks) < 50:
        return False, []

    df = pd.DataFrame(recent_ticks, columns=["ts", "price", "volume"])
    df["amount"] = df["price"] * df["volume"]
    df["ema_3"] = df["price"].ewm(span=3).mean()
    df["ema_8"] = df["price"].ewm(span=8).mean()
    df["ema_21"] = df["price"].ewm(span=21).mean()
    df["std_20"] = df["price"].rolling(20).std()
    df["bb_upper"] = df["price"].rolling(20).mean() + 2 * df["std_20"]
    df["bb_lower"] = df["price"].rolling(20).mean() - 2 * df["std_20"]
    df["vwap"] = (df["amount"].cumsum() / df["volume"].cumsum()).fillna(0)
    df["returns"] = df["price"].pct_change()

    # 현재값
    price_now = df["price"].iloc[-1]
    ema_3 = df["ema_3"].iloc[-1]
    ema_8 = df["ema_8"].iloc[-1]
    ema_21 = df["ema_21"].iloc[-1]
    vwap_now = df["vwap"].iloc[-1]
    bb_upper = df["bb_upper"].iloc[-1]
    bb_std_now = df["std_20"].iloc[-1]
    bb_std_prev = df["std_20"].iloc[-20] if len(df) >= 40 else 0
    volume_now = df["volume"].iloc[-1]
    mean_volume = df["volume"].mean()
    highest = df["price"].max()

    price_diff = df["price"].diff()
    uptick_ratio = (price_diff > 0).sum() / len(price_diff)

    # 🧠 조건들
    reasons = []
    pass_count = 0

    # (1) 정배열: EMA3 > EMA8 > EMA21
    if ema_3 > ema_8 > ema_21:
        reasons.append("🟢 EMA 정배열 확인")
        pass_count += 1

    # (2) VWAP 위 + EMA_3도 VWAP 위
    if price_now > vwap_now and ema_3 > vwap_now:
        reasons.append("🟢 VWAP 위 정착 + EMA도 위에 위치")
        pass_count += 1

    # (3) 볼린저 수축 후 확장 → breakout 징후
    if bb_std_prev < bb_std_now * 0.7 and bb_std_now > 0.15:
        reasons.append("🟢 BB 수축 후 확장")
        pass_count += 1

    # (4) 최근 고점 대비 0.2% 이내 (돌파 시도)
    if price_now >= highest * 0.998:
        reasons.append(f"🟢 고점 돌파 직전 (고점: {highest:.2f})")
        pass_count += 1

    # (5) 체결강도 uptick ratio > 0.6
    if uptick_ratio > 0.6:
        reasons.append(f"🟢 체결강도 확실 (uptick ratio: {uptick_ratio:.2f})")
        pass_count += 1

    # (6) 거래량 최근 급증 (틱당 평균 대비 1.5배)
    if volume_now > mean_volume * 1.5:
        reasons.append("🟢 틱당 평균 거래량 대비 1.5배 이상")
        pass_count += 1

    return (pass_count >= 5), reasons

def check_monitoring_shutdown():
    """ 
    모든 종목에 대해 매매가 종료되면 웹소켓 티켓 구독 취소 
    그러나 백테스팅 기간 동안은 모니터링을 위해 매매 종료 대신 모든 종목에 대한 틱 업데이트가 더 이상 진행되지 않을 때 티켓 구독 취소
    """
    #if not positions:  # 모든 종목이 매수 매도를 거치면
    if not initial: # 모든 종목에 대한 틱 업데이트가 더 이상 진행되지 않을 때
        print("✅ 모든 종목 거래 종료됨. 모니터링 중단.")
        log("SYSTEM", "✅ 모든 종목 거래 종료됨. 모니터링 중단.") # 자동매매가 종료되었다는 정보를 프론트에 뿌릴 로그를 담은 Dictionary에 저장
        for ticket in tickets:
            ticket.unsubscribe() # 티켓 구독 취소
        tickets.clear()

def check_monitoring_shutdown2():
    """ 
    모든 종목에 대해 매매가 종료되면 웹소켓 티켓 구독 취소 
    그러나 백테스팅 기간 동안은 모니터링을 위해 매매 종료 대신 모든 종목에 대한 틱 업데이트가 더 이상 진행되지 않을 때 티켓 구독 취소
    """
    #if not positions:  # 모든 종목이 매수 매도를 거치면
    if not initial2: # 모든 종목에 대한 틱 업데이트가 더 이상 진행되지 않을 때
        print("✅ 모든 종목 거래 종료됨. 모니터링 중단.")
        log("SYSTEM", "✅ 모든 종목 거래 종료됨. 모니터링 중단.") # 자동매매가 종료되었다는 정보를 프론트에 뿌릴 로그를 담은 Dictionary에 저장
        for ticket in tickets2:
            ticket.unsubscribe() # 티켓 구독 취소
        tickets2.clear()

def check_monitoring_shutdown3():
    """ 
    모든 종목에 대해 매매가 종료되면 웹소켓 티켓 구독 취소 
    그러나 백테스팅 기간 동안은 모니터링을 위해 매매 종료 대신 모든 종목에 대한 틱 업데이트가 더 이상 진행되지 않을 때 티켓 구독 취소
    """
    #if not positions:  # 모든 종목이 매수 매도를 거치면
    if not initial3: # 모든 종목에 대한 틱 업데이트가 더 이상 진행되지 않을 때
        print("✅ 모든 종목 거래 종료됨. 모니터링 중단.")
        log("SYSTEM", "✅ 모든 종목 거래 종료됨. 모니터링 중단.") # 자동매매가 종료되었다는 정보를 프론트에 뿌릴 로그를 담은 Dictionary에 저장
        for ticket in tickets3:
            ticket.unsubscribe() # 티켓 구독 취소
        tickets3.clear()

def write_reasons_log(reasons, ticker):
    os.makedirs("logs/strategy1", exist_ok=True)
    filename = f"logs/strategy1/trade_log_{ticker}.txt"
    with open(filename, "a") as f:
        f.write(f"매수 사유 : {[reason for reason in reasons]}")

def write_reasons_log2(reasons, ticker):
    os.makedirs("logs/strategy2", exist_ok=True)
    filename = f"logs/strategy2/trade_log_{ticker}.txt"
    with open(filename, "a") as f:
        f.write(f"매수 사유 : {[reason for reason in reasons]}")

def write_reasons_log3(reasons, ticker):
    os.makedirs("logs/strategy3", exist_ok=True)
    filename = f"logs/strategy3/trade_log_{ticker}.txt"
    with open(filename, "a") as f:
        f.write(f"매수 사유 : {[reason for reason in reasons]}")

def write_trade_log(ticker, buy_time, sell_time, buy_price, sell_price, return_pct, result):
    """
    자동매매 시나리오 수익률 백테스팅을 위한 로컬 로그 기록용 함수
    """
    os.makedirs("logs/strategy1", exist_ok=True)
    filename = f"logs/strategy1/trade_log_{ticker}.txt"
    duration = (sell_time - buy_time).total_seconds()

    with open(filename, "a") as f:
        f.write(f"[{result}] {ticker}\n")
        f.write(f" - 매수 시간: {buy_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f" - 매도 시간: {sell_time.strftime('%Y-%m-%d %H:%M:%S')} (소요: {duration:.1f}초)\n")
        f.write(f" - 매수 가격: {buy_price:.2f}\n")
        f.write(f" - 매도 가격: {sell_price:.2f}\n")
        f.write(f" - 수익률: {return_pct:.2f}%\n")
        f.write("-" * 40 + "\n")

def write_trade_log2(ticker, buy_time, sell_time, buy_price, sell_price, return_pct, result):
    """
    자동매매 시나리오 수익률 백테스팅을 위한 로컬 로그 기록용 함수
    """
    os.makedirs("logs/strategy2", exist_ok=True)
    filename = f"logs/strategy2/trade_log_{ticker}.txt"
    duration = (sell_time - buy_time).total_seconds()

    with open(filename, "a") as f:
        f.write(f"[{result}] {ticker}\n")
        f.write(f" - 매수 시간: {buy_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f" - 매도 시간: {sell_time.strftime('%Y-%m-%d %H:%M:%S')} (소요: {duration:.1f}초)\n")
        f.write(f" - 매수 가격: {buy_price:.2f}\n")
        f.write(f" - 매도 가격: {sell_price:.2f}\n")
        f.write(f" - 수익률: {return_pct:.2f}%\n")
        f.write("-" * 40 + "\n")

def write_trade_log3(ticker, buy_time, sell_time, buy_price, sell_price, return_pct, result):
    """
    자동매매 시나리오 수익률 백테스팅을 위한 로컬 로그 기록용 함수
    """
    os.makedirs("logs/strategy3", exist_ok=True)
    filename = f"logs/strategy3/trade_log_{ticker}.txt"
    duration = (sell_time - buy_time).total_seconds()

    with open(filename, "a") as f:
        f.write(f"[{result}] {ticker}\n")
        f.write(f" - 매수 시간: {buy_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f" - 매도 시간: {sell_time.strftime('%Y-%m-%d %H:%M:%S')} (소요: {duration:.1f}초)\n")
        f.write(f" - 매수 가격: {buy_price:.2f}\n")
        f.write(f" - 매도 가격: {sell_price:.2f}\n")
        f.write(f" - 수익률: {return_pct:.2f}%\n")
        f.write("-" * 40 + "\n")

# 웹소켓 콜백
def on_price(sender: KisWebsocketClient, e: KisSubscriptionEventArgs[KisRealtimePrice]):
    ticker = e.response.symbol
    price = e.response.price 
    volume = e.response.volume
    now = datetime.now()

    tick_data[ticker].append((now, price, volume))
    initial[ticker] = 'yes' # 모니터링 시작 후 1틱 들어온 순간 티커별로 기록

    tick_data2[ticker].append((now, price, volume))
    initial2[ticker] = 'yes'

    tick_data3[ticker].append((now, price, volume))
    initial3[ticker] = 'yes'


    if ticker not in positions : # 아직 매수 안된 티커라면
        if (now - last_logged_time[ticker]).total_seconds() >= 10: # 10초에 한 번씩
            last_logged_time[ticker] = now
            log(ticker, f"Price: {price} | Volume: {volume}") # 해당 틱의 가격과 거래량에 대한 정보를 프론트로 뿌릴 로그 dicitonary에 저장

        triggered, reasons = check_buy_signal(ticker, price, volume) # 매수 트리거 발동 여부 판별

        if triggered : # 트리거가 발동 됐으면
            write_reasons_log(reasons, ticker)
            #### 여기에 실제 매수 코드 붙이기 ####
            positions[ticker] = {"buy_price": price, "buy_time": now} # 티커의 매수 기록용 dictionary에 매수 가격과 매수 시간 기록
            del initial[ticker] # 티커의 최초 틱 기록용 dictionary에서 매수 된 티커 제거
            print(f"\n🚀 [매수 트리거 발동] 가격: {price:.2f}\n📋 매수 사유:\n{[reason for reason in reasons]}")
            log(ticker, f"\n🚀 [매수 트리거 발동] 가격: {price:.2f}\n📋 매수 사유:\n{[reason for reason in reasons]}") # 매수 된 티커의 매수 가격과 매수 사유에 대한 정보를 프론트로 뿌릴 로그 Dictionary에 저장

    else: # 이미 매수 된 티커라면
        buy_price = positions[ticker]['buy_price'] # 매수가격
        buy_time = positions[ticker]['buy_time']  # 매수 시간
        rtn = (price - buy_price) / buy_price * 100 # 수익률 계신
        duration = (now - buy_time).total_seconds() # 매수 후 경과시간 계산

        if (now - last_logged_time[ticker]).total_seconds() >= 10: # 10초에 한 번씩
            last_logged_time[ticker] = now
            print(f"💹 [수익률 추적]: 현재가 {price:.2f} | 매수가 {buy_price:.2f} | 수익률 {rtn:+.2f}% | 매수 후 {duration}초 경과")
            log(ticker, f"💹 [수익률 추적]: 현재가 {price:.2f} | 매수가 {buy_price:.2f} | 수익률 {rtn:+.2f}% | 매수 후 {duration}초 경과") # 매수 된 티커의 매수 가격, 수익률, 매수 후 경과시간에 대한 정보를 프론트로 뿌릴 로그 Dictionary에 저장 

        # 1. 익절
        if rtn > 0.5: # 수익률이 0.5% 초과일 경우
            print(f"🎯 [익절] +0.5% 초과! 현재 수익률: {rtn:.2f}%")
            #### 이곳에 실제 매도 코드 붙이기 ####
            log(ticker, f"🎯 [익절] +0.5% 초과! 현재 수익률: {rtn:.2f}%") # 0.5% 수익 발생하여 익절했다는 정보를 프론트에 뿌릴 로그 dictionary에 저장
            write_trade_log(ticker, buy_time, now, buy_price, price, rtn, "+0.5%이상 익절") # 백테스팅을 위해 로컬 로그에 저장
            del positions[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            check_monitoring_shutdown()
            return

        # 2. 손절
        if rtn < -0.3: # 수익률이 -0.3% 미만일 경우
            print(f"🎯 [손절] -0.3% 초과! 현재 수익률: {rtn:.2f}%")
            #### 이곳에 실제 매도 코드 붙이기 ####
            log(ticker, f"🎯 [손절] -0.3% 초과! 현재 수익률: {rtn:.2f}%") # -0.3% 손실 발생하여 손절했다는 정보를 프론트에 뿌릴 로그 dictionary에 저장
            write_trade_log(ticker, buy_time, now, buy_price, price, rtn, "-0.3%이상 손절") # 백테스팅을 위해 로컬 로그에 저장
            del positions[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            check_monitoring_shutdown()
            return

        # X분 내 익절 또는 손절라인 터치 실패
        X = 3
        sec = 60 * X
        if duration >= sec:
            print(f"💥 [{X}분 경과] +0.5% 도달 실패. 현재 수익률: {rtn:.2f}%")
            #### 이곳에 실제 매도 코드 붙이기 ####
            log(ticker, f"💥 [{X}분 경과] +0.5% 도달 실패. 현재 수익률: {rtn:.2f}%") # X분 내 매도하지 못했다는 정보를 프론트에 뿌릴 로그 Dictionary에 저장
            write_trade_log(ticker, buy_time, now, buy_price, price, rtn, f"{X}분 후 자동 매도") # 백테스팅을 위해 로컬 로그에 저장
            del positions[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            check_monitoring_shutdown()
            return

    if ticker not in positions2 : # 아직 매수 안된 티커라면
        if (now - last_logged_time2[ticker]).total_seconds() >= 10: # 10초에 한 번씩
            last_logged_time2[ticker] = now
        
        triggered, reasons = check_buy_signal2(ticker, tick_data2) # 매수 트리거 발동 여부 판별
        
        if triggered : # 트리거가 발동 됐으면
            write_reasons_log2(reasons, ticker)
            #### 여기에 실제 매수 코드 붙이기 ####
            positions2[ticker] = {"buy_price": price, "buy_time": now} # 티커의 매수 기록용 dictionary에 매수 가격과 매수 시간 기록
            del initial2[ticker] # 티커의 최초 틱 기록용 dictionary에서 매수 된 티커 제거

    else: # 이미 매수 된 티커라면
        buy_price = positions2[ticker]['buy_price'] # 매수가격
        buy_time = positions2[ticker]['buy_time']  # 매수 시간
        rtn = (price - buy_price) / buy_price * 100 # 수익률 계신
        duration = (now - buy_time).total_seconds() # 매수 후 경과시간 계산

        if (now - last_logged_time2[ticker]).total_seconds() >= 10: # 10초에 한 번씩
            last_logged_time2[ticker] = now

        # 1. 익절
        if rtn > 0.5: # 수익률이 0.5% 초과일 경우
            write_trade_log2(ticker, buy_time, now, buy_price, price, rtn, "+0.5%이상 익절") # 백테스팅을 위해 로컬 로그에 저장
            del positions2[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            return

        # 2. 손절
        if rtn < -0.3: # 수익률이 -0.3% 미만일 경우
            write_trade_log2(ticker, buy_time, now, buy_price, price, rtn, "-0.3%이상 손절") # 백테스팅을 위해 로컬 로그에 저장
            del positions2[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            return

        # X분 내 익절 또는 손절라인 터치 실패
        X = 3
        sec = 60 * X
        if duration >= sec:
            write_trade_log2(ticker, buy_time, now, buy_price, price, rtn, f"{X}분 후 자동 매도") # 백테스팅을 위해 로컬 로그에 저장
            del positions2[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            return

    if ticker not in positions3 : # 아직 매수 안된 티커라면
        if (now - last_logged_time3[ticker]).total_seconds() >= 10: # 10초에 한 번씩
            last_logged_time3[ticker] = now

        triggered, reasons = check_buy_signal3(ticker, tick_data3) # 매수 트리거 발동 여부 판별
        
        if triggered : # 트리거가 발동 됐으면
            write_reasons_log2(reasons, ticker)
            #### 여기에 실제 매수 코드 붙이기 ####
            positions3[ticker] = {"buy_price": price, "buy_time": now} # 티커의 매수 기록용 dictionary에 매수 가격과 매수 시간 기록
            del initial3[ticker] # 티커의 최초 틱 기록용 dictionary에서 매수 된 티커 제거

    else: # 이미 매수 된 티커라면
        buy_price = positions3[ticker]['buy_price'] # 매수가격
        buy_time = positions3[ticker]['buy_time']  # 매수 시간
        rtn = (price - buy_price) / buy_price * 100 # 수익률 계신
        duration = (now - buy_time).total_seconds() # 매수 후 경과시간 계산

        if (now - last_logged_time3[ticker]).total_seconds() >= 10: # 10초에 한 번씩
            last_logged_time3[ticker] = now

        # 1. 익절
        if rtn > 0.5: # 수익률이 0.5% 초과일 경우
            write_trade_log3(ticker, buy_time, now, buy_price, price, rtn, "+0.5%이상 익절") # 백테스팅을 위해 로컬 로그에 저장
            del positions3[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            return

        # 2. 손절
        if rtn < -0.3: # 수익률이 -0.3% 미만일 경우
            write_trade_log3(ticker, buy_time, now, buy_price, price, rtn, "-0.3%이상 손절") # 백테스팅을 위해 로컬 로그에 저장
            del positions3[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            return

        # X분 내 익절 또는 손절라인 터치 실패
        X = 3
        sec = 60 * X
        if duration >= sec:
            write_trade_log3(ticker, buy_time, now, buy_price, price, rtn, f"{X}분 후 자동 매도") # 백테스팅을 위해 로컬 로그에 저장
            del positions3[ticker] # 매수 기록용 티커에서 매도 완료된 티커 제거
            return


# FastAPI endpoint
@router.post("/start_monitoring")
async def start_monitoring(data: dict):
    """
    자동매매 에이전트로부터 사용자가 입력한 티커와 예산 수신함 
    """
    tickers = data.get("tickers", [])
    budget = data.get("budget", 0)
    print(f"\n✅ 모니터링 시작: {tickers}")

    for ticker in tickers: 
        tickets.append(kis.stock(ticker).on("price", on_price)) # 티커별 웹소켓 구독 티켓 저장

    return {"status": "monitoring_started", "tickers": tickers}

@router.get("/monitoring_status")
def get_monitoring_status():
    """ 
    프론트엔드 서버에 로그 dictionary 전달
    """
    response = {}
    for ticker, ticks in tick_data.items():
        if ticker in positions:
            buy_price = positions[ticker]['buy_price']
            latest_price = ticks[-1][1]
            rtn = (latest_price - buy_price) / buy_price * 100
            response[ticker] = {
                "status": "holding",
                "price": latest_price,
                "buy_price": buy_price,
                "return": rtn
            }
        else:
            response[ticker] = {
                "status": "monitoring",
                "price": ticks[-1][1] if ticks else 0.0
            }
    return {
        "status": "ok",
        "logs": log_buffer,  
        "tickers": response
    }