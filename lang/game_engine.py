import random
import time
from roles import Role, RoleType, Team
from agent import GeminiAgent
import os
import re

class GameEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.players = {}  # id: Agent
        self.roles = {}    # id: Role
        self.alive = {}    # id: bool
        self.day = 0
        self.logs = []
        
        # Game State
        self.witch_potions = {"cure": True, "poison": True}
        
    def log(self, message):
        print(message)
        self.logs.append(message)
        
    def broadcast(self, message):
        """Send a message to all players (as if they heard it)."""
        self.log(f"[广播] {message}")
        for pid, agent in self.players.items():
            if self.alive[pid]:
                agent.receive_message(f"主持人: {message}")

    def setup_game(self):
        self.log("正在初始化游戏...")
        
        # Define roles for 8 players
        # 3 Wolves, 1 Seer, 1 Witch, 1 Hunter, 2 Villagers
        role_distribution = [
            RoleType.WEREWOLF, RoleType.WEREWOLF, RoleType.WEREWOLF,
            RoleType.SEER,
            RoleType.WITCH,
            RoleType.HUNTER,
            RoleType.VILLAGER, RoleType.VILLAGER
        ]
        random.shuffle(role_distribution)
        
        wolf_ids = [i for i, r in enumerate(role_distribution) if r == RoleType.WEREWOLF]
        
        # Helper to translate role names for logs
        role_names_cn = {
            RoleType.WEREWOLF: "狼人",
            RoleType.VILLAGER: "平民",
            RoleType.SEER: "预言家",
            RoleType.WITCH: "女巫",
            RoleType.HUNTER: "猎人"
        }

        for i, r_type in enumerate(role_distribution):
            partners = str(wolf_ids) if r_type == RoleType.WEREWOLF else None
            role_obj = Role(r_type)
            self.roles[i] = role_obj
            self.alive[i] = True
            
            # Initialize Agent (pass English role name for internal prompt logic if needed)
            agent = GeminiAgent(i, r_type.value, partners, self.api_key)
            self.players[i] = agent
            
            self.log(f"玩家 {i} 分配角色: {role_names_cn[r_type]}")
            
        self.log("游戏设置完成。狼人是: " + str(wolf_ids))

    def check_win_condition(self):
        wolves_alive = sum(1 for i in self.players if self.roles[i].type == RoleType.WEREWOLF and self.alive[i])
        good_alive = sum(1 for i in self.players if self.roles[i].team == Team.GOOD and self.alive[i])
        
        if wolves_alive == 0:
            return Team.GOOD
        if wolves_alive >= good_alive:
            return Team.BAD # Generally if wolves >= good, wolves win
        return None

    def run_night_phase(self):
        self.broadcast("天黑请闭眼。")
        time.sleep(1)
        
        # 1. Werewolves
        wolf_target = -1
        alive_wolves = [i for i in self.players if self.roles[i].type == RoleType.WEREWOLF and self.alive[i]]
        if alive_wolves:
            leader = alive_wolves[0]
            # Prompt allows reasoning now
            response = self.players[leader].run_night_action(
                f"现在是夜晚。你和你的队友 {[w for w in alive_wolves if w!=leader]} 必须杀一个人。 "
                f"存活玩家: {[k for k,v in self.alive.items() if v]}. "
                "请先简短陈述你的理由，然后在最后给出目标玩家的ID数字。"
            )
            print(f"[思考] 狼人 (玩家 {leader}): {response}")
            try:
                # Find the last number in the string to be safe? Or just any number.
                # Assuming reasoning might contain numbers (e.g. "Player 1 is sus").
                # Let's verify if target is alive.
                matches = re.findall(r'\d+', response)
                if matches:
                    # HEURISTIC: take the LAST number found, assuming they state decision at end.
                    for m in reversed(matches):
                        t_id = int(m)
                        if t_id in self.players and self.alive.get(t_id):
                            wolf_target = t_id
                            break
            except:
                pass
        
        self.log(f"(夜晚) 狼人选择了玩家 {wolf_target}")
        time.sleep(2) # Avoid rate limit

        # 2. Seer
        seer_id = next((i for i, r in self.roles.items() if r.type == RoleType.SEER), None)
        if seer_id and self.alive[seer_id]:
            response = self.players[seer_id].run_night_action(
                f"现在是夜晚。你可以查验一个人的身份。 "
                f"存活玩家: {[k for k,v in self.alive.items() if v]}. "
                "请先简短陈述你的理由，然后在最后给出目标玩家的ID数字。"
            )
            print(f"[思考] 预言家 (玩家 {seer_id}): {response}")
            try:
                matches = re.findall(r'\d+', response)
                if matches:
                    for m in reversed(matches):
                        target_id = int(m)
                        if target_id in self.players:
                             # Translate identity result
                            identity = "坏人" if self.roles[target_id].type == RoleType.WEREWOLF else "好人"
                            self.players[seer_id].receive_message(f"主持人: 玩家 {target_id} 是 {identity}。")
                            break
            except:
                pass
            time.sleep(2) # Avoid rate limit
                
        # 3. Witch
        witch_id = next((i for i, r in self.roles.items() if r.type == RoleType.WITCH), None)
        killed_by_witch = -1
        saved_by_witch = False
        
        if witch_id and self.alive[witch_id]:
            # Save?
            if self.witch_potions["cure"] and wolf_target != -1:
                response = self.players[witch_id].run_night_action(
                    f"现在是夜晚。玩家 {wolf_target} 被狼人袭击了。 "
                    "你要使用解药吗？请简述理由，并回复 'YES' 或 'NO'。"
                )
                print(f"[思考] 女巫 (玩家 {witch_id}) - 解药: {response}")
                if "YES" in response.upper():
                    saved_by_witch = True
                    self.witch_potions["cure"] = False
                    self.log(f"(夜晚) 女巫救了玩家 {wolf_target}")
            
            time.sleep(1)

            # Poison?
            if not saved_by_witch and self.witch_potions["poison"]:
                response = self.players[witch_id].run_night_action(
                    f"现在是夜晚。你要使用毒药杀人吗？ "
                    f"存活玩家: {[k for k,v in self.alive.items() if v]}. "
                    "请简述理由，并回复要毒杀的玩家ID，如果不毒杀回复 'NO'。"
                )
                print(f"[思考] 女巫 (玩家 {witch_id}) - 毒药: {response}")
                if "NO" not in response.upper():
                    matches = re.findall(r'\d+', response)
                    if matches:
                        for m in reversed(matches):
                             t_id = int(m)
                             if t_id in self.players and self.alive.get(t_id):
                                killed_by_witch = t_id
                                self.witch_potions["poison"] = False
                                self.log(f"(夜晚) 女巫毒死了玩家 {killed_by_witch}")
                                break
            
            time.sleep(1)

        # Resolve Deaths
        dead_this_night = []
        if wolf_target != -1 and not saved_by_witch:
            dead_this_night.append(wolf_target)
        if killed_by_witch != -1:
            dead_this_night.append(killed_by_witch)
            
        return list(set(dead_this_night))

    def run_day_phase(self, dead_last_night):
        self.day += 1
        self.broadcast(f"--- 第 {self.day} 天开始 ---")
        
        # Announce deaths
        if not dead_last_night:
            self.broadcast("昨晚是平安夜，没有人死亡。")
        else:
            self.broadcast(f"昨晚，以下玩家死亡: {dead_last_night}")
            for pid in dead_last_night:
                self.handle_death(pid, "昨晚")

        if self.check_win_condition():
            return

        # Discussion
        self.broadcast("讨论环节开始。请发表你的看法。")
        alive_ids = [i for i in self.players if self.alive[i]]
        
        for pid in alive_ids:
            if not self.alive[pid]: continue
            time.sleep(4) # Throttle for RPM limits
            
            # Prompt for Inner Thought + Public Speech
            raw_response = self.players[pid].speak(
                "现在轮到你发言了。请按以下格式回答：\n"
                "[思考] 你的内心独白（分析局势，暴露真实身份及其策略，这部分只有你自己能听到）\n"
                "[发言] 你的公开言论（其他玩家听到的内容，如果你是坏人，请注意伪装）"
            )
            
            # Parse logic
            thought_content = ""
            speech_content = raw_response
            
            # Try to extract [思考] and [发言] blocks
            # Case insensitive check just in case, though prompt uses Chinese brackets
            # Use regex to find content between tags
            t_match = re.search(r'\[思考\](.*?)(?=\[发言\]|$)', raw_response, re.DOTALL)
            s_match = re.search(r'\[发言\](.*)', raw_response, re.DOTALL)
            
            if t_match:
                thought_content = t_match.group(1).strip()
            if s_match:
                speech_content = s_match.group(1).strip()
            # If no tags found, just keep raw_response as speech (fallback)
            
            if thought_content:
                print(f"[思考] 玩家 {pid} ({self.roles[pid].type.value}): {thought_content}")
            
            # Broadcast only speech
            self.broadcast(f"玩家 {pid}: {speech_content}")

        # Vote
        self.broadcast("现在开始投票。你想把谁投出去？")
        votes = {}
        for pid in alive_ids:
            if not self.alive[pid]: continue
            time.sleep(4) # Throttle for RPM limits
            
            # Change prompt to ask for reasoning + ID
            response = self.players[pid].run_vote_action(
                "现在是投票时间。请先简述你的投票理由，然后在最后回复你想投出的玩家ID（例如 '1'）。弃票请回复 '-1'。"
            )
            print(f"[思考] 玩家 {pid} 投票: {response}")
            
            vote = -1
            # Parse last number
            matches = re.findall(r'-?\d+', response)
            if matches:
                # Heuristic: verify candidates from end to start
                for m in reversed(matches):
                    try:
                        v = int(m)
                        if v == -1:
                            vote = -1
                            break
                        if v in alive_ids:
                            vote = v
                            break
                    except: pass
            
            if vote in alive_ids:
                votes[pid] = vote
            else:
                votes[pid] = -1 # Abstain
        
        self.broadcast(f"投票结果: {votes}")
        
        # Tally
        from collections import Counter
        valid_votes = [v for v in votes.values() if v != -1]
        if not valid_votes:
            self.broadcast("没有人被投出局。")
        else:
            vote_counts = Counter(valid_votes)
            top_target, count = vote_counts.most_common(1)[0]
            # Check tie
            if list(vote_counts.values()).count(count) > 1:
                self.broadcast("票数相同，无人出局。")
            else:
                self.broadcast(f"玩家 {top_target} 以 {count} 票被投出局。")
                self.handle_death(top_target, "投票")

    def handle_death(self, pid, reason):
        if not self.alive[pid]: return
        self.alive[pid] = False
        role = self.roles[pid]
        self.broadcast(f"玩家 {pid} ({reason}) 死亡。") 
        
        # Hunter logic
        if role.type == RoleType.HUNTER:
            self.broadcast(f"玩家 {pid} 是猎人！")
            response = self.players[pid].run_night_action(
                f"你是猎人，你死了。你可以选择带走一个人。 "
                f"存活玩家: {[k for k,v in self.alive.items() if v]}. 请回复理由和目标ID。"
            )
            print(f"[思考] 猎人 (玩家 {pid}): {response}")
            
            matches = re.findall(r'\d+', response)
            if matches:
                for m in reversed(matches):
                    shot_id = int(m)
                    if shot_id in self.alive and self.alive[shot_id]:
                        self.broadcast(f"猎人开枪带走了玩家 {shot_id}！")
                        self.handle_death(shot_id, "猎人开枪")
                        break

    def run(self):
        self.setup_game()
        
        while True:
            winner = self.check_win_condition()
            if winner:
                w_str = "好人" if winner == Team.GOOD else "狼人"
                self.broadcast(f"游戏结束。 {w_str} 阵营获胜！")
                break
                
            dead_list = self.run_night_phase()
            
            winner = self.check_win_condition()
            if winner:
                w_str = "好人" if winner == Team.GOOD else "狼人"
                self.broadcast(f"游戏结束。 {w_str} 阵营获胜！")
                break
                
            self.run_day_phase(dead_list)

        # Reveal all roles at end
        summary = "最终角色揭晓:\n"
        role_names_cn = {
            RoleType.WEREWOLF: "狼人",
            RoleType.VILLAGER: "平民",
            RoleType.SEER: "预言家",
            RoleType.WITCH: "女巫",
            RoleType.HUNTER: "猎人"
        }
        for i, r in self.roles.items():
            summary += f"玩家 {i}: {role_names_cn[r.type]}\n"
        print(summary)
