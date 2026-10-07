import datetime
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

    def send_email_alert(self, subject, body):
        sender_email = os.getenv("MAIL_USER")
        sender_pass = os.getenv("MAIL_PASS")
        if not sender_email or not sender_pass:
            return  # Skip if credentials aren't set

        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = sender_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, sender_email, msg.as_string())
            server.quit()
        except Exception as e:
            print(f"Email notification failed: {e}")

    def execute_market_checks(self):
        now_ist = datetime.datetime.now(self.ist)
        current_time = now_ist.time()
        current_day = now_ist.weekday()

        if current_day >= 5:
            return

        market_open = datetime.time(9, 15)
        market_close = datetime.time(15, 30)
        log_file = "live_trading_exec.log"
        timestamp = now_ist.strftime('%Y-%m-%d %H:%M:%S')

        action_logs = []

        with open(log_file, "a", encoding="utf-8") as f:
            if market_open <= current_time <= market_close:
                header_msg = f"[{timestamp}] 🟢 LIVE MARKET OPEN: Executing buys for PF1 & PF2..."
                f.write(header_msg + "\n")
                action_logs.append(header_msg)

                # PF1 Check
                active_pf1_symbols = {item['Symbol'] for item in self.active_pf1}
                available_pf1 = [s for s in self.pf1_universe if (s + '.NS') not in active_pf1_symbols]

                if available_pf1:
                    s1 = random.choice(available_pf1) + '.NS'
                    p1 = self.fetch_live_market_price(s1)
                    margin_req = p1 * 25
eoh
EOH
