# Code by TimoNiki
# Copyright 2026 TimoNiki
# TS3 is a TeamSpeak3


import sys
import threading
import time
import ts3

class TS3BotThread(threading.Thread):
    def __init__(self, bot_name, privilege_level, host, port, username, password):
        super().__init__()
        self.bot_name = bot_name
        self.privilege_level = privilege_level
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        self.running = False

    def run(self):
        try:
            self.connection = ts3.query.TS3Connection(self.host, self.port)
            self.connection.login(client_login_name=self.username, client_login_password=self.password)
            self.connection.use(sid=1)
            
            try:
                self.connection.clientupdate(client_nickname=self.bot_name)
            except Exception:
                pass
                
            self.running = True
            print(f"\n[+] Bot '{self.bot_name}' successfully connected and spawned on the server!")
            
            while self.running:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"\n[-] Bot '{self.bot_name}' failed to connect: {e}")
            self.running = False
        finally:
            if self.connection:
                try:
                    self.connection.close()
                except Exception:
                    pass

    def create_channels(self, name, count):
        if not self.connection:
            print(f"Error: Bot '{self.bot_name}' connection is not initialized.")
            return

        try:
            count = int(count)
        except ValueError:
            print("Error: Channel count must be a number.")
            return

        print(f"[{self.bot_name}] Starting channel creation ({count} channels)...")
        for i in range(1, count + 1):
            channel_name = f"{name}_{i}"
            try:
                self.connection.channelcreate(
                    channel_name=channel_name, 
                    channel_flag_semi_permanent=1
                )
                print(f"  [{self.bot_name}][+] Created channel: {channel_name}")
            except Exception as e:
                print(f"  [{self.bot_name}][-] Failed to create channel {channel_name}: {e}")
        print(f"[{self.bot_name}] Command execution finished.")

    def get_channel_id_by_name(self, name):
        if not self.connection:
            return None
        try:
            response = self.connection.channellist()
            for channel in response.parsed:
                if channel.get('channel_name') == name:
                    return channel.get('cid')
        except Exception:
            pass
        return None

    def delete_single_channel(self, name):
        if not self.connection:
            print(f"Error: Bot '{self.bot_name}' connection is not initialized.")
            return

        cid = self.get_channel_id_by_name(name)
        if not cid:
            print(f"Error: Channel '{name}' not found.")
            return

        try:
            self.connection.channeldelete(cid=cid, force=1)
            print(f"  [{self.bot_name}][-] Successfully deleted channel: {name}")
        except Exception as e:
            print(f"  [{self.bot_name}][-] Failed to delete channel {name}: {e}")

    def delete_multiple_channels(self, raw_args):
        if not self.connection:
            print(f"Error: Bot '{self.bot_name}' connection is not initialized.")
            return

        if " to " not in raw_args.lower():
            print("Error: Invalid format. Use: delete more_channels PREFIX_START to PREFIX_END")
            return

        try:
            parts = raw_args.split(" to ")
            start_name = parts[0].strip()
            end_name = parts[1].strip()

            start_num = int(''.join(filter(str.isdigit, start_name.split('_')[-1])))
            end_num = int(''.join(filter(str.isdigit, end_name.split('_')[-1])))

            prefix = start_name.rsplit('_', 1)[0]

            print(f"[{self.bot_name}] Starting mass deletion for prefix '{prefix}' from index {start_num} to {end_num}...")
            
            response = self.connection.channellist()
            server_channels = response.parsed

            deleted_count = 0
            for i in range(start_num, end_num + 1):
                target_name_1 = f"{prefix}_{i}"
                target_name_2 = f"{prefix} {i}"
                
                cid = None
                found_name = ""
                for ch in server_channels:
                    ch_name = ch.get('channel_name')
                    if ch_name == target_name_1 or ch_name == target_name_2:
                        cid = ch.get('cid')
                        found_name = ch_name
                        break
                
                if cid:
                    try:
                        self.connection.channeldelete(cid=cid, force=1)
                        print(f"  [{self.bot_name}][-] Deleted channel: {found_name} (ID: {cid})")
                        deleted_count += 1
                    except Exception as e:
                        print(f"  [{self.bot_name}][-] Failed to delete channel {found_name}: {e}")
                else:
                    print(f"  [{self.bot_name}][?] Channel with index {i} ({target_name_1}) not found, skipping...")
                    
            print(f"[{self.bot_name}] Mass deletion finished. Total deleted: {deleted_count} channels.")
        except Exception as e:
            print(f"Error parsing delete range: {e}")

    def stop(self):
        self.running = False


class TS3QueryManager:
    def __init__(self):
        self.username = None
        self.password = None
        self.host = "localhost"
        self.port = 10011
        self.main_bot = None
        self.virtual_bots = {}
        self.current_managed_bot = None

    def set_name(self, username):
        self.username = username
        print(f"Username set to: {self.username}")

    def set_password(self, password):
        self.password = password
        print("Password has been set successfully.")

    def connect_server(self, host="localhost", port=10011):
        if not self.username or not self.password:
            print("Error: Please set username and password first using 'set name' and 'set password' commands.")
            return
        
        self.host = host
        self.port = port
        
        print(f"Spawning Main_Bot and attempting connection to {host}:{port}...")
        self.main_bot = TS3BotThread("Main_Bot", "100", self.host, self.port, self.username, self.password)
        self.main_bot.start()

    def add_virtual_bot(self, name, privilege_level):
        if not self.username or not self.password:
            print("Error: Set manager username and password before creating extra bots.")
            return
            
        if name in self.virtual_bots or name == "Main_Bot":
            print(f"Error: Bot with name '{name}' already exists.")
            return
        
        print(f"Spawning parallel bot '{name}' (Level: {privilege_level})...")
        new_bot = TS3BotThread(name, privilege_level, self.host, self.port, self.username, self.password)
        self.virtual_bots[name] = new_bot
        new_bot.start()

    def manage_bot(self, name):
        if name.lower() == "exit":
            if self.current_managed_bot is None:
                print("You are already managing the main manager.")
            else:
                print(f"Exiting management mode. Returned to main manager.")
                self.current_managed_bot = None
            return

        if name == "Main_Bot" and self.main_bot:
            self.current_managed_bot = self.main_bot
            print("Now managing: Main_Bot")
            return

        if name not in self.virtual_bots:
            print(f"Error: Active bot '{name}' does not exist.")
            return

        self.current_managed_bot = self.virtual_bots[name]
        print(f"Now managing bot: '{self.current_managed_bot.name}' (Privilege Level: {self.current_managed_bot.privilege_level})")

    def get_active_executor(self):
        if self.current_managed_bot:
            return self.current_managed_bot
        return self.main_bot

    def run(self):
        print("TS3 Query Manager started. Awaiting commands...")
        print("Available commands:")
        print("  -> set name [USERNAME]")
        print("  -> set password [PASSWORD]")
        print("  -> connect localhost")
        print("  -> bots add [BOT_NAME] [PRIVILEGE_LEVEL]")
        print("  -> bot manage [BOT_NAME] / bot manage exit")
        print("  -> create channel [NAME] [COUNT]")
        print("  -> delete channel [NAME]")
        print("  -> delete more_channels [NAME_1] to [NAME_4]")
        print("  -> exit")
        
        while True:
            try:
                active_bot = self.get_active_executor()
                prompt_prefix = f"({active_bot.bot_name}) " if active_bot else ""
                
                user_input = input(f"\n{prompt_prefix}Enter command > ").strip()
                if not user_input:
                    continue
                
                if user_input.lower() == "exit":
                    print("Exiting and stopping all bot threads...")
                    if self.main_bot:
                        self.main_bot.stop()
                    for bot in self.virtual_bots.values():
                        bot.stop()
                    break

                if user_input.lower().startswith("set name "):
                    name_value = user_input[9:].strip()
                    if name_value:
                        self.set_name(name_value)
                    else:
                        print("Error: Username cannot be empty.")
                    continue

                if user_input.lower().startswith("set password "):
                    pwd_value = user_input[13:].strip()
                    if pwd_value:
                        self.set_password(pwd_value)
                    else:
                        print("Error: Password cannot be empty.")
                    continue

                if user_input.lower().startswith("connect"):
                    parts = user_input.split()
                    host = parts[1] if len(parts) > 1 else "localhost"
                    if host.lower() == "localhost":
                        host = "localhost"
                    self.connect_server(host=host)
                    continue

                if user_input.lower().startswith("bots add "):
                    cmd_body = user_input[9:].strip()
                    parts = cmd_body.split()
                    if len(parts) < 2:
                        print("Error: Invalid format. Use: bots add BOT_NAME PRIVILEGE_LEVEL")
                        continue
                    bot_level = parts[-1]
                    bot_name = " ".join(parts[:-1])
                    self.add_virtual_bot(bot_name, bot_level)
                    continue

                if user_input.lower().startswith("bot manage "):
                    target_bot = user_input[11:].strip()
                    self.manage_bot(target_bot)
                    continue

                executor = self.get_active_executor()
                if not executor:
                    print("Error: No active server connection. Run 'connect localhost' first.")
                    continue

                if user_input.lower().startswith("create channel "):
                    cmd_body = user_input[15:].strip()
                    parts = cmd_body.split()
                    if len(parts) < 2:
                        print("Error: Invalid format. Use: create channel NAME COUNT")
                        continue
                    count = parts[-1]
                    name = " ".join(parts[:-1])
                    executor.create_channels(name, count)
                    continue

                if user_input.lower().startswith("delete more_channels "):
                    raw_args = user_input[21:].strip()
                    executor.delete_multiple_channels(raw_args)
                    continue

                if user_input.lower().startswith("delete channel "):
                    channel_name = user_input[15:].strip()
                    executor.delete_single_channel(channel_name)
                    continue
                
                print("Error: Unknown command.")
                
            except KeyboardInterrupt:
                print("\nShutting down threads...")
                if self.main_bot:
                    self.main_bot.stop()
                for bot in self.virtual_bots.values():
                    bot.stop()
                break

if __name__ == "__main__":
    bot = TS3QueryManager()
    bot.run()
