#!/usr/bin/env python3
"""
기존 보유 종목의 purchase_info 복구 스크립트
"""

import json
from datetime import datetime
from hanlyang_stock.data.fetcher import get_data_fetcher
from hanlyang_stock.config.settings import get_hantustock

def repair_purchase_info():
    """기존 보유 종목의 purchase_info 복구"""
    print("🔧 Purchase Info 복구 시작...")
    
    # 데이터 로드
    with open('strategy_data.json', 'r') as f:
        data = json.load(f)
    
    # 현재 보유 종목 조회
    fetcher = get_data_fetcher()
    holdings = fetcher.get_holding_stock()
    
    print(f"\n📊 현재 보유 종목: {len(holdings)}개")
    
    # purchase_info가 없는 종목 확인
    missing_info_tickers = []
    for ticker in holdings:
        if ticker not in data.get('purchase_info', {}):
            missing_info_tickers.append(ticker)
            print(f"   ❌ {ticker}: purchase_info 없음")
    
    if not missing_info_tickers:
        print("\n✅ 모든 보유 종목의 purchase_info가 정상입니다.")
        return
    
    print(f"\n⚠️ purchase_info가 없는 종목: {len(missing_info_tickers)}개")
    
    # 복구 진행
    ht = get_hantustock()
    
    for ticker in missing_info_tickers:
        try:
            # 계좌 잔고에서 종목 정보 조회
            account_stocks = ht.get_stock_balance()
            
            # 해당 종목 찾기
            stock_info = None
            for stock in account_stocks:
                if stock.get('종목코드') == ticker:
                    stock_info = stock
                    break
            
            if stock_info:
                # 평균 매수가와 수량 추출
                avg_price = float(stock_info.get('평균매수가', 0))
                quantity = int(stock_info.get('보유수량', 0))
                
                if avg_price > 0 and quantity > 0:
                    # purchase_info 복구
                    purchase_info = {
                        'buy_price': avg_price,
                        'quantity': quantity,
                        'investment': avg_price * quantity,
                        'buy_date': datetime.now().isoformat(),  # 실제 매수일은 알 수 없음
                        'confidence_level': '복구됨',
                        'reset_count': 0,
                        'is_restored': True,  # 복구된 데이터임을 표시
                        'restored_date': datetime.now().isoformat()
                    }
                    
                    # 데이터에 추가
                    if 'purchase_info' not in data:
                        data['purchase_info'] = {}
                    data['purchase_info'][ticker] = purchase_info
                    
                    print(f"   ✅ {ticker} 복구 완료:")
                    print(f"      평균매수가: {avg_price:,.0f}원")
                    print(f"      보유수량: {quantity:,}주")
                    print(f"      투자금액: {avg_price * quantity:,.0f}원")
                else:
                    print(f"   ⚠️ {ticker}: 매수 정보를 찾을 수 없음")
            else:
                print(f"   ⚠️ {ticker}: 계좌 잔고에서 찾을 수 없음")
                
        except Exception as e:
            print(f"   ❌ {ticker} 복구 실패: {e}")
    
    # 데이터 저장
    with open('strategy_data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("\n💾 strategy_data.json 저장 완료!")
    print("✅ Purchase Info 복구 완료!")


if __name__ == "__main__":
    repair_purchase_info()
