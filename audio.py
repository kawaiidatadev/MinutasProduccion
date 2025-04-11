import pygame
import tempfile
import pyttsx3
import os
import time


def texto_a_voz(texto, velocidad=120, tono=50, volumen=0.8):
    try:
        # Inicializar pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', velocidad)

        try:
            engine.setProperty('pitch', tono)  # Puede fallar en SAPI5
        except:
            print("Ajuste de tono no soportado en este motor de voz.")

        engine.setProperty('volume', volumen)

        # Crear archivo temporal
        temp_file = tempfile.mktemp(suffix='.wav')
        engine.save_to_file(texto, temp_file)
        engine.runAndWait()  # Espera a que se guarde el archivo

        # Reproducir con pygame
        pygame.mixer.init()
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()

        # Esperar a que termine la reproducción
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Cerrar el mixer para liberar el archivo
        pygame.mixer.music.stop()
        pygame.mixer.quit()

        # Pequeña pausa para asegurar que el sistema operativo libere el archivo
        time.sleep(0.1)

        # Eliminar archivo temporal
        if os.path.exists(temp_file):
            os.remove(temp_file)

    except Exception as e:
        print(f"Error en texto_a_voz: {e}")