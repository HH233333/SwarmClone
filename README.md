# SwarmClone 从零开始·蜂群克隆计划
这是一个致力于从零开始复刻一个Neuro-sama的开源项目！

什么是“从零开始”？
- 不使用第三方构建好的大语言模型
- 不使用第三方API（如ChatGPT）
- 不使用Open-LLM-VTuber等已有的人工智能虚拟主播框架

## 我们的目标？
- 实现一个以大语言模型为核心，使用一个虚拟形象并可以在Bilibili等直播平台上进行直播并与观众互动的人工智能虚拟主播

## 现在的进度？
- 见“总技术路线”

## 如何开始？
您需要安装最新版本的Anaconda，然后打开`Anaconda Prompt`，并运行以下命令：

```console
$ conda create -n swarmclone python=3.10.6
$ conda activate swarmclone
```

然后切换到项目的根目录，并运行以下命令：

```console
$ python get_req.py
```

如果遇到网络问题，请尝试使用国内镜像源或代理。


## 如何参与开发？
- 您可以加入我们的开发QQ群：1017493942


## 总技术路线：
1) 大语言模型搭建（见[MiniLM2](https://github.com/swarmclone/MiniLM2)）*已基本完成*
2) 微调（数据来源：魔改COIG-CQIA等）*阶段性完成*
3) 虚拟形象（设定：见`设定.txt`）*进行中*
4) 直播画面（形式：Unity驱动的Live2D）*进行中*
5) 技术整合（对语言大模型、语音模型、虚拟形象、语音输入等，统一调度）*进行中*
6) 接入直播平台
7) 精进：
    - 长期记忆RAG
    - 联网RAG
    - 与外界主动互动（发评论/私信？）
    - 多模态（视觉听觉，甚至其他？）
    - 整活（翻滚/b动静等）
    - 唱歌
    - 玩Minecraft、无人深空等游戏
