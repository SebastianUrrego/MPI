from mpi4py import MPI
import time
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import psutil
import os
from datetime import datetime
import json

# ─────────────────────────────────────────────
#  Proceso psutil persistente (evita overhead
#  de crear Process() en cada medición)
# ─────────────────────────────────────────────
_PROCESO_PSUTIL = psutil.Process()


def factorizar(n):
    """Devuelve los factores primos de n como lista."""
    factores = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factores.append(d)
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        factores.append(n)
    return factores


def medir_recursos():
    """
    Mide el uso de CPU y memoria del proceso actual.
    FIX: ya no recibe un argumento que se pisaba internamente;
         usa el proceso psutil global para evitar overhead.
    """
    cpu_percent = _PROCESO_PSUTIL.cpu_percent(interval=0.05)
    memory_info = _PROCESO_PSUTIL.memory_info()
    return {
        'cpu':          cpu_percent,
        'memoria_rss':  memory_info.rss / 1024 / 1024,   # MB
        'memoria_vms':  memory_info.vms / 1024 / 1024,   # MB
        'timestamp':    time.time(),
    }


def _recursos_con_fallback(recursos):
    """
    Retorna la lista de recursos, o una lista con valores neutros
    si está vacía (evita crash en np.mean/max de lista vacía).
    """
    if recursos:
        return recursos
    return [{'cpu': 0.0, 'memoria_rss': 0.0, 'memoria_vms': 0.0, 'timestamp': time.time()}]


def generar_graficas(maestra_tiempos, esclava_tiempos, tiempo_comunicacion,
                     maestra_recursos, esclava_recursos, numeros_procesados,
                     tiempos_por_numero_maestra, tiempos_por_numero_esclava):
    """
    Genera 5 graficas de rendimiento:
      1. Barras de tiempos totales
      2. Uso de CPU a lo largo del tiempo
      3. Uso de memoria a lo largo del tiempo
      4. Distribucion del trabajo (pie)
      5. Latencia por numero (scatter / line)
    """
    fig = plt.figure(figsize=(18, 12))
    gs  = gridspec.GridSpec(2, 3, figure=fig)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1:])   # grafica ancha para latencias

    mr = _recursos_con_fallback(maestra_recursos)
    er = _recursos_con_fallback(esclava_recursos)

    # -- 1. Tiempos de ejecucion --
    procesos = ['Maestra\n(computo)', 'Esclava\n(computo)', 'Comunicacion\n(scatter+gather)']
    tiempos  = [maestra_tiempos['total'], esclava_tiempos['total'], tiempo_comunicacion]
    colores  = ['#2ecc71', '#3498db', '#e74c3c']

    bars = ax1.bar(procesos, tiempos, color=colores, edgecolor='white', linewidth=1.2)
    ax1.set_ylabel('Tiempo (segundos)')
    ax1.set_title('Tiempo de ejecucion por proceso', fontweight='bold')
    for bar, v in zip(bars, tiempos):
        ax1.text(bar.get_x() + bar.get_width() / 2, v + max(tiempos) * 0.02,
                 f'{v:.4f}s', ha='center', va='bottom', fontsize=9)
    ax1.set_ylim(0, max(tiempos) * 1.18)

    # Speedup & eficiencia como texto en la grafica
    tiempo_sec_estimado = maestra_tiempos['total'] + esclava_tiempos['total']
    tiempo_paralelo     = max(maestra_tiempos['total'], esclava_tiempos['total'])
    speedup             = tiempo_sec_estimado / tiempo_paralelo if tiempo_paralelo > 0 else 1
    eficiencia          = speedup / 2 * 100
    ax1.text(0.98, 0.97,
             f'Speedup: {speedup:.2f}x\nEficiencia: {eficiencia:.1f}%',
             transform=ax1.transAxes, ha='right', va='top',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8),
             fontsize=9)

    # -- 2. CPU a lo largo del tiempo --
    xm = range(len(mr))
    xe = range(len(er))
    ax2.plot(xm, [r['cpu'] for r in mr], 'g-o', label='Maestra', linewidth=2, markersize=4)
    ax2.plot(xe, [r['cpu'] for r in er], 'b-s', label='Esclava',  linewidth=2, markersize=4)
    ax2.set_xlabel('Muestra #')
    ax2.set_ylabel('Uso de CPU (%)')
    ax2.set_title('CPU durante la ejecucion', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 105)

    # -- 3. Memoria a lo largo del tiempo --
    ax3.plot(xm, [r['memoria_rss'] for r in mr], 'g--o', label='Maestra', linewidth=2, markersize=4)
    ax3.plot(xe, [r['memoria_rss'] for r in er], 'b--s', label='Esclava',  linewidth=2, markersize=4)
    ax3.set_xlabel('Muestra #')
    ax3.set_ylabel('Memoria RSS (MB)')
    ax3.set_title('Memoria durante la ejecucion', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # -- 4. Distribucion del trabajo (pie) --
    nm = numeros_procesados['maestra']
    ne = numeros_procesados['esclava']
    ax4.pie([nm, ne],
            labels=[f'Maestra\n({nm})', f'Esclava\n({ne})'],
            colors=['#2ecc71', '#3498db'],
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops=dict(edgecolor='white', linewidth=2))
    ax4.set_title('Distribucion de trabajo', fontweight='bold')

    # -- 5. Latencia por numero procesado --
    if tiempos_por_numero_maestra:
        ax5.plot(range(len(tiempos_por_numero_maestra)),
                 [t * 1000 for t in tiempos_por_numero_maestra],
                 color='#2ecc71', alpha=0.7, linewidth=1, label='Maestra')
        # Linea de promedio
        prom_m = np.mean(tiempos_por_numero_maestra) * 1000
        ax5.axhline(prom_m, color='#27ae60', linestyle='--', linewidth=1.5,
                    label=f'Prom. Maestra {prom_m:.3f} ms')

    if tiempos_por_numero_esclava:
        offset = len(tiempos_por_numero_maestra)
        ax5.plot(range(offset, offset + len(tiempos_por_numero_esclava)),
                 [t * 1000 for t in tiempos_por_numero_esclava],
                 color='#3498db', alpha=0.7, linewidth=1, label='Esclava')
        prom_e = np.mean(tiempos_por_numero_esclava) * 1000
        ax5.axhline(prom_e, color='#2980b9', linestyle='--', linewidth=1.5,
                    label=f'Prom. Esclava {prom_e:.3f} ms')

    ax5.set_xlabel('Numero procesado (indice)')
    ax5.set_ylabel('Tiempo por numero (ms)')
    ax5.set_title('Latencia por numero (Maestra vs Esclava)', fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)

    plt.suptitle('Rendimiento - Factorizacion Distribuida con MPI', fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f'rendimiento_factorizacion_{timestamp}.png'
    plt.savefig(filename, dpi=120, bbox_inches='tight')
    print(f"\nGrafica guardada como: {filename}")
    plt.show()
    return filename


def guardar_metricas(maestra_tiempos, esclava_tiempos, comunicacion_tiempo,
                     maestra_recursos, esclava_recursos, numeros_procesados):
    """Guarda las metricas en un archivo JSON y muestra un resumen extendido."""

    mr = _recursos_con_fallback(maestra_recursos)
    er = _recursos_con_fallback(esclava_recursos)

    # Speedup y eficiencia
    t_paralelo  = max(maestra_tiempos['total'], esclava_tiempos['total'])
    t_secuencial = maestra_tiempos['total'] + esclava_tiempos['total']
    speedup     = t_secuencial / t_paralelo if t_paralelo > 0 else 1
    eficiencia  = speedup / 2

    metricas = {
        'timestamp': datetime.now().isoformat(),
        'tiempos': {
            'maestra':       maestra_tiempos,
            'esclava':       esclava_tiempos,
            'comunicacion':  comunicacion_tiempo,
            'paralelo_total': t_paralelo,
            'secuencial_estimado': t_secuencial,
        },
        'rendimiento': {
            'speedup':    round(speedup, 4),
            'eficiencia': round(eficiencia, 4),
        },
        'recursos': {
            'maestra': {
                'cpu_promedio':     float(np.mean([r['cpu']         for r in mr])),
                'cpu_max':          float(np.max ([r['cpu']         for r in mr])),
                'memoria_promedio': float(np.mean([r['memoria_rss'] for r in mr])),
                'memoria_max':      float(np.max ([r['memoria_rss'] for r in mr])),
            },
            'esclava': {
                'cpu_promedio':     float(np.mean([r['cpu']         for r in er])),
                'cpu_max':          float(np.max ([r['cpu']         for r in er])),
                'memoria_promedio': float(np.mean([r['memoria_rss'] for r in er])),
                'memoria_max':      float(np.max ([r['memoria_rss'] for r in er])),
            },
        },
        'numeros_procesados': numeros_procesados,
        'total_numeros': numeros_procesados['maestra'] + numeros_procesados['esclava'],
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f'metricas_factorizacion_{timestamp}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)
    print(f"Metricas guardadas como: {filename}")

    # -- Resumen extendido en consola --
    W = 55
    print("\n" + "=" * W)
    print("  RESUMEN DE RENDIMIENTO".center(W))
    print("=" * W)
    print(f"  Total numeros procesados : {metricas['total_numeros']}")
    print(f"  Maestra                  : {numeros_procesados['maestra']} numeros")
    print(f"  Esclava                  : {numeros_procesados['esclava']} numeros")

    print(f"\n  {'':─<{W-4}}")
    print(f"  {'Metrica':<28} {'Maestra':>10} {'Esclava':>10}")
    print(f"  {'':─<{W-4}}")
    print(f"  {'Tiempo computo (s)':<28} "
          f"{maestra_tiempos['total']:>10.4f} "
          f"{esclava_tiempos['total']:>10.4f}")
    print(f"  {'Tiempo prom/numero (ms)':<28} "
          f"{maestra_tiempos['promedio_por_numero']*1000:>10.4f} "
          f"{esclava_tiempos['promedio_por_numero']*1000:>10.4f}")
    print(f"  {'Tiempo min/numero (ms)':<28} "
          f"{maestra_tiempos['min_por_numero']*1000:>10.4f} "
          f"{esclava_tiempos['min_por_numero']*1000:>10.4f}")
    print(f"  {'Tiempo max/numero (ms)':<28} "
          f"{maestra_tiempos['max_por_numero']*1000:>10.4f} "
          f"{esclava_tiempos['max_por_numero']*1000:>10.4f}")
    print(f"  {'CPU promedio (%)':<28} "
          f"{metricas['recursos']['maestra']['cpu_promedio']:>10.1f} "
          f"{metricas['recursos']['esclava']['cpu_promedio']:>10.1f}")
    print(f"  {'CPU max (%)':<28} "
          f"{metricas['recursos']['maestra']['cpu_max']:>10.1f} "
          f"{metricas['recursos']['esclava']['cpu_max']:>10.1f}")
    print(f"  {'Memoria prom (MB)':<28} "
          f"{metricas['recursos']['maestra']['memoria_promedio']:>10.1f} "
          f"{metricas['recursos']['esclava']['memoria_promedio']:>10.1f}")
    print(f"  {'Memoria max (MB)':<28} "
          f"{metricas['recursos']['maestra']['memoria_max']:>10.1f} "
          f"{metricas['recursos']['esclava']['memoria_max']:>10.1f}")
    print(f"\n  Tiempo de comunicacion   : {comunicacion_tiempo:.4f} s")
    print(f"  Speedup                  : {speedup:.2f}x")
    print(f"  Eficiencia               : {eficiencia*100:.1f}%")
    print("=" * W)

    return filename


def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if size != 2:
        if rank == 0:
            print("Este programa requiere exactamente 2 procesos MPI.")
            print("Ejecutalo con:  mpirun -n 2 python factorizacion_primos_v2.py")
        comm.Abort(1)

    # -- Configuracion --
    RANGO_INICIO      = 1_000_000
    RANGO_FIN         = 1_001_000
    INTERVALO_MEDICION = 0.5   # segundos entre muestras de recursos

    # ======================================================================
    if rank == 0:  # -- PROCESO MAESTRA --
    # ======================================================================
        numeros = list(range(RANGO_INICIO, RANGO_FIN))
        mitad   = len(numeros) // 2
        mitad_maestra = numeros[mitad:]
        mitad_esclava = numeros[:mitad]

        print("=" * 60)
        print("INICIANDO FACTORIZACION DISTRIBUIDA")
        print("=" * 60)
        print(f"  Rango      : {RANGO_INICIO} -> {RANGO_FIN - 1}")
        print(f"  Total      : {len(numeros)} numeros")
        print(f"  Maestra    : {len(mitad_maestra)} numeros")
        print(f"  Esclava    : {len(mitad_esclava)} numeros")
        print("=" * 60)

        # -- Envio al esclavo (medimos tiempo de scatter) --
        t_scatter_ini = time.time()
        comm.send(mitad_esclava, dest=1, tag=0)
        t_scatter     = time.time() - t_scatter_ini
        print(f"Scatter -> {len(mitad_esclava)} numeros enviados al esclavo  ({t_scatter*1000:.2f} ms)")

        # -- Computo de la maestra --
        maestra_recursos      = []
        tiempos_por_numero    = []
        resultados_propios    = []

        t_computo_ini  = time.time()
        t_ultima_muestra = t_computo_ini

        for i, num in enumerate(mitad_maestra):
            t0 = time.perf_counter()
            factores = factorizar(num)
            tiempos_por_numero.append(time.perf_counter() - t0)
            resultados_propios.append((num, factores))

            if time.time() - t_ultima_muestra >= INTERVALO_MEDICION:
                maestra_recursos.append(medir_recursos())
                t_ultima_muestra = time.time()

            if (i + 1) % 100 == 0:
                pct = (i + 1) / len(mitad_maestra) * 100
                print(f"   [Maestra] {i+1}/{len(mitad_maestra)} ({pct:.0f}%) "
                      f"- ult. {tiempos_por_numero[-1]*1000:.3f} ms")

        t_computo_maestra = time.time() - t_computo_ini

        # -- Recibir resultados del esclavo (medimos tiempo de gather) --
        t_gather_ini      = time.time()
        resultados_esclavo = comm.recv(source=1, tag=1)
        t_gather           = time.time() - t_gather_ini

        tiempo_comunicacion = t_scatter + t_gather

        # Recibir metricas del esclavo
        esclava_tiempos, esclava_recursos, tiempos_por_numero_esclava = comm.recv(source=1, tag=3)

        # -- Armar dict de tiempos maestra --
        maestra_tiempos = {
            'total':               t_computo_maestra,
            'promedio_por_numero': float(np.mean(tiempos_por_numero)) if tiempos_por_numero else 0.0,
            'min_por_numero':      float(np.min (tiempos_por_numero)) if tiempos_por_numero else 0.0,
            'max_por_numero':      float(np.max (tiempos_por_numero)) if tiempos_por_numero else 0.0,
        }

        # -- Resultados detallados en consola --
        print("\n" + "=" * 60)
        print("RESULTADOS DETALLADOS")
        print("=" * 60)
        print(f"\n  Tiempos de computo:")
        print(f"   Maestra     : {maestra_tiempos['total']:.4f} s")
        print(f"   Esclava     : {esclava_tiempos['total']:.4f} s")
        print(f"\n  Tiempos de comunicacion:")
        print(f"   Scatter     : {t_scatter*1000:.2f} ms")
        print(f"   Gather      : {t_gather*1000:.2f} ms")
        print(f"   Total comm  : {tiempo_comunicacion*1000:.2f} ms")

        # Speedup rapido
        t_par = max(maestra_tiempos['total'], esclava_tiempos['total'])
        t_seq = maestra_tiempos['total'] + esclava_tiempos['total']
        print(f"\n  Speedup       : {t_seq/t_par:.2f}x  (eficiencia {t_seq/t_par/2*100:.1f}%)")

        print(f"\n  Ejemplos (primeros 5 de cada proceso):")
        for num, fact in resultados_propios[:5]:
            print(f"   [M] {num} = {' x '.join(map(str, fact))}")
        for num, fact in resultados_esclavo[:5]:
            print(f"   [E] {num} = {' x '.join(map(str, fact))}")

        # -- Graficas y metricas --
        print("\n" + "=" * 60)
        print("GENERANDO GRAFICAS Y METRICAS...")
        print("=" * 60)

        numeros_procesados = {
            'maestra': len(resultados_propios),
            'esclava': len(resultados_esclavo),
        }

        try:
            generar_graficas(
                maestra_tiempos, esclava_tiempos, tiempo_comunicacion,
                maestra_recursos, esclava_recursos, numeros_procesados,
                tiempos_por_numero, tiempos_por_numero_esclava,
            )
            guardar_metricas(
                maestra_tiempos, esclava_tiempos, tiempo_comunicacion,
                maestra_recursos, esclava_recursos, numeros_procesados,
            )
        except Exception as e:
            print(f"Error al generar graficas/metricas: {e}")

        print("\nPROCESO COMPLETADO")
        print("=" * 60)

    # ======================================================================
    elif rank == 1:  # -- PROCESO ESCLAVO --
    # ======================================================================
        numeros = comm.recv(source=0, tag=0)
        print(f"Esclavo recibio {len(numeros)} numeros.")

        esclava_recursos   = []
        tiempos_por_numero = []
        resultados         = []

        t_inicio      = time.time()
        t_ultima_muestra = t_inicio

        for i, num in enumerate(numeros):
            t0 = time.perf_counter()
            factores = factorizar(num)
            tiempos_por_numero.append(time.perf_counter() - t0)
            resultados.append((num, factores))

            if time.time() - t_ultima_muestra >= INTERVALO_MEDICION:
                esclava_recursos.append(medir_recursos())
                t_ultima_muestra = time.time()

        t_total = time.time() - t_inicio

        esclava_tiempos = {
            'total':               t_total,
            'promedio_por_numero': float(np.mean(tiempos_por_numero)) if tiempos_por_numero else 0.0,
            'min_por_numero':      float(np.min (tiempos_por_numero)) if tiempos_por_numero else 0.0,
            'max_por_numero':      float(np.max (tiempos_por_numero)) if tiempos_por_numero else 0.0,
        }

        # Enviar resultados y metricas (incluye tiempos por numero para la grafica 5)
        comm.send(resultados,                                          dest=0, tag=1)
        comm.send((esclava_tiempos, esclava_recursos, tiempos_por_numero), dest=0, tag=3)

        cpu_prom = (np.mean([r['cpu'] for r in esclava_recursos])
                    if esclava_recursos else 0.0)
        print(f"Esclavo completo {len(numeros)} numeros en {t_total:.3f} s  "
              f"(CPU prom: {cpu_prom:.1f}%)")


if __name__ == "__main__":
    main()