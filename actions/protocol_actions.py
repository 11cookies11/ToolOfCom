from __future__ import annotations

from typing import Dict

from actions.registry import ActionRegistry
from utils.crc16 import crc16_xmodem
from utils.file_utils import get_file_meta, read_block


class XMODEMPacketBuilder:
    @staticmethod
    def build_block(block_no: int, data: bytes, use_crc: bool = True) -> bytes:
        data128 = data[:128] if len(data) >= 128 else data + b"\x1A" * (128 - len(data))
        header = bytes([0x01, block_no & 0xFF, 0xFF - (block_no & 0xFF)])
        if use_crc:
            crc = crc16_xmodem(data128).to_bytes(2, "big")
            return header + data128 + crc
        checksum = sum(data128) & 0xFF
        return header + data128 + bytes([checksum])

    @staticmethod
    def build_eot() -> bytes:
        return bytes([0x04])


def send_xmodem_block(ctx, args: Dict[str, object]):
    meta = get_file_meta(ctx)
    block = int(ctx.eval_value(args.get("block", 1)))
    data = read_block(meta["path"], block, 128)
    packet = XMODEMPacketBuilder.build_block(block, data)
    ctx.channel_write(packet)
    ctx.set_var("last_sent_block", block)


def send_eot(ctx, args: Dict[str, object]):
    ctx.channel_write(XMODEMPacketBuilder.build_eot())


def register_protocol_actions():
    ActionRegistry.register("send_xmodem_block", send_xmodem_block)
    ActionRegistry.register("send_eot", send_eot)
