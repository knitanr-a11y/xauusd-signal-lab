#property script_show_inputs
#property strict

input string InpSymbol = "";
input string InpOutputFile = "stage263_mt5_weekly_sessions.csv";
input bool InpUseCommonFolder = true;

string HhMm(const datetime value)
  {
   return TimeToString(value,TIME_MINUTES);
  }

void OnStart()
  {
   string symbol=InpSymbol;
   if(symbol=="") symbol=_Symbol;
   if(!SymbolSelect(symbol,true))
     {
      PrintFormat("SymbolSelect failed for %s. Error %d",symbol,GetLastError());
      return;
     }

   int flags=FILE_WRITE|FILE_CSV|FILE_ANSI;
   if(InpUseCommonFolder) flags|=FILE_COMMON;
   int handle=FileOpen(InpOutputFile,flags,',');
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("FileOpen failed. Error %d",GetLastError());
      return;
     }

   FileWrite(handle,
             "captured_at_server","broker_company","account_server","symbol",
             "weekday","session_index","from_hhmm","to_hhmm",
             "source_name","source_version","holiday_exceptions_included");

   string company=AccountInfoString(ACCOUNT_COMPANY);
   string server=AccountInfoString(ACCOUNT_SERVER);
   datetime captured=TimeTradeServer();

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
                   TimeToString(captured,TIME_DATE|TIME_SECONDS),company,server,symbol,
                   EnumToString((ENUM_DAY_OF_WEEK)day),(int)index,HhMm(from_time),HhMm(to_time),
                   "MT5_SymbolInfoSessionTrade","CURRENT_TERMINAL_CAPTURE",false);
        }
     }
   FileClose(handle);
   PrintFormat("Weekly session schedule exported to %s. Holiday/short-session exceptions are NOT included.",InpOutputFile);
  }
