# Simulación de Eventos Discretos: Aeropuerto de Barajas

---

## 1. Descripción del sistema

El Aeropuerto de Barajas cuenta con 5 pistas de aterrizaje dedicadas a aviones de carga. Una pista se considera **ocupada** desde el momento en que un avión comienza a aterrizar hasta que termina de despegar. El objetivo de la simulación es estimar el **tiempo total que cada pista permanece vacía** durante una semana de operación.

Cuando un avión arriba al aeropuerto y no existen pistas libres, espera en una cola virtual con disciplina **FIFO** hasta que se desocupe una. Una vez asignado a una pista, el avión atraviesa la siguiente secuencia de fases:

1. **Aterrizaje** — duración aleatoria, Normal(10, 5) minutos.
2. **Recarga de combustible** — comienza simultáneamente con el aterrizaje; duración Exp(λ = 1/30) minutos.
3. **Carga y/o descarga** — ocurre con probabilidad uniforme (0.5); si ocurre, duración Exp(λ = 1/30) minutos.
4. **Revisión de averías** — detectada antes del despegue; probabilidad 0.1 de avería; reparación Exp(λ = 1/15) minutos.
5. **Despegue** — Normal(10, 5) minutos.

Las fases 1, 2 y 3 ocurren en paralelo. El avión no puede despegar hasta que las tres hayan concluido. La reparación (fase 4) se verifica justo antes de iniciar el despegue; si hay avería, la reparación retrasa el inicio del despegue. La pista solo queda libre al finalizar el despegue (fase 5).

Los tiempos entre llegadas de aviones siguen una distribución exponencial con λ = 1/20 aviones por minuto (media de 20 minutos entre llegadas). El horizonte de simulación es T = 7 × 24 × 60 = 10 080 minutos (una semana).

---

## 2. Marco teórico

### 2.1. Simulación de eventos discretos

La **simulación de eventos discretos** (SED) modela la evolución de un sistema en el que el estado solo cambia en instantes determinados llamados **eventos**. Entre dos eventos consecutivos el estado del sistema permanece constante, por lo que el reloj de simulación no avanza de forma continua sino que salta directamente de un evento al siguiente.

El mecanismo central es la **lista de eventos futuros** (LEF o *event queue*): una estructura de datos que almacena los eventos pendientes ordenados por tiempo. En cada iteración del bucle principal se extrae el evento más inminente, se avanza el reloj hasta ese instante y se ejecuta la rutina correspondiente, la cual puede a su vez programar nuevos eventos.

#### Bucle principal

```
Inicializar variables
Programar primer arribo
Mientras la LEF no esté vacía:
    e ← extraer el evento de menor tiempo de la LEF
    t ← e.tiempo
    Ejecutar la rutina de e
```

Este esquema es el mismo que se estudia en los modelos de servidor simple, servidores en paralelo y servidores en serie: la diferencia entre modelos reside en los **tipos de eventos** que existen y en la **lógica de cada rutina**, no en la estructura del bucle.

#### Relación con los modelos de clase

| Modelo de clase | Tipos de eventos | Variables de estado |
|---|---|---|
| Servidor simple | Arribo, Salida | n (clientes en sistema) |
| 2 Servidores en serie | Arribo, Salida S1, Salida S2 | n1, n2 |
| c Servidores en paralelo | Arribo, Salida | servidores libres, cola |
| **Aeropuerto de Barajas** | Arribo, Fin aterrizaje, Fin combustible, Fin carga, Fin reparación, Fin despegue | pistas[i], cola de espera, estado por avión |

El presente modelo extiende el esquema de **c servidores en paralelo** (con c = 5 pistas) añadiendo que el "servicio" no es una sola fase sino un conjunto de sub-eventos que deben completarse antes de que el recurso (la pista) quede libre.

### 2.2. Variables de la simulación

#### Variables de tiempo

| Símbolo | Descripción |
|---|---|
| t | Reloj actual de la simulación. Avanza saltando al evento más inminente. |
| tA | Instante del próximo arribo. Si no quedan arribos, tA = ∞. |
| tD_k | Instante del próximo evento de salida de la pista k. Si la pista está libre, tD_k = ∞. En la implementación se usa una cola de prioridad global que agrupa todos los eventos de todas las pistas. |

#### Variables contadoras y de estado

| Variable | Descripción |
|---|---|
| NA | Número total de aviones que han llegado al aeropuerto. |
| pistas[i] | Booleano: True si la pista i está ocupada, False si está libre. |
| cola_espera | Cola FIFO de aviones que esperan una pista libre. |
| estado[id] | Registro por avión: banderas landing_done, refuel_done, unload_done, repair_done. |
| runway_free_time[i] | Acumulador: tiempo total que la pista i ha estado libre hasta el momento. |
| runway_last_freed[i] | Instante en que la pista i quedó libre por última vez (para calcular el intervalo libre actual). |

#### Inicialización

```
t = 0
NA = 0
pistas = [False, False, False, False, False]
cola_espera = []
runway_free_time = [0, 0, 0, 0, 0]
runway_last_freed = [0, 0, 0, 0, 0]

Generar t0 ~ Exp(1/20)
tA = t0
LEF = {Evento(tA, ARRIBO)}
```

### 2.3. Tipos de eventos y sus rutinas

El sistema tiene **seis tipos de eventos**. A continuación se describe cada uno con la misma notación de los apuntes de clase.

---

#### Evento de arribo: tA ≤ T

Condición: el evento más inminente en la LEF es un ARRIBO y tA ≤ T.

1. Avanzar el reloj: t ← tA.
2. Contabilizar: NA ← NA + 1. El valor NA es el identificador único del avión.
3. Programar el próximo arribo:
   - Generar tAt ~ Exp(1/20).
   - Si t + tAt ≤ T: insertar Evento(t + tAt, ARRIBO) en la LEF.
4. Asignar pista:
   - Si existe pista libre i: asignar el avión a la pista i → ejecutar rutina de asignación (ver §2.4).
   - Si todas ocupadas: cola_espera.append(NA).

---

#### Evento fin de aterrizaje: LANDING_END

Condición: el evento más inminente es FIN_ATERRIZAJE del avión id.

1. Avanzar el reloj: t ← evento.tiempo.
2. Marcar: estado[id].landing_done ← True.
3. Intentar despegue (ver §2.5).

---

#### Evento fin de combustible: REFUEL_END

Condición: el evento más inminente es FIN_COMBUSTIBLE del avión id.

1. Avanzar el reloj: t ← evento.tiempo.
2. Marcar: estado[id].refuel_done ← True.
3. Intentar despegue (ver §2.5).

---

#### Evento fin de carga/descarga: UNLOAD_END

Condición: el evento más inminente es FIN_CARGA del avión id.

1. Avanzar el reloj: t ← evento.tiempo.
2. Marcar: estado[id].unload_done ← True.
3. Intentar despegue (ver §2.5).

---

#### Evento fin de reparación: REPAIR_END

Condición: el evento más inminente es FIN_REPARACION del avión id.

1. Avanzar el reloj: t ← evento.tiempo.
2. Marcar: estado[id].repair_done ← True.
3. Generar tDt ~ Normal(10, 5); tDt ← max(0, tDt).
4. Insertar Evento(t + tDt, FIN_DESPEGUE, id) en la LEF.

---

#### Evento fin de despegue: TAKEOFF_END

Condición: el evento más inminente es FIN_DESPEGUE del avión id en pista k.

1. Avanzar el reloj: t ← evento.tiempo.
2. Eliminar el avión del registro de estados.
3. Liberar la pista: pistas[k] ← False.
4. Acumular tiempo libre para la pista k: runway_last_freed[k] ← t.
5. Si cola_espera no está vacía:
   - next_id ← cola_espera.popleft()
   - Ejecutar rutina de asignación de next_id a la pista k (ver §2.4).

---

#### Cierre del sistema

Cuando tA > T, no se insertan más eventos de arribo. El sistema continúa procesando los eventos de las pistas hasta que todas queden vacías. Esto es análogo al cierre descrito en los modelos de clase: los aviones que ya están en pista o en cola completan su ciclo normalmente.

Al finalizar, para cada pista i que siga libre en el instante final t_fin:

```
runway_free_time[i] += t_fin - runway_last_freed[i]
```

### 2.4. Rutina de asignación de pista

Cuando se asigna el avión id a la pista k:

1. pistas[k] ← True.
2. Acumular tiempo libre previo: runway_free_time[k] += t − runway_last_freed[k].
3. Determinar si habrá carga/descarga: unload ← Bernoulli(0.5). Si unload = False, marcar estado[id].unload_done ← True desde el inicio.
4. Generar y programar en paralelo:
   - Aterrizaje: tLt ← max(0, Normal(10, 5)); insertar Evento(t + tLt, FIN_ATERRIZAJE, id, k).
   - Combustible: tRt ← Exp(1/30); insertar Evento(t + tRt, FIN_COMBUSTIBLE, id, k).
   - Carga (si aplica): tUt ← Exp(1/30); insertar Evento(t + tUt, FIN_CARGA, id, k).

### 2.5. Rutina de intento de despegue (_try_takeoff)

Esta subrutina se llama cada vez que una de las fases paralelas termina. Solo actúa cuando **las tres condiciones previas al despegue están satisfechas**:

```
Si estado[id].landing_done = True
   Y estado[id].refuel_done = True
   Y estado[id].unload_done = True:

    averia ← Bernoulli(0.1)
    Si averia = True:
        tRep ← Exp(1/15)
        Insertar Evento(t + tRep, FIN_REPARACION, id, k)
    Si averia = False:
        tDt ← max(0, Normal(10, 5))
        Insertar Evento(t + tDt, FIN_DESPEGUE, id, k)
```

El uso de banderas booleanas por avión garantiza que esta rutina sea **idempotente**: aunque sea invocada hasta tres veces (una por cada fase paralela), solo programa el despegue en la última llamada que completa todas las condiciones.

---

## 3. Fundamentos estadísticos y probabilísticos

### 3.1. Variables aleatorias continuas utilizadas

#### Distribución Exponencial — tiempos entre llegadas y duraciones de servicio

Una variable aleatoria X sigue una distribución exponencial con parámetro λ > 0, escrito X ~ Exp(λ), si su función de densidad es:

```
f(x) = λ · e^(−λx),   x ≥ 0
```

Sus parámetros son:
- Media: E[X] = 1/λ
- Varianza: Var(X) = 1/λ²

La propiedad clave es la **ausencia de memoria**: dado que un avión lleva τ minutos en cola sin ser atendido, la distribución del tiempo restante de espera es la misma Exp(λ). Esto justifica su uso para modelar procesos de Poisson.

En el modelo se usa para:

| Variable | λ | Media |
|---|---|---|
| Tiempo entre llegadas | 1/20 | 20 min |
| Recarga de combustible | 1/30 | 30 min |
| Carga/descarga | 1/30 | 30 min |
| Reparación de avería | 1/15 | 15 min |

#### Distribución Normal — aterrizaje y despegue

Una variable aleatoria X sigue una distribución normal con media μ y varianza σ², escrito X ~ N(μ, σ²), si su función de densidad es:

```
f(x) = (1 / (σ√(2π))) · exp(−(x−μ)² / (2σ²))
```

Sus parámetros son:
- Media: E[X] = μ
- Varianza: Var(X) = σ²

En el modelo se usa para aterrizaje y despegue con μ = 10 min y σ² = 5 min². Dado que la distribución Normal puede tomar valores negativos y un tiempo no puede ser negativo, en la implementación se aplica max(0, X) para garantizar valores válidos.

#### Distribución Uniforme — probabilidad de carga/descarga

La variable U ~ U(0, 1) se usa para generar Bernoulli(0.5): si U < 0.5, el avión carga/descarga; en caso contrario no lo hace. El enunciado indica que esta probabilidad "corresponde a una distribución uniforme", lo que se interpreta como equiprobabilidad de ocurrencia.

### 3.2. Generación de variables aleatorias desde cero

La implementación no usa librerías externas de números aleatorios. Todos los valores se generan a partir de un **generador congruencial lineal (LCG)** y se transforman mediante los métodos matemáticos vistos en clase.

#### Generador congruencial lineal (LCG)

La semilla se actualiza en cada llamada según la recurrencia:

```
X_{n+1} = (a · X_n + c) mod m
U_n = X_n / m
```

Con los parámetros:
- a = 1 664 525
- c = 1 013 904 223
- m = 2³² = 4 294 967 296

Estos valores son los del generador de Numerical Recipes, conocidos por tener buen período (m = 2³²) y distribución uniforme aceptable. El resultado U_n ∈ [0, 1) aproxima una variable U(0, 1).

#### Método de la transformada inversa — distribución Exponencial

Dado U ~ U(0, 1), si F es la CDF de una distribución continua, entonces X = F⁻¹(U) tiene distribución F.

Para la exponencial, F(x) = 1 − e^(−λx), por lo que F⁻¹(u) = −(1/λ) ln(1 − u). Como 1 − U tiene la misma distribución que U cuando U ~ U(0,1), se simplifica a:

```
X = −(1/λ) · ln(U),   U ~ U(0,1), U ≠ 0
```

En código:

```python
def exponential(lam):
    u = _lcg()
    return -1.0 / lam * math.log(u)
```

#### Método de Box-Muller — distribución Normal

Para generar X ~ N(μ, σ²) se utilizan dos uniformes independientes U₁, U₂ ~ U(0,1):

```
Z = √(−2 ln U₁) · cos(2π U₂)
X = μ + σ · Z
```

Z sigue una distribución N(0, 1) estándar. Este resultado se demuestra por el teorema de cambio de variable en 2D: el jacobiano de la transformación (U₁, U₂) → (Z₁, Z₂) produce exactamente el producto de dos densidades normales estándar.

En código:

```python
def normal(mu, sigma2):
    sigma = math.sqrt(sigma2)
    u1 = _lcg()
    u2 = _lcg()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z
```

#### Variable de Bernoulli — comparación con umbral

Para generar X ~ Bernoulli(p):

```
X = 1  si U < p
X = 0  si U ≥ p
```

con U ~ U(0, 1). La probabilidad de que U < p es exactamente p, por la definición de la distribución uniforme. Se usa para la decisión de carga/descarga (p = 0.5) y para la avería (p = 0.1).

### 3.3. Proceso de Poisson y llegadas exponenciales

El modelo de llegadas de aviones es un **proceso de Poisson homogéneo** de tasa λ = 1/20 aviones/minuto. En un proceso de Poisson, los tiempos entre eventos consecutivos son independientes e idénticamente distribuidos (i.i.d.) según Exp(λ). Esta es la única distribución de tiempos entre llegadas compatible con la propiedad de ausencia de memoria, lo que a su vez es equivalente a que el número de llegadas en cualquier intervalo de longitud t siga una distribución Poisson(λt).

La generación de cada tiempo entre llegadas como:

```
tAt = −(1/λ) · ln(U)
```

es exactamente la simulación de un proceso de Poisson por el método de la transformada inversa.

### 3.4. Método de réplicas independientes

Para obtener estimaciones estadísticamente fiables se realizan **30 réplicas independientes** de la simulación de una semana. Cada réplica usa una semilla diferente para el LCG, garantizando independencia entre réplicas.

Sea X_i el tiempo total de idle de una pista en la réplica i (i = 1, ..., 30). El estimador puntual de la media es:

```
X̄ = (1/n) · Σ X_i
```

La varianza muestral es:

```
S² = (1/(n-1)) · Σ (X_i − X̄)²
```

Y el intervalo de confianza al 95% para la media poblacional es aproximadamente:

```
X̄ ± t_{n-1, 0.025} · S / √n
```

donde t_{n-1, 0.025} es el cuantil de la distribución t de Student con n − 1 grados de libertad. Con n = 30 réplicas, t_{29, 0.025} ≈ 2.045, lo que da una estimación de la precisión suficiente para el análisis.

---

## 4. Implementación

### 4.1. Estructura del proyecto

```
barajas-airport-sim/
├── src/
│   ├── random_vars.py    generadores de variables aleatorias
│   ├── events.py         tipos de eventos y dataclass Event
│   ├── simulation.py     núcleo de la simulación de eventos discretos
│   └── main.py           punto de entrada, ejecución de réplicas
└── .gitignore
```

El proyecto está versionado con Git. Cada módulo fue creado en un commit atómico independiente.

### 4.2. Módulo random_vars.py — generación de variables aleatorias

```python
import math

_state = ...  # semilla global

def _lcg() -> float:
    # X_{n+1} = (1664525 * X_n + 1013904223) mod 2^32
    # retorna X_n / 2^32  in [0, 1)
    ...

def exponential(lam: float) -> float:
    # transformada inversa: -1/lam * ln(U)
    u = _lcg()
    return -1.0 / lam * math.log(u)

def normal(mu: float, sigma2: float) -> float:
    # Box-Muller: Z = sqrt(-2 ln U1) * cos(2*pi*U2)
    sigma = math.sqrt(sigma2)
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z

def bernoulli(p: float) -> bool:
    return _lcg() < p
```

### 4.3. Módulo events.py — tipos de eventos

```python
class EventType(Enum):
    ARRIVAL      # avión llega al aeropuerto
    LANDING_END  # fin del aterrizaje
    REFUEL_END   # fin de la recarga de combustible
    UNLOAD_END   # fin de carga/descarga
    REPAIR_END   # fin de reparación
    TAKEOFF_END  # fin del despegue — pista queda libre

@dataclass(order=True)
class Event:
    time: float       # instante del evento (campo de ordenación)
    etype: EventType  # tipo de evento
    plane_id: int     # identificador del avión
    runway_id: int    # pista asignada (-1 para ARRIVAL)
```

El dataclass `Event` se ordena por `time`, lo que permite usarlo directamente en el heap de Python (`heapq`).

### 4.4. Módulo simulation.py — núcleo DES

La clase `AirportSimulation` encapsula todo el estado del sistema:

```python
class AirportSimulation:
    clock: float                    # reloj de simulación (t)
    event_queue: List[Event]        # LEF implementada como min-heap
    arrival_queue: deque            # cola FIFO de aviones esperando pista
    runways: List[bool]             # pistas[i] = True si ocupada
    runway_free_time: List[float]   # acumulador de tiempo libre por pista
    runway_last_freed: List[float]  # instante en que pista i quedó libre
    planes: Dict[int, PlaneState]   # estado actual de cada avión en pista
```

El bucle principal:

```python
while event_queue:
    event = heappop(event_queue)          # extraer evento más inminente
    if ARRIVAL and event.time > T: skip   # cierre: no más llegadas
    clock = event.time                    # avanzar reloj
    dispatch(event)                       # ejecutar rutina correspondiente
```

La LEF se implementa como un **min-heap** (`heapq` de Python), que garantiza extracción del mínimo en O(log n) e inserción en O(log n). Esto es la generalización directa del método de comparar tA, tD1, tD2, ... descrito en los apuntes para c servidores en paralelo: en lugar de variables separadas tD1, ..., tDc, se mantiene una única estructura con todos los tiempos futuros.

La subrutina `_try_takeoff` implementa la **barrera de sincronización** entre las fases paralelas:

```python
def _try_takeoff(plane_id):
    estado = planes[plane_id]
    if landing_done AND refuel_done AND unload_done:
        # todas las fases completadas: verificar avería y programar despegue
        ...
```

Esta barrera se invoca al finalizar cada una de las tres fases; solo en la última llamada (cuando la última condición se cumple) se programa el despegue.

### 4.5. Módulo main.py — réplicas y resultados

```python
REPLICATIONS = 30

for rep in range(REPLICATIONS):
    seed(rep * 31337 + 1)          # semilla diferente por réplica
    sim = AirportSimulation()
    results = sim.run()
    acumular resultados

reportar promedios por pista
```

---

## 5. Variables del modelo — tabla resumen

Siguiendo la notación de los apuntes:

### Variables de tiempo

| Variable | Descripción |
|---|---|
| t | Reloj de simulación. Avanza saltando al evento más inminente. |
| tA | Instante del próximo arribo. Si tA > T o no hay más, tA = ∞. |
| tL_id | Instante de fin de aterrizaje del avión id. |
| tR_id | Instante de fin de combustible del avión id. |
| tU_id | Instante de fin de carga del avión id (si aplica). |
| tRep_id | Instante de fin de reparación del avión id (si hay avería). |
| tD_id | Instante de fin de despegue del avión id. Al ocurrir, la pista queda libre. |

Todos estos tiempos están almacenados en la LEF. El siguiente evento es siempre min(LEF).

### Variables contadoras

| Variable | Descripción |
|---|---|
| NA | Total de aviones que han llegado al aeropuerto. |
| ND | Total de aviones que han completado su ciclo y despegado. |

### Variables de estado

| Variable | Descripción |
|---|---|
| pistas[i], i = 0..4 | True si la pista i está ocupada; False si está libre. |
| cola_espera | Cola FIFO de ids de aviones esperando pista disponible. |
| estado[id].landing_done | Bandera: aterrizaje completado. |
| estado[id].refuel_done | Bandera: combustible completado. |
| estado[id].unload_done | Bandera: carga/descarga completada (o no requerida). |
| estado[id].repair_done | Bandera: reparación completada (si hubo avería). |

### Acumuladores de la métrica objetivo

| Variable | Descripción |
|---|---|
| runway_free_time[i] | Tiempo total acumulado que la pista i ha estado libre (minutos). |
| runway_last_freed[i] | Instante en que la pista i quedó libre por última vez. |

La métrica objetivo se calcula incrementalmente: cada vez que una pista queda libre en el instante t, se registra runway_last_freed[i] = t. Cuando la pista vuelve a ocuparse en el instante t', se acumula:

```
runway_free_time[i] += t' − runway_last_freed[i]
```

Al finalizar la simulación se suma el tiempo libre restante para las pistas que sigan desocupadas.

---

## 6. Resultados de la simulación

Se ejecutaron 30 réplicas independientes de una semana de operación (T = 10 080 minutos). Los resultados promedio son:

| Pista | Tiempo idle promedio (min) | Porcentaje del horizonte |
|---|---|---|
| Pista 1 | 2 721 | 27.0 % |
| Pista 2 | 3 750 | 37.2 % |
| Pista 3 | 5 052 | 50.1 % |
| Pista 4 | 6 397 | 63.5 % |
| Pista 5 | 7 630 | 75.7 % |

**Promedio de aviones atendidos por semana:** ~501

### Interpretación

La asimetría entre pistas es consecuencia directa de la política de asignación: la pista 1 siempre se asigna primero (es la primera libre encontrada), por lo que recibe la mayor carga. La pista 5 recibe carga solo cuando las cuatro anteriores están ocupadas simultáneamente, lo cual es infrecuente dado el nivel de tráfico (λ = 1/20 y servicio medio de ~77 minutos por avión: carga media del sistema ≈ 3.85 pistas ocupadas en promedio, lo que explica que la pista 5 esté libre el 75% del tiempo).

El tiempo de servicio medio por avión se estima como:
- Aterrizaje: 10 min
- Combustible: 30 min (generalmente el cuello de botella)
- Carga (50% de los aviones): 0.5 × 30 = 15 min esperado, pero en paralelo
- Reparación (10%): 0.1 × 15 = 1.5 min esperado
- Despegue: 10 min

Como el aterrizaje, combustible y carga ocurren en paralelo, el tiempo de espera entre inicio y despegue depende del máximo de las tres: E[max(Normal(10,5), Exp(1/30), Exp(1/30) si aplica)] + E[reparación] + E[despegue].

---

## 7. Consideraciones del modelo

1. **Paralelismo de fases:** A diferencia de los modelos de clase (donde el servicio es una sola fase), aquí el "servicio" consiste en tres fases simultáneas más dos fases secuenciales. Esto requiere la barrera de sincronización (_try_takeoff) que verifica que todas las fases paralelas hayan concluido antes de proceder.

2. **Cola global vs. cola por pista:** Se usa una única cola FIFO de entrada (análoga al modelo de c servidores en paralelo de los apuntes). Al quedar libre una pista, se toma el primer avión en espera. No existe preferencia por pistas específicas.

3. **Distribución Normal con truncamiento:** La distribución Normal puede producir valores negativos. Dado que los tiempos de aterrizaje y despegue deben ser no negativos, se aplica max(0, X). Con μ = 10 y σ = √5 ≈ 2.24, la probabilidad de obtener X < 0 es P(Z < −10/2.24) ≈ P(Z < −4.47) ≈ 0.000004, prácticamente despreciable.

4. **Horizonte de simulación:** El enunciado pide simular una semana. Al alcanzar T = 10 080 minutos, se deja de admitir nuevos aviones pero se completan los ciclos de los que ya están en pista o en cola, en analogía exacta con el "cierre del sistema" descrito en los apuntes.

5. **Réplicas independientes:** Dado que la simulación tiene componentes aleatorios, una sola réplica no es suficiente para estimar parámetros del sistema. Las 30 réplicas permiten calcular un estimador de la media con varianza conocida.
