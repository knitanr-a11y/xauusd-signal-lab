#property strict
#property script_show_inputs
#property version   "1.00"
#property description "Read-only GOLD V3 forward tick-window exporter."
#property description "MQL5 Script: does not consume an EA slot."

enum ENUM_GOLD_V3_TICK_RANGE_MODE
  {
   GOLD_V3_LAST_HOURS=0,
   GOLD_V3_EXPLICIT_SERVER_RANGE=1
  };

input string                       InpSymbol             = "";
input ENUM_GOLD_V3_TICK_RANGE_MODE InpRangeMode          = GOLD_V3_LAST_HOURS;
input int                          InpLastHours          = 1;
input datetime                     InpFromServer         = D'2026.06.22 00:00:00';
input datetime                     InpToServerExclusive  = D'2026.06.22 01:00:00';
input string                       InpFilePrefix         = "gold_v3_forward_tick_window";
input bool                         InpUseCommonFolder    = false;
input int                          InpChunkMinutes       = 15;
input int                          InpCopyRetryCount     = 5;
input int                          InpRetrySleepMs       = 500;

string SanitizeFilePart(string value)
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
   StringReplace(value,"#","_");
   StringTrimLeft(value);
   StringTrimRight(value);
   if(value=="") value="gold_v3_forward_tick_window";
   return value;
  }

string TimeStampForFile(const datetime value)
  {
   MqlDateTime parts;
   TimeToStruct(value,parts);
   return StringFormat("%04d%02d%02d_%02d%02d%02d",
                       parts.year,parts.mon,parts.day,
                       parts.hour,parts.min,parts.sec);
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

int CopyTicksRetry(const string symbol,
                   const ulong from_msc,
                   const ulong to_msc,
                   MqlTick &ticks[])
  {
   int retries=InpCopyRetryCount;
   if(retries<1) retries=1;
   int sleep_ms=InpRetrySleepMs;
   if(sleep_ms<100) sleep_ms=100;

   for(int attempt=0;attempt<retries;attempt++)
     {
      ResetLastError();
      ArrayFree(ticks);
      ArraySetAsSeries(ticks,false);
      int copied=CopyTicksRange(symbol,ticks,COPY_TICKS_ALL,from_msc,to_msc);
      if(copied>=0) return copied;
      PrintFormat("CopyTicksRange retry: attempt=%d error=%d",attempt+1,GetLastError());
      Sleep(sleep_ms);
     }
   return -1;
  }

void WriteMetadata(const string filename,
                   const string symbol,
                   const int digits,
                   const double point,
                   const datetime from_server,
                   const datetime to_server_exclusive,
                   const string tick_filename,
                   const long rows,
                   const long first_tick_msc,
                   const long last_tick_msc,
                   const int chunks,
                   const int empty_chunks,
                   const int copy_errors,
                   const string status)
  {
   int handle=FileOpen(filename,FileFlags(),',');
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("Metadata FileOpen failed: %s error=%d",filename,GetLastError());
      return;
     }

   FileWrite(handle,
             "captured_at_server","broker_company","account_server","terminal_build",
             "symbol","digits","point","requested_from_server_inclusive",
             "requested_to_server_exclusive","tick_filename","rows",
             "first_tick_msc","last_tick_msc","chunks","empty_chunks",
             "copy_errors","status","time_contract","gap_fill_applied","audit_only");

   FileWrite(handle,
             TimeToString(TimeTradeServer(),TIME_DATE|TIME_SECONDS),
             AccountInfoString(ACCOUNT_COMPANY),
             AccountInfoString(ACCOUNT_SERVER),
             (long)TerminalInfoInteger(TERMINAL_BUILD),
             symbol,digits,DoubleToString(point,digits),
             TimeToString(from_server,TIME_DATE|TIME_SECONDS),
             TimeToString(to_server_exclusive,TIME_DATE|TIME_SECONDS),
             tick_filename,rows,first_tick_msc,last_tick_msc,chunks,empty_chunks,
             copy_errors,status,
             "input range is broker server time; time_msc is raw; no JST conversion",
             false,true);

   FileFlush(handle);
   FileClose(handle);
  }

void OnStart()
  {
   string symbol=InpSymbol;
   if(symbol=="") symbol=_Symbol;
   if(!SymbolSelect(symbol,true))
     {
      PrintFormat("SymbolSelect failed for %s. error=%d",symbol,GetLastError());
      return;
     }

   datetime server_now=TimeTradeServer();
   if(server_now<=0) server_now=TimeCurrent();
   if(server_now<=0)
     {
      Print("Server time unavailable. Confirm MT5 connection.");
      return;
     }

   datetime from_server=InpFromServer;
   datetime to_server_exclusive=InpToServerExclusive;
   if(InpRangeMode==GOLD_V3_LAST_HOURS)
     {
      if(InpLastHours<1)
        {
         Print("InpLastHours must be at least 1.");
         return;
        }
      to_server_exclusive=server_now+1;
      from_server=to_server_exclusive-(datetime)(InpLastHours*3600);
     }
   if(to_server_exclusive<=from_server)
     {
      Print("Invalid range: end must be later than start.");
      return;
     }

   long digits_long=0;
   if(!SymbolInfoInteger(symbol,SYMBOL_DIGITS,digits_long))
     {
      PrintFormat("SYMBOL_DIGITS unavailable for %s. error=%d",symbol,GetLastError());
      return;
     }
   int digits=(int)digits_long;
   double point=SymbolInfoDouble(symbol,SYMBOL_POINT);

   string prefix=SanitizeFilePart(InpFilePrefix);
   string symbol_part=SanitizeFilePart(symbol);
   string range_part=TimeStampForFile(from_server)+"_"+TimeStampForFile(to_server_exclusive);
   string tick_filename=prefix+"_"+symbol_part+"_"+range_part+".csv";
   string metadata_filename=prefix+"_"+symbol_part+"_"+range_part+"_metadata.csv";

   int tick_handle=FileOpen(tick_filename,FileFlags(),',');
   if(tick_handle==INVALID_HANDLE)
     {
      PrintFormat("Tick FileOpen failed: %s error=%d",tick_filename,GetLastError());
      return;
     }
   FileWrite(tick_handle,
             "tick_time_text","tick_time_epoch_seconds","time_msc_raw",
             "bid","ask","last","volume","volume_real","flags","spread_price");

   int chunk_minutes=InpChunkMinutes;
   if(chunk_minutes<1) chunk_minutes=1;
   datetime chunk_seconds=(datetime)(chunk_minutes*60);

   long total_rows=0;
   long first_tick_msc=0;
   long last_tick_msc=0;
   int chunks=0;
   int empty_chunks=0;
   int copy_errors=0;
   datetime cursor=from_server;

   while(cursor<to_server_exclusive)
     {
      datetime next=cursor+chunk_seconds;
      if(next>to_server_exclusive) next=to_server_exclusive;
      ulong from_msc=(ulong)cursor*1000;
      ulong to_msc=(ulong)next*1000-1;

      MqlTick ticks[];
      ArraySetAsSeries(ticks,false);
      int copied=CopyTicksRetry(symbol,from_msc,to_msc,ticks);
      chunks++;
      if(copied<0)
        {
         copy_errors++;
         cursor=next;
         continue;
        }
      if(copied==0) empty_chunks++;

      for(int i=0;i<copied;i++)
        {
         long tick_msc=ticks[i].time_msc;
         if((ulong)tick_msc<from_msc || (ulong)tick_msc>to_msc) continue;

         FileWrite(tick_handle,
                   TimeToString((datetime)ticks[i].time,TIME_DATE|TIME_SECONDS),
                   (long)ticks[i].time,tick_msc,
                   DoubleToString(ticks[i].bid,digits),
                   DoubleToString(ticks[i].ask,digits),
                   DoubleToString(ticks[i].last,digits),
                   (long)ticks[i].volume,
                   DoubleToString(ticks[i].volume_real,2),
                   (long)ticks[i].flags,
                   DoubleToString(ticks[i].ask-ticks[i].bid,digits));
         if(total_rows==0) first_tick_msc=tick_msc;
         last_tick_msc=tick_msc;
         total_rows++;
        }

      FileFlush(tick_handle);
      PrintFormat("Tick export progress: through=%s copied=%d total=%I64d",
                  TimeToString(next,TIME_DATE|TIME_SECONDS),copied,total_rows);
      cursor=next;
     }

   FileFlush(tick_handle);
   FileClose(tick_handle);

   string status="SUCCESS";
   if(total_rows==0 && copy_errors==0) status="NO_TICKS_RETURNED";
   if(copy_errors>0 && total_rows>0) status="PARTIAL_COPY_ERRORS";
   if(copy_errors>0 && total_rows==0) status="COPY_FAILED";

   WriteMetadata(metadata_filename,symbol,digits,point,
                 from_server,to_server_exclusive,tick_filename,total_rows,
                 first_tick_msc,last_tick_msc,chunks,empty_chunks,copy_errors,status);

   Print("------------------------------------------------------------");
   PrintFormat("GOLD V3 tick-window export: status=%s rows=%I64d",status,total_rows);
   PrintFormat("Range: [%s, %s)",
               TimeToString(from_server,TIME_DATE|TIME_SECONDS),
               TimeToString(to_server_exclusive,TIME_DATE|TIME_SECONDS));
   PrintFormat("Tick file: %s",tick_filename);
   PrintFormat("Metadata file: %s",metadata_filename);
   PrintFormat("Output folder: %s",OutputRoot());
   Print("Read-only audit script. No orders, position changes, or alerts.");
  }
