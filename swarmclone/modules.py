from __future__ import annotations # 为了延迟注解评估
import asyncio
import time
import random
from typing import Any
from uuid import uuid4
from .constants import *
from .messages import *
from .config import Config

class ModuleBase:
    def __init__(self, module_role: ModuleRoles, name: str, config: Config):
        self.name: str = name
        self.role: ModuleRoles = module_role
        self.task_queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=128)
        self.results_queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=128)
        self.config: Config = config
    
    async def run(self) -> None:
        while True:
            try:
                task = self.task_queue.get_nowait()
            except asyncio.QueueEmpty:
                task = None
            result = await self.process_task(task)
            if result is not None:
                await self.results_queue.put(result)
            await asyncio.sleep(0.1)

    def __repr__(self):
        return f"<{self.role} {self.name}>"

    async def process_task(self, task: Message | None) -> Message | None:
        """
        处理任务的方法，每个循环会自动调用
        返回None表示不需要返回结果，返回Message对象则表示需要返回结果，返回的对象会自动放入results_queue中。
        也可以选择手动往results_queue中put结果然后返回None
        """

class LLMBase(ModuleBase):
    def __init__(self, name: str, config: Config):
        super().__init__(ModuleRoles.LLM, name, config)
        self.state: LLMState = LLMState.IDLE
        self.history: list[dict[str, str]] = []
        self.generated_text: str = ""
        self.generate_task: asyncio.Task[Any] | None = None
        self.chat_maxsize: int = 20
        self.chat_size_threshold: int = 10
        self.chat_queue: asyncio.Queue[ChatMessage] = asyncio.Queue(maxsize=self.chat_maxsize)
        self.asr_timeout: int = 60 # 应该没有人说话一分钟不停
        self.tts_timeout: int = 60 ## TODO：是否应该加入设置项？
        self.idle_start_time: float = time.time()
        self.waiting4asr_start_time: float = time.time()
        self.waiting4tts_start_time: float = time.time()
        self.asr_counter = 0 # 有多少人在说话？
        assert isinstance((chat_role := self.config.llm.main_model.chat_role), str)
        self.chat_role = chat_role
        assert isinstance((asr_role := self.config.llm.main_model.asr_role), str)
        self.asr_role = asr_role
        assert isinstance((chat_template := self.config.llm.main_model.chat_template), str)
        self.chat_template = chat_template
        assert isinstance((asr_template := self.config.llm.main_model.asr_template), str)
        self.asr_template = asr_template
        assert isinstance((system_prompt := self.config.llm.main_model.system_prompt), str)
        if system_prompt:
            self.history += [{'role': 'system', 'content': system_prompt}]
    
    def _switch_to_generating(self):
        self.state = LLMState.GENERATING
        self.generated_text = ""
        self.generate_task = asyncio.create_task(self.start_generating())
    
    def _switch_to_waiting4asr(self):
        if self.generate_task is not None and not self.generate_task.done():
            self.generate_task.cancel()
        if self.generated_text:
            self._add_llm_history(self.generated_text)
        self.generated_text = ""
        self.generate_task = None
        self.state = LLMState.WAITING4ASR
        self.waiting4asr_start_time = time.time()
        self.asr_counter = 1 # 等待第一个人
    
    def _switch_to_idle(self):
        self.state = LLMState.IDLE
        self.idle_start_time = time.time()
    
    def _switch_to_waiting4tts(self):
        self._add_llm_history(self.generated_text)
        self.generated_text = ""
        self.generate_task = None
        self.state = LLMState.WAITING4TTS
        self.waiting4tts_start_time = time.time()
    
    def _add_chat_history(self, user: str, content: str):
        self.history += [
            {'role': self.chat_role, 'content': self.chat_template.format(user=user, content=content)}
        ]
    
    def _add_asr_history(self, user: str, content: str):
        self.history += [
            {'role': self.asr_role, 'content': self.asr_template.format(user=user, content=content)}
        ]
    
    def _add_llm_history(self, content: str):
        self.history += [
            {'role': 'assistant', 'content': content}
        ]
    
    def _add_system_history(self, content: str):
        self.history += [
            {'role': 'system', 'content': content}
        ]
   
    async def run(self):
        assert isinstance((idle_timeout := self.config.llm.idle_time), float | int), idle_timeout

        while True:
            try:
                task = self.task_queue.get_nowait()
                print(self.state, task)
            except asyncio.QueueEmpty:
                task = None
            
            if isinstance(task, ChatMessage):
                if (qsize := self.chat_queue.qsize()) < self.chat_size_threshold:
                    prob = 1
                else:
                    prob = 1 - (qsize - self.chat_size_threshold) / (self.chat_maxsize - self.chat_size_threshold)
                if random.random() < prob:
                    try:
                        self.chat_queue.put_nowait(task)
                    except asyncio.QueueFull:
                        pass

            match self.state:
                case LLMState.IDLE:
                    if isinstance(task, ASRActivated):
                        self._switch_to_waiting4asr()
                    elif not self.chat_queue.empty():
                        try:
                            chat = self.chat_queue.get_nowait().get_value(self) # 逐条回复弹幕
                            self._add_chat_history(chat['user'], chat['content']) ## TODO：可能需要一次回复多条弹幕
                            self._switch_to_generating()
                        except asyncio.QueueEmpty:
                            pass
                    elif time.time() - self.idle_start_time > idle_timeout:
                        self._add_system_history("请随便说点什么吧！")
                        self._switch_to_generating()
                case LLMState.GENERATING:
                    if isinstance(task, ASRActivated):
                        self._switch_to_waiting4asr()
                    if self.generate_task is not None and self.generate_task.done():
                        self._switch_to_waiting4tts()
                case LLMState.WAITING4ASR:
                    if time.time() - self.waiting4asr_start_time > self.asr_timeout:
                        self._switch_to_idle() # ASR超时，回到待机
                    if task is not None and isinstance(task, ASRMessage):
                        message_value = task.get_value(self)
                        speaker_name = message_value["speaker_name"]
                        content = message_value["message"]
                        self._add_asr_history(speaker_name, content)
                        self.asr_counter -= 1 # 有人说话完毕，计数器-1
                    if task is not None and isinstance(task, ASRActivated):
                        self.asr_counter += 1 # 有人开始说话，计数器+1
                    if self.asr_counter <= 0: # 所有人说话完毕，开始生成
                        self._switch_to_generating()
                case LLMState.WAITING4TTS:
                    if time.time() - self.waiting4tts_start_time > self.tts_timeout:
                        self._switch_to_idle() # 太久没有TTS完成信息，说明TTS生成失败，回到待机
                    if task is not None and isinstance(task, AudioFinished):
                        self._switch_to_idle()
                    elif task is not None and isinstance(task, ASRActivated):
                        self._switch_to_waiting4asr()
            await asyncio.sleep(0.1) # 避免卡死事件循环
    
    async def start_generating(self) -> None:
        iterator = self.iter_sentences_emotions()
        try:
            async for sentence, emotion in iterator:
                self.generated_text += sentence
                await self.results_queue.put(
                    LLMMessage(
                        self,
                        sentence,
                        str(uuid4()),
                        emotion
                    )
                )
        except asyncio.CancelledError:
            await iterator.aclose()
        finally:
            await self.results_queue.put(LLMEOS(self))
    
    async def iter_sentences_emotions(self):
        """
        句子-感情迭代器
        使用yield返回：
        (句子: str, 感情: dict)
        句子：模型返回的单个句子（并非整个回复）
        情感：{
            'like': float,
            'disgust': float,
            'anger': float,
            'happy': float,
            'sad': float,
            'neutral': float
        }
        迭代直到本次回复完毕即可
        """
        yield str(""), {"like": 0., "disgust": 0., "anger": 0., "happy": 0., "sad": 0., "neutral": 1.}

class LLMDummy(LLMBase):
    def __init__(self, config: Config):
        super().__init__("LLMDummy", config)

    async def iter_sentences_emotions(self):
        sentences = ["This is a test sentence.", f"I received user prompt {self.history[-1]['content']}"]
        for sentence in sentences:
            yield sentence, {'like': 0, 'disgust': 0, 'anger': 0, 'happy': 0, 'sad': 0, 'neutral': 1.}

class FrontendDummy(ModuleBase):
    def __init__(self, config: Config):
        super().__init__(ModuleRoles.FRONTEND, "FrontendDummy", config)

    async def process_task(self, task: Message | None) -> Message | None:
        if task is not None:
            print(f"{self} received {task}")
        return None

class ControllerDummy(ModuleBase):
    """给Controller直接发送消息用的马甲，没有实际功能"""
    def __init__(self, config: Config):
        super().__init__(ModuleRoles.CONTROLLER, "ControllerDummy", config)
    