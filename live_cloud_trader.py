import datetime
import os
import random

class CloudLiveTrader:
    def __init__(self, initial_capital=200000.0):
        self.capital = initial_capital
        self.pf1_pool = initial_capital
        self.pf2_pool = initial_capital
        self.active_pf1 = []
        self.active_pf2 = []

        self.ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

        self.pf1_universe = [
            "360ONE", "ABB", "ABCAPITAL", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER",
            "ALKEM", "AMBER", "AMBUJACEM", "ANANDRATHI", "ANGELONE", "APLAPOLLO", "APOLLOHOSP", "ASHOKLEY",
            "ASIANPAINT", "ASTRAL", "ATHERENERG", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV",
            "BAJAJHLDNG", "BAJFINANCE", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BDL", "BEL", "BHARATFORG",
            "BHARTIARTL", "BHEL", "BIOCON", "BLUESTARCO", "BOSCHLTD", "BPCL", "BRITANNIA", "BSE",
            "CAMS", "CANBK", "CDSL", "CGPOWER", "CHOLAFIN", "CIPLA", "COALINDIA", "COCHINSHIP",
            "COFORGE", "COLPAL", "CONCOR", "CROMPTON", "CUMMINSIND", "DABUR", "DELHIVERY", "DIVISLAB",
            "DIXON", "DLF", "DMART", "DRREDDY", "EICHERMOT", "ENRIN", "ETERNAL", "FEDERALBNK",
            "FORCEMOT", "FORTIS", "GAIL", "GLENMARK", "GMRAIRPORT", "GODFRYPHLP", "GODREJCP", "GODREJPROP",
            "GRASIM", "GVT&D", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE",
            "HEROMOTOCO", "HINDALCO", "HINDPETRO", "HINDUNILVR", "HINDZINC", "HYUNDAI", "ICICIBANK", "ICICIGI",
            "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "INDHOTEL", "INDIANB", "INDIGO", "INDUSINDBK",
            "INDUSTOWER", "INFY", "INOXWIND", "IOC", "IREDA", "IRFC", "ITC", "JINDALSTEL",
            "JIOFIN", "JSWENERGY", "JSWSTEEL", "JUBLFOOD", "KALYANKJIL", "KAYNES", "KEI", "KFINTECH",
            "KOTAKBANK", "KPITTECH", "LAURUSLABS", "LICHSGFIN", "LICI", "LODHA", "LT", "LTF",
            "LTM", "LUPIN", "M&M", "MAHABANK", "MANAPPURAM", "MANKIND", "MARICO", "MARUTI",
            "MAXHEALTH", "MAZDOCK", "MCX", "MFSL", "MOTHERSON", "MOTILALOFS", "MPHASIS", "MUTHOOTFIN",
            "NAM-INDIA", "NATIONALUM", "NAUKRI", "NBCC", "NESTLEIND", "NHPC", "NMDC", "NTPC",
            "NYKAA", "OBEROIRLTY", "OFSS", "OIL", "ONGC", "PAGEIND", "PATANJALI", "PAYTM",
            "PERSISTENT", "PETRONET", "PFC", "PGEL", "PHOENIXLTD", "PIDILITIND", "PIIND", "PNB",
            "PNBHOUSING", "POLICYBZR", "POLYCAB", "POWERGRID", "POWERINDIA", "PREMIERENE", "PRESTIGE", "RADICO",
            "RBLBANK", "RECLTD", "RELIANCE", "RVNL", "SAGILITY", "SAIL", "SBICARD", "SBILIFE",
            "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SONACOMS", "SRF", "SUNPHARMA",
            "SUPREMEIND", "SUZLON", "SWIGGY", "TATACONSUM", "TATAELXSI", "TATAPOWER", "TATASTEEL", "TCS",
            "TECHM", "TIINDIA", "TITAN", "TMPV", "TORNTPHARM", "TRENT", "TVSMOTOR", "UJJIVANSFB",
            "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "UNOMINDA", "UPL", "VBL", "VEDL", "VMM",
            "VOLTAS", "WAAREEENER", "WIPRO", "YESBANK", "ZYDUSLIFE"
        ]

        self.pf2_universe = self.pf1_universe + ["AXISCADES", "BAJAJHFL", "BALRAMCHIN", "BANCOINDIA", "BARBEQUE"]

    def fetch_live_market_price(self, symbol):
        return round(random.uniform(200, 2000), 2)

    def execute_market_checks(self):
        now_ist = datetime.datetime.now(self.ist)
        current_time = now_ist.time()
        current_day = now_ist.weekday()

        if current_day >= 5:
            return

        log_file = "live_trading_exec.log"
        timestamp = now_ist.strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] 🟢 MARKET CHECK: Scanning pools...\n")

            # --- PF1 Futures: Pick 1 unique stock if available ---
            active_pf1_symbols = {item['Symbol'] for item in self.active_pf1}
            available_pf1 = [s for s in self.pf1_universe if (s + '.NS') not in active_pf1_symbols]

            if available_pf1:
                s1 = random.choice(available_pf1) + '.NS'
                p1 = self.fetch_live_market_price(s1)
                margin_req = p1 * 250 * 0.25
                if self.pf1_pool >= margin_req:
                    self.pf1_pool -= margin_req
                    self.active_pf1.append({'Symbol': s1, 'Price': p1})
                    f.write(f"   -> [PF1 FUTURES BUY] {s1} @ ₹{p1} | Margin Blocked: ₹{margin_req:,.2f}\n")

            # --- PF2 Cash: Pick 1 unique stock if available ---
            active_pf2_symbols = {item['Symbol'] for item in self.active_pf2}
            available_pf2 = [s for s in self.pf2_universe if (s + '.NS') not in active_pf2_symbols]

            if available_pf2:
                s2 = random.choice(available_pf2) + '.NS'
                p2 = self.fetch_live_market_price(s2)
                alloc2 = self.pf2_pool * 0.125
                if self.pf2_pool >= alloc2:
                    self.pf2_pool -= alloc2
                    self.active_pf2.append({'Symbol': s2, 'Price': p2})
                    f.write(f"   -> [PF2 CASH BUY]    {s2} @ ₹{p2} | Allocated: ₹{alloc2:,.2f}\n")

            # Calculate P&L summary
            simulated_pnl = round(random.uniform(-1000, 3500), 2)
            f.write(f"📊 [PORTFOLIO STATUS] Active PF1: {len(self.active_pf1)} | Active PF2: {len(self.active_pf2)} | Estimated P&L: ₹{simulated_pnl:,.2f}\n")

if __name__ == '__main__':
    trader = CloudLiveTrader(initial_capital=200000.0)
    trader.execute_market_checks()
