#!/usr/bin/env python
# coding: utf-8

"""
保险文档智能问答助手 - GUI版本
基于 qwen-agent-multi-files.py 添加 WebUI 图形界面
"""

import pprint
import urllib.parse
import json5
import os
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.gui import WebUI


# 注册自定义工具：AI图像生成
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    """AI 绘画（图像生成）服务，输入文本描述，返回基于文本信息绘制的图像 URL。"""
    
    description = 'AI 绘画（图像生成）服务，输入文本描述，返回基于文本信息绘制的图像 URL。'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '期望的图像内容的详细描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json5.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


def get_llm_cfg():
    """获取LLM配置，需要填写有效的API Key"""
    # 请在这里填写你的阿里云 DashScope API Key
    YOUR_API_KEY = 'sk-afd94a5004eb407da5cf133f685a1139'
    
    llm_cfg = {
        'model': 'deepseek-v3',
        'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'api_key': YOUR_API_KEY,
        'generate_cfg': {
            'top_p': 0.8
        }
    }
    return llm_cfg


def get_files():
    """获取docs文件夹下的所有文件"""
    file_dir = os.path.join('./', 'docs')
    files = []
    if os.path.exists(file_dir):
        for file in os.listdir(file_dir):
            file_path = os.path.join(file_dir, file)
            if os.path.isfile(file_path):
                files.append(file_path)
    print('files=', files)
    return files


def get_system_instruction():
    """获取系统指令"""
    return '''你是一个乐于助人的AI助手，精通各类保险产品的介绍和解答。
在收到用户的请求后，你应该：
- 首先根据用户的问题，从给定的保险文档中查找相关信息
- 然后绘制一幅与保险主题相关的图像，得到图像的url（如果需要）
- 最后运行代码展示图像或处理相关信息
用 `plt.show()` 展示图像。
你总是用中文回复用户。'''


def init_agent_service():
    """初始化智能体服务"""
    llm_cfg = get_llm_cfg()
    tools = ['my_image_gen', 'code_interpreter']
    files = get_files()
    
    try:
        bot = Assistant(
            llm=llm_cfg,
            system_message=get_system_instruction(),
            function_list=tools,
            files=files
        )
        print("助手初始化成功！")
        return bot
    except Exception as e:
        print(f"助手初始化失败: {str(e)}")
        raise


def app_gui():
    """启动Web图形界面"""
    try:
        print("正在启动 Web 界面...")
        bot = init_agent_service()
        chatbot_config = {
            'prompt.suggestions': [
                '介绍下雇主责任险',
                '平安商业综合责任保险是什么？',
                '雇主安心保的保障范围有哪些？',
                '施工保适合哪些场景？',
            ]
        }
        print("Web 界面准备就绪，正在启动服务...")
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run()
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 API Key 配置")


def app_tui():
    """启动终端交互模式"""
    try:
        bot = init_agent_service()
        messages = []
        while True:
            try:
                query = input('请输入问题: ').strip()
                if not query:
                    print('问题不能为空！')
                    continue
                messages.append({'role': 'user', 'content': query})
                print("正在处理您的请求...")
                
                response = []
                for resp in bot.run(messages):
                    print('bot response:', resp)
                    response.append(resp)
                messages.extend(response)
            except KeyboardInterrupt:
                print("\n退出程序")
                break
            except Exception as e:
                print(f"处理请求时出错: {str(e)}")
                print("请重试或输入新的问题")
    except Exception as e:
        print(f"启动终端模式失败: {str(e)}")


if __name__ == '__main__':
    # 默认启动Web界面，如需终端模式可注释下面一行并取消注释app_tui()
    app_gui()
    # app_tui()
