# Factorización Distribuida de Números Primos con MPI

Implementación del algoritmo de factorización de números primos usando **MPI (Message Passing Interface)** en un clúster de 3 máquinas virtuales Ubuntu bajo el paradigma maestro-esclavo.

## Descripción

El programa distribuye la factorización de 1.000 números enteros (rango 1.000.000 – 1.001.000) entre dos procesos MPI. El proceso maestro divide el trabajo en dos mitades iguales, retiene una y envía la otra al proceso esclavo. Al finalizar, recolecta los resultados y genera gráficas y métricas de rendimiento.

## Resultados

| Métrica | Valor |
|---|---|
| Total números procesados | 1.000 |
| Tiempo cómputo Maestra | 0,0036 s |
| Tiempo cómputo Esclava | 0,0043 s |
| Tiempo comunicación total | 1,86 ms |
| Speedup | 1,84x |
| Eficiencia | 92,2% |

## Requisitos

- Python 3.x
- mpi4py
- numpy
- matplotlib
- psutil

```bash
pip install mpi4py numpy matplotlib psutil
```

## Uso

```bash
mpirun -n 2 python factorizacion_primos.py
```

> Requiere exactamente 2 procesos MPI. Asegúrate de tener SSH sin contraseña configurado entre los nodos del clúster.

## Archivos generados

- `rendimiento_factorizacion_<timestamp>.png` — gráficas de rendimiento
- `metricas_factorizacion_<timestamp>.json` — métricas en formato JSON

## Estructura del repositorio

```
MPI/
├── factorizacion_primos.py   # Código principal
└── README.md
```
## Link instalacion MPICH
https://mpitutorial.com/tutorials/installing-mpich2/
