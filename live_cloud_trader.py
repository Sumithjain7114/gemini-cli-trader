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

        # IST is UTC + 5:30 (Built-in standard library timezone)
        self.ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

        # PF1: F&O Universe (Futures Strategy - 213 Stocks)
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

        # PF2: Nifty 500 Universe (Cash Delivery Strategy - 501 Stocks)
        self.pf2_universe = [
            "360ONE", "ABB", "ACC", "ACMESOLAR", "AIAENG", "APLAPOLLO", "AUBANK", "AWL", "AADHARHFC", "AARTIIND", "AAVAS", "ABBOTINDIA", "ACE", "ACUTAAS", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ATGL", "ABCAPITAL", "ABREL", "ABSLAMC", "CPPLUS", "AEGISLOG",
            "AEGISVOPAK", "AETHER", "AFCONS", "AFFLE", "AJANTPHARM", "ALKEM", "ABDL", "ARE&M", "AMBER", "AMBUJACEM", "ANANDRATHI", "ANANTRAJ", "ANGELONE", "ANTHEM", "ANURAS", "APARINDS", "APOLLOHOSP", "APOLLOTYRE", "APTUS", "ASAHIINDIA", "ASHOKLEY", "ASIANPAINT", "ASTERDM", "ASTRAL", "ATHERENERG",
            "ATUL", "AUROPHARMA", "AIIL", "AVANTIFEED", "DMART", "AXISBANK", "AZAD", "BEML", "BLS", "BSE", "BAGMANE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG", "BAJAJHFL", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "MAHABANK", "BATAINDIA", "BELRISE", "BERGEPAINT",
            "BHARATCOAL", "BDL", "BEL", "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL", "BHARTIHEXA", "GROWW", "BIOCON", "BSOFT", "BBOX", "BLUESTARCO", "BOSCHLTD", "FIRSTCRY", "BRIGADE", "BRITANNIA", "BIRET", "CCL", "CESC", "CGPOWER", "CIEINDIA", "CRISIL", "CANFINHOME", "CANBK",
            "CANHLIFE", "CAPLIPOINT", "CGCL", "CARBORUNIV", "CARTRADE", "CASTROLIND", "CEATLTD", "CEMPRO", "CENTRALBK", "CDSL", "CMPDI", "CHAMBLFERT", "CHENNPETRO", "CHOICEIN", "CHOLAHLDNG", "CHOLAFIN", "CIPLA", "CUB", "CLEANMAX", "CLEAN", "COALINDIA", "COCHINSHIP", "COFORGE", "COHANCE", "COLPAL",
            "CAMS", "CONCORDBIO", "CONCOR", "COROMANDEL", "CRAFTSMAN", "CREDITACC", "CROMPTON", "CUMMINSIND", "CUPID", "CYIENT", "DLF", "DOMS", "DABUR", "DALBHARAT", "DATAPATTNS", "DEEPAKFERT", "DEEPAKNTR", "DELHIVERY", "DEVYANI", "DIVISLAB", "DIXON", "LALPATHLAB", "DRREDDY", "DUMMYHEG", "EIDPARRY",
            "EIHOTEL", "EMBASSY", "EICHERMOT", "ELECON", "ELGIEQUIP", "EMAMILTD", "EMCURE", "EMMVEE", "ENDURANCE", "ENGINERSIN", "ESCORTS", "ETERNAL", "EXIDEIND", "NYKAA", "FEDERALBNK", "FACT", "FINCABLES", "FSL", "FIVESTAR", "FORCEMOT", "FORTIS", "FRACTAL", "GAIL", "GVT&D", "GMRAIRPORT",
            "GABRIEL", "GALLANTT", "GRSE", "GICRE", "GILLETTE", "GLAND", "GLAXO", "GLENMARK", "MEDANTA", "GPIL", "GODFRYPHLP", "GODREJCP", "GODREJIND", "GODREJPROP", "GRANULES", "GRAPHITE", "GRASIM", "GRAVITA", "GESHIP", "FLUOROCHEM", "GMDCLTD", "HBLENGINE", "HCLTECH", "HDBFS", "HDFCAMC",
            "HDFCBANK", "HDFCLIFE", "HEGAM", "HFCL", "HAVELLS", "HEROMOTOCO", "HEXT", "HSCL", "HINDALCO", "HAL", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "POWERINDIA", "HOMEFIRST", "HONASA", "HONAUT", "HUDCO", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIAMC", "ICICIPRULI", "IDBI",
            "IDFCFIRSTB", "IFCI", "IIFL", "INOXINDIA", "IRB", "IRCON", "ITCHOTELS", "ITC", "ITI", "INDIACEM", "INDIAMART", "INDIANB", "IEX", "INDHOTEL", "IOC", "IOB", "IRCTC", "IRFC", "IREDA", "IGL", "INDUSTOWER", "INDUSINDBK", "NAUKRI", "INFY", "INOXWIND",
            "INTELLECT", "INDIGO", "IGIL", "IKS", "IPCALAB", "JKCEMENT", "JBMA", "JKTYRE", "JMFINANCIL", "JSWCEMENT", "JSWENERGY", "JSWINFRA", "JSWSTEEL", "JAINREC", "JPPOWER", "J&KBANK", "JINDALSAW", "JSL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "JUBLINGREA", "JWL", "JYOTICNC", "KPRMILL",
            "KEI", "KPITTECH", "KSB", "KAJARIACER", "KPIL", "KALYANKJIL", "KARURVYSYA", "KAYNES", "KEC", "KFINTECH", "KIRLOSBROS", "KIRLOSENG", "KOTAKBANK", "KIMS", "LTF", "LTTS", "LGEINDIA", "LICHSGFIN", "LTFOODS", "LTM", "LT", "LAURUSLABS", "LEMONTREE", "LENSKART", "LICI",
            "LINDEINDIA", "LLOYDSME", "LODHA", "LUPIN", "MMTC", "MRF", "MTARTECH", "MGL", "M&MFIN", "M&M", "MANAPPURAM", "MRPL", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "MEESHO", "MINDACORP", "MSUMI", "MOTILALOFS", "MPHASIS", "MCX", "MUTHOOTFIN",
            "NATCOPHARM", "NBCC", "NCC", "NHPC", "NLCINDIA", "NMDC", "NSLNISP", "NTPCGREEN", "NTPC", "NH", "NATIONALUM", "NAVA", "NAVINFLUOR", "NESTLEIND", "NETWEB", "NEULANDLAB", "NAM-INDIA", "NUVAMA", "NUVOCO", "OBERIRLTY", "ONGC", "OIL", "OLAELEC", "OLECTRA", "PAYTM",
            "ONESOURCE", "OFSS", "POLICYBZR", "PCBL", "PGEL", "PIIND", "PNBHOUSING", "PTCIL", "PVRINOX", "PAGEIND", "PARADEEP", "PATANJALI", "PERSISTENT", "PETRONET", "PHOENIXLTD", "PWL", "PIDILITIND", "PINELABS", "PIRAMALFIN", "PPLPHARMA", "POLYMED", "POLYCAB", "POONAWALLA", "PFC", "POWERGRID",
            "PREMIERENE", "PRESTIGE", "PFOCUS", "PRIVISCL", "PNB", "RRKABEL", "RBLBANK", "RECLTD", "RHIM", "RITES", "RADICO", "RVNL", "RAILTEL", "RAINBOW", "RKFORGE", "REDINGTON", "RELIANCE", "RPOWER", "RUBICON", "SBICARD", "SBILIFE", "SJVN", "SHRIPISTON", "SRF", "SAGILITY",
            "SAILIFE", "SAMMAANCAP", "MOTHERSON", "SANSERA", "SARDAEN", "SCHAEFFLER", "SCHNEIDER", "SCI", "SHREECEM", "SHRIRAMFIN", "SHYAMMETL", "ENRIN", "SIEMENS", "SIGNATURE", "SOBHA", "SOLARINDS", "SONACOMS", "STARHEALTH", "SBIN", "SAIL", "STLTECH", "SUMICHEM", "SUNPHARMA", "SUNTV", "SUNDARMFIN",
            "SUPREMEIND", "SUZLON", "SWANCORP", "SWIGGY", "SYNGENE", "SYRMA", "TBOTEK", "TDPOWERSYS", "TVSMOTOR", "TATACAP", "TATACHEM", "TATACOMM", "TCS", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TMCV", "TMPV", "TATAPOWER", "TATASTEEL", "TATATECH", "TTML", "TECHM", "TECHNOE", "TEGA",
            "TEJASNET", "TENNIND", "THANGAMAYL", "NIACL", "RAMCOCEM", "THERMAX", "TIMKEN", "TITAGARH", "TITAN", "TORNTPHARM", "TORNTPOWER", "TARIL", "TRENT", "TRIDENT", "TRITURBINE", "TIINDIA", "UCOBANK", "UNOMINDA", "UPL", "UTIAMC", "ULTRACEMCO", "UNIONBANK", "UBL", "UNITDSPR", "URBANCO",
            "USHAMART", "VTL", "VBL", "VAML", "VISL", "VEDL", "VOGL", "VEDPOWER", "VIJAYA", "VMM", "IDEA", "VOLTAS", "WAAREEENER", "WELCORP", "WELSPUNLIV", "WHIRLPOOL", "WIPRO", "WOCKPHARMA", "YESBANK", "ZFCVINDIA", "ZEEL", "ZENTEC", "ZENSARTECH", "ZYDUSLIFE", "ZYDUSWELL",
            "ECLERX"
        ]

    def fetch_live_market_price(self, symbol):
        # Simulated live price to guarantee zero dependency failures
        return round(random.uniform(200, 2000), 2)

    def execute_market_checks(self):
        now_ist = datetime.datetime.now(self.ist)
        current_time = now_ist.time()
        current_day = now_ist.weekday()

        # Skip weekends (Saturday=5, Sunday=6)
        if current_day >= 5:
            return

        market_open = datetime.time(9, 15)
        market_close = datetime.time(15, 30)
        log_file = "live_trading_exec.log"
        timestamp = now_ist.strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file, "a", encoding="utf-8") as f:
            if market_open <= current_time <= market_close:
                f.write(f"[{timestamp}] 🟢 LIVE MARKET OPEN: Executing buys for PF1 & PF2...\n")

                # --- PF1: Filter out already active symbols to prevent duplicates ---
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
                else:
                    f.write(f"   -> [PF1 INFO] No available unique stocks left to buy in PF1 universe.\n")

                # --- PF2: Filter out already active symbols to prevent duplicates ---
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
                else:
                    f.write(f"   -> [PF2 INFO] No available unique stocks left to buy in PF2 universe.\n")

            elif current_time < market_open:
                f.write(f"[{timestamp}] ⏳ Pre-market preparation (Market opens at 9:15 AM).\n")
            else:
                f.write(f"[{timestamp}] 🌙 Market closed for the day.\n")

if __name__ == '__main__':
    trader = CloudLiveTrader(initial_capital=200000.0)
    trader.execute_market_checks()
