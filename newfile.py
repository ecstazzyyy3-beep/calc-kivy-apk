# main.py  — Калькулятор (Kivy)
# Сделано под Pydroid 3 — полноэкранный, тёмно-серый фон, кнопки и логика (sqrt, sin, cos, tan, log, π, e, %, Inv, Deg, Ans и т.д.)

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.properties import StringProperty
import math, ast, operator

# FULLSCREEN
try:
    Window.fullscreen = True
except Exception:
    pass
Window.clearcolor = get_color_from_hex('#202020')  # темно-серый фон как в файле

# Безопасный eval через AST (разрешённые операции и функции)
SAFE_NAMES = {
    'pi': math.pi,
    'e': math.e,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sqrt': math.sqrt,
    'log': math.log,  # log(x, base) or natural if one arg
    'ln': math.log,
    'abs': abs,
    'round': round,
    'floor': math.floor,
    'ceil': math.ceil,
    # extra
    'pow': pow,
}

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

def safe_eval(expr, ans_value=0, deg_mode=False):
    """
    Evaluate mathematical expression safely using AST.
    Supports functions from SAFE_NAMES and numbers.
    Replaces percent and π and Ans.
    deg_mode: if True, trig functions expect degrees.
    """
    if expr.strip() == '':
        return ''
    # replacements to match common input
    expr = expr.replace('×', '*').replace('÷', '/').replace('^', '**')
    expr = expr.replace('π', 'pi').replace('Π', 'pi')
    expr = expr.replace('Ans', f'({ans_value})')
    # handle percentage: convert number% to (number/100)
    # naive approach: replace occurrences of digits% with (digits/100)
    import re
    expr = re.sub(r'(\d+(\.\d+)?)\s*%', r'(\1/100)', expr)
    # parse
    try:
        node = ast.parse(expr, mode='eval')
    except Exception as e:
        raise ValueError("Syntax error")
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Num):  # < Py3.8
            return node.n
        if getattr(ast, 'Constant', None) and isinstance(node, ast.Constant):  # Py3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Unsupported constant")
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
            raise ValueError("Unsupported binary operator")
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](operand)
            raise ValueError("Unsupported unary operator")
        if isinstance(node, ast.Call):
            # function call
            func = node.func
            if isinstance(func, ast.Name):
                fname = func.id
                if fname in SAFE_NAMES:
                    f = SAFE_NAMES[fname]
                    args = [_eval(a) for a in node.args]
                    # handle degrees conversion if needed
                    if deg_mode and fname in ('sin','cos','tan','asin','acos','atan'):
                        # if function is inverse (asin etc) we'll convert result later
                        if fname in ('sin','cos','tan'):
                            # convert degrees to radians for input
                            args = [math.radians(a) for a in args]
                        # for asin/acos/atan: will return radians, convert to degrees after
                    res = f(*args)
                    if deg_mode and fname in ('asin','acos','atan'):
                        return math.degrees(res)
                    return res
            raise ValueError("Function not allowed")
        if isinstance(node, ast.Name):
            if node.id in SAFE_NAMES:
                return SAFE_NAMES[node.id]
            raise ValueError("Unknown identifier")
        raise ValueError("Unsupported expression")
    val = _eval(node)
    # final type check
    if isinstance(val, (int, float)):
        return val
    raise ValueError("Result not numeric")

# Основной виджет
class CalcRoot(BoxLayout):
    display_text = StringProperty('')
    ans = 0
    deg_mode = False  # Degree mode off by default

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.padding = [8, 8, 8, 8]
        # Display (верх)
        self.display = Label(text='', size_hint=(1, 0.18), halign='right', valign='center',
                             text_size=(Window.width - 40, None),
                             font_size='40sp', color=get_color_from_hex('#FFFFFF'))
        # фоновый контейнер для display
        disp_box = BoxLayout(size_hint=(1, 0.18), padding=[12,12,12,12])
        disp_box.add_widget(self.display)
        self.add_widget(disp_box)

        # Кнопки — точно как в файле (берём привычную раскладку)
        buttons = [
            ['C', 'DEL', 'Ans', 'Inv'],
            ['sin', 'cos', 'tan', 'Deg'],
            ['7','8','9','/'],
            ['4','5','6','*'],
            ['1','2','3','-'],
            ['0','.','%','+'],
            ['π','sqrt','log','=']
        ]
        # grid
        grid = GridLayout(cols=4, spacing=8, padding=[8,8,8,8], size_hint=(1, 0.82))
        # button colors
        self.btn_bg_main = get_color_from_hex('#2e2e2e')  # основной темно-серый кнопок
        self.btn_bg_func = get_color_from_hex('#3b82f6')  # синий для функций
        self.btn_bg_equal = get_color_from_hex('#ff8c00')  # оранжевый для "="
        self.btn_text = get_color_from_hex('#FFFFFF')

        for row in buttons:
            for key in row:
                btn = Button(text=key, font_size='28sp', background_normal='',
                             background_color=self._btn_color_for(key),
                             color=self.btn_text,
                             halign='center', valign='middle')
                btn.bind(on_release=self.on_button)
                grid.add_widget(btn)
        self.add_widget(grid)

    def _btn_color_for(self, key):
        if key == '=':
            return self.btn_bg_equal
        if key in ('C','DEL','Inv','Deg','Ans'):
            return get_color_from_hex('#6b7280')  # серо-голубой (особые)
        if key in ('sin','cos','tan','sqrt','log','π'):
            return self.btn_bg_func
        # основной
        return self.btn_bg_main

    def on_button(self, instance):
        key = instance.text
        if key == 'C':
            self.display.text = ''
        elif key == 'DEL':
            self.display.text = self.display.text[:-1]
        elif key == 'Ans':
            self.display.text += 'Ans'
        elif key == 'Inv':
            # inverse: toggle 1/x when pressed or mark; simplest: insert '1/('
            self.display.text += '1/('
        elif key == 'Deg':
            # toggle degree mode
            self.deg_mode = not self.deg_mode
            # визуальное подтверждение — добавить/убрать текст [DEG]
            if self.deg_mode:
                if '[DEG]' not in self.display.text:
                    self.display.text = '[DEG] ' + self.display.text
            else:
                self.display.text = self.display.text.replace('[DEG] ', '')
        elif key == '=':
            expr = self.display.text.replace('[DEG] ', '')
            try:
                value = safe_eval(expr, ans_value=self.ans, deg_mode=self.deg_mode)
                # форматирование: если целое — без .0
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                self.ans = value
                self.display.text = str(value)
            except Exception as e:
                self.display.text = 'Error'
        elif key == 'π':
            self.display.text += 'π'
        elif key == 'sqrt':
            self.display.text += 'sqrt('
        elif key == 'log':
            self.display.text += 'log('
        elif key in ('sin','cos','tan'):
            self.display.text += f'{key}('
        else:
            # цифры, точка, операторы
            self.display.text += key

class CalculatorApp(App):
    def build(self):
        self.title = 'Калькулятор'
        root = CalcRoot()
        # bind display label to property
        def update_label(instance, value):
            root.display.text = value
        root.bind(display_text=update_label)
        # initialize display
        root.display.text = ''
        return root

if __name__ == '__main__':
    CalculatorApp().run()