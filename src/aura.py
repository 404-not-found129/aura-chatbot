import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

# Load environment variables from .env file
load_dotenv()

console = Console()

class SlashCommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # Only trigger if the text starts exactly with '/' and has no spaces
        if text.startswith('/') and ' ' not in text:
            for cmd in self.commands:
                if cmd.startswith(text.lower()):
                    yield Completion(cmd, start_position=-len(text))

class AuraBot:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.chat = None
        self.name = "Aura"
        self.theme_color = "medium_purple1"
        self.model_name = "gemini-2.5-flash"
        self.version = "v1.4.0"
        self.use_web = False
        self.last_response = ""
        self.system_instruction = ""
        
        # Setup interactive autocomplete session
        self.commands = [
            '/help', '/exit', '/quit', '/clear', '/init', 
            '/save', '/system', '/web'
        ]
        self.completer = SlashCommandCompleter(self.commands)
        self.session = PromptSession(completer=self.completer, complete_while_typing=True)
        
    def draw_dashboard(self):
        # Left side: Greeting, Logo, Info
        left_text = Text()
        left_text.append("Welcome back!\n\n", style="bold")
        
        # New sleek ASCII logo
        logo = """ █████╗ ██╗   ██╗██████╗  █████╗ 
██╔══██╗██║   ██║██╔══██╗██╔══██╗
███████║██║   ██║██████╔╝███████║
██╔══██║██║   ██║██╔══██╗██╔══██║
██║  ██║╚██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"""
        left_text.append(logo + "\n\n", style=self.theme_color)
        
        left_text.append(f"{self.model_name}\n", style="bold green")
        
        web_status = "Enabled" if self.use_web else "Disabled"
        left_text.append(f"Web Search: {web_status}\n", style="cyan" if self.use_web else "dim")
        
        user = os.getenv('USER', 'User')
        left_text.append(f"{user}'s Workspace\n", style="dim")
        
        cwd = os.getcwd()
        display_cwd = f"...{cwd[-35:]}" if len(cwd) > 38 else cwd
        left_text.append(f"~{display_cwd}\n", style="dim")
        
        # Right side: Tips and What's New
        right_text = Text()
        right_text.append("Tips for getting started\n", style="bold")
        right_text.append("Type / to instantly see the auto-complete command menu!\n")
        right_text.append("───────────────────────────────────────────────────────────────────────\n", style="dim")
        right_text.append("What's new in v1.3.0\n", style="bold")
        right_text.append("• Stunning new ASCII text logo\n")
        right_text.append("• Live command auto-complete dropdown\n")
        right_text.append("• /web command to toggle Google Search grounding\n")
        right_text.append("• /save to instantly save Aura's last code output\n")
        right_text.append("• /system to view active project instructions\n")

        table = Table.grid(padding=(0, 4))
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="left", ratio=1)
        table.add_row(left_text, right_text)

        panel = Panel(
            table,
            title=f" {self.name} Code {self.version} ",
            border_style=self.theme_color,
            box=box.ROUNDED,
            expand=False,
            padding=(1, 2)
        )
        console.print(panel)

    def _init_gemini(self):
        with console.status(f"[dim]Initializing {self.name} {self.model_name}...[/dim]", spinner="point"):
            from google import genai
            from google.genai import types
            
            if not self.client:
                self.client = genai.Client(api_key=self.api_key)
            
            self.system_instruction = """You are Aura, an expert AI programming assistant running in a user's terminal. 
            You possess the following core capabilities:
            - Generate code: Write code snippets, functions, classes, or full scripts.
            - Debug code: Find errors in code and suggest fixes.
            - Explain code: Describe what a piece of code does and explain concepts.
            - Refactor/Optimize code: Suggest improvements for performance and readability.
            
            **SPEED & CONCISENESS (CRITICAL):**
            - Be extremely concise. 
            - Omit ALL conversational filler, preambles (e.g. "Here is the code..."), and postambles.
            - Provide the answer or code immediately to ensure the fastest possible terminal response time.
            
            **FILE SYSTEM ACCESS (IMPORTANT):**
            You have the ability to create and edit files directly on the user's hard drive! 
            To create or edit a file, you MUST format your markdown code block EXACTLY like this, with NO OTHER language tags (do not use ```python file:..., ONLY use ```file:...):
            
            ```file:src/main.py
            print("Hello world")
            ```
            
            **COMMAND EXECUTION (IMPORTANT):**
            You CAN execute shell commands directly on the user's machine! NEVER say you cannot run commands.
            To execute a command, output it in a markdown block EXACTLY like this:
            ```bash:run
            mv test ~/Downloads/
            ```
            The local application will intercept this and run it on your behalf. Use this proactively when the user asks you to move, copy, delete files, run scripts, or perform system operations.
            
            When you output these exact formats, the local Aura application automatically intercepts them. ALWAYS use these capabilities proactively."""

            if os.path.exists("AURA.md"):
                try:
                    with open("AURA.md", "r") as f:
                        project_rules = f.read()
                    self.system_instruction += f"\n\nPROJECT SPECIFIC INSTRUCTIONS (from AURA.md):\n{project_rules}"
                except Exception:
                    pass

            config_params = {
                "system_instruction": self.system_instruction
            }
            
            if self.use_web:
                # Enable Google Search Grounding
                config_params["tools"] = [{"google_search": {}}]

            self.chat = self.client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(**config_params)
            )

    def setup(self):
        console.clear()
        self.draw_dashboard()
        
        if not self.api_key or self.api_key == "your_api_key_here" or self.api_key.strip() == "":
            console.print("[bold yellow]No valid Gemini API key found.[/bold yellow]")
            console.print("You can get a free API key at: [cyan]https://aistudio.google.com/[/cyan]")
            
            while not self.api_key or self.api_key.strip() == "" or self.api_key == "your_api_key_here":
                self.api_key = console.input(f"\n[{self.theme_color}]Please paste your Gemini API key: [/{self.theme_color}]").strip()
            
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
            env_content = ""
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_content = f.read()
            
            if "GEMINI_API_KEY=" in env_content:
                import re
                env_content = re.sub(r'GEMINI_API_KEY=.*', f'GEMINI_API_KEY="{self.api_key}"', env_content)
            else:
                env_content += f'\nGEMINI_API_KEY="{self.api_key}"\n'
                
            with open(env_path, 'w') as f:
                f.write(env_content.strip() + "\n")
                
            console.print("[bold green]API Key saved to .env![/bold green]\n")
            
        try:
            self._init_gemini()
        except Exception as e:
            console.print(f"[bold red]Failed to initialize {self.name}:[/bold red] {e}")
            sys.exit(1)
            
    def run(self):
        self.setup()
        
        while True:
            try:
                # Use prompt_toolkit for live auto-complete!
                user_input = self.session.prompt(HTML("\n<b>You</b>\n<ansigray>&gt;</ansigray> ")).strip()
                
                if not user_input:
                    continue
                    
                if user_input.startswith('/'):
                    parts = user_input.lower().split()
                    cmd = parts[0]
                    
                    if cmd in ['/exit', '/quit']:
                        console.print(f"\n[{self.theme_color}]✧ {self.name}[/{self.theme_color}]\nGoodbye! Have a great day.\n")
                        break
                        
                    elif cmd == '/clear':
                        console.clear()
                        self.draw_dashboard()
                        continue
                        
                    elif cmd == '/init':
                        if os.path.exists("AURA.md"):
                            console.print("[yellow]AURA.md already exists in this directory.[/yellow]")
                        else:
                            with open("AURA.md", "w") as f:
                                f.write("# Aura Project Instructions\n\nAdd specific rules, architectural guidelines, or context for this project here.\nAura will automatically read these instructions on startup.")
                            console.print(f"[{self.theme_color}]Created AURA.md![/{self.theme_color}] I will remember the rules you write there.")
                            self._init_gemini()
                        continue
                        
                    elif cmd == '/save':
                        if not self.last_response:
                            console.print("[yellow]No response to save yet! Ask me something first.[/yellow]")
                            continue
                            
                        filename = console.input(f"[{self.theme_color}]Enter filename to save to (e.g. script.py): [/{self.theme_color}]").strip()
                        if filename:
                            try:
                                with open(filename, "w") as f:
                                    f.write(self.last_response)
                                console.print(f"[bold green]✓ Saved {len(self.last_response)} characters to {filename}[/bold green]")
                            except Exception as e:
                                console.print(f"[bold red]Failed to save file: {e}[/bold red]")
                        continue
                        
                    elif cmd == '/system':
                        console.print(Panel(self.system_instruction, title="Active System Rules", border_style="cyan"))
                        continue
                        
                    elif cmd == '/web':
                        self.use_web = not self.use_web
                        self._init_gemini()
                        console.clear()
                        self.draw_dashboard()
                        continue
                        
                    elif cmd == '/help':
                        console.print("\n[bold]Available Commands:[/bold]")
                        console.print(f"  [{self.theme_color}]/init[/{self.theme_color}]   - Create an AURA.md file for project-specific rules")
                        console.print(f"  [{self.theme_color}]/web[/{self.theme_color}]    - Toggle live Google Search (let Aura browse the internet)")
                        console.print(f"  [{self.theme_color}]/save[/{self.theme_color}]   - Save Aura's last message to a local file")
                        console.print(f"  [{self.theme_color}]/system[/{self.theme_color}] - View the hidden instructions Aura is currently following")
                        console.print(f"  [{self.theme_color}]/clear[/{self.theme_color}]  - Clear the screen and reload the dashboard")
                        console.print(f"  [{self.theme_color}]/help[/{self.theme_color}]   - Show this help message")
                        console.print(f"  [{self.theme_color}]/exit[/{self.theme_color}]   - Quit the application")
                        continue
                        
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red] Type /help for a list of commands.")
                        continue

                console.print(f"\n[{self.theme_color}]✧ {self.name}[/{self.theme_color}]")
                
                self.last_response = ""
                # High-speed initial render with CPU-saving fallback
                with Live(Markdown(""), console=console, refresh_per_second=6) as live:
                    response_stream = self.chat.send_message_stream(user_input)
                    chunk_counter = 0
                    
                    for chunk in response_stream:
                        if chunk.text:
                            self.last_response += chunk.text
                            chunk_counter += 1
                            
                            # Render the first 2 chunks instantly so it feels lightning fast,
                            # then fall back to batching every 4th chunk to save CPU on large code blocks.
                            if chunk_counter <= 2 or chunk_counter % 4 == 0:
                                live.update(Markdown(self.last_response))
                    
                    # Ensure the final, complete text is rendered when the stream finishes
                    live.update(Markdown(self.last_response))
                    
                # Post-processing: Automatically save any requested files
                import re
                import subprocess
                
                # 1. Handle File Writing
                # Regex made more robust to handle spaces and optional language tags before 'file:'
                file_blocks = re.findall(r'```(?:[a-zA-Z0-9_-]*\s*)?file:\s*([^\n]+)\n(.*?)```', self.last_response, re.DOTALL | re.IGNORECASE)
                for file_path, content in file_blocks:
                    file_path = file_path.strip()
                    try:
                        # Create directories if they don't exist
                        os.makedirs(os.path.dirname(os.path.abspath(file_path)) or '.', exist_ok=True)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        console.print(f"[bold green]✓ Aura successfully created/edited file: {file_path}[/bold green]")
                    except Exception as e:
                        console.print(f"[bold red]✗ Aura failed to write to {file_path}: {e}[/bold red]")
                        
                # 2. Handle Shell Execution
                # Regex made more robust to handle varying formatting of bash:run
                cmd_blocks = re.findall(r'```(?:bash:run|run:bash)\s*\n(.*?)```', self.last_response, re.DOTALL | re.IGNORECASE)
                for cmd in cmd_blocks:
                    cmd = cmd.strip()
                    console.print(f"\n[bold yellow]⚡ Aura wants to execute the following command:[/bold yellow]\n[cyan]{cmd}[/cyan]")
                    choice = console.input(f"[{self.theme_color}]Execute this command? (y/N): [/{self.theme_color}]").strip().lower()
                    if choice == 'y':
                        try:
                            result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
                            if result.returncode == 0:
                                console.print(f"[bold green]✓ Command executed successfully.[/bold green]")
                                if result.stdout:
                                    console.print(f"[dim]{result.stdout.strip()}[/dim]")
                            else:
                                console.print(f"[bold red]✗ Command failed with exit code {result.returncode}[/bold red]")
                                if result.stderr:
                                    console.print(f"[red]{result.stderr.strip()}[/red]")
                        except Exception as e:
                            console.print(f"[bold red]✗ Failed to execute command: {e}[/bold red]")
                    else:
                        console.print("[dim]Command skipped.[/dim]")
                
            except KeyboardInterrupt:
                console.print(f"\n\n[{self.theme_color}]✧ {self.name}[/{self.theme_color}]\nSession terminated. Goodbye!\n")
                break
            except Exception as e:
                console.print(f"\n[bold red]An error occurred:[/bold red] {e}")

if __name__ == "__main__":
    bot = AuraBot()
    bot.run()