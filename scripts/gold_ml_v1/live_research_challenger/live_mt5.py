from __future__ import annotations

import hashlib
import importlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from live_settings import RuntimeSettings, SLEEVES

MAGIC_OFFSETS = {comp: index + 1 for index, comp in enumerate(SLEEVES)}
COMMENT_CODES = {
    "A_CORE": "A",
    "B_STATE": "B",
    "P18": "P18",
    "W024A": "W24",
}


class MT5ExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrderResult:
    status: str
    retcode: int | None
    message: str
    magic: int
    comment: str
    symbol: str
    volume: float
    order_ticket: int | None = None
    deal_ticket: int | None = None
    position_ticket: int | None = None
    fill_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None


class MetaTrader5Client:
    def __init__(self, settings: RuntimeSettings):
        self.settings = settings
        self.mt5 = importlib.import_module("MetaTrader5")
        self._connected = False
        self.symbol_info: Any | None = None

    def __enter__(self) -> "MetaTrader5Client":
        kwargs: dict[str, Any] = {}
        if self.settings.mt5_login is not None:
            kwargs["login"] = self.settings.mt5_login
        if self.settings.mt5_password:
            kwargs["password"] = self.settings.mt5_password
        if self.settings.mt5_server:
            kwargs["server"] = self.settings.mt5_server
        if self.settings.mt5_terminal_path:
            ok = self.mt5.initialize(self.settings.mt5_terminal_path, **kwargs)
        else:
            ok = self.mt5.initialize(**kwargs)
        if not ok:
            raise MT5ExecutionError(
                f"MetaTrader5 initialize failed: {self.mt5.last_error()}"
            )
        self._connected = True
        self._validate_connection()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._connected:
            self.mt5.shutdown()
            self._connected = False

    def _validate_connection(self) -> None:
        terminal = self.mt5.terminal_info()
        account = self.mt5.account_info()
        if terminal is None or account is None:
            raise MT5ExecutionError(
                f"MT5 terminal/account info unavailable: {self.mt5.last_error()}"
            )
        if not bool(getattr(terminal, "connected", True)):
            raise MT5ExecutionError("MT5 terminal is not connected")
        if not bool(getattr(terminal, "trade_allowed", True)):
            raise MT5ExecutionError("MT5 terminal does not allow automated trading")
        if not bool(getattr(account, "trade_allowed", True)):
            raise MT5ExecutionError("MT5 account does not allow trading")
        if self.settings.mt5_require_hedging:
            hedging = getattr(self.mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", None)
            if hedging is not None and getattr(account, "margin_mode", None) != hedging:
                raise MT5ExecutionError(
                    "GML1 requires an MT5 hedging account so four sleeves remain "
                    "independently traceable"
                )

        symbol = self.settings.mt5_symbol
        if not symbol:
            raise MT5ExecutionError("MT5 symbol is not configured")
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise MT5ExecutionError(f"MT5 symbol not found: {symbol}")
        if not bool(getattr(info, "visible", False)):
            if not self.mt5.symbol_select(symbol, True):
                raise MT5ExecutionError(f"MT5 symbol_select failed: {symbol}")
            info = self.mt5.symbol_info(symbol)
        self.symbol_info = info

    def magic(self, comp: str) -> int:
        return self.settings.mt5_magic_base + MAGIC_OFFSETS[comp]

    @staticmethod
    def comment(candidate_key: str, comp: str) -> str:
        digest = hashlib.sha1(candidate_key.encode("utf-8")).hexdigest()[:12]
        return f"GML1-{COMMENT_CODES[comp]}-{digest}"[:31]

    @staticmethod
    def _asdict(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "_asdict"):
            return dict(value._asdict())
        if isinstance(value, dict):
            return dict(value)
        return {}

    def _normalize_volume(self, requested: float) -> float:
        info = self.symbol_info
        assert info is not None
        minimum = float(getattr(info, "volume_min", 0.0))
        maximum = float(getattr(info, "volume_max", requested))
        step = float(getattr(info, "volume_step", 0.0))
        if requested < minimum - 1e-12 or requested > maximum + 1e-12:
            raise MT5ExecutionError(
                f"requested volume {requested} outside broker range {minimum}..{maximum}"
            )
        if step <= 0:
            return requested
        units = round(requested / step)
        effective = units * step
        if not math.isclose(
            effective,
            requested,
            rel_tol=0.0,
            abs_tol=max(step * 1e-6, 1e-12),
        ):
            raise MT5ExecutionError(
                f"requested volume {requested} is not aligned to broker step {step}"
            )
        decimals = max(0, int(round(-math.log10(step)))) if step < 1 else 0
        return round(effective, decimals + 2)

    def _normalize_price(self, value: float) -> float:
        assert self.symbol_info is not None
        return round(float(value), int(getattr(self.symbol_info, "digits", 2)))

    def _filling_candidates(self) -> list[int]:
        configured = self.settings.mt5_filling_mode
        mapping = {
            "FOK": getattr(self.mt5, "ORDER_FILLING_FOK"),
            "IOC": getattr(self.mt5, "ORDER_FILLING_IOC"),
            "RETURN": getattr(self.mt5, "ORDER_FILLING_RETURN"),
        }
        if configured != "AUTO":
            return [mapping[configured]]
        values = [getattr(self.symbol_info, "filling_mode", None)]
        values.extend(mapping.values())
        output: list[int] = []
        for value in values:
            if value is not None and int(value) not in output:
                output.append(int(value))
        return output

    def gml1_positions(self) -> list[Any]:
        positions = self.mt5.positions_get(symbol=self.settings.mt5_symbol) or ()
        valid_magics = {self.magic(comp) for comp in SLEEVES}
        return [
            position
            for position in positions
            if int(getattr(position, "magic", -1)) in valid_magics
        ]

    def find_position(self, *, magic: int, comment: str) -> Any | None:
        positions = self.mt5.positions_get(symbol=self.settings.mt5_symbol) or ()
        exact = [
            position
            for position in positions
            if int(getattr(position, "magic", -1)) == magic
            and str(getattr(position, "comment", "")) == comment
        ]
        if exact:
            return exact[0]
        same_magic = [
            position
            for position in positions
            if int(getattr(position, "magic", -1)) == magic
        ]
        if len(same_magic) == 1:
            return same_magic[0]
        if len(same_magic) > 1:
            raise MT5ExecutionError(
                f"multiple open MT5 positions use GML1 magic {magic}; "
                "duplicate recovery is ambiguous"
            )
        return None

    def find_historical_deals(self, *, magic: int, comment: str) -> list[Any]:
        start = datetime.now() - timedelta(days=60)
        end = datetime.now() + timedelta(days=1)
        deals = self.mt5.history_deals_get(start, end) or ()
        return [
            deal
            for deal in deals
            if int(getattr(deal, "magic", -1)) == magic
            and str(getattr(deal, "comment", "")) == comment
        ]

    def recover_existing(self, *, magic: int, comment: str) -> OrderResult | None:
        position = self.find_position(magic=magic, comment=comment)
        if position is not None:
            return OrderResult(
                status="ORDER_RECOVERED_OPEN",
                retcode=None,
                message="existing MT5 position recovered by magic/comment",
                magic=magic,
                comment=comment,
                symbol=self.settings.mt5_symbol or "",
                volume=float(getattr(position, "volume", 0.0)),
                position_ticket=int(getattr(position, "ticket", 0)) or None,
                fill_price=float(getattr(position, "price_open", 0.0)) or None,
                stop_price=float(getattr(position, "sl", 0.0)) or None,
                target_price=float(getattr(position, "tp", 0.0)) or None,
            )
        deals = self.find_historical_deals(magic=magic, comment=comment)
        if deals:
            latest = sorted(
                deals, key=lambda item: int(getattr(item, "time_msc", 0))
            )[-1]
            return OrderResult(
                status="ORDER_RECOVERED_HISTORY",
                retcode=None,
                message="existing MT5 deal recovered by magic/comment",
                magic=magic,
                comment=comment,
                symbol=self.settings.mt5_symbol or "",
                volume=float(getattr(latest, "volume", 0.0)),
                deal_ticket=int(getattr(latest, "ticket", 0)) or None,
                position_ticket=int(getattr(latest, "position_id", 0)) or None,
                fill_price=float(getattr(latest, "price", 0.0)) or None,
            )
        return None

    def _position_id_from_deal(self, deal_ticket: int | None) -> int | None:
        if not deal_ticket:
            return None
        deals = self.mt5.history_deals_get(ticket=int(deal_ticket)) or ()
        for deal in deals:
            position_id = int(getattr(deal, "position_id", 0))
            if position_id > 0:
                return position_id
        return None

    def _validate_stops(self, price: float, stop: float, target: float) -> None:
        assert self.symbol_info is not None
        point = float(getattr(self.symbol_info, "point", 0.0))
        level_points = float(getattr(self.symbol_info, "trade_stops_level", 0.0))
        minimum = point * level_points
        if minimum > 0 and (
            abs(price - stop) + 1e-12 < minimum
            or abs(target - price) + 1e-12 < minimum
        ):
            raise MT5ExecutionError(
                f"ATR-derived SL/TP violates broker minimum stop distance {minimum}"
            )

    def open_market_order(
        self, record: dict[str, Any], volume_requested: float
    ) -> OrderResult:
        comp = str(record["comp"])
        direction = str(record["direction"])
        atr = float(record["atr"])
        target_r = float(record["target_r"])
        volume = self._normalize_volume(volume_requested)
        tick = self.mt5.symbol_info_tick(self.settings.mt5_symbol)
        if tick is None:
            raise MT5ExecutionError(f"MT5 tick unavailable: {self.mt5.last_error()}")
        if direction == "LONG":
            price = float(tick.ask)
            stop = price - atr
            target = price + target_r * atr
            order_type = self.mt5.ORDER_TYPE_BUY
        elif direction == "SHORT":
            price = float(tick.bid)
            stop = price + atr
            target = price - target_r * atr
            order_type = self.mt5.ORDER_TYPE_SELL
        else:
            raise MT5ExecutionError(f"unsupported direction: {direction}")
        price = self._normalize_price(price)
        stop = self._normalize_price(stop)
        target = self._normalize_price(target)
        self._validate_stops(price, stop, target)

        magic = self.magic(comp)
        comment = self.comment(str(record["candidate_key"]), comp)
        last_check: Any | None = None
        for filling in self._filling_candidates():
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": self.settings.mt5_symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": stop,
                "tp": target,
                "deviation": self.settings.mt5_deviation_points,
                "magic": magic,
                "comment": comment,
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            check = self.mt5.order_check(request)
            last_check = check
            if check is None or int(getattr(check, "retcode", -1)) != 0:
                continue
            result = self.mt5.order_send(request)
            if result is None:
                raise MT5ExecutionError(
                    f"order_send returned None: {self.mt5.last_error()}"
                )
            result_dict = self._asdict(result)
            retcode = int(result_dict.get("retcode", -1))
            success_codes = {
                int(getattr(self.mt5, "TRADE_RETCODE_DONE")),
                int(getattr(self.mt5, "TRADE_RETCODE_DONE_PARTIAL")),
            }
            if retcode not in success_codes:
                return OrderResult(
                    status="ORDER_REJECTED",
                    retcode=retcode,
                    message=str(result_dict.get("comment", "order_send rejected")),
                    magic=magic,
                    comment=comment,
                    symbol=self.settings.mt5_symbol or "",
                    volume=volume,
                    order_ticket=int(result_dict.get("order", 0)) or None,
                    deal_ticket=int(result_dict.get("deal", 0)) or None,
                    fill_price=float(result_dict.get("price", price)),
                    stop_price=stop,
                    target_price=target,
                )
            position = self.find_position(magic=magic, comment=comment)
            deal_ticket = int(result_dict.get("deal", 0)) or None
            position_ticket = int(
                getattr(position, "ticket", 0)
            ) or self._position_id_from_deal(deal_ticket)
            return OrderResult(
                status="ORDER_FILLED",
                retcode=retcode,
                message=str(result_dict.get("comment", "order executed")),
                magic=magic,
                comment=comment,
                symbol=self.settings.mt5_symbol or "",
                volume=float(result_dict.get("volume", volume)),
                order_ticket=int(result_dict.get("order", 0)) or None,
                deal_ticket=deal_ticket,
                position_ticket=position_ticket,
                fill_price=float(result_dict.get("price", price)),
                stop_price=stop,
                target_price=target,
            )
        check_message = self._asdict(last_check).get(
            "comment", "order_check rejected all filling modes"
        )
        raise MT5ExecutionError(str(check_message))

    def get_position(self, ticket: int) -> Any | None:
        positions = self.mt5.positions_get(ticket=int(ticket)) or ()
        return positions[0] if positions else None

    def close_position(self, ticket: int, *, comment: str, magic: int) -> OrderResult:
        position = self.get_position(ticket)
        if position is None:
            raise MT5ExecutionError(f"MT5 position {ticket} is not open")
        tick = self.mt5.symbol_info_tick(self.settings.mt5_symbol)
        if tick is None:
            raise MT5ExecutionError(f"MT5 tick unavailable: {self.mt5.last_error()}")
        position_type = int(getattr(position, "type", -1))
        if position_type == int(self.mt5.POSITION_TYPE_BUY):
            order_type = self.mt5.ORDER_TYPE_SELL
            price = float(tick.bid)
        elif position_type == int(self.mt5.POSITION_TYPE_SELL):
            order_type = self.mt5.ORDER_TYPE_BUY
            price = float(tick.ask)
        else:
            raise MT5ExecutionError(
                f"unsupported MT5 position type: {position_type}"
            )
        price = self._normalize_price(price)
        volume = float(getattr(position, "volume", 0.0))
        for filling in self._filling_candidates():
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": self.settings.mt5_symbol,
                "volume": volume,
                "type": order_type,
                "position": int(ticket),
                "price": price,
                "deviation": self.settings.mt5_deviation_points,
                "magic": magic,
                "comment": (comment + "-EXIT")[:31],
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            check = self.mt5.order_check(request)
            if check is None or int(getattr(check, "retcode", -1)) != 0:
                continue
            result = self.mt5.order_send(request)
            if result is None:
                raise MT5ExecutionError(
                    f"close order_send returned None: {self.mt5.last_error()}"
                )
            payload = self._asdict(result)
            retcode = int(payload.get("retcode", -1))
            success_codes = {
                int(getattr(self.mt5, "TRADE_RETCODE_DONE")),
                int(getattr(self.mt5, "TRADE_RETCODE_DONE_PARTIAL")),
            }
            return OrderResult(
                status=(
                    "TIME_EXIT_FILLED"
                    if retcode in success_codes
                    else "TIME_EXIT_REJECTED"
                ),
                retcode=retcode,
                message=str(payload.get("comment", "time exit sent")),
                magic=magic,
                comment=comment,
                symbol=self.settings.mt5_symbol or "",
                volume=float(payload.get("volume", volume)),
                order_ticket=int(payload.get("order", 0)) or None,
                deal_ticket=int(payload.get("deal", 0)) or None,
                position_ticket=int(ticket),
                fill_price=float(payload.get("price", price)),
            )
        raise MT5ExecutionError("time-exit order_check rejected all filling modes")

    def closed_position_profit(
        self, position_ticket: int
    ) -> tuple[float, datetime | None] | None:
        deals = self.mt5.history_deals_get(position=int(position_ticket)) or ()
        if not deals:
            return None
        entries_out = {
            int(getattr(self.mt5, "DEAL_ENTRY_OUT", 1)),
            int(getattr(self.mt5, "DEAL_ENTRY_OUT_BY", 3)),
        }
        if not any(
            int(getattr(deal, "entry", -1)) in entries_out for deal in deals
        ):
            return None
        net = 0.0
        last_time: datetime | None = None
        for deal in deals:
            net += float(getattr(deal, "profit", 0.0))
            net += float(getattr(deal, "commission", 0.0))
            net += float(getattr(deal, "swap", 0.0))
            net += float(getattr(deal, "fee", 0.0))
            timestamp = int(getattr(deal, "time", 0))
            if timestamp:
                converted = datetime.fromtimestamp(timestamp)
                if last_time is None or converted > last_time:
                    last_time = converted
        return net, last_time
