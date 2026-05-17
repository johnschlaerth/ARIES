"""Pygame input handling for the ARIES demo."""

from __future__ import annotations


class GuiControls:
    def __init__(self) -> None:
        self.show_vectors = True
        self.show_paths = True
        self.fast_mode = False
        self.single_step = False
        self.save_screenshot = False
        self.quit_requested = False

    def handle_event(self, event, sim) -> None:
        import pygame

        if event.type == pygame.QUIT:
            self.quit_requested = True
        elif event.type == pygame.KEYDOWN:
            if event.key in {pygame.K_q, pygame.K_ESCAPE}:
                self.quit_requested = True
            elif event.key == pygame.K_SPACE:
                sim.state.paused = not sim.state.paused
            elif event.key == pygame.K_n:
                self.single_step = True
            elif event.key == pygame.K_r:
                sim.reset()
            elif event.key == pygame.K_f:
                self.fast_mode = not self.fast_mode
            elif event.key == pygame.K_v:
                self.show_vectors = not self.show_vectors
            elif event.key == pygame.K_p:
                self.show_paths = not self.show_paths
            elif event.key == pygame.K_s:
                self.save_screenshot = True
