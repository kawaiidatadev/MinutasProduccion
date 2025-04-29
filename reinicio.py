# reinicio.py
from common import *
from main import main as main_func


def reinicio_conexion():
    print("Reinciando el sistema…")

    if os.environ.get("YA_REINICIADO") == "1":
        print("Ejecución ya reiniciada una vez. Cancelando para evitar bucle.")
        return

    os.environ["YA_REINICIADO"] = "1"  # previene loops infinitos
    main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    os.execve(sys.executable, [sys.executable, main_path], os.environ)