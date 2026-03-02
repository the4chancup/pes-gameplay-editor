import struct
import zlib


class DecodeError(Exception):
    pass


def encode_header(buffer_compressed: bytes, buffer_uncompressed: bytes) -> bytes:
    return struct.pack(
        "< 3B 5s II",
        0x00,
        0x10,
        0x01,
        "WESYS".encode("UTF-8"),
        len(buffer_compressed),
        len(buffer_uncompressed),
    )


def decode_header(byte_buffer: bytes) -> memoryview[int] | None:
    if len(byte_buffer) < 16:
        return None
    header = byte_buffer[0:16]
    (magic,) = struct.unpack("< 4x 4s 8x", header)
    if magic != b"ESYS":
        return None
    return memoryview(byte_buffer)[16:]


def compress(byte_buffer: bytes) -> bytes:
    buffer_compressed = zlib.compress(byte_buffer)
    return encode_header(buffer_compressed, byte_buffer) + buffer_compressed


def try_compress(byte_buffer: bytes) -> bytes:
    buffer_compressed = zlib.compress(byte_buffer)
    if len(buffer_compressed) + 16 < len(byte_buffer):
        return encode_header(buffer_compressed, byte_buffer) + buffer_compressed
    else:
        return byte_buffer


def decompress(byte_buffer: bytes) -> bytes:
    buffer_compressed = decode_header(byte_buffer)
    if buffer_compressed is None:
        raise DecodeError()
    try:
        return zlib.decompress(buffer_compressed)
    except zlib.error:
        raise DecodeError()


def try_decompress(byte_buffer: bytes) -> bytes:
    buffer_compressed = decode_header(byte_buffer)
    if buffer_compressed is None:
        return byte_buffer
    try:
        return zlib.decompress(buffer_compressed)
    except zlib.error:
        raise DecodeError()


def is_compressed(byte_buffer: bytes) -> bool:
    buffer_compressed = decode_header(byte_buffer)
    return buffer_compressed is not None
