import hashlib
import struct
from typing import List, Dict, Tuple, Union

from utils.dev_paths import get_dev_path

class SCXorShift32:
    """XorShift32随机数生成器，用于加密/解密数据"""
    def __init__(self, seed: int):
        # 确保使用无符号整数
        seed = seed & 0xFFFFFFFF
        # 根据seed的popcount进行多次XorshiftAdvance
        pop_count = self.popcount(seed)
        self.seed = seed
        for _ in range(pop_count):
            self.seed = self.xorshift_advance(self.seed)
        
        self.counter = 0
    
    def next(self) -> int:
        """生成下一个随机字节"""
        c = self.counter
        result = (self.seed >> (c << 3)) & 0xFF
        if c == 3:
            self.seed = self.xorshift_advance(self.seed)
            self.counter = 0
        else:
            self.counter += 1
        return result
    
    def next32(self) -> int:
        """生成下一个32位随机数"""
        return self.next() | (self.next() << 8) | (self.next() << 16) | (self.next() << 24)
    
    @staticmethod
    def xorshift_advance(state: int) -> int:
        """XorShift算法的核心实现，使用无符号整数"""
        state = state & 0xFFFFFFFF  # 确保是无符号整数
        state ^= (state << 2) & 0xFFFFFFFF
        state ^= (state >> 15) & 0xFFFFFFFF
        state ^= (state << 13) & 0xFFFFFFFF
        return state & 0xFFFFFFFF
    
    @staticmethod
    def popcount(x: int) -> int:
        """计算整数中设置的位数，使用无符号整数"""
        x = x & 0xFFFFFFFF  # 确保是无符号整数
        x -= (x >> 1) & 0x55555555
        x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
        x = (x + (x >> 4)) & 0x0F0F0F0F
        x += x >> 8
        x += x >> 16
        return x & 0x3F

class SCBlock:
    """处理块数据的读写逻辑"""
    def __init__(self, key: int, block_type: str = "Object", data: bytes = None, sub_type: str = None):
        self.Key = key
        self.Type = block_type
        self.data = bytearray(data) if data else bytearray()
        self.SubType = sub_type
        self.Offset = 0
    
    def get_value(self, data_type: str) -> Union[int, float, bool, bytes]:
        """从块数据中读取值"""
        if data_type == "Bool1":
            return self.data[self.Offset] != 0
        elif data_type == "Bool2":
            return self.data[self.Offset] != 0
        elif data_type == "Byte":
            value = self.data[self.Offset]
            self.Offset += 1
            return value
        elif data_type == "UInt16":
            value = struct.unpack_from('<H', self.data, self.Offset)[0]
            self.Offset += 2
            return value
        elif data_type == "UInt32":
            value = struct.unpack_from('<I', self.data, self.Offset)[0]
            self.Offset += 4
            return value
        elif data_type == "Int32":
            value = struct.unpack_from('<i', self.data, self.Offset)[0]
            self.Offset += 4
            return value
        elif data_type == "Single":
            value = struct.unpack_from('<f', self.data, self.Offset)[0]
            self.Offset += 4
            return value
        elif data_type == "Object":
            # 对于对象类型，我们需要知道大小
            # 这里简化处理，假设我们已经知道大小
            size = len(self.data) - self.Offset
            value = bytes(self.data[self.Offset:self.Offset + size])
            self.Offset += size
            return value
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def set_value(self, data_type: str, value: Union[int, float, bool, bytes]):
        """向块数据中写入值"""
        if data_type == "Bool1" or data_type == "Bool2":
            self.data[self.Offset] = 1 if value else 0
            self.Offset += 1
        elif data_type == "Byte":
            self.data[self.Offset] = value & 0xFF
            self.Offset += 1
        elif data_type == "UInt16":
            struct.pack_into('<H', self.data, self.Offset, value & 0xFFFF)
            self.Offset += 2
        elif data_type == "UInt32":
            struct.pack_into('<I', self.data, self.Offset, value & 0xFFFFFFFF)
            self.Offset += 4
        elif data_type == "Int32":
            struct.pack_into('<i', self.data, self.Offset, value)
            self.Offset += 4
        elif data_type == "Single":
            struct.pack_into('<f', self.data, self.Offset, value)
            self.Offset += 4
        elif data_type == "Object":
            if isinstance(value, (bytes, bytearray)):
                self.data[self.Offset:self.Offset + len(value)] = value
                self.Offset += len(value)
            else:
                raise ValueError("Object type requires bytes or bytearray")
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def write_block(self) -> bytes:
        """加密块数据"""
        result = bytearray()
        rng = SCXorShift32(self.Key)
        
        # 写入块键
        result.extend(struct.pack('<I', self.Key))
        
        # 写入块类型（加密）
        type_code = self.get_type_code(self.Type)
        result.append(type_code ^ rng.next())
        
        # 根据类型写入额外信息
        if self.Type == "Object":
            # 写入对象大小（加密）
            # 使用有符号整数，与PKHeX实现一致
            result.extend(struct.pack('<i', len(self.data) ^ rng.next32()))
        elif self.Type == "Array":
            # 写入条目数（加密）
            sub_type_code = self.get_type_code(self.SubType)
            entry_size = self.get_type_size(sub_type_code)
            num_entries = len(self.data) // entry_size
            # 使用有符号整数，与PKHeX实现一致
            result.extend(struct.pack('<i', num_entries ^ rng.next32()))
            # 写入子类型（加密）
            result.append(sub_type_code ^ rng.next())
        
        # 加密并写入数据
        for b in self.data:
            result.append(b ^ rng.next())
        
        return bytes(result)
    
    @staticmethod
    def read_from_offset(data: bytes, offset: int) -> Tuple['SCBlock', int]:
        """从偏移量解密块数据"""
        # 读取块键
        if offset + 4 > len(data):
            print(f"调试：在偏移量 {offset} 处无法读取块键，数据长度不足")
            return None, offset
        key = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        
        # 初始化XorShift32
        rng = SCXorShift32(key)
        
        # 读取块类型（解密）
        if offset >= len(data):
            print(f"调试：在偏移量 {offset} 处无法读取块类型，数据长度不足")
            return None, offset
        type_code = data[offset] ^ rng.next()
        offset += 1
        
        block_type = SCBlock.get_type_name(type_code)
        
        # 如果类型无法识别或者是None类型，跳过此块
        if block_type is None or block_type == "None":
            print(f"调试：跳过无效类型 {block_type} (代码: {type_code})，键: 0x{key:08X}")
            return None, offset
        
        # 调试信息：打印所有块的键和类型
        print(f"调试：读取块，键: 0x{key:08X}, 类型: {block_type} (代码: {type_code}), 偏移量: {offset}")
        
        # 特别关注KBox或KParty的键值
        if key == 0x0D66012C or key == 0x2985FE5D:  # KBox或KParty的键值
            print(f"调试：*** 找到目标块键 0x{key:08X}, 类型: {block_type} (代码: {type_code}) ***")
        
        # 根据类型读取额外信息
        if block_type == "Bool1" or block_type == "Bool2" or block_type == "Bool3":
            # 布尔类型没有额外数据
            return SCBlock(key, block_type), offset
        
        elif block_type == "Object":
            # 读取对象大小（解密）
            if offset + 4 > len(data):
                print(f"调试：在偏移量 {offset} 处无法读取Object块大小，数据长度不足")
                return None, offset
            # 使用无符号整数，与PKHeX实现一致
            encrypted_size = struct.unpack_from('<I', data, offset)[0]
            xor_value = rng.next32()
            # 直接进行XOR运算，与PKHeX实现一致
            num_bytes = encrypted_size ^ xor_value
            offset += 4
            
            # 调试信息：对于所有Object块，打印大小信息
            print(f"调试：Object块 0x{key:08X} 加密大小: 0x{encrypted_size:08X} ({encrypted_size})")
            print(f"调试：Object块 0x{key:08X} XOR值: 0x{xor_value:08X} ({xor_value})")
            print(f"调试：Object块 0x{key:08X} 解密后大小: {num_bytes} 字节")
            
            # 检查大小是否合理
            if num_bytes <= 0 or num_bytes > len(data) - offset:
                print(f"调试：Object块 0x{key:08X} 大小 {num_bytes} 不合理，跳过此块")
                return None, offset
            
            # 读取对象数据
            if offset + num_bytes > len(data):
                print(f"调试：在偏移量 {offset} 处无法读取Object块数据，需要 {num_bytes} 字节，但只有 {len(data) - offset} 字节可用")
                return None, offset
            arr = bytearray(data[offset:offset + num_bytes])
            offset += num_bytes
            
            print(f"调试：Object块 0x{key:08X} 数据读取完成，新偏移量: {offset}")
            
            # 解密数据
            for i in range(len(arr)):
                arr[i] ^= rng.next()
            
            # 如果是KParty块，输出前32字节用于调试
            if key == 0x2985FE5D:
                print(f"调试：KParty块前32字节数据:")
                for i in range(min(32, len(arr))):
                    print(f"{arr[i]:02X} ", end="")
                    if (i + 1) % 16 == 0:
                        print()
                print()
            
            return SCBlock(key, block_type, arr), offset
        
        elif block_type == "Array":
            print(f"调试：处理Array类型块，当前偏移量: {offset}")
            
            # 读取条目数（解密）
            if offset + 4 > len(data):
                print(f"调试：在偏移量 {offset} 处无法读取Array块条目数，数据长度不足")
                return None, offset
            # 使用无符号整数读取加密条目数，与PKHeX实现一致
            encrypted_entries = struct.unpack_from('<I', data, offset)[0]
            xor_value = rng.next32()
            # 直接进行XOR运算
            num_entries = encrypted_entries ^ xor_value
            offset += 4
            
            print(f"调试：Array块加密条目数: 0x{encrypted_entries:08X} ({encrypted_entries})")
            print(f"调试：Array块XOR值: 0x{xor_value:08X} ({xor_value})")
            print(f"调试：Array块解密后条目数: {num_entries}")
            
            # 检查条目数是否合理
            if num_entries <= 0 or num_entries > 1000000:  # 设置一个合理的上限
                print(f"调试：Array块 0x{key:08X} 条目数 {num_entries} 不合理，跳过此块")
                return None, offset
            
            # 读取子类型（解密）
            if offset >= len(data):
                print(f"调试：在偏移量 {offset} 处无法读取Array块子类型，数据长度不足")
                return None, offset
            sub_type_code = data[offset] ^ rng.next()
            offset += 1
            
            sub_type = SCBlock.get_type_name(sub_type_code)
            print(f"调试：Array块子类型: {sub_type} (代码: {sub_type_code})")
            
            # 计算字节数
            entry_size = SCBlock.get_type_size(sub_type_code)
            if entry_size == 0:
                print(f"调试：Array块子类型 {sub_type} (代码: {sub_type_code}) 的大小为0，使用默认大小1字节")
                entry_size = 1
            
            num_bytes = num_entries * entry_size
            print(f"调试：Array块总数据大小: {num_bytes} 字节 ({num_entries} * {entry_size})")
            
            # 检查是否是KBox或KParty块的大小
            if num_bytes == 330240:
                print(f"调试：*** Array块大小匹配KBox (330240字节)! ***")
            if num_bytes == 2068:
                print(f"调试：*** Array块大小匹配KParty (2068字节)! ***")
            
            # 检查数据大小是否合理
            if num_bytes < 0 or num_bytes > len(data) - offset:
                print(f"调试：Array块数据大小 {num_bytes} 不合理，可能解密错误")
                return None, offset
            
            # 读取数组数据
            if offset + num_bytes > len(data):
                print(f"调试：在偏移量 {offset} 处无法读取Array块数据，需要 {num_bytes} 字节，但只有 {len(data) - offset} 字节可用")
                return None, offset
            arr = bytearray(data[offset:offset + num_bytes])
            offset += num_bytes
            
            print(f"调试：Array块数据读取完成，新偏移量: {offset}")
            
            # 解密数据
            for i in range(len(arr)):
                arr[i] ^= rng.next()
            
            return SCBlock(key, block_type, arr, sub_type), offset
        
        else:  # 单值类型或Unknown类型
            # 计算字节数
            num_bytes = SCBlock.get_type_size(type_code)
            
            # 如果是Unknown类型，尝试使用默认大小1字节
            if block_type == "Unknown":
                print(f"调试：遇到Unknown类型块 (代码: {type_code})，尝试使用默认大小1字节")
                num_bytes = 1
            
            print(f"调试：读取{block_type}类型块，数据大小: {num_bytes}字节")
            
            # 读取数据
            if offset + num_bytes > len(data):
                print(f"调试：在偏移量 {offset} 处无法读取{num_bytes}字节数据，数据长度不足")
                return None, offset
            arr = bytearray(data[offset:offset + num_bytes])
            offset += num_bytes
            
            # 解密数据
            for i in range(len(arr)):
                arr[i] ^= rng.next()
            
            print(f"调试：成功读取{block_type}类型块，新偏移量: {offset}")
            
            return SCBlock(key, block_type, arr), offset
    
    @staticmethod
    def get_type_code(type_name: str) -> int:
        """根据类型名称获取类型代码"""
        type_codes = {
            "None": 0,
            "Bool1": 1,
            "Bool2": 2,
            "Bool3": 3,
            "Object": 4,
            "Array": 5,
            "Byte": 8,
            "UInt16": 9,
            "UInt32": 10,
            "UInt64": 11,
            "SByte": 12,
            "Int16": 13,
            "Int32": 14,
            "Int64": 15,
            "Single": 16,
            "Double": 17
        }
        return type_codes.get(type_name, 0)
    
    @staticmethod
    def get_type_name(type_code: int) -> str:
        """根据类型代码获取类型名称"""
        type_names = {
            0: "None",
            1: "Bool1",
            2: "Bool2",
            3: "Bool3",
            4: "Object",
            5: "Array",
            8: "Byte",
            9: "UInt16",
            10: "UInt32",
            11: "UInt64",
            12: "SByte",
            13: "Int16",
            14: "Int32",
            15: "Int64",
            16: "Single",
            17: "Double"
        }
        return type_names.get(type_code, None)  # 返回None而不是"Unknown"，以便跳过无效类型
    
    @staticmethod
    def get_type_size(type_code: int) -> int:
        """根据类型代码获取类型大小"""
        type_sizes = {
            0: 0,  # None
            1: 1,  # Bool1
            2: 1,  # Bool2
            3: 1,  # Bool3
            4: 0,  # Object (大小在数据中指定)
            5: 0,  # Array (大小在数据中指定)
            8: 1,  # Byte
            9: 2,  # UInt16
            10: 4, # UInt32
            11: 8, # UInt64
            12: 1, # SByte
            13: 2, # Int16
            14: 4, # Int32
            15: 8, # Int64
            16: 4, # Single
            17: 8  # Double
        }
        
        size = type_sizes.get(type_code, 1)  # 为未知类型代码提供默认大小1字节
        if type_code not in type_sizes:
            print(f"调试：未知类型代码 {type_code}，使用默认大小1字节")
        
        return size

class SwishCrypto:
    """主要的加密/解密类"""
    def __init__(self):
        # 根据C#实现，使用固定的StaticXorpad
        self.static_xorpad = bytes([
            0xA0, 0x92, 0xD1, 0x06, 0x07, 0xDB, 0x32, 0xA1, 0xAE, 0x01, 0xF5, 0xC5, 0x1E, 0x84, 0x4F, 0xE3,
            0x53, 0xCA, 0x37, 0xF4, 0xA7, 0xB0, 0x4D, 0xA0, 0x18, 0xB7, 0xC2, 0x97, 0xDA, 0x5F, 0x53, 0x2B,
            0x75, 0xFA, 0x48, 0x16, 0xF8, 0xD4, 0x8A, 0x6F, 0x61, 0x05, 0xF4, 0xE2, 0xFD, 0x04, 0xB5, 0xA3,
            0x0F, 0xFC, 0x44, 0x92, 0xCB, 0x32, 0xE6, 0x1B, 0xB9, 0xB1, 0x2E, 0x01, 0xB0, 0x56, 0x53, 0x36,
            0xD2, 0xD1, 0x50, 0x3D, 0xDE, 0x5B, 0x2E, 0x0E, 0x52, 0xFD, 0xDF, 0x2F, 0x7B, 0xCA, 0x63, 0x50,
            0xA4, 0x67, 0x5D, 0x23, 0x17, 0xC0, 0x52, 0xE1, 0xA6, 0x30, 0x7C, 0x2B, 0xB6, 0x70, 0x36, 0x5B,
            0x2A, 0x27, 0x69, 0x33, 0xF5, 0x63, 0x7B, 0x36, 0x3F, 0x26, 0x9B, 0xA3, 0xED, 0x7A, 0x53, 0x00,
            0xA4, 0x48, 0xB3, 0x50, 0x9E, 0x14, 0xA0, 0x52, 0xDE, 0x7E, 0x10, 0x2B, 0x1B, 0x77, 0x6E
        ])
        
        self.intro_hash_bytes = bytes([
            0x9E, 0xC9, 0x9C, 0xD7, 0x0E, 0xD3, 0x3C, 0x44, 0xFB, 0x93, 0x03, 0xDC, 0xEB, 0x39, 0xB4, 0x2A,
            0x19, 0x47, 0xE9, 0x63, 0x4B, 0xA2, 0x33, 0x44, 0x16, 0xBF, 0x82, 0xA2, 0xBA, 0x63, 0x55, 0xB6,
            0x3D, 0x9D, 0xF2, 0x4B, 0x5F, 0x7B, 0x6A, 0xB2, 0x62, 0x1D, 0xC2, 0x1B, 0x68, 0xE5, 0xC8, 0xB5,
            0x3A, 0x05, 0x90, 0x00, 0xE8, 0xA8, 0x10, 0x3D, 0xE2, 0xEC, 0xF0, 0x0C, 0xB2, 0xED, 0x4F, 0x6D
        ])
        
        self.outro_hash_bytes = bytes([
            0xD6, 0xC0, 0x1C, 0x59, 0x8B, 0xC8, 0xB8, 0xCB, 0x46, 0xE1, 0x53, 0xFC, 0x82, 0x8C, 0x75, 0x75,
            0x13, 0xE0, 0x45, 0xDF, 0x32, 0x69, 0x3C, 0x75, 0xF0, 0x59, 0xF8, 0xD9, 0xA2, 0x5F, 0xB2, 0x17,
            0xE0, 0x80, 0x52, 0xDB, 0xEA, 0x89, 0x73, 0x99, 0x75, 0x79, 0xAF, 0xCB, 0x2E, 0x80, 0x07, 0xE6,
            0xF1, 0x26, 0xE0, 0x03, 0x0A, 0xE6, 0x6F, 0xF6, 0x41, 0xBF, 0x7E, 0x59, 0xC2, 0xAE, 0x55, 0xFD
        ])
        
        self.hash_size = 0x20  # SHA256哈希大小
    
    def crypt_static_xorpad_bytes(self, data: bytearray) -> None:
        """使用StaticXorpad解密/加密数据（除了最后的哈希部分）"""
        data_region_len = len(data) - self.hash_size if len(data) > self.hash_size else len(data)
        print(f"调试：数据区域大小: {data_region_len}, 哈希大小: {self.hash_size}")
        
        # 添加调试信息：显示解密前的前32字节
        print("调试：解密前的前32字节:")
        for i in range(min(32, data_region_len)):
            print(f"{data[i]:02X} ", end="")
            if (i + 1) % 16 == 0: print()
        print()
        
        # 添加调试信息：显示StaticXorpad的前32字节
        print("调试：StaticXorpad的前32字节:")
        for i in range(min(32, len(self.static_xorpad))):
            print(f"{self.static_xorpad[i]:02X} ", end="")
            if (i + 1) % 16 == 0: print()
        print()
        
        # 执行XOR解密
        for i in range(data_region_len):
            data[i] ^= self.static_xorpad[i % len(self.static_xorpad)]
            
        # 添加调试信息：显示解密后的前32字节
        print("调试：解密后的前32字节:")
        for i in range(min(32, data_region_len)):
            print(f"{data[i]:02X} ", end="")
            if (i + 1) % 16 == 0: print()
        print()
    
    def compute_hash(self, data: bytes) -> bytes:
        """计算SHA256哈希"""
        # 创建哈希输入：IntroHashBytes + data（不包括最后的哈希） + OutroHashBytes
        hash_input = self.intro_hash_bytes + data[:-self.hash_size] + self.outro_hash_bytes
        return hashlib.sha256(hash_input).digest()
    
    def get_is_hash_valid(self, data: bytes) -> bool:
        """检查文件哈希是否有效"""
        computed_hash = self.compute_hash(data)
        stored_hash = data[-self.hash_size:]
        return computed_hash == stored_hash
    
    def decrypt(self, data: bytes) -> Tuple[bytes, Dict[str, SCBlock]]:
        """解密数据"""
        if len(data) < 8:
            return data, {}
        
        # 首先检查哈希是否有效
        if not self.get_is_hash_valid(data):
            print("警告：文件哈希无效，可能不是有效的保存文件")
        
        # 创建数据的可写副本
        decrypted = bytearray(data)
        
        # 使用StaticXorpad解密数据（除了最后的哈希部分）
        self.crypt_static_xorpad_bytes(decrypted)
        
        # 读取块
        blocks = {}
        offset = 0
        
        # 只处理除哈希外的数据区域
        data_region = decrypted[:-self.hash_size] if len(decrypted) > self.hash_size else decrypted
        
        # 调试：打印数据区域前4字节
        print(f"调试：读取块前数据区域前4字节: {' '.join(f'{b:02X}' for b in data_region[:4])}")
        
        # 使用BlockDataRatioEstimate2初始化列表容量（与PKHeX一致）
        block_data_ratio_estimate2 = 555  # 每个块的平均字节数
        estimated_block_count = len(data_region) // block_data_ratio_estimate2
        
        print(f"估计块数量: {estimated_block_count}")
        
        # 记录处理块的数量，用于调试
        block_count = 0
        
        # 记录尝试跳过的次数，避免无限循环
        skip_attempts = 0
        max_skip_attempts = 100
        
        # 添加调试信息：记录KParty和KBox块的查找状态
        kparty_found = False
        kbox_found = False
        
        # 修改块读取逻辑，使其更接近PKHeX的实现
        # 不使用块数量估计，而是处理所有数据直到结束
        while offset < len(data_region):
            # 记录当前偏移量作为块的起始位置
            block_start_offset = offset
            
            # 检查是否有足够的数据读取块键（4字节）和类型（1字节）
            if offset + 5 > len(data_region):
                print(f"调试：在偏移量 {offset} 处数据不足，无法读取块键和类型，结束读取")
                break
                
            block, new_offset = SCBlock.read_from_offset(data_region, offset)
            
            if block is None:
                # 如果块为None，跳过4个字节（块键大小）以尝试找到下一个可能的块
                skip_attempts += 1
                if skip_attempts > max_skip_attempts:
                    print(f"调试：跳过次数超过最大限制({max_skip_attempts})，重置计数器")
                    skip_attempts = 0  # 重置计数器，继续尝试
                offset += 4  # 跳过4个字节（块键大小）
                print(f"调试：遇到无效块，跳过4个字节，新偏移量: {offset}")
                continue
            
            if new_offset <= offset:
                # 如果偏移量没有更新，尝试跳过1个字节
                skip_attempts += 1
                if skip_attempts > max_skip_attempts:
                    print(f"调试：跳过次数超过最大限制({max_skip_attempts})，重置计数器")
                    skip_attempts = 0  # 重置计数器，继续尝试
                offset += 1  # 只跳过1个字节，避免跳过可能的块
                print(f"调试：块解析失败，尝试跳过1个字节，新偏移量: {offset}")
                continue
            
            # 成功解析一个块
            offset = new_offset
            blocks[f"0x{block.Key:08X}"] = block
            
            # 检查是否找到KParty或KBox块
            if block.Key == 0x2985FE5D:  # KParty的键值
                kparty_found = True
                print(f"调试：*** 找到KParty块! Key=0x{block.Key:08X}, Type={block.Type}, DataSize={len(block.data)} 字节 ***")
            elif block.Key == 0x0D66012C:  # KBox的键值
                kbox_found = True
                print(f"调试：*** 找到KBox块! Key=0x{block.Key:08X}, Type={block.Type}, DataSize={len(block.data)} 字节 ***")
            
            # 记录块的偏移量（使用块在数据区域中的起始位置）
            block.Offset = block_start_offset
            
            # 增加块计数
            block_count += 1
            
            # 每处理100个块打印一次进度
            if block_count % 100 == 0:
                print(f"调试：已处理 {block_count} 个块，当前偏移量: {offset}/{len(data_region)}")
            
            # 如果块数量超过real main中的块数量(5184)很多，提前结束循环
            if block_count > 6000:
                print(f"调试：块数量({block_count})超过预期，提前结束循环")
                break
            
            # 清除跳过计数器
            skip_attempts = 0
            
            # 不提前结束循环，尝试读取所有可能的块
            # 移除这个提前结束的条件，确保读取到所有块
        
        # 添加调试信息：打印剩余未处理数据
        remaining_data = len(data_region) - offset
        print(f"调试：读取块完成，总共读取 {block_count} 个块，最终偏移量: {offset}/{len(data_region)}")
        print(f"调试：剩余未处理数据: {remaining_data} 字节 (包括 {self.hash_size} 字节哈希)")
        
        # 添加调试信息：确认KParty和KBox块的查找状态
        print(f"调试：KParty块查找状态: {'找到' if kparty_found else '未找到'}")
        print(f"调试：KBox块查找状态: {'找到' if kbox_found else '未找到'}")
        
        # 返回解密后的数据区域（不包括哈希部分）
        return bytes(data_region), blocks
    
    def encrypt(self, blocks: Dict[str, SCBlock]) -> bytes:
        """加密数据"""
        # 估计块数据大小
        block_data_ratio_estimate = 777  # 每个块的平均字节数
        result_size = len(blocks) * block_data_ratio_estimate + self.hash_size
        
        # 创建内存流并写入块
        result = bytearray(result_size)
        offset = 0
        
        # 写入所有块
        for block_key, block in blocks.items():
            encrypted_block = block.write_block()
            if offset + len(encrypted_block) > len(result):
                # 如果空间不足，扩展结果数组
                result.extend(encrypted_block)
            else:
                result[offset:offset + len(encrypted_block)] = encrypted_block
            offset += len(encrypted_block)
        
        # 截断到实际大小并添加哈希空间
        result = result[:offset + self.hash_size]
        
        # 使用StaticXorpad加密数据（除了最后的哈希部分）
        self.crypt_static_xorpad_bytes(result)
        
        # 计算并写入哈希
        computed_hash = self.compute_hash(result)
        result[-self.hash_size:] = computed_hash
        
        return bytes(result)

def decrypt_main_file(input_path: str, output_path: str) -> Tuple[bytes, Dict[str, SCBlock]]:
    """解密main文件"""
    # 读取文件
    with open(input_path, 'rb') as f:
        data = f.read()
    
    # 创建解密器
    crypto = SwishCrypto()
    
    # 解密数据
    decrypted_data, blocks = crypto.decrypt(data)
    
    # 保存解密后的数据
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)
    
    return decrypted_data, blocks

def extract_kbox_kparty(blocks: Dict[str, SCBlock], output_dir: str):
    """提取KBox和KParty块"""
    # 查找KBox和KParty块
    kbox_block = None
    kparty_block = None
    
    for block_key, block in blocks.items():
        if len(block.data) == 330240:  # KBox块大小
            kbox_block = block
            print(f"找到KBox块: {block_key}, 大小: {len(block.data)}字节")
        elif len(block.data) == 2068:  # KParty块大小
            kparty_block = block
            print(f"找到KParty块: {block_key}, 大小: {len(block.data)}字节")
    
    # 保存KBox块
    if kbox_block:
        with open(f"{output_dir}/KBoxData.bin", 'wb') as f:
            f.write(kbox_block.data)
        print(f"KBox数据已保存到 {output_dir}/KBoxData.bin")
    else:
        print("未找到KBox块")
    
    # 保存KParty块
    if kparty_block:
        with open(f"{output_dir}/KPartyData.bin", 'wb') as f:
            f.write(kparty_block.data)
        print(f"KParty数据已保存到 {output_dir}/KPartyData.bin")
    else:
        print("未找到KParty块")

def decrypt_block_at_offset(input_path: str, offset: int, output_dir: str) -> SCBlock:
    """直接跳转到特定偏移位置解密并提取数据"""
    # 读取文件
    with open(input_path, 'rb') as f:
        data = f.read()
    
    # 创建解密器
    crypto = SwishCrypto()
    
    # 首先检查哈希是否有效
    if not crypto.get_is_hash_valid(data):
        print("警告：文件哈希无效，可能不是有效的保存文件")
    
    # 创建数据的可写副本
    decrypted = bytearray(data)
    
    # 使用StaticXorpad解密数据（除了最后的哈希部分）
    crypto.crypt_static_xorpad_bytes(decrypted)
    
    # 只处理除哈希外的数据区域
    data_region = decrypted[:-crypto.hash_size] if len(decrypted) > crypto.hash_size else decrypted
    
    # 检查偏移量是否有效
    if offset < 0 or offset >= len(data_region):
        print(f"错误：偏移量 {offset} 超出数据区域范围 (0-{len(data_region)-1})")
        return None
    
    print(f"调试：尝试在偏移量 {offset} 处解密块")
    
    # 直接在指定偏移量处解密块
    block, new_offset = SCBlock.read_from_offset(data_region, offset)
    
    if block is None:
        print(f"调试：在偏移量 {offset} 处无法解密块")
        return None
    
    print(f"调试：成功在偏移量 {offset} 处解密块")
    print(f"调试：块信息 - 键: 0x{block.Key:08X}, 类型: {block.Type}, 数据大小: {len(block.data)} 字节")
    
    # 保存块数据
    os.makedirs(output_dir, exist_ok=True)
    
    if block.Key == 0x2985FE5D:  # KParty的键值
        output_path = f"{output_dir}/KPartyData_direct.bin"
        print(f"调试：找到KParty块，保存到 {output_path}")
    elif block.Key == 0x0D66012C:  # KBox的键值
        output_path = f"{output_dir}/KBoxData_direct.bin"
        print(f"调试：找到KBox块，保存到 {output_path}")
    else:
        output_path = f"{output_dir}/Block_0x{block.Key:08X}.bin"
        print(f"调试：找到其他块，保存到 {output_path}")
    
    with open(output_path, 'wb') as f:
        f.write(block.data)
    
    print(f"调试：块数据已保存到 {output_path}")
    
    return block

if __name__ == "__main__":
    input_file = get_dev_path("main_file_for_debug")
    output_dir = get_dev_path("real_main_output_dir")
    output_file = get_dev_path("main_decrypted_output", "")
    if not input_file or not output_dir:
        raise RuntimeError("请在 config/dev_paths.local.json 中配置 main_file_for_debug 和 real_main_output_dir")

    import os
    os.makedirs(output_dir, exist_ok=True)

    if not output_file:
        output_file = os.path.join(output_dir, "main_decrypted_python.bin")

    print(f"解密文件: {input_file}")
    print(f"输出文件: {output_file}")
    
    # 测试直接跳转到特定偏移位置解密块
    print("\n===== 测试直接跳转到特定偏移位置解密块 =====")
    
    # 根据blocks_info.json中的信息，KParty块的偏移量是572209，KBox块的偏移量是23710
    kparty_offset = 572209
    kbox_offset = 23710
    
    print(f"\n尝试直接解密KParty块（偏移量: {kparty_offset}）...")
    kparty_block = decrypt_block_at_offset(input_file, kparty_offset, output_dir)
    
    print(f"\n尝试直接解密KBox块（偏移量: {kbox_offset}）...")
    kbox_block = decrypt_block_at_offset(input_file, kbox_offset, output_dir)
    
    # 比较直接解密和完整解密的结果
    print("\n===== 比较直接解密和完整解密的结果 =====")
    
    # 检查直接解密的KParty块数据
    kparty_direct_path = f"{output_dir}/KPartyData_direct.bin"
    kparty_original_path = f"{output_dir}/KPartyData.bin"
    
    if os.path.exists(kparty_direct_path) and os.path.exists(kparty_original_path):
        with open(kparty_direct_path, 'rb') as f1, open(kparty_original_path, 'rb') as f2:
            direct_data = f1.read()
            original_data = f2.read()
            
            if direct_data == original_data:
                print("KParty块：直接解密和完整解密的结果一致")
            else:
                print(f"KParty块：直接解密和完整解密的结果不一致")
                print(f"直接解密大小: {len(direct_data)} 字节")
                print(f"完整解密大小: {len(original_data)} 字节")
    
    # 检查直接解密的KBox块数据
    kbox_direct_path = f"{output_dir}/KBoxData_direct.bin"
    kbox_original_path = f"{output_dir}/KBoxData.bin"
    
    if os.path.exists(kbox_direct_path) and os.path.exists(kbox_original_path):
        with open(kbox_direct_path, 'rb') as f1, open(kbox_original_path, 'rb') as f2:
            direct_data = f1.read()
            original_data = f2.read()
            
            if direct_data == original_data:
                print("KBox块：直接解密和完整解密的结果一致")
            else:
                print(f"KBox块：直接解密和完整解密的结果不一致")
                print(f"直接解密大小: {len(direct_data)} 字节")
                print(f"完整解密大小: {len(original_data)} 字节")
    
    # 注释掉完整解密过程，只测试直接跳转解密
    print("\n===== 跳过完整解密过程 =====")
    
    # 注释掉完整解密过程，只测试直接跳转解密
    # # 读取原始文件大小
    # # with open(input_file, 'rb') as f:
    #     original_data = f.read()
    # print(f"原始文件大小: {len(original_data)}字节")
    # 
    # # 创建解密器并检查哈希
    # crypto = SwishCrypto()
    # is_valid = crypto.get_is_hash_valid(original_data)
    # print(f"文件哈希有效性: {is_valid}")
    # 
    # # 解密文件
    # decrypted_data, blocks = decrypt_main_file(input_file, output_file)
    # 
    # print(f"解密完成，文件大小: {len(decrypted_data)}字节")
    # print(f"目标文件大小: 1,576,681字节")
    # print(f"找到 {len(blocks)} 个块")
    # 
    # # 查找KBox和KParty块
    # kbox_found = False
    # kparty_found = False
    # 
    # # 查找特定键值的块
    # kbox_key = "0x0D66012C"  # KBox的键值
    # kparty_key = "0x2985FE5D"  # KParty的键值
    # 
    # for block_key, block in blocks.items():
    #     if block_key == kbox_key:
    #         print(f"找到KBox块: {block_key}, 大小: {len(block.data)}字节")
    #         kbox_found = True
    #     elif block_key == kparty_key:
    #         print(f"找到KParty块: {block_key}, 大小: {len(block.data)}字节")
    #         kparty_found = True
    #     
    #     # 也检查大小
    #     if len(block.data) == 330240:  # KBox块大小
    #         print(f"找到大小匹配KBox的块: {block_key}, 大小: {len(block.data)}字节")
    #     elif len(block.data) == 2068:  # KParty块大小
    #         print(f"找到大小匹配KParty的块: {block_key}, 大小: {len(block.data)}字节")
    # 
    # if not kbox_found:
    #     print(f"未找到KBox块 (键值: {kbox_key})")
    # if not kparty_found:
    #     print(f"未找到KParty块 (键值: {kparty_key})")
    # 
    # # 提取KBox和KParty块
    # extract_kbox_kparty(blocks, output_dir)
    # 
    # # 保存块信息
    # blocks_info = []
    # for block_key, block in blocks.items():
    #     blocks_info.append({
    #         "Key": block_key,
    #         "Type": block.Type,
    #         "SubType": block.SubType if block.SubType else "None",
    #         "DataSize": len(block.data),
    #         "Offset": block.Offset,  # 使用实际计算的偏移量
    #         "Hash": hashlib.sha256(block.data).hexdigest().upper()
    #     })
    # 
    # import json
    # with open(f"{output_dir}/blocks_info.json", 'w') as f:
    #     json.dump(blocks_info, f, indent=2)
    # 
    # print(f"块信息已保存到 {output_dir}/blocks_info.json")
    # 
    # # 如果文件大小不匹配，保存前100个字节用于调试
    # if len(decrypted_data) != 1576681:
    #     print("保存解密文件的前100字节用于调试:")
    #     with open(f"{output_dir}/first_100_bytes.bin", 'wb') as f:
    #         f.write(decrypted_data[:100])
    #     
    #     # 打印前100字节的十六进制表示
    #     hex_str = "".join(f"{b:02X} " for b in decrypted_data[:100])
    #     print(hex_str)
