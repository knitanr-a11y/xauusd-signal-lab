//+------------------------------------------------------------------+
//|                                                ExportOhlcToCsv.mq5 |
//|                         MT5 OHLC CSV Export EA for Python detector |
//+------------------------------------------------------------------+
#property strict
#property version   "1.31"
#property description "Export confirmed OHLC candles for GOLD#/BTCUSD# to CSV for Python detector."

input string InpGoldSymbol = "GOLD#";
input string InpBtcSymbol  = "BTCUSD#";
input bool   InpExportGold = true;
input bool   InpExportBtc  = true;

input bool   InpExportM5  = true;
input bool   InpExportM15 = true;
input bool   InpExportH1  = true;
input bool   InpExportH4  = true;
input bool   InpGoldM5Enabled = true;
input bool   InpGoldH4Enabled = true;
input bool   InpBtcM5Enabled  = true;
input bool   InpBtcH4Enabled  = true;

input bool   InpAlignExportToMinute = true;
input int    InpExportSecond = 0;
input int    InpTimerSeconds = 1;
input bool   InpAppendMode = true;
input int    InpAppendLookbackBars = 20;
input int    InpBarsToExportM5  = 30000;
input int    InpBarsToExportM15 = 30000;
input int    InpBarsToExportH1  = 20000;
input int    InpBarsToExportH4  = 10000;

input bool   InpUseCommonFolder = false;
input string InpOutputRoot = "";
input bool   InpIncludeCurrentBar = false;
input bool   InpForceSymbolSelect = true;
input bool   InpWriteDebugLog = true;
input bool   InpSkipUnchangedFiles = true;

input string InpGoldM5File  = "goldsharp_m5.csv";
input string InpGoldM15File = "goldsharp_m15.csv";
input string InpGoldH1File  = "goldsharp_h1.csv";
input string InpGoldH4File  = "goldsharp_h4.csv";
input string InpBtcM5File   = "btcusdsharp_m5.csv";
input string InpBtcM15File  = "btcusdsharp_m15.csv";
input string InpBtcH1File   = "btcusdsharp_h1.csv";
input string InpBtcH4File   = "btcusdsharp_h4.csv";

struct ExportJob
{
   string symbol;
   ENUM_TIMEFRAMES timeframe;
   string filename;
   int bars_to_export;
   bool enabled;
};

string g_last_bar_key[];
datetime g_last_bar_time[];
int g_last_aligned_minute_key = -1;
bool g_initialized_full_export = false;

void DebugLog(const string message)
{
   if(InpWriteDebugLog)
      Print("[ExportOhlcToCsv] ", message);
}

int TextFileFlags(const bool write_mode)
{
   int flags = (write_mode ? FILE_WRITE : FILE_READ) | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFolder)
      flags |= FILE_COMMON;
   return flags;
}

int AppendFileFlags()
{
   int flags = FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFolder)
      flags |= FILE_COMMON;
   return flags;
}

string TrimSlashes(const string value)
{
   string out = value;
   StringReplace(out, "/", "\\");
   while(StringLen(out) > 0 && StringSubstr(out, 0, 1) == "\\")
      out = StringSubstr(out, 1);
   while(StringLen(out) > 0 && StringSubstr(out, StringLen(out) - 1, 1) == "\\")
      out = StringSubstr(out, 0, StringLen(out) - 1);
   return out;
}

string JoinPath(const string left, const string right)
{
   if(left == "")
      return right;
   string normalized = left;
   StringReplace(normalized, "/", "\\");
   string last = StringSubstr(normalized, StringLen(normalized) - 1, 1);
   if(last == "\\")
      return normalized + right;
   return normalized + "\\" + right;
}

string BuildPath(const string filename)
{
   string root = TrimSlashes(InpOutputRoot);
   if(root == "")
      return filename;
   return JoinPath(root, filename);
}

string TimeframeName(const ENUM_TIMEFRAMES timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      default:         return EnumToString(timeframe);
   }
}

int BarsToExportForTimeframe(const ENUM_TIMEFRAMES timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M5:  return MathMax(100, InpBarsToExportM5);
      case PERIOD_M15: return MathMax(100, InpBarsToExportM15);
      case PERIOD_H1:  return MathMax(100, InpBarsToExportH1);
      case PERIOD_H4:  return MathMax(100, InpBarsToExportH4);
      default:         return MathMax(100, InpBarsToExportM15);
   }
}

int DigitsForSymbol(const string symbol)
{
   long digits = 0;
   if(SymbolInfoInteger(symbol, SYMBOL_DIGITS, digits))
      return (int)digits;
   return _Digits;
}

bool EnsureFolderTree()
{
   string root = TrimSlashes(InpOutputRoot);
   if(root == "")
      return true;
   string parts[];
   int count = StringSplit(root, '\\', parts);
   if(count <= 0)
      return true;
   string current = "";
   for(int i = 0; i < count; i++)
   {
      if(parts[i] == "")
         continue;
      current = (current == "") ? parts[i] : current + "\\" + parts[i];
      ResetLastError();
      bool ok = FolderCreate(current, InpUseCommonFolder ? FILE_COMMON : 0);
      int err = GetLastError();
      if(!ok && err != 0)
         DebugLog("FolderCreate warning: " + current + ", err=" + IntegerToString(err));
   }
   return true;
}

bool PrepareSymbol(const string symbol)
{
   if(symbol == "")
      return false;
   if(InpForceSymbolSelect)
   {
      ResetLastError();
      if(!SymbolSelect(symbol, true))
      {
         Print("[ExportOhlcToCsv] SymbolSelect failed: ", symbol, ", err=", GetLastError());
         return false;
      }
   }
   if(!SymbolInfoInteger(symbol, SYMBOL_SELECT))
   {
      Print("[ExportOhlcToCsv] Symbol is not selected: ", symbol);
      return false;
   }
   return true;
}

string JobKey(const string symbol, const ENUM_TIMEFRAMES timeframe, const string filename)
{
   return symbol + "|" + TimeframeName(timeframe) + "|" + filename;
}

int FindKeyIndex(const string key)
{
   int n = ArraySize(g_last_bar_key);
   for(int i = 0; i < n; i++)
      if(g_last_bar_key[i] == key)
         return i;
   return -1;
}

bool LastBarAlreadyExported(const string key, const datetime last_bar_time)
{
   int idx = FindKeyIndex(key);
   if(idx < 0)
      return false;
   return g_last_bar_time[idx] == last_bar_time;
}

void RememberLastBar(const string key, const datetime last_bar_time)
{
   int idx = FindKeyIndex(key);
   if(idx < 0)
   {
      int n = ArraySize(g_last_bar_key);
      ArrayResize(g_last_bar_key, n + 1);
      ArrayResize(g_last_bar_time, n + 1);
      g_last_bar_key[n] = key;
      g_last_bar_time[n] = last_bar_time;
      return;
   }
   g_last_bar_time[idx] = last_bar_time;
}

bool ShouldRunAlignedExport()
{
   if(!InpAlignExportToMinute)
      return true;
   MqlDateTime now;
   TimeToStruct(TimeLocal(), now);
   int target_second = MathMax(0, MathMin(59, InpExportSecond));
   if(now.sec != target_second)
      return false;
   int minute_key = (int)(TimeLocal() / 60);
   if(minute_key == g_last_aligned_minute_key)
      return false;
   g_last_aligned_minute_key = minute_key;
   return true;
}

bool CopyConfirmedRates(const string symbol, const ENUM_TIMEFRAMES timeframe, const int bars_to_export, MqlRates &rates[])
{
   int start_pos = InpIncludeCurrentBar ? 0 : 1;
   int count = MathMax(1, bars_to_export);
   ArraySetAsSeries(rates, false);
   ResetLastError();
   int copied = CopyRates(symbol, timeframe, start_pos, count, rates);
   if(copied <= 0)
   {
      Print("[ExportOhlcToCsv] CopyRates failed: symbol=", symbol,
            ", timeframe=", TimeframeName(timeframe),
            ", copied=", copied,
            ", err=", GetLastError());
      return false;
   }
   return true;
}

bool RatesAreDescending(MqlRates &rates[])
{
   int n = ArraySize(rates);
   if(n < 2)
      return false;
   return rates[0].time > rates[n - 1].time;
}

datetime LastChronologicalTime(MqlRates &rates[])
{
   int n = ArraySize(rates);
   if(n <= 0)
      return 0;
   if(RatesAreDescending(rates))
      return rates[0].time;
   return rates[n - 1].time;
}

datetime FirstChronologicalTime(MqlRates &rates[])
{
   int n = ArraySize(rates);
   if(n <= 0)
      return 0;
   if(RatesAreDescending(rates))
      return rates[n - 1].time;
   return rates[0].time;
}

void WriteRateRow(const int handle, const string symbol, const MqlRates &rate)
{
   int digits = DigitsForSymbol(symbol);
   FileWrite(handle,
             TimeToString(rate.time, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             DoubleToString(rate.open, digits),
             DoubleToString(rate.high, digits),
             DoubleToString(rate.low, digits),
             DoubleToString(rate.close, digits),
             (long)rate.tick_volume,
             (int)rate.spread,
             (long)rate.real_volume);
}

void WriteCsvHeader(const int handle)
{
   FileWrite(handle, "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume");
}

bool WriteCsvFull(const string symbol, const string filename, MqlRates &rates[])
{
   string path = BuildPath(filename);
   ResetLastError();
   int handle = FileOpen(path, TextFileFlags(true), ',');
   if(handle == INVALID_HANDLE)
   {
      Print("[ExportOhlcToCsv] FileOpen failed: ", path, ", err=", GetLastError());
      return false;
   }
   WriteCsvHeader(handle);
   int copied = ArraySize(rates);
   bool descending = RatesAreDescending(rates);
   if(!descending)
   {
      for(int i = 0; i < copied; i++)
         WriteRateRow(handle, symbol, rates[i]);
   }
   else
   {
      for(int i = copied - 1; i >= 0; i--)
         WriteRateRow(handle, symbol, rates[i]);
   }
   FileFlush(handle);
   FileClose(handle);
   return true;
}

bool AppendCsvRows(const string symbol, const string filename, MqlRates &rates[], const datetime last_exported_time, int &appended_count, datetime &new_last_time)
{
   appended_count = 0;
   new_last_time = last_exported_time;
   string path = BuildPath(filename);
   ResetLastError();
   int handle = FileOpen(path, AppendFileFlags(), ',');
   if(handle == INVALID_HANDLE)
   {
      Print("[ExportOhlcToCsv] Append FileOpen failed: ", path, ", err=", GetLastError());
      return false;
   }
   FileSeek(handle, 0, SEEK_END);
   int copied = ArraySize(rates);
   bool descending = RatesAreDescending(rates);
   if(!descending)
   {
      for(int i = 0; i < copied; i++)
      {
         if(rates[i].time <= last_exported_time)
            continue;
         WriteRateRow(handle, symbol, rates[i]);
         appended_count++;
         if(rates[i].time > new_last_time)
            new_last_time = rates[i].time;
      }
   }
   else
   {
      for(int i = copied - 1; i >= 0; i--)
      {
         if(rates[i].time <= last_exported_time)
            continue;
         WriteRateRow(handle, symbol, rates[i]);
         appended_count++;
         if(rates[i].time > new_last_time)
            new_last_time = rates[i].time;
      }
   }
   FileFlush(handle);
   FileClose(handle);
   return true;
}

bool RewriteFullOne(const string symbol, const ENUM_TIMEFRAMES timeframe, const string filename, const int bars_to_export, const string reason)
{
   MqlRates rates[];
   if(!CopyConfirmedRates(symbol, timeframe, bars_to_export, rates))
      return false;
   int copied = ArraySize(rates);
   if(copied <= 0)
      return false;
   datetime first_time = FirstChronologicalTime(rates);
   datetime last_time = LastChronologicalTime(rates);
   string key = JobKey(symbol, timeframe, filename);
   if(InpSkipUnchangedFiles && LastBarAlreadyExported(key, last_time))
   {
      DebugLog("Skipped unchanged: " + symbol + " " + TimeframeName(timeframe) + " -> " + BuildPath(filename));
      return true;
   }
   if(!WriteCsvFull(symbol, filename, rates))
      return false;
   RememberLastBar(key, last_time);
   DebugLog("Rebuilt " + IntegerToString(copied) + " bars: " + symbol + " " + TimeframeName(timeframe)
            + " -> " + BuildPath(filename)
            + " / reason=" + reason
            + " / first=" + TimeToString(first_time, TIME_DATE | TIME_MINUTES)
            + " / last=" + TimeToString(last_time, TIME_DATE | TIME_MINUTES));
   return true;
}

bool AppendNewBarsOne(const string symbol, const ENUM_TIMEFRAMES timeframe, const string filename, const int bars_to_export)
{
   string key = JobKey(symbol, timeframe, filename);
   int idx = FindKeyIndex(key);
   if(idx < 0)
      return RewriteFullOne(symbol, timeframe, filename, bars_to_export, "no remembered last bar");

   datetime last_exported_time = g_last_bar_time[idx];
   int lookback = MathMax(2, InpAppendLookbackBars);
   MqlRates rates[];
   if(!CopyConfirmedRates(symbol, timeframe, lookback, rates))
      return false;
   if(ArraySize(rates) <= 0)
      return false;

   datetime latest_time = LastChronologicalTime(rates);
   if(InpSkipUnchangedFiles && latest_time <= last_exported_time)
   {
      DebugLog("Skipped unchanged append: " + symbol + " " + TimeframeName(timeframe)
               + " -> " + BuildPath(filename)
               + " / last=" + TimeToString(last_exported_time, TIME_DATE | TIME_MINUTES));
      return true;
   }

   int appended_count = 0;
   datetime new_last_time = last_exported_time;
   if(!AppendCsvRows(symbol, filename, rates, last_exported_time, appended_count, new_last_time))
      return RewriteFullOne(symbol, timeframe, filename, bars_to_export, "append failed fallback");

   if(appended_count <= 0)
   {
      DebugLog("No append rows: " + symbol + " " + TimeframeName(timeframe)
               + " / remembered=" + TimeToString(last_exported_time, TIME_DATE | TIME_MINUTES)
               + " / latest=" + TimeToString(latest_time, TIME_DATE | TIME_MINUTES));
      return true;
   }

   RememberLastBar(key, new_last_time);
   DebugLog("Appended " + IntegerToString(appended_count) + " bars: " + symbol + " " + TimeframeName(timeframe)
            + " -> " + BuildPath(filename)
            + " / from_after=" + TimeToString(last_exported_time, TIME_DATE | TIME_MINUTES)
            + " / last=" + TimeToString(new_last_time, TIME_DATE | TIME_MINUTES));
   return true;
}

bool ExportOne(const string symbol, const ENUM_TIMEFRAMES timeframe, const string filename, const int bars_to_export)
{
   if(!PrepareSymbol(symbol))
      return false;
   if(InpAppendMode && g_initialized_full_export)
      return AppendNewBarsOne(symbol, timeframe, filename, bars_to_export);
   return RewriteFullOne(symbol, timeframe, filename, bars_to_export, g_initialized_full_export ? "append mode disabled" : "initial full export");
}

void AddJob(ExportJob &jobs[], const string symbol, const ENUM_TIMEFRAMES timeframe, const string filename, const bool enabled)
{
   int n = ArraySize(jobs);
   ArrayResize(jobs, n + 1);
   jobs[n].symbol = symbol;
   jobs[n].timeframe = timeframe;
   jobs[n].filename = filename;
   jobs[n].bars_to_export = BarsToExportForTimeframe(timeframe);
   jobs[n].enabled = enabled;
}

void BuildJobs(ExportJob &jobs[])
{
   ArrayResize(jobs, 0);
   if(InpExportGold)
   {
      AddJob(jobs, InpGoldSymbol, PERIOD_M5,  InpGoldM5File,  InpExportM5  && InpGoldM5Enabled);
      AddJob(jobs, InpGoldSymbol, PERIOD_M15, InpGoldM15File, InpExportM15);
      AddJob(jobs, InpGoldSymbol, PERIOD_H1,  InpGoldH1File,  InpExportH1);
      AddJob(jobs, InpGoldSymbol, PERIOD_H4,  InpGoldH4File,  InpExportH4  && InpGoldH4Enabled);
   }
   if(InpExportBtc)
   {
      AddJob(jobs, InpBtcSymbol, PERIOD_M5,  InpBtcM5File,  InpExportM5  && InpBtcM5Enabled);
      AddJob(jobs, InpBtcSymbol, PERIOD_M15, InpBtcM15File, InpExportM15);
      AddJob(jobs, InpBtcSymbol, PERIOD_H1,  InpBtcH1File,  InpExportH1);
      AddJob(jobs, InpBtcSymbol, PERIOD_H4,  InpBtcH4File,  InpExportH4  && InpBtcH4Enabled);
   }
}

bool ExportAll()
{
   EnsureFolderTree();
   ExportJob jobs[];
   BuildJobs(jobs);
   int enabled_count = 0;
   bool ok_all = true;
   for(int i = 0; i < ArraySize(jobs); i++)
   {
      if(!jobs[i].enabled)
         continue;
      enabled_count++;
      bool ok = ExportOne(jobs[i].symbol, jobs[i].timeframe, jobs[i].filename, jobs[i].bars_to_export);
      ok_all = ok && ok_all;
   }
   if(enabled_count <= 0)
      Print("[ExportOhlcToCsv] No export jobs enabled.");
   if(!ok_all)
      Print("[ExportOhlcToCsv] Export finished with one or more errors.");
   return ok_all;
}

int OnInit()
{
   if(InpTimerSeconds < 1)
      return INIT_PARAMETERS_INCORRECT;
   if(InpExportSecond < 0 || InpExportSecond > 59)
      return INIT_PARAMETERS_INCORRECT;
   if(InpAppendLookbackBars < 2)
      return INIT_PARAMETERS_INCORRECT;

   DebugLog("Initializing EA v1.31");
   DebugLog("GoldSymbol=" + InpGoldSymbol + ", BtcSymbol=" + InpBtcSymbol);
   DebugLog("OutputRoot=" + InpOutputRoot + ", UseCommonFolder=" + (InpUseCommonFolder ? "true" : "false"));
   DebugLog("IncludeCurrentBar=" + (InpIncludeCurrentBar ? "true" : "false"));
   DebugLog("SkipUnchangedFiles=" + (InpSkipUnchangedFiles ? "true" : "false"));
   DebugLog("GoldM5Enabled=" + (InpGoldM5Enabled ? "true" : "false") + ", GoldH4Enabled=" + (InpGoldH4Enabled ? "true" : "false"));
   DebugLog("AppendMode=" + (InpAppendMode ? "true" : "false") + ", AppendLookbackBars=" + IntegerToString(InpAppendLookbackBars));
   DebugLog("AlignExportToMinute=" + (InpAlignExportToMinute ? "true" : "false")
            + ", ExportSecond=" + IntegerToString(InpExportSecond)
            + ", TimerSeconds=" + IntegerToString(InpTimerSeconds));

   EnsureFolderTree();
   g_initialized_full_export = false;
   bool ok = ExportAll();
   g_initialized_full_export = ok;
   EventSetTimer(InpTimerSeconds);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   DebugLog("Deinitialized. reason=" + IntegerToString(reason));
}

void OnTimer()
{
   if(ShouldRunAlignedExport())
      ExportAll();
}

void OnTick()
{
}
