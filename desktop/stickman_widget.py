"""Animated stickman widget — port of the HTML canvas stickman."""
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath


class StickmanWidget(QWidget):
    """
    Idle: a stickman with a top hat and monocle that gently bobs.
    Loading: body segments morph into a spinning ring; head orbits around it.
    """

    SCALE   = 0.245
    OX, OY  = 38, 48
    RING_R  = 21

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(76, 88)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.is_loading  = False
        self.progress    = 0.0
        self.spin_angle  = 0.0
        self.orbit_angle = -math.pi / 2
        self.idle_bob    = 0.0

        # Pre-compute idle line endpoints and arc segments
        def p(x, y):
            return ((x - 110) * self.SCALE, (y - 175) * self.SCALE)

        self._idle_lines = [
            (p(110, 116), p(110, 175)),   # torso
            (p(110, 132), p( 78, 155)),   # left arm
            (p(110, 132), p(142, 155)),   # right arm
            (p(110, 175), p( 85, 215)),   # left leg
            (p(110, 175), p(135, 215)),   # right leg
        ]
        self._head_cy_idle = (95 - 175) * self.SCALE
        self._head_r       = 20 * self.SCALE

        n = len(self._idle_lines)
        gap     = 0.35
        arc_len = (2 * math.pi - n * gap) / n
        self._arc_segs = [
            (i * (arc_len + gap) - math.pi / 2,
             i * (arc_len + gap) - math.pi / 2 + arc_len)
            for i in range(n)
        ]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)   # ~60 fps

    # ── Public API ────────────────────────────────────────────────────────────
    def set_loading(self, loading: bool):
        self.is_loading = loading

    # ── Animation tick ────────────────────────────────────────────────────────
    def _tick(self):
        dt  = 0.016
        spd = 1 / 0.6
        if self.is_loading:
            self.progress = min(1.0, self.progress + dt * spd)
        else:
            self.progress = max(0.0, self.progress - dt * spd)

        t = self._ease(self.progress)
        self.spin_angle  += 2.5 * dt * t
        self.orbit_angle += 2.0 * dt * t
        self.idle_bob    += dt
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.OX, self.OY)

        t  = self._ease(self.progress)
        ti = 1 - t
        R  = self.RING_R
        HR = self._head_r

        dark   = QColor('#3a2e22')
        cream  = QColor('#f0ebe1')
        medium = QColor('#5c4733')

        # ── Body segments ────────────────────────────────────────────────────
        for ln, seg in zip(self._idle_lines, self._arc_segs):
            a1 = seg[0] + self.spin_angle
            a2 = seg[1] + self.spin_angle

            x1 = self._lerp(ln[0][0], R * math.cos(a1), t)
            y1 = self._lerp(ln[0][1], R * math.sin(a1), t)
            x2 = self._lerp(ln[1][0], R * math.cos(a2), t)
            y2 = self._lerp(ln[1][1], R * math.sin(a2), t)

            amid = (a1 + a2) / 2
            cpx  = self._lerp((ln[0][0]+ln[1][0])/2, R*math.cos(amid), t)
            cpy  = self._lerp((ln[0][1]+ln[1][1])/2, R*math.sin(amid), t)

            path = QPainterPath()
            path.moveTo(x1, y1)
            path.quadTo(cpx, cpy, x2, y2)
            pen = QPen(dark, 2.5, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        # ── Head position ─────────────────────────────────────────────────────
        orbit_r = (R + HR + 2) * t
        hx = self._lerp(0.0,              orbit_r * math.cos(self.orbit_angle), t)
        hy = self._lerp(self._head_cy_idle, orbit_r * math.sin(self.orbit_angle), t)
        bob = math.sin(self.idle_bob * 1.8) * 1.2 if ti > 0.97 else 0.0
        hy_b = hy + bob

        # Head circle
        painter.setPen(QPen(dark, 2.0))
        painter.setBrush(QBrush(cream))
        painter.drawEllipse(
            int(hx - HR), int(hy_b - HR),
            int(HR * 2),  int(HR * 2)
        )

        # Monocle
        m_ang = self.orbit_angle if t > 0.05 else 0.3
        mox = hx + math.cos(m_ang) * HR * 0.45
        moy = hy_b + math.sin(m_ang) * HR * 0.3
        mR  = HR * 0.38
        painter.setPen(QPen(dark, 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(mox - mR), int(moy - mR), int(mR * 2), int(mR * 2))
        cA = m_ang + math.pi * 0.4
        painter.drawLine(
            int(mox + math.cos(cA) * mR),  int(moy + math.sin(cA) * mR),
            int(mox + math.cos(cA) * mR*2), int(moy + math.sin(cA) * mR*2)
        )

        # Top hat
        hat_y = hy_b - HR
        bw, bh = HR * 2.5, HR * 0.32
        cw, ch = HR * 1.55, HR * 1.45

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dark))
        painter.drawRoundedRect(int(hx - bw/2), int(hat_y - bh), int(bw), int(bh), 1, 1)
        painter.drawRoundedRect(int(hx - cw/2), int(hat_y - bh - ch), int(cw), int(ch), 1, 1)
        painter.setBrush(QBrush(medium))
        painter.drawRoundedRect(
            int(hx - cw/2), int(hat_y - bh - ch * 0.3),
            int(cw), int(ch * 0.28), 1, 1
        )

        painter.end()

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _ease(t):
        if t < 0.5:
            return 4 * t * t * t
        return 1 - (-2 * t + 2) ** 3 / 2

    @staticmethod
    def _lerp(a, b, t):
        return a + (b - a) * t
