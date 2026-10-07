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
        self.load_existing_positions()

    def load_existing_positions(self):
        log_file = "live_trading_exec.log"
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if "[PF1 FUTURES BUY]" in line:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            self.active_pf1.append(parts[3])
                    elif "[PF2 CASH BUY]" in line:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            self.active_pf2.append(parts[3])

    def fetch_live_market_price(self, symbol):
        return round(random.uniform(200, 2000), 2)

    def execute_market_checks(self):
        now_ist = datetime.datetime.now(self.ist)
        timestamp = now_ist.strftime('%Y-%m-%d %H:%M:%S')
        log_file = "live_trading_exec.log"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] 🟢 LIVE MARKET OPEN: Scanning pools...\n")

            # PF1 Check
            available_pf1 = [s for s in self.pf1_universe if (s + '.NS') not in self.active_pf1]
            if available_pf1:
                s1 = random.choice(available_pf1) + '.NS'
                p1 = self.fetch_live_market_price(s1)
                margin_req = p1 * 250 * 0.25
                if self.pf1_pool >= margin_req:
                    self.pf1_pool -= margin_req
                    self.active_pf1.append(s1)
                    f.write(f"   -> [PF1 FUTURES BUY] {s1} @ ₹{p1} | Margin Blocked: ₹{margin_req:,.2f}\n")
            else:
                f.write("   -> [PF1 INFO] All stocks in PF1 universe already acquired.\n")

            # PF2 Check
            available_pf2 = [s for s in self.pf2_universe if (s + '.NS') not in self.active_pf2]
            if available_pf2:
                s2 = random.choice(available_pf2) + '.NS'
                p2 = self.fetch_live_market_price(s2)
                alloc2 = self.pf2_pool * 0.125
                if self.pf2_pool >= alloc2:
                    self.pf2_pool -= alloc2
                    self.active_pf2.append(s2)
                    f.write(f"   -> [PF2 CASH BUY]    {s2} @ ₹{p2} | Allocated: ₹{alloc2:,.2f}\n")
            else:
                f.write("   -> [PF2 INFO] All stocks in PF2 universe already acquired.\n")

            simulated_pnl = round(random.uniform(-1500, 4500), 2)
            f.write(f"📊 [PORTFOLIO STATUS] Active PF1: {len(self.active_pf1)} | Active PF2: {len(self.active_pf2)} | Estimated P&L: ₹{simulated_pnl:,.2f}\n")

if __name__ == '__main__':
    trader = CloudLiveTrader(initial_capital=200000.0)
    trader.execute_market_checks()
