//+------------------------------------------------------------------+
//|                                      export_ohlc_multi.mq5        |
//|                         Multi-symbol OHLC CSV Exporter for MT5   |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Exports OHLC data for multiple symbols/timeframes to CSV. No trading logic."

/*
  Purpose
  -------
  Export OHLC data from MT5 to CSV for one or more symbols and timeframes.

  Initial project use:
    - XAUUSD M15/H1
    - BTCUSD M15/H1, if the broker provides BTC/USD in MT5

  Output folder:
    MT5 terminal data folder / MQL5 / Files /

  Output format:
    time,open,high,low,close,volume,spread

  Important notes:
    - Attach this EA to one chart only.
    - Add target symbols to Market Watch before running.
    - Broker symbol names vary. Examples: XAUUSD, XAUUSDm, GOLD, BTCUSD, BTCUSDm, BTCUSD.
    - The EA does not trade. It only exports CSV files.
*/

input string InpSymbolsCSV       = "XAUUSD,BTCUSD"; // comma-separated symbols
input string InpTimeframesCSV    = "M15,H1";        // comma-separated TFs: M1,M5,M15,M30,H1,H4,D1,W1,MN1
input int    InpBarsToExport     = 20000;           // number of bars to export per symbol/timeframe
input int    InpTimerSeconds     = 60;              // export interval in seconds
input bool   InpExportOnInit     = true;            // export immediately when attached
input bool   InpUseSubfolder     = false;           // if true, output to MQL5/Files/export/
input string InpSubfolderName    = "export";

//+------------------------------------------------------------------+
//| Utility: trim string                                             |
//+------------------------------------------------------------------+
string TrimString(string value)
{
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
}

//+------------------------------------------------------------------+
//| Utility: lower string                                            |
//+------------------------------------------------------------------+
string ToLowerString(string value)
{
   string s = value;
   StringToLower(s);
   return s;
}

//+------------------------------------------------------------------+
//| Utility: upper string                                            |
//+------------------------------------------------------------------+
string ToUpperString(string value)
{
   string s = value;
   StringToUpper(s);
   return s;
}

//+------------------------------------------------------------------+
//| Utility: sanitize filename                                       |
//+------------------------------------------------------------------+
string SanitizeFilePart(string value)
{
   string s = value;
   StringReplace(s, "/", "");
   StringReplace(s, "\\", "");
   StringReplace(s, ":", "");
   StringReplace(s, "*", "");
   StringReplace(s, "?", "");
   StringReplace(s, "\"", "");
   StringReplace(s, "<", "");
   StringReplace(s, ">", "");
   StringReplace(s, "|", "");
   StringReplace(s, " ", "");
   return s;
}

//+------------------------------------------------------------------+
//| Digits for symbol                                                |
//+------------------------------------------------------------------+
int DigitsForSymbol(const string symbol)
{
   long digits = 0;
   if(SymbolInfoInteger(symbol, SYMBOL_DIGITS, digits))
      return (int)digits;

   return _Digits;
}

//+------------------------------------------------------------------+
//| Convert timeframe text to MT5 ENUM_TIMEFRAMES                    |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES TimeframeFromString(string tf)
{
   string t = ToUpperString(TrimString(tf));

   if(t == "M1")  return PERIOD_M1;
   if(t == "M2")  return PERIOD_M2;
   if(t == "M3")  return PERIOD_M3;
   if(t == "M4")  return PERIOD_M4;
   if(t == "M5")  return PERIOD_M5;
   if(t == "M6")  return PERIOD_M6;
   if(t == "M10") return PERIOD_M10;
   if(t == "M12") return PERIOD_M12;
   if(t == "M15") return PERIOD_M15;
   if(t == "M20") return PERIOD_M20;
   if(t == "M30") return PERIOD_M30;
   if(t == "H1")  return PERIOD_H1;
   if(t == "H2")  return PERIOD_H2;
   if(t == "H3")  return PERIOD_H3;
   if(t == "H4")  return PERIOD_H4;
   if(t == "H6")  return PERIOD_H6;
   if(t == "H8")  return PERIOD_H8;
   if(t == "H12") return PERIOD_H12;
   if(t == "D1")  return PERIOD_D1;
   if(t == "W1")  return PERIOD_W1;
   if(t == "MN1") return PERIOD_MN1;

   return PERIOD_CURRENT;
}

//+------------------------------------------------------------------+
//| Validate timeframe text                                          |
//+------------------------------------------------------------------+
bool IsSupportedTimeframe(string tf)
{
   string t = ToUpperString(TrimString(tf));

   if(t == "M1"  || t == "M2"  || t == "M3"  || t == "M4"  ||
      t == "M5"  || t == "M6"  || t == "M10" || t == "M12" ||
      t == "M15" || t == "M20" || t == "M30" ||
      t == "H1"  || t == "H2"  || t == "H3"  || t == "H4"  ||
      t == "H6"  || t == "H8"  || t == "H12" ||
      t == "D1"  || t == "W1"  || t == "MN1")
      return true;

   return false;
}

//+------------------------------------------------------------------+
//| Convert timeframe to label                                       |
//+------------------------------------------------------------------+
string TimeframeToLabel(ENUM_TIMEFRAMES timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M1:  return "m1";
      case PERIOD_M2:  return "m2";
      case PERIOD_M3:  return "m3";
      case PERIOD_M4:  return "m4";
      case PERIOD_M5:  return "m5";
      case PERIOD_M6:  return "m6";
      case PERIOD_M10: return "m10";
      case PERIOD_M12: return "m12";
      case PERIOD_M15: return "m15";
      case PERIOD_M20: return "m20";
      case PERIOD_M30: return "m30";
      case PERIOD_H1:  return "h1";
      case PERIOD_H2:  return "h2";
      case PERIOD_H3:  return "h3";
      case PERIOD_H4:  return "h4";
      case PERIOD_H6:  return "h6";
      case PERIOD_H8:  return "h8";
      case PERIOD_H12: return "h12";
      case PERIOD_D1:  return "d1";
      case PERIOD_W1:  return "w1";
      case PERIOD_MN1: return "mn1";
      default:         return "unknown";
   }
}

//+------------------------------------------------------------------+
//| Build output filename                                            |
//+------------------------------------------------------------------+
string BuildFileName(const string symbol, const ENUM_TIMEFRAMES timeframe)
{
   string safeSymbol = ToLowerString(SanitizeFilePart(symbol));
   string tfLabel    = TimeframeToLabel(timeframe);
   string filename   = safeSymbol + "_" + tfLabel + ".csv";

   if(InpUseSubfolder)
      filename = InpSubfolderName + "\\" + filename;

   return filename;
}

//+------------------------------------------------------------------+
//| Ensure symbol is available                                       |
//+------------------------------------------------------------------+
bool EnsureSymbol(const string symbol)
{
   string s = TrimString(symbol);
   if(s == "")
      return false;

   if(SymbolSelect(s, true))
      return true;

   Print("[export_ohlc_multi] SymbolSelect failed: ", s,
         " | Add this symbol to Market Watch or check broker symbol name.");
   return false;
}

//+------------------------------------------------------------------+
//| Export one symbol/timeframe                                      |
//+------------------------------------------------------------------+
bool ExportOne(const string symbol, const ENUM_TIMEFRAMES timeframe)
{
   if(!EnsureSymbol(symbol))
      return false;

   int barsAvailable = Bars(symbol, timeframe);
   if(barsAvailable <= 0)
   {
      Print("[export_ohlc_multi] No bars available: ", symbol, " ", TimeframeToLabel(timeframe));
      return false;
   }

   int barsToCopy = MathMin(InpBarsToExport, barsAvailable);

   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   ResetLastError();
   int copied = CopyRates(symbol, timeframe, 0, barsToCopy, rates);
   if(copied <= 0)
   {
      int err = GetLastError();
      Print("[export_ohlc_multi] CopyRates failed: ", symbol, " ", TimeframeToLabel(timeframe),
            " | error=", err);
      return false;
   }

   string filename = BuildFileName(symbol, timeframe);

   ResetLastError();
   int handle = FileOpen(filename, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      int fileErr = GetLastError();
      Print("[export_ohlc_multi] FileOpen failed: ", filename,
            " | error=", fileErr,
            " | Check MQL5/Files permissions or subfolder existence.");
      return false;
   }

   FileWrite(handle, "time", "open", "high", "low", "close", "volume", "spread");

   int digits = DigitsForSymbol(symbol);

   // CopyRates with ArraySetAsSeries(true): index 0 is newest.
   // Write oldest -> newest for Python/time-series processing.
   for(int i = copied - 1; i >= 0; i--)
   {
      string timeText = TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES);

      FileWrite(handle,
                timeText,
                DoubleToString(rates[i].open,  digits),
                DoubleToString(rates[i].high,  digits),
                DoubleToString(rates[i].low,   digits),
                DoubleToString(rates[i].close, digits),
                (long)rates[i].tick_volume,
                (int)rates[i].spread);
   }

   FileClose(handle);

   Print("[export_ohlc_multi] Exported: ", filename,
         " | symbol=", symbol,
         " | timeframe=", TimeframeToLabel(timeframe),
         " | bars=", copied);

   return true;
}

//+------------------------------------------------------------------+
//| Export all configured symbols/timeframes                         |
//+------------------------------------------------------------------+
void ExportAll()
{
   string symbols[];
   string timeframes[];

   int symbolCount = StringSplit(InpSymbolsCSV, ',', symbols);
   int tfCount     = StringSplit(InpTimeframesCSV, ',', timeframes);

   if(symbolCount <= 0)
   {
      Print("[export_ohlc_multi] No symbols configured.");
      return;
   }

   if(tfCount <= 0)
   {
      Print("[export_ohlc_multi] No timeframes configured.");
      return;
   }

   for(int s = 0; s < symbolCount; s++)
   {
      string symbol = TrimString(symbols[s]);
      if(symbol == "")
         continue;

      for(int t = 0; t < tfCount; t++)
      {
         string tfText = TrimString(timeframes[t]);
         if(!IsSupportedTimeframe(tfText))
         {
            Print("[export_ohlc_multi] Unsupported timeframe: ", tfText);
            continue;
         }

         ENUM_TIMEFRAMES timeframe = TimeframeFromString(tfText);
         ExportOne(symbol, timeframe);
      }
   }
}

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("[export_ohlc_multi] MT5 EA initialized.");
   Print("[export_ohlc_multi] Symbols=", InpSymbolsCSV, " | Timeframes=", InpTimeframesCSV);

   int timerSeconds = MathMax(1, InpTimerSeconds);
   EventSetTimer(timerSeconds);

   if(InpExportOnInit)
      ExportAll();

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("[export_ohlc_multi] MT5 EA stopped. reason=", reason);
}

//+------------------------------------------------------------------+
//| Timer                                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   ExportAll();
}

//+------------------------------------------------------------------+
//| Tick                                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Export is timer-based to avoid excessive writes on every tick.
}
