#!/usr/bin/env python3
"""
Claude API 简单测试脚本
"""

import os
from anthropic import Anthropic

def main():
    # 从环境变量获取 API Key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("错误: 请设置 ANTHROPIC_API_KEY 环境变量")
        print("export ANTHROPIC_API_KEY='your-api-key'")
        return

    # 初始化客户端
    client = Anthropic(api_key=api_key)

    # 发送测试消息
    print("正在调用 Claude API...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "你好！请用一句话介绍你自己。"}
        ]
    )

    # 输出响应
    print("\n--- Claude 响应 ---")
    print(message.content[0].text)
    print("\n--- 元信息 ---")
    print(f"模型: {message.model}")
    print(f"输入 tokens: {message.usage.input_tokens}")
    print(f"输出 tokens: {message.usage.output_tokens}")


if __name__ == "__main__":
    main()
