from common import *

def obtener_nombre_completo_en_dominio(usuario, dominio):
    try:
        dc = win32net.NetGetDCName(None, dominio)
        info = win32net.NetUserGetInfo(dc, usuario, 2)
        return info.get('full_name')
    except pywintypes.error as e:
        print(f"[Dominio] NetUserGetInfo({dominio}\\{usuario}) falló: {e}")
        return None

def obtener_nombre_completo_usuario():
    usuario = win32api.GetUserName()
    dominio = win32api.GetDomainName()
    nombre_completo = None

    try:
        info_local = win32net.NetUserGetInfo(None, usuario, 2)
        nombre_completo = info_local.get('full_name')
    except pywintypes.error:
        pass

    if not nombre_completo:
        nombre_completo = obtener_nombre_completo_en_dominio(usuario, dominio)

    if not nombre_completo:
        try:
            import wmi
            c = wmi.WMI()
            for u in c.Win32_UserAccount(Name=usuario, Domain=dominio):
                if u.FullName:
                    nombre_completo = u.FullName
                    break
        except Exception:
            pass

    return usuario, nombre_completo or "(Sin nombre completo)"



