#property strict
#property script_show_inputs
#property version   "1.00"
#property description "Read-only GOLD V3 history exporter for MT5."
#property description "Exports M1/M5/M15/H1/H4/D1 bars without filling gaps."
#property description "All input/output datetimes are broker server time."

input string   InpSymbol              = "";                         // Empty = current chart symbol
input datetime InpFromServer          = D'2023.01.01 00:00:00';     // Inclusive, broker server time
input datetime InpToServerExclusive   = D'2025.01.01 00:00:00';     // Exclusive, broker server time
input string   InpFilePrefix          = "gold_v3_2023_2024";
input bool     InpUseCommonFolder     = false;
input int      InpRatesChunkDays      = 31;
input int      InpCopyRetryCount      = 8;
input int      InpRetrySleepMs        = 750;

input bool     InpExportM1            = true;
input bool     InpExportM5            = true;
input bool     InpExportM15           = true;
input bool     InpExportH1            = true;
input bool     InpExportH4            = true;
input bool     InpExportD1            = true;
input bool     InpExportWeeklySessions= true;

struct ExportResult
  {
   bool     ok;
   string   timeframe;
   string   filename;
   long     rows;
   datetime first_time;
   datetime last_time;
   int      copy_errors;
  };

string TfLabel(const ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return "m1";
      case PERIOD_M5:  return "m5";
      case PERIOD_M15: return "m15";
      case PERIOD_H1:  return "h1";
      case PERIOD_H4:  return "h4";
      case PERIOD_D1:  return "d1";
      default:         return "unknown";
     }
  }

string SanitizePrefix(string value)
  {
   StringReplace(value,"\\","_");
   StringReplace(value,"/","_");
   StringReplace(value,":","_");
   StringReplace(value,"*","_");
   StringReplace(value,"?","_");
   StringReplace(value,"\"","_");
   StringReplace(value,"<","_");
   StringReplace(value,">","_");
   StringReplace(value,"|","_");
   StringTrimLeft(value);
   StringTrimRight(value);
   if(value=="") value="gold_v3_history";
   return value;
  }

int FileFlags()
  {
   int flags=FILE_WRITE|FILE_CSV|FILE_ANSI;
   if(InpUseCommonFolder) flags|=FILE_COMMON;
   return flags;
  }

string OutputRoot()
  {
   if(InpUseCommonFolder)
      return TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";
   return TerminalInfoString(TERMINAL_DATA_PATH)+"\\MQL5\\Files\\";
  }

bool EnsureHistoryReady(const string symbol,const ENUM_TIMEFRAMES tf)
  {
   MqlRates probe[];
   ArraySetAsSeries(probe,false);

   for(int attempt=0;attempt<InpCopyRetryCount;attempt++)
     {
      ResetLastError();
      datetime probe_to=InpFromServer+86400*7;
      if(probe_to>=InpToServerExclusive) probe_to=InpToServerExclusive-1;
      int copied=CopyRates(symbol,tf,InpFromServer,probe_to,probe);
      if(copied>0)
         return true;

      long synchronized=0;
      SeriesInfoInteger(symbol,tf,SERIES_SYNCHRONIZED,synchronized);
      PrintFormat("History warm-up: symbol=%s tf=%s attempt=%d copied=%d synchronized=%d error=%d",
                  symbol,TfLabel(tf),attempt+1,copied,synchronized,GetLastError());
      int sleep_ms=InpRetrySleepMs;
      if(sleep_ms<100) sleep_ms=100;
      Sleep(sleep_ms);
     }
   return false;
  }

int CopyRatesRetry(const string symbol,
                   const ENUM_TIMEFRAMES tf,
                   const datetime from_time,
                   const datetime to_time_inclusive,
                   MqlRates &rates[])
  {
   for(int attempt=0;attempt<InpCopyRetryCount;attempt++)
     {
      ResetLastError();
      int copied=CopyRates(symbol,tf,from_time,to_time_inclusive,rates);
      if(copied>0)
         return copied;

      int err=GetLastError();
      PrintFormat("CopyRates retry: symbol=%s tf=%s from=%s to=%s attempt=%d error=%d",
                  symbol,TfLabel(tf),
                  TimeToString(from_time,TIME_DATE|TIME_SECONDS),
                  TimeToString(to_time_inclusive,TIME_DATE|TIME_SECONDS),
                  attempt+1,err);
      int sleep_ms=InpRetrySleepMs;
      if(sleep_ms<100) sleep_ms=100;
      Sleep(sleep_ms);
     }
   return -1;
  }

ExportResult ExportRatesFile(const string symbol,
                             const ENUM_TIMEFRAMES tf,
                             const string prefix,
                             const int digits)
  {
   ExportResult result;
   result.ok=false;
   result.timeframe=TfLabel(tf);
   result.filename=prefix+"_"+result.timeframe+".csv";
   result.rows=0;
   result.first_time=0;
   result.last_time=0;
   result.copy_errors=0;

   if(!EnsureHistoryReady(symbol,tf))
     {
      PrintFormat("History is not ready: %s %s",symbol,result.timeframe);
      return result;
     }

   int handle=FileOpen(result.filename,FileFlags(),',');
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("FileOpen failed: %s error=%d",result.filename,GetLastError());
      return result;
     }

   FileWrite(handle,
             "time","open","high","low","close",
             "tick_volume","spread","real_volume");

   const int period_seconds=PeriodSeconds(tf);
   int chunk_days=InpRatesChunkDays;
   if(chunk_days<1) chunk_days=1;
   datetime server_now=TimeTradeServer();
   if(server_now<=0) server_now=TimeCurrent();
   if(server_now<=0) server_now=InpToServerExclusive;
   datetime complete_cutoff=InpToServerExclusive;
   if(server_now<complete_cutoff) complete_cutoff=server_now;

   datetime cursor=InpFromServer;
   while(cursor<InpToServerExclusive)
     {
      datetime next=cursor+(datetime)(chunk_days*86400);
      if(next>InpToServerExclusive) next=InpToServerExclusive;

      MqlRates rates[];
      ArraySetAsSeries(rates,false);
      int copied=CopyRatesRetry(symbol,tf,cursor,next-1,rates);
      if(copied<0)
        {
         result.copy_errors++;
         FileClose(handle);
         PrintFormat("Export aborted after CopyRates failure: %s",result.filename);
         return result;
        }

      for(int i=0;i<copied;i++)
        {
         const datetime bar_time=rates[i].time;
         if(bar_time<InpFromServer || bar_time>=InpToServerExclusive)
            continue;

         // Export completed bars only. No forming/open bar is written.
         if(bar_time+(datetime)period_seconds>complete_cutoff)
            continue;

         FileWrite(handle,
                   TimeToString(bar_time,TIME_DATE|TIME_SECONDS),
                   DoubleToString(rates[i].open,digits),
                   DoubleToString(rates[i].high,digits),
                   DoubleToString(rates[i].low,digits),
                   DoubleToString(rates[i].close,digits),
                   (long)rates[i].tick_volume,
                   (int)rates[i].spread,
                   (long)rates[i].real_volume);

         if(result.rows==0) result.first_time=bar_time;
         result.last_time=bar_time;
         result.rows++;
        }

      PrintFormat("Export progress: tf=%s through=%s rows=%I64d",
                  result.timeframe,
                  TimeToString(next,TIME_DATE|TIME_SECONDS),
                  result.rows);
      cursor=next;
     }

   FileFlush(handle);
   FileClose(handle);
   result.ok=true;
   return result;
  }

void WriteMetadataHeader(const int handle)
  {
   FileWrite(handle,
             "captured_at_server","broker_company","account_server","terminal_build",
             "symbol","digits","point","requested_from_server","requested_to_server_exclusive",
             "timeframe","filename","rows","first_bar_time","last_bar_time",
             "csv_time_semantics","bar_availability_contract","gap_fill_applied","copy_errors");
  }

void WriteMetadataRow(const int handle,
                      const string symbol,
                      const int digits,
                      const double point,
                      const ExportResult &result)
  {
   int seconds=0;
   if(result.timeframe=="m1") seconds=60;
   if(result.timeframe=="m5") seconds=300;
   if(result.timeframe=="m15") seconds=900;
   if(result.timeframe=="h1") seconds=3600;
   if(result.timeframe=="h4") seconds=14400;
   if(result.timeframe=="d1") seconds=86400;

   FileWrite(handle,
             TimeToString(TimeTradeServer(),TIME_DATE|TIME_SECONDS),
             AccountInfoString(ACCOUNT_COMPANY),
             AccountInfoString(ACCOUNT_SERVER),
             (long)TerminalInfoInteger(TERMINAL_BUILD),
             symbol,digits,DoubleToString(point,digits),
             TimeToString(InpFromServer,TIME_DATE|TIME_SECONDS),
             TimeToString(InpToServerExclusive,TIME_DATE|TIME_SECONDS),
             result.timeframe,result.filename,result.rows,
             result.first_time==0 ? "" : TimeToString(result.first_time,TIME_DATE|TIME_SECONDS),
             result.last_time==0 ? "" : TimeToString(result.last_time,TIME_DATE|TIME_SECONDS),
             "broker_server_bar_open_time",
             StringFormat("source_close_time=time+%d_seconds",seconds),
             false,result.copy_errors);
  }

void ExportWeeklySessions(const string symbol,const string prefix)
  {
   string filename=prefix+"_weekly_sessions.csv";
   int handle=FileOpen(filename,FileFlags(),',');
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("Session FileOpen failed: %s error=%d",filename,GetLastError());
      return;
     }

   FileWrite(handle,
             "captured_at_server","broker_company","account_server","symbol",
             "weekday","session_index","from_hhmm","to_hhmm",
             "source_name","holiday_exceptions_included");

   for(int day=SUNDAY;day<=SATURDAY;day++)
     {
      for(uint index=0;index<32;index++)
        {
         datetime from_time=0;
         datetime to_time=0;
         ResetLastError();
         if(!SymbolInfoSessionTrade(symbol,(ENUM_DAY_OF_WEEK)day,index,from_time,to_time))
            break;

         FileWrite(handle,
                   TimeToString(TimeTradeServer(),TIME_DATE|TIME_SECONDS),
                   AccountInfoString(ACCOUNT_COMPANY),
                   AccountInfoString(ACCOUNT_SERVER),
                   symbol,
                   EnumToString((ENUM_DAY_OF_WEEK)day),
                   (int)index,
                   TimeToString(from_time,TIME_MINUTES),
                   TimeToString(to_time,TIME_MINUTES),
                   "MT5_SymbolInfoSessionTrade",
                   false);
        }
     }

   FileClose(handle);
   PrintFormat("Weekly sessions exported: %s",filename);
  }

void OnStart()
  {
   if(InpToServerExclusive<=InpFromServer)
     {
      Print("Invalid date range: InpToServerExclusive must be later than InpFromServer.");
      return;
     }

   string symbol=InpSymbol;
   if(symbol=="") symbol=_Symbol;

   if(!SymbolSelect(symbol,true))
     {
      PrintFormat("SymbolSelect failed for %s. Error=%d",symbol,GetLastError());
      return;
     }

   long digits_long=0;
   if(!SymbolInfoInteger(symbol,SYMBOL_DIGITS,digits_long))
     {
      PrintFormat("SYMBOL_DIGITS unavailable for %s. Error=%d",symbol,GetLastError());
      return;
     }
   int digits=(int)digits_long;
   double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   string prefix=SanitizePrefix(InpFilePrefix);

   string metadata_filename=prefix+"_metadata.csv";
   int metadata=FileOpen(metadata_filename,FileFlags(),',');
   if(metadata==INVALID_HANDLE)
     {
      PrintFormat("Metadata FileOpen failed: %s error=%d",metadata_filename,GetLastError());
      return;
     }
   WriteMetadataHeader(metadata);

   int requested=0;
   int succeeded=0;

   if(InpExportM1)
     {
      requested++;
      ExportResult r=ExportRatesFile(symbol,PERIOD_M1,prefix,digits);
      WriteMetadataRow(metadata,symbol,digits,point,r);
      if(r.ok) succeeded++;
     }
   if(InpExportM5)
     {
      requested++;
      ExportResult r=ExportRatesFile(symbol,PERIOD_M5,prefix,digits);
      WriteMetadataRow(metadata,symbol,digits,point,r);
      if(r.ok) succeeded++;
     }
   if(InpExportM15)
     {
      requested++;
      ExportResult r=ExportRatesFile(symbol,PERIOD_M15,prefix,digits);
      WriteMetadataRow(metadata,symbol,digits,point,r);
      if(r.ok) succeeded++;
     }
   if(InpExportH1)
     {
      requested++;
      ExportResult r=ExportRatesFile(symbol,PERIOD_H1,prefix,digits);
      WriteMetadataRow(metadata,symbol,digits,point,r);
      if(r.ok) succeeded++;
     }
   if(InpExportH4)
     {
      requested++;
      ExportResult r=ExportRatesFile(symbol,PERIOD_H4,prefix,digits);
      WriteMetadataRow(metadata,symbol,digits,point,r);
      if(r.ok) succeeded++;
     }
   if(InpExportD1)
     {
      requested++;
      ExportResult r=ExportRatesFile(symbol,PERIOD_D1,prefix,digits);
      WriteMetadataRow(metadata,symbol,digits,point,r);
      if(r.ok) succeeded++;
     }

   FileFlush(metadata);
   FileClose(metadata);

   if(InpExportWeeklySessions)
      ExportWeeklySessions(symbol,prefix);

   Print("------------------------------------------------------------");
   PrintFormat("GOLD V3 history export finished: symbol=%s success=%d/%d",symbol,succeeded,requested);
   PrintFormat("Requested server range: [%s, %s)",
               TimeToString(InpFromServer,TIME_DATE|TIME_SECONDS),
               TimeToString(InpToServerExclusive,TIME_DATE|TIME_SECONDS));
   PrintFormat("Output folder: %s",OutputRoot());
   Print("No missing bars were filled. CSV time is broker-server bar OPEN time.");
   Print("Please send all exported CSV files including metadata and weekly_sessions.");
  }
