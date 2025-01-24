"""解析新的API.txt中定义的请求序列"""
import json
from .config import Config
from typing import Literal

config = Config()
PayloadType = dict[str, str | float | int]
RequestType = dict[Literal["from", "type", "payload"], str | PayloadType]

def loads(request_str: str) -> list[RequestType]:
    request_strings = request_str.split(config.REQUESTS_SEPARATOR)
    requests = []
    for request_string in request_strings:
        if not request_string:
            continue
        try:
            requests.append(json.loads(request_string))
        except json.JSONDecodeError:
            print(f"Invalid JSON format: {request_string}")
    return requests

def dumps(requests: list[RequestType]) -> str:
    return "".join([
        (json.dumps(request).replace(config.REQUESTS_SEPARATOR, "") + # 防止在不应出现的地方出现分隔符
        config.REQUESTS_SEPARATOR)
        for request in requests
    ])

class Loader: # loads的进一步封装
    def __init__(self, config: Config):
        self.sep = config.REQUESTS_SEPARATOR
        self.request_str = ""
        self.requests: list[RequestType] = []
    
    def update(self, request_str: str) -> None:
        self.request_str += request_str
        request_strings = self.request_str.split(self.sep)
        left = ""
        for i, request_string in enumerate(request_strings):
            if not request_string:
                continue
            try:
                self.requests.append(json.loads(request_string))
            except json.JSONDecodeError:
                if i == len(request_strings) - 1: # 最后一个请求被截断，留待下次更新
                    left = request_strings[-1]
                else:
                    print(f"Invalid JSON format: {request_string}")
        self.request_str = left
    
    def get_requests(self) -> list[RequestType]:
        requests, self.requests = self.requests, []
        return requests

# 内置的信号
ASR_ACTIVATE: RequestType = {'from': 'asr', 'type': 'signal', 'payload': 'activate'}
LLM_EOS: RequestType = {'from': 'llm', 'type': 'signal', 'payload': 'eos'}
TTS_FINISH: RequestType = {'from': 'tts', 'type': 'signal', 'payload': 'finish'}
PANEL_START: RequestType = {'from': 'panel', 'type': 'signal', 'payload':'start'}
PANEL_STOP: RequestType = {'from': 'panel', 'type': 'signal', 'payload':'stop'}
MODULE_READY: RequestType = {'from':'*', 'type': 'signal', 'payload':'ready'}

__ALL__ = ["loads", "dumps", "ASR_ACTIVATE", "LLM_EOS", "TTS_FINISH"]
