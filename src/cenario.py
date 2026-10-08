"""
cenario.py - O labirinto na tela.

A classe Cenario recebe uma "grade" (lista de listas com 1 = parede e
0 = chao) gerada em jogo.py e cuida de:
  * desenhar o labirinto (so os tiles visiveis na camera);
  * responder colisoes (o jogador usa `colide(rect)`);
  * desenhar o portal de saida e o ponto de entrada.

O visual vem de um TEMA (veja TEMAS abaixo). O jogo sorteia um tema a
cada fase: "masmorra" (o labirinto classico) ou "gelo" (nevasca).
"""
import math
import random

import pygame

TILE = 56  # tamanho de cada quadrado do labirinto, em pixels

# ----------------------------------------------------------------------
# Temas visuais. Para criar outro mapa, basta adicionar uma entrada aqui.
# ----------------------------------------------------------------------
TEMAS = {
    "masmorra": {
        "estilo": "tijolos",
        "fundo": (18, 16, 28),
        "pisos": ((46, 42, 64), (50, 46, 70), (44, 40, 60), (48, 44, 66)),
        "rachaduras": None,
        "parede": (96, 88, 134),
        "junta": (70, 63, 102),
        "face": (56, 50, 84),
        "face_linha": (130, 122, 168),
        "face_junta": (40, 35, 64),
        "entrada": (60, 140, 90),
        "portal": ((255, 214, 90), (255, 240, 170)),  # aro, miolo
        "brilho": (255, 200, 70),
        "neve": 0,  # quantidade de flocos caindo na tela
    },
    "gelo": {
        "estilo": "gelo",
        "fundo": (12, 20, 32),
        "pisos": ((34, 56, 82), (38, 61, 88), (32, 52, 77), (36, 58, 85)),
        "rachaduras": (78, 114, 152),  # trincas no chao congelado
        "parede": (188, 216, 240),
        "junta": (126, 166, 206),
        "reflexo": (242, 250, 255),
        "face": (70, 118, 168),
        "face_linha": (228, 244, 255),
        "pingentes": (208, 234, 252),
        "entrada": (110, 200, 235),
        "portal": ((120, 225, 255), (205, 245, 255)),
        "brilho": (110, 200, 255),
        "neve": 180,
    },
}


class Cenario:
    def __init__(self, grade, entrada, saida, tile=TILE, tema="masmorra"):
        self.grade = grade
        self.linhas = len(grade)
        self.colunas = len(grade[0])
        self.entrada = entrada  # (coluna, linha) em tiles
        self.saida = saida      # (coluna, linha) em tiles
        self.tile = tile
        self.largura = self.colunas * tile
        self.altura = self.linhas * tile
        self.nome_tema = tema
        self.tema = TEMAS[tema]
        self.tempo = 0.0
        self.flocos = []   # criados no primeiro desenho (precisa do tamanho da tela)
        self.vento = 0.0
        self._criar_superficies()

    # ------------------------------------------------------------------
    # Construcao das imagens (feitas por codigo, nao precisa de assets)
    # ------------------------------------------------------------------
    def _criar_superficies(self):
        t = self.tile
        tema = self.tema
        rng = random.Random(7)

        # Pisos: 4 variacoes com "pontinhos" para nao ficar monotono
        self.pisos = []
        for i, base in enumerate(tema["pisos"]):
            s = pygame.Surface((t, t))
            s.fill(base)
            for _ in range(10):
                x, y = rng.randrange(t), rng.randrange(t)
                c = tuple(max(0, v - 10) for v in base)
                s.set_at((x, y), c)
                s.set_at((min(t - 1, x + 1), y), c)
            if tema["rachaduras"] and i % 2 == 0:
                self._rachadura(s, tema["rachaduras"], rng)
            pygame.draw.rect(s, tuple(max(0, v - 8) for v in base), (0, 0, t, t), 1)
            self.pisos.append(s)

        # Parede (vista de cima) e parede com "face" (quando ha chao abaixo)
        self.parede = self._parede_base()
        self.parede_face = self._parede_base()
        face = pygame.Rect(0, t - 18, t, 18)
        pygame.draw.rect(self.parede_face, tema["face"], face)
        pygame.draw.line(self.parede_face, tema["face_linha"], (0, t - 18), (t, t - 18), 2)
        if tema["estilo"] == "gelo":
            self._pingentes(self.parede_face, tema["pingentes"], rng)
        else:
            for x in range(0, t, 14):
                pygame.draw.line(self.parede_face, tema["face_junta"], (x, t - 18), (x, t), 1)

        # Brilho do portal de saida (gradiente radial)
        raio = int(t * 2.2)
        br, bg, bb = tema["brilho"]
        self.brilho = pygame.Surface((raio * 2, raio * 2))
        for r in range(raio, 0, -2):
            k = (1 - r / raio) ** 2
            cor = (int(br * k), int(bg * k), int(bb * k))
            pygame.draw.circle(self.brilho, cor, (raio, raio), r)

    def _parede_base(self):
        tema = self.tema
        if tema["estilo"] == "gelo":
            return self._blocos_gelo(tema["parede"], tema["junta"], tema["reflexo"])
        return self._tijolos(tema["parede"], tema["junta"])

    def _tijolos(self, cor, junta):
        t = self.tile
        s = pygame.Surface((t, t))
        s.fill(cor)
        for i, y in enumerate(range(0, t, 14)):
            pygame.draw.line(s, junta, (0, y), (t, y), 2)
            for x in range((i % 2) * 14, t, 28):
                pygame.draw.line(s, junta, (x, y), (x, y + 14), 2)
        return s

    def _blocos_gelo(self, cor, junta, reflexo):
        """Blocos de gelo grandes (como um iglu), cada um com um reflexo."""
        t = self.tile
        s = pygame.Surface((t, t))
        s.fill(cor)
        lado = 28
        for i, y in enumerate(range(0, t, lado)):
            for x in range((i % 2) * lado // 2 - lado, t, lado):
                pygame.draw.line(s, reflexo, (x + 5, y + 12), (x + 12, y + 5), 2)
                pygame.draw.line(s, reflexo, (x + 6, y + 19), (x + 19, y + 6), 1)
                pygame.draw.line(s, junta, (x, y), (x, y + lado), 2)
            pygame.draw.line(s, junta, (0, y), (t, y), 2)
        return s

    def _pingentes(self, s, cor, rng):
        """Pingentes de gelo pendurados na borda de cima da face da parede."""
        t = self.tile
        topo = t - 17
        x = rng.randint(1, 4)
        while x < t - 6:
            larg = rng.randint(4, 7)
            comp = rng.randint(6, 15)
            pygame.draw.polygon(s, cor, [(x, topo), (x + larg, topo), (x + larg // 2, topo + comp)])
            x += larg + rng.randint(2, 6)

    def _rachadura(self, s, cor, rng):
        """Trinca fina e quebrada no chao congelado, com alguns brilhos."""
        t = self.tile
        x, y = rng.randrange(10, t - 10), rng.randrange(10, t - 10)
        for _ in range(rng.randint(2, 4)):
            nx = min(t - 4, max(3, x + rng.randint(-14, 14)))
            ny = min(t - 4, max(3, y + rng.randint(-14, 14)))
            pygame.draw.line(s, cor, (x, y), (nx, ny), 1)
            x, y = nx, ny
        claro = tuple(min(255, v + 90) for v in cor)
        for _ in range(3):
            s.set_at((rng.randrange(2, t - 2), rng.randrange(2, t - 2)), claro)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def eh_parede(self, col, lin):
        if col < 0 or lin < 0 or col >= self.colunas or lin >= self.linhas:
            return True
        return self.grade[lin][col] == 1

    def colide(self, rect):
        """True se o retangulo (em pixels do mapa) encosta em alguma parede."""
        t = self.tile
        for lin in range(rect.top // t, (rect.bottom - 1) // t + 1):
            for col in range(rect.left // t, (rect.right - 1) // t + 1):
                if self.eh_parede(col, lin):
                    return True
        return False

    def centro_tile(self, tile):
        col, lin = tile
        return col * self.tile + self.tile // 2, lin * self.tile + self.tile // 2

    def rect_saida(self):
        """Area do portal (um pouco menor que o tile, para nao ser 'injusto')."""
        cx, cy = self.centro_tile(self.saida)
        r = pygame.Rect(0, 0, self.tile - 16, self.tile - 16)
        r.center = (cx, cy)
        return r

    # ------------------------------------------------------------------
    # Checagem de saída (adicionado para compatibilidade com o jogo.py)
    # ------------------------------------------------------------------
    def checar_saida(self, x, y):
        """Retorna True se a posição (x, y) colidir com o retângulo de saída."""
        r_saida = self.rect_saida()
        return r_saida.collidepoint(x, y)

    # ------------------------------------------------------------------
    # Atualizacao / desenho
    # ------------------------------------------------------------------
    def atualizar(self, dt):
        self.tempo += dt
        if self.flocos:
            self._atualizar_neve(dt)

    def _atualizar_neve(self, dt):
        # rajadas: o vento da nevasca aumenta e diminui sem parar
        rajada = 0.5 + 0.5 * math.sin(self.tempo * 0.9) * math.sin(self.tempo * 0.31 + 1.0)
        self.vento = 40 + 260 * rajada
        for f in self.flocos:
            x, y, prof, fase = f
            f[0] = x + (self.vento + 30 * math.sin(self.tempo * 2 + fase)) * prof * dt
            f[1] = y + (40 + 110 * prof) * dt

    def desenhar(self, tela, cam_x, cam_y):
        t = self.tile
        c0 = max(0, cam_x // t)
        c1 = min(self.colunas, (cam_x + tela.get_width()) // t + 2)
        l0 = max(0, cam_y // t)
        l1 = min(self.linhas, (cam_y + tela.get_height()) // t + 2)

        for lin in range(l0, l1):
            for col in range(c0, c1):
                x, y = col * t - cam_x, lin * t - cam_y
                if self.grade[lin][col] == 1:
                    abaixo_livre = not self.eh_parede(col, lin + 1)
                    tela.blit(self.parede_face if abaixo_livre else self.parede, (x, y))
                else:
                    tela.blit(self.pisos[(col * 7 + lin * 13) % 4], (x, y))

        self._desenhar_entrada(tela, cam_x, cam_y)
        self._desenhar_portal(tela, cam_x, cam_y)

    def _desenhar_entrada(self, tela, cam_x, cam_y):
        cx, cy = self.centro_tile(self.entrada)
        pygame.draw.circle(tela, self.tema["entrada"], (cx - cam_x, cy - cam_y), self.tile // 2 - 8, 2)

    def _desenhar_portal(self, tela, cam_x, cam_y):
        cx, cy = self.centro_tile(self.saida)
        cx, cy = cx - cam_x, cy - cam_y
        aro, miolo = self.tema["portal"]
        pulso = 0.5 + 0.5 * math.sin(self.tempo * 4)
        r = int(self.tile * (0.30 + 0.06 * pulso))
        pygame.draw.circle(tela, aro, (cx, cy), r + 6, 3)
        pygame.draw.circle(tela, miolo, (cx, cy), r)
        pygame.draw.circle(tela, (255, 255, 255), (cx, cy), max(2, r // 2))

    def desenhar_brilho_saida(self, tela, cam_x, cam_y):
        """Halo do portal desenhado POR CIMA da escuridao: serve de farol."""
        cx, cy = self.centro_tile(self.saida)
        pulso = 0.75 + 0.25 * math.sin(self.tempo * 3)
        img = self.brilho
        if pulso < 0.99:
            img = self.brilho.copy()
            img.fill((int(255 * pulso),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        r = self.brilho.get_width() // 2
        tela.blit(img, (cx - cam_x - r, cy - cam_y - r), special_flags=pygame.BLEND_RGB_ADD)

    def desenhar_clima(self, tela, cam_x, cam_y):
        """Nevasca: flocos caindo por cima de tudo, inclusive da escuridao."""
        qtd = self.tema["neve"]
        if not qtd:
            return
        larg, alt = tela.get_size()
        if not self.flocos:
            rng = random.Random()
            # [x, y, profundidade (0.3 = longe, 1 = perto da tela), fase do balanco]
            self.flocos = [[rng.uniform(0, larg), rng.uniform(0, alt),
                            rng.uniform(0.3, 1.0), rng.uniform(0, math.tau)]
                           for _ in range(qtd)]
        for x, y, prof, _ in self.flocos:
            # flocos mais perto andam mais quando a camera mexe (profundidade)
            par = 1.0 + 0.6 * prof
            sx = int(x - cam_x * par) % larg
            sy = int(y - cam_y * par) % alt
            c = int(110 + 145 * prof)
            if prof > 0.8:  # rastro: os flocos mais proximos parecem mais rapidos
                rastro = self.vento * prof * 0.04
                pygame.draw.line(tela, (c // 2, c // 2, c // 2 + 25), (sx, sy), (sx - rastro, sy - 5), 2)
            pygame.draw.circle(tela, (c, c, min(255, c + 20)), (sx, sy), 1 if prof < 0.6 else 2)
