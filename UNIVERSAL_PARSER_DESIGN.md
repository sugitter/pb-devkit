# PB DevKit 通用解析器技术方案

> **版本**: v1.x (Python) → v2.0 (Rust)  
> **日期**: 2026-04-14  
> **目标**: 统一 PBL 源码解析 + PBD 编译库解析 + EXE/DLL PE 宿主解析，精准还原 Sybase 原始 PB 文件管理格式

---

## 一、设计目标

### 1.1 核心能力

| 能力 | 现状 (v1.3) | 目标 (v2.0) |
|------|------------|------------|
| PBL 源码解析 | ✅ ANSI + Unicode | ✅ 完整 ENT* 注释解析 |
| PBD 编译库 | ❌ 跳过编译对象 | ✅ 完整 chunk 链 + Entry 元数据 |
| EXE/DLL 宿主 | ❌ 不支持 | ✅ PE 资源节提取 → PBD 子流 |
| P-code 反编译 | ❌ 不支持 | ✅ PB9-PB11+ 指令集 |
| 编译对象结构 | ❌ 不解析 | ✅ 变量/函数/继承/类型完整解析 |
| 系统类型定义 | ❌ 不支持 | ✅ typedef .bin 解码 |

### 1.2 设计原则

1. **Sybase 原生格式优先** — 所有解析严格遵循 Sybase 设计的 chunk 管理格式（HDR*/NOD*/ENT*/DAT*），零猜测
2. **零外部依赖** — 纯 Python + 标准库（struct/gzip/re/io），与 v1.3 保持一致
3. **向后兼容** — 现有 `PBLParser` API 不变，新功能通过扩展类暴露
4. **渐进式解析** — 支持三种粒度：目录列表 → 元数据 → 源码/二进制 → P-code 反编译

---

## 二、Sybase PB 文件管理格式精确定义

### 2.1 四层 Chunk 结构

```
┌──────────────────────────────────────────────────────────┐
│  HDR* (Library Header)                                    │
│  ├─ ANSI (PB5-PB9):  512 bytes                           │
│  └─ Unicode (PB10+): 1024 bytes                          │
├──────────────────────────────────────────────────────────┤
│  FRE* (Free Space Bitmap) — 512 bytes                     │
├──────────────────────────────────────────────────────────┤
│  NOD* (B-Tree Index) — 6×512 = 3072 bytes per group      │
│  ├─ Header: 32 bytes                                      │
│  │   ├─ [0:4]   "NOD*" signature                          │
│  │   ├─ [4:8]   left sibling offset (uint32)              │
│  │   ├─ [8:12]  parent node offset (uint32)               │
│  │   ├─ [12:16] right sibling offset (uint32)             │
│  │   ├─ [16:20] space_left? (uint32)                     │
│  │   └─ [20:22] entry_count (uint16) ← 关键字段           │
│  └─ Entries start at byte 32                               │
├──────────────────────────────────────────────────────────┤
│  ENT* (Entry) — variable length, packed in NOD* blocks     │
│  ├─ ANSI header (24 bytes):                                │
│  │   [0:4]  "ENT*"                                        │
│  │   [4:8]  version string (ASCII, "0500"/"0600")         │
│  │   [8:12] data_offset (uint32) → DAT* chain start       │
│  │   [12:16] data_size (uint32)                           │
│  │   [16:20] timestamp (uint32, Unix epoch)               │
│  │   [20:22] unknown (uint16)                             │
│  │   [22:24] name_buf_len (uint16, includes version)      │
│  │   → followed by: name_buf(name_buf_len)                │
│  └─ Unicode header (28 bytes):                             │
│      [0:4]  "ENT*"                                        │
│      [4:12] version string (UTF-16LE, "0500"/"0600")     │
│      [12:16] data_offset (uint32)                          │
│      [16:20] data_size (uint32)                            │
│      [20:24] timestamp (uint32)                            │
│      [24:26] unknown (uint16)                              │
│      [26:28] name_buf_len (uint16)                         │
│      → followed by: name_buf(name_buf_len)                │
├──────────────────────────────────────────────────────────┤
│  DAT* (Data Block Chain) — 512 bytes per block             │
│  ├─ [0:4]   "DAT*" signature                               │
│  ├─ [4:8]   next_offset (uint32, 0 = end)                 │
│  ├─ [8:10]  data_len (uint16, max 502)                    │
│  └─ [10:512] data payload                                  │
└──────────────────────────────────────────────────────────┘
```

> **重要**: ENT* 头部中**没有 comment_len 字段**。Arnd Schmidt 原始文档中的描述不准确。
> PbdViewer (C#) 和 PbdCli (Python) 两个参考实现均已验证：header_size+14 处的 ushort
> 是 name_buf_len，头部之后紧跟 name 缓冲区。对象类型通过名称扩展名或命名前缀推断。

### 2.2 名字缓冲区解码（PbdViewer 精确算法）

```python
# name_buf_len 包含 ENT* marker(4) + version(num*4) 作为前缀
# 实际名字长度 = name_buf_len - num (num=1 for ANSI, num=2 for Unicode)
# 名字从 name_buf 的第 0 个字节开始（不是 num*4 之后）
# PbdViewer 源码: Project.GetString(buffer2, 0, uShort2 - num)
actual_name_len = name_buf_len - num
name = name_buf[:actual_name_len].decode('utf-16-le' if unicode else 'latin-1')
```

> **注意**: ENT* 中没有 comment 字段。对象类型通过以下方式检测：
> 1. PB12+ Unicode: 名称中嵌入的扩展名（.srw, .win, .dwo 等）
> 2. PB5-PB9 ANSI: 命名前缀约定（w_, d_, m_, n_ 等）

---

## 三、通用解析架构

### 3.1 模块结构

```
src/pb_devkit/
├── pbl_parser.py          # [保留] PBL 源码解析 (v1.3 兼容)
├── sr_parser.py           # [保留] .sr* 源码文本解析
├── universal_parser.py    # [新增] 通用入口：自动识别文件类型
├── chunk_engine.py        # [新增] 四层 Chunk 链解析引擎
├── binary_entry.py        # [新增] 编译对象 Entry 级别解析
├── type_system.py         # [新增] PB 类型系统 (值/系统/用户三类索引)
├── variable_parser.py     # [新增] 变量解析 (标志位/数组/枚举/默认值)
├── pcode/
│   ├── __init__.py        # P-code 反编译引擎入口
│   ├── instruction.py     # [新增] 指令定义与操作码表 (PB9-PB11+)
│   ├── decoder.py         # [新增] 指令流解码器 (字节→CodeLine)
│   ├── decompiler.py      # [新增] 反编译器 (CodeLine→PowerScript)
│   ├── sql_restore.py     # [新增] SQL 语句还原
│   ├── control_flow.py    # [新增] 控制流分析 (try-catch/choose/if-else)
│   ├── version_map.py     # [新增] PB 版本→指令集映射
│   └── stack_machine.py   # [新增] 栈式虚拟机模拟执行
├── pe_extractor.py        # [新增] PE 格式解析 + PBD 资源提取
├── typedef_loader.py      # [新增] 系统 typedef .bin 加载与解码
└── ...
```

### 3.2 核心类图

```
                    ┌──────────────────┐
                    │  UniversalParser │  ← 统一入口
                    │  (factory)       │
                    └────────┬─────────┘
                             │ 自动识别
                ┌────────────┼────────────┐
                ▼            ▼            ▼
        ┌──────────────┐ ┌──────────┐ ┌──────────────┐
        │ ChunkEngine  │ │PEExtract │ │ TypedefLoader│
        │ (PBL/PBD)    │ │(EXE/DLL) │ │ (.bin gzip)  │
        └──────┬───────┘ └────┬─────┘ └──────────────┘
               │              │
               │         ┌────┴─────┐
               │         │ChunkEngine│ ← 提取的 PBD 子流
               │         └────┬─────┘
               │              │
        ┌──────┴──────────────┴──────────┐
        │           PBEntry               │
        │  (name, type, offset, size,    │
        │   comment, timestamps)         │
        └──────┬──────────┬──────────────┘
               │          │
        ┌──────┴──┐ ┌─────┴──────────┐
        │SourceExp│ │BinaryEntryParser│
        │(文本)   │ │(编译对象)       │
        └─────────┘ └─────┬──────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         Variable    Function    Inheritance
         Parser      Defs        Tree
```

### 3.3 UniversalParser — 通用入口

```python
class UniversalParser:
    """通用 PB 文件解析器，自动识别输入类型并路由到对应引擎。

    支持输入:
    - .pbl — 本地源码库 (HDR* 魔数)
    - .pbd — 编译库 (HDR* 魔数, 内容为 P-code)
    - .exe / .dll — PE 宿主文件 (MZ/PE 魔数, 内含 PBD 资源)
    - .bin — 独立提取的 PBD 数据 (HDR* 魔数)
    """
    
    def __init__(self, path: str|Path, pb_version: int = 0):
        self.path = Path(path)
        self.pb_version = pb_version
        self._format = None  # 'pbl'|'pbd'|'pe'|'bin'
    
    def open(self) -> UniversalParser:
        """自动检测格式并初始化解析引擎。"""
        header = self._read_header(1028)
        
        if header[:4] == b"HDR*":
            # PBL 或 PBD — 需要进一步区分
            self._format = "pbd"  # 统一为 chunk 格式
            self._engine = ChunkEngine(self.path)
            self._engine.open()
            # 如果所有 entry 都是 .sr* 源码格式 → pbl
            # 如果包含 .win/.dwo/.prp 编译格式 → pbd
            source_count = sum(1 for e in self._engine.entries 
                             if e.extension in SOURCE_EXTENSIONS)
            compiled_count = len(self._engine.entries) - source_count
            if compiled_count == 0:
                self._format = "pbl"
        elif header[:2] == b"MZ":
            # PE 文件 — 需要提取内嵌 PBD 资源
            self._format = "pe"
            extractor = PEExtractor(self.path)
            self._embedded_pbd_data = extractor.extract_pbd_resources()
        else:
            raise ValueError(f"Unknown format: {self.path}")
        
        return self
    
    @property
    def format(self) -> str:
        return self._format
    
    @property
    def entries(self) -> list[PBEntry]:
        """统一返回 entry 列表，无论底层格式。"""
        if self._format in ("pbl", "pbd"):
            return self._engine.entries
        elif self._format == "pe":
            # 合并所有嵌入 PBD 的 entries
            return self._merged_entries()
    
    def export_source(self, entry: PBEntry) -> bytes|None:
        """导出 entry 的源数据 (源码文本或编译二进制)。"""
        ...
    
    def parse_binary(self, entry: PBEntry) -> BinaryEntry|None:
        """解析编译对象的内部结构 (变量/函数/继承/类型)。"""
        data = self.export_source(entry)
        if not data or entry.is_source:
            return None
        parser = BinaryEntryParser(data, self.pb_version)
        return parser.parse()
    
    def decompile(self, entry: PBEntry, routine_index: int = 0) -> str|None:
        """反编译 P-code 为 PowerScript 文本。"""
        binary = self.parse_binary(entry)
        if not binary:
            return None
        engine = PCodeEngine(self.pb_version or binary.pcode_version)
        return engine.decompile(binary, routine_index)
```

### 3.4 ChunkEngine — 四层 Chunk 链解析引擎

从现有 `PBLParser` 提取核心 chunk 逻辑，修复已知问题，增强通用性。

```python
class ChunkEngine:
    """Sybase PB 文件四层 Chunk 链解析引擎。
    
    严格遵循原始设计:
    - HDR* (512/1024b) → FRE* (512b) → NOD* (3072b B-tree) → ENT*/DAT*
    
    改进 (vs PBLParser v1.3):
    - 完整解析 ENT* comment 字段
    - 支持任意 ENT* version string (不限于 "0500"/"0600")
    - 双链遍历 NOD* (left/right/parent) 用于验证完整性
    - 精确的 PB 版本检测
    """
    
    BLOCK_SIZE = 512
    BLOCK_UNICODE = 1024
    NODE_BLOCK_SIZE = 3072
    
    def __init__(self, path: str|Path, data: bytes|None = None):
        """支持文件路径或内存数据 (用于 PE 提取的 PBD 子流)。"""
        self.path = Path(path) if path else None
        self._data = data  # 内存模式
        self._fh = None
        self.entries: list[PBEntry] = []
        self._is_unicode = False
        self._header_size = 0
        self._pb_version = 0
    
    def open(self) -> ChunkEngine:
        if self._data:
            self._stream = io.BytesIO(self._data)
        else:
            self._fh = open(self.path, "rb")
            self._stream = self._fh
        self._detect_format()
        self._parse_tree()
        return self
    
    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None
    
    def _read(self, offset: int, size: int) -> bytes:
        self._stream.seek(offset)
        return self._stream.read(size)
    
    def _detect_format(self):
        """检测 HDR* 格式并提取 PB 版本号。"""
        header = self._read(0, min(self.BLOCK_UNICODE + 4, self._stream_size))
        
        if header[:4] != b"HDR*":
            raise ValueError("Not a valid PB library file (missing HDR*)")
        
        # ANSI vs Unicode: 检查 FRE* 位置
        if header[512:516] == b"FRE*":
            self._is_unicode = False
            self._header_size = self.BLOCK_SIZE  # 512
        elif header[self.BLOCK_UNICODE:self.BLOCK_UNICODE+4] == b"FRE*":
            self._is_unicode = True
            self._header_size = self.BLOCK_UNICODE  # 1024
        else:
            # Fallback
            self._is_unicode = b"\xff\xfe" in header[:32]
            self._header_size = self.BLOCK_UNICODE if self._is_unicode else self.BLOCK_SIZE
        
        # 提取 PB 版本号
        self._detect_pb_version(header)
    
    def _detect_pb_version(self, header: bytes):
        """从 HDR* 提取 PB 版本。"""
        # HDR* 布局:
        # [0:4] "HDR*"
        # [4:20] "PowerBuilder" (ANSI) or UTF-16LE equivalent
        # 后面有版本号，具体位置因 PB 版本而异
        # 简化: 从第一个 ENT* 的 version 字符串提取
        # 完整实现参考 PbdViewer: 从 HDR* 的特定偏移读取
        pass  # 在 parse_tree 时从第一个 ENT* 获取
    
    def _parse_tree(self):
        """遍历 NOD* B-tree，解析所有 ENT* entries。"""
        file_size = self._stream_size
        nod_start = self._header_size + self.BLOCK_SIZE  # HDR* + FRE*
        
        if nod_start + 4 > file_size:
            return
        
        num = 2 if self._is_unicode else 1
        num2 = 4 + num * 4      # 固定字段起始偏移
        num3 = num2 + 16        # ENT* 固定头大小
        
        visited = set()
        current_offset = nod_start
        
        while current_offset > 0 and current_offset not in visited:
            visited.add(current_offset)
            
            nod_data = self._read(current_offset, self.NODE_BLOCK_SIZE)
            if not nod_data or nod_data[:4] != b"NOD*":
                break
            
            entry_count = struct.unpack_from("<H", nod_data, 20)[0]
            right_offset = struct.unpack_from("<I", nod_data, 12)[0]
            
            pos_in_nod = 32
            
            for _ in range(entry_count):
                if pos_in_nod + num3 > len(nod_data):
                    break
                
                ent_header = nod_data[pos_in_nod:pos_in_nod + num3]
                if ent_header[:4] != b"ENT*":
                    break
                
                # 版本字符串 (不限制为 "0500"/"0600")
                ver_bytes = ent_header[4:4 + num * 4]
                if self._is_unicode:
                    ver_text = ver_bytes.decode("utf-16-le", errors="replace")
                else:
                    ver_text = ver_bytes.decode("ascii", errors="replace")
                
                # 固定字段
                data_offset = struct.unpack_from("<I", ent_header, num2)[0]
                obj_size = struct.unpack_from("<I", ent_header, num2 + 4)[0]
                raw_ts = struct.unpack_from("<I", ent_header, num2 + 8)[0]
                comment_len = struct.unpack_from("<H", ent_header, num2 + 12)[0]
                name_buf_len = struct.unpack_from("<H", ent_header, num2 + 14)[0]
                
                # ★ 关键修复: 读取 comment 字段 (v1.3 遗漏)
                comment_raw_offset = pos_in_nod + num3
                comment = ""
                if comment_len > 0:
                    comment_bytes = nod_data[comment_raw_offset:comment_raw_offset + comment_len]
                    if self._is_unicode:
                        comment = comment_bytes.decode("utf-16-le", errors="replace")
                    else:
                        comment = comment_bytes.decode("latin-1", errors="replace")
                
                # 名字缓冲区 (在 comment 之后)
                name_buf_offset = comment_raw_offset + comment_len
                name_buf = nod_data[name_buf_offset:name_buf_offset + name_buf_len]
                
                actual_name_len = name_buf_len - num
                if actual_name_len <= 0:
                    pos_in_nod = name_buf_offset + name_buf_len
                    continue
                
                if self._is_unicode:
                    name = name_buf[:actual_name_len].decode("utf-16-le", errors="replace")
                else:
                    name = name_buf[:actual_name_len].decode("latin-1", errors="replace")
                name = name.rstrip("\x00").strip()
                
                pos_in_nod = name_buf_offset + name_buf_len
                
                # 时间戳
                ts = raw_ts
                if ts > 3_000_000_000:
                    ts //= 1000
                try:
                    t = datetime.fromtimestamp(ts, tz=timezone.utc) if ts > 0 else None
                except (OSError, OverflowError, ValueError):
                    t = None
                
                # 类型检测: 优先 comment, 其次扩展名, 最后前缀
                obj_type = self._detect_type(name, comment)
                
                entry = PBEntry(
                    name=name,
                    object_type=obj_type,
                    comment=comment,  # ★ v1.3 总是 ""
                    first_data_offset=data_offset,
                    data_size=obj_size,
                    creation_time=t,
                    is_source=self._is_source_entry(name, obj_type),
                )
                
                if (entry.first_data_offset > 0 and entry.data_size > 0
                    and entry.first_data_offset <= file_size
                    and entry.data_size <= 10_000_000
                    and not any(x.name == entry.name for x in self.entries)):
                    self.entries.append(entry)
                    # 记录 PB 版本 (从第一个有效的 ENT* 获取)
                    if not self._pb_version and ver_text.isdigit():
                        self._pb_version = int(ver_text)
            
            current_offset = right_offset
    
    def read_data_chain(self, offset: int, size: int) -> bytes|None:
        """读取 DAT* 块链，拼接完整数据。支持内存和文件两种模式。"""
        file_size = self._stream_size
        if offset > file_size:
            return None
        
        result = bytearray()
        cur = offset
        rem = min(size, 10_000_000) if size > 0 else 10_000_000
        
        while cur != 0 and rem > 0:
            if cur > file_size:
                break
            
            blk = self._read(cur, self.BLOCK_SIZE)
            if not blk or len(blk) < 10:
                break
            
            if blk[:4] != b"DAT*":
                result.extend(blk[:min(rem, len(blk))])
                break
            
            next_offset = struct.unpack_from("<I", blk, 4)[0]
            data_len = struct.unpack_from("<H", blk, 8)[0]
            
            if data_len <= 0 or data_len > 502:
                data_len = self.BLOCK_SIZE - 10
            
            actual_len = min(data_len, rem)
            result.extend(blk[10:10 + actual_len])
            rem -= actual_len
            
            if next_offset == 0 or next_offset > file_size or next_offset == 0xFFFFFFFF:
                cur = 0
            else:
                cur = next_offset
        
        return bytes(result) if result else None
```

---

## 四、PE 宿主文件解析

### 4.1 PEExtractor — 从 EXE/DLL 提取 PBD

PB 编译的 EXE/DLL 将 PBD 数据作为自定义资源嵌入 PE 文件的资源节。
PB 使用资源类型名称 (而非数字 ID) 来标识嵌入的 PBD。

```python
class PEExtractor:
    """从 PE 格式 EXE/DLL 中提取嵌入的 PBD 数据。
    
    PE 文件结构:
    DOS Header → PE Signature → COFF Header → Optional Header
    → Section Table (Section Headers)
    → Sections: .text, .rdata, .rsrc, ...
    
    PB 嵌入资源位于 .rsrc 节的 Resource Directory 中。
    """
    
    def __init__(self, path: str|Path):
        self.path = Path(path)
    
    def extract_pbd_resources(self) -> list[PBDResource]:
        """提取所有嵌入的 PBD 资源。"""
        data = self.path.read_bytes()
        
        # 1. 解析 DOS Header
        if data[:2] != b"MZ":
            raise ValueError("Not a valid PE file")
        
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_offset:pe_offset+4] != b"PE\x00\x00":
            raise ValueError("Invalid PE signature")
        
        # 2. COFF Header
        coff = pe_offset + 4
        num_sections = struct.unpack_from("<H", data, coff + 2)[0]
        optional_hdr_size = struct.unpack_from("<H", data, coff + 16)[0]
        
        # 3. Optional Header → Data Directory[2] = Resource Directory
        opt = coff + 20
        is_pe32plus = data[opt] == 0x0B  # PE32+ vs PE32
        
        if is_pe32plus:
            rsrc_rva = struct.unpack_from("<I", data, opt + 112)[0]
            rsrc_size = struct.unpack_from("<I", data, opt + 116)[0]
        else:
            rsrc_rva = struct.unpack_from("<I", data, opt + 96)[0]
            rsrc_size = struct.unpack_from("<I", data, opt + 100)[0]
        
        if rsrc_rva == 0:
            return []  # 无资源节
        
        # 4. Section Table → 找 .rsrc 节的文件偏移
        section_table = opt + optional_hdr_size
        rsrc_file_offset = None
        
        for i in range(num_sections):
            sec = section_table + i * 40
            sec_rva = struct.unpack_from("<I", data, sec + 12)[0]
            sec_vsize = struct.unpack_from("<I", data, sec + 8)[0]
            sec_raw = struct.unpack_from("<I", data, sec + 20)[0]
            sec_raw_size = struct.unpack_from("<I", data, sec + 16)[0]
            
            if sec_rva <= rsrc_rva < sec_rva + sec_vsize:
                rsrc_file_offset = rsrc_rva - sec_rva + sec_raw
                break
        
        if rsrc_file_offset is None:
            return []
        
        # 5. 遍历 Resource Directory 查找 PB 资源
        return self._parse_resource_directory(data, rsrc_file_offset, rsrc_rva)
    
    def _rva_to_offset(self, data: bytes, rva: int, sections: list) -> int:
        """RVA → 文件偏移转换。"""
        for sec in sections:
            if sec['rva'] <= rva < sec['rva'] + sec['vsize']:
                return rva - sec['rva'] + sec['raw_offset']
        return rva
    
    def _parse_resource_directory(self, data, base_offset, base_rva):
        """解析资源目录树，查找 PB 嵌入的 PBD 数据。"""
        # PB EXE 的 PBD 资源通常使用自定义资源类型
        # 资源目录是三层树: Type → Name/ID → Language
        # PB 使用类型名 (如 "PBDB" 或数字类型) 标识
        
        resources = []
        # 详细实现参考 PbdViewer PEHelper.cs LoadResourceDirectory()
        # 核心逻辑: 遍历所有资源类型，找到数据块，检查 HDR* 签名
        
        return resources
```

### 4.2 PE 提取流程

```
EXE/DLL 文件
    │
    ├─ DOS Header (e_lfanew → PE offset)
    │
    ├─ PE Header → Resource Directory RVA
    │
    ├─ Section Table → .rsrc file offset
    │
    └─ Resource Directory Tree
        │
        ├─ Level 1: Resource Type (PB 使用自定义类型)
        │
        ├─ Level 2: Resource ID / Name
        │
        ├─ Level 3: Language ID
        │
        └─ Data Entry → RVA → File Offset → Raw Data
            │
            └─ 检查 HDR* 签名 → ChunkEngine(data=raw_pbd)
```

---

## 五、编译对象 Entry 解析

### 5.1 编译对象内部结构

编译后的 PB 对象（.win, .dwo, .prp, .udo 等）的二进制格式如下
（参考 PbdViewer PbEntry.cs, 740 行精确逆向）:

```
┌──────────────────────────────────────────────────────┐
│ [ushort]  pdb_version      // P-code 版本 (193/238/283/316+)  │
│ [ushort]  flags            // 对象标志位                       │
│ [uint]    entry_type       // 对象类型 (Window/DW/Menu/...)    │
│ [uint]    modified_time    // 最后修改时间 (Unix timestamp)    │
│ [uint]    compiled_time    // 编译时间 (Unix timestamp)       │
│ [uint]    unk2             // 未知 (通常为 0)                 │
│ [ushort]  num4             // 变量/缓冲区数量计数器           │
├──────────────────────────────────────────────────────┤
│ Variable-length buffer (num4 entries)                  │
│   每个: [uint offset, uint size] → variable_buffer     │
├──────────────────────────────────────────────────────┤
│ Variables                                           │
│   PB5:  8 bytes/variable                             │
│   PB6+: 16 bytes/variable                            │
├──────────────────────────────────────────────────────┤
│ [uint] num5                 // 对象引用数量           │
│ [num5 objects]               // 每个引用的结构体      │
├──────────────────────────────────────────────────────┤
│ [uint] num6                 // 继承层次数量           │
│ [num6 inheritance buffers]   // 每层的继承数据       │
├──────────────────────────────────────────────────────┤
│ Types                                               │
│   三层索引:                                          │
│   index >> 12 == 0 → 值类型 (0x0000-0x0FFF)         │
│   index >> 12 == 4 → 系统类型 (0x4000-0x4FFF)       │
│   index >> 12 == 8 → 用户类型 (0x8000-0x8FFF)       │
│   index >> 12 == C → void/null                      │
├──────────────────────────────────────────────────────┤
│ Enums                                               │
│   枚举类型定义                                        │
├──────────────────────────────────────────────────────┤
│ Function Definitions                                 │
│   [access] [return_type] [name] [args...] [pcode]   │
└──────────────────────────────────────────────────────┘
```

### 5.2 BinaryEntryParser

```python
@dataclass
class BinaryEntry:
    """编译对象的完整解析结果。"""
    name: str
    object_type: PBObjectType
    pcode_version: int          # PB9=193, PB10=238, PB10.5=283, PB11=316+
    flags: int
    entry_type: int
    modified_time: datetime|None
    compiled_time: datetime|None
    variables: list[PBVariable]
    function_defs: list[FunctionDef]
    inheritance: list[InheritanceInfo]
    types: list[PBTypeRef]
    enums: list[PBEnumDef]
    raw_data: bytes             # 原始二进制数据


class BinaryEntryParser:
    """解析编译后 PB 对象的内部二进制结构。"""
    
    # PB 版本 → 变量结构体大小
    VAR_STRUCT_SIZE = {
        (0, 5): 8,    # PB5
        (6, 99): 16,  # PB6-PB9
        (10, 999): 16, # PB10+
    }
    
    def __init__(self, data: bytes, pb_version: int = 0):
        self.data = data
        self.pb_version = pb_version
        self._pos = 0
    
    def parse(self) -> BinaryEntry:
        result = BinaryEntry(name="", object_type=PBObjectType.BINARY, ...)
        
        # [1] Header
        result.pcode_version = self._read_ushort()
        result.flags = self._read_ushort()
        result.entry_type = self._read_uint()
        result.modified_time = self._read_timestamp(self._read_uint())
        result.compiled_time = self._read_timestamp(self._read_uint())
        unk2 = self._read_uint()
        num4 = self._read_ushort()
        
        # [2] Variable buffer
        var_buffer_offsets = []
        for _ in range(num4):
            off = self._read_uint()
            sz = self._read_uint()
            var_buffer_offsets.append((off, sz))
        
        # [3] Variables
        # PB5: 8 bytes/variable, PB6+: 16 bytes/variable
        var_size = self._get_var_struct_size()
        variables = []
        while self._pos < len(self.data):
            var = self._parse_variable()
            if var is None:
                break
            variables.append(var)
        result.variables = variables
        
        # [4] Objects / Inheritance / Types / Enums / Functions
        # ... (按 PbdViewer PbEntry.cs 逻辑逐步解析)
        
        return result
    
    def _parse_variable(self) -> PBVariable|None:
        """解析单个变量。"""
        start_pos = self._pos
        
        # 读取标志位字节 (buffer[17] in PbdViewer)
        var_data = self.data[self._pos:self._pos + self._var_size]
        if len(var_data) < self._var_size:
            return None
        
        flags_byte = var_data[17]
        
        # PbVariableFlag 枚举解析
        is_array = bool(flags_byte & 0x01)
        is_constant = bool(flags_byte & 0x02)
        is_global = bool(flags_byte & 0x04)
        is_shared = bool(flags_byte & 0x08)
        is_argument = bool(flags_byte & 0x10)
        
        # 类型索引
        type_index = struct.unpack_from("<H", var_data, 0)[0]
        
        # 名称
        name = var_data[20:20 + 256].split(b"\x00")[0].decode(
            "utf-16-le" if self._is_unicode else "latin-1", errors="replace")
        
        # 数组边界 (存储在 variable_buffer 中)
        # ... 
        
        self._pos += self._var_size
        return PBVariable(name=name, type_index=type_index, ...)
```

---

## 六、P-Code 反编译引擎

### 6.1 PB 版本 → P-code 指令集映射

```python
# version_map.py

PCODE_VERSIONS = {
    # PB version → (pcode_version, parser_class_name, instruction_count)
    9:   (193, "PCodeParser90",  547),   # PB9
    10:  (238, "PCodeParser100", 560),   # PB10
    10.5: (283, "PCodeParser105", 580),  # PB10.5
    11:  (316, "PCodeParser110", 600),   # PB11
    11.5: (333, "PCodeParser110", 610),  # PB11.5 (PB12 使用相同指令集)
    12:  (333, "PCodeParser110", 610),   # PB12
    12.5: (333, "PCodeParser110", 610),  # PB12.5
}

# 指令长度表 (每个版本的操作码 → 指令字节数)
# PB9: 547 个操作码
# PB10: 560 个操作码 (新增 Unicode 字符串操作)
# PB10.5: 580 个操作码 (新增 .NET 互操作)
# PB11: 600+ 个操作码 (新增泛型支持)
INSTRUCTION_LENGTHS = {
    193: [0] * 547,   # 填充实际数据
    238: [0] * 560,
    283: [0] * 580,
    316: [0] * 600,
    333: [0] * 610,
}
```

### 6.2 核心指令分类

```
P-code 操作码分类:

1. 栈操作
   ├── PushConstant (int/uint/long/real/double/decimal/string/date/time/bool/null)
   ├── PushVariable (local/global/shared/instance/argument/by-reference)
   ├── Pop
   ├── Duplicate
   └── Swap

2. 算术/逻辑
   ├── Add, Subtract, Multiply, Divide, Modulus
   ├── Negate, Increment, Decrement
   ├── And, Or, Not, Xor
   └── ShiftLeft, ShiftRight

3. 比较/跳转
   ├── Compare (=, <>, <, >, <=, >=)
   ├── Jump (unconditional)
   ├── JumpIfTrue / JumpIfFalse
   └── JumpIfNull / JumpIfNotNull

4. 函数调用
   ├── CallFunction (object method)
   ├── CallGlobal (global function)
   ├── CallSuper (parent class method)
   ├── CallBuiltin (system function: Len(), Left(), etc.)
   └── CallEvent

5. 对象操作
   ├── CreateObject
   ├── DestroyObject
   ├── GetProperty / SetProperty
   ├── GetAt / SetAt (array/collection)
   └── IsInstance, TypeOf

6. 控制流
   ├── Try / Catch / Finally / EndTry
   ├── ChooseCase / Case / EndChoose
   ├── ForNext / ForEach
   ├── DoWhile / DoUntil / Loop
   ├── If/ElseIf/Else/EndIf
   ├── Return
   ├── Throw
   └── Continue, Exit, Goto

7. SQL 操作
   ├── SQLConnect / SQLDisconnect / SQLCommit / SQLRollback
   ├── SQLOpen / SQLFetch / SQLClose
   ├── SQLPrepare / SQLExecute
   ├── SQLDescribe / SQLGetItem
   └── Dynamic SQL (Type 1-4)

8. 数据类型转换
   ├── IntToLong, IntToString, StringToInt
   ├── DateToString, StringToDate
   ├── RealToDouble, DecimalToReal
   └── AnyCast
```

### 6.3 PCodeEngine — 反编译引擎

```python
class PCodeEngine:
    """P-Code 反编译引擎。
    
    工作流程:
    bytes → Decoder → CodeLine[] → ControlFlowAnalyzer → Decompiler → PowerScript text
    """
    
    def __init__(self, pcode_version: int):
        self.version = pcode_version
        self.decoder = InstructionDecoder(pcode_version)
        self.decompiler = PowerScriptDecompiler(pcode_version)
    
    def decompile(self, binary: BinaryEntry, routine_index: int = 0) -> str:
        """反编译指定函数/事件的 P-code 为 PowerScript 文本。"""
        func = binary.function_defs[routine_index]
        
        # 1. 提取 P-code 字节流
        pcode_bytes = binary.raw_data[func.pcode_offset:func.pcode_offset + func.pcode_size]
        
        # 2. 解码为指令序列
        code_lines = self.decoder.decode(pcode_bytes, func.pcode_offset)
        
        # 3. 控制流分析
        cf_analyzer = ControlFlowAnalyzer(code_lines)
        cf_analyzer.analyze()
        
        # 4. 反编译为 PowerScript
        script = self.decompiler.decompile(code_lines, cf_analyzer, func)
        
        return script


class InstructionDecoder:
    """字节流 → CodeLine 指令解码器。"""
    
    def __init__(self, pcode_version: int):
        self.version = pcode_version
        self.length_table = INSTRUCTION_LENGTHS[pcode_version]
        self.opcode_names = OPCODE_NAMES[pcode_version]
    
    def decode(self, data: bytes, base_offset: int = 0) -> list[CodeLine]:
        """将字节流解码为指令序列。"""
        lines = []
        pos = 0
        
        while pos < len(data):
            offset = pos + base_offset
            opcode = data[pos]
            
            if opcode >= len(self.length_table):
                break
            
            instr_len = self.length_table[opcode]
            if instr_len == 0 or pos + instr_len > len(data):
                break
            
            operands = data[pos + 1:pos + instr_len]
            name = self.opcode_names.get(opcode, f"OP_{opcode:03d}")
            
            lines.append(CodeLine(
                offset=offset,
                opcode=opcode,
                name=name,
                operands=operands,
                raw_bytes=data[pos:pos + instr_len],
            ))
            
            pos += instr_len
        
        return lines


@dataclass
class CodeLine:
    """单条 P-code 指令。"""
    offset: int
    opcode: int
    name: str
    operands: bytes
    raw_bytes: bytes
    jump_target: int|None = None  # 跳转目标偏移


class ControlFlowAnalyzer:
    """控制流分析器。
    
    检测结构:
    - Try/Catch/Finally/EndTry
    - ChooseCase/Case/EndChoose
    - If/ElseIf/Else/EndIf
    - For/Next, Do/Loop
    """
    
    def analyze(self, code_lines: list[CodeLine]) -> ControlFlowGraph:
        """分析控制流，构建 CFG。"""
        cfg = ControlFlowGraph()
        
        # 第一遍: 标记所有跳转目标
        for line in code_lines:
            if line.name in ("Jump", "JumpIfTrue", "JumpIfFalse"):
                target = struct.unpack_from("<i", line.operands)[0] + line.offset
                line.jump_target = target
                cfg.add_jump(line.offset, target)
        
        # 第二遍: 识别结构化控制流
        self._identify_try_catch(code_lines, cfg)
        self._identify_choose(code_lines, cfg)
        self._identify_if_else(code_lines, cfg)
        self._identify_loops(code_lines, cfg)
        
        return cfg
    
    def _identify_try_catch(self, lines, cfg):
        """识别 try-catch-finally 结构。"""
        # Try 指令包含 catch/finally 的偏移信息
        for line in lines:
            if line.name == "Try":
                # operands: [catch_offset, finally_offset, end_offset]
                catch_off = struct.unpack_from("<i", line.operands, 0)[0] + line.offset
                end_off = struct.unpack_from("<i", line.operands, 8)[0] + line.offset
                cfg.add_structure("try", line.offset, end_off, catch=catch_off)
    
    def _identify_choose(self, lines, cfg):
        """识别 choose case 结构。"""
        # ChooseCase 操作码后跟 Case 操作码
        pass
    
    def _identify_if_else(self, lines, cfg):
        """识别 if-elseif-else 结构。"""
        # JumpIfFalse 跳到 else/endif
        pass
    
    def _identify_loops(self, lines, cfg):
        """识别 for-next / do-loop 结构。"""
        # 循环通过跳转回跳检测
        pass


class PowerScriptDecompiler:
    """CodeLine[] + CFG → PowerScript 文本。"""
    
    def decompile(self, code_lines: list[CodeLine], 
                  cfg: ControlFlowGraph, func: FunctionDef) -> str:
        """将指令序列反编译为 PowerScript。"""
        lines = []
        indent = 1
        
        for cl in code_lines:
            # 跳过结构标记指令
            if cl.name in ("Try", "Catch", "Finally", "EndTry",
                           "ChooseCase", "Case", "EndChoose"):
                # 由 CFG 驱动的结构化输出
                struct = cfg.get_structure_at(cl.offset)
                if struct:
                    lines.append(self._format_structure(struct, indent))
                continue
            
            # 普通指令 → PowerScript 语句
            ps_line = self._instruction_to_script(cl, func)
            if ps_line:
                lines.append("    " * indent + ps_line)
        
        return "\n".join(lines)
    
    def _instruction_to_script(self, cl: CodeLine, func: FunctionDef) -> str:
        """将单条指令翻译为 PowerScript 语句。"""
        if cl.name.startswith("PushConstant"):
            return self._decompile_push(cl)
        elif cl.name == "CallFunction":
            return self._decompile_call(cl, func)
        elif cl.name == "CallBuiltin":
            return self._decompile_builtin(cl)
        elif cl.name == "JumpIfFalse":
            return ""  # 由 CFG 处理
        elif cl.name.startswith("SQL"):
            return self._decompile_sql(cl)
        else:
            return f"// {cl.name} {cl.operands.hex()}"
```

### 6.4 SQL 语句还原

```python
class SQLRestorer:
    """还原嵌入 P-code 的 SQL 语句。
    
    PB P-code 中的 SQL 操作码:
    - SQLConnect / SQLDisconnect / SQLCommit / SQLRollback
    - SQLOpen(cursor, statement)
    - SQLFetch(cursor, into_variables...)
    - SQLClose(cursor)
    - SQLPrepare(statement_id, sql_text)
    - SQLExecute(statement_id, params...)
    - Dynamic SQL Type 1-4
    """
    
    def restore_connect(self, operands: bytes) -> str:
        return "CONNECT USING sqlca;"
    
    def restore_open(self, operands: bytes, variables: list) -> str:
        """还原 DECLARE cursor OPEN FOR ..."""
        # operands 包含游标索引和 SQL 语句引用
        cursor_idx = operands[0]
        sql_text = self._get_embedded_sql(operands)
        return f'DECLARE {variables[cursor_idx]} CURSOR FOR \\n    {sql_text};\\nOPEN {variables[cursor_idx]};'
    
    def restore_fetch(self, operands: bytes, variables: list) -> str:
        """还原 FETCH cursor INTO :var1, :var2, ..."""
        cursor_idx = operands[0]
        var_indices = operands[1:]
        var_names = [variables[i] for i in var_indices if i < len(variables)]
        return f'FETCH {variables[cursor_idx]} INTO :{", :".join(var_names)};'
    
    def restore_dynamic_sql(self, operands: bytes, sql_type: int) -> str:
        """还原动态 SQL (Type 1-4)。"""
        # Type 1: EXECUTE IMMEDIATE :sql_string;
        # Type 2: PREPARE stmt FROM :sql_string; EXECUTE stmt;
        # Type 3: PREPARE + DECLARE + OPEN (with descriptors)
        # Type 4: PREPARE + DECLARE + FETCH (with descriptors)
        ...
```

---

## 七、系统 Typedef 加载

### 7.1 TypedefLoader

PB 内置系统类型存储在 gzip 压缩的 .bin 文件中，按 PB 版本号命名。

```python
class TypedefLoader:
    """加载 PB 系统内置类型定义。
    
    文件命名: {version_hex}.bin (gzip 压缩)
    位置: PE 资源节中 RT_RCDATA (类型 10) 或嵌入 PBD
    版本映射: PB9=0x00c1(193), PB10=0x00ee(238), PB10.5=0x011b(283), PB11=0x013c(316)
    
    内容: 三层类型索引表
    - 0x0000-0x0FFF: 值类型 (int, long, string, date, time, datetime, blob, ...)
    - 0x4000-0x4FFF: 系统对象 (DataWindow, Transaction, Pipeline, ...)
    - 0x8000-0x8FFF: 用户定义类型 (在 PBD 中)
    """
    
    # 版本号 → hex 文件名
    VERSION_HEX = {
        193: "00c1",
        238: "00ee",
        283: "011b",
        316: "013c",
        333: "014d",
    }
    
    BUILTIN_TYPES = {
        # 值类型 (0x0000-0x0FFF)
        0: ("int", "Integer"),
        1: ("uint", "UnsignedInteger"),
        2: ("long", "Long"),
        3: ("ulong", "UnsignedLong"),
        4: ("real", "Real"),
        5: ("double", "Double"),
        6: ("decimal", "Decimal"),
        7: ("string", "String"),
        8: ("boolean", "Boolean"),
        9: ("date", "Date"),
        10: ("time", "Time"),
        11: ("datetime", "DateTime"),
        12: ("blob", "Blob"),
        13: ("char", "Char"),
        14: ("byte", "Byte"),
        15: ("any", "Any"),
        
        # 系统类型 (0x4000-0x4FFF)
        0x4000: ("datawindow", "DataWindow"),
        0x4001: ("transaction", "Transaction"),
        0x4002: ("pipeline", "Pipeline"),
        0x4003: ("menu", "Menu"),
        0x4004: ("window", "Window"),
        0x4005: ("userobject", "UserObject"),
        0x4006: ("function", "Function"),
        0x4007: ("structure", "Structure"),
        # ... 更多系统类型
    }
    
    def __init__(self, pe_path: str|Path|None = None, bin_data: bytes|None = None):
        self.pe_path = pe_path
        self.bin_data = bin_data
        self._typedef_cache: dict[int, PBTypeDef] = {}
    
    def load_for_version(self, pcode_version: int) -> dict[int, PBTypeDef]:
        """加载指定 PB 版本的系统类型定义。"""
        if pcode_version in self._typedef_cache:
            return self._typedef_cache
        
        # 1. 从 PE 文件提取或直接使用 bin_data
        raw = self._extract_typedef_bin(pcode_version)
        if not raw:
            # 回退到内置类型表
            return self._load_builtin_types()
        
        # 2. gzip 解压
        import gzip
        try:
            data = gzip.decompress(raw)
        except Exception:
            return self._load_builtin_types()
        
        # 3. 解析类型定义表
        return self._parse_typedef_table(data)
    
    def _extract_typedef_bin(self, pcode_version: int) -> bytes|None:
        """从 PE 资源节提取 typedef .bin。"""
        # 从 EXE/DLL 的 RT_RCDATA 资源中查找
        # 资源名 = "{version_hex}.bin"
        # 例如 PB12.6 (version=333): "014d.bin"
        ...
    
    def _parse_typedef_table(self, data: bytes) -> dict[int, PBTypeDef]:
        """解析类型定义二进制表。"""
        # 格式: [count] [entry1] [entry2] ...
        # 每个 entry: [type_index] [name_len] [name] [ancestor_index] [method_count] [methods...]
        ...
```

---

## 八、实施计划

### Phase 1: ChunkEngine 重构 (预计 3-4 小时) ✅

- [x] 从 `pbl_parser.py` 提取 chunk 逻辑到 `chunk_engine.py`
- [x] ~~修复 ENT* comment 字段解析~~ → 已证实 ENT* 无 comment 字段，更正设计文档
- [x] 放宽 ENT* version 验证 (支持任意版本号)
- [x] 支持内存模式 (BytesIO) 用于 PE 提取的子流
- [x] 添加 PB 版本检测
- [x] 重构 PBLParser 为 ChunkEngine 门面（100% API 向后兼容）
- [x] 49 单元测试通过 + 34 个真实 PBL 验证 (1649 entries)

### Phase 2: PEExtractor (预计 2-3 小时) ✅

- [x] 实现 DOS/PE/COFF/Optional Header 解析 (PE32 + PE32+)
- [x] 实现 Section Table → RVA → File Offset 转换
- [x] 实现 Resource Directory 三层树遍历 (Type → ID → Language → Data Entry)
- [x] 识别 PB 嵌入 PBD 资源 (HDR* 签名验证)
- [x] 与 ChunkEngine 集成 (内存模式 data=bytes)
- [x] 编写测试 (19 个合成 PE 测试 + 真实 PBD 验证)

### Phase 3: BinaryEntryParser (预计 4-5 小时)

- [ ] 实现编译对象 header 解析
- [ ] 实现变量解析 (PB5/PB6+ 结构差异)
- [ ] 实现函数定义解析
- [ ] 实现继承层次解析
- [ ] 实现类型索引解析
- [ ] 编写测试 (解析编译后的 .win/.dwo 对象)

### Phase 4: P-Code 反编译引擎 (预计 8-10 小时)

- [ ] 定义 4 个版本的指令长度表和操作码映射
- [ ] 实现 InstructionDecoder (字节流 → CodeLine)
- [ ] 实现 ControlFlowAnalyzer (控制流结构识别)
- [ ] 实现 PowerScriptDecompiler (指令 → PowerScript)
- [ ] 实现 SQLRestorer (SQL 操作码还原)
- [ ] 编写端到端测试 (编译对象 → PowerScript)

### Phase 5: UniversalParser 集成 (预计 2-3 小时)

- [ ] 实现自动格式检测 (HDR*/MZ)
- [ ] 统一 API: entries / export_source / parse_binary / decompile
- [ ] 集成 CLI 命令: `pb list --all`, `pb decompile <target> <entry>`
- [ ] 编写集成测试

### Phase 6: TypedefLoader + 完善文档 (预计 2 小时)

- [ ] 实现 PE 资源节 typedef .bin 提取
- [ ] 实现类型定义表解析
- [ ] 完善 API 文档
- [ ] 更新 SKILL.md

---

## 九、向后兼容策略

### 9.1 现有 API 不变

```python
# v1.3 代码继续正常工作
from pb_devkit import PBLParser, PBLBatchExporter

with PBLParser("app.pbl") as parser:
    entries = parser.list_entries()
    sources = parser.export_all()

# v2.0 新增能力
from pb_devkit.universal_parser import UniversalParser

up = UniversalParser("app.pbd")
up.open()

# 统一 API
for entry in up.entries:
    if entry.is_source:
        src = up.export_source(entry)
    else:
        binary = up.parse_binary(entry)
        if binary:
            script = up.decompile(binary)

up = UniversalParser("app.exe")  # 也支持 EXE
up.open()
```

### 9.2 CLI 扩展

```bash
# 现有命令不变
pb list app.pbl
pb export app.pbl ./out

# 新增命令
pb list app.pbd              # 列出编译库对象
pb list app.exe              # 列出 EXE 中嵌入的对象
pb decompile app.pbd w_main  # 反编译指定对象
pb inspect app.pbd d_emp     # 查看编译对象结构 (变量/函数/类型)
pb extract app.exe ./pbd_out # 提取 EXE 中的 PBD 资源
```

---

## 十、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| PE 资源节格式变体 | EXE 解析失败 | 严格参考 PbdViewer PEHelper.cs (1381 行)，覆盖多种 PE 变体 |
| P-code 指令集不完整 | 反编译失败/乱码 | 未知操作码输出注释行 `// OP_xxx`，不中断 |
| typedef .bin 位置不确定 | 类型名解析失败 | 回退到内置类型表 (BUILTIN_TYPES)，功能降级不中断 |
| ANSI PBL comment 编码 | 中文注释乱码 | 尝试 latin-1 → cp1252 → gbk → utf-8 编码链 |
| 编译对象内部结构未完全逆向 | 部分字段解析错误 | 标记为 "unknown"，不影响其他字段 |

---

## 附录 A: 参考项目

| 项目 | 语言 | 关键文件 | 说明 |
|------|------|---------|------|
| [PbdViewer](https://github.com/nario-ai/PbdViewer) | C# | PbFile.cs, PEHelper.cs, PbEntry.cs, PCodeParser90/100/105/110.cs | EXE+PBD+P-code 完整实现 |
| [PbdCli](https://github.com/nario-ai/PbdCli) | Python | pbdcli.py (2174 行) | PbdViewer 的 Python 移植，零依赖 |

## 附录 B: PBL/PBD 格式对比

| 特性 | PBL (源码库) | PBD (编译库) |
|------|-------------|-------------|
| HDR* 签名 | HDR* | HDR* |
| Chunk 结构 | 相同 | 相同 |
| ENT* 内容 | .sr* 源码文本 | .win/.dwo 等编译二进制 |
| DAT* 编码 | UTF-16LE (PB12+) 或 ANSI | P-code 字节码 |
| Comment 字段 | 含类型关键字 | 含类型关键字 |
| 可导出 | 源码文本 | 编译二进制 (需反编译) |
| 用途 | 开发时 | 运行时 (机器码加速) |

## 附录 C: 测试验证

```python
# 使用 datasync.pbl (PB12.6, 1649 entries) 验证
from pb_devkit.universal_parser import UniversalParser

up = UniversalParser(r"F:\workspace\X6\3.5\datasync\datasync.pbl")
up.open()

# 验证: entries 数量应与 v1.3 一致 (1649)
assert len(up.entries) == 1649

# 验证: comment 字段不为空 (v1.3 遗漏修复)
comments = [e for e in up.entries if e.comment]
assert len(comments) > 0  # 至少有部分对象有注释

# 验证: 所有 entry 的类型检测正确
for e in up.entries:
    assert e.object_type != PBObjectType.BINARY or e.extension == ".bin"
```

---

## 附录 D: 版本路线图

```
v1.3 (已完成) ─── Python PBL 源码解析，49 个单元测试
      │
      ▼
v1.4-v1.9 (Python) ─── 通用解析能力渐进增强
      │
      ├─ Phase 1: ChunkEngine 重构 (ENT* comment 修复 + 内存模式)
      ├─ Phase 2: PEExtractor (EXE/DLL → PBD 提取)
      ├─ Phase 3: BinaryEntryParser (编译对象结构解析)
      ├─ Phase 4: P-Code 反编译引擎 (PB9-PB11+ 四版本指令集)
      ├─ Phase 5: UniversalParser 集成 (统一入口)
      └─ Phase 6: TypedefLoader + 文档完善
      │
      ▼
v1.x 稳定版 (Python) ─── 格式验证完毕，全功能可用
      │
      ▼
v2.0 (Rust) ─── 全新重写，性能重构
      ├─ 纯 Rust CLI (零 Python 依赖)
      ├─ PyO3 扩展 (可选，供 Python 生态调用)
      ├─ 跨平台编译 (Windows/Linux/macOS)
      └─ 批量处理优化 (数百 PBL/PBD 并行)
```

### 技术选型理由

| 维度 | v1.x Python | v2.0 Rust |
|------|------------|-----------|
| **目标** | 格式验证 + 功能完整 | 性能极致 + 生产部署 |
| **依赖** | 零外部依赖 (stdlib only) | 零外部依赖 (no_std 可选) |
| **性能** | I/O 密集，秒级可接受 | CPU 密集，毫秒级响应 |
| **分发** | `pip install -e .` | 编译二进制 / PyO3 wheel |
| **适用** | 开发/调试/单文件分析 | 批量处理/IDE 集成/实时反编译 |
