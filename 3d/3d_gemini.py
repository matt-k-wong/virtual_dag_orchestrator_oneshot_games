# game.py
import pygame
import sys
import random
import math
import subprocess

# --- Auto-Install Bootstrap ---
def install_requirements():
    try:
        import pygame
    except ImportError:
        print("Pygame not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
        import pygame

install_requirements()

# --- Configuration & Constants ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
FOV = 400
WHITE = (255, 255, 255)
BLACK = (10, 10, 20)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)

# --- 3D Projection Engine ---
def project(x, y, z, roll=0):
    """Projects 3D coordinates to 2D screen coordinates with roll rotation."""
    if z <= 0:
        return None
    
    # Standard perspective projection
    f = FOV / z
    px = x * f
    py = y * f
    
    # Apply camera roll (2D rotation around screen center)
    if roll != 0:
        s = math.sin(roll)
        c = math.cos(roll)
        nx = px * c - py * s
        ny = px * s + py * c
        px, py = nx, ny
        
    return (int(px + WIDTH // 2), int(py + HEIGHT // 2))

# --- Game Entities ---
class Particle:
    def __init__(self, z_start=2000):
        self.reset(z_start)

    def reset(self, z_start):
        self.x = random.randint(-1000, 1000)
        self.y = random.randint(-600, 600)
        self.z = z_start
        self.speed = random.randint(10, 20)

    def update(self, speed_multiplier):
        self.z -= 15 * speed_multiplier
        if self.z < 1:
            self.reset(2000)

    def draw(self, surface, roll):
        p = project(self.x, self.y, self.z, roll)
        if p:
            size = max(1, int(50 / (self.z * 0.05 + 1)))
            pygame.draw.circle(surface, WHITE, p, size)

class Gate:
    def __init__(self, z):
        self.z = z
        self.x = random.randint(-200, 200)
        self.y = random.randint(-150, 150)
        self.width = 300
        self.height = 200
        self.passed = False
        self.color = MAGENTA

    def update(self, speed):
        self.z -= speed

    def is_off_screen(self):
        return self.z < -50

    def draw(self, surface, roll):
        # 3D vertices for a rectangular gate
        hw, hh = self.width / 2, self.height / 2
        points = [
            (self.x - hw, self.y - hh, self.z),
            (self.x + hw, self.y - hh, self.z),
            (self.x + hw, self.y + hh, self.z),
            (self.x - hw, self.y + hh, self.z)
        ]
        
        proj_points = []
        for pt in points:
            p = project(pt[0], pt[1], pt[2], roll)
            if p: proj_points.append(p)
            
        if len(proj_points) == 4:
            pygame.draw.lines(surface, self.color, True, proj_points, 3)
            # Add a slight "glow"
            pygame.draw.lines(surface, self.color, True, proj_points, 1)

class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 0
        self.y = 0
        self.z = 0
        self.roll = 0
        self.pitch = 0
        self.target_roll = 0
        self.score = 0
        self.alive = True
        self.speed = 15

    def update(self, keys):
        if not self.alive: return

        # Handling Input
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.target_roll = 0.4
            self.x -= 8
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.target_roll = -0.4
            self.x += 8
        else:
            self.target_roll = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= 8
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += 8

        # Smooth banking
        self.roll += (self.target_roll - self.roll) * 0.1
        
        # Boundaries
        self.x = max(-500, min(500, self.x))
        self.y = max(-400, min(300, self.y))

    def draw_hud(self, surface):
        font = pygame.font.SysFont("monospace", 30, bold=True)
        score_txt = font.render(f"DISTANCE: {int(self.score)}m", True, CYAN)
        surface.blit(score_txt, (20, 20))
        
        # Artificial Horizon
        center = (WIDTH // 2, HEIGHT - 100)
        pygame.draw.circle(surface, WHITE, center, 40, 2)
        h_line_y = center[1] + math.sin(self.roll) * 30
        pygame.draw.line(surface, CYAN, (center[0]-30, h_line_y), (center[0]+30, h_line_y), 2)

# --- Main Game Engine ---
class VectorReach:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("VECTOR-REACH 3D")
        self.clock = pygame.time.Clock()
        self.player = Player()
        self.particles = [Particle(random.randint(100, 2000)) for _ in range(100)]
        self.gates = []
        self.spawn_timer = 0
        self.shake = 0

    def reset(self):
        self.player.reset()
        self.gates = []
        self.spawn_timer = 0
        self.shake = 0

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            keys = pygame.key.get_pressed()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and not self.player.alive:
                        self.reset()

            self.update(keys)
            self.draw()

        pygame.quit()

    def update(self, keys):
        if self.player.alive:
            self.player.update(keys)
            self.player.score += 0.5
            
            # Spawn Gates
            self.spawn_timer += 1
            if self.spawn_timer > 60:
                self.gates.append(Gate(2500))
                self.spawn_timer = 0

            # Update Gates
            for gate in self.gates[:]:
                gate.update(self.player.speed)
                
                # Collision Check
                if 0 < gate.z < 50 and not gate.passed:
                    dist_x = abs((gate.x - self.player.x))
                    dist_y = abs((gate.y - self.player.y))
                    if dist_x < gate.width/2 and dist_y < gate.height/2:
                        # Passed successfully
                        gate.passed = True
                        gate.color = YELLOW
                        self.player.score += 100
                    else:
                        # Crash
                        self.player.alive = False
                        self.shake = 20

                if gate.is_off_screen():
                    self.gates.remove(gate)

            # Update Particles
            for p in self.particles:
                p.update(self.player.speed / 10)
        
        if self.shake > 0:
            self.shake -= 1

    def draw_grid(self):
        # Draw a moving 3D ground grid
        grid_color = (40, 40, 80)
        spacing = 200
        z_offset = -(self.player.score * 20) % spacing
        
        for gz in range(2500, 0, -spacing):
            z_pos = gz - z_offset
            points = []
            for gx in range(-2000, 2001, 500):
                p = project(gx - self.player.x, 400 - self.player.y, z_pos, self.player.roll)
                if p: points.append(p)
            if len(points) > 1:
                pygame.draw.lines(self.screen, grid_color, False, points, 1)

    def draw(self):
        # Screen Shake
        offset_x = random.randint(-self.shake, self.shake) if self.shake else 0
        offset_y = random.randint(-self.shake, self.shake) if self.shake else 0
        
        self.screen.fill(BLACK)
        
        # Draw everything in Z-order (simplified: grid -> particles -> gates)
        self.draw_grid()
        
        for p in self.particles:
            p.draw(self.screen, self.player.roll)
            
        for gate in sorted(self.gates, key=lambda g: g.z, reverse=True):
            # Translate world coords to camera-relative coords
            rel_x = gate.x - self.player.x
            rel_y = gate.y - self.player.y
            
            # Temporary object for relative projection
            temp_gate = Gate(gate.z)
            temp_gate.x, temp_gate.y = rel_x, rel_y
            temp_gate.color = gate.color
            temp_gate.draw(self.screen, self.player.roll)

        # Draw Player "Cockpit" or Ship (Simple triangle)
        if self.player.alive:
            ship_pts = [
                (0, 20), (-30, 40), (0, -20), (30, 40)
            ]
            # Ship stays centered visually but tilts
            rotated_ship = []
            for sx, sy in ship_pts:
                s = math.sin(self.player.roll * 0.5)
                c = math.cos(self.player.roll * 0.5)
                nx = sx * c - sy * s
                ny = sx * s + sy * c
                rotated_ship.append((WIDTH//2 + nx, HEIGHT//2 + 150 + ny))
            pygame.draw.polygon(self.screen, CYAN, rotated_ship, 2)
        else:
            font = pygame.font.SysFont("monospace", 70, bold=True)
            msg = font.render("CRITICAL FAILURE", True, MAGENTA)
            self.screen.blit(msg, (WIDTH//2 - 300, HEIGHT//2 - 50))
            retry = pygame.font.SysFont("monospace", 30)
            msg2 = retry.render("PRESS 'R' TO REBOOT SYSTEM", True, WHITE)
            self.screen.blit(msg2, (WIDTH//2 - 220, HEIGHT//2 + 50))

        self.player.draw_hud(self.screen)
        
        # Apply shake by blitting surface with offset if needed
        if self.shake:
            temp_surface = self.screen.copy()
            self.screen.fill(BLACK)
            self.screen.blit(temp_surface, (offset_x, offset_y))

        pygame.display.flip()

if __name__ == "__main__":
    game = VectorReach()
    game.run()
