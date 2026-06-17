"""
Laberinto Kivy - Compatible Android APK
Sin pygame, sin buildozer errors.
"""

import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import (
    Color, Rectangle, Ellipse, Line, Canvas
)
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.vector import Vector
from kivy.metrics import dp


# ==================== CONFIG ====================
GROSOR    = dp(3)
FPS       = 60
DPAD_AREA = 0.28   # 28% inferior de la pantalla para botones


# ==================== GENERADOR LABERINTO ====================
def generar_laberinto(cols, filas):
    paredes  = [[{'D': True, 'B': True} for _ in range(cols)] for _ in range(filas)]
    visitado = [[False] * cols for _ in range(filas)]

    def vecinos(f, c):
        v = []
        if f > 0:         v.append((f-1, c, 'A'))
        if f < filas - 1: v.append((f+1, c, 'B'))
        if c > 0:         v.append((f, c-1, 'I'))
        if c < cols - 1:  v.append((f, c+1, 'D'))
        return v

    pila = [(0, 0)]
    visitado[0][0] = True
    while pila:
        f, c = pila[-1]
        no_vis = [(nf, nc, d) for nf, nc, d in vecinos(f, c) if not visitado[nf][nc]]
        if no_vis:
            nf, nc, d = random.choice(no_vis)
            if d == 'D': paredes[f][c]['D']   = False
            if d == 'B': paredes[f][c]['B']   = False
            if d == 'I': paredes[nf][nc]['D'] = False
            if d == 'A': paredes[nf][nc]['B'] = False
            visitado[nf][nc] = True
            pila.append((nf, nc))
        else:
            pila.pop()
    return paredes


# ==================== WIDGET PRINCIPAL ====================
class LaberintoWidget(Widget):

    # Colores por nivel (r,g,b,a)
    COLORES_PARED = [
        (0.12, 0.12, 0.12, 1),
        (0.08, 0.16, 0.32, 1),
        (0.24, 0.08, 0.08, 1),
        (0.08, 0.24, 0.08, 1),
    ]
    COLORES_FONDO = [
        (0.94, 0.94, 0.92, 1),
        (0.86, 0.90, 0.96, 1),
        (0.96, 0.86, 0.86, 1),
        (0.86, 0.96, 0.86, 1),
    ]
    POWERUP_TIPOS = {
        "velocidad": {"color": (1, 0.78, 0, 1),   "icono": "V", "duracion": 5},
        "vision":    {"color": (0.39, 1, 0.78, 1), "icono": "?", "duracion": 7},
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nivel         = 1
        self.ganado        = False
        self.tiempo_inicio = Clock.get_time()
        self.tiempo_ganado = 0

        # Estado táctil D-pad
        self.touch_dir = {'dx': 0, 'dy': 0}
        self.dpad_touches = {}   # touch.uid → dirección

        # Estado jugador
        self.px = 0.0
        self.py = 0.0
        self.vel_base  = 0.0
        self.vel       = 0.0
        self.vision_activa   = False
        self.powerup_activo  = None
        self.powerup_fin     = 0.0

        # Power-ups en el mapa: lista de {'cx','cy','tipo','activo'}
        self.powerups = []

        # Dimensiones calculadas en on_size
        self.celda  = 1
        self.cols   = 1
        self.filas  = 1
        self.ax     = 0
        self.ay     = 0
        self.aw     = 0
        self.ah     = 0
        self.maze_h = 0
        self.paredes = []
        self.pared_rects = []   # lista de (x,y,w,h)

        # D-pad botones: nombre → (cx,cy,radio)
        self.dpad_btns = {}
        self.dpad_activos = set()

        bind_size = self.bind(size=self._on_size, pos=self._on_size)
        Window.bind(on_resize=self._on_window_resize)
        Clock.schedule_interval(self._update, 1.0 / FPS)

    # -------- Layout --------
    def _on_window_resize(self, window, w, h):
        self._recalcular()

    def _on_size(self, *args):
        self._recalcular()

    def _recalcular(self):
        sw, sh = self.width or Window.width, self.height or Window.height
        if sw < 10 or sh < 10:
            return

        borde      = dp(8)
        btn_area_h = int(sh * DPAD_AREA)
        self.maze_h = sh - btn_area_h

        self.ax = borde
        self.ay = btn_area_h + borde          # Kivy Y desde abajo
        self.aw = sw - borde * 2
        self.ah = self.maze_h - borde * 2

        self.celda  = max(dp(36), min(dp(56), self.ah // 14))
        self.cols   = int(self.aw // self.celda)
        self.filas  = int(self.ah // self.celda)
        self.vel_base = max(dp(2), self.celda / 16)
        self.vel      = self.vel_base

        self._nuevo_nivel_interno()
        self._recalcular_dpad(sw, sh, btn_area_h)
        self.canvas.ask_update()

    def _recalcular_dpad(self, sw, sh, btn_area_h):
        zona_cy = btn_area_h // 2
        radio   = int(btn_area_h * 0.28)
        paso    = int(radio * 2.3)
        cx_base = sw // 4
        self.dpad_btns = {
            'ARR': (cx_base,        zona_cy + radio + dp(4), radio),
            'ABJ': (cx_base,        zona_cy - radio - dp(4), radio),
            'IZQ': (cx_base - paso, zona_cy,                 radio),
            'DER': (cx_base + paso, zona_cy,                 radio),
        }

    # -------- Nuevo nivel --------
    def _nuevo_nivel_interno(self):
        self.paredes     = generar_laberinto(self.cols, self.filas)
        self.pared_rects = self._construir_paredes()
        self._crear_powerups()

        # Posición inicial: centro celda (0,0) en coords Kivy
        self.px = float(self.ax + self.celda * 0.5)
        self.py = float(self.ay + (self.filas - 1) * self.celda + self.celda * 0.5)

        self.ganado       = False
        self.tiempo_inicio = Clock.get_time()
        self.tiempo_ganado = 0
        self.vision_activa  = False
        self.powerup_activo = None

        if self.vel != self.vel_base:
            self.vel = self.vel_base

    def _construir_paredes(self):
        rects = []
        ax, ay, aw, ah = self.ax, self.ay, self.aw, self.ah
        g = GROSOR
        c = self.celda

        # Borde exterior
        rects.append((ax,           ay,           aw, g))           # techo
        rects.append((ax,           ay + ah - g,  aw, g))           # suelo
        rects.append((ax,           ay,           g,  ah))          # izq
        rects.append((ax + aw - g,  ay,           g,  ah))          # der

        for f in range(self.filas):
            for col in range(self.cols):
                # En Kivy Y crece hacia arriba: fila 0 = arriba → mayor Y
                x = ax + col * c
                y = ay + (self.filas - 1 - f) * c
                if self.paredes[f][col]['D'] and col < self.cols - 1:
                    rects.append((x + c - g, y, g * 2, c + g))
                if self.paredes[f][col]['B'] and f < self.filas - 1:
                    rects.append((x, y - g, c + g, g * 2))
        return rects

    def _crear_powerups(self):
        self.powerups = []
        usadas = {(0, 0), (self.filas-1, self.cols-1)}
        tipos  = list(self.POWERUP_TIPOS.keys())
        intentos = 0
        while len(self.powerups) < 6 and intentos < 200:
            intentos += 1
            f = random.randint(1, self.filas - 2)
            col = random.randint(1, self.cols - 2)
            if (f, col) not in usadas:
                usadas.add((f, col))
                cx = self.ax + col * self.celda + self.celda * 0.5
                cy = self.ay + (self.filas - 1 - f) * self.celda + self.celda * 0.5
                self.powerups.append({
                    'cx': cx, 'cy': cy,
                    'tipo': random.choice(tipos),
                    'activo': True
                })

    # -------- Update loop --------
    def _update(self, dt):
        if not self.paredes:
            return

        ahora = Clock.get_time()

        if not self.ganado:
            self._mover_jugador()
            self._check_powerups(ahora)
            self._check_meta()

        self._dibujar()

    def _mover_jugador(self):
        dx = self.touch_dir['dx'] * self.vel
        dy = self.touch_dir['dy'] * self.vel
        if dx == 0 and dy == 0:
            return

        r = self.celda * 0.38   # radio hitbox jugador
        # Mover X
        nx = self.px + dx
        ny = self.py
        if not self._colisiona(nx, ny, r):
            self.px = nx
        # Mover Y
        nx = self.px
        ny = self.py + dy
        if not self._colisiona(nx, ny, r):
            self.py = ny

    def _colisiona(self, cx, cy, r):
        for (rx, ry, rw, rh) in self.pared_rects:
            # AABB vs círculo
            near_x = max(rx, min(cx, rx + rw))
            near_y = max(ry, min(cy, ry + rh))
            dist2  = (cx - near_x) ** 2 + (cy - near_y) ** 2
            if dist2 < r * r:
                return True
        return False

    def _check_powerups(self, ahora):
        # Expirar powerup activo
        if self.powerup_activo and ahora >= self.powerup_fin:
            if self.powerup_activo == "velocidad":
                self.vel = self.vel_base
            elif self.powerup_activo == "vision":
                self.vision_activa = False
            self.powerup_activo = None

        # Recoger
        r = self.celda * 0.38
        for pu in self.powerups:
            if not pu['activo']:
                continue
            dx = self.px - pu['cx']
            dy = self.py - pu['cy']
            if dx*dx + dy*dy < (r * 2) ** 2:
                pu['activo'] = False
                tipo = pu['tipo']
                dur  = self.POWERUP_TIPOS[tipo]['duracion']
                self.powerup_activo = tipo
                self.powerup_fin    = ahora + dur
                if tipo == "velocidad":
                    self.vel = self.vel_base + dp(4)
                elif tipo == "vision":
                    self.vision_activa = True

    def _check_meta(self):
        # Meta = esquina inferior derecha en coords pantalla
        fin_x = self.ax + (self.cols - 1) * self.celda + self.celda * 0.5
        fin_y = self.ay + self.celda * 0.5   # fila 0 Kivy = abajo del laberinto
        dx = self.px - fin_x
        dy = self.py - fin_y
        if dx*dx + dy*dy < (self.celda * 0.5) ** 2:
            self.ganado       = True
            self.tiempo_ganado = int(Clock.get_time() - self.tiempo_inicio)

    # -------- Dibujo --------
    def _dibujar(self):
        self.canvas.clear()
        sw, sh = Window.width, Window.height
        idx = (self.nivel - 1) % len(self.COLORES_FONDO)

        with self.canvas:
            # Fondo
            Color(*self.COLORES_FONDO[idx])
            Rectangle(pos=(0, 0), size=(sw, sh))

            # Zona botones fondo
            Color(0.08, 0.08, 0.12, 0.7)
            Rectangle(pos=(0, 0), size=(sw, self.maze_h - self.ah - dp(8) + sh * DPAD_AREA))

            # Paredes
            Color(*self.COLORES_PARED[idx])
            for (rx, ry, rw, rh) in self.pared_rects:
                Rectangle(pos=(rx, ry), size=(rw, rh))

            # Inicio (verde)
            Color(0.20, 0.78, 0.20, 1)
            ix = self.ax + GROSOR
            iy = self.ay + (self.filas - 1) * self.celda + GROSOR
            Rectangle(pos=(ix, iy), size=(self.celda - GROSOR*2, self.celda - GROSOR*2))

            # Meta (rojo) — fila filas-1 en lógica = Y más baja en Kivy
            Color(0.78, 0.20, 0.20, 1)
            fx = self.ax + (self.cols - 1) * self.celda + GROSOR
            fy = self.ay + GROSOR
            Rectangle(pos=(fx, fy), size=(self.celda - GROSOR*2, self.celda - GROSOR*2))

            # Power-ups
            for pu in self.powerups:
                if not pu['activo']:
                    continue
                cfg = self.POWERUP_TIPOS[pu['tipo']]
                Color(*cfg['color'])
                r = self.celda * 0.35
                Ellipse(pos=(pu['cx'] - r, pu['cy'] - r), size=(r*2, r*2))

            # Jugador
            Color(0.20, 0.51, 0.86, 1)
            pr = self.celda * 0.36
            Ellipse(pos=(self.px - pr, self.py - pr), size=(pr*2, pr*2))
            # Ojo
            Color(1, 1, 1, 1)
            er = max(dp(3), pr * 0.28)
            ox = pr * 0.35 * self.touch_dir['dx']
            oy = pr * 0.35 * self.touch_dir['dy']
            Ellipse(pos=(self.px + ox - er, self.py + oy - er), size=(er*2, er*2))
            Color(0, 0, 0, 1)
            pr2 = max(dp(1), er * 0.5)
            Ellipse(pos=(self.px + ox - pr2, self.py + oy - pr2), size=(pr2*2, pr2*2))

        # Niebla de guerra
        if not self.vision_activa:
            self._dibujar_niebla(sw, sh)

        # D-pad
        self._dibujar_dpad()

        # HUD
        self._dibujar_hud(sw, sh)

        # Pantalla de victoria
        if self.ganado:
            self._dibujar_victoria(sw, sh)

    def _dibujar_niebla(self, sw, sh):
        """Niebla: rectángulo negro con hueco circular alrededor del jugador."""
        with self.canvas:
            # Capas de niebla decrecientes
            radio = self.celda * 2.5
            pasos = 12
            for i in range(pasos, 0, -1):
                r = radio * i / pasos
                alpha = 0.82 * (1 - i / pasos)
                Color(0, 0, 0, alpha)
                # Dibujamos un círculo sólido — el último (más grande) cubre todo
                Ellipse(pos=(self.px - r, self.py - r), size=(r*2, r*2))

            # Rectángulos que cubren los 4 lados fuera del radio
            Color(0, 0, 0, 0.82)
            Rectangle(pos=(0, self.py + radio), size=(sw, sh))
            Rectangle(pos=(0, 0), size=(sw, max(0, self.py - radio)))
            Rectangle(pos=(0, self.py - radio), size=(max(0, self.px - radio), radio*2))
            Rectangle(pos=(self.px + radio, self.py - radio), size=(sw, radio*2))

    def _dibujar_dpad(self):
        with self.canvas:
            for nombre, (cx, cy, radio) in self.dpad_btns.items():
                activo = nombre in self.dpad_activos
                if activo:
                    Color(0.35, 0.35, 0.55, 0.9)
                else:
                    Color(0.24, 0.24, 0.35, 0.65)
                Ellipse(pos=(cx - radio, cy - radio), size=(radio*2, radio*2))
                Color(0.78, 0.78, 0.87, 0.9)
                Line(circle=(cx, cy, radio), width=dp(2))

    def _dibujar_hud(self, sw, sh):
        # HUD con Labels → los añadimos como widgets temporales
        # Más eficiente: usar canvas + instrucciones de texto no es nativo en Kivy puro,
        # así que usamos la label superpuesta en el widget padre (ver LaberintoApp)
        pass   # El HUD se maneja en LaberintoApp._actualizar_hud

    def _dibujar_victoria(self, sw, sh):
        with self.canvas:
            Color(0, 0, 0, 0.78)
            Rectangle(pos=(0, 0), size=(sw, sh))

    # -------- Touch input --------
    def on_touch_down(self, touch):
        px, py = touch.x, touch.y
        for nombre, (cx, cy, radio) in self.dpad_btns.items():
            if (px - cx)**2 + (py - cy)**2 <= radio**2:
                self.dpad_activos.add(nombre)
                self.dpad_touches[touch.uid] = nombre
                self._actualizar_dir()
                return True

        # Toque fuera del D-pad en victoria → siguiente nivel
        if self.ganado:
            self._siguiente_nivel()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        nombre = self.dpad_touches.pop(touch.uid, None)
        if nombre:
            self.dpad_activos.discard(nombre)
            self._actualizar_dir()
            return True
        return super().on_touch_up(touch)

    def _actualizar_dir(self):
        dx, dy = 0, 0
        for nombre in self.dpad_activos:
            if nombre == 'DER': dx =  1
            elif nombre == 'IZQ': dx = -1
            elif nombre == 'ARR': dy =  1
            elif nombre == 'ABJ': dy = -1
        self.touch_dir['dx'] = dx
        self.touch_dir['dy'] = dy

    # -------- Teclado PC --------
    def _on_key_down(self, window, key, *args):
        KEYS = {273: 'ARR', 274: 'ABJ', 275: 'DER', 276: 'IZQ',
                119: 'ARR', 115: 'ABJ', 100: 'DER', 97: 'IZQ'}
        if key == 27:   # ESC
            App.get_running_app().stop()
        if key in KEYS:
            nombre = KEYS[key]
            self.dpad_activos.add(nombre)
            self._actualizar_dir()

    def _on_key_up(self, window, key, *args):
        KEYS = {273: 'ARR', 274: 'ABJ', 275: 'DER', 276: 'IZQ',
                119: 'ARR', 115: 'ABJ', 100: 'DER', 97: 'IZQ'}
        if key in KEYS:
            self.dpad_activos.discard(KEYS[key])
            self._actualizar_dir()

    def _siguiente_nivel(self):
        self.nivel += 1
        self._nuevo_nivel_interno()


# ==================== APP ====================
class LaberintoApp(App):
    def build(self):
        self.title = "Laberinto"
        root = FloatLayout()

        self.juego = LaberintoWidget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        root.add_widget(self.juego)

        # HUD labels
        fs = dp(14)
        self.lbl_nivel = Label(
            text="Nivel: 1", font_size=fs, color=(0.1, 0.1, 0.1, 1),
            size_hint=(None, None), size=(dp(120), dp(28)),
            pos_hint={'x': 0.02, 'top': 1}
        )
        self.lbl_tiempo = Label(
            text="Tiempo: 0s", font_size=fs, color=(0.1, 0.1, 0.1, 1),
            size_hint=(None, None), size=(dp(140), dp(28)),
            pos_hint={'x': 0.02, 'top': 0.96}
        )
        self.lbl_powerup = Label(
            text="", font_size=fs, color=(1, 0.78, 0, 1),
            size_hint=(None, None), size=(dp(200), dp(28)),
            pos_hint={'right': 0.98, 'top': 1}
        )
        self.lbl_victoria = Label(
            text="", font_size=dp(32), bold=True, color=(0.31, 0.86, 0.31, 1),
            halign='center', size_hint=(1, None), height=dp(50),
            pos_hint={'x': 0, 'center_y': 0.6}
        )
        self.lbl_sub = Label(
            text="", font_size=dp(16), color=(0.9, 0.9, 0.9, 1),
            halign='center', size_hint=(1, None), height=dp(36),
            pos_hint={'x': 0, 'center_y': 0.48}
        )

        for w in [self.lbl_nivel, self.lbl_tiempo, self.lbl_powerup,
                  self.lbl_victoria, self.lbl_sub]:
            root.add_widget(w)

        # Ícono D-pad labels (flechas sobre botones)
        self._dpad_labels = {}
        for nombre, icono in [('ARR','▲'),('ABJ','▼'),('IZQ','◄'),('DER','►')]:
            lbl = Label(text=icono, font_size=dp(20), color=(1,1,1,0.9),
                        size_hint=(None,None), size=(dp(40),dp(40)))
            root.add_widget(lbl)
            self._dpad_labels[nombre] = lbl

        Window.bind(on_key_down=self.juego._on_key_down,
                    on_key_up=self.juego._on_key_up)

        Clock.schedule_interval(self._actualizar_hud, 1.0 / 30)
        return root

    def _actualizar_hud(self, dt):
        j = self.juego
        if not j.paredes:
            return

        ahora   = Clock.get_time()
        tiempo  = int(ahora - j.tiempo_inicio) if not j.ganado else j.tiempo_ganado

        self.lbl_nivel.text  = f"Nivel: {j.nivel}"
        self.lbl_tiempo.text = f"Tiempo: {tiempo}s"

        if j.powerup_activo:
            restante = max(0, int(j.powerup_fin - ahora))
            cfg      = j.POWERUP_TIPOS[j.powerup_activo]
            self.lbl_powerup.color = cfg['color']
            self.lbl_powerup.text  = f"[{j.powerup_activo.upper()}] {restante}s"
        else:
            self.lbl_powerup.text = ""

        if j.ganado:
            self.lbl_victoria.text = "¡GANASTE!"
            self.lbl_sub.text      = f"Tiempo: {j.tiempo_ganado}s  –  Toca para continuar"
        else:
            self.lbl_victoria.text = ""
            self.lbl_sub.text      = ""

        # Posicionar iconos del D-pad
        for nombre, lbl in self._dpad_labels.items():
            if nombre in j.dpad_btns:
                cx, cy, radio = j.dpad_btns[nombre]
                lbl.center = (cx, cy)
                lbl.opacity = 1
            else:
                lbl.opacity = 0


if __name__ == "__main__":
    LaberintoApp().run()
