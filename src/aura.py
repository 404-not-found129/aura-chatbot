import os
import sys
import re
import glob
import subprocess
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.spinner import Spinner
from rich.rule import Rule
from rich.columns import Columns
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

console = Console()


class SlashCommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith('/') and ' ' not in text:
            for cmd in self.commands:
                if cmd.startswith(text.lower()):
                    yield Completion(cmd, start_position=-len(text))


MODELS = {
    "gemini": [
        ("gemini-3.1-pro-preview", "Latest Gemini 3 Pro"),
        ("gemini-3-pro-preview",   "Gemini 3 Pro"),
        ("gemini-2.5-pro",         "Most capable 2.5, best for complex tasks"),
        ("gemini-2.5-flash",       "Fast & smart, recommended default"),
        ("gemini-2.5-flash-lite",  "Fastest & most efficient"),
        ("gemini-2.0-flash",       "Stable, reliable performance"),
        ("gemini-2.0-flash-lite",  "Lightweight, low latency"),
    ],
    "openai": [
        ("gpt-4o",       "GPT-4o, fast and capable"),
        ("gpt-4o-mini",  "GPT-4o Mini, faster and cheaper"),
        ("gpt-4.1",      "GPT-4.1, latest flagship"),
        ("gpt-4.1-mini", "GPT-4.1 Mini, efficient"),
        ("o3",           "o3, advanced reasoning"),
        ("o4-mini",      "o4-mini, fast reasoning"),
    ],
    "claude": [
        ("claude-opus-4-7",           "Most capable Claude"),
        ("claude-sonnet-4-6",         "Balanced performance"),
        ("claude-haiku-4-5-20251001", "Fastest Claude"),
    ],
}

DEFAULT_MODEL = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-6",
}

PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "openai": "OpenAI GPT",
    "claude": "Anthropic Claude",
}

PROVIDER_COLOR = {
    "gemini": "bright_blue",
    "openai": "bright_green",
    "claude": "orange3",
}


class AuraBot:
    def __init__(self):
        self.provider = os.getenv("AURA_PROVIDER", "gemini")
        self.model_name = os.getenv("AURA_MODEL", DEFAULT_MODEL.get(self.provider, "gemini-2.5-flash"))
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.claude_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_client = None
        self.gemini_chat = None
        self.openai_client = None
        self.claude_client = None
        self.history = []
        self.attached_files: dict[str, str] = {}
        self.name = "Aura"
        self.theme_color = "medium_purple1"
        self.version = "v1.6.0"
        self.use_web = os.getenv("AURA_USE_WEB", "false").lower() == "true"
        self.last_response = ""
        self.system_instruction = ""

        self.commands = [
            '/help', '/exit', '/quit', '/clear', '/init',
            '/save', '/system', '/web', '/websearch', '/model', '/provider',
            '/attach', '/detach', '/files',
        ]
        self.completer = SlashCommandCompleter(self.commands)
        self.session = PromptSession(completer=self.completer, complete_while_typing=True)

    # ── UI helpers ─────────────────────────────────────────────────────────────

    def _response_panel(self, content=None, thinking=False):
        provider_color = PROVIDER_COLOR[self.provider]
        title = (
            f"[{self.theme_color}]✧ {self.name}[/{self.theme_color}]"
            f"  [dim]{PROVIDER_LABELS[self.provider]}[/dim]"
            f"  [{provider_color}]{self.model_name}[/{provider_color}]"
        )
        if thinking:
            inner = Spinner("dots2", style=self.theme_color)
            border = "dim"
        else:
            inner = Markdown(content or "")
            border = self.theme_color
        return Panel(inner, title=title, border_style=border, box=box.ROUNDED, padding=(0, 1))

    def _print_attached_files_bar(self):
        if not self.attached_files:
            return
        names = "  ".join(
            f"[bold]{os.path.basename(p)}[/bold]" for p in self.attached_files
        )
        console.print(f"[dim]📎 {len(self.attached_files)} attached:[/dim]  {names}")

    # ── Core logic ─────────────────────────────────────────────────────────────

    def _build_system_instruction(self):
        instruction = """You are Aura, an expert AI programming assistant running in a user's terminal.
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
        To create or edit a file, you MUST format your markdown code block EXACTLY like this:

        ```file:src/main.py
        print("Hello world")
        ```

        **COMMAND EXECUTION (IMPORTANT):**
        You CAN execute shell commands. To protect the user's system, these commands are executed safely within an isolated virtual machine (Docker container).
        To execute a command, output it in a markdown block EXACTLY like this:
        ```bash:run
        ls -la
        ```
        The local application will intercept this and run it securely in the VM on your behalf.

        When you output these exact formats, the local Aura application automatically intercepts them. ALWAYS use these capabilities proactively."""

        if os.path.exists("AURA.md"):
            try:
                with open("AURA.md", "r") as f:
                    project_rules = f.read()
                instruction += f"\n\nPROJECT SPECIFIC INSTRUCTIONS (from AURA.md):\n{project_rules}"
            except Exception:
                pass

        return instruction

    def _build_user_message(self, user_input: str) -> str:
        if not self.attached_files:
            return user_input
        parts = ["[ATTACHED FILE CONTEXT]"]
        for path, content in self.attached_files.items():
            ext = os.path.splitext(path)[1].lstrip('.')
            parts.append(f"### {path}\n```{ext}\n{content}\n```")
        parts.append(f"[USER MESSAGE]\n{user_input}")
        return "\n\n".join(parts)

    def _save_env_var(self, key_name, key_value):
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        env_content = ""
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_content = f.read()
        if f"{key_name}=" in env_content:
            env_content = re.sub(rf'{key_name}=.*', f'{key_name}="{key_value}"', env_content)
        else:
            env_content += f'\n{key_name}="{key_value}"\n'
        with open(env_path, 'w') as f:
            f.write(env_content.strip() + "\n")

    def _prompt_for_key(self, key_name, label, help_url):
        key = ""
        console.print(f"[bold yellow]No {label} API key found.[/bold yellow]")
        console.print(f"Get one at: [cyan]{help_url}[/cyan]")
        while not key or key.strip() == "":
            key = console.input(f"\n[{self.theme_color}]Paste your {label} API key: [/{self.theme_color}]").strip()
        self._save_env_var(key_name, key)
        console.print(f"[bold green]API key saved to .env![/bold green]\n")
        return key

    # ── Provider init ──────────────────────────────────────────────────────────

    def _init_provider(self):
        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "claude":
            self._init_claude()

    def _init_gemini(self):
        with console.status(f"[dim]Initializing {self.name} with {self.model_name}...[/dim]", spinner="point"):
            from google import genai
            from google.genai import types
            self.system_instruction = self._build_system_instruction()
            if not self.gemini_client:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
            config_params = {"system_instruction": self.system_instruction}
            if self.use_web:
                config_params["tools"] = [{"google_search": {}}]
            self.gemini_chat = self.gemini_client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(**config_params)
            )

    def _init_openai(self):
        with console.status(f"[dim]Initializing {self.name} with {self.model_name}...[/dim]", spinner="point"):
            from openai import OpenAI
            self.system_instruction = self._build_system_instruction()
            self.openai_client = OpenAI(api_key=self.openai_key)
            self.history = []

    def _init_claude(self):
        with console.status(f"[dim]Initializing {self.name} with {self.model_name}...[/dim]", spinner="point"):
            import anthropic
            self.system_instruction = self._build_system_instruction()
            self.claude_client = anthropic.Anthropic(api_key=self.claude_key)
            self.history = []

    def _send_message_stream(self, user_input):
        message = self._build_user_message(user_input)

        if self.provider == "gemini":
            for chunk in self.gemini_chat.send_message_stream(message):
                if chunk.text:
                    yield chunk.text

        elif self.provider == "openai":
            self.history.append({"role": "user", "content": message})
            stream = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": self.system_instruction}] + self.history,
                stream=True
            )
            assistant_text = ""
            for chunk in stream:
                text = chunk.choices[0].delta.content or ""
                if text:
                    assistant_text += text
                    yield text
            self.history.append({"role": "assistant", "content": assistant_text})

        elif self.provider == "claude":
            self.history.append({"role": "user", "content": message})
            with self.claude_client.messages.stream(
                model=self.model_name,
                max_tokens=8096,
                system=self.system_instruction,
                messages=self.history
            ) as stream:
                assistant_text = ""
                for text in stream.text_stream:
                    assistant_text += text
                    yield text
            self.history.append({"role": "assistant", "content": assistant_text})

    # ── Dashboard ──────────────────────────────────────────────────────────────

    def draw_dashboard(self):
        left_text = Text()
        left_text.append("Welcome back!\n\n", style="bold")

        logo = """ █████╗ ██╗   ██╗██████╗  █████╗
██╔══██╗██║   ██║██╔══██╗██╔══██╗
███████║██║   ██║██████╔╝███████║
██╔══██║██║   ██║██╔══██╗██╔══██║
██║  ██║╚██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"""
        left_text.append(logo + "\n\n", style=self.theme_color)

        provider_color = PROVIDER_COLOR[self.provider]
        left_text.append(f"{PROVIDER_LABELS[self.provider]}  ", style=f"bold {provider_color}")
        left_text.append(f"{self.model_name}\n", style="bold green")

        if self.provider == "gemini":
            web_status = "● Enabled" if self.use_web else "○ Disabled"
            left_text.append(f"Web Search: {web_status}\n", style="cyan" if self.use_web else "dim")

        if self.attached_files:
            left_text.append(f"📎 {len(self.attached_files)} file(s) attached\n", style="yellow")

        user = os.getenv('USER', 'User')
        left_text.append(f"\n{user}'s Workspace\n", style="dim")
        cwd = os.getcwd()
        display_cwd = f"...{cwd[-35:]}" if len(cwd) > 38 else cwd
        left_text.append(f"{display_cwd}\n", style="dim")

        right_text = Text()
        right_text.append("Tips for getting started\n", style="bold")
        right_text.append("Type / to see the auto-complete command menu\n")
        right_text.append("Use /attach to give Aura context from your files\n")
        right_text.append("────────────────────────────────────────────────────\n", style="dim")
        right_text.append("What's new in v1.6.0\n", style="bold")
        right_text.append("• /attach <path> — share files as context (glob ok)\n")
        right_text.append("• /files — view and manage attached files\n")
        right_text.append("• Responses now shown in styled panels\n")
        right_text.append("• /provider to switch Gemini · GPT · Claude\n")
        right_text.append("• Loading spinner while waiting for response\n")

        table = Table.grid(padding=(0, 4))
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="left", ratio=1)
        table.add_row(left_text, right_text)

        console.print(Panel(
            table,
            title=f" {self.name} Code {self.version} ",
            border_style=self.theme_color,
            box=box.ROUNDED,
            expand=False,
            padding=(1, 2)
        ))

    # ── Setup / Run ────────────────────────────────────────────────────────────

    def setup(self):
        console.clear()
        self.draw_dashboard()

        if not self.gemini_key or self.gemini_key.strip() == "" or self.gemini_key == "your_api_key_here":
            self.gemini_key = self._prompt_for_key(
                "GEMINI_API_KEY", "Gemini", "https://aistudio.google.com/"
            )

        try:
            self._init_gemini()
        except Exception as e:
            console.print(f"[bold red]Failed to initialize {self.name}:[/bold red] {e}")
            sys.exit(1)

    def run(self):
        self.setup()

        while True:
            try:
                self._print_attached_files_bar()
                user_input = self.session.prompt(HTML("\n<b>You</b>\n<ansigray>▸ </ansigray>")).strip()

                if not user_input:
                    continue

                if user_input.startswith('/'):
                    # Preserve original casing for paths; use lowered only for cmd
                    cmd = user_input.split()[0].lower()
                    arg = user_input[len(cmd):].strip()

                    if cmd in ['/exit', '/quit']:
                        console.print(f"\n[{self.theme_color}]✧ {self.name}[/{self.theme_color}]  Goodbye!\n")
                        break

                    elif cmd == '/clear':
                        console.clear()
                        self.draw_dashboard()

                    elif cmd == '/init':
                        if os.path.exists("AURA.md"):
                            console.print("[yellow]AURA.md already exists in this directory.[/yellow]")
                        else:
                            with open("AURA.md", "w") as f:
                                f.write("# Aura Project Instructions\n\nAdd specific rules, architectural guidelines, or context for this project here.\nAura will automatically read these instructions on startup.")
                            console.print(f"[{self.theme_color}]Created AURA.md![/{self.theme_color}] I will remember the rules you write there.")
                            self._init_provider()

                    elif cmd == '/save':
                        if not self.last_response:
                            console.print("[yellow]No response to save yet![/yellow]")
                        else:
                            filename = console.input(f"[{self.theme_color}]Filename (e.g. script.py): [/{self.theme_color}]").strip()
                            if filename:
                                try:
                                    with open(filename, "w") as f:
                                        f.write(self.last_response)
                                    console.print(f"[bold green]✓ Saved to {filename}[/bold green]")
                                except Exception as e:
                                    console.print(f"[bold red]Failed: {e}[/bold red]")

                    elif cmd == '/system':
                        console.print(Panel(self.system_instruction, title="Active System Rules", border_style="cyan", box=box.ROUNDED))

                    elif cmd in ('/web', '/websearch'):
                        if self.provider != "gemini":
                            console.print("[yellow]Web Search is only available with the Gemini provider.[/yellow]")
                        else:
                            self.use_web = not self.use_web
                            self._save_env_var("AURA_USE_WEB", str(self.use_web).lower())
                            self._init_gemini()
                            console.clear()
                            self.draw_dashboard()

                    elif cmd == '/attach':
                        if not arg:
                            console.print("[yellow]Usage: /attach <filepath>  (glob patterns supported)[/yellow]")
                        else:
                            matches = glob.glob(arg, recursive=True)
                            if not matches:
                                console.print(f"[red]No files found matching:[/red] {arg}")
                            else:
                                added = []
                                for path in sorted(matches):
                                    if os.path.isfile(path):
                                        try:
                                            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                                                self.attached_files[path] = f.read()
                                            added.append(path)
                                        except Exception as e:
                                            console.print(f"[red]Could not read {path}: {e}[/red]")
                                if added:
                                    console.print(f"[bold green]✓ Attached {len(added)} file(s):[/bold green] " + "  ".join(f"[dim]{p}[/dim]" for p in added))

                    elif cmd == '/detach':
                        if not self.attached_files:
                            console.print("[dim]No files currently attached.[/dim]")
                        elif not arg:
                            count = len(self.attached_files)
                            self.attached_files.clear()
                            console.print(f"[dim]Detached all {count} file(s).[/dim]")
                        else:
                            if arg in self.attached_files:
                                del self.attached_files[arg]
                                console.print(f"[dim]Detached: {arg}[/dim]")
                            else:
                                console.print(f"[yellow]Not attached: {arg}[/yellow]")

                    elif cmd == '/files':
                        if not self.attached_files:
                            console.print("[dim]No files attached. Use /attach <path> to add files.[/dim]")
                        else:
                            rows = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                            rows.add_column("File", style="bold")
                            rows.add_column("Size", justify="right", style="dim")
                            rows.add_column("Lines", justify="right", style="dim")
                            for path, content in self.attached_files.items():
                                size = f"{len(content):,} chars"
                                lines = str(content.count('\n') + 1)
                                rows.add_row(path, size, lines)
                            console.print(Panel(rows, title=f"📎 Attached Files ({len(self.attached_files)})", border_style=self.theme_color, box=box.ROUNDED))

                    elif cmd == '/provider':
                        providers = list(PROVIDER_LABELS.keys())
                        console.print("\n[bold]Available Providers:[/bold]")
                        for i, p in enumerate(providers, 1):
                            color = PROVIDER_COLOR[p]
                            marker = " [bold green]← current[/bold green]" if p == self.provider else ""
                            console.print(f"  [{self.theme_color}]{i}[/{self.theme_color}]  [{color}]{PROVIDER_LABELS[p]}[/{color}]{marker}")
                        choice = console.input(f"\n[{self.theme_color}]Select provider (1-{len(providers)}, Enter to cancel): [/{self.theme_color}]").strip()
                        if choice.isdigit() and 1 <= int(choice) <= len(providers):
                            new_provider = providers[int(choice) - 1]
                            if new_provider == self.provider:
                                console.print("[dim]Provider unchanged.[/dim]")
                            else:
                                self.provider = new_provider
                                self.model_name = DEFAULT_MODEL[self.provider]
                                self._save_env_var("AURA_PROVIDER", self.provider)
                                self._save_env_var("AURA_MODEL", self.model_name)
                                if self.provider == "openai" and (not self.openai_key or not self.openai_key.strip()):
                                    self.openai_key = self._prompt_for_key("OPENAI_API_KEY", "OpenAI", "https://platform.openai.com/api-keys")
                                elif self.provider == "claude" and (not self.claude_key or not self.claude_key.strip()):
                                    self.claude_key = self._prompt_for_key("ANTHROPIC_API_KEY", "Anthropic Claude", "https://console.anthropic.com/")
                                try:
                                    self._init_provider()
                                    console.clear()
                                    self.draw_dashboard()
                                    console.print(f"[bold green]✓ Switched to {PROVIDER_LABELS[self.provider]} · {self.model_name}[/bold green]")
                                except Exception as e:
                                    console.print(f"[bold red]Failed to initialize provider: {e}[/bold red]")
                        elif choice:
                            console.print("[dim]Provider unchanged.[/dim]")

                    elif cmd == '/model':
                        models = MODELS[self.provider]
                        console.print(f"\n[bold]Models — {PROVIDER_LABELS[self.provider]}:[/bold]")
                        for i, (name, desc) in enumerate(models, 1):
                            marker = " [bold green]← current[/bold green]" if name == self.model_name else ""
                            console.print(f"  [{self.theme_color}]{i}[/{self.theme_color}]  {name:<35} [dim]{desc}[/dim]{marker}")
                        choice = console.input(f"\n[{self.theme_color}]Select model (1-{len(models)}, Enter to cancel): [/{self.theme_color}]").strip()
                        if choice.isdigit() and 1 <= int(choice) <= len(models):
                            self.model_name = models[int(choice) - 1][0]
                            self._save_env_var("AURA_MODEL", self.model_name)
                            self._init_provider()
                            console.clear()
                            self.draw_dashboard()
                            console.print(f"[bold green]✓ Switched to {self.model_name}[/bold green]")
                        elif choice:
                            console.print("[dim]Model unchanged.[/dim]")

                    elif cmd == '/help':
                        help_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                        help_table.add_column(style=self.theme_color, no_wrap=True)
                        help_table.add_column()
                        help_table.add_row("/attach <path>", "Attach file(s) as context for the AI (glob patterns ok)")
                        help_table.add_row("/detach [path]", "Remove attached file(s) — omit path to clear all")
                        help_table.add_row("/files",         "List currently attached files")
                        help_table.add_row("/provider",      "Switch between Gemini, GPT, and Claude")
                        help_table.add_row("/model",         "Switch models for the current provider")
                        help_table.add_row("/web",           "Toggle Google Search grounding (Gemini only)")
                        help_table.add_row("/init",          "Create AURA.md for project-specific rules")
                        help_table.add_row("/save",          "Save last response to a file")
                        help_table.add_row("/system",        "View active system instructions")
                        help_table.add_row("/clear",         "Clear screen and reload dashboard")
                        help_table.add_row("/exit",          "Quit Aura")
                        console.print(Panel(help_table, title="Commands", border_style=self.theme_color, box=box.ROUNDED))

                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]  Type /help for a list of commands.")

                    continue

                # ── Send message ───────────────────────────────────────────────
                console.print()
                self.last_response = ""
                chunk_counter = 0
                first_chunk = True

                with Live(self._response_panel(thinking=True), console=console, refresh_per_second=12) as live:
                    for text in self._send_message_stream(user_input):
                        self.last_response += text
                        chunk_counter += 1
                        if first_chunk:
                            live.update(self._response_panel(self.last_response))
                            first_chunk = False
                        elif chunk_counter % 4 == 0:
                            live.update(self._response_panel(self.last_response))
                    live.update(self._response_panel(self.last_response))

                # ── Post-process: write files ──────────────────────────────────
                file_blocks = re.findall(
                    r'```(?:[a-zA-Z0-9_-]*\s*)?file:\s*([^\n]+)\n(.*?)```',
                    self.last_response, re.DOTALL | re.IGNORECASE
                )
                workspace_root = os.path.abspath(os.getcwd())
                for file_path, content in file_blocks:
                    file_path = file_path.strip()
                    try:
                        # Prevent path traversal: resolve path and ensure it's within workspace
                        target_path = os.path.abspath(os.path.join(workspace_root, file_path.lstrip('/\\')))
                        if os.path.commonpath([workspace_root, target_path]) != workspace_root:
                            raise PermissionError(f"Cannot write outside of workspace: {target_path}")
                            
                        os.makedirs(os.path.dirname(target_path) or '.', exist_ok=True)
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        console.print(f"[bold green]✓ Wrote:[/bold green] {os.path.relpath(target_path, workspace_root)}")
                    except Exception as e:
                        console.print(f"[bold red]✗ Failed to write {file_path}: {e}[/bold red]")

                # ── Post-process: run commands ─────────────────────────────────
                cmd_blocks = re.findall(
                    r'```(?:bash:run|run:bash)\s*\n(.*?)```',
                    self.last_response, re.DOTALL | re.IGNORECASE
                )
                for shell_cmd in cmd_blocks:
                    shell_cmd = shell_cmd.strip()
                    console.print(Panel(
                        f"[cyan]{shell_cmd}[/cyan]",
                        title="[bold yellow]⚡ Aura wants to run in VM (Docker)[/bold yellow]",
                        border_style="yellow", box=box.ROUNDED
                    ))
                    choice = console.input(f"[{self.theme_color}]Execute in isolated VM? (y/N): [/{self.theme_color}]").strip().lower()
                    if choice == 'y':
                        import shlex
                        # Sandbox command in a Docker container acting as a VM
                        # Use the host's real workspace path for the nested volume mount
                        host_workspace = os.getenv("HOST_WORKSPACE", os.getcwd())
                        docker_cmd = f'docker run --rm -v "{host_workspace}:/workspace" -w /workspace python:3.11-slim bash -c {shlex.quote(shell_cmd)}'
                        result = subprocess.run(docker_cmd, shell=True, text=True, capture_output=True)
                        if result.returncode == 0:
                            console.print(f"[bold green]✓ Done[/bold green]")
                            if result.stdout:
                                console.print(f"[dim]{result.stdout.strip()}[/dim]")
                        else:
                            console.print(f"[bold red]✗ Exit {result.returncode}[/bold red]")
                            if result.stderr:
                                console.print(f"[red]{result.stderr.strip()}[/red]")
                    else:
                        console.print("[dim]Skipped.[/dim]")

            except KeyboardInterrupt:
                console.print(f"\n[{self.theme_color}]✧ {self.name}[/{self.theme_color}]  Session terminated. Goodbye!\n")
                break
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    bot = AuraBot()
    bot.run()
