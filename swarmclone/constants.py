from enum import Enum

class MessageType(Enum):
    SIGNAL = "Signal"
    DATA = "Data"

class ModuleRoles(Enum):
    # 输出模块
    LLM = "LLM"
    TTS = "TTS"
    FRONTEND = "Frontend"

    # 输入模块
    ASR = "ASR"
    CHAT = "Chat"

    # 其他模块
    PLUGIN = "Plugin"

    # 主控（并非模块，但是为了向其他模块发送消息，必须要有角色）
    CONTROLLER = "Controller"

    # 未指定（仅用于基类，任何未指定角色的模块在注册时都会引发错误）
    UNSPECIFIED = "Unspecified"

class LLMState(Enum):
    IDLE = "Idle"
    GENERATING = "Generating"
    WAITING4TTS = "Waiting for TTS"
    WAITING4ASR = "Waiting for ASR"
    SINGING = "Singing"
