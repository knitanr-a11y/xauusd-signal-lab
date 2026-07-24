from pathlib import Path
import os
local=Path(os.environ.get('LOCALAPPDATA',''))/'xauusd_signal_lab'/'mochipoyo_alert_research'/'m9y_runtime';local.mkdir(parents=True,exist_ok=True);p=local/'STOP_M9Y_SHADOW_LOOP';p.write_text('STOP\n',encoding='utf-8');print('[M9Y STOP REQUESTED]',p)
