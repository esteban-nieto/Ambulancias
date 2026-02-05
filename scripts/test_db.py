from db import init_db, crear_usuario, obtener_consecutivo, obtener_historias_por_estado, guardar_historia
init_db()
crear_usuario('test','pass')
print('consec:', obtener_consecutivo())
guardar_historia('HC-TEST-0001','test','Paciente X','45','Dolor','Probable','Tratamiento')
h = obtener_historias_por_estado('test','incompleta')
print('len h', len(h), 'row0', h[0])
