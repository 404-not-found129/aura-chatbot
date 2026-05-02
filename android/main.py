"""
Aura - Android chat app (Kivy)
"""
import os
import json
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex as hex_c
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.core.window import Window
from kivy.properties import ListProperty

# ── Palette ────────────────────────────────────────────────────────────────────

BG       = hex_c('#0d0d1a')
SURFACE  = hex_c('#1a1a2e')
INPUT_BG = hex_c('#111126')
PURPLE   = hex_c('#9b59b6')
USR_BG   = hex_c('#5c3484')
AI_BG    = hex_c('#1c2336')
WHITE    = hex_c('#e8e8f4')
DIM      = hex_c('#7777aa')
BLUE     = hex_c('#3498db')
GREEN    = hex_c('#27ae60')
ORANGE   = hex_c('#e67e22')
RED      = hex_c('#e74c3c')

PROVIDER_LABEL = {'gemini': 'Gemini', 'openai': 'GPT', 'claude': 'Claude'}
PROVIDER_COLOR = {'gemini': BLUE,     'openai': GREEN,  'claude': ORANGE}

MODELS = {
    'gemini': ['gemini-3.1-pro-preview', 'gemini-3-pro-preview', 'gemini-2.5-pro',
               'gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.0-flash'],
    'openai': ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'o3', 'o4-mini'],
    'claude': ['claude-opus-4-7', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
}
DEFAULT_MODEL = {
    'gemini': 'gemini-2.5-flash',
    'openai': 'gpt-4o',
    'claude': 'claude-sonnet-4-6',
}

SYSTEM = (
    "You are Aura, an expert AI coding assistant. "
    "Be concise. Omit all conversational filler. Answer immediately. "
    "Use markdown for code blocks."
)

# ── Config persistence ─────────────────────────────────────────────────────────

def _cfg_path():
    return os.path.join(App.get_running_app().user_data_dir, 'config.json')

def load_cfg() -> dict:
    d = {
        'provider': 'gemini', 'model': 'gemini-2.5-flash',
        'gemini_key': '', 'openai_key': '', 'claude_key': '',
    }
    try:
        with open(_cfg_path()) as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d

def save_cfg(d: dict):
    try:
        with open(_cfg_path(), 'w') as f:
            json.dump(d, f)
    except Exception:
        pass

# ── AI streaming ───────────────────────────────────────────────────────────────

def stream_ai(provider, model, api_key, history, on_chunk, on_done):
    def _run():
        try:
            if provider == 'gemini':
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                contents = [
                    types.Content(
                        role='user' if m['role'] == 'user' else 'model',
                        parts=[types.Part(text=m['content'])]
                    )
                    for m in history
                ]
                for chunk in client.models.generate_content_stream(
                    model=model, contents=contents,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM)
                ):
                    if chunk.text:
                        Clock.schedule_once(lambda dt, t=chunk.text: on_chunk(t))
                Clock.schedule_once(lambda dt: on_done(None))

            elif provider == 'openai':
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                msgs = [{'role': 'system', 'content': SYSTEM}] + history
                for chunk in client.chat.completions.create(
                    model=model, messages=msgs, stream=True
                ):
                    t = chunk.choices[0].delta.content or ''
                    if t:
                        Clock.schedule_once(lambda dt, t=t: on_chunk(t))
                Clock.schedule_once(lambda dt: on_done(None))

            elif provider == 'claude':
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                with client.messages.stream(
                    model=model, max_tokens=4096,
                    system=SYSTEM, messages=history
                ) as s:
                    for t in s.text_stream:
                        Clock.schedule_once(lambda dt, t=t: on_chunk(t))
                Clock.schedule_once(lambda dt: on_done(None))

        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): on_done(err))

    threading.Thread(target=_run, daemon=True).start()

# ── Reusable widgets ───────────────────────────────────────────────────────────

class RoundedBox(BoxLayout):
    """BoxLayout with a rounded-rectangle canvas background."""
    bg_color = ListProperty([0.11, 0.14, 0.21, 1])
    radius    = ListProperty([dp(14)])

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*self.bg_color)
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
        self.bind(pos=self._sync, size=self._sync,
                  bg_color=lambda *_: setattr(self._c, 'rgba', self.bg_color))

    def _sync(self, *_):
        self._r.pos    = self.pos
        self._r.size   = self.size
        self._r.radius = self.radius


def flat_btn(text, bg=SURFACE, fg=WHITE, font_size=sp(14), **kw) -> Button:
    """Create a button with a solid background and no Kivy default styling."""
    btn = Button(
        text=text, font_size=font_size,
        background_normal='', background_color=bg,
        color=fg, **kw
    )
    return btn


class Bubble(Label):
    """Auto-sizing text bubble with a rounded rect background."""

    def __init__(self, text='', is_user=True, **kw):
        self.is_user = is_user
        max_w = min(Window.width * 0.78, dp(340))
        super().__init__(
            text=text,
            markup=False,
            color=WHITE,
            font_size=sp(14.5),
            size_hint=(None, None),
            text_size=(max_w, None),
            halign='left',
            valign='top',
            padding=(dp(14), dp(10)),
            **kw
        )
        bg = list(USR_BG) + [1] if is_user else list(AI_BG) + [1]
        r  = [dp(16), dp(4), dp(16), dp(16)] if is_user else [dp(4), dp(16), dp(16), dp(16)]
        with self.canvas.before:
            self._bg_color = Color(*bg)
            self._bg_rect  = RoundedRectangle(pos=self.pos, size=self.size, radius=r)
        self.bind(
            texture_size=self._on_texture,
            pos=self._sync_bg,
            size=self._sync_bg,
        )

    def _on_texture(self, _, ts):
        self.size = ts[0] + dp(28), ts[1] + dp(20)

    def _sync_bg(self, *_):
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size

    def append(self, chunk: str):
        self.text += chunk


class MessageRow(BoxLayout):
    """Horizontal row that positions a bubble left (AI) or right (user)."""

    def __init__(self, bubble: Bubble, **kw):
        super().__init__(
            orientation='horizontal',
            size_hint_y=None,
            padding=[dp(10), dp(4)],
            spacing=dp(0),
            **kw
        )
        self._bubble = bubble
        if bubble.is_user:
            self.add_widget(Label(size_hint_x=1))
            self.add_widget(bubble)
        else:
            self.add_widget(bubble)
            self.add_widget(Label(size_hint_x=1))

        bubble.bind(size=self._sync_height)
        self.height = bubble.height + dp(8)

    def _sync_height(self, _, size):
        self.height = size[1] + dp(8)

# ── Settings screen ────────────────────────────────────────────────────────────

class SettingsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cfg = {}
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        root.canvas.before.clear()
        with root.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, 'pos', root.pos),
                  size=lambda *_: setattr(self._bg, 'size', root.size))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        back = flat_btn('← Back', bg=SURFACE, size_hint_x=None, width=dp(90))
        back.bind(on_release=lambda _: setattr(self.manager, 'current', 'chat'))
        hdr.add_widget(back)
        hdr.add_widget(Label(text='[b]Settings[/b]', markup=True, color=WHITE,
                              font_size=sp(18), halign='left',
                              text_size=(None, None)))
        root.add_widget(hdr)

        # Provider spinner
        root.add_widget(Label(text='Provider', color=DIM, font_size=sp(13),
                               size_hint_y=None, height=dp(22), halign='left',
                               text_size=(Window.width - dp(32), None)))
        self.provider_sp = Spinner(
            values=['gemini', 'openai', 'claude'],
            size_hint_y=None, height=dp(44),
            background_normal='', background_color=SURFACE,
            color=WHITE, font_size=sp(14),
        )
        self.provider_sp.bind(text=self._on_provider_change)
        root.add_widget(self.provider_sp)

        # Model spinner
        root.add_widget(Label(text='Model', color=DIM, font_size=sp(13),
                               size_hint_y=None, height=dp(22), halign='left',
                               text_size=(Window.width - dp(32), None)))
        self.model_sp = Spinner(
            size_hint_y=None, height=dp(44),
            background_normal='', background_color=SURFACE,
            color=WHITE, font_size=sp(13),
        )
        root.add_widget(self.model_sp)

        # API key inputs
        for label, attr in [
            ('Gemini API Key',  'gemini_inp'),
            ('OpenAI API Key',  'openai_inp'),
            ('Claude API Key',  'claude_inp'),
        ]:
            root.add_widget(Label(text=label, color=DIM, font_size=sp(13),
                                   size_hint_y=None, height=dp(22), halign='left',
                                   text_size=(Window.width - dp(32), None)))
            inp = TextInput(
                hint_text='Paste API key…',
                password=True,
                size_hint_y=None, height=dp(44),
                background_color=INPUT_BG,
                foreground_color=WHITE,
                hint_text_color=DIM,
                cursor_color=PURPLE,
                font_size=sp(13),
                multiline=False,
            )
            setattr(self, attr, inp)
            root.add_widget(inp)

        root.add_widget(Label(size_hint_y=1))  # spacer

        save_btn = flat_btn('Save & Apply', bg=PURPLE, font_size=sp(15),
                             size_hint_y=None, height=dp(50))
        save_btn.bind(on_release=self._save)
        root.add_widget(save_btn)

        self.add_widget(root)

    def on_enter(self):
        self.cfg = load_cfg()
        self.provider_sp.text = self.cfg.get('provider', 'gemini')
        self._refresh_models(self.cfg.get('provider', 'gemini'))
        self.model_sp.text = self.cfg.get('model', DEFAULT_MODEL['gemini'])
        self.gemini_inp.text = self.cfg.get('gemini_key', '')
        self.openai_inp.text = self.cfg.get('openai_key', '')
        self.claude_inp.text = self.cfg.get('claude_key', '')

    def _on_provider_change(self, _, value):
        self._refresh_models(value)
        self.model_sp.text = DEFAULT_MODEL.get(value, '')

    def _refresh_models(self, provider):
        self.model_sp.values = MODELS.get(provider, [])

    def _save(self, _):
        cfg = {
            'provider':   self.provider_sp.text,
            'model':      self.model_sp.text,
            'gemini_key': self.gemini_inp.text.strip(),
            'openai_key': self.openai_inp.text.strip(),
            'claude_key': self.claude_inp.text.strip(),
        }
        save_cfg(cfg)
        chat: ChatScreen = self.manager.get_screen('chat')
        chat.apply_cfg(cfg)
        self.manager.current = 'chat'

# ── Chat screen ────────────────────────────────────────────────────────────────

class ChatScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cfg      = load_cfg()
        self.history  = []
        self.streaming = False
        self._ai_row  = None

        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, 'pos', root.pos),
                  size=lambda *_: setattr(self._bg, 'size', root.size))

        # ── Header ────────────────────────────────────────────────────────────
        hdr = RoundedBox(
            orientation='horizontal',
            size_hint_y=None, height=dp(56),
            padding=[dp(14), dp(8)], spacing=dp(10),
            bg_color=list(SURFACE) + [1],
            radius=[0],
        )
        self.title_lbl = Label(
            text='✧ Aura',
            markup=True, color=WHITE,
            font_size=sp(17), bold=True,
            size_hint_x=None, width=dp(80),
            halign='left', text_size=(dp(80), None),
        )
        self.model_lbl = Label(
            text=self._model_text(),
            markup=True, color=DIM,
            font_size=sp(12),
            halign='left', text_size=(None, None),
        )
        settings_btn = flat_btn('⚙', bg=SURFACE, fg=DIM,
                                 font_size=sp(20),
                                 size_hint=(None, None),
                                 size=(dp(44), dp(44)))
        settings_btn.bind(on_release=lambda _: setattr(
            self.manager, 'current', 'settings'))
        hdr.add_widget(self.title_lbl)
        hdr.add_widget(self.model_lbl)
        hdr.add_widget(settings_btn)
        root.add_widget(hdr)

        # ── Chat area ─────────────────────────────────────────────────────────
        self.scroll = ScrollView(do_scroll_x=False)
        self.chat_grid = GridLayout(
            cols=1, spacing=dp(6),
            size_hint_y=None, padding=[0, dp(8)],
        )
        self.chat_grid.bind(minimum_height=self.chat_grid.setter('height'))
        self.scroll.add_widget(self.chat_grid)
        root.add_widget(self.scroll)

        # ── Input bar ─────────────────────────────────────────────────────────
        bar = RoundedBox(
            orientation='horizontal',
            size_hint_y=None, height=dp(62),
            padding=[dp(10), dp(8)], spacing=dp(8),
            bg_color=list(SURFACE) + [1],
            radius=[0],
        )
        self.text_input = TextInput(
            hint_text='Message Aura…',
            multiline=False,
            background_color=INPUT_BG,
            foreground_color=WHITE,
            hint_text_color=DIM,
            cursor_color=PURPLE,
            font_size=sp(15),
            padding=[dp(14), dp(10)],
        )
        self.text_input.bind(on_text_validate=self._send)
        send_btn = flat_btn('➤', bg=PURPLE, fg=WHITE,
                             font_size=sp(18),
                             size_hint=(None, None),
                             size=(dp(46), dp(46)))
        send_btn.bind(on_release=self._send)
        self.send_btn = send_btn
        bar.add_widget(self.text_input)
        bar.add_widget(send_btn)
        root.add_widget(bar)

        self.add_widget(root)
        self._add_welcome()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _model_text(self):
        p = self.cfg.get('provider', 'gemini')
        m = self.cfg.get('model', DEFAULT_MODEL[p])
        color = '#{:02x}{:02x}{:02x}'.format(
            int(PROVIDER_COLOR[p][0]*255),
            int(PROVIDER_COLOR[p][1]*255),
            int(PROVIDER_COLOR[p][2]*255),
        )
        return f'[color={color}]{PROVIDER_LABEL[p]}[/color]  [color=#7777aa]{m}[/color]'

    def _add_welcome(self):
        b = Bubble(
            text='Hi! I\'m Aura, your AI coding assistant.\nHow can I help you today?',
            is_user=False,
        )
        self.chat_grid.add_widget(MessageRow(b))

    def _scroll_bottom(self, *_):
        self.scroll.scroll_y = 0

    def apply_cfg(self, cfg: dict):
        self.cfg     = cfg
        self.history = []
        self.model_lbl.text = self._model_text()

    def _get_api_key(self) -> str:
        p = self.cfg.get('provider', 'gemini')
        return self.cfg.get(f'{p}_key', '')

    def _show_error(self, msg: str):
        popup = Popup(
            title='Error',
            content=Label(text=msg, color=WHITE, text_size=(dp(260), None),
                           halign='center'),
            size_hint=(0.85, None), height=dp(180),
            background_color=list(SURFACE) + [1],
            title_color=RED,
        )
        popup.open()

    # ── Sending ───────────────────────────────────────────────────────────────

    def _send(self, *_):
        if self.streaming:
            return
        text = self.text_input.text.strip()
        if not text:
            return

        key = self._get_api_key()
        if not key:
            self._show_error(
                f'No API key set for {PROVIDER_LABEL[self.cfg["provider"]]}.\n'
                'Tap ⚙ to add one in Settings.'
            )
            return

        self.text_input.text = ''

        # User bubble
        ub = Bubble(text=text, is_user=True)
        self.chat_grid.add_widget(MessageRow(ub))
        self.history.append({'role': 'user', 'content': text})
        Clock.schedule_once(self._scroll_bottom, 0.05)

        # Thinking bubble
        ab = Bubble(text='● ● ●', is_user=False)
        ai_row = MessageRow(ab)
        self.chat_grid.add_widget(ai_row)
        self._ai_row = ai_row
        self._ai_bubble = ab
        self._ai_text = ''
        self.streaming = True
        self.send_btn.disabled = True
        Clock.schedule_once(self._scroll_bottom, 0.05)

        stream_ai(
            provider=self.cfg.get('provider', 'gemini'),
            model=self.cfg.get('model', 'gemini-2.5-flash'),
            api_key=key,
            history=self.history,
            on_chunk=self._on_chunk,
            on_done=self._on_done,
        )

    def _on_chunk(self, text: str):
        if not self._ai_text:
            self._ai_bubble.text = text  # replace "● ● ●" placeholder
        else:
            self._ai_bubble.text += text
        self._ai_text += text
        Clock.schedule_once(self._scroll_bottom, 0)

    def _on_done(self, error):
        self.streaming = False
        self.send_btn.disabled = False
        if error:
            self._ai_bubble.text = f'Error: {error}'
            Clock.schedule_once(self._scroll_bottom, 0.05)
        else:
            self.history.append({'role': 'assistant', 'content': self._ai_text})
        self._ai_row = None

# ── App ────────────────────────────────────────────────────────────────────────

class AuraApp(App):
    def build(self):
        Window.clearcolor = BG
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(ChatScreen(name='chat'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm


if __name__ == '__main__':
    AuraApp().run()
