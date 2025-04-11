import pygame
import tempfile
import pyttsx3
import os


def texto_a_voz(texto, velocidad=120, tono=50, volumen=0.8):
    # Generar audio temporal con pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', velocidad)
    engine.setProperty('pitch', tono)
    engine.setProperty('volume', volumen)

    # Crear archivo temporal
    temp_file = tempfile.mktemp(suffix='.wav')
    engine.save_to_file(texto, temp_file)
    engine.runAndWait()

    # Reproducir con pygame
    pygame.mixer.init()
    pygame.mixer.music.load(temp_file)
    pygame.mixer.music.play()

    # Esperar a que termine la reproducción
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    # Eliminar archivo temporal
    os.remove(temp_file)