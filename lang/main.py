import os
import sys
from game_engine import GameEngine

def main():
    print("欢迎来到 Project Lang: Gemini 狼人杀")
    
    # API Key provided by user
    api_key = os.environ.get("GEMINI_API_KEY") or "AIzaSyAK9EkYlwI_JC2rwg4QSfPL-BEHp9Kcq7I"
    
    if not api_key:
        print("错误: 未找到 GEMINI_API_KEY 环境变量。")
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
