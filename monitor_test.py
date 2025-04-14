import sqlite3
import time
from datetime import datetime
import threading
import traceback
from plyer import notification
import platform
import os
import subprocess


class AcuerdoMonitor:
    def __init__(self, db_path, check_interval=3):
        self.db_path = db_path
        self.check_interval = check_interval
        self.running = False
        self.last_checked_id = self._get_last_agreement_id()

    def _get_last_agreement_id(self):
        """Obtiene el ID más reciente para comenzar el monitoreo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM historial_acuerdos")
            last_id = cursor.fetchone()[0] or 0
            conn.close()
            return last_id
        except:
            return 0

    def _show_notification(self, title, message, pdf_path=None):
        """Muestra notificación con capacidad para abrir PDF"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Monitor de Acuerdos",
                timeout=10,
                # Plyer no soporta acciones directas en notificaciones, usaremos un enfoque alternativo
            )

            # Guardamos el PDF para abrir si el usuario hace clic (solución alternativa)
            if pdf_path and os.path.exists(pdf_path):
                self.last_pdf_path = pdf_path
        except Exception as e:
            print(f"Error mostrando notificación: {e}")

    def _open_pdf(self, pdf_path):
        """Abre el PDF con el visor predeterminado"""
        try:
            if os.path.exists(pdf_path):
                os.startfile(pdf_path)
            else:
                print(f"El archivo PDF no existe: {pdf_path}")
        except Exception as e:
            print(f"Error abriendo PDF: {e}")

    def _check_closed_agreements(self):
        """Busca acuerdos recién cerrados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, acuerdo, usuario_modifico, ruta_pdf 
                FROM historial_acuerdos 
                WHERE id > ? AND estatus = 'Cerrado'
                ORDER BY id DESC
            """, (self.last_checked_id,))

            new_closed = cursor.fetchall()

            for agreement in new_closed:
                id_, acuerdo, usuario, ruta_pdf = agreement
                self.last_checked_id = max(self.last_checked_id, id_)

                # Mostrar notificación
                self._show_notification(
                    "Acuerdo Cerrado",
                    f"El usuario {usuario} ha cerrado el acuerdo {acuerdo}",
                    ruta_pdf
                )

                # Registrar en consola
                print(f"\n=== ACUERDO CERRADO DETECTADO ===")
                print(f"ID: {id_}")
                print(f"Acuerdo: {acuerdo}")
                print(f"Usuario: {usuario}")
                print(f"PDF: {ruta_pdf}\n")

            conn.close()
            return len(new_closed)

        except Exception as e:
            print(f"Error verificando acuerdos: {e}")
            return 0

    def _monitor_changes(self):
        """Monitorea cambios en la base de datos"""
        while self.running:
            try:
                num_closed = self._check_closed_agreements()
                if num_closed > 0:
                    print(f"Se detectaron {num_closed} acuerdos cerrados nuevos")
            except Exception as e:
                print(f"Error en monitor: {str(e)[:100]}...")

            time.sleep(self.check_interval)

    def start(self):
        """Inicia el monitor en segundo plano"""
        if not self.running:
            self.running = True
            monitor_thread = threading.Thread(
                target=self._monitor_changes,
                daemon=True
            )
            monitor_thread.start()
            print(f"Monitor iniciado. Observando acuerdos cerrados en: {self.db_path}")

    def stop(self):
        """Detiene el monitor"""
        self.running = False
        print("Monitor detenido")


if __name__ == "__main__":
    DB_PATH = r"\\mercury\Mtto_Prod\00_Departamento_Mantenimiento\Minutas\minutas.db"

    print(f"Sistema: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print("Monitor especializado para acuerdos cerrados")
    print("Presione Ctrl+C para detener\n")

    monitor = AcuerdoMonitor(DB_PATH)
    monitor.start()

    try:
        while True:
            # Esta solución alternativa verifica si el usuario quiere abrir el último PDF
            user_input = input("Presione 'a' para abrir el último PDF detectado o Enter para continuar...")
            if user_input.lower() == 'a' and hasattr(monitor, 'last_pdf_path'):
                monitor._open_pdf(monitor.last_pdf_path)
    except KeyboardInterrupt:
        monitor.stop()