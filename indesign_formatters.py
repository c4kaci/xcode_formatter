#!/usr/bin/env python3
#
# indesign_formatters.py
#
# Adobe InDesign 2026 PMString formatter
#

import lldb


# ============================================================================
# Memory helpers
# ============================================================================

def read_u16(process, address):
    error = lldb.SBError()

    value = process.ReadUnsignedFromMemory(
        address,
        2,
        error)

    if not error.Success():
        raise RuntimeError(error.GetCString())

    return value


def read_u32(process, address):
    error = lldb.SBError()

    value = process.ReadUnsignedFromMemory(
        address,
        4,
        error)

    if not error.Success():
        raise RuntimeError(error.GetCString())

    return value


def read_u64(process, address):
    error = lldb.SBError()

    value = process.ReadUnsignedFromMemory(
        address,
        8,
        error)

    if not error.Success():
        raise RuntimeError(error.GetCString())

    return value


# ============================================================================
# UTF16 helpers
# ============================================================================

def read_utf16_fixed_length(process, address, length):
    chars = []

    for i in range(length):
        ch = read_u16(process, address + (i * 2))
        chars.append(ch)

    try:
        return "".join(chr(ch) for ch in chars)
    except Exception:
        return "<utf16 decode error>"


# ============================================================================
# PMString formatter
# ============================================================================
#
# InDesign 2026
#
# UnicodeSavvyString
#
# offset 0   : StringStorage* fStorage
# offset 8   : UTF16TextChar fSmallStorage[24]
# offset 56  : int32 fUTF16BufferLength
# offset 60  : int32 fNumChars
#
# sizeof(UnicodeSavvyString) = 64
# sizeof(PMString)           = 80
#
# Small string:
#     fStorage == nullptr
#     text in fSmallStorage
#
# Heap string:
#     fStorage != nullptr
#     UTF16 payload starts at StringStorage + 0x0C
#
# ============================================================================

def PMString_SummaryProvider(valobj, internal_dict):
    try:

        process = valobj.GetProcess()

        addr_obj = valobj.AddressOf()

        if not addr_obj.IsValid():
            return "<invalid PMString>"

        base_addr = addr_obj.GetValueAsUnsigned()

        if base_addr == 0:
            return "<invalid PMString>"

        fstorage = read_u64(process, base_addr + 0)
        utf16_len = read_u32(process, base_addr + 56)
        num_chars = read_u32(process, base_addr + 60)

        #
        # sanity checks
        #
        if utf16_len > 100000:
            return "<invalid PMString>"

        if num_chars > 100000:
            return "<invalid PMString>"

        #
        # Small String Optimization
        #
        if fstorage == 0:

            text = read_utf16_fixed_length(
                process,
                base_addr + 8,
                utf16_len)

            return '"' + text + '" [' + str(utf16_len) + ']'

        #
        # Heap StringStorage
        #
        # Observed InDesign 2026 layout:
        #
        # +0x00 header
        # +0x0C UTF16 payload
        #

        text_address = fstorage + 0x0C

        text = read_utf16_fixed_length(
            process,
            text_address,
            utf16_len)

        return '"' + text + '" [' + str(utf16_len) + ']'

    except Exception:
        return "<invalid PMString>"


# ============================================================================
# Registration
# ============================================================================

def __lldb_init_module(debugger, internal_dict):

    debugger.HandleCommand(
        "type summary delete PMString"
    )

    debugger.HandleCommand(
        "type summary add "
        "-F indesign_formatters.PMString_SummaryProvider "
        "PMString"
    )