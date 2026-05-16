# Informe de Proyecto
## Simulación basada en Eventos Discretos

---

## Generales del Estudiante

| | |
|---|---|
| **Nombre y apellidos** | Melissa Maureen Sales Brito |
| **Grupo** | C-311 |
| **Asignatura** | Simulación |
| **Problema asignado** | Problema 5 — Aeropuerto de Barajas |
| **Lenguaje de implementación** | Python 3 |
| **Repositorio** | [ENLACE_GITHUB] |

---

## Orden del Problema Asignado

**Problema 5 — Aeropuerto de Barajas**

El Aeropuerto de Barajas cuenta con 5 pistas de aterrizaje dedicadas a aviones de carga. Se considera que una pista está ocupada cuando hay un avión aterrizando, despegando, cargando o descargando mercancía, o recargando combustible. El objetivo es simular el comportamiento del aeropuerto durante una semana y **estimar el tiempo total en que se encuentra vacía cada una de las 5 pistas**.

---

## Principales Ideas Seguidas para la Solución del Problema

### 1. Identificación del sistema como un modelo de servidores en paralelo extendido

El sistema se reconoció como una variante del modelo de **c servidores en paralelo** estudiado en clase, con c = 5 pistas. Sin embargo, a diferencia del modelo clásico donde el servicio es una única fase, aquí el "servicio" de cada avión consta de **múltiples fases con distinta naturaleza temporal**:

- Fases en **paralelo** (ocurren simultáneamente desde que el avión ocupa la pista): aterrizaje, recarga de combustible y carga/descarga de mercancía.
- Fases en **secuencia** (ocurren después): verificación de avería y despegue.

La idea central fue representar cada fase como un **evento independiente** en la lista de eventos futuros, y usar una **barrera de sincronización** que verifique, cada vez que termina una fase paralela, si ya es posible proceder al despegue.

### 2. Representación del estado con banderas por avión

Para cada avión en pista se mantiene un registro de banderas booleanas (`landing_done`, `refuel_done`, `unload_done`, `repair_done`) que indican qué fases han concluido. El despegue solo se programa cuando las tres fases paralelas están completas. Esto permite que los eventos de las tres fases sean completamente independientes entre sí en la lista de eventos.

### 3. Cola FIFO global de entrada

Se utiliza una única cola de espera para los aviones que no encuentran pista disponible al llegar, en analogía con el modelo de c servidores en paralelo de los apuntes. Al liberarse una pista, se toma el primer avión en espera (disciplina FIFO) y se inicia su ciclo de servicio.

### 4. Métrica de tiempo idle acumulada incrementalmente

El tiempo libre de cada pista se acumula de forma incremental: cada vez que una pista queda libre se registra el instante, y cada vez que vuelve a ocuparse se suma la diferencia. Al finalizar la simulación se añade el tiempo libre restante de las pistas que sigan desocupadas. Este mecanismo evita recorrer el historial completo al final.

### 5. Generación de variables aleatorias desde cero

Todas las muestras aleatorias se generan sin bibliotecas externas, implementando:
- Un **generador congruencial lineal (LCG)** como fuente de uniformes U(0,1).
- El **método de la transformada inversa** para la distribución exponencial.
- El **método de Box-Muller** para la distribución normal.
- **Comparación con umbral** para variables de Bernoulli.

### 6. Réplicas independientes para estimación estadística

Una única réplica no es suficiente para caracterizar el sistema estocástico. Se ejecutaron **30 réplicas independientes** con semillas distintas para el generador, obteniendo estimaciones promedio por pista con variabilidad controlada.

---

## Modelo de Simulación de Eventos Discretos

### Descripción del sistema

Un avión llega al aeropuerto y espera en cola (FIFO) hasta que exista una pista vacía. Al ocupar una pista, el avión realiza la siguiente secuencia:

1. **Aterrizaje** — Normal(μ=10, σ²=5) minutos — comienza al ocupar la pista.
2. **Recarga de combustible** — Exp(λ=1/30) minutos — comienza simultáneamente con el aterrizaje.
3. **Carga/descarga de mercancía** — con probabilidad 0.5 ocurre; duración Exp(λ=1/30) minutos — comienza simultáneamente con el aterrizaje.
4. **Verificación de avería** — con probabilidad 0.1 hay una rotura; reparación Exp(λ=1/15) minutos — se verifica cuando las fases 1, 2 y 3 han concluido.
5. **Despegue** — Normal(μ=10, σ²=5) minutos — comienza tras resolver la avería (si la hubo).

La pista queda libre únicamente al finalizar el despegue. El horizonte de simulación es T = 7 × 24 × 60 = 10 080 minutos (una semana). Al alcanzar T, no se admiten nuevos aviones pero los que ya están en pista o en cola completan su ciclo.

Los tiempos entre llegadas de aviones siguen una distribución Exp(λ=1/20), con una media de 20 minutos entre aviones.

### Tipos de eventos

El sistema cuenta con **seis tipos de eventos**:

| Evento | Condición de disparo |
|---|---|
| ARRIBO | Un nuevo avión llega al aeropuerto |
| FIN_ATERRIZAJE | El avión completa la fase de aterrizaje |
| FIN_COMBUSTIBLE | El avión completa la recarga de combustible |
| FIN_CARGA | El avión completa la carga/descarga (si aplica) |
| FIN_REPARACION | El avión completa la reparación (si hay avería) |
| FIN_DESPEGUE | El avión termina de despegar — pista queda libre |

### Variables de la simulación

**Variables de tiempo:**

- **t** — reloj actual de la simulación. Avanza saltando al evento más inminente.
- **tA** — instante del próximo arribo. Si tA > T o no quedan aviones por llegar, tA = ∞.
- **LEF** — lista de eventos futuros (min-heap): contiene todos los eventos pendientes de todas las pistas. El próximo evento es siempre min(LEF).

**Variables contadoras:**

- **NA** — número total de aviones que han llegado al aeropuerto.
- **ND** — número total de aviones que han completado su ciclo y despegado.

**Variables de estado:**

- **pistas[i]**, i = 0..4 — booleano: True si la pista i está ocupada, False si está libre.
- **cola\_espera** — cola FIFO con los identificadores de aviones que esperan pista.
- **estado[id].landing\_done** — bandera: aterrizaje completado.
- **estado[id].refuel\_done** — bandera: combustible completado.
- **estado[id].unload\_done** — bandera: carga/descarga completada (o no requerida).
- **estado[id].repair\_done** — bandera: reparación completada (si hubo avería).

**Acumuladores de la métrica objetivo:**

- **runway\_free\_time[i]** — tiempo total acumulado que la pista i ha estado libre (minutos).
- **runway\_last\_freed[i]** — instante en que la pista i quedó libre por última vez.

### Inicialización

```text
t = 0,  NA = 0,  ND = 0
pistas = [False, False, False, False, False]
cola_espera = []
runway_free_time = [0, 0, 0, 0, 0]
runway_last_freed = [0, 0, 0, 0, 0]

Generar t₀ ~ Exp(1/20)
tA = t₀
LEF = { Evento(tA, ARRIBO) }
```

### Bucle principal

En cada iteración se extrae el evento de menor tiempo de la LEF:

```text
Mientras LEF no esté vacía:
    e ← extraer min(LEF)
    Si e es ARRIBO y e.tiempo > T: descartar, continuar
    t ← e.tiempo
    Ejecutar rutina del evento e
```

Cuando tA > T se deja de insertar eventos de ARRIBO. El bucle continúa hasta que todas las pistas queden vacías.

### Rutinas de cada evento

#### Evento de arribo — tA ≤ T

Condición: el evento más inminente es ARRIBO y tA ≤ T.

1. Avanzar el reloj: t ← tA.
2. Contabilizar: NA ← NA + 1. El valor de NA es el identificador único del avión.
3. Programar el próximo arribo: generar tAt ~ Exp(1/20). Si t + tAt ≤ T: insertar Evento(t + tAt, ARRIBO) en la LEF.
4. Asignar pista:
   - Si existe pista libre i: ejecutar rutina de asignación del avión NA a la pista i.
   - Si todas las pistas están ocupadas: cola\_espera.append(NA).

#### Rutina de asignación de pista (subrutina)

Cuando se asigna el avión id a la pista k:

1. pistas[k] ← True.
2. Acumular tiempo libre previo: runway\_free\_time[k] += t − runway\_last\_freed[k].
3. Determinar carga/descarga: unload ← Bernoulli(0.5).
   - Si unload = False: estado[id].unload\_done ← True (no requiere ese evento).
4. Generar y programar en paralelo:
   - tLt ← max(0, Normal(10, 5)); insertar Evento(t + tLt, FIN\_ATERRIZAJE, id, k).
   - tRt ← Exp(1/30); insertar Evento(t + tRt, FIN\_COMBUSTIBLE, id, k).
   - Si unload = True: tUt ← Exp(1/30); insertar Evento(t + tUt, FIN\_CARGA, id, k).

#### Evento fin de aterrizaje

1. Avanzar el reloj: t ← evento.tiempo.
2. estado[id].landing\_done ← True.
3. Llamar a la subrutina de intento de despegue.

#### Evento fin de combustible

1. Avanzar el reloj: t ← evento.tiempo.
2. estado[id].refuel\_done ← True.
3. Llamar a la subrutina de intento de despegue.

#### Evento fin de carga/descarga

1. Avanzar el reloj: t ← evento.tiempo.
2. estado[id].unload\_done ← True.
3. Llamar a la subrutina de intento de despegue.

#### Subrutina de intento de despegue

Se ejecuta cada vez que concluye una fase paralela. Solo actúa si las tres condiciones están satisfechas:

```text
Si landing_done = True  Y  refuel_done = True  Y  unload_done = True:
    averia ← Bernoulli(0.1)
    Si averia = True:
        tRep ← Exp(1/15)
        Insertar Evento(t + tRep, FIN_REPARACION, id, k) en LEF
    Si averia = False:
        tDt ← max(0, Normal(10, 5))
        Insertar Evento(t + tDt, FIN_DESPEGUE, id, k) en LEF
```

Esta subrutina es idempotente: aunque se invoca hasta tres veces (una por fase), solo programa el despegue en la llamada donde se completa la última condición.

#### Evento fin de reparación

1. Avanzar el reloj: t ← evento.tiempo.
2. estado[id].repair\_done ← True.
3. Generar tDt ← max(0, Normal(10, 5)); insertar Evento(t + tDt, FIN\_DESPEGUE, id, k) en LEF.

#### Evento fin de despegue

Condición: el evento más inminente es FIN\_DESPEGUE del avión id en pista k.

1. Avanzar el reloj: t ← evento.tiempo.
2. ND ← ND + 1.
3. Eliminar registro del avión: borrar estado[id].
4. Liberar la pista: pistas[k] ← False; runway\_last\_freed[k] ← t.
5. Si cola\_espera no está vacía:
   - next\_id ← cola\_espera.popleft().
   - Ejecutar rutina de asignación de next\_id a la pista k.

#### Cierre del sistema

Cuando el evento más inminente es ARRIBO con tiempo > T, se descarta y se establece tA = ∞. A partir de ese momento solo se procesan eventos de fases en curso. La simulación concluye cuando todas las pistas están vacías (pistas = [False,...,False]) y la LEF no contiene más eventos de fases activas.

Al finalizar, para cada pista i que esté libre en el instante final t\_fin:

```text
runway_free_time[i] += t_fin − runway_last_freed[i]
```

### Generación de variables aleatorias

Todas las muestras se generan a partir de un **generador congruencial lineal (LCG)** con la recurrencia:

```text
X_{n+1} = (1 664 525 · X_n + 1 013 904 223)  mod  2³²
U_n = X_n / 2³²
```

que produce valores U_n ∈ [0, 1) aproximando una distribución U(0, 1).

**Distribución Exponencial — método de la transformada inversa:**

Dado que la CDF de Exp(λ) es F(x) = 1 − e^(−λx), su inversa es F⁻¹(u) = −(1/λ)·ln(1−u). Como 1−U tiene la misma distribución que U cuando U ~ U(0,1):

```text
X = −(1/λ) · ln(U)
```

**Distribución Normal — método de Box-Muller:**

Con dos uniformes independientes U₁, U₂ ~ U(0,1):

```text
Z = √(−2 ln U₁) · cos(2π U₂)
X = μ + σ · Z,   con σ = √σ²
```

Z sigue una distribución N(0,1), por lo que X ~ N(μ, σ²). Dado que la normal puede tomar valores negativos, se aplica max(0, X) para los tiempos de aterrizaje y despegue.

**Variable de Bernoulli — comparación con umbral:**

```text
X = True   si U < p
X = False  si U ≥ p
```

con U ~ U(0,1). Se usa con p = 0.5 para la decisión de carga/descarga y con p = 0.1 para la avería.

---

## Consideraciones Obtenidas a partir de la Ejecución de las Simulaciones

Se ejecutaron **30 réplicas independientes** del sistema, cada una simulando una semana completa de operación (T = 10 080 minutos). Los resultados reales obtenidos son los siguientes.

### Resultados por pista

| Pista | Media idle (min) | % de T | Desv. estándar | Mínimo | Máximo | IC 95% (min) |
| --- | --- | --- | --- | --- | --- | --- |
| Pista 1 | 2 721.2 | 27.0 % | 252.1 | 2 350.7 | 3 308.6 | [2 627.1 — 2 815.3] |
| Pista 2 | 3 750.4 | 37.2 % | 362.1 | 2 786.2 | 4 239.7 | [3 615.2 — 3 885.6] |
| Pista 3 | 5 051.9 | 50.1 % | 440.1 | 4 206.6 | 6 255.4 | [4 887.6 — 5 216.2] |
| Pista 4 | 6 397.4 | 63.5 % | 505.5 | 5 513.7 | 7 578.1 | [6 208.6 — 6 586.1] |
| Pista 5 | 7 630.0 | 75.7 % | 606.2 | 6 419.5 | 8 908.6 | [7 403.7 — 7 856.4] |

Los intervalos de confianza al 95% se calcularon con t(29, 0.025) = 2.045.

### Resultados globales

| Métrica | Valor |
|---|---|
| Aviones atendidos por semana (media) | 500.6 |
| Aviones atendidos — desviación estándar | 29.1 |
| Aviones atendidos — mínimo (entre réplicas) | 428 |
| Aviones atendidos — máximo (entre réplicas) | 555 |
| Aviones en cola al cierre del sistema (media) | 0.00 |
| Tiempo idle total (suma 5 pistas, media) | 25 550.9 min |
| Tiempo idle total — desviación estándar | 1 855.8 min |
| Tiempo idle total — mínimo | 21 755.7 min |
| Tiempo idle total — máximo | 30 262.3 min |
| Porcentaje idle promedio por pista | 50.7 % |

### Consideración 1 — Asimetría entre pistas

Las cinco pistas son físicamente equivalentes, sin embargo presentan tiempos de idle muy distintos: la pista 1 está libre el 27.0% del tiempo mientras que la pista 5 lo está el 75.7%. Esta diferencia de 4 909 minutos (más de 3 días) entre la pista más cargada y la menos cargada es consecuencia directa de la política de asignación: siempre se selecciona la primera pista libre disponible (índice más bajo). La pista 1 es la primera candidata en casi todos los arribos, mientras que la pista 5 solo se ocupa cuando las cuatro anteriores están simultáneamente ocupadas.

Si el objetivo fuera equilibrar el desgaste entre pistas, bastaría con cambiar la política de asignación a **round-robin** o **menor tiempo acumulado de uso**, sin modificar ninguna otra parte del modelo.

### Consideración 2 — Estabilidad del sistema

En ninguna de las 30 réplicas quedaron aviones en cola al cierre del sistema (media = 0.00, máximo = 0). Esto confirma que el sistema es **estable**: la tasa de llegadas no supera la capacidad de servicio. Con λ = 1/20 aviones/minuto y un tiempo de servicio medio aproximado de 77 minutos, la carga teórica es:

```text
ρ = λ · E[servicio] / c = (1/20) · 77 / 5 ≈ 0.77
```

El sistema opera al 77% de su capacidad en promedio, con margen suficiente para absorber los picos de llegadas sin acumulación permanente de cola.

### Consideración 3 — El combustible es el cuello de botella

La recarga de combustible (media 30 min, presente en el 100% de los vuelos) domina sobre el aterrizaje (media 10 min) y sobre la carga/descarga (media 30 min pero solo en el 50% de los vuelos, contribuyendo 15 min en esperanza). En la mayoría de los aviones, la subrutina de intento de despegue se activa en el evento FIN\_COMBUSTIBLE, siendo este el último en completarse. Reducir el tiempo de repostaje sería la intervención más efectiva para aumentar el throughput del aeropuerto.

### Consideración 4 — Impacto de la avería

Con probabilidad 0.1 y una reparación de media 15 minutos, la avería añade en esperanza 1.5 minutos al ciclo de cada avión. Sobre 500 aviones por semana, esto suma aproximadamente 750 minutos (12.5 horas) de ocupación adicional en las pistas. El efecto es pequeño en términos relativos (menos del 2% del tiempo de servicio medio) pero no despreciable a escala semanal.

### Consideración 5 — Variabilidad entre réplicas

La desviación estándar del tiempo idle total (suma de las 5 pistas) es de 1 855.8 minutos, con un rango de casi 8 507 minutos entre la réplica con menor idle (21 755.7 min) y la de mayor idle (30 262.3 min). Esto refleja la alta variabilidad inherente al sistema estocástico: una semana real puede diferir significativamente del valor esperado. Los intervalos de confianza al 95% muestran que las estimaciones son precisas (ancho del IC entre 188 y 453 minutos por pista), validando el uso de 30 réplicas.

### Consideración 6 — Sensibilidad al parámetro λ

Un incremento en la tasa de llegadas reduciría el tiempo idle de todas las pistas. El umbral de saturación del sistema se alcanza cuando:

```text
λ · E[servicio] = c  →  λ_max = 5 / 77 ≈ 0.065 aviones/min  (1 avión cada ~15.4 min)
```

El valor actual λ = 1/20 = 0.05 aviones/min está un 23% por debajo de ese umbral. Un aumento del tráfico aéreo de un 20-23% llevaría el sistema al límite de su capacidad, con colas creciendo indefinidamente.

---

## Enlace al Repositorio en GitHub

[ENLACE_GITHUB]
