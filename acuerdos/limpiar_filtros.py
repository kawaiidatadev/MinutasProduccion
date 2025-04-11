from common import *
from acuerdos.carga_acuerdos import load_acuerdos
def clear_filters(id_filter, text_filter, resp_filter, date_from, date_to, status_filter, acuerdos_tree, db_path):
    """Limpia todos los filtros"""
    id_filter.delete(0, "end")
    text_filter.delete(0, "end")
    resp_filter.delete(0, "end")
    date_from.delete(0, "end")
    date_to.delete(0, "end")
    status_filter.set("Todos")
    load_acuerdos(acuerdos_tree, db_path, id_filter, text_filter, resp_filter, date_from, date_to, status_filter)

