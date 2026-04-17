"""
pb_devkit.decompiler - PowerBuilder PBD/PBL Decompiler (library)
Based on PbdCli (https://github.com/Hucxy/PbdViewer).

Changes from original:
- RESOURCE_DIR points to package-internal resoures/
- get_string: ANSI uses gbk encoding for Chinese support (fallback latin-1)
- dump_function / dump_entry: return str instead of printing
- Library API: DecompileResult, decompile_file, decompile_bytes, list_entries, get_tree
"""

import struct
import sys
import os
import re
import gzip
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntFlag, IntEnum
from typing import List, Dict, Optional, Tuple, Any

# Directory containing system type .bin resources
RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resoures")

# ==================== Buffer Helpers ====================

def get_buffer(buf: bytes, offset: int, size: int) -> bytes:
    offset &= 0x7FFFFFFF
    size = min(size, len(buf) - offset)
    return buf[offset:offset + size]

def get_ushort(buf: bytes, offset: int) -> int:
    offset &= 0x7FFFFFFF
    return buf[offset] | (buf[offset + 1] << 8)

def get_uint(buf: bytes, offset: int) -> int:
    offset &= 0x7FFFFFFF
    return buf[offset] | (buf[offset + 1] << 8) | (buf[offset + 2] << 16) | (buf[offset + 3] << 24)

def get_string(is_unicode: bool, buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    end = offset
    if is_unicode:
        while end + 1 < len(buf) and (buf[end] != 0 or buf[end + 1] != 0):
            end += 2
    else:
        while end < len(buf) and buf[end] != 0:
            end += 1
    if end - offset == 0:
        return ""
    if is_unicode:
        return buf[offset:end].decode('utf-16-le', errors='replace')
    else:
        raw = buf[offset:end]
        try:
            return raw.decode('gbk', errors='strict')
        except (UnicodeDecodeError, LookupError):
            return raw.decode('latin-1', errors='replace')

def get_escape_string(is_unicode: bool, buf: bytes, offset: int) -> str:
    s = get_string(is_unicode, buf, offset)
    s = s.replace("~", "~~").replace("\r", "~r").replace("\n", "~n")
    s = s.replace("\t", "~t").replace('"', '~"')
    return f'"{s}"'

def get_date(buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    y = get_ushort(buf, offset + 4)
    return f"{y + 1900}-{buf[offset + 6] + 1:02d}-{buf[offset + 7]:02d}"

def get_time(buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    t = f"{buf[offset + 8]:02d}:{buf[offset + 9]:02d}:{buf[offset + 10]:02d}"
    ms = get_uint(buf, offset) // 1000
    if ms != 0:
        t += f".{ms:03d}"
    return t

def get_datetime(buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    return f"datetime({get_date(buf, offset)},{get_time(buf, offset)})"

def get_decimal(buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    sign = get_ushort(buf, offset)
    scale = buf[offset + 2]
    val = get_uint(buf, offset + 4) + (get_uint(buf, offset + 8) << 32) + (get_ushort(buf, offset + 12) << 64)
    text = str(val)
    if scale > 0:
        if len(text) <= scale:
            text = text.zfill(scale + 1)
        text = text[:-scale] + "." + text[-scale:].rstrip('0')
        if text.endswith('.'):
            text += '0'
    if sign > 0:
        text = "-" + text
    return text

def get_real(code: int) -> str:
    b = struct.pack('<I', code & 0xFFFFFFFF)
    return str(struct.unpack('<f', b)[0])

def get_double(buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    return str(struct.unpack_from('<d', buf, offset)[0])

def get_longlong(buf: bytes, offset: int) -> str:
    offset &= 0x7FFFFFFF
    return str(struct.unpack_from('<q', buf, offset)[0])

def get_cursor(is_unicode: bool, buf: bytes, offset: int, param_list) -> str:
    num = offset & 0x7FFFFFFF
    if get_uint(buf, num + 8) != 65535:
        return get_cursor(is_unicode, buf, get_uint(buf, num + 8), param_list)
    sql = get_string(is_unicode, buf, get_uint(buf, num + 24))
    text = ""
    if param_list is not None:
        num2 = get_uint(buf, num + 16)
        num3 = 0
        for param in param_list:
            u1 = get_ushort(buf, num2)
            u2 = get_ushort(buf, num2 + 2)
            num2 += 4
            if u1 == 0 and u2 == 0:
                break
            text = text + sql[num3:u1] + f":{param}"
            num3 = u2
        text += sql[num3:]
    return text


# ==================== Data Model ====================

class PbEnum:
    def __init__(self):
        self.index = 0
        self.name = ""
        self.items: Dict[int, str] = {}


VALUE_TYPE_NAMES = {
    0: "", 1: "integer", 2: "long", 3: "real", 4: "double",
    5: "decimal", 6: "string", 7: "boolean", 8: "any",
    9: "uint", 10: "ulong", 11: "blob", 12: "date",
    13: "time", 14: "datetime", 15: "cursor", 16: "procedure",
    18: "char", 19: "objhandle", 20: "longlong", 21: "byte",
}


class PbType:
    _value_types: Dict[int, 'PbType'] = {}

    def __init__(self):
        self.index = 0
        self.name = ""
        self.is_value_type = False
        self.is_system_type = False
        self.is_referenced_object = False
        self.enum: Optional[PbEnum] = None
        self.entry: Optional['PbEntry'] = None
        self.object: Optional['PbObject'] = None
        self._is_found = False

    @staticmethod
    def create_value_type(index: int) -> 'PbType':
        t = PbType()
        t.index = index
        t.name = VALUE_TYPE_NAMES.get(index, f"{index:04X}")
        t.is_value_type = True
        return t

    @staticmethod
    def create_user_type(entry: 'PbEntry', index: int, name: str, is_ref_obj: bool, is_system: bool) -> 'PbType':
        t = PbType()
        t.name = name
        t.entry = entry
        t.is_referenced_object = is_ref_obj
        if is_system:
            if is_ref_obj:
                raise Exception("system entry can't reference other object")
            t.is_system_type = True
            t.index = 0x4000 | index
            entry.project.system_types[t.index] = t
        else:
            if is_ref_obj:
                for e in entry.project.enums.values():
                    if e.name == name:
                        t.enum = e
                        break
            t.index = 0x8000 | index
            entry.types[t.index] = t
        return t

    @staticmethod
    def get_pb_type(entry: 'PbEntry', index: int) -> 'PbType':
        cat = index >> 12
        if cat == 0:
            if index not in PbType._value_types:
                PbType._value_types[index] = PbType.create_value_type(index)
            return PbType._value_types[index]
        elif cat == 4:
            return entry.project.system_types[index]
        elif cat == 8:
            return entry.types[index]
        elif cat == 12:
            return PbType.create_value_type(0)
        else:
            raise Exception(f"Unknown Type {index:04X}")

    def get_object(self, entry: 'PbEntry') -> Optional['PbObject']:
        if self.object is not None:
            return self.object
        if self.is_value_type:
            return None
        if self._is_found:
            return self.object
        if '`' in self.name or self.is_system_type or self.is_referenced_object:
            if self.name in entry.project.objects:
                self.object = entry.project.objects[self.name]
        else:
            e = self.entry or entry
            if self.index in e.objects:
                self.object = e.objects[self.index]
        self._is_found = True
        return self.object


class PbFunctionParam:
    def __init__(self):
        self.is_read_only = False
        self.is_reference = False
        self.type: Optional[PbType] = None
        self.name = ""
        self.array_string = ""

    def __str__(self):
        t = ""
        if self.is_reference: t += "ref "
        if self.is_read_only: t += "readonly "
        return f"{t}{self.type.name} {self.name}{self.array_string}"


class PbFunctionDefinition:
    def __init__(self):
        self.object: Optional['PbObject'] = None
        self.index = 0
        self.global_index = 0
        self.ref_index = 0
        self.event_code = 0
        self.flag = 0
        self.return_type: Optional[PbType] = None
        self.name = ""
        self.params: List[PbFunctionParam] = []
        self.library: Optional[str] = None
        self.alias: Optional[str] = None
        self.throws_type: Optional[PbType] = None

    @property
    def is_event(self): return bool(self.flag & 1)
    @property
    def is_external(self): return bool(self.flag & 4)
    @property
    def is_private(self): return bool(self.flag & 0x10)
    @property
    def is_protected(self): return bool(self.flag & 0x20)

    def __str__(self):
        r = ""
        if not self.is_event:
            if self.is_private: r += "private "
            elif self.is_protected: r += "protected "
            else: r += "public "
            r += "function " if self.return_type and self.return_type.index != 0 else "subroutine "
        else:
            r += "event "
        r += (self.return_type.name if self.return_type else "") + " "
        r += f"{self.name}({','.join(str(p) for p in self.params)})"
        if self.throws_type:
            r += f" throws {self.throws_type.name}"
        if self.library:
            r += f' library "{self.library}" alias for "{self.alias}"'
        return r


class PbReferencedFunction:
    def __init__(self, index, buf):
        self.index = index
        self.buffer = buf
        self.name = ""
        self.global_index = 0
        self.is_global_function = False


class PbVariable:
    def __init__(self, entry: 'PbEntry', index: int, buf: bytes, struct_buffer: bytes, delay_parse: bool):
        self.entry = entry
        self.buffer = buf
        self.index = index
        self.flag = buf[17]
        self.is_private = bool(self.flag & 64)
        self.is_protected = bool(self.flag & 128)
        self.access_string = "private " if self.is_private else ("protected " if self.is_protected else "")
        self.is_shared = bool(self.flag & 2)
        self.is_referenced_global = (buf[16] & 0x40) == 64
        self.is_instance = (buf[0] & 0xF) <= 1
        self.is_indirect = (buf[0] & 2) == 2
        self.is_constant = (buf[0] & 4) == 4
        self.is_custom = bool(self.flag & 1)
        self.is_array = bool(self.flag & 32)
        self.is_invalid = (self.flag & 12) == 12
        self.type: Optional[PbType] = None
        self.precision_or_size = ""
        self.object: Optional['PbObject'] = None
        self._sql_declare: Optional[str] = None

        if not delay_parse:
            self.parse_type()
        self.name = get_string(entry.project.is_unicode, struct_buffer, get_uint(buf, 8))
        self.array_string = PbVariable.get_array_string(get_uint(buf, 4), struct_buffer)

    @property
    def global_index(self):
        if not self.is_shared:
            return 0xFFFF
        return get_ushort(self.buffer, 12)

    def parse_type(self):
        self.type = PbType.get_pb_type(self.entry, get_ushort(self.buffer, 18))
        if self.type.is_value_type:
            if self.type.name == "blob":
                u = get_ushort(self.buffer, 12)
                self.precision_or_size = "" if u == 0 else f"{{{u}}}"
            elif self.type.name == "decimal":
                n = self.buffer[16] & 0x3F
                self.precision_or_size = "" if n == 62 else f"{{{self.buffer[16] // 2}}}"

    def inherit(self, control: 'PbObject') -> 'PbVariable':
        import copy
        v = copy.copy(self)
        v.type = control.type
        v.entry = control.entry
        v.object = control
        return v

    @staticmethod
    def get_array_string(offset: int, buf: bytes) -> str:
        if offset == 65535:
            return ""
        text = "["
        dim = buf[offset]
        for i in range(dim):
            if i != 0: text += ","
            lo = get_uint(buf, offset + 4 + i * 8)
            hi = get_uint(buf, offset + 8 + i * 8)
            if lo == 1:
                text += str(hi)
            elif lo != hi or hi != 0:
                text += f"{lo} to {hi}"
        text += "]"
        return text

    def get_value(self, value_buffer: bytes) -> Optional[str]:
        if not self.is_custom: return None
        if not self.type.is_value_type and self.type.enum is None: return None
        if self.is_indirect or self.is_referenced_global: return None
        if self.is_array:
            if self.is_invalid: return None
            lst = self._get_list(value_buffer)
            vals = [self._get_value(o, value_buffer, True) for o in lst]
            while vals and vals[-1] is None: vals.pop()
            for i in range(len(vals)):
                if vals[i] is None: vals[i] = self._get_value(lst[i], value_buffer, False)
            return "{" + ",".join(str(v) for v in vals) + "}"
        return self._get_value(get_uint(self.buffer, 12), value_buffer, True)

    def _get_value(self, code: int, vb: bytes, check_default: bool) -> Optional[str]:
        if self.type.enum is not None:
            if not check_default or (code & 0xFFFF) != 0:
                return self.type.enum.items.get(code & 0xFFFF, f"enum_{code}")
            return None
        name = self.type.name
        code_s = struct.pack('<I', code & 0xFFFFFFFF)
        if name == "integer":
            v = struct.unpack('<h', code_s[:2])[0]
            return str(v) if not check_default or v != 0 else None
        elif name == "uint":
            v = code & 0xFFFF
            return str(v) if not check_default or v != 0 else None
        elif name == "long":
            v = struct.unpack('<i', code_s)[0]
            return str(v) if not check_default or v != 0 else None
        elif name == "ulong":
            return str(code) if not check_default or code != 0 else None
        elif name == "char":
            return f"'{chr(code & 0xFFFF)}'" if not check_default or (code & 0xFFFF) != 0 else None
        elif name == "byte":
            return str(code & 0xFF) if not check_default or (code & 0xFF) != 0 else None
        elif name == "boolean":
            return str((code & 0xFF) != 0).lower() if not check_default or (code & 0xFF) != 0 else None
        elif name == "real":
            return get_real(code) if not check_default or code != 0 else None
        elif name == "string":
            s = get_string(self.entry.project.is_unicode, vb, code)
            if not check_default or (not self.is_invalid and s != ""):
                return get_escape_string(self.entry.project.is_unicode, vb, code)
            return None
        elif name == "decimal":
            d = get_decimal(vb, code)
            return d if not check_default or (not self.is_invalid and d != "0.0") else None
        elif name == "double":
            d = get_double(vb, code)
            return d if not check_default or (not self.is_invalid and d != "0") else None
        elif name == "longlong":
            d = get_longlong(vb, code)
            return d if not check_default or (not self.is_invalid and d != "0") else None
        elif name == "date":
            d = get_date(vb, code)
            return d if not check_default or (not self.is_invalid and d != "1900-01-01") else None
        elif name == "time":
            d = get_time(vb, code)
            return d if not check_default or (not self.is_invalid and d != "00:00:00") else None
        elif name == "datetime":
            d = get_datetime(vb, code)
            return d if not check_default or (not self.is_invalid and d != "datetime(1900-01-01,00:00:00)") else None
        return None

    def _get_list(self, vb: bytes) -> List[int]:
        lst = []
        u = get_ushort(self.buffer, 12)
        u2 = get_ushort(vb, u + 14)
        pos = u + 28 + u2 * 8
        count = get_uint(vb, pos)
        for i in range(count):
            lst.append(get_uint(vb, pos + 4 + 8 * i))
        return lst

    def set_cursor_params(self, param_list, sqlca_str):
        if self._sql_declare is None:
            c = get_cursor(self.entry.project.is_unicode, self.entry.variable_buffer, get_uint(self.buffer, 12), param_list)
            self._sql_declare = f"declare {self.name} cursor for {c} using {sqlca_str} ;"

    def set_dynamic_cursor_params(self, sqlsa_str):
        if self._sql_declare is None:
            c = get_cursor(self.entry.project.is_unicode, self.entry.variable_buffer, get_uint(self.buffer, 12), None)
            self._sql_declare = f"declare {self.name} dynamic cursor {c} for {sqlsa_str} ;"

    def set_procedure_params(self, param_list, sqlca_str):
        if self._sql_declare is None:
            c = get_cursor(self.entry.project.is_unicode, self.entry.variable_buffer, get_uint(self.buffer, 12), param_list).replace("execute ", "")
            self._sql_declare = f"declare {self.name} procedure for {c} using {sqlca_str} ;"

    def set_dynamic_procedure_params(self, sqlsa_str):
        if self._sql_declare is None:
            c = get_cursor(self.entry.project.is_unicode, self.entry.variable_buffer, get_uint(self.buffer, 12), None)
            self._sql_declare = f"declare {self.name} dynamic procedure {c} for {sqlsa_str} ;"

    def to_string(self, value_buffer=None) -> str:
        text = f"{self.access_string}{self.type.name}{self.precision_or_size} {self.name}{self.array_string}"
        if self._sql_declare is not None:
            text = self._sql_declare
        if self.is_constant:
            text = "constant " + text
        if value_buffer is not None:
            val = None
            if not self.is_referenced_global:
                val = self.get_value(value_buffer)
            if val is not None:
                text += f" = {val}"
        return text


class PbFunction:
    def __init__(self, obj: 'PbObject'):
        self.object = obj
        self.entry = obj.entry
        self.project = obj.entry.project
        self.index = 0
        self.definition: Optional[PbFunctionDefinition] = None
        self.pcode_bytes = b''
        self.debug_bytes = b''
        self.buffer = b''
        self.variables: List[PbVariable] = []


class PbObject:
    def __init__(self, entry: 'PbEntry', index: int, pb_type: PbType):
        self.entry = entry
        self.project = entry.project
        self.index = index
        self.type = pb_type
        self.inherit_type: Optional[PbType] = None
        self.inherit_object: Optional['PbObject'] = None
        self.parent_type: Optional[PbType] = None
        self.parent_object: Optional['PbObject'] = None
        self.functions: List[PbFunction] = []
        self.variables: List[PbVariable] = []
        self.referenced_functions: List[PbReferencedFunction] = []
        self.function_definitions: List[PbFunctionDefinition] = []
        self.all_variables: List[Optional[PbVariable]] = []
        self.all_function_definitions: List[Optional[PbFunctionDefinition]] = []
        self.controls: List['PbObject'] = []
        self._parsed_inherit = False

    def parse_inherit(self):
        if self._parsed_inherit:
            return
        if self.inherit_type:
            self.inherit_object = self.inherit_type.get_object(self.entry)
        if self.parent_type:
            self.parent_object = self.parent_type.get_object(self.entry)
        if self.inherit_object:
            self.inherit_object.parse_inherit()
            n = min(len(self.inherit_object.all_variables), len(self.all_variables))
            for i in range(n):
                self.all_variables[i] = self.inherit_object.all_variables[i]
            for fd in self.inherit_object.all_function_definitions:
                if fd is not None:
                    self.all_function_definitions[fd.global_index] = fd
        inst_vars = [v for v in self.variables if v.is_instance]
        inst_vars.reverse()
        for k, v in enumerate(inst_vars):
            self.all_variables[len(self.all_variables) - 1 - k] = v
        for fd in self.function_definitions:
            self.all_function_definitions[fd.global_index] = fd
        self.controls = [o for o in self.entry.objects.values() if o.parent_type == self.type]
        for l in range(len(self.all_variables)):
            variable = self.all_variables[l]
            if variable is not None:
                ctrl = next((o for o in self.controls if o.type.name == variable.name), None)
                if ctrl is not None and ctrl.type != variable.type:
                    self.all_variables[l] = variable.inherit(ctrl)
        self._parsed_inherit = True


# ==================== PbEntry ====================

class PbEntry:
    def __init__(self, file: 'PbFile', entry_name: str, entry_data: bytes):
        self._entry_data = entry_data
        self.file = file
        self.entry_name = entry_name
        self.project = file.project
        self.name = entry_name[:entry_name.rfind('.')]
        self.suffix = entry_name[entry_name.rfind('.') + 1:]
        self.types: Dict[int, PbType] = {}
        self.objects: Dict[int, PbObject] = {}
        self.entry_object: Optional[PbObject] = None
        self.source: Optional[str] = None
        self.variable_buffer: bytes = b''
        self.variables: List[PbVariable] = []
        self._function_buffer: bytes = b''
        self._param_buffer: bytes = b''
        self._is_parsed = False
        self._data_buffer: bytes = b''
        self._position = 0
        self.modified_time = datetime.min
        self.compiled_time = datetime.min

        if self.suffix in ('ico', 'jpg', 'png', 'bmp'):
            self._is_parsed = True
        elif self.suffix == 'exe':
            self._parse_exe()
            self._is_parsed = True
        elif self.suffix == 'srj':
            self._parse_srj()
            self._is_parsed = True
        elif self.suffix == 'grp':
            self.project.system_entry = self
            self.parse_object(is_system=True)
            self._is_parsed = True
        elif self.suffix in ('apl', 'str', 'fun', 'win', 'men', 'udo'):
            self.project.on_system_library(get_ushort(self._entry_data, 0))
        elif self.suffix == 'dwo':
            self.source = "(DataWindow object - binary)"
            self._is_parsed = True
        else:
            self.source = self.project.get_string_from_buf(self._entry_data)
            self._is_parsed = True

    def parse_object(self, is_system=False):
        if self._is_parsed:
            return
        self._data_buffer = self._entry_data
        self._position = 0
        pdb_ver = self._read_ushort()
        flag = self._read_ushort()
        entry_type = self._read_uint()
        unk1 = self._read_uint()
        self.modified_time = self._get_time(self._read_uint())
        if self.project.version >= 334:
            self._read_uint()
        self.compiled_time = self._get_time(self._read_uint())
        if self.project.version >= 334:
            self._read_uint()
        unk2 = self._read_uint()
        num4 = self._read_ushort()
        for i in range(num4):
            self._read_buffer(12)
        self.variable_buffer = self._read_struct_buffer()
        self.variables = self._read_variables(delay_parse=True)
        num5 = self._read_ushort()
        num6 = self._read_ushort()
        self._function_buffer = self._read_struct_buffer()
        self._param_buffer = self._read_struct_buffer()
        self._read_types(is_system)
        for v in self.variables:
            v.parse_type()
        enums = self._read_variables()
        for e in enums:
            self.project.on_new_enum_item(e.type, get_ushort(e.buffer, 12), e.name)

        obj_size = 8 if self.project.is_pb5 else 16
        obj_bufs = [self._read_buffer(obj_size) for _ in range(num5)]
        inh_bufs = [self._read_buffer(32) for _ in range(num6)]

        inh_idx = 0
        for i in range(num5):
            ob = obj_bufs[i]
            pb_type = PbType.get_pb_type(self, get_ushort(ob, 2))
            pb_obj = PbObject(self, i, pb_type)
            ctrl_type = (ob[0] >> 1) & 7
            if ctrl_type == 0:
                ib = inh_bufs[inh_idx]; inh_idx += 1
                pb_obj.inherit_type = PbType.get_pb_type(self, get_ushort(ib, 0))
                pb_obj.parent_type = PbType.get_pb_type(self, get_ushort(ib, 2))
                self.objects[pb_obj.type.index] = pb_obj
                if is_system:
                    self.project.objects[pb_obj.type.name] = pb_obj
                elif pb_obj.type.name == self.name:
                    self.entry_object = pb_obj
                    self.project.objects[pb_obj.type.name] = pb_obj
                elif '`' not in pb_obj.type.name:
                    self.project.objects[self.name + '`' + pb_obj.type.name] = pb_obj
                self._read_object(pb_obj, ib)
            elif ctrl_type == 1:
                cnt = get_ushort(ob, 4)
                for _ in range(cnt):
                    self._read_buffer(8)
        self._is_parsed = True

    def _read_object(self, pb_obj: PbObject, buffer: bytes):
        func_count = self._read_ushort()
        pb_obj.functions = [None] * func_count
        func_idx_bufs = [self._read_buffer(4) for _ in range(func_count)]
        for j in range(func_count):
            pb_obj.functions[j] = PbFunction(pb_obj)
            self._read_function(pb_obj.functions[j], func_idx_bufs[j])
        n1 = get_ushort(buffer, 24)
        self._read_buffer(6 * n1)
        n2 = get_ushort(buffer, 22)
        self._read_buffer(4 * n2)
        pb_obj.referenced_functions = self._read_referenced_functions()
        pb_obj.variables = self._read_variables()
        for v in pb_obj.variables:
            v.object = pb_obj
        all_var_count = get_ushort(buffer, 28)
        self._read_buffer(8 * all_var_count)
        pb_obj.all_variables = [None] * all_var_count
        struct_size = 12 if self.project.is_pb5 else 16
        n3 = get_ushort(buffer, 26)
        self._read_buffer(struct_size * n3)
        fd_count = get_ushort(buffer, 4)
        fd_size = 48 if self.project.version > 146 else (32 if self.project.is_pb5 else 44)
        pb_obj.function_definitions = [None] * fd_count
        pb_obj.all_function_definitions = [None] * get_ushort(buffer, 16)
        for i in range(fd_count):
            fb = self._read_buffer(fd_size)
            fd = PbFunctionDefinition()
            pb_obj.function_definitions[i] = fd
            fd.object = pb_obj
            fd.index = i
            fd.flag = fb[27 if self.project.is_pb5 else 31]
            fd.return_type = PbType.get_pb_type(self, get_ushort(fb, 24 if self.project.is_pb5 else 28))
            fd.name = get_string(self.project.is_unicode, self._function_buffer, get_uint(fb, 0))
            if fd.name.startswith('+'):
                fd.name = fd.name[1:]
            fd.global_index = get_ushort(fb, 16 if self.project.is_pb5 else 20)
            fd.ref_index = get_ushort(fb, 18 if self.project.is_pb5 else 22)
            fd.event_code = get_ushort(fb, 28 if self.project.is_pb5 else 32)
            fd.params = []
            param_offset = get_uint(fb, 4 if self.project.is_pb5 else 8)
            if param_offset != 65535:
                param_count = fb[26 if self.project.is_pb5 else 30]
                for m in range(param_count):
                    p = PbFunctionParam()
                    pb = get_buffer(self._param_buffer, int(param_offset) + m * 12, 12)
                    if (pb[10] & 4) == 4: p.is_read_only = True
                    elif (pb[10] & 2) == 2: p.is_reference = True
                    p.type = PbType.get_pb_type(self, get_ushort(pb, 8))
                    p.name = get_string(self.project.is_unicode, self._function_buffer, get_uint(pb, 0))
                    p.array_string = PbVariable.get_array_string(get_uint(pb, 4), self._function_buffer)
                    fd.params.append(p)
            lib_offset = get_uint(fb, 8 if self.project.is_pb5 else 12)
            if lib_offset != 65535:
                alias_offset = get_uint(fb, 12 if self.project.is_pb5 else 16)
                fd.library = get_string(self.project.is_unicode, self._function_buffer, alias_offset)
                fd.alias = get_string(self.project.is_unicode, self._function_buffer, lib_offset)
            if self.project.version > 146 and len(fb) >= 46:
                throw_idx = get_ushort(fb, 44)
                if throw_idx != 0xFFFF:
                    fd.throws_type = PbType.get_pb_type(self, get_ushort(self._function_buffer, throw_idx))

    def _read_function(self, pf: PbFunction, index_buf: bytes):
        pf.index = get_ushort(index_buf, 2)
        pcode_len = self._read_ushort()
        debug_count = self._read_ushort()
        self._read_ushort()  # unknown
        pf.pcode_bytes = self._read_buffer(pcode_len)
        pf.debug_bytes = self._read_buffer(debug_count * 4)
        pf.variables = self._read_variables()
        pf.buffer = self._read_struct_buffer()
        for v in pf.variables:
            v.object = pf.object

    def _read_ushort(self) -> int:
        self._position += 2
        return get_ushort(self._data_buffer, self._position - 2)

    def _read_uint(self) -> int:
        self._position += 4
        return get_uint(self._data_buffer, self._position - 4)

    def _read_buffer(self, size: int) -> bytes:
        self._position += size
        return get_buffer(self._data_buffer, self._position - size, size)

    def _read_struct_buffer(self) -> bytes:
        s1 = self._read_uint()
        s2 = self._read_uint()
        r = self._read_buffer(s1)
        self._read_buffer(s2)
        return r

    def _read_types(self, is_system: bool):
        self._read_buffer(6)
        buffer = self._read_struct_buffer()
        num = self._read_ushort() // 20
        for i in range(num):
            tb = self._read_buffer(20)
            PbType.create_user_type(self, i,
                get_string(self.project.is_unicode, buffer, get_uint(tb, 8)),
                tb[16] == 64, is_system)

    def _read_variables(self, delay_parse=False) -> List[PbVariable]:
        self._read_buffer(6)
        struct_buf = self._read_struct_buffer()
        num = self._read_ushort() // 20
        result = []
        for i in range(num):
            vb = self._read_buffer(20)
            result.append(PbVariable(self, i, vb, struct_buf, delay_parse))
        return result

    def _read_referenced_functions(self) -> List[PbReferencedFunction]:
        self._read_buffer(6)
        buffer = self._read_struct_buffer()
        num = self._read_ushort() // 20
        result = []
        for i in range(num):
            rb = self._read_buffer(20)
            rf = PbReferencedFunction(i, rb)
            rf.name = get_string(self.project.is_unicode, buffer, get_uint(rb, 8))
            rf.global_index = get_ushort(rb, 12)
            rf.is_global_function = (rb[16] == 2)
            result.append(rf)
        return result

    def parse_inherit(self):
        for o in self.objects.values():
            o.parse_inherit()

    def _parse_srj(self):
        self.source = self.project.get_string_from_buf(self._entry_data)
        for line in self.source.split('\n'):
            line = line.strip()
            if line.startswith("PBD:"):
                self.project.on_new_library(line[4:].split(',')[0], True)

    def _parse_exe(self):
        libs = []
        entries = []
        data = self._entry_data
        if self.project.is_unicode:
            pos = 0
            cnt = data[pos] | (data[pos + 1] << 8); pos += 2
            while cnt > 0:
                while data[pos] != 0 or data[pos + 1] != 0: pos += 2
                pos += 2; cnt -= 1
            cnt = data[pos] | (data[pos + 1] << 8); pos += 2; start = pos
            while cnt > 0:
                while data[pos] != 0 or data[pos + 1] != 0: pos += 2
                libs.append(data[start:pos].decode('utf-16-le')); pos += 2; start = pos; cnt -= 1
            cnt = data[pos] | (data[pos + 1] << 8); pos += 2; start = pos
            while cnt > 0:
                while data[pos] != 0 or data[pos + 1] != 0: pos += 2
                entries.append(data[start:pos].decode('utf-16-le')); pos += 2; start = pos; cnt -= 1
        else:
            j = 0 if self.project.is_pb5 else 1
            cnt = 1 if self.project.is_pb5 else data[0]
            while cnt > 0:
                while data[j] != 0: j += 1
                j += 1; cnt -= 1
            cnt = data[j] | (data[j + 1] << 8); j += 2; start = j
            while cnt > 0:
                while data[j] != 0: j += 1
                libs.append(data[start:j].decode('latin-1')); j += 1; start = j; cnt -= 1
            cnt = data[j] | (data[j + 1] << 8); j += 2; start = j
            while cnt > 0:
                while data[j] != 0: j += 1
                entries.append(data[start:j].decode('latin-1')); j += 1; start = j; cnt -= 1
        for lib in libs:
            self.project.on_new_library(lib, False)
        self.source = "Libraries:\n  " + "\n  ".join(libs) + "\nEntries:\n  " + "\n  ".join(entries)

    @staticmethod
    def _get_time(ts: int) -> datetime:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except:
            return datetime.min


# ==================== PbFile ====================

class PbFile:
    def __init__(self, project: 'PbProject', file_path: str):
        self.project = project
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.entries: List[PbEntry] = []

        with open(file_path, 'rb') as f:
            data = f.read()

        node_list = self._get_node_list(data)
        for node_offset in node_list:
            buf = data[node_offset:node_offset + 32]
            current = node_offset + 32
            entry_count = get_ushort(buf, 20)
            char_size = 2 if self.project.is_unicode else 1
            header_size = 4 + char_size * 4
            total_header_size = header_size + 16

            for i in range(entry_count):
                hdr = data[current:current + total_header_size]
                if hdr[:4] != b'ENT*':
                    raise Exception("Format error at ENT*")
                ver_str = self.project.get_string_from_buf_slice(hdr, 4, char_size * 4)
                if ver_str not in ('0600', '0500'):
                    raise Exception(f"Unknown ENT version: {ver_str}")
                data_start = get_uint(hdr, header_size)
                data_size = get_uint(hdr, header_size + 4)
                name_len = get_ushort(hdr, header_size + 14)
                name_buf = data[current + total_header_size:current + total_header_size + name_len]
                current = current + total_header_size + name_len
                name = self.project.get_string_from_buf_slice(name_buf, 0, name_len - char_size)
                entry_data = self._read_data(data, data_start, data_size)
                self.entries.append(PbEntry(self, name, entry_data))

    @staticmethod
    def _read_data(data: bytes, start: int, size: int) -> bytes:
        result = bytearray(size)
        pos = 0
        offset = start
        while pos < size:
            if offset + 10 > len(data):
                break
            hdr = data[offset:offset + 10]
            if hdr[:4] != b'DAT*':
                break
            chunk_size = get_ushort(hdr, 8)
            result[pos:pos + chunk_size] = data[offset + 10:offset + 10 + chunk_size]
            pos += chunk_size
            offset = get_uint(hdr, 4)
        return bytes(result)

    def _get_node_list(self, data: bytes) -> List[int]:
        node_list = []
        base_offset = 0
        found = False

        # scan for HDR*
        pos = 0
        while pos + 512 <= len(data):
            block = data[pos:pos + 512]
            if block[:4] == b'HDR*':
                if block[4:16] == b'PowerBuilder':
                    if block[18:22] == b'0500':
                        self.project.is_pb5 = True; found = True; base_offset = pos; break
                    if block[18:22] == b'0600':
                        found = True; base_offset = pos; break
                try:
                    if block[4:28].decode('utf-16-le') == 'PowerBuilder' and block[32:40].decode('utf-16-le') == '0600':
                        found = True; self.project.is_unicode = True; base_offset = pos; break
                except:
                    pass
            pos += 512

        if found:
            base_offset += 1536 if self.project.is_unicode else 1024
            block = data[base_offset:base_offset + 512]
            if len(block) != 512 or block[:4] != b'NOD*':
                raise Exception("Format error at NOD*")
            node_list.append(base_offset)
            next1 = get_uint(block, 4)
            next2 = get_uint(block, 12)
            while next1 != 0:
                block = data[next1:next1 + 512]
                if len(block) != 512 or block[:4] != b'NOD*':
                    raise Exception("Format error at NOD*")
                node_list.append(next1)
                next1 = get_uint(block, 4)
            while next2 != 0:
                block = data[next2:next2 + 512]
                if len(block) != 512 or block[:4] != b'NOD*':
                    raise Exception("Format error at NOD*")
                node_list.append(next2)
                next2 = get_uint(block, 12)
        return node_list


# ==================== PbProject ====================

class PbProject:
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._dir = os.path.dirname(file_path)
        self.is_debug = False
        self.files: List[PbFile] = []
        self.objects: Dict[str, PbObject] = {}
        self.system_types: Dict[int, PbType] = {}
        self.enums: Dict[int, PbEnum] = {}
        self.system_entry: Optional[PbEntry] = None
        self.is_unicode = False
        self.is_pb5 = False
        self.version = 0

        main_file = PbFile(self, file_path)
        self.files.insert(0, main_file)
        for f in self.files:
            for entry in f.entries:
                entry.parse_object()
        if self.system_entry:
            self.system_entry.parse_inherit()
        for f in self.files:
            for entry in f.entries:
                entry.parse_inherit()

    def get_string_from_buf(self, buf: bytes) -> str:
        if self.is_unicode:
            return buf.decode('utf-16-le', errors='replace')
        return buf.decode('latin-1', errors='replace')

    def get_string_from_buf_slice(self, buf: bytes, offset: int, size: int) -> str:
        if self.is_unicode:
            return buf[offset:offset + size].decode('utf-16-le', errors='replace')
        return buf[offset:offset + size].decode('latin-1', errors='replace')

    def on_new_library(self, libpath: str, is_full_path: bool):
        if not is_full_path:
            libpath = os.path.join(self._dir, libpath)
        if not os.path.normcase(self._file_path) == os.path.normcase(libpath) and os.path.exists(libpath):
            self.files.append(PbFile(self, libpath))

    def on_system_library(self, version: int):
        if self.version == 0:
            self.version = version
            self._load_system_types(version)
        elif self.version != version:
            raise Exception("two version library in one project??")

    def _load_system_types(self, version: int):
        res_path = os.path.join(RESOURCE_DIR, f"{version:04x}.bin")
        if not os.path.exists(res_path):
            print(f"Warning: system type resource not found: {res_path}", file=sys.stderr)
            return
        with open(res_path, 'rb') as f:
            entry_data = gzip.decompress(f.read())
        # Create a dummy PbFile for system types
        sys_file = PbFile.__new__(PbFile)
        sys_file.project = self
        sys_file.file_path = res_path
        sys_file.file_name = "system"
        sys_file.entries = []
        sys_entry = PbEntry(sys_file, "_typedef.grp", entry_data)
        sys_file.entries.append(sys_entry)

    def on_new_enum_item(self, pb_type: PbType, index: int, item_name: str):
        if pb_type.index not in self.enums:
            self.enums[pb_type.index] = PbEnum()
            self.enums[pb_type.index].index = pb_type.index
            self.enums[pb_type.index].name = pb_type.name
        self.enums[pb_type.index].items[index] = item_name + "!"


# ==================== PCode Parser ====================

class StackObject:
    def __init__(self, s: str, t: PbType = None):
        self.str = s
        self.type = t
        self.operator = None
    def __str__(self): return self.str


class CodeLine:
    def __init__(self):
        self.pcode_position = 0
        self.debug_line = None
        self.pcode_op = 0
        self.pcode_param = b''
        self.scode = ""
        self.jmp_position = 0
        self.jmp_type = 0  # 0=None, 1=Jmp, 2=JmpIfTrue, 3=JmpIfFalse
        self.condition = ""
        self.pre_code_line: Optional['CodeLine'] = None
        self.next_code_line: Optional['CodeLine'] = None
        self.label_scode: List[str] = []

    def to_output(self) -> str:
        lines = []
        for ls in self.label_scode:
            if ls and ls.strip(): lines.append(ls)
        if self.scode and self.scode.strip():
            lines.append(self.scode)
        return "\n".join(lines)


class CodeArea:
    def __init__(self):
        self.type = ""
        self.start = 0
        self.end = 0

# Jmp type constants
JMP_NONE = 0
JMP_JMP = 1
JMP_IF_TRUE = 2
JMP_IF_FALSE = 3

def _op_level(op):
    if op in ('+', '-'): return 5
    if op in ('*', '/'): return 4
    if op == '^': return 3
    if op in ('and', 'or'): return 2
    if op in ('=', '<>', '>', '<', '>=', '<='): return 1
    if op in ('$not', '$-'): return 6
    return 0


class PCodeParserBase:
    def __init__(self, pf: PbFunction):
        self.pf = pf
        self._stack: List[StackObject] = []
        self._cl: Optional[CodeLine] = None

    def get_pcode_len_array(self) -> List[int]:
        raise NotImplementedError

    def get_pcode_len(self, pcode: int) -> int:
        arr = self.get_pcode_len_array()
        if pcode < len(arr): return arr[pcode]
        return 255

    def parse_pcode(self, cl: CodeLine):
        self._cl = cl
        cl.scode = ""
        if not self._on_parse(cl.pcode_op, cl):
            cl.scode = f"-------{cl.pcode_op:04X}"

    def _on_parse(self, op: int, cl: CodeLine) -> bool:
        raise NotImplementedError

    # Stack operations
    def _push(self, s: str, t: PbType = None):
        self._stack.append(StackObject(s, t))

    def _pop(self) -> StackObject:
        return self._stack.pop()

    def _peek(self) -> StackObject:
        return self._stack[-1]

    def _pop_n(self, n: int) -> List[StackObject]:
        result = [None] * n
        for i in range(n):
            result[n - 1 - i] = self._pop()
        return result

    def _push_var(self, v: PbVariable):
        self._push(v.name, v.type)

    # Variable operations
    def _begin_assign_local(self, idx): self._push_var(self.pf.variables[idx])
    def _begin_assign_shared(self, idx): self._push_var(self.pf.entry.variables[idx])
    def _begin_assign_global(self, idx):
        v = next(v for v in self.pf.variables if v.global_index == idx)
        self._push_var(v)

    def _begin_assign_instance(self):
        s1 = self._pop(); s2 = self._pop()
        if s2.str == "entryobject":
            self._push(s1.str, s1.type)
        else:
            self._push(f"{s2.str}.{s1.str}", s1.type)

    def _end_assign(self, is_array=False):
        val = self._pop(); target = self._pop()
        self._cl.scode = f"{target.str}[] = {val.str}" if is_array else f"{target.str} = {val.str}"

    def _end_assign_op(self, op: str):
        val = self._pop(); target = self._pop()
        self._cl.scode = f"{target.str} {op}= {val.str}"

    def _end_assign2(self, op: str):
        target = self._pop()
        self._cl.scode = f"{target.str} {op}"

    def _reset_assign(self, count):
        item = self._pop(); item2 = self._peek()
        self._stack.append(item2); self._stack.append(item)

    def _push_local(self, idx): self._push_var(self.pf.variables[idx])
    def _push_shared(self, idx): self._push_var(self.pf.entry.variables[idx])
    def _push_global_shared(self, idx):
        v = next((v for v in self.pf.entry.variables if v.global_index == idx), None)
        if v: self._push_var(v)
    def _push_global(self, idx):
        v = next(v for v in self.pf.variables if v.global_index == idx)
        self._push_var(v)

    def _push_instance_var(self, unk=0):
        s1 = self._pop(); s2 = self._pop()
        if s2.str == "entryobject":
            self._push(s1.str, s1.type)
        else:
            self._push(f"{s2.str}.{s1.str}", s1.type)

    def _push_instance_var_name(self, offset):
        if 1 <= offset <= 7:
            self._push("entryobject", self.pf.entry.entry_object.type)
            return
        u = get_uint(self.pf.buffer, offset)
        t = self._peek().type
        pv = None
        if t is not None:
            obj = t.get_object(self.pf.entry)
            if obj is not None:
                idx = get_ushort(self.pf.buffer, offset + 4)
                if idx < len(obj.all_variables):
                    pv = obj.all_variables[idx]
        if pv is None:
            text = f"{get_ushort(self.pf.buffer, offset + 4):04X}" if (u & 0xFFFF) == 65535 else get_string(self.pf.project.is_unicode, self.pf.buffer, u)
        elif (u & 0xFFFF) != 65535:
            text = get_string(self.pf.project.is_unicode, self.pf.buffer, u)
        else:
            text = pv.name
        self._push(text, pv.type if pv else None)

    def _push_this(self): self._push("this", self.pf.object.type)
    def _push_parent(self): self._push("parent", self.pf.object.parent_object.type if self.pf.object.parent_object else None)

    def _push_enum(self, enum_idx, item_idx):
        self._push(self.pf.project.enums[enum_idx].items[item_idx], PbType.get_pb_type(self.pf.entry, enum_idx))

    def _push_constant(self, c): self._push(c)

    def _operate(self, op):
        level = _op_level(op)
        right = self._pop()
        if _op_level(right.operator) >= level: right.str = f"({right.str})"
        left = self._pop()
        if _op_level(left.operator) > level: left.str = f"({left.str})"
        so = StackObject(f"{left.str} {op} {right.str}")
        so.operator = op
        self._stack.append(so)

    def _operate_single(self, op):
        s = self._pop()
        if _op_level(s.operator) > 0: s.str = f"({s.str})"
        so = StackObject(f"{op} {s.str}")
        so.operator = "$" + op
        self._stack.append(so)

    def _return(self, p1=0):
        self._cl.scode = f"return {self._pop().str}" if p1 == 1 else "return"

    def _halt(self, force):
        self._cl.scode = "halt close" if force == 0 else "halt"

    def _jump(self, pos, jmp_type):
        self._cl.jmp_type = jmp_type; self._cl.jmp_position = pos
        if jmp_type == JMP_JMP:
            self._cl.scode = f"goto {pos:04X}"
        elif jmp_type == JMP_IF_TRUE:
            self._cl.condition = self._pop().str
            self._cl.scode = f"if {self._cl.condition} then goto {pos:04X}"
        elif jmp_type == JMP_IF_FALSE:
            self._cl.condition = self._pop().str
            self._cl.scode = f"if {self._cl.condition} then not goto {pos:04X}"

    def _try(self, cp, ep): self._cl.scode = "try "
    def _end_try(self): self._cl.scode = "end try "
    def _catch(self):
        s = self._pop()
        self._push(f"catch ({s.type.name} {s.str})" if s.type else f"catch ({s.str})")
    def _throw(self): self._cl.scode = f"throw {self._pop()}"
    def _enter_finally(self, pos): self._cl.scode = "enter finally "; self._cl.jmp_position = pos
    def _leave_finally(self): pass
    def _cast(self, pos=0): pass

    def _create_object(self, offset):
        u = get_uint(self.pf.buffer, offset)
        idx = get_ushort(self.pf.buffer, offset + 4)
        t = PbType.get_pb_type(self.pf.entry, idx)
        self._push(f"create {t.name}", t)

    def _create_using(self, idx):
        self._push(f"create using {self._pop()}", PbType.get_pb_type(self.pf.entry, 8))

    def _destroy(self): self._cl.scode = f"destroy({self._pop().str})"
    def _pop_function(self): self._cl.scode = f"{self._pop().str}"

    def _push_global_func_name(self, obj_idx, func_idx):
        name = None
        if (obj_idx & 0x8000) == 0x8000:
            name = self.pf.object.referenced_functions[func_idx].name
        elif (obj_idx & 0x4000) == 0x4000:
            se = self.pf.project.system_entry
            if se and obj_idx in se.objects:
                fd = se.objects[obj_idx].function_definitions[func_idx]
                name = fd.name if fd else f"({obj_idx:04X}{func_idx:04X})"
            else:
                name = f"({obj_idx:04X}{func_idx:04X})"
        self._push(name or "")

    def _call_global(self, count, call_type):
        text = self._pop().str
        args = self._pop_n(count)
        if call_type & 1: text = "post " + text
        if call_type & 2: text = "dynamic " + text
        if call_type & 4: text = "event " + text
        self._push(f"{text}({','.join(a.str for a in args)})")

    def _call_super(self, func_idx, param_count, obj_type, name_offset):
        for _ in range(param_count): self._pop()
        self._push("call super::" + get_string(self.pf.project.is_unicode, self.pf.buffer, name_offset))

    def _call_function(self, offset, count, call_type):
        u = get_ushort(self.pf.buffer, offset)
        pb_type = PbType.get_pb_type(self.pf.entry, get_ushort(self.pf.buffer, offset + 2))
        name_offset = get_uint(self.pf.buffer, offset + 4)
        if (name_offset & 0xFFFF) == 65535:
            raise Exception("CallFunction funnameoffset==0xFFFF")
        args = self._pop_n(count)
        target = self._pop()
        text = get_string(self.pf.project.is_unicode, self.pf.buffer, name_offset)
        fd = None
        if u != 0xFFFF and target.type and target.type.name != "any":
            obj = target.type.get_object(self.pf.entry)
            if obj and u < len(obj.all_function_definitions):
                fd = obj.all_function_definitions[u]
                if fd and fd.name and fd.name.lower() != (text or "").lower():
                    fd = None
        if call_type & 1: text = "post " + text
        if call_type & 2: text = "dynamic " + text
        if call_type & 4: text = "event " + text
        prefix = "super::" if (target.str == "this" and pb_type.name) else f"{target.str}."
        result = f"{prefix}{text}({','.join(a.str for a in args)})"
        ret_type = target.type if (target.type and target.type.name == "any") else (fd.return_type if fd else None)
        self._push(result, ret_type)

    def _call_builtin(self, func, paramcount=1):
        args = self._pop_n(paramcount)
        self._push(f"{func}({','.join(a.str for a in args)})")

    def _create_array(self, length):
        args = self._pop_n(length)
        self._push("{" + ",".join(a.str for a in args) + "}")

    def _index(self):
        idx = self._pop(); arr = self._pop()
        self._push(f"{arr.str}[{idx.str}]", arr.type)

    def _index2(self, p1, p2): self._index()

    def _index3(self, p1, p2, p3):
        self._pop_n(2)
        self._index()

    # SQL operations
    def _sql_transaction(self, func): self._cl.scode = f"{func} using {self._pop()};"
    def _sql_open(self, pc):
        args = self._pop_n(pc); sqlca = self._pop(); cursor = self._pop()
        v = next((v for v in self.pf.variables if v.name == cursor.str), None)
        if v: v.set_cursor_params([a.str for a in args], sqlca.str)
        self._cl.scode = f"open {cursor};"
    def _sql_open_dynamic(self, co, pc):
        sqlca = self._pop(); cursor = self._pop(); args = self._pop_n(pc)
        v = next((v for v in self.pf.variables if v.name == cursor.str), None)
        if v: v.set_dynamic_cursor_params(sqlca.str)
        u = f"using {','.join(':' + str(a) for a in args)}" if pc > 0 else ""
        self._cl.scode = f"open dynamic {cursor} {u};"
    def _sql_execute(self, pc):
        args = self._pop_n(pc); sqlca = self._pop(); proc = self._pop()
        v = next((v for v in self.pf.variables if v.name == proc.str), None)
        if v: v.set_procedure_params([a.str for a in args], sqlca.str)
        self._cl.scode = f"execute {proc};"
    def _sql_execute_dynamic(self, po, pc):
        sqlca = self._pop(); cursor = self._pop(); args = self._pop_n(pc)
        v = next((v for v in self.pf.variables if v.name == cursor.str), None)
        if v: v.set_dynamic_procedure_params(sqlca.str)
        u = f"using {','.join(':' + str(a) for a in args)}" if pc > 0 else ""
        self._cl.scode = f"execute dynamic {cursor} {u};"
    def _sql_fetch(self, pc):
        self._pop(); cursor = self._pop(); args = self._pop_n(pc)
        self._cl.scode = f"fetch {cursor.str} into {','.join(':' + a.str for a in args)};"
    def _sql_close(self):
        self._pop(); c = self._pop()
        self._cl.scode = f"close {c.str};"
    def _sql_prepare(self):
        sqlca = self._pop(); sql = self._pop().str
        if not sql.startswith('"'): sql = ":" + sql
        sqlsa = self._pop()
        self._cl.scode = f"prepare {sqlsa} from {sql} using {sqlca};"
    def _sql_execute_sqlsa(self, pc):
        args = self._pop_n(pc); sqlsa = self._pop()
        self._cl.scode = f"execute {sqlsa} using {','.join(':' + str(a) for a in args)};"
    def _sql_execute_immediate(self):
        sqlca = self._pop(); sql = self._pop().str
        if not sql.startswith('"'): sql = ":" + sql
        self._cl.scode = f"execute immediate {sql} using {sqlca};"
    def _sql_describe(self):
        desc = self._pop(); sqlsa = self._pop()
        self._cl.scode = f"describe {sqlsa} into {desc};"
    def _sql_open_dynamic_desc(self, co):
        sqlca = self._pop(); cursor = self._pop(); desc = self._pop()
        v = next((v for v in self.pf.variables if v.name == cursor.str), None)
        if v: v.set_dynamic_cursor_params(sqlca.str)
        self._cl.scode = f"open dynamic {cursor} using descriptor {desc};"
    def _sql_execute_dynamic_desc(self, po):
        sqlca = self._pop(); cursor = self._pop(); desc = self._pop()
        v = next((v for v in self.pf.variables if v.name == cursor.str), None)
        if v: v.set_dynamic_cursor_params(sqlca.str)
        self._cl.scode = f"execute dynamic {cursor} using descriptor {desc};"
    def _sql_fetch_dynamic_desc(self):
        self._pop(); cursor = self._pop(); desc = self._pop()
        self._cl.scode = f"fetch {cursor} using descriptor {desc};"
    def _sql_direct_iud(self, co, pc):
        sqlca = self._pop(); args = self._pop_n(pc)
        cursor = get_cursor(self.pf.project.is_unicode, self.pf.entry.variable_buffer, co, [a.str for a in args])
        self._cl.scode = f"{cursor} using {sqlca};"
    def _sql_direct_select(self, co, pc1, pc2):
        sqlca = self._pop(); args1 = self._pop_n(pc1); args2 = self._pop_n(pc2)
        cursor = get_cursor(self.pf.project.is_unicode, self.pf.entry.variable_buffer, co, [a.str for a in args1])
        cursor = re.sub(r' from ', f" into {','.join(':' + str(a) for a in args2)} from ", cursor, count=1, flags=re.IGNORECASE)
        self._cl.scode = f"{cursor} using {sqlca};"


# ==================== PCode Parser 90 ====================

PCODE_LEN_90 = [
    2,1,1,1,0,0,0,0,0,1,3,3,1,3,3,4,0,1,5,0,3,0,3,3,0,4,3,1,1,2,0,0,
    0,0,0,0,1,0,3,2,3,4,2,3,1,1,1,1,1,2,2,2,2,2,2,2,2,1,2,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,
    1,2,1,0,0,0,0,0,0,0,2,0,2,2,2,2,0,0,0,0,0,0,0,0,0,0,2,0,2,2,2,2,
    0,0,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,
    0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,2,2,2,2,2,2,2,2,2,2,2,2,2,
    2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,0,0,0,1,1,1,1,1,1,
    0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1,
    0,0,0,0,3,3,2,2,3,3,4,4,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,2,2,1,1,2,3,2,3,4,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,1,1,0,1,1,1,0,0,1,0,0,0,1,
    0,0,0,1,1,0,1,1,1,1,1,5,1,4,1,0,2,3,3,5,3,5,1,4,1,1,2,2,2,3,3,3,
    3,0,3,0,2,2,2,3,1,1,4,3,1,1,1,0,0,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,2,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,2,
    1,1,1,1,1,1,1,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,3,2,3,4,3,1,1,0,
    1,1,0
]

PCODE_LEN_100 = [
    2,1,1,1,0,0,0,0,0,1,3,3,1,3,3,4,0,1,5,0,3,0,3,3,0,4,3,5,4,1,1,2,
    0,0,0,0,0,0,1,0,3,2,3,4,2,3,1,1,1,1,1,2,2,2,2,2,2,2,2,1,2,1,1,1,
    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
    1,2,1,2,1,0,0,0,0,0,0,0,2,0,2,2,2,2,0,0,0,0,0,0,0,0,0,0,2,0,2,2,
    2,2,0,0,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,
    0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,2,2,2,2,2,2,2,2,2,2,2,
    2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,0,0,0,1,1,1,1,
    1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,
    1,1,0,0,0,0,3,3,2,2,3,3,4,4,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,2,2,1,1,2,3,2,3,4,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,1,0,0,0,0,0,1,2,0,0,0,0,0,0,1,1,1,1,0,1,1,1,0,0,1,0,0,
    0,1,0,0,0,1,1,0,1,1,1,1,1,5,1,4,1,0,2,3,3,5,3,5,1,4,2,2,2,2,2,3,
    3,3,3,0,3,0,2,2,2,3,1,1,4,3,1,1,1,0,0,2,1,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,2,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,
    0,2,1,1,1,1,1,1,1,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,3,2,3,4,3,1,
    1,0,1,1,0
]

PCODE_LEN_105 = [
    0,1,1,1,1,0,0,0,0,0,1,3,3,1,3,3,4,0,1,5,0,3,0,3,3,0,4,3,5,4,1,1,
    2,0,0,0,0,0,0,1,0,3,2,3,4,2,3,1,1,1,1,1,2,2,2,2,2,2,2,2,1,2,1,1,
    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
    1,1,1,2,1,2,1,0,0,0,0,0,0,0,2,0,2,2,2,2,0,0,0,0,0,0,0,0,0,0,2,0,
    2,2,2,2,0,0,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,0,
    0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,2,2,2,2,2,2,2,2,2,
    2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,0,0,0,1,1,
    1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
    0,0,1,1,0,0,0,0,3,3,2,2,3,3,4,4,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,2,2,1,1,2,3,2,3,4,1,1,1,1,1,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,1,0,0,0,0,0,1,2,0,0,0,0,0,0,1,1,1,1,0,1,1,1,0,0,1,
    0,0,0,1,0,0,0,1,1,0,1,1,1,1,1,5,1,4,1,0,2,3,3,5,3,5,1,4,2,2,2,2,
    2,3,3,3,3,0,3,0,2,2,2,3,1,1,4,3,1,1,1,0,0,2,1,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,2,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,
    0,0,0,2,1,1,1,1,1,1,1,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,3,2,3,4,
    3,1,1,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,2,
    2,1,2,2,2,0,0,0,0,0,0
]

PCODE_LEN_110 = [
    0,1,1,1,1,0,0,0,0,0,1,3,3,1,3,3,4,0,1,5,0,3,0,3,3,0,4,3,5,4,1,1,
    2,0,0,0,0,0,0,1,0,3,2,3,4,2,3,1,1,1,1,1,2,2,2,2,2,2,2,2,1,2,1,1,
    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
    1,1,1,2,1,2,1,0,0,0,0,0,0,0,2,0,2,2,2,2,0,0,0,0,0,0,0,0,0,0,2,0,
    2,2,2,2,0,0,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,0,
    0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,0,2,2,2,2,2,2,2,2,2,
    2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,0,0,0,1,1,
    1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
    0,0,1,1,0,0,0,0,3,3,2,2,3,3,4,4,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,2,2,1,1,2,3,2,3,4,1,1,1,1,1,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,1,0,0,0,0,0,1,2,0,0,0,0,0,0,1,1,1,1,0,1,1,0,0,1,0,
    0,0,0,0,0,1,0,1,1,1,1,1,5,1,4,1,0,2,3,3,5,3,5,1,4,2,2,2,2,2,3,3,
    3,3,0,3,0,2,2,2,3,1,1,4,3,1,1,1,0,0,2,1,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,2,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,
    2,1,1,1,1,1,1,1,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,3,2,3,4,3,1,1,
    0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,2,2,1,2,
    2,2,0,0,0,0,0,0
]


# I'll use a dispatch table approach instead of the massive switch.
# The PCodeParser90 _on_parse is loaded from the C# switch verbatim but using a dict.

# Due to the sheer size, I'll implement it with the same range-based logic as C#

class PCodeParser90(PCodeParserBase):
    def get_pcode_len_array(self): return PCODE_LEN_90

    def get_pcode_len(self, pcode):
        if self.pf.project.version < 193 and pcode == 297: return 0
        return super().get_pcode_len(pcode)

    def _on_parse(self, op, cl):
        p = cl.pcode_param
        if op == 0: self._return(get_ushort(p, 0))
        elif op == 1: self._jump(get_ushort(p, 0), JMP_IF_TRUE)
        elif op == 2: self._jump(get_ushort(p, 0), JMP_IF_FALSE)
        elif op == 3: self._jump(get_ushort(p, 0), JMP_JMP)
        elif op == 4: self._sql_transaction("connect")
        elif op == 5: self._sql_transaction("commit")
        elif op == 6: self._sql_transaction("rollback")
        elif op == 7: self._sql_transaction("disconnect")
        elif op == 8: self._sql_close()
        elif op == 9: self._sql_open(get_ushort(p, 0))
        elif op in (10, 11): self._sql_direct_iud(get_uint(p, 0), get_ushort(p, 4))
        elif op == 12: self._sql_execute(get_ushort(p, 0))
        elif op == 13: self._sql_fetch(get_ushort(p, 4))
        elif op == 14: self._sql_direct_iud(get_uint(p, 0), get_ushort(p, 4))
        elif op == 15: self._sql_direct_select(get_uint(p, 0), get_ushort(p, 4), get_ushort(p, 6))
        elif op == 16: self._destroy()
        elif op == 17: self._halt(get_ushort(p, 0))
        elif op == 18: self._call_super(get_ushort(p, 0), get_ushort(p, 2), get_ushort(p, 4), get_uint(p, 6))
        elif op == 19: self._pop_function()
        elif op == 20: self._sql_execute_sqlsa(get_ushort(p, 4))
        elif op == 21: self._sql_prepare()
        elif op == 22: self._sql_open_dynamic(get_uint(p, 0), get_ushort(p, 4))
        elif op == 23: self._sql_execute_dynamic(get_uint(p, 0), get_ushort(p, 4))
        elif op == 24: self._sql_describe()
        elif op == 25: self._sql_direct_select(get_uint(p, 0), get_ushort(p, 4), get_ushort(p, 6))
        elif op == 26: self._sql_direct_iud(get_uint(p, 0), get_ushort(p, 4) + 1)
        elif op == 27: self._push_local(get_ushort(p, 0))
        elif op == 28: self._push_shared(get_ushort(p, 0))
        elif op == 29: self._push_instance_var_name(get_ushort(p, 0))
        elif op == 30: self._push_this()
        elif op == 31: self._push_parent()
        elif op == 33: self._operate("and")
        elif op == 34: self._operate("or")
        elif op == 35: self._operate_single("not")
        elif op == 36: self._push_instance_var(get_ushort(p, 0))
        elif op in (37, 317, 449): pass  # nop
        elif op == 41: self._call_function(get_uint(p, 0), get_ushort(p, 4), get_ushort(p, 6))
        elif op == 42: self._create_object(get_uint(p, 0))
        elif op == 44: self._push_global(get_ushort(p, 0))
        elif op == 45: self._push_local(get_ushort(p, 0))
        elif op == 46: self._push_global_shared(get_ushort(p, 0))
        elif op == 47: self._push_constant(str(struct.unpack('<h', p[:2])[0]))
        elif op == 48: self._push_constant(str(get_ushort(p, 0)))
        elif op == 49: self._push_constant(str(struct.unpack('<i', p[:4])[0]))
        elif op == 50: self._push_constant(str(get_uint(p, 0)))
        elif op == 51: self._push_constant(get_decimal(self.pf.buffer, get_uint(p, 0)))
        elif op == 52: self._push_constant(get_real(get_uint(p, 0)))
        elif op == 53: self._push_constant(get_double(self.pf.buffer, get_uint(p, 0)))
        elif op == 54: self._push_constant(get_time(self.pf.buffer, get_uint(p, 0)))
        elif op == 55: self._push_constant(get_date(self.pf.buffer, get_uint(p, 0)))
        elif op == 56: self._push_constant(get_escape_string(self.pf.project.is_unicode, self.pf.buffer, get_uint(p, 0)))
        elif op == 57: self._push_constant(str(get_ushort(p, 0) == 1).lower())
        elif op == 58: self._push_enum(get_ushort(p, 2), get_ushort(p, 0))
        elif 59 <= op <= 79: self._cast(get_ushort(p, 0))
        elif 80 <= op <= 86: self._operate("+")
        elif 87 <= op <= 93: self._operate("-")
        elif 94 <= op <= 100: self._operate("*")
        elif 101 <= op <= 107: self._operate("/")
        elif 108 <= op <= 114: self._operate("^")
        elif 115 <= op <= 121: self._operate_single("-")
        elif op in (122, 123): self._operate("+")
        elif op == 124: self._end_assign(True)
        elif 125 <= op <= 137: self._end_assign()
        elif 138 <= op <= 162: self._cast(get_ushort(p, 0))
        elif 163 <= op <= 178: self._operate("=")
        elif 179 <= op <= 194: self._operate("<>")
        elif 195 <= op <= 206: self._operate(">")
        elif 207 <= op <= 218: self._operate("<")
        elif 219 <= op <= 230: self._operate(">=")
        elif 231 <= op <= 242: self._operate("<=")
        elif 243 <= op <= 249: self._end_assign2("++")
        elif 250 <= op <= 256: self._end_assign2("--")
        elif 257 <= op <= 263: self._end_assign_op("+")
        elif 264 <= op <= 270: self._end_assign_op("-")
        elif 271 <= op <= 277: self._end_assign_op("*")
        elif op == 278: self._reset_assign(get_ushort(p, 0))
        elif op == 282: self._begin_assign_local(get_ushort(p, 0))
        elif op == 283: self._begin_assign_shared(get_ushort(p, 0))
        elif op == 284: self._begin_assign_global(get_ushort(p, 0))
        elif op == 285: self._begin_assign_local(get_ushort(p, 0))
        elif op == 287: self._begin_assign_instance()
        elif 288 <= op <= 296: self._cast(0)
        elif 298 <= op <= 315: self._cast(get_ushort(p, 0))
        elif op in (318, 319): self._push_instance_var(get_ushort(p, 0))
        elif 320 <= op <= 323: self._cast(0)
        elif op in (330, 331): self._call_function(get_uint(p, 0), get_ushort(p, 4), get_ushort(p, 6))
        elif op in (332, 333): self._push_local(get_ushort(p, 0))
        elif op in (334, 335): self._push_shared(get_ushort(p, 0))
        elif op in (336, 337): self._push_global(get_ushort(p, 0))
        elif op == 342: self._end_assign()
        elif 343 <= op <= 361: self._cast(get_ushort(p, 0))
        elif op == 362: self._create_object(get_uint(p, 0))
        elif op == 366: self._call_function(get_uint(p, 0), get_ushort(p, 4), get_ushort(p, 6))
        elif op == 367: self._push_local(get_ushort(p, 0))
        elif op == 368: self._push_shared(get_ushort(p, 0))
        elif op == 369: self._push_global(get_ushort(p, 0))
        elif op == 372: self._operate("+")
        elif op == 373: self._operate("-")
        elif op == 374: self._operate("*")
        elif op == 375: self._operate("/")
        elif op == 376: self._operate("^")
        elif op == 377: self._operate_single("-")
        elif op == 378: self._operate("=")
        elif op == 379: self._operate("<>")
        elif op == 380: self._operate(">")
        elif op == 381: self._operate("<")
        elif op == 382: self._operate(">=")
        elif op == 383: self._operate("<=")
        elif op == 384: self._operate("and")
        elif op == 385: self._operate("or")
        elif op == 386: self._operate_single("not")
        elif op == 387: self._push_instance_var(get_ushort(p, 0))
        elif op in (388, 389): self._cast(0)
        elif op == 390: self._call_builtin("int")
        elif op in (391, 392): self._call_builtin("abs")
        elif op == 393: self._call_builtin("asc")
        elif op == 394: self._call_builtin("blob")
        elif op == 395: self._call_builtin("ceiling")
        elif op == 396: self._call_builtin("cos")
        elif op == 397: self._call_builtin("exp")
        elif op == 398: self._call_builtin("fact")
        elif op == 399: self._call_builtin("inthigh")
        elif op == 400: self._call_builtin("intlow")
        elif op == 401: self._call_builtin("isdate")
        elif op == 402: self._call_builtin("isnull")
        elif op == 403: self._call_builtin("isnumber")
        elif op == 404: self._call_builtin("istime")
        elif op == 405: self._call_builtin("isvalid")
        elif op == 406: self._call_builtin("lefttrim")
        elif op in (407, 408): self._call_builtin("len")
        elif op == 409: self._call_builtin("log")
        elif op == 410: self._call_builtin("logten")
        elif op == 411: self._call_builtin("lower")
        elif op == 412: self._call_builtin("pi")
        elif op == 413: self._call_builtin("rand")
        elif op == 415: self._call_builtin("righttrim")
        elif op == 416: self._call_builtin("sin")
        elif op == 417: self._call_builtin("sqrt")
        elif op == 418: self._call_builtin("tan")
        elif op == 419: self._call_builtin("trim")
        elif op == 420: self._call_builtin("upper")
        elif op == 422: self._push_global(get_ushort(p, 0))
        elif op == 425: self._push_local(get_ushort(p, 0))
        elif op == 426: self._push_shared(get_ushort(p, 0))
        elif op == 427: self._cast(0)
        elif op == 430: self._cast(get_ushort(p, 0))
        elif op == 431: self._index()
        elif op == 432: self._index2(get_ushort(p, 0), get_ushort(p, 2))
        elif op == 433: self._index3(get_ushort(p, 0), get_ushort(p, 2), get_ushort(p, 4))
        elif op in (434, 435): self._create_array(get_ushort(p, 4))
        elif op == 438: self._cast(get_ushort(p, 0))
        elif op == 440: self._call_builtin("lowerbound")
        elif op == 441: self._call_builtin("upperbound")
        elif op == 442: self._end_assign2("++")
        elif op == 443: self._end_assign2("--")
        elif op == 444: self._push_global_func_name(get_ushort(p, 2), get_ushort(p, 0))
        elif 445 <= op <= 448: self._call_global(get_ushort(p, 2), get_ushort(p, 4))
        elif op == 451: self._sql_execute_immediate()
        elif op == 452: self._sql_execute_dynamic_desc(get_uint(p, 0))
        elif op == 453: self._sql_fetch_dynamic_desc()
        elif op == 454: self._sql_open_dynamic_desc(get_uint(p, 0))
        elif op == 456: self._create_using(get_ushort(p, 0))
        elif op in (457, 459, 461, 462): self._cast(get_ushort(p, 0))
        elif op == 463: self._cast(0)
        elif op == 464: self._push_instance_var(0)
        elif op == 466: self._push_instance_var_name(get_ushort(p, 0))
        elif 467 <= op <= 471: self._call_builtin("mod", 2)
        elif op in (472, 473): self._call_builtin("abs")
        elif op == 474: self._call_builtin("ceiling")
        elif 475 <= op <= 479: self._call_builtin("min", 2)
        elif 480 <= op <= 484: self._call_builtin("max", 2)
        elif op == 485: self._try(get_ushort(p, 0), get_ushort(p, 2))
        elif op == 486: self._end_try()
        elif op == 487: self._catch()
        elif op == 488: self._throw()
        elif op == 489: self._enter_finally(get_ushort(p, 0))
        elif op == 490: self._leave_finally()
        elif 491 <= op <= 504: self._cast(get_ushort(p, 0))
        elif op == 505: self._operate("+")
        elif op == 506: self._operate("-")
        elif op == 507: self._operate("*")
        elif op == 508: self._operate("/")
        elif op == 509: self._operate("^")
        elif op == 510: self._operate_single("-")
        elif op == 511: self._push_constant(get_longlong(self.pf.buffer, get_uint(p, 0)))
        elif op == 512: self._push_local(get_ushort(p, 0))
        elif op == 513: self._push_global(get_ushort(p, 0))
        elif op == 515: self._push_shared(get_ushort(p, 0))
        elif op == 517: self._end_assign()
        elif op == 519: self._end_assign_op("+")
        elif op == 520: self._end_assign_op("-")
        elif op == 521: self._end_assign_op("*")
        elif op == 522: self._end_assign2("++")
        elif op == 523: self._end_assign2("--")
        elif op == 524: self._cast(get_ushort(p, 0))
        elif op == 525: self._call_builtin("abs")
        elif op == 527: self._operate("=")
        elif op == 528: self._operate("<>")
        elif op == 529: self._operate(">")
        elif op == 530: self._operate("<")
        elif op == 531: self._operate(">=")
        elif op == 532: self._operate("<=")
        elif op == 533: self._call_builtin("mod", 2)
        elif op == 534: self._call_builtin("min", 2)
        elif op == 535: self._call_builtin("max", 2)
        elif op == 539: self._call_function(get_uint(p, 0), get_ushort(p, 4), get_ushort(p, 6))
        elif op == 540: self._call_global(get_ushort(p, 2), get_ushort(p, 4))
        elif op == 542: self._push_instance_var(get_ushort(p, 0))
        elif op == 543: self._cast(0)
        elif op == 544: self._cast(get_ushort(p, 0))
        elif op == 546: self._cast(0)
        else: return False
        return True


class PCodeParser100(PCodeParser90):
    def get_pcode_len_array(self): return PCODE_LEN_100
    def _on_parse(self, op, cl):
        if op <= 26: return super()._on_parse(op, cl)
        if op >= 29: return super()._on_parse(op - 2, cl)
        return False


class PCodeParser105(PCodeParser100):
    def get_pcode_len_array(self): return PCODE_LEN_105
    def _on_parse(self, op, cl):
        if 2 <= op <= 549: return super()._on_parse(op - 1, cl)
        if op == 0: self._return(0); return True
        if op == 1: self._return(get_ushort(cl.pcode_param, 0)); return True
        return False


class PCodeParser110(PCodeParser105):
    def get_pcode_len_array(self): return PCODE_LEN_110
    def _on_parse(self, op, cl):
        if op <= 408: return super()._on_parse(op, cl)
        if op <= 416: return super()._on_parse(op + 1, cl)
        if op <= 419: return super()._on_parse(op + 2, cl)
        return super()._on_parse(op + 3, cl)


def get_parser(pf: PbFunction, version: int) -> Optional[PCodeParserBase]:
    if version in (79, 114, 146, 166, 193, 196): return PCodeParser90(pf)
    if version == 238: return PCodeParser100(pf)
    if version == 283: return PCodeParser105(pf)
    if version in (316, 319, 321, 322, 325, 333, 334): return PCodeParser110(pf)
    return None


# ==================== PCode Control Flow Analysis ====================

def parse_pcode(pf: PbFunction) -> List[str]:
    if not pf.pcode_bytes:
        return []
    parser = get_parser(pf, pf.project.version)
    if parser is None:
        return ["// Unsupported PB version"]

    debug_map = {}
    for i in range(len(pf.debug_bytes) // 4):
        buf = get_buffer(pf.debug_bytes, i * 4, 4)
        debug_map[get_ushort(buf, 2)] = get_ushort(buf, 0)

    code_lines: Dict[int, CodeLine] = {}
    failed = False
    pos = 0
    prev = None
    while pos < len(pf.pcode_bytes):
        opcode = get_ushort(pf.pcode_bytes, pos)
        plen = parser.get_pcode_len(opcode)
        if plen == 255: failed = True; break
        cl = CodeLine()
        cl.pcode_position = pos
        cl.debug_line = debug_map.get(pos)
        cl.pcode_op = opcode
        cl.pcode_param = get_buffer(pf.pcode_bytes, pos + 2, plen * 2)
        if prev: prev.next_code_line = cl; cl.pre_code_line = prev
        prev = cl
        try:
            if not failed: parser.parse_pcode(cl)
        except:
            failed = True
        code_lines[cl.pcode_position] = cl
        pos += 2 + plen * 2

    try: _parse_jmp(pf, code_lines)
    except: pass

    result = []
    for cl in code_lines.values():
        out = cl.to_output()
        for line in out.split('\n'):
            if line.strip():
                result.append(line)
    return result


def _first_valid_pre(cl):
    p = cl.pre_code_line if cl else None
    while p and not (p.scode and p.scode.strip()): p = p.pre_code_line
    return p

def _first_valid_next(cl):
    n = cl.next_code_line if cl else None
    while n and not (n.scode and n.scode.strip()): n = n.next_code_line
    return n

def _parse_jmp(pf, lines):
    areas = []
    if pf.project.version >= 283: _parse_return(lines)
    _parse_try_catch_finally(lines, areas)
    _parse_choose(lines, areas)
    _parse_for_next(lines, areas)
    _parse_do_loop(lines, areas)
    _parse_exit_continue(lines, areas)
    _parse_if_else(lines)
    _parse_event_return(lines)
    _parse_indent(pf, lines)

def _parse_return(lines):
    for cl in lines.values():
        if cl.scode and cl.scode.startswith("return ") and cl.next_code_line and \
           cl.next_code_line.jmp_type == JMP_JMP and cl.next_code_line.jmp_position in lines and \
           lines[cl.next_code_line.jmp_position].scode == "return":
            cl.next_code_line.scode = ""; cl.next_code_line.jmp_type = JMP_NONE

def _parse_try_catch_finally(lines, areas):
    for cl in lines.values():
        if not cl.scode: continue
        if cl.jmp_type == JMP_IF_FALSE and cl.condition and cl.condition.startswith("catch ("):
            cl.scode = cl.condition; cl.jmp_type = JMP_NONE
            if cl.jmp_position in lines:
                t = lines[cl.jmp_position]
                if not t.scode.startswith("end try ") and not t.scode.startswith("enter finally "):
                    if t.pre_code_line and t.pre_code_line.jmp_type == JMP_JMP and t.pre_code_line.jmp_position in lines:
                        tt = lines[t.pre_code_line.jmp_position]
                        if tt.scode.startswith("end try ") or tt.scode.startswith("enter finally "):
                            t.pre_code_line.scode = ""; t.pre_code_line.jmp_type = JMP_NONE
        if cl.jmp_type == JMP_JMP and cl.jmp_position in lines:
            t = lines[cl.jmp_position]
            if t.scode.startswith("end try ") or t.scode.startswith("enter finally "):
                cl.scode = ""; cl.jmp_type = JMP_NONE
        if cl.scode == "enter finally ":
            cl.scode = ""
            if cl.jmp_position in lines:
                lines[cl.jmp_position].label_scode.append("finally ")

def _parse_choose(lines, areas):
    d = {}
    for cl in lines.values():
        if not cl.scode: continue
        if cl.scode.startswith("\x01case"):
            key = cl.scode[:cl.scode.index('=')].strip()
            cl.scode = cl.scode.replace(key + " = ", "choose case ")
            a = CodeArea(); a.type = "choose"; a.start = cl.pcode_position
            d[key] = a
        if cl.jmp_type != JMP_IF_FALSE or cl.jmp_position <= cl.pcode_position: continue
        if not cl.condition or "\x01" not in cl.condition: continue
        found = ""
        for k in d:
            if cl.condition.endswith(k) or (k + " ") in cl.condition: found = k; break
        if not found: continue
        if f" <= {found} and " in cl.condition:
            cl.scode = "case " + cl.condition.replace(f" <= {found} and ", " to ").replace(f" >= {found}", "")
        elif cl.condition.endswith(f" = {found}"):
            cl.scode = "case " + cl.condition.replace(f" = {found}", "")
        elif f" <= {found}" in cl.condition:
            cl.scode = "case is >= " + cl.condition.replace(f" <= {found}", "")
        elif f" >= {found}" in cl.condition:
            cl.scode = "case is <= " + cl.condition.replace(f" >= {found}", "")
        elif f" < {found}" in cl.condition:
            cl.scode = "case is > " + cl.condition.replace(f" < {found}", "")
        elif f" > {found}" in cl.condition:
            cl.scode = "case is < " + cl.condition.replace(f" > {found}", "")
        cl.jmp_type = JMP_NONE
        pre = cl.pre_code_line
        while pre and not pre.scode: pre = pre.pre_code_line
        if pre and pre.scode == "case else ": pre.scode = ""
        if cl.jmp_position in lines and lines[cl.jmp_position].pre_code_line and lines[cl.jmp_position].pre_code_line.jmp_type == JMP_JMP:
            lines[cl.jmp_position].pre_code_line.scode = "case else "
            lines[cl.jmp_position].pre_code_line.jmp_type = JMP_NONE
            if d[found].end == 0 and lines[cl.jmp_position].pre_code_line.jmp_position in lines:
                lines[lines[cl.jmp_position].pre_code_line.jmp_position].label_scode.insert(0, "end choose ")
                d[found].end = lines[lines[cl.jmp_position].pre_code_line.jmp_position].pre_code_line.pcode_position
        elif d[found].end == 0 and cl.jmp_position in lines:
            lines[cl.jmp_position].label_scode.insert(0, "end choose ")
            d[found].end = lines[cl.jmp_position].pre_code_line.pcode_position
    areas.extend(d.values())

def _parse_for_next(lines, areas):
    for cl in lines.values():
        if not cl.scode or cl.jmp_type != JMP_IF_FALSE or cl.jmp_position <= cl.pcode_position: continue
        if cl.jmp_position not in lines: continue
        end = lines[cl.jmp_position]
        if not end.pre_code_line or end.pre_code_line.jmp_type != JMP_JMP: continue
        if end.pre_code_line.jmp_position >= end.pre_code_line.pcode_position or end.pre_code_line.jmp_position >= cl.pcode_position: continue
        if end.pre_code_line.jmp_position not in lines: continue
        loop_start = lines[end.pre_code_line.jmp_position]
        if not loop_start.pre_code_line or loop_start.pre_code_line.jmp_type != JMP_JMP: continue
        parts = [x for x in re.split(r'[><=\s]+', cl.condition) if x]
        if len(parts) > 1:
            pre = cl.pre_code_line
            while pre and not pre.scode: pre = pre.pre_code_line
            step = ""
            if pre and pre.scode and pre.scode.startswith(f"{parts[1]} += "):
                step = "step " + pre.scode[len(f"{parts[1]} += "):]
            if pre: pre.scode = ""
            init = loop_start.pre_code_line.pre_code_line.scode if loop_start.pre_code_line and loop_start.pre_code_line.pre_code_line else ""
            cl.scode = f"for {init} to {parts[0]} {step}"
            cl.jmp_type = JMP_NONE
            if loop_start.pre_code_line.pre_code_line: loop_start.pre_code_line.pre_code_line.scode = ""
            loop_start.pre_code_line.scode = ""; loop_start.pre_code_line.jmp_type = JMP_NONE
            end.pre_code_line.scode = "next "; end.pre_code_line.jmp_type = JMP_NONE
            a = CodeArea(); a.type = "for"; a.start = cl.pcode_position; a.end = end.pre_code_line.pcode_position
            areas.append(a)

def _parse_do_loop(lines, areas):
    for cl in lines.values():
        if not cl.scode: continue
        if cl.jmp_type == JMP_IF_FALSE:
            if cl.jmp_position > cl.pcode_position and cl.jmp_position in lines:
                end = lines[cl.jmp_position]
                if end.pre_code_line and end.pre_code_line.jmp_type == JMP_JMP and end.pre_code_line.jmp_position < end.pre_code_line.pcode_position and end.pre_code_line.jmp_position < cl.pcode_position:
                    cl.scode = f"do while {cl.condition}"; cl.jmp_type = JMP_NONE
                    end.pre_code_line.scode = "loop "; end.pre_code_line.jmp_type = JMP_NONE
                    a = CodeArea(); a.type = "do"; a.start = cl.pcode_position; a.end = end.pre_code_line.pcode_position; areas.append(a)
            elif cl.jmp_position in lines:
                lines[cl.jmp_position].label_scode.append("do ")
                cl.scode = f"loop until {cl.condition}"; cl.jmp_type = JMP_NONE
                a = CodeArea(); a.type = "do"; a.start = lines[cl.jmp_position].pcode_position; a.end = cl.pcode_position; areas.append(a)
        elif cl.jmp_type == JMP_IF_TRUE:
            if cl.jmp_position > cl.pcode_position and cl.jmp_position in lines:
                end = lines[cl.jmp_position]
                if end.pre_code_line and end.pre_code_line.jmp_type == JMP_JMP and end.pre_code_line.jmp_position < end.pre_code_line.pcode_position and end.pre_code_line.jmp_position < cl.pcode_position:
                    cl.scode = f"do until {cl.condition}"; cl.jmp_type = JMP_NONE
                    end.pre_code_line.scode = "loop "; end.pre_code_line.jmp_type = JMP_NONE
                    a = CodeArea(); a.type = "do"; a.start = cl.pcode_position; a.end = end.pre_code_line.pcode_position; areas.append(a)
            elif cl.jmp_position in lines:
                lines[cl.jmp_position].label_scode.append("do ")
                cl.scode = f"loop while {cl.condition}"; cl.jmp_type = JMP_NONE
                a = CodeArea(); a.type = "do"; a.start = lines[cl.jmp_position].pcode_position; a.end = cl.pcode_position; areas.append(a)

def _parse_exit_continue(lines, areas):
    if not areas: return
    for cl in lines.values():
        if not cl.scode or cl.jmp_type != JMP_JMP or cl.jmp_position <= cl.pcode_position: continue
        area = min(areas, key=lambda a: abs(cl.pcode_position - a.start) + abs(a.end - cl.pcode_position))
        if area.start <= cl.pcode_position <= area.end:
            if cl.jmp_position in lines and lines[cl.jmp_position].pre_code_line and lines[cl.jmp_position].pre_code_line.pcode_position == area.end:
                cl.scode = "exit"; cl.jmp_type = JMP_NONE
            elif cl.jmp_position in lines and lines[cl.jmp_position].pcode_position == area.end:
                cl.scode = "continue"; cl.jmp_type = JMP_NONE

def _parse_if_else(lines):
    for cl in lines.values():
        if not cl.scode or cl.jmp_type != JMP_IF_FALSE or cl.jmp_position <= cl.pcode_position: continue
        if cl.jmp_position not in lines: continue
        target = lines[cl.jmp_position]
        if target.pre_code_line and target.pre_code_line.jmp_type == JMP_JMP and target.pre_code_line.jmp_position > target.pre_code_line.pcode_position:
            cl.scode = f"if {cl.condition} then "; cl.jmp_type = JMP_NONE
            if target.pre_code_line.scode in ("exit", "continue"):
                target.pre_code_line.jmp_type = JMP_NONE; target.label_scode.insert(0, "end if ")
            else:
                target.pre_code_line.scode = "else "; target.pre_code_line.jmp_type = JMP_NONE
                if target.pre_code_line.jmp_position in lines:
                    lines[target.pre_code_line.jmp_position].label_scode.insert(0, "end if ")
        else:
            cl.scode = f"if {cl.condition} then"; cl.jmp_type = JMP_NONE
            target.label_scode.insert(0, "end if ")
    # merge elseif
    depth = 0; merge_set = set()
    for cl in lines.values():
        if cl.scode is None: continue
        if cl.scode.strip().startswith("if "):
            depth += 1
            pre = _first_valid_pre(cl)
            if pre and pre.scode == "else ":
                pre.scode += cl.scode; cl.scode = ""; merge_set.add(depth)
        for i in range(len(cl.label_scode)):
            if cl.label_scode[i].strip().startswith("end if"):
                if depth in merge_set: cl.label_scode[i] = ""; merge_set.discard(depth)
                depth -= 1
        if cl.scode.strip().startswith("end if"):
            if depth in merge_set: cl.scode = ""; merge_set.discard(depth)
            depth -= 1

def _parse_event_return(lines):
    for cl in lines.values():
        if not cl.scode or not cl.scode.strip().startswith("if isvalid(::message) then goto "): continue
        n1 = _first_valid_next(cl)
        if not n1 or n1.scode.strip() != "return 0": continue
        n2 = _first_valid_next(n1)
        if not n2 or not n2.scode.strip().startswith("goto "): continue
        n3 = _first_valid_next(n2)
        if n3 and n3.scode.strip() == "return ::message.returnvalue":
            cl.scode = ""; n1.scode = ""; n2.scode = ""; n3.scode = ""

def _parse_indent(pf, lines):
    indent = 0
    for cl in lines.values():
        try:
            for i in range(len(cl.label_scode)):
                cl.label_scode[i], indent = _apply_indent(cl.label_scode[i], indent)
            if cl.scode:
                cl.scode, indent = _apply_indent(cl.scode, indent)
        except: break

def _apply_indent(s, indent):
    pad = "    " * indent
    if s.startswith("try "): s = pad + s; indent += 1
    elif s.startswith("catch "): indent -= 1; s = "    " * indent + s; indent += 1
    elif s.startswith("finally "): indent -= 1; s = "    " * indent + s; indent += 1
    elif s.startswith("end try "): indent -= 1; s = "    " * indent + s
    elif s.startswith("if "): s = pad + s; indent += 1
    elif s.startswith("else "): indent -= 1; s = "    " * indent + s; indent += 1
    elif s.startswith("end if "): indent -= 1; s = "    " * indent + s
    elif s.startswith("for "): s = pad + s; indent += 1
    elif s.startswith("next "): indent -= 1; s = "    " * indent + s
    elif s.startswith("choose case "): s = pad + s; indent += 2
    elif s.startswith("case "): indent -= 1; s = "    " * indent + s; indent += 1
    elif s.startswith("end choose "): indent -= 2; s = "    " * indent + s
    elif s.startswith("do "): s = pad + s; indent += 1
    elif s.startswith("loop "): indent -= 1; s = "    " * indent + s
    elif s.strip(): s = pad + s
    return s, indent


# ==================== CLI Output ====================

def dump_function(f: PbFunction, indent="  ") -> str:
    _out = []
    _out.append(f"\n{indent}//{f.definition}")
    for v in f.variables:
        if any(p.name == v.name for p in f.definition.params): continue
        if v.is_referenced_global or v.name.startswith("\x01"): continue
        _out.append(f"{indent}{v.to_string(f.buffer)}")
    _out.append("")
    for line in parse_pcode(f):
        _out.append(f"{indent}{line}")
    return "\n".join(_out)


def dump_entry(entry: PbEntry) -> str:
    _out = []
    _out.append(f"\n{'=' * 60}")
    _out.append(f"Entry: {entry.entry_name}")
    if entry.modified_time != datetime.min:
        _out.append(f"Modified: {entry.modified_time}  Compiled: {entry.compiled_time}")
    _out.append(f"{'=' * 60}")

    if entry.source:
        _out.append(entry.source)

    if entry.entry_object is None:
        return "\n".join(_out)

    # Shared variables
    shared = [v for v in entry.variables if v.is_shared]
    if shared:
        _out.append("\n-- Shared Variables --")
        for v in shared: print(f"  {v.to_string(entry.variable_buffer)}")

    # Instance variables
    inst = [v for v in entry.entry_object.variables if v.is_instance and v.is_shared]
    if inst:
        _out.append("\n-- Instance Variables --")
        for v in inst: print(f"  {v.to_string(entry.variable_buffer)}")

    # Properties
    props = [v for v in entry.entry_object.variables if not v.is_instance]
    if props:
        _out.append("\n-- Properties --")
        for v in props: print(f"  {v.to_string(entry.variable_buffer)}")

    # External functions
    ext_funcs = [fd for fd in entry.entry_object.function_definitions if fd and fd.is_external]
    if ext_funcs:
        _out.append("\n-- External Functions --")
        for fd in ext_funcs: print(f"  {fd}")

    # Controls
    controls = [o for o in entry.objects.values() if o.parent_object == entry.entry_object]
    if controls:
        _out.append("\n-- Controls --")
        for ctrl in sorted(controls, key=lambda c: c.type.name):
            inh = ctrl.inherit_type.name if ctrl.inherit_type else "?"
            _out.append(f"  {ctrl.type.name} : {inh}")
            if ctrl.variables:
                for v in ctrl.variables:
                    if not v.is_instance:
                        _out.append(f"    {v.to_string(entry.variable_buffer)}")

    # Bind function definitions
    for func in entry.entry_object.functions:
        func.definition = entry.entry_object.function_definitions[func.index]

    # Events
    events = [f for f in entry.entry_object.functions if f.definition.is_event]
    if events:
        _out.append("\n-- Events --")
        for f in events: _out.append(dump_function(f))

    # Functions
    funcs = sorted([f for f in entry.entry_object.functions if not f.definition.is_event and not f.definition.is_external],
                   key=lambda f: f.definition.name)
    if funcs:
        _out.append("\n-- Functions --")
        for f in funcs: _out.append(dump_function(f))

    # Control events/functions
    for ctrl in sorted(controls, key=lambda c: c.type.name):
        if not ctrl.functions: continue
        for f in ctrl.functions:
            f.definition = ctrl.function_definitions[f.index]
        ctrl_events = [f for f in ctrl.functions if f.definition.is_event]
        ctrl_funcs = [f for f in ctrl.functions if not f.definition.is_event and not f.definition.is_external]
        if ctrl_events or ctrl_funcs:
            _out.append(f"\n-- Control: {ctrl.type.name} --")
            for f in ctrl_events: _out.append(dump_function(f))
            for f in sorted(ctrl_funcs, key=lambda f: f.definition.name): dump_function(f)


    return "\n".join(_out)

def print_tree(project: PbProject):
    for f in project.files:
        print(f"\n{f.file_name}")
        by_suffix = {}
        for e in sorted(f.entries, key=lambda e: e.entry_name):
            by_suffix.setdefault(e.suffix, []).append(e)
        for suffix in sorted(by_suffix.keys()):
            entries = by_suffix[suffix]
            label = {
                'apl': 'Applications', 'win': 'Windows', 'men': 'Menus',
                'udo': 'User Objects', 'fun': 'Functions', 'str': 'Structures',
                'dwo': 'DataWindows', 'exe': 'Executables', 'srj': 'Projects',
                'grp': 'System Groups',
            }.get(suffix, suffix.upper())
            print(f"  [{label}]")
            for e in entries:
                extra = ""
                if e.entry_object:
                    inh = e.entry_object.inherit_type
                    if inh and inh.name: extra = f" : {inh.name}"
                    funcs = e.entry_object.functions or []
                    vars_count = len([v for v in (e.entry_object.variables or []) if v.is_instance])
                    ctrls = [o for o in e.objects.values() if o.parent_object == e.entry_object]
                    parts = []
                    if funcs: parts.append(f"{len(funcs)} funcs")
                    if vars_count: parts.append(f"{vars_count} vars")
                    if ctrls: parts.append(f"{len(ctrls)} controls")
                    if parts: extra += f"  ({', '.join(parts)})"
                print(f"    {e.name}{extra}")



# ==================== Library API ====================

@dataclass
class DecompileResult:
    """Structured result of a decompile operation."""
    entry_name: str
    source: str
    success: bool = True
    error: str = None


def decompile_file(file_path: str, entry_name: str = None,
                   decompile_all: bool = True) -> list:
    """
    Decompile entries from a PBD/PBL file.

    Args:
        file_path: Path to .pbd or .pbl file
        entry_name: Specific entry name (None = all)
        decompile_all: If False, return entry list only

    Returns:
        List[DecompileResult]
    """
    results = []
    try:
        project = PbProject(file_path)
    except Exception as e:
        return [DecompileResult(entry_name="", source="", success=False, error=str(e))]

    for pbf in project.files:
        for entry in sorted(pbf.entries, key=lambda e: e.entry_name):
            if entry_name and entry.name.lower() != entry_name.lower()                and entry.entry_name.lower() != entry_name.lower():
                continue
            if not decompile_all:
                results.append(DecompileResult(entry_name=entry.entry_name, source=""))
                continue
            try:
                src = dump_entry(entry)
                results.append(DecompileResult(entry_name=entry.entry_name, source=src))
            except Exception as e:
                results.append(DecompileResult(
                    entry_name=entry.entry_name, source="", success=False, error=str(e)
                ))
    return results


def decompile_bytes(data: bytes, label: str = "<memory>",
                    entry_name: str = None,
                    decompile_all: bool = True) -> list:
    """
    Decompile PBD data from bytes (e.g. extracted from EXE by PEExtractor).

    Args:
        data: Raw PBD bytes
        label: Display label
        entry_name: Specific entry (None = all)
        decompile_all: Decompile all entries

    Returns:
        List[DecompileResult]
    """
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".pbd", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return decompile_file(tmp_path, entry_name=entry_name, decompile_all=decompile_all)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        return [DecompileResult(entry_name=label, source="", success=False, error=str(e))]


def list_entries(file_path: str) -> list:
    """List all entry names in a PBD/PBL file."""
    try:
        project = PbProject(file_path)
        names = []
        for pbf in project.files:
            for e in sorted(pbf.entries, key=lambda e: e.entry_name):
                names.append(e.entry_name)
        return names
    except Exception:
        return []


def get_tree_str(file_path: str) -> str:
    """Return tree view of a PBD/PBL as string."""
    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        project = PbProject(file_path)
        print_tree(project)
    finally:
        sys.stdout = old_out
    return buf.getvalue()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="PbdCli - PowerBuilder PBD/PBL Decompiler")
    ap.add_argument("file", help="PBD/PBL file to decompile")
    ap.add_argument("--list", action="store_true", help="List all entries")
    ap.add_argument("--tree", action="store_true", help="Show PBD structure tree with details")
    ap.add_argument("--entry", help="Decompile a specific entry (e.g. w_cas02_c01)")
    ap.add_argument("--all", action="store_true", help="Decompile all entries")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {args.file}...", file=sys.stderr)
    project = PbProject(args.file)
    print(f"PB Version: {project.version}, Unicode: {project.is_unicode}, PB5: {project.is_pb5}", file=sys.stderr)

    if args.list:
        for f in project.files:
            print(f"\n{f.file_name}:")
            for e in sorted(f.entries, key=lambda e: e.entry_name):
                print(f"  {e.entry_name}")
        return

    if args.tree:
        print_tree(project)
        return

    if args.entry:
        found = False
        for f in project.files:
            for e in f.entries:
                if e.name.lower() == args.entry.lower() or e.entry_name.lower() == args.entry.lower():
                    dump_entry(e)
                    found = True
        if not found:
            print(f"Entry not found: {args.entry}", file=sys.stderr)
            print("Available entries:", file=sys.stderr)
            for f in project.files:
                for e in sorted(f.entries, key=lambda e: e.entry_name):
                    print(f"  {e.entry_name}", file=sys.stderr)
        return

    if args.all:
        for f in project.files:
            for e in sorted(f.entries, key=lambda e: e.entry_name):
                dump_entry(e)
        return

    # Default: show tree
    print_tree(project)


if __name__ == "__main__":
    main()
