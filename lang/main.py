import os
import sys
from game_engine import GameEngine

from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    print("欢迎来到 Project Lang: Gemini 狼人杀")
    
    # API Key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("错误: 未在 .env 文件或环境变量中查找到 GEMINI_API_KEY。")
        return

    # Initialize and run
    game = GameEngine(api_key=api_key)
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n游戏已被用户终止。")
    except Exception as e:
        print(f"\n发生错误: {e}")

if __name__ == "__main__":
    main()
